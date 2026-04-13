#!/usr/bin/env python3
"""Build a compact early-vs-late appendix display from the refreshed benchmark."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    REPO_ROOT
    / "outputs/paper/123_effective_benchmark_widened_1990_2015/widened_era_summary.csv"
)
OUTPUT_DIR = REPO_ROOT / "outputs/paper/132_early_late_appendix_display"

WINNERS = {
    5: "adopted_glm_logit_family_aware_boundary_gap",
    10: "adopted_pairwise_logit_family_aware_composition",
    15: "adopted_glm_logit_quality",
}
ERA_ORDER = ["early_1990_1995", "late_2000_2015"]
ERA_LABELS = {
    "early_1990_1995": "Early (1990-1995)",
    "late_2000_2015": "Late (2000-2015)",
}


def main() -> None:
    df = pd.read_csv(INPUT)
    rows = []
    for horizon, model in WINNERS.items():
        sub = df[(df["horizon"] == horizon) & (df["model"] == model)].copy()
        for era in ERA_ORDER:
            row = sub[sub["era"] == era].iloc[0]
            endpoint_recent_share = (
                row["mean_top_mean_source_recent_share"]
                + row["mean_top_mean_target_recent_share"]
            ) / 2.0
            rows.append(
                {
                    "horizon": horizon,
                    "era": ERA_LABELS[era],
                    "winner_model": model,
                    "n_cutoffs": int(row["n_cutoffs"]),
                    "mean_eval_positives": float(row["mean_n_eval_pos"]),
                    "winner_recall_at_100": float(row["mean_recall_at_100"]),
                    "top100_support_age_years": float(
                        row["mean_top_mean_support_age_years"]
                    ),
                    "endpoint_recent_share": float(endpoint_recent_share),
                    "top100_evidence_diversity": float(
                        row["mean_top_mean_pair_evidence_diversity"]
                    ),
                }
            )

    out = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_DIR / "early_late_regime_summary.csv", index=False)

    lines = [
        "# Early vs Late Benchmark Regime Summary",
        "",
        "Uses the horizon-specific adopted winner at each main horizon.",
        "",
        "| Horizon | Era | Cutoffs | Mean eval positives | Winner R@100 | Support age | Endpoint recent share |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in out.itertuples(index=False):
        lines.append(
            "| "
            f"{row.horizon} | {row.era} | {row.n_cutoffs} | "
            f"{row.mean_eval_positives:.1f} | {row.winner_recall_at_100:.3f} | "
            f"{row.top100_support_age_years:.1f} | {row.endpoint_recent_share:.3f} |"
        )
    lines.extend(
        [
            "",
            "Definitions:",
            "- `Mean eval positives`: average number of realized positives in the cutoff-year evaluation cell.",
            "- `Winner R@100`: Recall@100 for the horizon-specific adopted reranker winner.",
            "- `Support age`: mean support age in years for the winner's surfaced top-100.",
            "- `Endpoint recent share`: mean of source and target recent-share measures in the winner's surfaced top-100.",
        ]
    )
    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
