"""Build 10-vote modal decisions for the no-majority hard-case set.

Combines:
- run1/run2/run3 decisions from `main_grounding_review_v2_vote_matrix.parquet`
- extra hard-case runs from `no_majority_grounding_review_results_runX.parquet`
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

VOTE_MATRIX_PATH = DATA_DIR / "main_grounding_review_v2_vote_matrix.parquet"

OUTPUT_PARQUET = DATA_DIR / "no_majority_modal_vote_10run.parquet"
OUTPUT_CSV = DATA_DIR / "no_majority_modal_vote_10run.csv"
OUTPUT_MD = DATA_DIR / "no_majority_modal_vote_10run.md"
TIES_PARQUET = DATA_DIR / "no_majority_modal_vote_10run_ties.parquet"
TIES_CSV = DATA_DIR / "no_majority_modal_vote_10run_ties.csv"

EXTRA_RUNS = [f"run{i}" for i in range(4, 12)]


def majority_vote(values: list[str | None]) -> tuple[str | None, int, int, str]:
    clean = [str(v) for v in values if pd.notna(v) and str(v) != "missing"]
    if not clean:
        return None, 0, 0, "all_missing"
    counts = Counter(clean)
    top = counts.most_common()
    max_votes = top[0][1]
    tied = [label for label, count in top if count == max_votes]
    if len(tied) == 1:
        label = tied[0]
        split_type = "strict_modal" if max_votes >= 4 else "weak_modal"
        return label, max_votes, len(clean), split_type
    return None, max_votes, len(clean), "tied_modal"


def main() -> None:
    vote = pd.read_parquet(VOTE_MATRIX_PATH)
    hard = vote[vote["split_type"] == "no_majority"].copy()

    present_extra_runs: list[str] = []
    for run in EXTRA_RUNS:
        path = DATA_DIR / f"no_majority_grounding_review_results_{run}.parquet"
        if not path.exists():
            continue
        present_extra_runs.append(run)
        df = pd.read_parquet(path)[["review_id", "decision", "confidence", "reason"]].rename(
            columns={
                "decision": f"{run}_decision",
                "confidence": f"{run}_confidence",
                "reason": f"{run}_reason",
            }
        )
        hard = hard.merge(df, on="review_id", how="left")

    rows = []
    decision_cols = ["run1_decision", "run2_decision", "run3_decision"] + [
        f"{run}_decision" for run in present_extra_runs
    ]
    for _, row in hard.iterrows():
        values = [row.get(col) for col in decision_cols]
        pattern_values = [str(v) if pd.notna(v) else "missing" for v in values]
        modal, votes, nonmissing, modal_type = majority_vote(values)
        rows.append(
            {
                "review_id": row["review_id"],
                "modal_decision": modal,
                "modal_votes": votes,
                "nonmissing_votes": nonmissing,
                "modal_type": modal_type,
                "vote_pattern": " | ".join(pattern_values),
                "unique_nonmissing_decisions": len({v for v in values if v and v != "missing"}),
            }
        )
    modal_df = pd.DataFrame(rows)
    hard = hard.merge(modal_df, on="review_id", how="left")

    hard.to_parquet(OUTPUT_PARQUET, index=False)
    hard.to_csv(OUTPUT_CSV, index=False)

    ties = hard[hard["modal_type"] == "tied_modal"].copy()
    ties.to_parquet(TIES_PARQUET, index=False)
    ties.to_csv(TIES_CSV, index=False)

    lines = [
        "# No-Majority 10-Run Modal Vote",
        "",
        f"- target rows: `{len(hard):,}`",
        f"- strict modal rows: `{int((hard['modal_type'] == 'strict_modal').sum()):,}`",
        f"- weak modal rows: `{int((hard['modal_type'] == 'weak_modal').sum()):,}`",
        f"- tied modal rows: `{int((hard['modal_type'] == 'tied_modal').sum()):,}`",
        "",
        "## Modal decisions",
    ]
    for decision, count in hard["modal_decision"].fillna("missing").value_counts().items():
        lines.append(f"- `{decision}`: `{count:,}`")
    lines.extend(["", "## Vote strengths"])
    for votes, count in hard["modal_votes"].value_counts().sort_index().items():
        lines.append(f"- `{votes}` votes: `{count:,}`")
    lines.extend(["", "## Sample rows", ""])
    sample_cols = [
        c
        for c in [
            "review_item_type",
            "label",
            "effective_score_band",
            "effective_proposed_action",
            "run1_decision",
            "run2_decision",
            "run3_decision",
            "run4_decision",
            "run5_decision",
            "run6_decision",
            "run7_decision",
            "run8_decision",
            "run9_decision",
            "run10_decision",
            "run11_decision",
            "modal_decision",
            "modal_votes",
            "modal_type",
        ]
        if c in hard.columns
    ]
    lines.append(hard[sample_cols].head(40).to_markdown(index=False))
    if len(ties):
        lines.extend(["", "## Tied sample", ""])
        lines.append(ties[sample_cols].head(40).to_markdown(index=False))
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
