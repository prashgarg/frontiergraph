from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "paper" / "176_wide_mechanism_mini_triage_analysis" / "triage_all_candidates.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "177_wide_mechanism_stage_b_seed"

FIELD_SHELVES = [
    "macro-finance",
    "climate-energy",
    "innovation-productivity",
    "labor-household-outcomes",
    "development-urban",
    "trade-globalization",
    "other",
]

USE_CASES = [
    "cross-area-mechanism",
    "phd-topic",
    "paper-ready",
    "strong-nearby-evidence",
    "open-little-direct",
]

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
ISSUE_ORDER = {"none": 0, "duplicate_or_alias_risk": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a shelf-specific Stage B rerank seed from the wide mechanism mini triage.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), dest="input_path")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--per-field", type=int, default=150, dest="per_field")
    parser.add_argument("--per-use-case", type=int, default=120, dest="per_use_case")
    parser.add_argument("--global-front", type=int, default=100, dest="global_front")
    return parser.parse_args()


def parse_json_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    text = str(raw).strip()
    if not text:
        return []
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def first_issue_rank(raw: object) -> int:
    return ISSUE_ORDER.get(str(raw or ""), 2)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(Path(args.input_path), low_memory=False)
    df["field_shelves"] = df["field_shelves"].apply(parse_json_list)
    df["collection_tags"] = df["collection_tags"].apply(parse_json_list)
    df["priority_rank"] = df["suggested_priority"].map(PRIORITY_ORDER).fillna(3).astype(int)
    df["issue_rank"] = df["primary_issue"].apply(first_issue_rank)
    df["duplicate_family_risk"] = pd.to_numeric(df["duplicate_family_risk"], errors="coerce").fillna(5)
    df["mechanism_plausibility"] = pd.to_numeric(df["mechanism_plausibility"], errors="coerce").fillna(0)
    df["question_object_clarity"] = pd.to_numeric(df["question_object_clarity"], errors="coerce").fillna(0)
    df["endpoint_specificity"] = pd.to_numeric(df["endpoint_specificity"], errors="coerce").fillna(0)
    df["packet_rank"] = pd.to_numeric(df["packet_rank"], errors="coerce").fillna(10**9)

    usable = df[
        (df["has_model_response"] == True)
        & (df["plausible_mechanism_question"] == True)
        & (df["reader_facing"] == True)
        & (df["too_generic"] == False)
        & (df["mechanism_plausibility"] >= 3)
        & (df["question_object_clarity"] >= 3)
    ].copy()

    usable = usable.sort_values(
        [
            "priority_rank",
            "issue_rank",
            "mechanism_plausibility",
            "question_object_clarity",
            "endpoint_specificity",
            "duplicate_family_risk",
            "packet_rank",
        ],
        ascending=[True, True, False, False, False, True, True],
    )

    usable.to_csv(out_dir / "usable_candidates.csv", index=False)

    selected_frames: list[pd.DataFrame] = []
    field_rows: list[dict[str, object]] = []
    for shelf in FIELD_SHELVES:
        sub = usable[usable["field_shelves"].apply(lambda values: shelf in values)].copy()
        take = sub.head(args.per_field).copy()
        take["seed_source"] = f"field:{shelf}"
        take.to_csv(out_dir / f"field_{shelf}.csv", index=False)
        selected_frames.append(take)
        field_rows.append({"field_shelf": shelf, "usable_count": len(sub), "selected_count": len(take)})

    use_case_rows: list[dict[str, object]] = []
    for tag in USE_CASES:
        sub = usable[usable["collection_tags"].apply(lambda values: tag in values)].copy()
        take = sub.head(args.per_use_case).copy()
        take["seed_source"] = f"use_case:{tag}"
        take.to_csv(out_dir / f"use_case_{tag}.csv", index=False)
        selected_frames.append(take)
        use_case_rows.append({"use_case": tag, "usable_count": len(sub), "selected_count": len(take)})

    front = usable.head(args.global_front).copy()
    front["seed_source"] = "global-front"
    front.to_csv(out_dir / "global_front.csv", index=False)
    selected_frames.append(front)

    combined = pd.concat(selected_frames, ignore_index=True)
    combined["seed_source"] = combined["seed_source"].astype(str)

    deduped = combined.sort_values(
        [
            "priority_rank",
            "issue_rank",
            "mechanism_plausibility",
            "question_object_clarity",
            "endpoint_specificity",
            "duplicate_family_risk",
            "packet_rank",
        ],
        ascending=[True, True, False, False, False, True, True],
    ).drop_duplicates(subset=["pair_key"], keep="first")

    deduped.to_csv(out_dir / "stage_b_seed_union.csv", index=False)
    pd.DataFrame(field_rows).to_csv(out_dir / "field_summary.csv", index=False)
    pd.DataFrame(use_case_rows).to_csv(out_dir / "use_case_summary.csv", index=False)

    lines = [
        "# Wide Mechanism Stage B Seed",
        "",
        f"- usable candidates after wide mini triage: {len(usable):,}",
        f"- global front cap: {args.global_front:,}",
        f"- per-field cap: {args.per_field:,}",
        f"- per-use-case cap: {args.per_use_case:,}",
        f"- deduped Stage B seed union: {len(deduped):,}",
        "",
        "## Field shelves",
        "",
    ]
    for row in field_rows:
        lines.append(f"- {row['field_shelf']}: usable {row['usable_count']:,}, selected {row['selected_count']:,}")

    lines.extend(["", "## Use cases", ""])
    for row in use_case_rows:
        lines.append(f"- {row['use_case']}: usable {row['usable_count']:,}, selected {row['selected_count']:,}")

    lines.extend(["", "## Top of deduped seed union", ""])
    for row in deduped.head(30).itertuples(index=False):
        lines.append(
            f"- {row.display_title} | priority={row.suggested_priority} | issue={row.primary_issue} | fields={row.field_shelves} | use_cases={row.collection_tags}"
        )

    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
