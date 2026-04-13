from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/GraphDir")
OVERALL_CSV = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/widened_overall_summary.csv"
ERA_CSV = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/widened_era_summary.csv"
PNG_OUT = ROOT / "paper/main_benchmark_refreshed.png"
PDF_OUT = ROOT / "paper/main_benchmark_refreshed.pdf"


MODEL_LABELS = {
    "pref_attach": "Preferential attachment",
    "transparent": "Transparent graph score",
    "adopted_glm_logit_family_aware_boundary_gap": "Learned reranker",
    "adopted_pairwise_logit_family_aware_composition": "Learned reranker",
    "adopted_glm_logit_quality": "Learned reranker",
}

MODEL_ORDER = ["pref_attach", "transparent", "adopted"]
MODEL_COLORS = {
    "pref_attach": "#7a7a7a",
    "transparent": "#4e79a7",
    "adopted": "#d55e00",
}


def _model_bucket(model: str) -> str:
    if model == "pref_attach":
        return "pref_attach"
    if model == "transparent":
        return "transparent"
    return "adopted"


def main() -> None:
    overall = pd.read_csv(OVERALL_CSV)
    era = pd.read_csv(ERA_CSV)

    overall["model_bucket"] = overall["model"].map(_model_bucket)
    era["model_bucket"] = era["model"].map(_model_bucket)

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)

    # Panel A: main benchmark overall Recall@100
    ax = axes[0]
    horizons = [5, 10, 15]
    x = range(len(horizons))
    width = 0.24

    for i, bucket in enumerate(MODEL_ORDER):
        vals = []
        for h in horizons:
            sub = overall[(overall["horizon"] == h) & (overall["model_bucket"] == bucket)]
            vals.append(float(sub["mean_recall_at_100"].iloc[0]))
        ax.bar(
            [xi + (i - 1) * width for xi in x],
            vals,
            width=width,
            color=MODEL_COLORS[bucket],
            label=MODEL_LABELS[
                "pref_attach" if bucket == "pref_attach" else ("transparent" if bucket == "transparent" else "adopted_glm_logit_quality")
            ],
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"h={h}" for h in horizons])
    ax.set_ylabel("Recall@100")
    ax.set_title("Main benchmark, 1990--2015 cutoffs")
    ax.set_ylim(0, 0.18)
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")

    # Panel B: early vs late regime split
    ax = axes[1]
    eras = ["early_1990_1995", "late_2000_2015"]
    era_labels = {"early_1990_1995": "Early: 1990, 1995", "late_2000_2015": "Late: 2000--2015"}
    line_styles = {"transparent": "--", "adopted": "-"}

    for bucket in ["transparent", "adopted"]:
        for era_key in eras:
            vals = []
            hs = [5, 10, 15]
            for h in hs:
                sub = era[
                    (era["horizon"] == h)
                    & (era["model_bucket"] == bucket)
                    & (era["era"] == era_key)
                ]
                vals.append(float(sub["mean_recall_at_100"].iloc[0]))
            ax.plot(
                hs,
                vals,
                marker="o",
                linestyle=line_styles[bucket],
                color=MODEL_COLORS[bucket],
                alpha=0.65 if era_key == "early_1990_1995" else 1.0,
                linewidth=2,
                label=f"{MODEL_LABELS['transparent' if bucket == 'transparent' else 'adopted_glm_logit_quality']}, {era_labels[era_key]}",
            )

    ax.set_xticks(horizons)
    ax.set_ylabel("Recall@100")
    ax.set_title("Early vs late regime split")
    ax.set_ylim(0, 0.19)
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")

    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    fig.savefig(PDF_OUT, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
