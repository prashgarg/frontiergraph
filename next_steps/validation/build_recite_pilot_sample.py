from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_INPUT_JSONL = "next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark.jsonl"
DEFAULT_OUTPUT_JSONL = "next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark_pilot10.jsonl"
DEFAULT_OUTPUT_MANIFEST = "next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark_pilot10_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a small diverse ReCITE pilot sample for FrontierGraph extraction.")
    parser.add_argument("--input-jsonl", default=DEFAULT_INPUT_JSONL)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-manifest", default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--sample-size", type=int, default=10)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def choose_evenly_spaced(rows: list[dict], sample_size: int) -> list[dict]:
    if sample_size >= len(rows):
        return rows
    sorted_rows = sorted(rows, key=lambda r: (r.get("gold_num_edges", 0), r.get("gold_num_nodes", 0), r.get("benchmark_id", 0)))
    chosen_indices: list[int] = []
    for i in range(sample_size):
        idx = round(i * (len(sorted_rows) - 1) / max(1, sample_size - 1))
        while idx in chosen_indices and idx + 1 < len(sorted_rows):
            idx += 1
        while idx in chosen_indices and idx - 1 >= 0:
            idx -= 1
        chosen_indices.append(idx)
    chosen = [sorted_rows[i] for i in sorted(chosen_indices)]
    return chosen


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.input_jsonl)))
    chosen = choose_evenly_spaced(rows, args.sample_size)
    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in chosen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "input_jsonl": str(Path(args.input_jsonl)),
        "output_jsonl": str(output_path),
        "sample_size": len(chosen),
        "selection_rule": "Evenly spaced over the sorted gold edge-count distribution.",
        "benchmark_ids": [row["benchmark_id"] for row in chosen],
        "gold_num_edges": [row["gold_num_edges"] for row in chosen],
        "gold_num_nodes": [row["gold_num_nodes"] for row in chosen],
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
