from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ENUM_EDGE_FIELDS = [
    "directionality",
    "relationship_type",
    "causal_presentation",
    "edge_role",
    "claim_status",
    "explicitness",
    "sign",
    "statistical_significance",
    "evidence_method",
    "nature_of_evidence",
    "tentativeness",
]


DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize FWCI source-cut FrontierGraph extraction outputs into SQLite and merged JSONL.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--out-sqlite", default=None)
    parser.add_argument("--out-jsonl-gz", default=None)
    parser.add_argument("--out-summary-json", default=None)
    parser.add_argument("--out-summary-md", default=None)
    parser.add_argument("--out-manifest", default=None)
    parser.add_argument("--retry-run-dir", action="append", default=[], help="Optional retry run directory containing parsed_results.jsonl and responses/*.json")
    return parser.parse_args()


def short_work_id(work_id: str) -> str:
    return work_id.rstrip("/").split("/")[-1]


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def extract_response_output(response_json: dict[str, Any]) -> Any:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return json.loads(output_text)
    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return json.loads(text)
    raise ValueError("Could not extract structured JSON output from response payload.")


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE works (
            custom_id TEXT PRIMARY KEY,
            short_work_id TEXT NOT NULL,
            openalex_work_id TEXT NOT NULL,
            title TEXT NOT NULL,
            abstract TEXT NOT NULL,
            publication_year INTEGER NOT NULL,
            bucket TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_display_name TEXT NOT NULL,
            output_origin TEXT NOT NULL,
            batch_output_path TEXT NOT NULL,
            response_id TEXT,
            model TEXT,
            created_at INTEGER,
            completed_at INTEGER,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            cached_input_tokens INTEGER NOT NULL,
            reasoning_tokens INTEGER NOT NULL,
            node_count INTEGER NOT NULL,
            edge_count INTEGER NOT NULL
        );

        CREATE TABLE nodes (
            custom_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            label TEXT NOT NULL,
            surface_forms_json TEXT NOT NULL,
            unit_of_analysis_json TEXT NOT NULL,
            start_year_json TEXT NOT NULL,
            end_year_json TEXT NOT NULL,
            countries_json TEXT NOT NULL,
            context_note TEXT NOT NULL,
            PRIMARY KEY (custom_id, node_id),
            FOREIGN KEY (custom_id) REFERENCES works(custom_id)
        );

        CREATE TABLE edges (
            custom_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            directionality TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            causal_presentation TEXT NOT NULL,
            edge_role TEXT NOT NULL,
            claim_status TEXT NOT NULL,
            explicitness TEXT NOT NULL,
            condition_or_scope_text TEXT NOT NULL,
            claim_text TEXT NOT NULL,
            evidence_text TEXT NOT NULL,
            sign TEXT NOT NULL,
            effect_size TEXT NOT NULL,
            statistical_significance TEXT NOT NULL,
            evidence_method TEXT NOT NULL,
            evidence_method_other_description TEXT NOT NULL,
            nature_of_evidence TEXT NOT NULL,
            uses_data INTEGER NOT NULL,
            sources_of_exogenous_variation TEXT NOT NULL,
            tentativeness TEXT NOT NULL,
            PRIMARY KEY (custom_id, edge_id),
            FOREIGN KEY (custom_id) REFERENCES works(custom_id)
        );

        CREATE INDEX idx_works_year ON works(publication_year);
        CREATE INDEX idx_works_bucket ON works(bucket);
        CREATE INDEX idx_works_source ON works(source_id);
        CREATE INDEX idx_nodes_label ON nodes(label);
        CREATE INDEX idx_edges_source_node ON edges(source_node_id);
        CREATE INDEX idx_edges_target_node ON edges(target_node_id);
        CREATE INDEX idx_edges_method ON edges(evidence_method);
        CREATE INDEX idx_edges_role ON edges(edge_role);
        """
    )
    return conn


def percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac


class Summary:
    def __init__(self) -> None:
        self.record_count = 0
        self.node_counts: list[int] = []
        self.edge_counts: list[int] = []
        self.total_nodes = 0
        self.total_edges = 0
        self.zero_node = 0
        self.zero_edge = 0
        self.edge_scope_non_na = 0
        self.edge_evidence_text_na = 0
        self.edge_effect_size_non_na = 0
        self.node_context_country = 0
        self.node_context_year = 0
        self.node_context_unit = 0
        self.uses_data = Counter()
        self.edge_field_counters = {field: Counter() for field in ENUM_EDGE_FIELDS}
        self.bucket_counts = Counter()
        self.year_counts = Counter()
        self.source_counts = Counter()
        self.output_origin_counts = Counter()
        self.token_totals = Counter()

    def update(self, record: dict[str, Any]) -> None:
        raw_nodes = record["output"]["nodes"]
        raw_edges = record["output"]["edges"]
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        seen_node_ids: set[str] = set()
        seen_edge_ids: set[str] = set()
        for node in raw_nodes:
            node_id = str(node.get("node_id"))
            if node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)
            nodes.append(node)
        for edge in raw_edges:
            edge_id = str(edge.get("edge_id"))
            if edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            edges.append(edge)
        node_n = len(nodes)
        edge_n = len(edges)
        self.record_count += 1
        self.node_counts.append(node_n)
        self.edge_counts.append(edge_n)
        self.total_nodes += node_n
        self.total_edges += edge_n
        if node_n == 0:
            self.zero_node += 1
        if edge_n == 0:
            self.zero_edge += 1
        self.bucket_counts[record["bucket"]] += 1
        self.year_counts[int(record["publication_year"])] += 1
        self.source_counts[record["source_display_name"]] += 1
        self.output_origin_counts[record["output_origin"]] += 1
        self.token_totals["input_tokens"] += int(record["input_tokens"])
        self.token_totals["output_tokens"] += int(record["output_tokens"])
        self.token_totals["total_tokens"] += int(record["total_tokens"])
        self.token_totals["cached_input_tokens"] += int(record["cached_input_tokens"])
        self.token_totals["reasoning_tokens"] += int(record["reasoning_tokens"])

        for node in nodes:
            ctx = node.get("study_context") or {}
            if ctx.get("countries"):
                self.node_context_country += 1
            if ctx.get("start_year") or ctx.get("end_year"):
                self.node_context_year += 1
            if ctx.get("unit_of_analysis"):
                self.node_context_unit += 1

        for edge in edges:
            for field in ENUM_EDGE_FIELDS:
                self.edge_field_counters[field][str(edge.get(field, "MISSING"))] += 1
            self.uses_data[str(edge.get("uses_data", "MISSING"))] += 1
            if str(edge.get("condition_or_scope_text", "NA")) != "NA":
                self.edge_scope_non_na += 1
            if str(edge.get("evidence_text", "NA")) == "NA":
                self.edge_evidence_text_na += 1
            if str(edge.get("effect_size", "NA")) != "NA":
                self.edge_effect_size_non_na += 1

    def as_dict(self) -> dict[str, Any]:
        sorted_nodes = sorted(self.node_counts)
        sorted_edges = sorted(self.edge_counts)

        def counter_pct(counter: Counter) -> dict[str, float]:
            total = sum(counter.values())
            if total == 0:
                return {}
            return {k: round(v / total, 4) for k, v in counter.most_common()}

        return {
            "records": self.record_count,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "mean_nodes_per_paper": round(statistics.mean(self.node_counts), 3) if self.node_counts else 0.0,
            "median_nodes_per_paper": round(statistics.median(self.node_counts), 3) if self.node_counts else 0.0,
            "p90_nodes_per_paper": round(percentile(sorted_nodes, 0.9), 3) if sorted_nodes else 0.0,
            "mean_edges_per_paper": round(statistics.mean(self.edge_counts), 3) if self.edge_counts else 0.0,
            "median_edges_per_paper": round(statistics.median(self.edge_counts), 3) if self.edge_counts else 0.0,
            "p90_edges_per_paper": round(percentile(sorted_edges, 0.9), 3) if sorted_edges else 0.0,
            "papers_with_zero_nodes": self.zero_node,
            "papers_with_zero_edges": self.zero_edge,
            "papers_with_zero_edges_share": round(self.zero_edge / self.record_count, 4) if self.record_count else 0.0,
            "node_context_country_share": round(self.node_context_country / self.total_nodes, 4) if self.total_nodes else 0.0,
            "node_context_year_share": round(self.node_context_year / self.total_nodes, 4) if self.total_nodes else 0.0,
            "node_context_unit_share": round(self.node_context_unit / self.total_nodes, 4) if self.total_nodes else 0.0,
            "edge_scope_text_non_na_share": round(self.edge_scope_non_na / self.total_edges, 4) if self.total_edges else 0.0,
            "edge_evidence_text_na_share": round(self.edge_evidence_text_na / self.total_edges, 4) if self.total_edges else 0.0,
            "edge_effect_size_present_share": round(self.edge_effect_size_non_na / self.total_edges, 4) if self.total_edges else 0.0,
            "bucket_counts": dict(self.bucket_counts),
            "year_counts": {str(k): self.year_counts[k] for k in sorted(self.year_counts)},
            "top_sources_by_papers": [{"source_display_name": k, "papers": v} for k, v in self.source_counts.most_common(25)],
            "output_origin_counts": dict(self.output_origin_counts),
            "uses_data_distribution": counter_pct(self.uses_data),
            "edge_enum_distributions": {
                field: counter_pct(counter) for field, counter in self.edge_field_counters.items()
            },
            "token_totals": {
                "input_tokens": self.token_totals["input_tokens"],
                "output_tokens": self.token_totals["output_tokens"],
                "total_tokens": self.token_totals["total_tokens"],
                "cached_input_tokens": self.token_totals["cached_input_tokens"],
                "uncached_input_tokens": self.token_totals["input_tokens"] - self.token_totals["cached_input_tokens"],
                "reasoning_tokens": self.token_totals["reasoning_tokens"],
            },
        }


def load_sample_metadata(sample_jsonl: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(sample_jsonl):
        custom_id = f"{short_work_id(str(row['openalex_work_id']))}__gpt5mini_low"
        enriched = dict(row)
        enriched["short_work_id"] = short_work_id(str(row["openalex_work_id"]))
        enriched["custom_id"] = custom_id
        out[custom_id] = enriched
    return out


def load_preexisting_targets(completed_jsonl: Path) -> dict[Path, set[str]]:
    targets: dict[Path, set[str]] = defaultdict(set)
    if not completed_jsonl.exists():
        return targets
    for row in iter_jsonl(completed_jsonl):
        path = Path(str(row["batch_output_path"]))
        targets[path].add(str(row["custom_id"]))
    return targets


def iter_output_records(
    sample_lookup: dict[str, dict[str, Any]],
    fwci_batch_outputs_dir: Path,
    preexisting_targets: dict[Path, set[str]],
    retry_run_dirs: list[Path],
    invalid_records: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    seen: set[str] = set()

    def build_record(custom_id: str, body: dict[str, Any], batch_output_path: Path, origin: str) -> dict[str, Any]:
        output = extract_response_output(body)
        sample_meta = sample_lookup[custom_id]
        usage = body.get("usage") or {}
        return {
            **sample_meta,
            "batch_output_path": str(batch_output_path),
            "output_origin": origin,
            "response_id": body.get("id"),
            "model": body.get("model"),
            "created_at": body.get("created_at"),
            "completed_at": body.get("completed_at"),
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
            "cached_input_tokens": int(((usage.get("input_tokens_details") or {}).get("cached_tokens")) or 0),
            "reasoning_tokens": int(((usage.get("output_tokens_details") or {}).get("reasoning_tokens")) or 0),
            "output": output,
        }

    for path in sorted(fwci_batch_outputs_dir.glob("batch_*.output.jsonl")):
        for obj in iter_jsonl(path):
            if int(obj.get("response", {}).get("status_code", 0)) != 200:
                continue
            custom_id = str(obj.get("custom_id") or "")
            if custom_id not in sample_lookup or custom_id in seen:
                continue
            try:
                record = build_record(custom_id, obj["response"]["body"], path, "fwci_source_cut")
            except Exception as exc:
                invalid_records.append(
                    {
                        "custom_id": custom_id,
                        "batch_output_path": str(path),
                        "output_origin": "fwci_source_cut",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                continue
            seen.add(custom_id)
            yield record

    for path, wanted_ids in sorted(preexisting_targets.items(), key=lambda item: str(item[0])):
        if not path.exists():
            continue
        remaining = set(wanted_ids)
        for obj in iter_jsonl(path):
            if int(obj.get("response", {}).get("status_code", 0)) != 200:
                continue
            custom_id = str(obj.get("custom_id") or "")
            if custom_id not in remaining or custom_id in seen:
                continue
            try:
                record = build_record(custom_id, obj["response"]["body"], path, "preexisting_broad_batch")
            except Exception as exc:
                invalid_records.append(
                    {
                        "custom_id": custom_id,
                        "batch_output_path": str(path),
                        "output_origin": "preexisting_broad_batch",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                remaining.remove(custom_id)
                continue
            seen.add(custom_id)
            remaining.remove(custom_id)
            yield record
            if not remaining:
                break

    for run_dir in retry_run_dirs:
        parsed_path = run_dir / "parsed_results.jsonl"
        responses_dir = run_dir / "responses"
        if not parsed_path.exists() or not responses_dir.exists():
            continue
        for obj in iter_jsonl(parsed_path):
            custom_id = str(obj.get("custom_id") or "")
            if custom_id not in sample_lookup or custom_id in seen:
                continue
            response_path = responses_dir / f"{custom_id}.json"
            if not response_path.exists():
                invalid_records.append(
                    {
                        "custom_id": custom_id,
                        "batch_output_path": str(response_path),
                        "output_origin": "retry_live",
                        "error_type": "MissingResponseFile",
                        "error_message": "Retry parsed result exists but raw response file is missing.",
                    }
                )
                continue
            try:
                body = json.loads(response_path.read_text(encoding="utf-8"))
                record = build_record(custom_id, body, response_path, "retry_live")
            except Exception as exc:
                invalid_records.append(
                    {
                        "custom_id": custom_id,
                        "batch_output_path": str(response_path),
                        "output_origin": "retry_live",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                continue
            seen.add(custom_id)
            yield record


def insert_record(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    output = record["output"]
    nodes = output.get("nodes", [])
    edges = output.get("edges", [])
    conn.execute(
        """
        INSERT INTO works (
            custom_id, short_work_id, openalex_work_id, title, abstract, publication_year, bucket,
            source_id, source_display_name, output_origin, batch_output_path, response_id, model,
            created_at, completed_at, input_tokens, output_tokens, total_tokens, cached_input_tokens,
            reasoning_tokens, node_count, edge_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["custom_id"],
            record["short_work_id"],
            record["openalex_work_id"],
            record["title"],
            record["abstract"],
            int(record["publication_year"]),
            record["bucket"],
            record["source_id"],
            record["source_display_name"],
            record["output_origin"],
            record["batch_output_path"],
            record["response_id"],
            record["model"],
            record["created_at"],
            record["completed_at"],
            int(record["input_tokens"]),
            int(record["output_tokens"]),
            int(record["total_tokens"]),
            int(record["cached_input_tokens"]),
            int(record["reasoning_tokens"]),
            len(nodes),
            len(edges),
        ),
    )

    seen_node_ids: set[str] = set()
    for node in nodes:
        node_id = str(node["node_id"])
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        ctx = node.get("study_context") or {}
        conn.execute(
            """
            INSERT INTO nodes (
                custom_id, node_id, label, surface_forms_json, unit_of_analysis_json, start_year_json,
                end_year_json, countries_json, context_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["custom_id"],
                node_id,
                node["label"],
                json.dumps(node.get("surface_forms", []), ensure_ascii=False),
                json.dumps(ctx.get("unit_of_analysis", []), ensure_ascii=False),
                json.dumps(ctx.get("start_year", []), ensure_ascii=False),
                json.dumps(ctx.get("end_year", []), ensure_ascii=False),
                json.dumps(ctx.get("countries", []), ensure_ascii=False),
                str(ctx.get("context_note", "NA")),
            ),
        )

    seen_edge_ids: set[str] = set()
    for edge in edges:
        edge_id = str(edge["edge_id"])
        if edge_id in seen_edge_ids:
            continue
        seen_edge_ids.add(edge_id)
        conn.execute(
            """
            INSERT INTO edges (
                custom_id, edge_id, source_node_id, target_node_id, directionality, relationship_type,
                causal_presentation, edge_role, claim_status, explicitness, condition_or_scope_text,
                claim_text, evidence_text, sign, effect_size, statistical_significance, evidence_method,
                evidence_method_other_description, nature_of_evidence, uses_data,
                sources_of_exogenous_variation, tentativeness
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["custom_id"],
                edge_id,
                edge["source_node_id"],
                edge["target_node_id"],
                edge["directionality"],
                edge["relationship_type"],
                edge["causal_presentation"],
                edge["edge_role"],
                edge["claim_status"],
                edge["explicitness"],
                edge.get("condition_or_scope_text", "NA"),
                edge.get("claim_text", ""),
                edge.get("evidence_text", "NA"),
                edge.get("sign", "NA"),
                edge.get("effect_size", "NA"),
                edge.get("statistical_significance", "NA"),
                edge.get("evidence_method", "do_not_know"),
                edge.get("evidence_method_other_description", "NA"),
                edge.get("nature_of_evidence", "other"),
                1 if bool(edge.get("uses_data")) else 0,
                edge.get("sources_of_exogenous_variation", "NA"),
                edge.get("tentativeness", "unclear"),
            ),
        )


