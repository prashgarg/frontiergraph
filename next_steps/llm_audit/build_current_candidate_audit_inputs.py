from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build current FrontierGraph candidate-audit inputs from generated site data.")
    parser.add_argument("--site-data-json", default="site/src/generated/site-data.json")
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--exclude-results-jsonl", action="append", default=[])
    parser.add_argument("--snapshot-year", type=int, default=2026)
    return parser.parse_args()


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def short_papers_blob(papers: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    out = []
    for paper in papers[:limit]:
        out.append(
            {
                "title": paper.get("title", ""),
                "year": paper.get("year", ""),
                "citation_label": paper.get("citation_label", ""),
                "journal": paper.get("journal", ""),
                "edge": f"{paper.get('edge_src_display_label', '')} -> {paper.get('edge_dst_display_label', '')}",
            }
        )
    return out


def pseudo_paths(source_label: str, target_label: str, mediators: list[str], limit: int = 3) -> list[str]:
    out = []
    for mediator in mediators[:limit]:
        out.append(f"{source_label} -> {mediator} -> {target_label}")
    if not out:
        out.append("No explicit path rows exported in the current ranked-question payload.")
    return out


def load_excluded_ids(paths: list[str]) -> set[str]:
    excluded: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                benchmark_id = str(payload.get("benchmark_id") or "")
                if benchmark_id:
                    excluded.add(benchmark_id)
    return excluded


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.site_data_json).read_text(encoding="utf-8"))
    rows = as_list(payload.get("questions", {}).get("ranked_questions", []))
    rows = sorted(rows, key=lambda row: float(row.get("score", 0.0)), reverse=True)
    excluded_ids = load_excluded_ids(args.exclude_results_jsonl)
    if excluded_ids:
        rows = [row for row in rows if str(row.get("pair_key", "")) not in excluded_ids]
    if args.offset:
        rows = rows[args.offset :]
    rows = rows[: args.top_n]

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as handle:
        for rank, row in enumerate(rows, start=1):
            source_label = str(row.get("source_display_label") or row.get("source_label") or "")
            target_label = str(row.get("target_display_label") or row.get("target_label") or "")
            mediators = [str(item) for item in as_list(row.get("top_mediator_display_labels")) if str(item).strip()]
            papers = short_papers_blob(as_list(row.get("representative_papers")))

            question_rendering = (
                str(row.get("display_question_title", "")).strip()
                or f"How might {source_label} change {target_label}?"
            )
            candidate_type = "missing_direct_link_path_supported"
            score_summary = {
                "public_score": row.get("score"),
                "base_score": row.get("base_score"),
                "duplicate_penalty": row.get("duplicate_penalty"),
                "path_support_norm": row.get("path_support_norm"),
                "gap_bonus": row.get("gap_bonus"),
                "slice_label": row.get("slice_label", ""),
                "question_family": row.get("question_family", ""),
            }
            support_summary = {
                "why_now": row.get("why_now", ""),
                "recommended_move": row.get("recommended_move", ""),
                "supporting_path_count": row.get("supporting_path_count", 0),
                "mediator_count": row.get("mediator_count", 0),
                "motif_count": row.get("motif_count", 0),
                "direct_link_status": row.get("direct_link_status", ""),
                "common_contexts": row.get("common_contexts", ""),
            }
            graph_stats = {
                "rank_in_current_public_window": rank,
                "cross_field": row.get("cross_field", False),
                "source_bucket": row.get("source_bucket", ""),
                "target_bucket": row.get("target_bucket", ""),
                "public_specificity_score": row.get("public_specificity_score"),
                "cooc_count": row.get("cooc_count", 0),
                "source_context_summary": row.get("source_context_summary", ""),
                "target_context_summary": row.get("target_context_summary", ""),
            }

            audit_row = {
                "benchmark_dataset": "frontiergraph_current",
                "benchmark_id": str(row.get("pair_key", "")),
                "prompt_family": "current_2026_ranked_question_audit",
                "condition_id": "site_v2_ranked_questions",
                "model": "frontiergraph_public_release",
                "reasoning_effort": "NA",
                "snapshot_year": args.snapshot_year,
                "candidate_id": str(row.get("pair_key", "")),
                "candidate_type": candidate_type,
                "source_node": source_label,
                "target_node": target_label,
                "question_rendering": question_rendering,
                "score_summary": score_summary,
                "support_summary": support_summary,
                "top_mediators": mediators[:5],
                "top_paths": pseudo_paths(source_label, target_label, mediators),
                "supporting_papers": papers,
                "graph_stats": graph_stats,
                "app_link": row.get("app_link", ""),
            }
            handle.write(json.dumps(audit_row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
