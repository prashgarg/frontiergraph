from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_RESULTS_JSONL = "data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_medium/parsed_results.jsonl"
DEFAULT_RECITE_PARQUET = "next_steps/validation/data/reCITE/test.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare FrontierGraph pilot outputs against ReCITE gold graphs.")
    parser.add_argument("--results-jsonl", default=DEFAULT_RESULTS_JSONL)
    parser.add_argument("--recite-parquet", default=DEFAULT_RECITE_PARQUET)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def normalize_label(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def parse_benchmark_id(openalex_work_id: str) -> int:
    return int(str(openalex_work_id).rstrip("/").split("/")[-1])


def safe_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        return value
    return []


def node_overlap_metrics(gold_labels: set[str], pred_labels: set[str]) -> dict[str, Any]:
    intersection = gold_labels & pred_labels
    return {
        "gold_nodes": len(gold_labels),
        "pred_nodes": len(pred_labels),
        "matched_nodes": len(intersection),
        "node_precision": round(len(intersection) / len(pred_labels), 3) if pred_labels else None,
        "node_recall": round(len(intersection) / len(gold_labels), 3) if gold_labels else None,
        "node_jaccard": round(len(intersection) / len(gold_labels | pred_labels), 3) if (gold_labels or pred_labels) else None,
        "missing_gold_nodes": sorted(gold_labels - pred_labels),
        "extra_pred_nodes": sorted(pred_labels - gold_labels),
    }


def gold_edge_set(row: pd.Series) -> set[tuple[str, str]]:
    edges = safe_list(row["edges"])
    out: set[tuple[str, str]] = set()
    for edge in edges:
        source = normalize_label(str(edge.get("source", "")))
        target = normalize_label(str(edge.get("target", "")))
        if source and target:
            out.add((source, target))
    return out


def pred_edge_sets(output: dict[str, Any]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    nodes = output.get("nodes", [])
    edges = output.get("edges", [])
    id_to_label = {
        str(node.get("node_id")): normalize_label(str(node.get("label", "")))
        for node in nodes
        if node.get("node_id") and node.get("label")
    }
    directed: set[tuple[str, str]] = set()
    relaxed: set[tuple[str, str]] = set()
    for edge in edges:
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
    return directed, relaxed


def edge_metrics(gold_edges: set[tuple[str, str]], pred_directed: set[tuple[str, str]], pred_relaxed: set[tuple[str, str]]) -> dict[str, Any]:
    gold_relaxed = {tuple(sorted(edge)) for edge in gold_edges}
    directed_match = gold_edges & pred_directed
    relaxed_match = gold_relaxed & pred_relaxed
    return {
        "gold_edges": len(gold_edges),
        "pred_edges": len(pred_directed),
        "matched_edges_directed": len(directed_match),
        "matched_edges_relaxed": len(relaxed_match),
        "edge_recall_directed": round(len(directed_match) / len(gold_edges), 3) if gold_edges else None,
        "edge_recall_relaxed": round(len(relaxed_match) / len(gold_edges), 3) if gold_edges else None,
        "missing_gold_edges_directed": [list(edge) for edge in sorted(gold_edges - pred_directed)[:25]],
        "extra_pred_edges_directed": [list(edge) for edge in sorted(pred_directed - gold_edges)[:25]],
    }


def main() -> None:
    args = parse_args()
    results_path = Path(args.results_jsonl)
    out_dir = Path(args.output_dir) if args.output_dir else results_path.parent / "recite_review"
    out_dir.mkdir(parents=True, exist_ok=True)

    recite = pd.read_parquet(args.recite_parquet).set_index("id")
    review_rows: list[dict[str, Any]] = []

    for row in iter_jsonl(results_path):
        benchmark_id = parse_benchmark_id(row["openalex_work_id"])
        gold_row = recite.loc[benchmark_id]
        gold_labels = {normalize_label(str(label)) for label in safe_list(gold_row["nodes"]) if normalize_label(str(label))}
        pred_labels = {
            normalize_label(str(node.get("label", "")))
            for node in row["output"].get("nodes", [])
            if normalize_label(str(node.get("label", "")))
        }
        gold_edges = gold_edge_set(gold_row)
        pred_directed, pred_relaxed = pred_edge_sets(row["output"])
        node_metrics = node_overlap_metrics(gold_labels, pred_labels)
        edge_stats = edge_metrics(gold_edges, pred_directed, pred_relaxed)
        review_rows.append(
            {
                "benchmark_id": benchmark_id,
                "title": gold_row["title"],
                "condition_id": row["condition_id"],
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                **{k: v for k, v in node_metrics.items() if not isinstance(v, list)},
                **{k: v for k, v in edge_stats.items() if not isinstance(v, list)},
                "missing_gold_nodes": node_metrics["missing_gold_nodes"][:25],
                "extra_pred_nodes": node_metrics["extra_pred_nodes"][:25],
                "missing_gold_edges_directed": edge_stats["missing_gold_edges_directed"],
                "extra_pred_edges_directed": edge_stats["extra_pred_edges_directed"],
            }
        )

    review_jsonl = out_dir / "manual_review.jsonl"
    with review_jsonl.open("w", encoding="utf-8") as handle:
        for row in review_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary_df = pd.DataFrame(review_rows)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    aggregate = {
        "rows": len(review_rows),
        "conditions": sorted(summary_df["condition_id"].unique().tolist()),
        "mean_node_precision": round(float(summary_df["node_precision"].dropna().mean()), 3) if not summary_df["node_precision"].dropna().empty else None,
        "mean_node_recall": round(float(summary_df["node_recall"].dropna().mean()), 3) if not summary_df["node_recall"].dropna().empty else None,
        "mean_node_jaccard": round(float(summary_df["node_jaccard"].dropna().mean()), 3) if not summary_df["node_jaccard"].dropna().empty else None,
        "mean_edge_recall_directed": round(float(summary_df["edge_recall_directed"].dropna().mean()), 3) if not summary_df["edge_recall_directed"].dropna().empty else None,
        "mean_edge_recall_relaxed": round(float(summary_df["edge_recall_relaxed"].dropna().mean()), 3) if not summary_df["edge_recall_relaxed"].dropna().empty else None,
        "output_dir": str(out_dir),
    }
    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
