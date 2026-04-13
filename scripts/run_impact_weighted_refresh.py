from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map, paired_bootstrap_delta
from src.analysis.impact_weighted_eval import _future_novel_weight_map, evaluate_weighted_ranking
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking
from src.utils import load_config, load_corpus


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ensure_output_dir(ROOT / "outputs/paper/136_value_weighted_refresh")
PAPER_DIR = ROOT / "paper"

CORPUS_PATH = ROOT / "data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet"
CONFIG_PATH = ROOT / "config/config_causalclaims.yaml"
BEST_CONFIG_PATH = ROOT / "outputs/paper/69_v2_2_effective_model_search/best_config.yaml"
PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"

REPORT_CUTOFFS = {
    5: [1990, 1995, 2000, 2005, 2010, 2015],
    10: [1990, 1995, 2000, 2005, 2010, 2015],
    15: [1990, 1995, 2000, 2005, 2010],
}
MAIN_HORIZONS = [5, 10, 15]
K_VALUES = [50, 100, 500, 1000]

PLOT_MODELS = {
    "main": ("Transparent graph score", "#4393c3", "-"),
    "pref_attach": ("Preferential attachment", "#b2182b", "--"),
}


def build_impact_panel(corpus_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    benchmark_panel = pd.read_parquet(
        PANEL_PATH,
        columns=[
            "u",
            "v",
            "cutoff_year_t",
            "horizon",
            "transparent_rank",
            "transparent_score",
            "score",
            "support_degree_product_raw",
        ],
    ).copy()
    benchmark_panel["graph_score"] = (
        pd.to_numeric(benchmark_panel["transparent_score"], errors="coerce")
        .fillna(pd.to_numeric(benchmark_panel["score"], errors="coerce"))
        .fillna(0.0)
        .astype(float)
    )

    edge_year_counts = (
        corpus_df.groupby(["src_code", "dst_code", "year"], as_index=False)
        .agg(paper_count=("paper_id", "nunique"))
        .astype({"src_code": str, "dst_code": str})
    )
    candidate_cfg = candidate_cfg_from_config(cfg, best_config_path=BEST_CONFIG_PATH)
    first_year = first_appearance_map(
        corpus_df,
        candidate_kind=candidate_cfg.candidate_kind,
        candidate_family_mode=candidate_cfg.candidate_family_mode,
    )
    rows: list[dict[str, float | int | str]] = []

    for horizon, cutoffs in REPORT_CUTOFFS.items():
        for cutoff_t in cutoffs:
            cutoff_df = benchmark_panel[
                (benchmark_panel["horizon"] == int(horizon)) & (benchmark_panel["cutoff_year_t"] == int(cutoff_t))
            ].copy()
            if cutoff_df.empty:
                continue

            weight_map = _future_novel_weight_map(
                edge_year_counts=edge_year_counts,
                first_year_map=first_year,
                cutoff_t=int(cutoff_t),
                horizon_h=int(horizon),
            )
            if not weight_map:
                continue

            universe = set(zip(cutoff_df["u"].astype(str), cutoff_df["v"].astype(str)))
            weight_map = {edge: weight for edge, weight in weight_map.items() if edge in universe}
            if not weight_map:
                continue

            positives = set(weight_map.keys())
            rankings = {
                "main": cutoff_df.sort_values(["transparent_rank", "u", "v"], ascending=[True, True, True])[["u", "v"]].copy(),
                "pref_attach": cutoff_df.sort_values(
                    ["support_degree_product_raw", "u", "v"], ascending=[False, True, True]
                )[["u", "v"]].copy(),
            }
            for model, ranking in rankings.items():
                binary_metrics = evaluate_binary_ranking(ranking, positives=positives, k_values=K_VALUES)
                weighted_metrics = evaluate_weighted_ranking(ranking, weight_map=weight_map, k_values=K_VALUES)
                row = {
                    "model": model,
                    "cutoff_year_t": int(cutoff_t),
                    "horizon": int(horizon),
                    "n_positives": int(binary_metrics.get("n_positives", 0)),
                    "total_positive_weight": float(weighted_metrics.get("total_positive_weight", 0.0)),
                    "mrr": float(binary_metrics.get("mrr", 0.0)),
                    "weighted_mrr": float(weighted_metrics.get("weighted_mrr", 0.0)),
                }
                for k in K_VALUES:
                    row[f"recall_at_{k}"] = float(binary_metrics.get(f"recall_at_{k}", 0.0))
                    row[f"weighted_recall_at_{k}"] = float(weighted_metrics.get(f"weighted_recall_at_{k}", 0.0))
                rows.append(row)

    return pd.DataFrame(rows)


def summarize(panel: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "mrr": "mean",
        "weighted_mrr": "mean",
        "n_positives": "mean",
        "total_positive_weight": "mean",
    }
    for k in K_VALUES:
        agg[f"recall_at_{k}"] = "mean"
        agg[f"weighted_recall_at_{k}"] = "mean"
    summary = (
        panel.groupby(["model", "horizon"], as_index=False)
        .agg(agg)
        .sort_values(["horizon", "weighted_mrr"], ascending=[True, False])
        .reset_index(drop=True)
    )
    summary["lift_weighted_mrr_over_mrr"] = summary["weighted_mrr"] / summary["mrr"].replace(0.0, np.nan)
    for k in K_VALUES:
        summary[f"lift_weighted_recall_over_recall_at_{k}"] = summary[f"weighted_recall_at_{k}"] / summary[
            f"recall_at_{k}"
        ].replace(0.0, np.nan)
    return summary


def significance(panel: pd.DataFrame, n_boot: int = 1000, seed: int = 42) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for horizon in MAIN_HORIZONS:
        main = panel[(panel["model"] == "main") & (panel["horizon"] == horizon)]
        pref = panel[(panel["model"] == "pref_attach") & (panel["horizon"] == horizon)]
        joined = main.merge(pref, on=["cutoff_year_t", "horizon"], suffixes=("_main", "_pref"), how="inner")
        if joined.empty:
            continue
        metrics = ["weighted_mrr"] + [f"weighted_recall_at_{k}" for k in K_VALUES]
        for metric in metrics:
            delta, lo, hi, pval = paired_bootstrap_delta(
                joined[f"{metric}_main"],
                joined[f"{metric}_pref"],
                n_boot=n_boot,
                seed=seed,
            )
            rows.append(
                {
                    "horizon": int(horizon),
                    "metric": metric,
                    "delta_main_minus_pref": float(delta),
                    "ci_lo": float(lo),
                    "ci_hi": float(hi),
                    "p_value": float(pval),
                    "n_pairs": int(len(joined)),
                }
            )
    return pd.DataFrame(rows)


def plot_main_figure(summary: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
        }
    )
    fig = plt.figure(figsize=(14.6, 5.0))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.1, 1.25, 1.25, 1.25])

    ax0 = fig.add_subplot(gs[0, 0])
    bar = summary[summary["model"].isin(PLOT_MODELS.keys())].copy()
    horizons = MAIN_HORIZONS
    x = np.arange(len(horizons))
    width = 0.34
    for offset, model in [(-width / 2, "main"), (width / 2, "pref_attach")]:
        vals = [float(bar[(bar["model"] == model) & (bar["horizon"] == h)]["weighted_mrr"].iloc[0]) for h in horizons]
        label, color, _ = PLOT_MODELS[model]
        ax0.bar(x + offset, vals, width=width, color=color, label=label)
    ax0.set_xticks(x)
    ax0.set_xticklabels([f"h={h}" for h in horizons])
    ax0.set_ylabel("Weighted MRR")
    ax0.set_title("Weighted MRR", fontsize=12)
    ax0.grid(True, axis="y", alpha=0.25)

    for i, horizon in enumerate(horizons, start=1):
        ax = fig.add_subplot(gs[0, i])
        for model, (label, color, linestyle) in PLOT_MODELS.items():
            row = summary[(summary["model"] == model) & (summary["horizon"] == horizon)].iloc[0]
            ys = [float(row[f"weighted_recall_at_{k}"]) for k in K_VALUES]
            ax.plot(K_VALUES, ys, color=color, linestyle=linestyle, marker="o", linewidth=2.2, markersize=5.0, label=label)
        ax.set_xscale("log")
        ax.set_title(f"h = {horizon}", fontsize=12)
        ax.set_xlabel("Shortlist size K")
        ax.grid(True, alpha=0.25)
        if i == 1:
            ax.set_ylabel("Weighted Recall@K")
        ax.tick_params(labelsize=10)

    handles, labels = ax0.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT_DIR / "impact_weighted_main_refreshed.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "impact_weighted_main_refreshed.pdf", bbox_inches="tight")
    fig.savefig(PAPER_DIR / "impact_weighted_main_refreshed.png", dpi=300, bbox_inches="tight")
    fig.savefig(PAPER_DIR / "impact_weighted_main_refreshed.pdf", bbox_inches="tight")
    plt.close(fig)


