from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize structured graph-overlap judge outputs.")
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.results_jsonl)))
    out_dir = Path(args.output_dir) if args.output_dir else Path(args.results_jsonl).parent / "judge_summary"
    out_dir.mkdir(parents=True, exist_ok=True)

    flat_rows = []
    mismatch_counter = Counter()
    comparability_counter = Counter()
    by_prompt_family = defaultdict(list)
    for row in rows:
        out = row["output"]
        comparability_counter[out["comparability_class"]] += 1
        for mode in out["main_mismatch_modes"]:
            mismatch_counter[mode] += 1
        flat = {
            "benchmark_id": row["benchmark_id"],
            "benchmark_dataset": row["benchmark_dataset"],
            "prompt_family": row["prompt_family"],
            "source_model": row["source_model"],
            "judge_model": row["judge_model"],
            "comparability_class": out["comparability_class"],
            "gold_graph_recoverable_from_abstract": out["gold_graph_recoverable_from_abstract"],
            "node_overlap_score": out["node_overlap_score"],
            "edge_overlap_score": out["edge_overlap_score"],
            "main_mismatch_modes": out["main_mismatch_modes"],
            "summary": out["summary"],
        }
        flat_rows.append(flat)
        by_prompt_family[row["prompt_family"]].append(flat)

    df = pd.DataFrame(flat_rows)
    df.to_csv(out_dir / "summary.csv", index=False)

    aggregate = {
        "rows": len(flat_rows),
        "mean_node_overlap_score": round(float(df["node_overlap_score"].mean()), 3) if not df.empty else None,
        "mean_edge_overlap_score": round(float(df["edge_overlap_score"].mean()), 3) if not df.empty else None,
        "comparability_counts": dict(comparability_counter),
        "mismatch_mode_counts": dict(mismatch_counter),
        "by_prompt_family": {
            key: {
                "rows": len(values),
                "mean_node_overlap_score": round(sum(v["node_overlap_score"] for v in values) / len(values), 3) if values else None,
                "mean_edge_overlap_score": round(sum(v["edge_overlap_score"] for v in values) / len(values), 3) if values else None,
                "comparability_counts": dict(Counter(v["comparability_class"] for v in values)),
            }
            for key, values in by_prompt_family.items()
        },
    }
    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
