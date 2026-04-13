"""Build 11-vote modal decisions for remaining heuristic no-majority rows.

Combines:
- original three row-review decisions from `remaining_heuristic_row_review_majority.parquet`
- extra runs `run4` ... `run11` from `remaining_heuristic_no_majority_results_runX.parquet`
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

SOURCE_PATH = DATA_DIR / "remaining_heuristic_row_review_majority.parquet"
OUTPUT_PARQUET = DATA_DIR / "remaining_heuristic_no_majority_modal_vote_11run.parquet"
OUTPUT_MD = DATA_DIR / "remaining_heuristic_no_majority_modal_vote_11run.md"
TIES_PARQUET = DATA_DIR / "remaining_heuristic_no_majority_modal_vote_11run_ties.parquet"

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
        modal_type = "strict_modal" if max_votes >= 4 else "weak_modal"
        return label, max_votes, len(clean), modal_type
    return None, max_votes, len(clean), "tied_modal"


def main() -> None:
    source = pd.read_parquet(SOURCE_PATH)
    hard = source[source["majority_decision"].isna()].copy()

    present_runs: list[str] = []
    for run in EXTRA_RUNS:
        path = DATA_DIR / f"remaining_heuristic_no_majority_results_{run}.parquet"
        if not path.exists():
            continue
        present_runs.append(run)
        df = pd.read_parquet(path)[["review_id", "decision", "confidence", "reason"]].rename(
            columns={
                "decision": f"{run}_decision",
                "confidence": f"{run}_confidence",
                "reason": f"{run}_reason",
            }
        )
        hard = hard.merge(df, on="review_id", how="left")

    rows = []
    decision_cols = ["rh1_decision", "rh2_decision", "rh3_decision"] + [f"{run}_decision" for run in present_runs]
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
                "unique_nonmissing_decisions": len({v for v in values if pd.notna(v) and str(v) != "missing"}),
            }
        )
    modal_df = pd.DataFrame(rows)
    hard = hard.merge(modal_df, on="review_id", how="left")

    hard.to_parquet(OUTPUT_PARQUET, index=False)
    ties = hard[hard["modal_type"] == "tied_modal"].copy()
    ties.to_parquet(TIES_PARQUET, index=False)

    lines = [
        "# Remaining-Heuristic No-Majority 11-Run Modal Vote",
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
            "label",
            "effective_score_band",
            "effective_proposed_action",
            "rh1_decision",
            "rh2_decision",
            "rh3_decision",
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
