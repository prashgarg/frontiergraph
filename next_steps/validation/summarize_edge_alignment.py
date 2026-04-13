from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EDGE_WEIGHTS = {
    "exact_edge_match": 1.00,
    "same_direction_broader_nodes": 0.75,
    "same_direction_partial_nodes": 0.60,
    "same_relation_different_graph_resolution": 0.40,
    "reversed_direction": 0.10,
    "context_or_method_edge": 0.10,
    "no_match": 0.00,
    "not_recoverable_from_abstract": 0.00,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize edge-alignment judge outputs into weighted metrics.")
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
    return EDGE_WEIGHTS.get(label, 0.0)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def threshold_share(values: list[float], threshold: float) -> float:
    return sum(1 for value in values if value >= threshold) / len(values) if values else 0.0


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.results_jsonl)))
    summary_rows = []
    by_prompt_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    gold_class_counter: Counter[str] = Counter()
    pred_class_counter: Counter[str] = Counter()

    for row in rows:
        output = row["output"]
        gold_alignments = output["gold_edge_alignments"]
        pred_alignments = output["predicted_edge_alignments"]

        gold_scores = [weight_for(item["edge_overlap_class"]) for item in gold_alignments]
        pred_scores = [weight_for(item["edge_overlap_class"]) for item in pred_alignments]
        adjusted_gold_scores = [
            weight_for(item["edge_overlap_class"])
            for item in gold_alignments
            if item["gold_edge_recoverable_from_abstract"] in {"yes", "partly"}
        ]

        edge_recall = mean(gold_scores)
        edge_precision = mean(pred_scores)
        adjusted_edge_recall = mean(adjusted_gold_scores)
        edge_f1 = 0.0 if edge_precision + edge_recall == 0 else 2 * edge_precision * edge_recall / (edge_precision + edge_recall)

        summary_row = {
            "benchmark_id": row["benchmark_id"],
            "benchmark_dataset": row["benchmark_dataset"],
            "prompt_family": row["prompt_family"],
            "source_model": row.get("source_model", ""),
            "judge_model": row.get("judge_model", ""),
            "edge_precision": round(edge_precision, 3),
            "edge_recall": round(edge_recall, 3),
            "adjusted_edge_recall": round(adjusted_edge_recall, 3),
            "edge_f1": round(edge_f1, 3),
            "gold_edge_coverage_ge_060": round(threshold_share(gold_scores, 0.60), 3),
            "gold_edge_coverage_ge_075": round(threshold_share(gold_scores, 0.75), 3),
            "pred_edge_coverage_ge_060": round(threshold_share(pred_scores, 0.60), 3),
            "pred_edge_coverage_ge_075": round(threshold_share(pred_scores, 0.75), 3),
            "overall_notes": output["overall_notes"],
        }
        summary_rows.append(summary_row)
        by_prompt_family[row["prompt_family"]].append(summary_row)
        gold_class_counter.update(item["edge_overlap_class"] for item in gold_alignments)
        pred_class_counter.update(item["edge_overlap_class"] for item in pred_alignments)

    aggregate = {
        "rows": len(summary_rows),
        "by_prompt_family": {},
        "gold_edge_class_counts": dict(gold_class_counter),
        "pred_edge_class_counts": dict(pred_class_counter),
    }
    for prompt_family, family_rows in by_prompt_family.items():
        aggregate["by_prompt_family"][prompt_family] = {
            "rows": len(family_rows),
            "mean_edge_precision": round(mean([row["edge_precision"] for row in family_rows]), 3),
            "mean_edge_recall": round(mean([row["edge_recall"] for row in family_rows]), 3),
            "mean_adjusted_edge_recall": round(mean([row["adjusted_edge_recall"] for row in family_rows]), 3),
            "mean_edge_f1": round(mean([row["edge_f1"] for row in family_rows]), 3),
            "mean_gold_edge_coverage_ge_060": round(mean([row["gold_edge_coverage_ge_060"] for row in family_rows]), 3),
            "mean_gold_edge_coverage_ge_075": round(mean([row["gold_edge_coverage_ge_075"] for row in family_rows]), 3),
            "mean_pred_edge_coverage_ge_060": round(mean([row["pred_edge_coverage_ge_060"] for row in family_rows]), 3),
            "mean_pred_edge_coverage_ge_075": round(mean([row["pred_edge_coverage_ge_075"] for row in family_rows]), 3),
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
