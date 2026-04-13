from __future__ import annotations

import ast
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANKINGS_PATH = ROOT / "outputs" / "paper" / "180_wide_mechanism_stage_b_pairwise_analysis_sampled" / "stage_b_shelf_rankings.csv"
CURATED_PATH = ROOT / "site" / "src" / "content" / "mechanism-editorial-opportunities.json"
GROUPS_PATH = ROOT / "site" / "src" / "content" / "mechanism-carousel-groups.json"
OUT_PATH = ROOT / "site" / "src" / "content" / "mechanism-archive-generated.json"

SHELF_ORDER = [
    ("field", "innovation-productivity"),
    ("field", "macro-finance"),
    ("field", "climate-energy"),
    ("field", "labor-household-outcomes"),
    ("field", "development-urban"),
    ("field", "trade-globalization"),
    ("use_case", "paper-ready"),
    ("use_case", "cross-area-mechanism"),
    ("use_case", "phd-topic"),
    ("use_case", "open-little-direct"),
    ("use_case", "strong-nearby-evidence"),
]
MAX_ITEMS = 18


FIELD_LABELS = {
    "innovation-productivity": "innovation and productivity",
    "macro-finance": "macro and finance",
    "climate-energy": "climate and energy",
    "labor-household-outcomes": "labor and household",
    "development-urban": "development and urban",
    "trade-globalization": "trade and globalization",
    "other": "other",
}


def parse_list(value: str) -> list[str]:
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return []


def load_excluded_pairs() -> set[str]:
    curated = json.loads(CURATED_PATH.read_text())
    groups = json.loads(GROUPS_PATH.read_text())
    excluded = set(curated.keys())
    excluded.update(groups["front"]["items"])
    for group in groups["field_shelves"]:
        excluded.update(group["items"])
    for group in groups["use_case_shelves"]:
        excluded.update(group["items"])
    return excluded


def build_rows() -> list[dict]:
    rows = list(csv.DictReader(RANKINGS_PATH.open()))
    clean_rows = [
        row
        for row in rows
        if row.get("has_model_response") == "True"
        and row.get("keep_for_public_site") == "True"
        and row.get("primary_issue") in {"none", "duplicate_or_alias_risk"}
    ]
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in clean_rows:
        key = (row["shelf_kind"], row["shelf_name"])
        grouped.setdefault(key, []).append(row)

    for key, bucket in grouped.items():
        bucket.sort(
            key=lambda row: (
                {"none": 0, "duplicate_or_alias_risk": 1}.get(row.get("primary_issue", "duplicate_or_alias_risk"), 1),
                {"high": 0, "medium": 1, "low": 2}.get(row.get("suggested_priority", "medium"), 1),
                int(row.get("stage_b_rank") or "9999"),
                -float(row.get("pairwise_copeland_score") or "0"),
                -float(row.get("confidence") or "0"),
            )
        )

    excluded = load_excluded_pairs()
    selected: list[dict] = []
    seen_pairs: set[str] = set()
    indices = {key: 0 for key in SHELF_ORDER}

    while len(selected) < MAX_ITEMS:
        advanced = False
        for key in SHELF_ORDER:
            bucket = grouped.get(key, [])
            idx = indices[key]
            while idx < len(bucket):
                row = bucket[idx]
                idx += 1
                pair_key = row["pair_key"]
                if pair_key in excluded or pair_key in seen_pairs:
                    continue
                selected.append(row)
                seen_pairs.add(pair_key)
                advanced = True
                break
            indices[key] = idx
            if len(selected) >= MAX_ITEMS:
                break
        if not advanced:
            break
    return selected


def derive_who_its_for(field_shelves: list[str], source_label: str, target_label: str) -> str:
    if field_shelves:
        labels = [FIELD_LABELS.get(shelf, shelf.replace("-", " ")) for shelf in field_shelves[:2]]
        return ", ".join(labels) + " economists"
    return f"researchers working on {source_label.lower()} and {target_label.lower()}"


def main() -> None:
    archive_items = {}
    for display_order, row in enumerate(build_rows(), start=1):
        field_shelves = parse_list(row.get("field_shelves"))
        collection_tags = ["mechanism", *parse_list(row.get("collection_tags"))]
        channel_labels = parse_list(row.get("primary_channels"))
        archive_items[row["pair_key"]] = {
            "pair_key": row["pair_key"],
            "question_title": row["display_title"],
            "short_why": row["display_why"],
            "first_next_step": row["display_first_step"],
            "who_its_for": derive_who_its_for(field_shelves, row["source_label"], row["target_label"]),
            "display_order": display_order,
            "field_shelves": field_shelves,
            "collection_tags": collection_tags,
            "question_family": f"mechanism-archive-{display_order}",
            "graph_query": row["source_label"],
            "graph_family": "mechanism",
            "source_label": row["source_label"],
            "target_label": row["target_label"],
            "channel_labels": channel_labels,
            "route_family": row["route_family"],
        }

    OUT_PATH.write_text(json.dumps(archive_items, indent=2, ensure_ascii=True) + "\n")
    print(f"Wrote {len(archive_items)} archive items to {OUT_PATH}")


if __name__ == "__main__":
    main()
