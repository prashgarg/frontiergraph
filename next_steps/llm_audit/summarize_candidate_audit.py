from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize candidate-audit judge outputs.")
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.results_jsonl)))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    by_model: dict[str, list[dict]] = defaultdict(list)
    reason_counts: dict[str, Counter[str]] = defaultdict(Counter)
    decision_counts: dict[str, Counter[str]] = defaultdict(Counter)
    formulation_counts: dict[str, Counter[str]] = defaultdict(Counter)
    implication_counts: dict[str, Counter[str]] = defaultdict(Counter)
    summary_rows = []

    for row in rows:
        output = row["output"]
        judge_model = row["judge_model"]
        by_model[judge_model].append(output)
        reason_counts[judge_model].update([output["main_reason"]])
        decision_counts[judge_model].update([output["decision"]])
        formulation_counts[judge_model].update([output["better_formulation"]])
        implication_counts[judge_model].update([output["deterministic_implication"]])
        summary_rows.append(
            {
                "benchmark_id": row["benchmark_id"],
                "judge_model": judge_model,
                "decision": output["decision"],
                "main_reason": output["main_reason"],
                "secondary_reason": output["secondary_reason"],
                "better_formulation": output["better_formulation"],
                "candidate_quality_score": output["candidate_quality_score"],
                "paper_shapedness_score": output["paper_shapedness_score"],
                "mechanism_support_score": output["mechanism_support_score"],
                "genericity_score": output["genericity_score"],
                "likely_useful_for_current_2026_shortlist": output["likely_useful_for_current_2026_shortlist"],
                "deterministic_implication": output["deterministic_implication"],
                "brief_rationale": output["brief_rationale"],
            }
        )

    aggregate = {"rows": len(rows), "by_model": {}}
    for model, outputs in by_model.items():
        aggregate["by_model"][model] = {
            "rows": len(outputs),
            "decision_counts": dict(decision_counts[model]),
            "main_reason_counts": dict(reason_counts[model]),
            "better_formulation_counts": dict(formulation_counts[model]),
            "deterministic_implication_counts": dict(implication_counts[model]),
            "mean_candidate_quality_score": round(mean([o["candidate_quality_score"] for o in outputs]), 3),
            "mean_paper_shapedness_score": round(mean([o["paper_shapedness_score"] for o in outputs]), 3),
            "mean_mechanism_support_score": round(mean([o["mechanism_support_score"] for o in outputs]), 3),
            "mean_genericity_score": round(mean([o["genericity_score"] for o in outputs]), 3),
        }

    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
        if summary_rows:
            writer.writeheader()
            writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
