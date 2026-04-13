from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs/paper/135_precision_at_k_refresh"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PAPER_DIR = ROOT / "paper"

PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"

REPORT_CUTOFFS = {
    5: [1990, 1995, 2000, 2005, 2010, 2015],
    10: [1990, 1995, 2000, 2005, 2010, 2015],
    15: [1990, 1995, 2000, 2005, 2010],
}
K_RANGE = [25, 50, 100, 200, 500, 1000]

MODEL_SPECS = [
    ("transparent", "Transparent graph score", "graph_score", "#4393c3", "-", "o"),
    ("cooc", "Co-occurrence", "cooc_count", "#d6604d", "-.", "s"),
    ("direct_degree", "Directed degree product", "direct_degree_product_raw", "#2166ac", ":", "^"),
    ("pref_attach", "Preferential attachment", "support_degree_product_raw", "#b2182b", "--", "D"),
]


def build_precision_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(
        PANEL_PATH,
        columns=[
            "cutoff_year_t",
            "horizon",
            "appears_within_h",
            "transparent_score",
            "score",
            "support_degree_product_raw",
            "cooc_count",
            "direct_degree_product_raw",
        ],
    ).copy()

    df["graph_score"] = (
        pd.to_numeric(df["transparent_score"], errors="coerce")
        .fillna(pd.to_numeric(df["score"], errors="coerce"))
        .fillna(0.0)
        .astype(float)
    )

    rows: list[dict[str, float | int | str]] = []

    for horizon, cutoffs in REPORT_CUTOFFS.items():
        horizon_df = df[(df["horizon"] == horizon) & (df["cutoff_year_t"].isin(cutoffs))].copy()

        for model_key, model_label, score_col, _, _, _ in MODEL_SPECS:
            for cutoff_year_t, cutoff_df in horizon_df.groupby("cutoff_year_t"):
                ranked = cutoff_df.sort_values(score_col, ascending=False)

                for k in K_RANGE:
                    topk = ranked.head(k)
                    precision = float(topk["appears_within_h"].mean()) if len(topk) else np.nan
                    rows.append(
                        {
                            "horizon": int(horizon),
                            "cutoff_year_t": int(cutoff_year_t),
                            "k": int(k),
                            "model_key": model_key,
                            "model": model_label,
                            "precision_at_k": precision,
                        }
                    )

    panel = pd.DataFrame(rows)
    summary = (
        panel.groupby(["horizon", "k", "model_key", "model"], as_index=False)
        .agg(
            mean_precision_at_k=("precision_at_k", "mean"),
            sd_precision_at_k=("precision_at_k", "std"),
            n_cutoffs=("precision_at_k", "size"),
        )
        .sort_values(["horizon", "k", "mean_precision_at_k"], ascending=[True, True, False])
        .reset_index(drop=True)
    )
    winners = (
        summary.sort_values(["horizon", "k", "mean_precision_at_k"], ascending=[True, True, False])
        .groupby(["horizon", "k"], as_index=False)
        .first()
        .rename(columns={"model": "winning_model", "mean_precision_at_k": "winning_precision_at_k"})
    )
    return panel, summary, winners


def plot_precision_curves(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharex=True, sharey=True)

    for ax, horizon in zip(axes, [5, 10, 15]):
        horizon_summary = summary[summary["horizon"] == horizon]
        for model_key, model_label, _, color, linestyle, marker in MODEL_SPECS:
            series = horizon_summary[horizon_summary["model_key"] == model_key].sort_values("k")
            ax.plot(
                series["k"],
                series["mean_precision_at_k"],
                color=color,
                linestyle=linestyle,
                marker=marker,
                linewidth=2.0,
                markersize=4.2,
                label=model_label,
            )

        ax.set_xscale("log")
        ax.set_title(f"h = {horizon} years")
        ax.set_xlabel("Shortlist size K")
        ax.grid(True, alpha=0.25)

    axes[0].set_ylabel("Mean precision@K")
    axes[0].set_ylim(0, 0.23)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    fig.savefig(OUT_DIR / "precision_at_k_curves_refreshed.png")
    fig.savefig(OUT_DIR / "precision_at_k_curves_refreshed.pdf")
    fig.savefig(PAPER_DIR / "precision_at_k_curves_refreshed.png")
    fig.savefig(PAPER_DIR / "precision_at_k_curves_refreshed.pdf")
    plt.close(fig)


def write_summary_note(summary: pd.DataFrame, winners: pd.DataFrame) -> None:
    lines: list[str] = []
    lines.append("# Precision-at-K Refresh")
    lines.append("")
    lines.append("Current main benchmark: 1990--2015 horizon-valid cutoff grid.")
    lines.append("")
    for horizon in [5, 10, 15]:
        lines.append(f"## Horizon {horizon}")
        h_winners = winners[winners["horizon"] == horizon].sort_values("k")
        for _, row in h_winners.iterrows():
            lines.append(
                f"- K={int(row['k'])}: {row['winning_model']} ({row['winning_precision_at_k']:.4f})"
            )
        lines.append("")

    lines.append("## Headline interpretation")
    lines.append(
        "- The transparent graph score is strongest at the very tight shortlist margin (K=25 and K=50) at all three main horizons."
    )
    lines.append(
        "- Co-occurrence becomes slightly stronger at intermediate shortlist sizes (especially K=100 and K=200)."
    )
    lines.append(
        "- By K=500 and K=1000, the simple-score family converges. At longer horizons, directed degree product and preferential attachment catch up or slightly overtake."
    )
    lines.append(
        "- So the transparent score is best read as a strict-shortlist screen, not as a universal simple-score winner across all attention budgets."
    )
    lines.append(
        "- This complements the main benchmark table: the learned reranker matters because no simple score dominates across horizons and shortlist depths."
    )
    lines.append("")

    (OUT_DIR / "summary.md").write_text("\n".join(lines))


def main() -> None:
    panel, summary, winners = build_precision_panel()
    panel.to_csv(OUT_DIR / "precision_at_k_panel.csv", index=False)
    summary.to_csv(OUT_DIR / "precision_at_k_summary.csv", index=False)
    winners.to_csv(OUT_DIR / "precision_at_k_winners.csv", index=False)
    plot_precision_curves(summary)
    write_summary_note(summary, winners)


if __name__ == "__main__":
    main()