def build_summary_markdown(summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = []
    lines.append("# FWCI Source-Cut Extraction Corpus Summary")
    lines.append("")
    lines.append(f"- Generated at: `{manifest['generated_at_utc']}`")
    lines.append(f"- Records: `{summary['records']}`")
    lines.append(f"- Total nodes: `{summary['total_nodes']}`")
    lines.append(f"- Total edges: `{summary['total_edges']}`")
    lines.append(f"- Mean nodes/paper: `{summary['mean_nodes_per_paper']}`")
    lines.append(f"- Mean edges/paper: `{summary['mean_edges_per_paper']}`")
    lines.append(f"- Zero-edge papers: `{summary['papers_with_zero_edges']}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- Expected selected papers: `{manifest['expected_custom_ids']}`")
    lines.append(f"- Materialized papers: `{manifest['materialized_records']}`")
    lines.append(f"- Missing papers: `{manifest['missing_expected_count']}`")
    lines.append("")
    lines.append("## Token totals")
    token_totals = summary["token_totals"]
    lines.append(f"- Input: `{token_totals['input_tokens']}`")
    lines.append(f"- Cached input: `{token_totals['cached_input_tokens']}`")
    lines.append(f"- Uncached input: `{token_totals['uncached_input_tokens']}`")
    lines.append(f"- Output: `{token_totals['output_tokens']}`")
    lines.append(f"- Total: `{token_totals['total_tokens']}`")
    lines.append(f"- Reasoning: `{token_totals['reasoning_tokens']}`")
    lines.append("")
    lines.append("## Bucket counts")
    for bucket, count in sorted(summary["bucket_counts"].items()):
        lines.append(f"- `{bucket}`: `{count}`")
    lines.append("")
    lines.append("## Top sources by papers")
    for row in summary["top_sources_by_papers"][:15]:
        lines.append(f"- `{row['source_display_name']}`: `{row['papers']}`")
    lines.append("")
    lines.append("## Selected enum distributions")
    for field in ("directionality", "relationship_type", "causal_presentation", "edge_role", "evidence_method"):
        lines.append(f"### {field}")
        for key, value in summary["edge_enum_distributions"][field].items():
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    merged_dir = output_root / "merged"
    analysis_dir = output_root / "analysis"
    sample_jsonl = output_root / "sample" / "fwci_core150_adj150_all.jsonl"
    completed_jsonl = output_root / "completed" / "completed_successes.jsonl"
    fwci_batch_outputs_dir = output_root / "batch_outputs"
    retry_run_dirs = [Path(path) for path in args.retry_run_dir]

    out_sqlite = Path(args.out_sqlite) if args.out_sqlite else merged_dir / "fwci_core150_adj150_extractions.sqlite"
    out_jsonl_gz = Path(args.out_jsonl_gz) if args.out_jsonl_gz else merged_dir / "fwci_core150_adj150_extractions.jsonl.gz"
    out_summary_json = Path(args.out_summary_json) if args.out_summary_json else analysis_dir / "fwci_core150_adj150_corpus_summary.json"
    out_summary_md = Path(args.out_summary_md) if args.out_summary_md else analysis_dir / "fwci_core150_adj150_corpus_summary.md"
    out_manifest = Path(args.out_manifest) if args.out_manifest else merged_dir / "fwci_core150_adj150_extractions_manifest.json"
    out_retry_jsonl = merged_dir / "fwci_core150_adj150_invalid_response_retries.jsonl"

    sample_lookup = load_sample_metadata(sample_jsonl)
    preexisting_targets = load_preexisting_targets(completed_jsonl)
    conn = init_db(out_sqlite)
    summary = Summary()
    seen_custom_ids: set[str] = set()
    invalid_records: list[dict[str, Any]] = []

    out_jsonl_gz.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_jsonl_gz, "wt", encoding="utf-8") as handle:
        for record in iter_output_records(sample_lookup, fwci_batch_outputs_dir, preexisting_targets, retry_run_dirs, invalid_records):
            custom_id = record["custom_id"]
            if custom_id in seen_custom_ids:
                continue
            seen_custom_ids.add(custom_id)
            insert_record(conn, record)
            summary.update(record)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    conn.commit()
    conn.close()

    expected_ids = set(sample_lookup)
    missing_ids = sorted(expected_ids - seen_custom_ids)
    retry_rows = [sample_lookup[custom_id] for custom_id in missing_ids if custom_id in sample_lookup]
    out_retry_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_retry_jsonl.open("w", encoding="utf-8") as handle:
        for row in retry_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_dict = summary.as_dict()
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "output_root": str(output_root),
            "sample_jsonl": str(sample_jsonl),
            "completed_successes_jsonl": str(completed_jsonl),
            "fwci_batch_outputs_dir": str(fwci_batch_outputs_dir),
            "retry_run_dirs": [str(path) for path in retry_run_dirs],
            "out_sqlite": str(out_sqlite),
            "out_jsonl_gz": str(out_jsonl_gz),
            "out_summary_json": str(out_summary_json),
            "out_summary_md": str(out_summary_md),
            "out_retry_jsonl": str(out_retry_jsonl),
        },
        "expected_custom_ids": len(expected_ids),
        "materialized_records": len(seen_custom_ids),
        "missing_expected_count": len(missing_ids),
        "missing_expected_sample": missing_ids[:50],
        "invalid_records": invalid_records,
        "preexisting_broad_output_files": len(preexisting_targets),
        "fwci_source_cut_output_files": len(list(fwci_batch_outputs_dir.glob('batch_*.output.jsonl'))),
        "summary": summary_dict,
    }

    write_json(out_summary_json, summary_dict)
    out_summary_md.parent.mkdir(parents=True, exist_ok=True)
    out_summary_md.write_text(build_summary_markdown(summary_dict, manifest), encoding="utf-8")
    write_json(out_manifest, manifest)
    print(json.dumps({
        "materialized_records": manifest["materialized_records"],
        "missing_expected_count": manifest["missing_expected_count"],
        "out_sqlite": str(out_sqlite),
        "out_summary_json": str(out_summary_json),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
