from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ATTENTION_SUMMARY = ROOT / "outputs" / "paper" / "07_attention_allocation" / "attention_summary.csv"
IMPACT_SUMMARY = ROOT / "outputs" / "paper" / "08_impact_weighted" / "impact_summary.csv"
CRED_KIND = ROOT / "outputs" / "paper" / "04_credibility" / "edge_quality_by_kind.csv"
CRED_METHOD = ROOT / "outputs" / "paper" / "04_credibility" / "edge_quality_by_method.csv"
CRED_BAND = ROOT / "outputs" / "paper" / "04_credibility" / "edge_quality_by_stability_band.csv"
OUT_DIR = ROOT / "outputs" / "paper" / "14_title_revision"


MODEL_LABELS = {
    "main": "Graph-based score",
    "pref_attach": "Preferential attachment",
}
MODEL_COLORS = {
    "main": "#155e75",
    "pref_attach": "#7c2d12",
}


def _pct(value: float) -> str:
    return f"{100 * float(value):.1f}\\%"


def _fmt_int(value: float) -> str:
    return f"{int(round(float(value))):,}"


def _ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_attention_figure() -> None:
    summary = pd.read_csv(ATTENTION_SUMMARY)
    summary = summary[
        summary["model"].isin(["main", "pref_attach"])
        & summary["horizon"].isin([3, 5, 10])
        & summary["k"].isin([50, 100, 500, 1000])
    ].copy()
    summary.sort_values(["horizon", "model", "k"], inplace=True)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), sharey=True, constrained_layout=True)
    ks = [50, 100, 500, 1000]
    for ax, horizon in zip(axes, [3, 5, 10]):
        horizon_df = summary[summary["horizon"] == horizon]
        for model in ["main", "pref_attach"]:
            model_df = horizon_df[horizon_df["model"] == model].sort_values("k")
            ax.plot(
                model_df["k"],
                model_df["mean_yield_per_100"],
                marker="o",
                linewidth=2.2,
                markersize=5,
                color=MODEL_COLORS[model],
                label=MODEL_LABELS[model],
            )
        ax.set_title(f"Horizon = {horizon} years")
        ax.set_xlabel("Shortlist size K")
        ax.set_xticks(ks)
        ax.grid(axis="y", alpha=0.18, linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("Future links per 100 suggestions")
    axes[-1].legend(frameon=False, loc="upper right")
    fig.savefig(OUT_DIR / "attention_allocation_frontier_main.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def build_impact_figure() -> None:
    summary = pd.read_csv(IMPACT_SUMMARY)
    summary = summary[summary["model"].isin(["main", "pref_attach"])].copy()
    summary.sort_values(["model", "horizon"], inplace=True)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )

    fig = plt.figure(figsize=(11.8, 5.4), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, width_ratios=[1.0, 1.35], wspace=0.28, hspace=0.28)

    ax_left = fig.add_subplot(grid[:, 0])
    for model in ["main", "pref_attach"]:
        model_df = summary[summary["model"] == model].sort_values("horizon")
        ax_left.plot(
            model_df["horizon"],
            model_df["weighted_mrr"],
            marker="o",
            linewidth=2.2,
            markersize=5,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
        )
    ax_left.set_title("Weighted MRR by horizon")
    ax_left.set_xlabel("Horizon (years)")
    ax_left.set_ylabel("Weighted MRR")
    ax_left.set_xticks([3, 5, 10])
    ax_left.grid(axis="y", alpha=0.18, linewidth=0.8)
    ax_left.spines["top"].set_visible(False)
    ax_left.spines["right"].set_visible(False)
    ax_left.legend(frameon=False, loc="upper right")

    k_labels = [50, 100, 500, 1000]
    for row, horizon in enumerate([3, 5, 10]):
        ax = fig.add_subplot(grid[row, 1])
        horizon_df = summary[summary["horizon"] == horizon]
        for model in ["main", "pref_attach"]:
            model_df = horizon_df[horizon_df["model"] == model].sort_values("horizon")
            values = [
                float(model_df[f"weighted_recall_at_{k}"].iloc[0])
                for k in k_labels
            ]
            ax.plot(
                k_labels,
                values,
                marker="o",
                linewidth=2.0,
                markersize=4.5,
                color=MODEL_COLORS[model],
                label=None,
            )
        ax.set_title(f"Weighted recall frontier, h={horizon}")
        if row == 2:
            ax.set_xlabel("Shortlist size K")
        if row == 1:
            ax.set_ylabel("Weighted recall")
        ax.set_xticks(k_labels)
        ax.grid(axis="y", alpha=0.18, linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.savefig(OUT_DIR / "impact_weighted_main.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def _latex_table_edge_kind(kind_df: pd.DataFrame) -> str:
    rows = []
    order = ["directed_causal", "undirected_noncausal"]
    labels = {
        "directed_causal": "Directed causal",
        "undirected_noncausal": "Undirected contextual",
    }
    kind_df = kind_df.set_index("edge_kind")
    for key in order:
        row = kind_df.loc[key]
        rows.append(
            f"{labels[key]} & {_fmt_int(row['rows'])} & {_fmt_int(row['papers'])} & "
            f"{row['mean_stability']:.3f} & {_pct(row['explicit_causal_share'])} \\\\"
        )
    body = "\n".join(rows)
    return (
        "\\begin{table}[h]\n"
        "  \\caption{Credibility audit by edge kind}\n"
        "  \\label{tab:credibility-kind}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrrr}\n"
        "    \\toprule\n"
        "    Edge kind & Rows & Papers & Mean stability & Explicit-causal share \\\\\n"
        "    \\midrule\n"
        f"    {body}\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )


def _latex_table_method(method_df: pd.DataFrame) -> str:
    method_df = method_df[method_df["edge_kind"] == "directed_causal"].copy()
    method_labels = {
        "panel_FE_or_TWFE": "Panel FE / TWFE",
        "DiD": "Difference-in-differences",
        "experiment": "Experiment",
        "event_study": "Event study",
        "IV": "Instrumental variables",
        "RDD": "Regression discontinuity",
    }
    rows = []
    for key in ["panel_FE_or_TWFE", "DiD", "experiment", "event_study", "IV", "RDD"]:
        row = method_df.loc[method_df["evidence_type"] == key].iloc[0]
        rows.append(
            f"{method_labels[key]} & {_fmt_int(row['rows'])} & {row['mean_stability']:.3f} & "
            f"{_pct(row['explicit_causal_share'])} \\\\"
        )
    body = "\n".join(rows)
    return (
        "\\begin{table}[h]\n"
        "  \\caption{Directed-causal credibility audit by evidence type}\n"
        "  \\label{tab:credibility-method}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrr}\n"
        "    \\toprule\n"
        "    Evidence type & Rows & Mean stability & Explicit-causal share \\\\\n"
        "    \\midrule\n"
        f"    {body}\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )


def _latex_table_stability(band_df: pd.DataFrame) -> str:
    rows = []
    labels = {
        "directed_causal": "Directed causal",
        "undirected_noncausal": "Undirected contextual",
    }
    share_map: dict[str, dict[str, float]] = {}
    for edge_kind, group in band_df.groupby("edge_kind"):
        total = float(group["rows"].sum())
        share_map[edge_kind] = {
            band: float(rows / total)
            for band, rows in zip(group["stability_band"], group["rows"])
        }
    for key in ["directed_causal", "undirected_noncausal"]:
        rows.append(
            f"{labels[key]} & {_pct(share_map[key].get('high', 0.0))} & "
            f"{_pct(share_map[key].get('mid', 0.0))} & {_pct(share_map[key].get('low', 0.0))} \\\\"
        )
    body = "\n".join(rows)
    return (
        "\\begin{table}[h]\n"
        "  \\caption{Stability-band shares by edge kind}\n"
        "  \\label{tab:credibility-stability}\n"
        "  \\centering\n"
        "  \\small\n"
        "  \\begin{tabular}{lrrr}\n"
        "    \\toprule\n"
        "    Edge kind & High stability & Mid stability & Low stability \\\\\n"
        "    \\midrule\n"
        f"    {body}\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )


def build_credibility_tables() -> None:
    kind_df = pd.read_csv(CRED_KIND)
    method_df = pd.read_csv(CRED_METHOD)
    band_df = pd.read_csv(CRED_BAND)
    tex = "\n".join(
        [
            _latex_table_edge_kind(kind_df),
            _latex_table_method(method_df),
            _latex_table_stability(band_df),
        ]
    )
    (OUT_DIR / "credibility_appendix_tables.tex").write_text(tex, encoding="utf-8")

    manifest = {
        "attention_source": str(ATTENTION_SUMMARY.relative_to(ROOT)),
        "impact_source": str(IMPACT_SUMMARY.relative_to(ROOT)),
        "credibility_sources": [
            str(CRED_KIND.relative_to(ROOT)),
            str(CRED_METHOD.relative_to(ROOT)),
            str(CRED_BAND.relative_to(ROOT)),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    _ensure_out_dir()
    build_attention_figure()
    build_impact_figure()
    build_credibility_tables()


if __name__ == "__main__":
    main()
