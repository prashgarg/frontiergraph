"""Combine three runs of the remaining heuristic row review and compare them.

This script builds:
- a three-run vote matrix
- modal / majority decisions
- comparison against the current heuristic row decision
- comparison against cluster-level decisions where available
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

RUN_SUFFIXES = ["rh1", "rh2", "rh3"]

VOTE_MATRIX_PATH = DATA_DIR / "remaining_heuristic_row_review_vote_matrix.parquet"
VOTE_SUMMARY_PATH = DATA_DIR / "remaining_heuristic_row_review_vote_summary.md"
MAJORITY_PATH = DATA_DIR / "remaining_heuristic_row_review_majority.parquet"
DISAGREEMENT_PATH = DATA_DIR / "remaining_heuristic_row_review_disagreements.parquet"


def majority_vote(values: list[str | None]) -> tuple[str | None, int, str]:
    clean = [v for v in values if v]
    if not clean:
        return None, 0, "all_missing"
    counts = Counter(clean)
    top = counts.most_common()
    if len(top) == 1:
        return top[0][0], top[0][1], "unanimous"
    if top[0][1] >= 2:
        return top[0][0], top[0][1], "two_to_one"
    return None, 1, "no_majority"


def load_run(suffix: str) -> pd.DataFrame:
    path = DATA_DIR / f"remaining_heuristic_row_review_results_final_{suffix}.parquet"
    return pd.read_parquet(path).set_index("review_id")


def main() -> None:
    runs = {suffix: load_run(suffix) for suffix in RUN_SUFFIXES}
    base = runs[RUN_SUFFIXES[0]].reset_index()

    context_cols = [
        c
        for c in [
            "review_id",
            "label",
            "cluster_id",
            "effective_score_band",
            "effective_proposed_action",
            "heuristic_final_decision",
            "heuristic_overlay_action",
            "cluster_final_decision",
            "cluster_final_proposal",
            "onto_label",
            "rank2_label",
            "impact_score",
            "freq",
        ]
        if c in base.columns
    ]
    vote = base[context_cols].copy().set_index("review_id")

    for suffix, df in runs.items():
        prefix = suffix
        for col in ["decision", "confidence", "canonical_target_label", "new_concept_family_label", "reason"]:
            if col in df.columns:
                vote[f"{prefix}_{col}"] = df[col]

    majority_rows = []
    for review_id, row in vote.iterrows():
        values = [row.get(f"{suffix}_decision") for suffix in RUN_SUFFIXES]
        maj, maj_votes, split_type = majority_vote(values)
        majority_rows.append(
            {
                "review_id": review_id,
                "majority_decision": maj,
                "majority_votes": maj_votes,
                "split_type": split_type,
                "decision_pattern": " | ".join(v if v else "missing" for v in values),
                "unique_nonmissing_decisions": len({v for v in values if v}),
            }
        )
    majority_df = pd.DataFrame(majority_rows).set_index("review_id")
    vote = vote.join(majority_df).reset_index()

    vote["agrees_with_heuristic"] = vote["majority_decision"] == vote["heuristic_final_decision"]
    vote["agrees_with_cluster"] = vote["majority_decision"] == vote["cluster_final_decision"]

    vote.to_parquet(VOTE_MATRIX_PATH, index=False)
    vote.to_parquet(MAJORITY_PATH, index=False)

    disagreements = vote[
        (~vote["agrees_with_heuristic"].fillna(False))
        | (~vote["agrees_with_cluster"].fillna(True))
        | (vote["split_type"] != "unanimous")
    ].copy()
    disagreements.to_parquet(DISAGREEMENT_PATH, index=False)

    lines = [
        "# Remaining Heuristic Row Review Vote Summary",
        "",
        f"- total rows: `{len(vote):,}`",
        f"- unanimous: `{int((vote['split_type'] == 'unanimous').sum()):,}`",
        f"- two-to-one: `{int((vote['split_type'] == 'two_to_one').sum()):,}`",
        f"- no majority: `{int((vote['split_type'] == 'no_majority').sum()):,}`",
        "",
        "## Majority decisions",
    ]
    for key, value in vote["majority_decision"].fillna("missing").value_counts().items():
        lines.append(f"- `{key}`: `{int(value):,}`")
    lines.extend(
        [
            "",
            "## Comparison with current heuristic row decisions",
            f"- agreement count: `{int(vote['agrees_with_heuristic'].sum()):,}`",
            f"- disagreement count: `{int((~vote['agrees_with_heuristic']).sum()):,}`",
            "",
            "## Comparison with cluster decisions where available",
            f"- rows with cluster decision context: `{int(vote['cluster_final_decision'].notna().sum()):,}`",
            f"- agreement count: `{int(vote.loc[vote['cluster_final_decision'].notna(), 'agrees_with_cluster'].sum()):,}`",
            f"- disagreement count: `{int((vote.loc[vote['cluster_final_decision'].notna(), 'agrees_with_cluster'] == False).sum()):,}`",
            "",
            "## Top heuristic -> majority transitions",
        ]
    )
    trans = (
        vote.groupby(["heuristic_final_decision", "majority_decision"], dropna=False)
        .size()
        .sort_values(ascending=False)
    )
    for (left, right), count in trans.head(20).items():
        lines.append(f"- `{left}` -> `{right}`: `{int(count):,}`")
    VOTE_SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
