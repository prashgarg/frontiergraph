from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_INPUT_JSONL = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark.jsonl"
DEFAULT_OUTPUT_JSONL = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_pilot5.jsonl"
DEFAULT_OUTPUT_MANIFEST = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_pilot5_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a small diverse DAGverse pilot sample for FrontierGraph extraction.")
    parser.add_argument("--input-jsonl", default=DEFAULT_INPUT_JSONL)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-manifest", default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--sample-size", type=int, default=5)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def semantic_edge_count(row: dict) -> int:
    value = row["gold_semantic_dag"]
    payload = json.loads(value) if isinstance(value, str) else value
    return len(payload.get("edges", []))


def semantic_node_count(row: dict) -> int:
    value = row["gold_semantic_dag"]
    payload = json.loads(value) if isinstance(value, str) else value
    return len(payload.get("nodes", []))


def choose_evenly_spaced(rows: list[dict], sample_size: int) -> list[dict]:
    if sample_size >= len(rows):
        return rows
    sorted_rows = sorted(rows, key=lambda r: (semantic_edge_count(r), semantic_node_count(r), r.get("benchmark_id", "")))
    chosen_indices: list[int] = []
    for i in range(sample_size):
        idx = round(i * (len(sorted_rows) - 1) / max(1, sample_size - 1))
        while idx in chosen_indices and idx + 1 < len(sorted_rows):
            idx += 1
        while idx in chosen_indices and idx - 1 >= 0:
            idx -= 1
        chosen_indices.append(idx)
    return [sorted_rows[i] for i in sorted(chosen_indices)]


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.input_jsonl)))
    chosen = choose_evenly_spaced(rows, args.sample_size)
    out_jsonl = Path(args.output_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for row in chosen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "input_jsonl": str(Path(args.input_jsonl)),
        "output_jsonl": str(out_jsonl),
        "sample_size": len(chosen),
        "selection_rule": "Evenly spaced over semantic DAG edge-count distribution.",
        "benchmark_ids": [row["benchmark_id"] for row in chosen],
        "semantic_nodes": [semantic_node_count(row) for row in chosen],
        "semantic_edges": [semantic_edge_count(row) for row in chosen],
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
