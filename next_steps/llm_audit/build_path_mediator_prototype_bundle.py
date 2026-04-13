from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PATH_TITLE_TEMPLATE = "Through which nearby pathways might {source} shape {target}?"
MEDIATOR_TITLE_TEMPLATE = "Which nearby mechanisms most plausibly link {source} to {target}?"

PROMOTE_PATH_FIRST_STEP = "Start with a short synthesis or pilot that follows the nearest mediating topics."
DOWNRANK_PATH_FIRST_STEP = "Treat this as a lower-priority path question unless stronger local support appears."
PROMOTE_MEDIATOR_FIRST_STEP = "Start by testing which nearby channel carries the effect."
DOWNRANK_MEDIATOR_FIRST_STEP = "Keep this in reserve until one mechanism stands out more clearly."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build internal path/mediator prototype bundle from ranked questions and audit outputs.")
    parser.add_argument("--site-data-json", default="site/src/generated/site-data.json")
    parser.add_argument("--audit-results-jsonl", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def quote_list(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return "the nearest available mediators"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{items[0]}, {items[1]}, and {items[2]}"


def load_audit_rows(paths: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        for row in iter_jsonl(Path(raw_path)):
            benchmark_id = str(row["benchmark_id"])
            if benchmark_id in out:
                raise ValueError(f"Duplicate audit result for {benchmark_id}")
            out[benchmark_id] = row["output"]
    return out


def route_label_from_audit(output: dict[str, Any]) -> str:
    decision = str(output["decision"])
    formulation = str(output["better_formulation"])
    if decision == "keep" and formulation == "reframe_as_path_question":
        return "promote_path_question"
    if decision in {"downrank", "drop"} and formulation == "reframe_as_path_question":
        return "downrank_path_question"
    if decision == "keep" and formulation == "reframe_as_mediator_question":
        return "promote_mediator_question"
    if decision in {"downrank", "drop"} and formulation == "reframe_as_mediator_question":
        return "downrank_mediator_question"
    if decision == "keep" and formulation == "keep_direct_edge":
        return "keep_direct_edge"
    raise ValueError(f"Unsupported audit combination: decision={decision}, formulation={formulation}")


def object_family_for_route(route_label: str) -> str:
    if "path_question" in route_label:
        return "path_question"
    if "mediator_question" in route_label:
        return "mediator_question"
    if route_label == "keep_direct_edge":
        return "direct_edge_question"
    raise ValueError(route_label)


def shortlist_status_for_route(route_label: str) -> str:
    if route_label.startswith("promote_"):
        return "promote"
    if route_label.startswith("downrank_"):
        return "downrank"
    if route_label == "keep_direct_edge":
        return "keep"
    raise ValueError(route_label)


def prototype_title(row: dict[str, Any], route_label: str) -> str:
    source = clean_text(row.get("source_display_label") or row.get("source_label"))
    target = clean_text(row.get("target_display_label") or row.get("target_label"))
    current_title = clean_text(row.get("display_question_title"))
    if route_label == "keep_direct_edge":
        return current_title
    if route_label in {"promote_path_question", "downrank_path_question"}:
        return PATH_TITLE_TEMPLATE.format(source=source, target=target)
    if route_label in {"promote_mediator_question", "downrank_mediator_question"}:
        return MEDIATOR_TITLE_TEMPLATE.format(source=source, target=target)
    raise ValueError(route_label)


def prototype_why(row: dict[str, Any], route_label: str, mediators: list[str]) -> str:
    current_why = clean_text(row.get("why_now"))
    mediator_blob = quote_list(mediators[:3])
    if route_label == "keep_direct_edge":
        return current_why
    if route_label in {"promote_path_question", "downrank_path_question"}:
        return f"Nearby papers already suggest routes through {mediator_blob}."
    if route_label in {"promote_mediator_question", "downrank_mediator_question"}:
        return f"The main open question is which channel does the work: {mediator_blob}."
    raise ValueError(route_label)


def prototype_first_step(row: dict[str, Any], route_label: str) -> str:
    current_first_step = clean_text(row.get("recommended_move"))
    if route_label == "keep_direct_edge":
        return current_first_step
    if route_label == "promote_path_question":
        return PROMOTE_PATH_FIRST_STEP
    if route_label == "downrank_path_question":
        return DOWNRANK_PATH_FIRST_STEP
    if route_label == "promote_mediator_question":
        return PROMOTE_MEDIATOR_FIRST_STEP
    if route_label == "downrank_mediator_question":
        return DOWNRANK_MEDIATOR_FIRST_STEP
    raise ValueError(route_label)


def build_review_note(rows: list[dict[str, Any]], aggregate: dict[str, Any]) -> str:
    route_counts = aggregate["route_counts"]
    route_shares = aggregate["route_shares"]

    promoted_path = [row for row in rows if row["prototype_route_label"] == "promote_path_question"][:10]
    promoted_mediator = [row for row in rows if row["prototype_route_label"] == "promote_mediator_question"][:5]
    direct_rows = [row for row in rows if row["prototype_route_label"] == "keep_direct_edge"]
    side_by_side_candidates = (
        [row for row in rows if row["prototype_route_label"] == "promote_path_question"][:3]
        + [row for row in rows if row["prototype_route_label"] == "downrank_path_question"][:1]
        + [row for row in rows if row["prototype_route_label"] == "promote_mediator_question"][:1]
        + direct_rows[:1]
    )

    lines = [
        "# Internal Path/Mediator Prototype Review",
        "",
        "## Route counts and shares",
        "",
    ]
    for route in [
        "promote_path_question",
        "downrank_path_question",
        "promote_mediator_question",
        "downrank_mediator_question",
        "keep_direct_edge",
    ]:
        count = route_counts.get(route, 0)
        share = route_shares.get(route, 0.0)
        lines.append(f"- `{route}`: {count} ({share:.1%})")

    lines.extend(["", "## Top 10 promoted path questions", ""])
    for row in promoted_path:
        lines.append(
            f"- `{row['pair_key']}`: {row['prototype_display_title']}  \n"
            f"  Before: {row['prototype_source_title']}"
        )

    lines.extend(["", "## Top 5 promoted mediator questions", ""])
    if promoted_mediator:
        for row in promoted_mediator:
            lines.append(
                f"- `{row['pair_key']}`: {row['prototype_display_title']}  \n"
                f"  Before: {row['prototype_source_title']}"
            )
    else:
        lines.append("- No promoted mediator questions in this window.")

    lines.extend(["", "## Rare direct-edge case", ""])
    if direct_rows:
        row = direct_rows[0]
        lines.append(f"- `{row['pair_key']}`: {row['prototype_display_title']}")
        lines.append(f"  Why: {row['prototype_display_why']}")
    else:
        lines.append("- No direct-edge exceptions in this window.")

    lines.extend(["", "## Side-by-side examples", ""])
    for row in side_by_side_candidates:
        lines.extend(
            [
                f"### {row['pair_key']}",
                f"- Route: `{row['prototype_route_label']}`",
                f"- Before: {row['prototype_source_title']}",
                f"- After: {row['prototype_display_title']}",
                f"- Why: {row['prototype_display_why']}",
                f"- First step: {row['prototype_display_first_step']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    site_payload = json.loads(Path(args.site_data_json).read_text(encoding="utf-8"))
    ranked_rows = list(site_payload["questions"]["ranked_questions"])
    ranked_rows = sorted(ranked_rows, key=lambda row: float(row.get("score", 0.0)), reverse=True)
    audit_by_id = load_audit_rows(args.audit_results_jsonl)

    if len(ranked_rows) != len(audit_by_id):
        missing = [row["pair_key"] for row in ranked_rows if row["pair_key"] not in audit_by_id]
        extra = [pair_key for pair_key in audit_by_id if pair_key not in {row["pair_key"] for row in ranked_rows}]
        raise ValueError(
            f"Audit coverage mismatch: ranked={len(ranked_rows)} audit={len(audit_by_id)} missing={missing} extra={extra}"
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prototype_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked_rows, start=1):
        pair_key = str(row["pair_key"])
        audit_output = audit_by_id[pair_key]
        route_label = route_label_from_audit(audit_output)
        object_family = object_family_for_route(route_label)
        shortlist_status = shortlist_status_for_route(route_label)
        mediators = [clean_text(item) for item in (row.get("top_mediator_labels") or row.get("top_mediator_display_labels") or [])]
        primary_mediators = [item for item in mediators if item][:3]
        current_title = clean_text(row.get("display_question_title"))

        prototype_row = {
            "rank": rank,
            "pair_key": pair_key,
            "prototype_object_family": object_family,
            "prototype_route_label": route_label,
            "prototype_shortlist_status": shortlist_status,
            "prototype_display_title": prototype_title(row, route_label),
            "prototype_display_why": prototype_why(row, route_label, primary_mediators),
            "prototype_display_first_step": prototype_first_step(row, route_label),
            "prototype_primary_mediators": primary_mediators,
            "prototype_source_title": current_title,
            "source_node": clean_text(row.get("source_display_label") or row.get("source_label")),
            "target_node": clean_text(row.get("target_display_label") or row.get("target_label")),
            "score": float(row.get("score", 0.0) or 0.0),
            "supporting_path_count": int(row.get("supporting_path_count", 0) or 0),
            "mediator_count": int(row.get("mediator_count", 0) or 0),
            "motif_count": int(row.get("motif_count", 0) or 0),
            "public_specificity_score": float(row.get("public_specificity_score", 0.0) or 0.0),
            "question_family": clean_text(row.get("question_family")),
            "app_link": clean_text(row.get("app_link")),
            "audit_decision": audit_output["decision"],
            "audit_main_reason": audit_output["main_reason"],
            "audit_better_formulation": audit_output["better_formulation"],
            "audit_deterministic_implication": audit_output["deterministic_implication"],
        }
        prototype_rows.append(prototype_row)

    allowed_route_labels = {
        "promote_path_question",
        "downrank_path_question",
        "promote_mediator_question",
        "downrank_mediator_question",
        "keep_direct_edge",
    }
    allowed_object_families = {"path_question", "mediator_question", "direct_edge_question"}
    for row in prototype_rows:
        if row["prototype_route_label"] not in allowed_route_labels:
            raise ValueError(f"Unexpected route label: {row['prototype_route_label']}")
        if row["prototype_object_family"] not in allowed_object_families:
            raise ValueError(f"Unexpected object family: {row['prototype_object_family']}")
        for required in [
            "prototype_object_family",
            "prototype_route_label",
            "prototype_display_title",
            "prototype_display_why",
            "prototype_display_first_step",
        ]:
            if not clean_text(row.get(required)):
                raise ValueError(f"Missing required field {required} for {row['pair_key']}")
        if row["prototype_object_family"] != "direct_edge_question" and "How might " in row["prototype_display_title"]:
            raise ValueError(f"Unexpected direct-edge phrasing in {row['pair_key']}")

    route_counts = Counter(row["prototype_route_label"] for row in prototype_rows)
    aggregate = {
        "rows": len(prototype_rows),
        "route_counts": dict(route_counts),
        "route_shares": {route: count / len(prototype_rows) for route, count in route_counts.items()},
        "object_family_counts": dict(Counter(row["prototype_object_family"] for row in prototype_rows)),
        "route_counts_first_100": dict(Counter(row["prototype_route_label"] for row in prototype_rows[:100])),
        "route_counts_remaining_20": dict(Counter(row["prototype_route_label"] for row in prototype_rows[100:])),
        "top10_promoted_path_pair_keys": [
            row["pair_key"] for row in prototype_rows if row["prototype_route_label"] == "promote_path_question"
        ][:10],
        "top5_promoted_mediator_pair_keys": [
            row["pair_key"] for row in prototype_rows if row["prototype_route_label"] == "promote_mediator_question"
        ][:5],
        "direct_edge_pair_keys": [
            row["pair_key"] for row in prototype_rows if row["prototype_route_label"] == "keep_direct_edge"
        ],
    }

    jsonl_path = output_dir / "prototype_ranked_questions.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in prototype_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_path = output_dir / "prototype_ranked_questions.csv"
    fieldnames = list(prototype_rows[0].keys()) if prototype_rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if prototype_rows:
            writer.writeheader()
            writer.writerows(prototype_rows)

    (output_dir / "aggregate.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "review_note.md").write_text(build_review_note(prototype_rows, aggregate), encoding="utf-8")
    (output_dir / "validation.json").write_text(
        json.dumps(
            {
                "rows": len(prototype_rows),
                "all_required_fields_present": True,
                "allowed_route_labels_only": True,
                "allowed_object_families_only": True,
                "non_direct_titles_use_new_templates": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
