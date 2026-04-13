from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build generic graph-overlap judge inputs from benchmark data and extraction outputs.")
    parser.add_argument("--dataset", choices=["recite", "dagverse"], required=True)
    parser.add_argument("--benchmark-source", required=True)
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--prompt-family", required=True)
    parser.add_argument("--benchmark-jsonl", default=None)
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


def pred_graph_from_output(output: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    node_map = {
        str(node["node_id"]): str(node["label"])
        for node in output.get("nodes", [])
        if node.get("node_id") and node.get("label")
    }
    pred_nodes = list(node_map.values())
    pred_edges: list[dict[str, str]] = []
    for edge in output.get("edges", []):
        src = node_map.get(str(edge.get("source_node_id", "")))
        tgt = node_map.get(str(edge.get("target_node_id", "")))
        if not src or not tgt:
            continue
        pred_edges.append(
            {
                "source": src,
                "target": tgt,
                "directionality": str(edge.get("directionality", "directed")),
            }
        )
    return pred_nodes, pred_edges


def load_recite_gold(recite_parquet: Path) -> dict[str, dict[str, Any]]:
    df = pd.read_parquet(recite_parquet)
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        gold_nodes = [str(item) for item in safe_list(row["nodes"]) if str(item).strip()]
        gold_edges = []
        for edge in safe_list(row["edges"]):
            source = str(edge.get("source", "")).strip()
            target = str(edge.get("target", "")).strip()
            if source and target:
                gold_edges.append({"source": source, "target": target})
        out[str(row["id"])] = {
            "benchmark_id": str(row["id"]),
            "title": str(row["title"]),
            "abstract": str(row.get("abstract", "")),
            "gold_nodes": gold_nodes,
            "gold_edges": gold_edges,
        }
    return out


def load_dagverse_gold(benchmark_jsonl: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(benchmark_jsonl):
        payload = row["gold_semantic_dag"]
        payload = json.loads(payload) if isinstance(payload, str) else payload
        gold_nodes = []
        for node in payload.get("nodes", []):
            aliases = [str(alias) for alias in node.get("aliases", []) if str(alias).strip()]
            label = aliases[0] if aliases else str(node["id"])
            gold_nodes.append(label)
        gold_edges = []
        alias_by_id = {}
        for node in payload.get("nodes", []):
            aliases = [str(alias) for alias in node.get("aliases", []) if str(alias).strip()]
            alias_by_id[str(node["id"])] = aliases[0] if aliases else str(node["id"])
        for edge in payload.get("edges", []):
            source = alias_by_id.get(str(edge.get("source", "")), str(edge.get("source", "")))
            target = alias_by_id.get(str(edge.get("target", "")), str(edge.get("target", "")))
            if source and target:
                gold_edges.append({"source": source, "target": target})
        out[str(row["benchmark_id"])] = {
            "benchmark_id": str(row["benchmark_id"]),
            "title": str(row["title"]),
            "abstract": str(row.get("abstract", "")),
            "gold_nodes": gold_nodes,
            "gold_edges": gold_edges,
        }
    return out


def main() -> None:
    args = parse_args()
    results = list(iter_jsonl(Path(args.results_jsonl)))
    if args.dataset == "recite":
        gold = load_recite_gold(Path(args.benchmark_source))
    else:
        benchmark_jsonl = Path(args.benchmark_jsonl or args.benchmark_source)
        gold = load_dagverse_gold(benchmark_jsonl)

    out_rows = []
    for row in results:
        benchmark_id = parse_benchmark_id(str(row["openalex_work_id"]))
        gold_row = gold[benchmark_id]
        pred_nodes, pred_edges = pred_graph_from_output(row["output"])
        out_rows.append(
            {
                "benchmark_dataset": args.dataset,
                "benchmark_id": benchmark_id,
                "prompt_family": args.prompt_family,
                "condition_id": row["condition_id"],
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "title": gold_row["title"],
                "abstract": gold_row["abstract"],
                "gold_nodes": gold_row["gold_nodes"],
                "gold_edges": gold_row["gold_edges"],
                "pred_nodes": pred_nodes,
                "pred_edges": pred_edges,
            }
        )

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
