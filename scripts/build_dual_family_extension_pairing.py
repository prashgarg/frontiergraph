#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PATH_HET = ROOT / "outputs/paper/137_benchmark_panel_heterogeneity_refresh/frontier_summary.csv"
DIRECT_HET = ROOT / "outputs/paper/152_direct_to_path_heterogeneity/frontier_summary.csv"
PATH_FRONTIER_SUMMARY = ROOT / "outputs/paper/78_current_reranked_frontier_path_to_direct/current_reranked_frontier_summary.csv"
DIRECT_FRONTIER_SUMMARY = ROOT / "outputs/paper/153_current_reranked_frontier_direct_to_path/current_reranked_frontier_summary.csv"
PATH_FRONTIER = ROOT / "outputs/paper/78_current_reranked_frontier_path_to_direct/current_reranked_frontier.csv"
DIRECT_FRONTIER = ROOT / "outputs/paper/153_current_reranked_frontier_direct_to_path/current_reranked_frontier.csv"


FAMILY_LABELS = {
    "path_to_direct": "Path-to-direct",
    "direct_to_path": "Direct-to-path",
}

DIMENSION_LABELS = {
    "cutoff_period": "Cutoff period",
    "first_source": "Journal tier",
    "first_method_group": "Method family",
    "first_has_grant": "Funding",
}

GROUP_LABELS = {
    "1990s": "1990s",
    "2000s": "2000s",
    "2010s": "2010s",
    "core": "Core",
    "adjacent": "Adjacent",
    "design_based_causal": "Design-based causal",
    "panel_or_time_series": "Panel / time series",
    "Funded": "Funded",
    "Unfunded": "Unfunded",
}

PALETTE = {
    "Path-to-direct": "#46627f",
    "Direct-to-path": "#c97255",
}


def _clean_label(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"[.;:,]+\s*$", "", text).strip()
    return text


