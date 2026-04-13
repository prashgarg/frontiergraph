from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "paper" / "167_exploratory_testbeds"
OUTDIR = ROOT / "outputs" / "paper" / "181_slides_followon_results"
OUTDIR.mkdir(parents=True, exist_ok=True)


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def build_bundle_figure() -> None:
    summary = pd.read_csv(BASE / "bundle_uptake" / "bundle_uptake_summary.csv")
    family_mix = pd.read_csv(BASE / "bundle_uptake" / "bundle_uptake_family_mix.csv")

    mix_order = [
        "single_direct_to_path",
        "single_path_to_direct",
        "multi_direct_only",
        "multi_path_only",
        "mixed_family",
    ]
    mix_labels = {
        "single_direct_to_path": "Single direct-to-path",
        "single_path_to_direct": "Single path-to-direct",
        "multi_direct_only": "Multi-edge, direct-only",
        "multi_path_only": "Multi-edge, path-only",
        "mixed_family": "Mixed family",
    }
    mix_colors = {
        "single_direct_to_path": "#274c77",
        "single_path_to_direct": "#6096ba",
        "multi_direct_only": "#c58f2f",
        "multi_path_only": "#d8b26e",
        "mixed_family": "#b23a48",
    }

    horizon = 10
    summary_row = summary.loc[summary["horizon"] == horizon].iloc[0]
    mix = (
        family_mix.loc[family_mix["horizon"] == horizon]
        .assign(share=lambda frame: frame["n_papers"] / frame["n_papers"].sum())
        .set_index("family_mix")
        .reindex(mix_order)
        .fillna(0.0)
    )

    fig = plt.figure(figsize=(11.4, 3.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 0.95], wspace=0.34)
    ax_cards = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[0, 1])

    ax_cards.axis("off")
    card_specs = [
        ("Single-edge uptake", pct(1 - float(summary_row["share_multi_edge"]))),
        ("Mixed-family bundles", pct(float(summary_row["share_mixed_family"]))),
        ("Median graph\ndistance", str(int(summary_row["median_min_graph_distance"]))),
    ]

    x_positions = [0.00, 0.34, 0.68]
    for (label, value), xpos in zip(card_specs, x_positions):
        rect = plt.Rectangle(
            (xpos, 0.50),
            0.27,
            0.30,
            transform=ax_cards.transAxes,
            facecolor="#f7f1e8",
            edgecolor="#c8b48a",
            linewidth=1.0,
        )
        ax_cards.add_patch(rect)
        ax_cards.text(
            xpos + 0.02,
            0.66,
            value,
            transform=ax_cards.transAxes,
            fontsize=19,
            fontweight="bold",
            color="#1f2a44",
            va="center",
            ha="left",
        )
        ax_cards.text(
            xpos + 0.02,
            0.57,
            label,
            transform=ax_cards.transAxes,
            fontsize=8.9,
            color="#4a5568",
            va="center",
            ha="left",
        )

    ax_cards.text(
        0.02,
        0.29,
        "At h=10, only about 5.3% of realizing papers absorb more than one\npredicted edge.",
        transform=ax_cards.transAxes,
        fontsize=10.2,
        color="#2d3748",
        ha="left",
        va="center",
    )
    ax_cards.text(
        0.02,
        0.12,
        "When multi-edge uptake occurs, it is usually within the same family\nand within a very local graph neighborhood.",
        transform=ax_cards.transAxes,
        fontsize=10.2,
        color="#2d3748",
        ha="left",
        va="center",
    )

    left = 0.0
    for key in mix_order:
        share = float(mix.loc[key, "share"])
        ax_bar.barh(
            [""],
            [share],
            left=left,
            color=mix_colors[key],
            edgecolor="white",
            linewidth=1.2,
            label=mix_labels[key],
            height=0.42,
        )
        if share >= 0.06:
            ax_bar.text(
                left + share / 2,
                0,
                pct(share),
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
            )
        left += share

    ax_bar.set_xlim(0, 1)
    ax_bar.set_title("Composition of realizing papers at h=10", fontsize=10.5, pad=10)
    ax_bar.set_xlabel("Share of realizing papers", fontsize=10.5)
    ax_bar.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_bar.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=9)
    ax_bar.set_yticks([])
    ax_bar.spines[["top", "right", "left"]].set_visible(False)
    ax_bar.grid(axis="x", color="#d9d9d9", linewidth=0.7, alpha=0.6)
    ax_bar.text(
        0.0,
        -0.30,
        "84.5% single direct-to-path, 10.2% single path-to-direct,\n5.3% multi-edge in total.",
        transform=ax_bar.transAxes,
        fontsize=9.1,
        color="#2d3748",
        ha="left",
        va="top",
    )

    fig.savefig(OUTDIR / "bundle_uptake_slide_summary.pdf", bbox_inches="tight")
    fig.savefig(OUTDIR / "bundle_uptake_slide_summary.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_adopter_figure() -> None:
    df = pd.read_csv(BASE / "adopter_profiles" / "adopter_profile_difference_tests.csv")
    selected = df.loc[df["horizon"] == 10].copy()

    plot_rows = [
        ("Any recorded funder", "has_any_funder", "percentage_point"),
        ("Cross-country team", "cross_country_team", "percentage_point"),
        ("Team size", "team_size", "level"),
        ("Mean career age", "mean_career_age_global", "years"),
    ]
    display = []
    for label, metric, unit in plot_rows:
        row = selected.loc[selected["metric"] == metric].iloc[0]
        display.append(
            {
                "label": label,
                "metric": metric,
                "unit": unit,
                "diff": float(row["difference_path_minus_direct"]),
                "ci_low": float(row["ci_low"]),
                "ci_high": float(row["ci_high"]),
                "path_mean": float(row["path_to_direct_mean"]),
                "direct_mean": float(row["direct_to_path_mean"]),
                "p_display": row["p_display"],
            }
        )
    plot_df = pd.DataFrame(display)
    plot_df["diff_plot"] = plot_df.apply(
        lambda row: row["diff"] * 100 if row["unit"] == "percentage_point" else row["diff"], axis=1
    )
    plot_df["ci_low_plot"] = plot_df.apply(
        lambda row: row["ci_low"] * 100 if row["unit"] == "percentage_point" else row["ci_low"], axis=1
    )
    plot_df["ci_high_plot"] = plot_df.apply(
        lambda row: row["ci_high"] * 100 if row["unit"] == "percentage_point" else row["ci_high"], axis=1
    )

    fig = plt.figure(figsize=(10.6, 4.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.18)
    ax = fig.add_subplot(gs[0, 0])
    ax_note = fig.add_subplot(gs[0, 1])

    y = list(range(len(plot_df)))[::-1]
    colors = ["#b23a48" if value < 0 else "#274c77" for value in plot_df["diff_plot"]]
    for ypos, (_, row), color in zip(y, plot_df.iterrows(), colors):
        ax.plot([row["ci_low_plot"], row["ci_high_plot"]], [ypos, ypos], color=color, linewidth=2.4)
        ax.scatter(row["diff_plot"], ypos, s=58, color=color, zorder=3)
    ax.axvline(0, color="#666666", linewidth=1.0, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"], fontsize=10.5)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.7, alpha=0.6)
    ax.set_xlabel("Path-to-direct minus direct-to-path", fontsize=10.5)

    ax_note.axis("off")
    ax_note.text(
        0.02,
        0.92,
        "At h=10, path-to-direct adopters are:",
        fontsize=12.5,
        fontweight="bold",
        color="#1f2a44",
        ha="left",
        va="top",
        transform=ax_note.transAxes,
    )
    stat_lines = [
        f"• team size: {plot_df.loc[plot_df.metric == 'team_size', 'path_mean'].iloc[0]:.2f} vs {plot_df.loc[plot_df.metric == 'team_size', 'direct_mean'].iloc[0]:.2f} authors ({plot_df.loc[plot_df.metric == 'team_size', 'p_display'].iloc[0]})",
        f"• any funder: {100 * plot_df.loc[plot_df.metric == 'has_any_funder', 'path_mean'].iloc[0]:.1f}% vs {100 * plot_df.loc[plot_df.metric == 'has_any_funder', 'direct_mean'].iloc[0]:.1f}% ({plot_df.loc[plot_df.metric == 'has_any_funder', 'p_display'].iloc[0]})",
        f"• cross-country: {100 * plot_df.loc[plot_df.metric == 'cross_country_team', 'path_mean'].iloc[0]:.1f}% vs {100 * plot_df.loc[plot_df.metric == 'cross_country_team', 'direct_mean'].iloc[0]:.1f}% ({plot_df.loc[plot_df.metric == 'cross_country_team', 'p_display'].iloc[0]})",
        f"• career age: {plot_df.loc[plot_df.metric == 'mean_career_age_global', 'path_mean'].iloc[0]:.1f} vs {plot_df.loc[plot_df.metric == 'mean_career_age_global', 'direct_mean'].iloc[0]:.1f} years ({plot_df.loc[plot_df.metric == 'mean_career_age_global', 'p_display'].iloc[0]})",
    ]
    ypos = 0.78
    for line in stat_lines:
        ax_note.text(
            0.03,
            ypos,
            line,
            fontsize=10.8,
            color="#2d3748",
            ha="left",
            va="top",
            transform=ax_note.transAxes,
        )
        ypos -= 0.17
    ax_note.text(
        0.03,
        0.08,
        "Interpretation: path-to-direct uptake is rarer, but it is more often taken up by larger, funded, and internationally linked teams.",
        fontsize=10.5,
        color="#2d3748",
        ha="left",
        va="bottom",
        transform=ax_note.transAxes,
    )

    fig.savefig(OUTDIR / "adopter_profile_slide_summary.pdf", bbox_inches="tight")
    fig.savefig(OUTDIR / "adopter_profile_slide_summary.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    fig_coef, ax_coef = plt.subplots(figsize=(5.4, 3.8))
    for ypos, (_, row), color in zip(y, plot_df.iterrows(), colors):
        ax_coef.plot([row["ci_low_plot"], row["ci_high_plot"]], [ypos, ypos], color=color, linewidth=2.6)
        ax_coef.scatter(row["diff_plot"], ypos, s=62, color=color, zorder=3)
    ax_coef.axvline(0, color="#666666", linewidth=1.0, linestyle="--")
    ax_coef.set_yticks(y)
    ax_coef.set_yticklabels(plot_df["label"], fontsize=10.5)
    ax_coef.tick_params(axis="x", labelsize=9.5)
    ax_coef.spines[["top", "right", "left"]].set_visible(False)
    ax_coef.grid(axis="x", color="#d9d9d9", linewidth=0.7, alpha=0.6)
    ax_coef.set_xlabel("Path-to-direct minus direct-to-path", fontsize=10.5)
    fig_coef.savefig(OUTDIR / "adopter_profile_coef_only.pdf", bbox_inches="tight")
    fig_coef.savefig(OUTDIR / "adopter_profile_coef_only.png", dpi=220, bbox_inches="tight")
    plt.close(fig_coef)


def main() -> None:
    build_bundle_figure()
    build_adopter_figure()
    print(f"Wrote figures to {OUTDIR}")


if __name__ == "__main__":
    main()
