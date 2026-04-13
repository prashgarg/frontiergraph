"""Build final adjudicated grounding review tables.

This resolves:
1. base unanimous / 2-1 majority rows from the 3-run vote matrix
2. former no-majority rows from the extended modal panel
3. the final tied rows via explicit manual adjudication
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

VOTE_MATRIX_PATH = DATA_DIR / "main_grounding_review_v2_vote_matrix.parquet"
HARD_MODAL_PATH = DATA_DIR / "no_majority_modal_vote_10run.parquet"

HARD_ADJ_PATH = DATA_DIR / "no_majority_final_adjudicated.parquet"
HARD_ADJ_CSV_PATH = DATA_DIR / "no_majority_final_adjudicated.csv"
HARD_ADJ_MD_PATH = DATA_DIR / "no_majority_final_adjudication_note.md"

FULL_ADJ_PATH = DATA_DIR / "main_grounding_review_v2_adjudicated.parquet"
FULL_ADJ_CSV_PATH = DATA_DIR / "main_grounding_review_v2_adjudicated.csv"
FULL_ADJ_MD_PATH = DATA_DIR / "main_grounding_review_v2_adjudicated.md"


MANUAL_OVERRIDES = {
    "gr_03780_row": {
        "label": "socioeconomic conditions",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Socioeconomics",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a broad socioeconomic context phrase rather than a distinct missing family. "
            "It is not an exact alias of Socioeconomics, so broad grounding is safer than aliasing."
        ),
    },
    "gr_04350_row": {
        "label": "ramsey pricing",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Ramsey pricing",
        "manual_reason": (
            "Ramsey pricing is an established economics concept in regulated pricing and public finance. "
            "It is related to Ramsey-rule reasoning but is not just an alias of Ramsey Rule."
        ),
    },
}


def build_hard_case_adjudicated() -> pd.DataFrame:
    hard = pd.read_parquet(HARD_MODAL_PATH).copy()

    hard["final_decision"] = hard["modal_decision"]
    hard["adjudication_source"] = hard["modal_type"].map(
        {
            "strict_modal": "hard_case_modal",
            "weak_modal": "hard_case_modal_weak",
            "tied_modal": "manual_override_pending",
        }
    )
    hard["manual_canonical_target_label"] = None
    hard["manual_new_concept_family_label"] = None
    hard["manual_reason"] = None

    for review_id, override in MANUAL_OVERRIDES.items():
        mask = hard["review_id"] == review_id
        if not mask.any():
            continue
        hard.loc[mask, "final_decision"] = override["final_decision"]
        hard.loc[mask, "manual_canonical_target_label"] = override["manual_canonical_target_label"]
        hard.loc[mask, "manual_new_concept_family_label"] = override["manual_new_concept_family_label"]
        hard.loc[mask, "manual_reason"] = override["manual_reason"]
        hard.loc[mask, "adjudication_source"] = "manual_override"

    return hard


def build_full_adjudicated(hard: pd.DataFrame) -> pd.DataFrame:
    vote = pd.read_parquet(VOTE_MATRIX_PATH).copy()

    vote["final_decision"] = vote["majority_decision"]
    vote["adjudication_source"] = vote["split_type"].map(
        {
            "unanimous": "three_run_unanimous",
            "two_to_one": "three_run_majority",
            "two_with_missing": "three_run_majority",
            "no_majority": "hard_case_pending",
            "all_missing": "hard_case_pending",
        }
    )

    hard_resolved = hard[
        [
            "review_id",
            "final_decision",
            "adjudication_source",
            "manual_canonical_target_label",
            "manual_new_concept_family_label",
            "manual_reason",
            "modal_type",
            "modal_votes",
        ]
    ].copy()
    vote = vote.merge(hard_resolved, on="review_id", how="left", suffixes=("", "_hard"))

    needs_hard = vote["split_type"].isin(["no_majority", "all_missing"])
    vote.loc[needs_hard, "final_decision"] = vote.loc[needs_hard, "final_decision_hard"]
    vote.loc[needs_hard, "adjudication_source"] = vote.loc[needs_hard, "adjudication_source_hard"]

    vote["manual_canonical_target_label"] = vote["manual_canonical_target_label"]
    vote["manual_new_concept_family_label"] = vote["manual_new_concept_family_label"]
    vote["manual_reason"] = vote["manual_reason"]
    vote["hard_modal_type"] = vote["modal_type"]
    vote["hard_modal_votes"] = vote["modal_votes"]

    drop_cols = [c for c in ["final_decision_hard", "adjudication_source_hard", "modal_type", "modal_votes"] if c in vote.columns]
    vote = vote.drop(columns=drop_cols)

    return vote


def write_notes(hard: pd.DataFrame, full: pd.DataFrame) -> None:
    hard_lines = [
        "# Final Hard-Case Adjudication",
        "",
        "- Former no-majority set size: `352`",
        f"- Resolved by modal vote: `{int((hard['adjudication_source'].isin(['hard_case_modal', 'hard_case_modal_weak'])).sum()):,}`",
        f"- Resolved by manual override: `{int((hard['adjudication_source'] == 'manual_override').sum()):,}`",
        "",
        "## Manual Adjudications",
        "",
        "### `socioeconomic conditions` (`gr_03780_row`)",
        "- Final decision: `accept_existing_broad`",
        "- Canonical target: `Socioeconomics`",
        "- Reason:",
        "This phrase functions as a broad socioeconomic context label rather than a distinct missing concept family. "
        "It is too broad to justify a new family and not exact enough to force aliasing, so broad grounding is the safest fit.",
        "",
        "### `ramsey pricing` (`gr_04350_row`)",
        "- Final decision: `promote_new_concept_family`",
        "- New concept family: `Ramsey pricing`",
        "- Reason:",
        "Ramsey pricing is a real economics concept in regulated pricing and public finance. "
        "It is semantically related to Ramsey-rule reasoning, but it is not simply an alias of `Ramsey Rule`, so a new-family promotion is cleaner.",
        "",
        "## Hard-Case Decision Counts",
    ]
    for decision, count in hard["final_decision"].fillna("missing").value_counts().items():
        hard_lines.append(f"- `{decision}`: `{count:,}`")
    HARD_ADJ_MD_PATH.write_text("\n".join(hard_lines) + "\n")

    full_lines = [
        "# Final Adjudicated Grounding Review",
        "",
        f"- total rows: `{len(full):,}`",
        "",
        "## Final decision counts",
    ]
    for decision, count in full["final_decision"].fillna("missing").value_counts().items():
        full_lines.append(f"- `{decision}`: `{count:,}`")
    full_lines.extend(["", "## Resolution sources"])
    for source, count in full["adjudication_source"].fillna("missing").value_counts().items():
        full_lines.append(f"- `{source}`: `{count:,}`")
    FULL_ADJ_MD_PATH.write_text("\n".join(full_lines) + "\n")


def main() -> None:
    hard = build_hard_case_adjudicated()
    hard.to_parquet(HARD_ADJ_PATH, index=False)
    hard.to_csv(HARD_ADJ_CSV_PATH, index=False)

    full = build_full_adjudicated(hard)
    full.to_parquet(FULL_ADJ_PATH, index=False)
    full.to_csv(FULL_ADJ_CSV_PATH, index=False)

    write_notes(hard, full)


if __name__ == "__main__":
    main()
