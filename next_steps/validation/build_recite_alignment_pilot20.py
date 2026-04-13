from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_BENCHMARK_JSONL = "next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark.jsonl"
DEFAULT_SUMMARY_CSV = "data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_gpt5nano_low_v1/judge_summary/summary.csv"
DEFAULT_OUTPUT_JSONL = "next_steps/validation/data/reCITE/frontiergraph_alignment_pilot20.jsonl"
DEFAULT_OUTPUT_MANIFEST = "next_steps/validation/data/reCITE/frontiergraph_alignment_pilot20_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a balanced ReCITE alignment sample.")
    parser.add_argument("--benchmark-jsonl", default=DEFAULT_BENCHMARK_JSONL)
    parser.add_argument("--summary-csv", default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-manifest", default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--fair-count", type=int, default=4)
    parser.add_argument("--partly-count", type=int, default=12)
    parser.add_argument("--unfair-count", type=int, default=4)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def choose_evenly_spaced(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if count >= len(rows):
        return list(rows)
    rows = sorted(rows, key=lambda r: (float(r["node_overlap_score"]), float(r["edge_overlap_score"]), int(r["benchmark_id"])))
    chosen: list[dict[str, str]] = []
    used: set[int] = set()
    for i in range(count):
        idx = round(i * (len(rows) - 1) / max(1, count - 1))
        while idx in used and idx + 1 < len(rows):
            idx += 1
        while idx in used and idx - 1 >= 0:
            idx -= 1
        used.add(idx)
        chosen.append(rows[idx])
    return sorted(chosen, key=lambda r: int(r["benchmark_id"]))


def main() -> None:
    args = parse_args()
    rows = list(csv.DictReader(Path(args.summary_csv).open(encoding="utf-8")))
    by_class = {
        "fair_abstract_level_comparison": [],
        "partly_fair_but_resolution_mismatch": [],
        "mostly_unfair_for_abstract_extraction": [],
    }
    for row in rows:
        if row["comparability_class"] in by_class:
            by_class[row["comparability_class"]].append(row)

    selected_summary_rows = []
    selected_summary_rows.extend(choose_evenly_spaced(by_class["fair_abstract_level_comparison"], args.fair_count))
    selected_summary_rows.extend(choose_evenly_spaced(by_class["partly_fair_but_resolution_mismatch"], args.partly_count))
    selected_summary_rows.extend(choose_evenly_spaced(by_class["mostly_unfair_for_abstract_extraction"], args.unfair_count))

    selected_ids = {str(row["benchmark_id"]) for row in selected_summary_rows}
    benchmark_rows = [row for row in iter_jsonl(Path(args.benchmark_jsonl)) if str(row["benchmark_id"]) in selected_ids]
    benchmark_rows = sorted(benchmark_rows, key=lambda r: int(r["benchmark_id"]))

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in benchmark_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    selected_by_id = {str(row["benchmark_id"]): row for row in selected_summary_rows}
    fair = args.fair_count
    partly = args.partly_count
    unfair = args.unfair_count
    manifest = {
        "benchmark_jsonl": str(Path(args.benchmark_jsonl)),
        "summary_csv": str(Path(args.summary_csv)),
        "selection_rule": (
            "Balanced development sample: "
            f"{fair} fair, {partly} partly fair, {unfair} mostly unfair; "
            "evenly spaced over node-overlap within each class from the existing "
            "variable-prompt full ReCITE judge summary."
        ),
        "sample_size": len(benchmark_rows),
        "benchmark_ids": [row["benchmark_id"] for row in benchmark_rows],
        "comparability_classes": {bid: selected_by_id[str(bid)]["comparability_class"] for bid in [row["benchmark_id"] for row in benchmark_rows]},
        "node_overlap_scores": {bid: selected_by_id[str(bid)]["node_overlap_score"] for bid in [row["benchmark_id"] for row in benchmark_rows]},
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