def write_summary(summary: pd.DataFrame, sig: pd.DataFrame) -> None:
    lines = ["# Impact-Weighted Refresh", ""]
    for horizon in MAIN_HORIZONS:
        hsum = summary[(summary["horizon"] == horizon) & (summary["model"].isin(PLOT_MODELS.keys()))].set_index("model")
        lines.append(f"## Horizon {horizon}")
        for model in ["main", "pref_attach"]:
            label = PLOT_MODELS[model][0]
            row = hsum.loc[model]
            lines.append(
                f"- {label}: weighted_mrr={float(row['weighted_mrr']):.6f}, "
                f"weighted_recall@100={float(row['weighted_recall_at_100']):.4f}, "
                f"weighted_recall@1000={float(row['weighted_recall_at_1000']):.4f}"
            )
        hsig = sig[(sig["horizon"] == horizon) & (sig["metric"] == "weighted_mrr")]
        if not hsig.empty:
            row = hsig.iloc[0]
            lines.append(
                f"- weighted_mrr delta main - pref_attach = {float(row['delta_main_minus_pref']):.6f} "
                f"[{float(row['ci_lo']):.6f}, {float(row['ci_hi']):.6f}]"
            )
        lines.append("")
    lines.append("## Headline interpretation")
    lines.append("- Weighting by later reuse does not mechanically flip the benchmark in favor of the graph score.")
    lines.append("- The weighted strict-rank margin still favors preferential attachment if weighted MRR remains higher.")
    lines.append("- But the weighted frontier can still narrow at broader shortlist sizes if the graph score captures a more comparable share of later-reused links once K expands.")
    (OUT_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    corpus_df = load_corpus(CORPUS_PATH)
    cfg = load_config(CONFIG_PATH)
    panel = build_impact_panel(corpus_df, cfg)
    summary_df = summarize(panel)
    sig_df = significance(panel)

    panel.to_csv(OUT_DIR / "impact_panel.csv", index=False)
    summary_df.to_csv(OUT_DIR / "impact_summary.csv", index=False)
    sig_df.to_csv(OUT_DIR / "impact_significance.csv", index=False)
    plot_main_figure(summary_df)
    write_summary(summary_df, sig_df)


if __name__ == "__main__":
    main()
