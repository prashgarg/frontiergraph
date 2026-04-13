from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


NANO_INPUT_PER_M = 0.20
NANO_OUTPUT_PER_M = 1.25
MINI_INPUT_PER_M = 0.75
MINI_OUTPUT_PER_M = 4.50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare candidate-audit outputs across two judge models.")
    parser.add_argument("--nano-results-jsonl", required=True)
    parser.add_argument("--mini-results-jsonl", required=True)
    parser.add_argument("--nano-responses-dir", required=True)
    parser.add_argument("--mini-responses-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_results(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in iter_jsonl(path):
        out[str(row["benchmark_id"])] = row
    return out


def load_usage_totals(responses_dir: Path) -> dict[str, float]:
    input_tokens = 0
    output_tokens = 0
    response_count = 0
    for path in sorted(responses_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        usage = payload.get("usage", {})
        input_tokens += int(usage.get("input_tokens", 0) or 0)
        output_tokens += int(usage.get("output_tokens", 0) or 0)
        response_count += 1
    return {
        "responses": response_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def estimated_cost(model_label: str, usage: dict[str, float]) -> float:
    input_m = usage["input_tokens"] / 1_000_000
    output_m = usage["output_tokens"] / 1_000_000
    if model_label == "nano":
        return input_m * NANO_INPUT_PER_M + output_m * NANO_OUTPUT_PER_M
    if model_label == "mini":
        return input_m * MINI_INPUT_PER_M + output_m * MINI_OUTPUT_PER_M
    raise ValueError(model_label)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nano_rows = load_results(Path(args.nano_results_jsonl))
    mini_rows = load_results(Path(args.mini_results_jsonl))
    benchmark_ids = sorted(set(nano_rows) & set(mini_rows))

    if not benchmark_ids:
        raise SystemExit("No overlapping benchmark ids between nano and mini results.")

    decision_agreement = 0
    reason_agreement = 0
    formulation_agreement = 0
    shortlist_agreement = 0

    differing_rows = []
    candidate_quality_deltas = []
    paper_shapedness_deltas = []
    mechanism_deltas = []
    genericity_deltas = []
    decision_pair_counts: Counter[tuple[str, str]] = Counter()
    reason_pair_counts: Counter[tuple[str, str]] = Counter()

    for benchmark_id in benchmark_ids:
        nano_output = nano_rows[benchmark_id]["output"]
        mini_output = mini_rows[benchmark_id]["output"]

        nano_decision = nano_output["decision"]
        mini_decision = mini_output["decision"]
        nano_reason = nano_output["main_reason"]
        mini_reason = mini_output["main_reason"]
        nano_formulation = nano_output["better_formulation"]
        mini_formulation = mini_output["better_formulation"]
        nano_shortlist = nano_output["likely_useful_for_current_2026_shortlist"]
        mini_shortlist = mini_output["likely_useful_for_current_2026_shortlist"]

        decision_pair_counts.update([(nano_decision, mini_decision)])
        reason_pair_counts.update([(nano_reason, mini_reason)])

        if nano_decision == mini_decision:
            decision_agreement += 1
        if nano_reason == mini_reason:
            reason_agreement += 1
        if nano_formulation == mini_formulation:
            formulation_agreement += 1
        if nano_shortlist == mini_shortlist:
            shortlist_agreement += 1

        candidate_quality_deltas.append(mini_output["candidate_quality_score"] - nano_output["candidate_quality_score"])
        paper_shapedness_deltas.append(mini_output["paper_shapedness_score"] - nano_output["paper_shapedness_score"])
        mechanism_deltas.append(mini_output["mechanism_support_score"] - nano_output["mechanism_support_score"])
        genericity_deltas.append(mini_output["genericity_score"] - nano_output["genericity_score"])

        if (
            nano_decision != mini_decision
            or nano_reason != mini_reason
            or nano_formulation != mini_formulation
            or nano_shortlist != mini_shortlist
        ):
            differing_rows.append(
                {
                    "benchmark_id": benchmark_id,
                    "nano_decision": nano_decision,
                    "mini_decision": mini_decision,
                    "nano_main_reason": nano_reason,
                    "mini_main_reason": mini_reason,
                    "nano_better_formulation": nano_formulation,
                    "mini_better_formulation": mini_formulation,
                    "nano_shortlist": nano_shortlist,
                    "mini_shortlist": mini_shortlist,
                    "nano_candidate_quality_score": nano_output["candidate_quality_score"],
                    "mini_candidate_quality_score": mini_output["candidate_quality_score"],
                    "nano_paper_shapedness_score": nano_output["paper_shapedness_score"],
                    "mini_paper_shapedness_score": mini_output["paper_shapedness_score"],
                    "nano_mechanism_support_score": nano_output["mechanism_support_score"],
                    "mini_mechanism_support_score": mini_output["mechanism_support_score"],
                    "nano_genericity_score": nano_output["genericity_score"],
                    "mini_genericity_score": mini_output["genericity_score"],
                    "nano_rationale": nano_output["brief_rationale"],
                    "mini_rationale": mini_output["brief_rationale"],
                }
            )

    nano_usage = load_usage_totals(Path(args.nano_responses_dir))
    mini_usage = load_usage_totals(Path(args.mini_responses_dir))
    nano_cost = estimated_cost("nano", nano_usage)
    mini_cost = estimated_cost("mini", mini_usage)

    aggregate = {
        "rows_compared": len(benchmark_ids),
        "agreement": {
            "decision_agreement_rate": round(decision_agreement / len(benchmark_ids), 3),
            "main_reason_agreement_rate": round(reason_agreement / len(benchmark_ids), 3),
            "better_formulation_agreement_rate": round(formulation_agreement / len(benchmark_ids), 3),
            "shortlist_agreement_rate": round(shortlist_agreement / len(benchmark_ids), 3),
        },
        "score_deltas_mini_minus_nano": {
            "mean_candidate_quality_delta": round(mean(candidate_quality_deltas), 3),
            "mean_paper_shapedness_delta": round(mean(paper_shapedness_deltas), 3),
            "mean_mechanism_support_delta": round(mean(mechanism_deltas), 3),
            "mean_genericity_delta": round(mean(genericity_deltas), 3),
        },
        "decision_pair_counts": {
            f"{nano_decision}__{mini_decision}": count
            for (nano_decision, mini_decision), count in sorted(decision_pair_counts.items())
        },
        "main_reason_pair_counts": {
            f"{nano_reason}__{mini_reason}": count
            for (nano_reason, mini_reason), count in sorted(reason_pair_counts.items())
        },
        "usage_and_estimated_cost": {
            "nano": {
                **nano_usage,
                "estimated_cost_usd": round(nano_cost, 4),
            },
            "mini": {
                **mini_usage,
                "estimated_cost_usd": round(mini_cost, 4),
            },
            "mini_cost_multiple_of_nano": round(mini_cost / nano_cost, 2) if nano_cost else None,
        },
        "rows_with_any_material_difference": len(differing_rows),
    }

    (out_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (out_dir / "differences.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(differing_rows[0].keys()) if differing_rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if differing_rows:
            writer.writeheader()
            writer.writerows(differing_rows)


if __name__ == "__main__":
    main()
