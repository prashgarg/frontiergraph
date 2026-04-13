from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build edge-alignment judge inputs from benchmark graphs, predicted graphs, and node-alignment results.")
    parser.add_argument("--benchmark-source", required=True)
    parser.add_argument("--benchmark-jsonl", required=True)
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--node-alignment-jsonl", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--prompt-family", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        return value
    return []


def parse_benchmark_id(openalex_work_id: str) -> str:
    return str(openalex_work_id).rstrip("/").split("/")[-1]


def edge_to_str(source: str, target: str) -> str:
    return f"{source} -> {target}"


def load_subset(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["benchmark_id"]): row for row in iter_jsonl(path)}


def load_gold(path: Path) -> dict[str, dict[str, Any]]:
    df = pd.read_parquet(path)
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        gold_edges = []
        for edge in safe_list(row["edges"]):
            if isinstance(edge, dict):
                source = str(edge.get("source", "")).strip()
                target = str(edge.get("target", "")).strip()
                if source and target:
                    gold_edges.append({"source": source, "target": target, "edge_str": edge_to_str(source, target)})
        out[str(row["id"])] = {
            "title": str(row["title"]),
            "abstract": str(row.get("abstract", "")),
            "gold_edges": gold_edges,
        }
    return out


def load_predicted(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row in iter_jsonl(path):
        benchmark_id = parse_benchmark_id(str(row["openalex_work_id"]))
        node_labels = {str(node["node_id"]): str(node["label"]) for node in row["output"].get("nodes", [])}
        pred_edges = []
        for edge in row["output"].get("edges", []):
            source = node_labels.get(str(edge.get("source_node_id", "")), "").strip()
            target = node_labels.get(str(edge.get("target_node_id", "")), "").strip()
            if source and target:
                pred_edges.append(
                    {
                        "source": source,
                        "target": target,
                        "edge_str": edge_to_str(source, target),
                        "claim_text": str(edge.get("claim_text", "")).strip(),
                        "directionality": str(edge.get("directionality", "")).strip(),
                    }
                )
        out[benchmark_id] = {
            "pred_edges": pred_edges,
            "condition_id": str(row.get("condition_id", "")),
            "model": str(row.get("model", "")),
            "reasoning_effort": str(row.get("reasoning_effort", "")),
        }
    return out


def load_node_alignments(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row in iter_jsonl(path):
        benchmark_id = str(row["benchmark_id"])
        output = row["output"]
        out[benchmark_id] = output
    return out


def top_gold_candidates_for_pred_edge(
    pred_edge: dict[str, Any],
    gold_edges: list[dict[str, Any]],
    pred_to_gold_best: dict[str, str],
    top_k: int,
) -> list[dict[str, Any]]:
    src_best = pred_to_gold_best.get(pred_edge["source"], "NA")
    tgt_best = pred_to_gold_best.get(pred_edge["target"], "NA")
    scored = []
    for gold in gold_edges:
        score = 0
        if gold["source"] == src_best:
            score += 2
        if gold["target"] == tgt_best:
            score += 2
        if gold["source"] == tgt_best and gold["target"] == src_best:
            score += 1
        if gold["source"] in {src_best, tgt_best} or gold["target"] in {src_best, tgt_best}:
            score += 1
        scored.append({"candidate_edge": gold["edge_str"], "heuristic_score": score})
    scored.sort(key=lambda row: (row["heuristic_score"], row["candidate_edge"]), reverse=True)
    return scored[:top_k]


def top_pred_candidates_for_gold_edge(
    gold_edge: dict[str, Any],
    pred_edges: list[dict[str, Any]],
    gold_to_pred_best: dict[str, str],
    top_k: int,
) -> list[dict[str, Any]]:
    src_best = gold_to_pred_best.get(gold_edge["source"], "NA")
    tgt_best = gold_to_pred_best.get(gold_edge["target"], "NA")
    scored = []
    for pred in pred_edges:
        score = 0
        if pred["source"] == src_best:
            score += 2
        if pred["target"] == tgt_best:
            score += 2
        if pred["source"] == tgt_best and pred["target"] == src_best:
            score += 1
        if pred["source"] in {src_best, tgt_best} or pred["target"] in {src_best, tgt_best}:
            score += 1
        scored.append({"candidate_edge": pred["edge_str"], "heuristic_score": score, "claim_text": pred["claim_text"]})
    scored.sort(key=lambda row: (row["heuristic_score"], row["candidate_edge"]), reverse=True)
    return scored[:top_k]


def build_node_alignment_summary(output: dict[str, Any]) -> dict[str, Any]:
    gold_summary = []
    for item in output["gold_node_alignments"]:
        gold_summary.append(
            {
                "gold_node": item["gold_node"],
                "best_predicted_node": item["best_predicted_node"],
                "overlap_class": item["overlap_class"],
                "gold_recoverable_from_abstract": item["gold_recoverable_from_abstract"],
            }
        )
    pred_summary = []
    for item in output["predicted_node_alignments"]:
        pred_summary.append(
            {
                "predicted_node": item["predicted_node"],
                "best_gold_node": item["best_gold_node"],
                "overlap_class": item["overlap_class"],
            }
        )
    return {"gold_to_pred": gold_summary, "pred_to_gold": pred_summary}


def main() -> None:
    args = parse_args()
    subset = load_subset(Path(args.benchmark_jsonl))
    gold = load_gold(Path(args.benchmark_source))
    pred = load_predicted(Path(args.results_jsonl))
    node_align = load_node_alignments(Path(args.node_alignment_jsonl))

    out_rows = []
    for benchmark_id in sorted(subset, key=int):
        gold_row = gold[benchmark_id]
        pred_row = pred[benchmark_id]
        pred_edges = pred_row["pred_edges"]
        node_output = node_align[benchmark_id]
        gold_edges = gold_row["gold_edges"]

        gold_to_pred_best = {item["gold_node"]: item["best_predicted_node"] for item in node_output["gold_node_alignments"]}
        pred_to_gold_best = {item["predicted_node"]: item["best_gold_node"] for item in node_output["predicted_node_alignments"]}

        gold_edge_candidates = []
        for edge in gold_edges:
            gold_edge_candidates.append(
                {
                    "gold_edge": edge["edge_str"],
                    "candidates": top_pred_candidates_for_gold_edge(edge, pred_edges, gold_to_pred_best, args.top_k),
                }
            )

        pred_edge_candidates = []
        for edge in pred_edges:
            pred_edge_candidates.append(
                {
                    "pred_edge": edge["edge_str"],
                    "candidates": top_gold_candidates_for_pred_edge(edge, gold_edges, pred_to_gold_best, args.top_k),
                }
            )

        out_rows.append(
            {
                "benchmark_dataset": "recite",
                "benchmark_id": benchmark_id,
                "prompt_family": args.prompt_family,
                "condition_id": pred_row["condition_id"],
                "model": pred_row["model"],
                "reasoning_effort": pred_row["reasoning_effort"],
                "title": gold_row["title"],
                "abstract": gold_row["abstract"],
                "gold_edges": [edge["edge_str"] for edge in gold_edges],
                "pred_edges": [edge["edge_str"] for edge in pred_edges],
                "node_alignment_summary": build_node_alignment_summary(node_output),
                "gold_edge_candidates": gold_edge_candidates,
                "pred_edge_candidates": pred_edge_candidates,
            }
        )

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
