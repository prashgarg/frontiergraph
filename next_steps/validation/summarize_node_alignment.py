from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


NODE_WEIGHTS = {
    "exact_match": 1.00,
    "near_synonym": 0.90,
    "broader_than_gold": 0.70,
    "narrower_than_gold": 0.70,
    "partial_overlap": 0.50,
    "context_only": 0.15,
    "no_match": 0.00,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize node-alignment judge outputs into weighted metrics.")
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def weight_for(label: str) -> float:
    return NODE_WEIGHTS.get(label, 0.0)


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def threshold_share(values: list[float], threshold: float) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value >= threshold) / len(values)


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.results_jsonl)))
    summary_rows = []

    by_prompt_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    gold_class_counter: Counter[str] = Counter()
    pred_class_counter: Counter[str] = Counter()

    for row in rows:
        output = row["output"]
        gold_alignments = output["gold_node_alignments"]
        pred_alignments = output["predicted_node_alignments"]

        gold_scores = [weight_for(item["overlap_class"]) for item in gold_alignments]
        pred_scores = [weight_for(item["overlap_class"]) for item in pred_alignments]
        adjusted_gold_scores = [
            weight_for(item["overlap_class"])
            for item in gold_alignments
            if item["gold_recoverable_from_abstract"] in {"yes", "partly"}
        ]

        node_recall = mean(gold_scores)
        node_precision = mean(pred_scores)
        adjusted_node_recall = mean(adjusted_gold_scores)
        node_f1 = 0.0 if node_precision + node_recall == 0 else 2 * node_precision * node_recall / (node_precision + node_recall)

        summary_row = {
            "benchmark_id": row["benchmark_id"],
            "benchmark_dataset": row["benchmark_dataset"],
            "prompt_family": row["prompt_family"],
            "source_model": row["source_model"],
            "judge_model": row["judge_model"],
            "node_precision": round(node_precision, 3),
            "node_recall": round(node_recall, 3),
            "adjusted_node_recall": round(adjusted_node_recall, 3),
            "node_f1": round(node_f1, 3),
            "gold_coverage_ge_050": round(threshold_share(gold_scores, 0.50), 3),
            "gold_coverage_ge_070": round(threshold_share(gold_scores, 0.70), 3),
            "pred_coverage_ge_050": round(threshold_share(pred_scores, 0.50), 3),
            "pred_coverage_ge_070": round(threshold_share(pred_scores, 0.70), 3),
            "overall_notes": output["overall_notes"],
        }
        summary_rows.append(summary_row)
        by_prompt_family[row["prompt_family"]].append(summary_row)

        gold_class_counter.update(item["overlap_class"] for item in gold_alignments)
        pred_class_counter.update(item["overlap_class"] for item in pred_alignments)

    aggregate = {
        "rows": len(summary_rows),
        "by_prompt_family": {},
        "gold_overlap_class_counts": dict(gold_class_counter),
        "pred_overlap_class_counts": dict(pred_class_counter),
    }
    for prompt_family, family_rows in by_prompt_family.items():
        aggregate["by_prompt_family"][prompt_family] = {
            "rows": len(family_rows),
            "mean_node_precision": round(mean([row["node_precision"] for row in family_rows]), 3),
            "mean_node_recall": round(mean([row["node_recall"] for row in family_rows]), 3),
            "mean_adjusted_node_recall": round(mean([row["adjusted_node_recall"] for row in family_rows]), 3),
            "mean_node_f1": round(mean([row["node_f1"] for row in family_rows]), 3),
            "mean_gold_coverage_ge_050": round(mean([row["gold_coverage_ge_050"] for row in family_rows]), 3),
            "mean_gold_coverage_ge_070": round(mean([row["gold_coverage_ge_070"] for row in family_rows]), 3),
            "mean_pred_coverage_ge_050": round(mean([row["pred_coverage_ge_050"] for row in family_rows]), 3),
            "mean_pred_coverage_ge_070": round(mean([row["pred_coverage_ge_070"] for row in family_rows]), 3),
        }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
        if summary_rows:
            writer.writeheader()
            writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
