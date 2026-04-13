from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.attention_allocation import (
    compute_attention_significance,
    compute_attention_summary,
)
from src.analysis.common import ensure_output_dir

PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/134_attention_allocation_refresh"
PAPER_FIG_PNG = ROOT / "paper/attention_allocation_frontier_refreshed.png"
PAPER_FIG_PDF = ROOT / "paper/attention_allocation_frontier_refreshed.pdf"

REPORT_CUTOFFS = [1990, 1995, 2000, 2005, 2010, 2015]
HORIZONS = [5, 10, 15]
K_VALUES = [50, 100, 500, 1000]

MODEL_LABELS = {
    "main": "Transparent graph score",
    "pref_attach": "Preferential attachment",
}
MODEL_COLORS = {
    "main": "#155e75",
    "pref_attach": "#7c2d12",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh attention-allocation frontiers from a historical feature panel.")
    parser.add_argument("--panel", default=str(PANEL_PATH), dest="panel_path")
    parser.add_argument("--out", default=str(OUT_DIR), dest="out_dir")
    parser.add_argument("--paper-fig-png", default="", dest="paper_fig_png")
    parser.add_argument("--paper-fig-pdf", default="", dest="paper_fig_pdf")
    parser.add_argument("--family-label", default="path_to_direct", dest="family_label")
    return parser.parse_args()


def _valid_cutoffs_for_horizon(max_year: int, horizon: int) -> list[int]:
    return [year for year in REPORT_CUTOFFS if int(year) + int(horizon) <= int(max_year)]


def _build_panel_from_historical_panel(panel_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    max_year = 2026
    keep = panel_df[
        [
            "cutoff_year_t",
            "horizon",
            "appears_within_h",
            "transparent_rank",
            "support_degree_product_raw",
        ]
    ].copy()

    for horizon in HORIZONS:
        valid_cutoffs = _valid_cutoffs_for_horizon(max_year=max_year, horizon=horizon)
        sub = keep[(keep["horizon"] == horizon) & (keep["cutoff_year_t"].isin(valid_cutoffs))].copy()
        if sub.empty:
            continue
        sub["pref_attach_rank"] = sub.groupby(["cutoff_year_t", "horizon"])["support_degree_product_raw"].rank(
            method="first",
            ascending=False,
        )
        for cutoff in valid_cutoffs:
            cell = sub[sub["cutoff_year_t"] == cutoff].copy()
            if cell.empty:
                continue
            n_pos = int(cell["appears_within_h"].sum())
            n_missing = int(len(cell))
            for model, rank_col in [("main", "transparent_rank"), ("pref_attach", "pref_attach_rank")]:
                for k in K_VALUES:
                    top = cell[cell[rank_col] <= int(k)]
                    hits = int(top["appears_within_h"].sum())
                    precision = float(hits / float(k))
                    recall = float(hits / max(1, n_pos))
                    random_precision = float(n_pos / n_missing) if n_missing > 0 else np.nan
                    lift = float(precision / random_precision) if random_precision > 0 else np.nan
                    rows.append(
                        {
                            "model": model,
                            "cutoff_year_t": int(cutoff),
                            "horizon": int(horizon),
                            "k": int(k),
                            "n_missing_edges": int(n_missing),
                            "n_future_edges": int(n_pos),
                            "hits_at_k": int(hits),
                            "precision_at_k": precision,
                            "recall_at_k": recall,
                            "mrr": np.nan,
                            "random_precision": random_precision,
                            "lift_vs_random_precision": lift,
                            "yield_per_100_attention": float(100.0 * precision),
                            "source_field_coverage_k": np.nan,
                            "target_field_coverage_k": np.nan,
                            "cross_field_share_k": np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def _plot_frontier(summary_df: pd.DataFrame, out_dir: Path, paper_fig_png: Path | None, paper_fig_pdf: Path | None) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.8), sharey=True, constrained_layout=True)
    for ax, horizon in zip(axes, HORIZONS):
        sub = (
            summary_df[
                summary_df["model"].isin(["main", "pref_attach"])
                & (summary_df["horizon"] == horizon)
                & summary_df["k"].isin(K_VALUES)
            ]
            .copy()
            .sort_values(["model", "k"])
        )
        for model in ["main", "pref_attach"]:
            g = sub[sub["model"] == model].sort_values("k")
            ax.plot(
                g["k"],
                g["mean_yield_per_100"],
                marker="o",
                linewidth=2.2,
                markersize=5,
                color=MODEL_COLORS[model],
                label=MODEL_LABELS[model],
            )
        ax.set_title(f"Horizon = {horizon} years")
        ax.set_xlabel("Shortlist size K")
        ax.set_xticks(K_VALUES)
        ax.grid(axis="y", alpha=0.18, linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("Future links per 100 suggestions")
    axes[-1].legend(frameon=False, loc="upper right")
    if paper_fig_png is not None:
        fig.savefig(paper_fig_png, dpi=240, bbox_inches="tight")
    if paper_fig_pdf is not None:
        fig.savefig(paper_fig_pdf, bbox_inches="tight")
    fig.savefig(out_dir / "attention_allocation_frontier_refreshed.png", dpi=240, bbox_inches="tight")
    fig.savefig(out_dir / "attention_allocation_frontier_refreshed.pdf", bbox_inches="tight")
    plt.close(fig)


def _write_summary(panel_df: pd.DataFrame, summary_df: pd.DataFrame, sig_df: pd.DataFrame, out_dir: Path, family_label: str) -> None:
    key = (
        summary_df[
            summary_df["model"].isin(["main", "pref_attach"])
            & summary_df["k"].isin(K_VALUES)
        ]
        .copy()
        .sort_values(["horizon", "model", "k"])
    )
    rows = []
    for horizon in HORIZONS:
        sub = key[key["horizon"] == horizon]
        if sub.empty:
            continue
        wide = sub.pivot(index="k", columns="model", values="mean_yield_per_100").reset_index()
        wide["delta_main_minus_pref"] = wide["main"] - wide["pref_attach"]
        rows.append(f"## h={horizon}")
        for row in wide.itertuples(index=False):
            rows.append(
                f"- K={int(row.k)}: transparent={float(row.main):.2f}, "
                f"pref={float(row.pref_attach):.2f}, delta={float(row.delta_main_minus_pref):+.2f}"
            )
        rows.append("")
    if not sig_df.empty:
        rows.append("## Paired significance vs preferential attachment")
        for horizon in HORIZONS:
            sub = sig_df[
                (sig_df["metric"] == "precision_at_k")
                & (sig_df["horizon"] == horizon)
                & sig_df["k"].isin(K_VALUES)
            ].sort_values("k")
            for row in sub.itertuples(index=False):
                rows.append(
                    f"- h={int(row.horizon)}, K={int(row.k)}: "
                    f"delta={float(row.delta):+.4f}, p={float(row.p_value):.4f}"
                )
        rows.append("")
    cutoff_counts = (
        panel_df[["horizon", "cutoff_year_t"]]
        .drop_duplicates()
        .groupby("horizon")["cutoff_year_t"]
        .nunique()
        .to_dict()
    )
    rows.append(
        f"Panel rows: {len(panel_df):,}. "
        + "Horizon-valid cutoffs by horizon: "
        + ", ".join(f"h={h}: {int(cutoff_counts.get(h, 0))}" for h in HORIZONS)
    )
    header = f"# Attention Allocation Refresh ({family_label})\n\n"
    (out_dir / "summary.md").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    panel_path = Path(args.panel_path)
    historical_panel = pd.read_parquet(panel_path)
    panel_df = _build_panel_from_historical_panel(historical_panel)
    if panel_df.empty:
        raise SystemExit("No attention-allocation rows were produced.")
    summary_df = compute_attention_summary(panel_df)
    sig_df = compute_attention_significance(panel_df, n_boot=1000, seed=42)

    panel_df.to_parquet(out_dir / "attention_panel.parquet", index=False)
    panel_df.to_csv(out_dir / "attention_panel.csv", index=False)
    summary_df.to_parquet(out_dir / "attention_summary.parquet", index=False)
    summary_df.to_csv(out_dir / "attention_summary.csv", index=False)
    sig_df.to_parquet(out_dir / "attention_significance.parquet", index=False)
    sig_df.to_csv(out_dir / "attention_significance.csv", index=False)

    manifest = {
        "panel_path": str(panel_path.relative_to(ROOT)) if panel_path.is_relative_to(ROOT) else str(panel_path),
        "candidate_family_mode": str(args.family_label),
        "path_to_direct_scope": "broad",
        "report_cutoff_years": REPORT_CUTOFFS,
        "horizons": HORIZONS,
        "k_values": K_VALUES,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paper_fig_png = Path(args.paper_fig_png) if args.paper_fig_png else None
    paper_fig_pdf = Path(args.paper_fig_pdf) if args.paper_fig_pdf else None
    _plot_frontier(summary_df, out_dir=out_dir, paper_fig_png=paper_fig_png, paper_fig_pdf=paper_fig_pdf)
    _write_summary(panel_df, summary_df, sig_df, out_dir=out_dir, family_label=str(args.family_label))
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
