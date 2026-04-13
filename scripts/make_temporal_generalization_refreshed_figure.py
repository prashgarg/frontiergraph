#!/usr/bin/env python3
"""Render the refreshed temporal-generalization figure from summary CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TRAIN_ERA = "train_1990_2005"
HELDOUT_ERA = "heldout_2010_2015"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the refreshed temporal-generalization figure.")
    parser.add_argument(
        "--table",
        default="outputs/paper/133_temporal_generalization_refresh/temporal_generalization_table.csv",
        dest="table_path",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/133_temporal_generalization_refresh/temporal_generalization_refreshed.png",
        dest="out_path",
    )
    parser.add_argument(
        "--paper-out",
        default="paper/temporal_generalization_refreshed.png",
        dest="paper_out_path",
    )
    return parser.parse_args()


def render(table_df: pd.DataFrame, out_path: Path) -> None:
    eras = [TRAIN_ERA, HELDOUT_ERA]
    era_labels = {
        TRAIN_ERA: "Train era\n(1990-2005)",
        HELDOUT_ERA: "Held-out era\n(2010-2015)",
    }
    horizon_order = sorted(table_df["horizon"].astype(int).unique())
    colors = {"reranker": "#1f77b4", "pref": "#9aa0a6"}

    fig, axes = plt.subplots(1, len(horizon_order), figsize=(7.6, 3.6), sharey=True)
    if len(horizon_order) == 1:
        axes = [axes]

    for ax, horizon in zip(axes, horizon_order):
        sub = table_df[table_df["horizon"].astype(int) == int(horizon)].set_index("era")
        x = np.arange(len(eras))
        width = 0.34
        rer_vals = [float(sub.loc[e, "mean_p100_reranker"]) for e in eras]
        pref_vals = [float(sub.loc[e, "mean_p100_pref"]) for e in eras]
        delta_vals = [float(sub.loc[e, "mean_p100_reranker"] - sub.loc[e, "mean_p100_pref"]) for e in eras]

        ax.bar(x - width / 2, rer_vals, width=width, color=colors["reranker"], label="Reranker")
        ax.bar(x + width / 2, pref_vals, width=width, color=colors["pref"], label="Pref. attach.")
        for i, delta in enumerate(delta_vals):
            ax.text(
                x[i] - width / 2,
                rer_vals[i] + 0.012,
                f"+{delta:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
                color=colors["reranker"],
            )

        ax.set_xticks(x)
        ax.set_xticklabels([era_labels[e] for e in eras], fontsize=8)
        ax.set_title(f"h={int(horizon)}", fontsize=10)
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Precision@100")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors["reranker"]),
        plt.Rectangle((0, 0), 1, 1, color=colors["pref"]),
    ]
    fig.legend(handles, ["Reranker", "Pref. attach."], loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    table_df = pd.read_csv(args.table_path)
    render(table_df, Path(args.out_path))
    render(table_df, Path(args.paper_out_path))


if __name__ == "__main__":
    main()
