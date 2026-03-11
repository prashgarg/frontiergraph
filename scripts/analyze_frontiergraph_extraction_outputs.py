from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize FrontierGraph extraction outputs from direct runs and batch outputs.")
    parser.add_argument("--direct-run-dir", required=True)
    parser.add_argument("--batch-output", action="append", default=[])
    parser.add_argument("--out-json", default=None)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


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


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    node_counts: list[int] = []
    edge_counts: list[int] = []
    zero_edge = 0
    zero_node = 0
    field_counters = {field: Counter() for field in ENUM_EDGE_FIELDS}
    uses_data = Counter()
    condition_scope_present = 0
    evidence_text_na = 0
    effect_size_present = 0
    node_context_countries = 0
    node_context_years = 0
    node_context_units = 0
    total_nodes = 0
    total_edges = 0
    per_condition_counts = Counter()
    per_condition_edge_counts: dict[str, list[int]] = defaultdict(list)
    per_condition_node_counts: dict[str, list[int]] = defaultdict(list)

    for row in records:
        output = row["output"]
        nodes = output.get("nodes", [])
        edges = output.get("edges", [])
        node_n = len(nodes)
        edge_n = len(edges)
        node_counts.append(node_n)
        edge_counts.append(edge_n)
        total_nodes += node_n
        total_edges += edge_n
        if node_n == 0:
            zero_node += 1
        if edge_n == 0:
            zero_edge += 1
        condition = row.get("condition_id", "unknown")
        per_condition_counts[condition] += 1
        per_condition_edge_counts[condition].append(edge_n)
        per_condition_node_counts[condition].append(node_n)

        for node in nodes:
            ctx = node.get("study_context", {}) or {}
            if ctx.get("countries"):
                node_context_countries += 1
            if ctx.get("start_year") or ctx.get("end_year"):
                node_context_years += 1
            if ctx.get("unit_of_analysis"):
                node_context_units += 1

        for edge in edges:
            for field in ENUM_EDGE_FIELDS:
                field_counters[field][str(edge.get(field, "MISSING"))] += 1
            uses_data[str(edge.get("uses_data", "MISSING"))] += 1
            if str(edge.get("condition_or_scope_text", "NA")) != "NA":
                condition_scope_present += 1
            if str(edge.get("evidence_text", "NA")) == "NA":
                evidence_text_na += 1
            if str(edge.get("effect_size", "NA")) != "NA":
                effect_size_present += 1

    def pct(counter: Counter) -> dict[str, float]:
        total = sum(counter.values())
        if total == 0:
            return {}
        return {k: round(v / total, 4) for k, v in counter.most_common()}

    def mean(values: list[int]) -> float:
        return round(statistics.mean(values), 3) if values else 0.0

    def median(values: list[int]) -> float:
        return round(statistics.median(values), 3) if values else 0.0

    summary = {
        "records": len(records),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "mean_nodes_per_paper": mean(node_counts),
        "median_nodes_per_paper": median(node_counts),
        "mean_edges_per_paper": mean(edge_counts),
        "median_edges_per_paper": median(edge_counts),
        "papers_with_zero_nodes": zero_node,
        "papers_with_zero_edges": zero_edge,
        "papers_with_zero_edges_share": round(zero_edge / len(records), 4) if records else 0.0,
        "node_context_country_share": round(node_context_countries / total_nodes, 4) if total_nodes else 0.0,
        "node_context_year_share": round(node_context_years / total_nodes, 4) if total_nodes else 0.0,
        "node_context_unit_share": round(node_context_units / total_nodes, 4) if total_nodes else 0.0,
        "edge_scope_text_non_na_share": round(condition_scope_present / total_edges, 4) if total_edges else 0.0,
        "edge_evidence_text_na_share": round(evidence_text_na / total_edges, 4) if total_edges else 0.0,
        "edge_effect_size_present_share": round(effect_size_present / total_edges, 4) if total_edges else 0.0,
        "uses_data_distribution": pct(uses_data),
        "edge_enum_distributions": {field: pct(counter) for field, counter in field_counters.items()},
        "per_condition": {
            cond: {
                "records": per_condition_counts[cond],
                "mean_nodes_per_paper": mean(per_condition_node_counts[cond]),
                "mean_edges_per_paper": mean(per_condition_edge_counts[cond]),
                "median_nodes_per_paper": median(per_condition_node_counts[cond]),
                "median_edges_per_paper": median(per_condition_edge_counts[cond]),
            }
            for cond in sorted(per_condition_counts)
        },
    }
    return summary


def load_direct_records(run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed_path = run_dir / "parsed_results.jsonl"
    errors_path = run_dir / "errors.jsonl"
    manifest_path = run_dir / "run_manifest.json"
    records = list(iter_jsonl(parsed_path))
    errors = list(iter_jsonl(errors_path)) if errors_path.exists() else []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    return records, {
        "manifest": manifest,
        "errors": errors,
        "success_count": len(records),
        "error_count": len(errors),
    }


def infer_condition_id_from_name(path: Path) -> str:
    name = path.name
    if ".output.jsonl" in name:
        poll_name = name.replace(".output.jsonl", ".poll.json")
        poll_path = path.parent.parent / "batch_inputs" / path.parent.name / poll_name
        # fallback if not found
    for candidate in ("gpt5mini_low", "gpt5mini_medium", "gpt5nano_low", "gpt5nano_medium"):
        if candidate in name:
            return candidate
    return path.stem


def load_batch_records(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    condition_id = infer_condition_id_from_name(path)
    for row in iter_jsonl(path):
        response = row.get("response", {})
        if int(response.get("status_code", 0)) != 200:
            failures.append(row)
            continue
        body = response.get("body", {})
        try:
            output = extract_response_output(body)
        except Exception:
            failures.append(row)
            continue
        records.append(
            {
                "custom_id": row.get("custom_id"),
                "condition_id": condition_id,
                "response_id": body.get("id"),
                "output": output,
            }
        )
    return records, {
        "path": str(path),
        "condition_id": condition_id,
        "success_count": len(records),
        "failure_count": len(failures),
    }


def main() -> None:
    args = parse_args()
    direct_records, direct_meta = load_direct_records(Path(args.direct_run_dir))
    batch_sections: dict[str, Any] = {}
    batch_records_all: list[dict[str, Any]] = []
    for batch_path_str in args.batch_output:
        batch_path = Path(batch_path_str)
        records, meta = load_batch_records(batch_path)
        batch_sections[meta["condition_id"]] = {
            "meta": meta,
            "summary": summarize_records(records),
        }
        batch_records_all.extend(records)

    report = {
        "direct_run": {
            "meta": direct_meta,
            "summary": summarize_records(direct_records),
        },
        "batch_outputs": batch_sections,
    }

    out_json = Path(args.out_json) if args.out_json else None
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