def load_frontier_summary(path: Path, family_key: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["family_key"] = family_key
    df["family"] = FAMILY_LABELS[family_key]
    return df


def prepare_heterogeneity_summary() -> pd.DataFrame:
    df = pd.concat(
        [
            load_frontier_summary(PATH_HET, "path_to_direct"),
            load_frontier_summary(DIRECT_HET, "direct_to_path"),
        ],
        ignore_index=True,
    )
    df = df[df["dimension"].isin(DIMENSION_LABELS)].copy()
    df["dimension_label"] = df["dimension"].map(DIMENSION_LABELS)
    df["group_label"] = df["group"].map(GROUP_LABELS).fillna(df["group"])
    df["frontier_delta_pctK_pp"] = 100 * df["frontier_delta_pctK"]
    df["delta_recall_at_100_pp"] = 100 * df["delta_recall_at_100"]
    cols = [
        "family_key",
        "family",
        "dimension",
        "dimension_label",
        "group",
        "group_label",
        "horizon",
        "frontier_delta_fixedK",
        "frontier_delta_pctK",
        "frontier_delta_pctK_pp",
        "delta_recall_at_100",
        "delta_recall_at_100_pp",
        "frontier_delta_pctK_ci_lo",
        "frontier_delta_pctK_ci_hi",
        "delta_recall_at_100_ci_lo",
        "delta_recall_at_100_ci_hi",
    ]
    return df[cols].sort_values(["dimension", "horizon", "group_label", "family"])


def plot_heterogeneity(df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    dims = ["cutoff_period", "first_source", "first_method_group", "first_has_grant"]
    horizons = [5, 10, 15]
    fig, axes = plt.subplots(
        len(horizons),
        len(dims),
        figsize=(12.4, 7.6),
        sharey=True,
        constrained_layout=True,
    )

    for r, h in enumerate(horizons):
        for c, dim in enumerate(dims):
            ax = axes[r, c]
            sub = df[(df["horizon"] == h) & (df["dimension"] == dim)].copy()
            groups = list(dict.fromkeys(sub["group_label"].tolist()))
            x = np.arange(len(groups))
            width = 0.34
            for i, family in enumerate(["Path-to-direct", "Direct-to-path"]):
                fam = sub[sub["family"] == family].set_index("group_label").reindex(groups)
                vals = fam["frontier_delta_pctK_pp"].to_numpy(dtype=float)
                ax.bar(
                    x + (i - 0.5) * width,
                    vals,
                    width=width,
                    color=PALETTE[family],
                    label=family if (r == 0 and c == 0) else None,
                )
            ax.axhline(0, color="#8f8f8f", lw=0.8)
            ax.set_xticks(x)
            ax.set_xticklabels(groups, rotation=0, fontsize=8)
            if r == 0:
                ax.set_title(DIMENSION_LABELS[dim], fontsize=10)
            if c == 0:
                ax.set_ylabel(f"h={h}\nAdvantage at broader shortlist (pp)", fontsize=9)
            ax.tick_params(axis="y", labelsize=8)
            ax.grid(axis="y", color="#d9d9d9", lw=0.6, alpha=0.8)
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def prepare_current_frontier_summary() -> pd.DataFrame:
    path = pd.read_csv(PATH_FRONTIER_SUMMARY)
    path["family_key"] = "path_to_direct"
    path["family"] = FAMILY_LABELS["path_to_direct"]
    path = path.rename(columns={"top100_surface_flagged_share": "surface_flagged_share"})

    direct = pd.read_csv(DIRECT_FRONTIER_SUMMARY)
    direct["family_key"] = "direct_to_path"
    direct["family"] = FAMILY_LABELS["direct_to_path"]
    direct = direct.rename(columns={"top100_surface_flagged_share": "surface_flagged_share"})

    common = [
        "family_key",
        "family",
        "horizon",
        "model_kind",
        "feature_family",
        "alpha",
        "pool_size",
        "top100_mean_rank_delta",
        "top100_median_rank_delta",
        "top100_max_rank_gain",
        "top100_max_rank_drop",
        "surface_flagged_share",
    ]
    return pd.concat([path[common], direct[common]], ignore_index=True).sort_values(["horizon", "family"])


def plot_current_frontier(df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    horizons = sorted(df["horizon"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8), constrained_layout=True)
    metrics = [
        ("top100_mean_rank_delta", "Mean rank gain in surfaced top 100"),
        ("surface_flagged_share", "Flagged share in surfaced top 100"),
    ]

    for ax, (metric, title) in zip(axes, metrics):
        x = np.arange(len(horizons))
        width = 0.34
        for i, family in enumerate(["Path-to-direct", "Direct-to-path"]):
            fam = df[df["family"] == family].set_index("horizon").reindex(horizons)
            vals = fam[metric].to_numpy(dtype=float)
            if metric == "surface_flagged_share":
                vals = 100 * vals
            ax.bar(
                x + (i - 0.5) * width,
                vals,
                width=width,
                color=PALETTE[family],
                label=family if metric == "top100_mean_rank_delta" else None,
            )
        ax.set_xticks(x)
        ax.set_xticklabels([f"h={h}" for h in horizons], fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", color="#d9d9d9", lw=0.6, alpha=0.8)
        ax.tick_params(axis="y", labelsize=8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
    axes[1].set_ylabel("Percent", fontsize=9)
    axes[0].set_ylabel("Average positions moved upward", fontsize=9)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.05))
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def prepare_top_examples() -> pd.DataFrame:
    frames = []
    for family_key, path in {
        "path_to_direct": PATH_FRONTIER,
        "direct_to_path": DIRECT_FRONTIER,
    }.items():
        df = pd.read_csv(path, low_memory=False)
        subset = (
            df[df["horizon"] == 10]
            .sort_values("surface_rank")
            .head(10)
            .copy()
        )
        subset["u_label"] = subset["u_label"].map(_clean_label)
        subset["v_label"] = subset["v_label"].map(_clean_label)
        subset["family_key"] = family_key
        subset["family"] = FAMILY_LABELS[family_key]
        cols = [
            "family_key",
            "family",
            "surface_rank",
            "u_label",
            "v_label",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "rank_delta",
            "feature_family",
            "model_kind",
        ]
        if "surface_flagged" in subset.columns:
            cols.append("surface_flagged")
        frames.append(subset[cols])
    return pd.concat(frames, ignore_index=True)


def write_summary_note(
    het_df: pd.DataFrame,
    frontier_df: pd.DataFrame,
    examples_df: pd.DataFrame,
    out_path: Path,
) -> None:
    h10_het = het_df[het_df["horizon"] == 10].copy()
    path_h10 = frontier_df[(frontier_df["family_key"] == "path_to_direct") & (frontier_df["horizon"] == 10)].iloc[0]
    direct_h10 = frontier_df[(frontier_df["family_key"] == "direct_to_path") & (frontier_df["horizon"] == 10)].iloc[0]
    top_examples = examples_df.groupby("family").head(5)
    lines = [
        "# Dual-family extension pairing",
        "",
        "## Current frontier at h=10",
        f"- Path-to-direct mean rank gain in surfaced top 100: {path_h10['top100_mean_rank_delta']:.1f}",
        f"- Direct-to-path mean rank gain in surfaced top 100: {direct_h10['top100_mean_rank_delta']:.1f}",
        f"- Path-to-direct flagged share in surfaced top 100: {100*path_h10['surface_flagged_share']:.1f}%",
        f"- Direct-to-path flagged share in surfaced top 100: {100*direct_h10['surface_flagged_share']:.1f}%",
        "",
        "## Heterogeneity at h=10",
    ]
    for dim in ["first_source", "first_method_group", "first_has_grant", "cutoff_period"]:
        sub = h10_het[h10_het["dimension"] == dim]
        if sub.empty:
            continue
        lines.append(f"- {DIMENSION_LABELS[dim]}:")
        for _, row in sub.iterrows():
            lines.append(
                f"  - {row['family']}, {row['group_label']}: broader-shortlist advantage = {row['frontier_delta_pctK_pp']:+.2f} pp"
            )
    lines.extend(["", "## Top surfaced examples at h=10"])
    for family in ["Path-to-direct", "Direct-to-path"]:
        lines.append(f"- {family}:")
        fam = top_examples[top_examples["family"] == family]
        for _, row in fam.iterrows():
            lines.append(
                f"  - #{int(row['surface_rank'])}: {row['u_label']} -> {row['v_label']} (rank gain {int(row['rank_delta'])})"
            )
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    het = prepare_heterogeneity_summary()
    het.to_csv(out / "dual_family_heterogeneity_summary.csv", index=False)
    plot_heterogeneity(het, out / "dual_family_heterogeneity_comparison.png", out / "dual_family_heterogeneity_comparison.pdf")

    frontier = prepare_current_frontier_summary()
    frontier.to_csv(out / "dual_family_current_frontier_summary.csv", index=False)
    plot_current_frontier(frontier, out / "dual_family_current_frontier_summary.png", out / "dual_family_current_frontier_summary.pdf")

    examples = prepare_top_examples()
    examples.to_csv(out / "dual_family_current_frontier_examples_h10.csv", index=False)

    write_summary_note(het, frontier, examples, out / "summary.md")


if __name__ == "__main__":
    main()
