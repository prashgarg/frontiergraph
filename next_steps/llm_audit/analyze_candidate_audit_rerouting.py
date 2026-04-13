from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze current-candidate audit outputs and derive rerouting recommendations.")
    parser.add_argument("--audit-input-jsonl", required=True)
    parser.add_argument("--audit-results-jsonl", required=True)
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


def route_label(decision: str, formulation: str) -> str:
    if formulation == "keep_direct_edge" and decision == "keep":
        return "keep_direct_edge"
    if formulation == "reframe_as_path_question" and decision == "keep":
        return "promote_path_question"
    if formulation == "reframe_as_path_question" and decision != "keep":
        return "downrank_path_question"
    if formulation == "reframe_as_mediator_question" and decision == "keep":
        return "promote_mediator_question"
    if formulation == "reframe_as_mediator_question" and decision != "keep":
        return "downrank_mediator_question"
    if formulation == "drop_entirely":
        return "drop_entirely"
    return f"other__{decision}__{formulation}"


def main() -> None:
    args = parse_args()
    inputs = {row["benchmark_id"]: row for row in iter_jsonl(Path(args.audit_input_jsonl))}
    results = list(iter_jsonl(Path(args.audit_results_jsonl)))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    enriched_rows: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    reason_by_route: dict[str, Counter[str]] = defaultdict(Counter)
    implication_by_route: dict[str, Counter[str]] = defaultdict(Counter)

    for row in results:
        benchmark_id = row["benchmark_id"]
        audit = row["output"]
        source = inputs[benchmark_id]
        route = route_label(audit["decision"], audit["better_formulation"])
        route_counts.update([route])
        reason_by_route[route].update([audit["main_reason"]])
        implication_by_route[route].update([audit["deterministic_implication"]])

        enriched_rows.append(
            {
                "benchmark_id": benchmark_id,
                "route_label": route,
                "decision": audit["decision"],
                "main_reason": audit["main_reason"],
                "better_formulation": audit["better_formulation"],
                "deterministic_implication": audit["deterministic_implication"],
                "candidate_quality_score": audit["candidate_quality_score"],
                "paper_shapedness_score": audit["paper_shapedness_score"],
                "mechanism_support_score": audit["mechanism_support_score"],
                "genericity_score": audit["genericity_score"],
                "question_rendering": source["question_rendering"],
                "source_node": source["source_node"],
                "target_node": source["target_node"],
                "public_score": source["score_summary"].get("public_score"),
                "path_support_norm": source["score_summary"].get("path_support_norm"),
                "supporting_path_count": source["support_summary"].get("supporting_path_count"),
                "mediator_count": source["support_summary"].get("mediator_count"),
                "motif_count": source["support_summary"].get("motif_count"),
                "public_specificity_score": source["graph_stats"].get("public_specificity_score"),
                "top_mediators": json.dumps(source.get("top_mediators", []), ensure_ascii=False),
                "brief_rationale": audit["brief_rationale"],
                "app_link": source.get("app_link", ""),
            }
        )

    aggregate = {
        "rows": len(enriched_rows),
        "route_counts": dict(route_counts),
        "route_shares": {key: round(value / len(enriched_rows), 3) for key, value in route_counts.items()},
        "top_main_reasons_by_route": {
            route: dict(counter.most_common())
            for route, counter in reason_by_route.items()
        },
        "top_implications_by_route": {
            route: dict(counter.most_common())
            for route, counter in implication_by_route.items()
        },
        "route_feature_means": {},
    }

    for route in route_counts:
        group = [row for row in enriched_rows if row["route_label"] == route]
        aggregate["route_feature_means"][route] = {
            "mean_public_score": round(mean([float(row["public_score"] or 0) for row in group]), 4),
            "mean_supporting_path_count": round(mean([float(row["supporting_path_count"] or 0) for row in group]), 3),
            "mean_mediator_count": round(mean([float(row["mediator_count"] or 0) for row in group]), 3),
            "mean_motif_count": round(mean([float(row["motif_count"] or 0) for row in group]), 3),
            "mean_public_specificity_score": round(mean([float(row["public_specificity_score"] or 0) for row in group]), 3),
            "mean_candidate_quality_score": round(mean([float(row["candidate_quality_score"] or 0) for row in group]), 3),
            "mean_mechanism_support_score": round(mean([float(row["mechanism_support_score"] or 0) for row in group]), 3),
        }

    (out_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fieldnames = list(enriched_rows[0].keys()) if enriched_rows else []
    with (out_dir / "routing_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if enriched_rows:
            writer.writeheader()
            writer.writerows(enriched_rows)


if __name__ == "__main__":
    main()
