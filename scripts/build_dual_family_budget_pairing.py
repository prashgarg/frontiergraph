#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PATH_SUMMARY = ROOT / "outputs/paper/89_retrieval_budget_eval_path_to_direct/retrieval_budget_summary.csv"
DIRECT_SUMMARY = ROOT / "outputs/paper/151_retrieval_budget_direct_to_path/retrieval_budget_summary.csv"
PATH_CUTOFF = ROOT / "outputs/paper/89_retrieval_budget_eval_path_to_direct/retrieval_budget_cutoff_eval.csv"
DIRECT_CUTOFF = ROOT / "outputs/paper/151_retrieval_budget_direct_to_path/retrieval_budget_cutoff_eval.csv"
COMMON_POOL_SIZE = 5000

PALETTE = {
    "Path-to-direct": "#46627f",
    "Direct-to-path": "#c97255",
}


def load_summary(path: Path, family: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["family"] = family
    return df


def build_combined_summary() -> pd.DataFrame:
    df = pd.concat(
        [
            load_summary(PATH_SUMMARY, "Path-to-direct"),
            load_summary(DIRECT_SUMMARY, "Direct-to-path"),
        ],
        ignore_index=True,
    )
    for col in ["mean_recall_at_100", "mean_precision_at_100", "mean_pool_recall_ceiling", "mean_pool_positive_rate"]:
        if col in df.columns:
            df[f"{col}_pct"] = 100 * df[col]
    return df.sort_values(["horizon", "pool_size", "family"])


def build_budget_curve() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    metric_map = {
        20: ("precision_at_20", "recall_at_20"),
        50: ("precision_at_50", "recall_at_50"),
        100: ("precision_at_100", "recall_at_100"),
        250: ("precision_at_250", "recall_at_250"),
        500: ("precision_at_500", "recall_at_500"),
    }
    for family, path in [("Path-to-direct", PATH_CUTOFF), ("Direct-to-path", DIRECT_CUTOFF)]:
        df = pd.read_csv(path)
        df = df.loc[df["pool_size"].eq(COMMON_POOL_SIZE)].copy()
        if df.empty:
            continue
        for horizon in sorted(df["horizon"].unique()):
            sub = df.loc[df["horizon"].eq(horizon)].copy()
            row: dict[str, float | int | str] = {
                "family": family,
                "horizon": int(horizon),
                "pool_size": COMMON_POOL_SIZE,
                "pool_recall_ceiling_pct": 100 * float(sub["pool_recall_ceiling"].mean()),
            }
            for k, (precision_col, recall_col) in metric_map.items():
                row[f"future_links_per_100_at_{k}"] = 100 * float(sub[precision_col].mean())
                row[f"recall_pct_at_{k}"] = 100 * float(sub[recall_col].mean())
            frames.append(pd.DataFrame([row]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def plot_budget(curve_df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    horizons = sorted(curve_df["horizon"].unique())
    fig, axes = plt.subplots(2, len(horizons), figsize=(11.2, 5.8), constrained_layout=True, sharex=True)
    if len(horizons) == 1:
        axes = [[axes[0]], [axes[1]]]
    k_values = [20, 50, 100, 250, 500]
    for c, h in enumerate(horizons):
        sub = curve_df[curve_df["horizon"] == h]
        for family in ["Path-to-direct", "Direct-to-path"]:
            fam = sub[sub["family"] == family]
            if fam.empty:
                continue
            row = fam.iloc[0]
            future_per_100 = [float(row[f"future_links_per_100_at_{k}"]) for k in k_values]
            recall_pct = [float(row[f"recall_pct_at_{k}"]) for k in k_values]
            axes[0][c].plot(
                k_values,
                future_per_100,
                marker="o",
                lw=2,
                color=PALETTE[family],
                label=family if c == 0 else None,
            )
            axes[1][c].plot(
                k_values,
                recall_pct,
                marker="o",
                lw=2,
                color=PALETTE[family],
            )
        axes[0][c].set_title(f"h={h}", fontsize=10)
        axes[0][c].grid(color="#d9d9d9", lw=0.6, alpha=0.8)
        axes[1][c].grid(color="#d9d9d9", lw=0.6, alpha=0.8)
        axes[0][c].tick_params(labelsize=8)
        axes[1][c].tick_params(labelsize=8)
        axes[1][c].set_xlabel("Reading budget (top K)", fontsize=9)
        for ax in (axes[0][c], axes[1][c]):
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
    axes[0][0].set_ylabel("Future links per 100", fontsize=9)
    axes[1][0].set_ylabel("Recall (%)", fontsize=9)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.03))
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def write_summary_note(df: pd.DataFrame, curve_df: pd.DataFrame, out_path: Path) -> None:
    lines = ["# Dual-family retrieval-budget pairing", ""]
    lines.append(f"All reading-budget curves below use the common pool size of {COMMON_POOL_SIZE}.")
    lines.append("")
    for h in sorted(df["horizon"].unique()):
        lines.append(f"## Horizon {h}")
        sub = curve_df[curve_df["horizon"] == h].set_index("family")
        if {"Path-to-direct", "Direct-to-path"}.issubset(set(sub.index)):
            p = sub.loc["Path-to-direct"]
            d = sub.loc["Direct-to-path"]
            lines.append(
                "- top 100: future links per 100 = {pp:.2f} vs {dp:.2f}; recall = {pr:.3f}% vs {dr:.3f}%".format(
                    pp=p["future_links_per_100_at_100"],
                    dp=d["future_links_per_100_at_100"],
                    pr=p["recall_pct_at_100"],
                    dr=d["recall_pct_at_100"],
                )
            )
            lines.append(
                "- top 500: future links per 100 = {pp:.2f} vs {dp:.2f}; recall = {pr:.3f}% vs {dr:.3f}%".format(
                    pp=p["future_links_per_100_at_500"],
                    dp=d["future_links_per_100_at_500"],
                    pr=p["recall_pct_at_500"],
                    dr=d["recall_pct_at_500"],
                )
            )
            lines.append(
                "- pool recall ceiling at pool={pool}: {pp:.2f}% vs {dp:.2f}%".format(
                    pool=COMMON_POOL_SIZE,
                    pp=p["pool_recall_ceiling_pct"],
                    dp=d["pool_recall_ceiling_pct"],
                )
            )
        lines.append("")
    out_path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = build_combined_summary()
    curve_df = build_budget_curve()
    df.to_csv(out / "dual_family_retrieval_budget_summary.csv", index=False)
    curve_df.to_csv(out / "dual_family_retrieval_budget_curves.csv", index=False)
    plot_budget(curve_df, out / "dual_family_retrieval_budget_summary.png", out / "dual_family_retrieval_budget_summary.pdf")
    write_summary_note(df, curve_df, out / "summary.md")


if __name__ == "__main__":
    main()
