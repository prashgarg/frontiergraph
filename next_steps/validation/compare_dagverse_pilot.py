from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_JSONL = "data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1/parsed_results.jsonl"
DEFAULT_BENCHMARK_JSONL = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_pilot5.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare FrontierGraph pilot outputs against DAGverse semantic DAGs.")
    parser.add_argument("--results-jsonl", default=DEFAULT_RESULTS_JSONL)
    parser.add_argument("--benchmark-jsonl", default=DEFAULT_BENCHMARK_JSONL)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalize_label(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_benchmark_id(openalex_work_id: str) -> str:
    return str(openalex_work_id).rstrip("/").split("/")[-1]


def load_semantic_gold(row: dict[str, Any]) -> tuple[dict[str, set[str]], set[tuple[str, str]]]:
    payload = row["gold_semantic_dag"]
    payload = json.loads(payload) if isinstance(payload, str) else payload
    alias_map: dict[str, set[str]] = {}
    for node in payload.get("nodes", []):
        node_id = str(node["id"])
        alias_set = {normalize_label(node_id)}
        alias_set.update(normalize_label(str(alias)) for alias in node.get("aliases", []) if normalize_label(str(alias)))
        alias_map[node_id] = alias_set
    gold_edges = {
        (str(edge["source"]), str(edge["target"]))
        for edge in payload.get("edges", [])
        if edge.get("source") is not None and edge.get("target") is not None
    }
    return alias_map, gold_edges


def build_predicted_sets(output: dict[str, Any]) -> tuple[dict[str, str], set[tuple[str, str]], set[tuple[str, str]]]:
    id_to_label = {
        str(node["node_id"]): normalize_label(str(node["label"]))
        for node in output.get("nodes", [])
        if node.get("node_id") and node.get("label")
    }
    directed = set()
    relaxed = set()
    for edge in output.get("edges", []):
        src = id_to_label.get(str(edge.get("source_node_id", "")), "")
        tgt = id_to_label.get(str(edge.get("target_node_id", "")), "")
        if not src or not tgt:
            continue
        directionality = str(edge.get("directionality", "")).lower()
        if directionality == "undirected":
            relaxed.add(tuple(sorted((src, tgt))))
        else:
            directed.add((src, tgt))
            relaxed.add((src, tgt))
    return id_to_label, directed, relaxed


def main() -> None:
    args = parse_args()
    benchmark_rows = {row["benchmark_id"]: row for row in iter_jsonl(Path(args.benchmark_jsonl))}
    results = list(iter_jsonl(Path(args.results_jsonl)))
    out_dir = Path(args.output_dir) if args.output_dir else Path(args.results_jsonl).parent / "dagverse_review"
    out_dir.mkdir(parents=True, exist_ok=True)

    review_rows = []
    for row in results:
        benchmark_id = parse_benchmark_id(row["openalex_work_id"])
        gold_row = benchmark_rows[benchmark_id]
        alias_map, gold_edges = load_semantic_gold(gold_row)
        gold_node_ids = set(alias_map.keys())
        pred_label_map, pred_directed, pred_relaxed = build_predicted_sets(row["output"])

        pred_to_gold_ids: dict[str, set[str]] = {}
        matched_gold_ids: set[str] = set()
        for pred_label in pred_label_map.values():
            matched_ids = {node_id for node_id, aliases in alias_map.items() if pred_label in aliases}
            pred_to_gold_ids[pred_label] = matched_ids
            matched_gold_ids.update(matched_ids)

        pred_exact_nodes = {label for label, ids in pred_to_gold_ids.items() if ids}

        matched_edges_directed = 0
        matched_edges_relaxed = 0
        extra_pred_edges = []
        for src_label, tgt_label in sorted(pred_directed):
            src_ids = pred_to_gold_ids.get(src_label, set())
            tgt_ids = pred_to_gold_ids.get(tgt_label, set())
            if any((s, t) in gold_edges for s in src_ids for t in tgt_ids):
                matched_edges_directed += 1
            else:
                extra_pred_edges.append([src_label, tgt_label])

        gold_relaxed = {tuple(sorted(edge)) for edge in gold_edges}
        for src_label, tgt_label in sorted(pred_relaxed):
            src_ids = pred_to_gold_ids.get(src_label, set())
            tgt_ids = pred_to_gold_ids.get(tgt_label, set())
            pred_pairs = {tuple(sorted((s, t))) for s in src_ids for t in tgt_ids}
            if pred_pairs & gold_relaxed:
                matched_edges_relaxed += 1

        missing_gold_ids = sorted(gold_node_ids - matched_gold_ids)
        review_rows.append(
            {
                "benchmark_id": benchmark_id,
                "title": gold_row["title"],
                "condition_id": row["condition_id"],
                "gold_nodes": len(gold_node_ids),
                "pred_nodes": len(pred_label_map),
                "matched_gold_nodes_via_alias": len(matched_gold_ids),
                "node_recall_alias": round(len(matched_gold_ids) / len(gold_node_ids), 3) if gold_node_ids else None,
                "node_precision_alias": round(len(pred_exact_nodes) / len(pred_label_map), 3) if pred_label_map else None,
                "gold_edges": len(gold_edges),
                "pred_edges": len(pred_directed),
                "matched_edges_directed_alias": matched_edges_directed,
                "matched_edges_relaxed_alias": matched_edges_relaxed,
                "edge_recall_directed_alias": round(matched_edges_directed / len(gold_edges), 3) if gold_edges else None,
                "edge_recall_relaxed_alias": round(matched_edges_relaxed / len(gold_edges), 3) if gold_edges else None,
                "missing_gold_node_ids": missing_gold_ids[:25],
                "pred_nodes_without_alias_match": sorted([label for label, ids in pred_to_gold_ids.items() if not ids])[:25],
                "extra_pred_edges_directed": extra_pred_edges[:25],
            }
        )

    with (out_dir / "manual_review.jsonl").open("w", encoding="utf-8") as handle:
        for row in review_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    import pandas as pd

    df = pd.DataFrame(review_rows)
    df.to_csv(out_dir / "summary.csv", index=False)
    aggregate = {
        "rows": len(review_rows),
        "mean_node_precision_alias": round(float(df["node_precision_alias"].dropna().mean()), 3) if not df["node_precision_alias"].dropna().empty else None,
        "mean_node_recall_alias": round(float(df["node_recall_alias"].dropna().mean()), 3) if not df["node_recall_alias"].dropna().empty else None,
        "mean_edge_recall_directed_alias": round(float(df["edge_recall_directed_alias"].dropna().mean()), 3) if not df["edge_recall_directed_alias"].dropna().empty else None,
        "mean_edge_recall_relaxed_alias": round(float(df["edge_recall_relaxed_alias"].dropna().mean()), 3) if not df["edge_recall_relaxed_alias"].dropna().empty else None,
        "output_dir": str(out_dir),
    }
    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
