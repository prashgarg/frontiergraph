from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.headline_heterogeneity import (
    _bootstrap_mean_ci_fast,
    _cutoff_period_label,
    _pct_label_from_suffix,
    _pct_suffix,
    build_first_edge_metadata,
    maybe_write_top_funder_appendix,
    plot_funding_source_interaction,
    plot_method_forest,
    plot_pooled_frontier,
    plot_time_heatmap,
)


FIXED_K_VALUES = [10, 50, 100, 500, 1000]
PCT_K_VALUES = [0.01, 0.02, 0.05, 0.10]
MAIN_HORIZONS = [5, 10, 15]
APPENDIX_HORIZONS = [20]
KEEP_DIMENSIONS = [
    "overall",
    "cutoff_period",
    "first_source",
    "first_method_group",
    "first_has_grant",
    "first_has_grant x first_source",
    "first_funder_group",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh retained heterogeneity figures on the current historical benchmark panel."
    )
    parser.add_argument(
        "--panel",
        default="outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet",
        dest="panel_path",
    )
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument(
        "--paper-meta",
        default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet",
        dest="paper_meta_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _prepare_panel(panel_df: pd.DataFrame) -> pd.DataFrame:
    df = panel_df.copy()
    df["cutoff_year_t"] = pd.to_numeric(df["cutoff_year_t"], errors="coerce").astype("Int64")
    df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce").astype("Int64")
    df = df[df["cutoff_year_t"].notna() & df["horizon"].notna()].copy()
    df["cutoff_year_t"] = df["cutoff_year_t"].astype(int)
    df["horizon"] = df["horizon"].astype(int)
    df = df[df["horizon"].isin(MAIN_HORIZONS)].copy()
    df = df[df["cutoff_year_t"].between(1990, 2015)].copy()
    df["cutoff_period"] = df["cutoff_year_t"].map(_cutoff_period_label)
    df["appears_within_h"] = pd.to_numeric(df["appears_within_h"], errors="coerce").fillna(0).astype(int)
    df["transparent_rank"] = pd.to_numeric(df["transparent_rank"], errors="coerce")
    df["support_degree_product_raw"] = pd.to_numeric(df["support_degree_product_raw"], errors="coerce").fillna(-np.inf)
    df["pref_attach_rank"] = (
        df.groupby(["cutoff_year_t", "horizon"])["support_degree_product_raw"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    df["panel_kind"] = "pooled"
    return df


def _merge_first_edge_metadata(panel_df: pd.DataFrame, corpus_path: Path, paper_meta_path: Path) -> pd.DataFrame:
    corpus_df = pd.read_parquet(corpus_path)
    paper_meta_df = pd.read_parquet(paper_meta_path)
    edge_meta_df = build_first_edge_metadata(corpus_df, paper_meta_df, candidate_kind="directed_causal")
    keep_cols = [
        "u",
        "v",
        "first_source",
        "first_method_group",
        "first_has_grant",
        "first_funder_group",
    ]
    merged = panel_df.merge(edge_meta_df[keep_cols], on=["u", "v"], how="left")
    merged["first_source"] = merged["first_source"].fillna("Unknown")
    merged["first_method_group"] = merged["first_method_group"].fillna("Unknown")
    merged["first_has_grant"] = merged["first_has_grant"].fillna("Unknown")
    merged["first_funder_group"] = merged["first_funder_group"].fillna("Other/Unknown")
    merged["first_has_grant x first_source"] = (
        merged["first_has_grant"].astype(str) + " | " + merged["first_source"].astype(str)
    )
    return merged


def _group_values(df: pd.DataFrame, dimension: str) -> pd.Series:
    if dimension == "overall":
        return pd.Series(["All"] * len(df), index=df.index, dtype=object)
    return df[dimension].astype(str)


def _group_parts(dimension: str, group_value: str) -> tuple[str | None, str | None]:
    if " x " not in dimension:
        return None, None
    parts = str(group_value).split(" | ", 1)
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def _metric_block(ranks: pd.Series, positives: pd.Series, universe_n: int) -> dict[str, float]:
    pos_ranks = pd.to_numeric(ranks[positives.astype(bool)], errors="coerce")
    pos_ranks = pos_ranks[np.isfinite(pos_ranks)]
    n_pos = int(positives.sum())
    out: dict[str, float] = {
        "n_positives": float(n_pos),
        "n_candidates": float(universe_n),
        "mrr": float((1.0 / pos_ranks).mean()) if len(pos_ranks) else 0.0,
    }
    for k in FIXED_K_VALUES:
        hits = int((pos_ranks <= k).sum())
        out[f"hits_at_{k}"] = float(hits)
        out[f"recall_at_{k}"] = float(hits) / float(max(1, n_pos))
    for p in PCT_K_VALUES:
        suffix = _pct_suffix(p)
        k = max(10, int(np.ceil(float(p) * max(1, universe_n))))
        hits = int((pos_ranks <= k).sum())
        out[f"k_at_{suffix}"] = float(k)
        out[f"hits_at_{suffix}"] = float(hits)
        out[f"recall_at_{suffix}"] = float(hits) / float(max(1, n_pos))
    return out


def build_compare_panel(panel_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (cutoff_t, horizon), cell in panel_df.groupby(["cutoff_year_t", "horizon"], sort=True):
        universe_n = int(len(cell))
        for dimension in KEEP_DIMENSIONS:
            group_values = _group_values(cell, dimension)
            for group_value, sub in cell.assign(_group=group_values).groupby("_group", dropna=False):
                positives = sub["appears_within_h"].astype(bool)
                if int(positives.sum()) == 0:
                    continue
                left, right = _group_parts(dimension, str(group_value))
                main_metrics = _metric_block(sub["transparent_rank"], positives, universe_n)
                pref_metrics = _metric_block(sub["pref_attach_rank"], positives, universe_n)
                rec: dict[str, object] = {
                    "panel_kind": "pooled",
                    "cutoff_year_t": int(cutoff_t),
                    "cutoff_period": _cutoff_period_label(int(cutoff_t)),
                    "horizon": int(horizon),
                    "dimension": str(dimension),
                    "group": str(group_value),
                    "group_left": left,
                    "group_right": right,
                    "n_group_edges": int(positives.sum()),
                    "total_future_edges_all": int(cell["appears_within_h"].sum()),
                    "n_candidates": int(universe_n),
                    "mrr_main": float(main_metrics["mrr"]),
                    "mrr_pref": float(pref_metrics["mrr"]),
                }
                rec["delta_mrr"] = rec["mrr_main"] - rec["mrr_pref"]
                rec["relative_advantage_mrr"] = (
                    (rec["mrr_main"] / rec["mrr_pref"]) - 1.0 if rec["mrr_pref"] > 0 else np.nan
                )
                for k in FIXED_K_VALUES:
                    rec[f"hits_at_{k}_main"] = float(main_metrics[f"hits_at_{k}"])
                    rec[f"hits_at_{k}_pref"] = float(pref_metrics[f"hits_at_{k}"])
                    rec[f"recall_at_{k}_main"] = float(main_metrics[f"recall_at_{k}"])
                    rec[f"recall_at_{k}_pref"] = float(pref_metrics[f"recall_at_{k}"])
                    rec[f"delta_hits_at_{k}"] = rec[f"hits_at_{k}_main"] - rec[f"hits_at_{k}_pref"]
                    rec[f"delta_recall_at_{k}"] = rec[f"recall_at_{k}_main"] - rec[f"recall_at_{k}_pref"]
                    rec[f"relative_advantage_at_{k}"] = (
                        (rec[f"recall_at_{k}_main"] / rec[f"recall_at_{k}_pref"]) - 1.0
                        if rec[f"recall_at_{k}_pref"] > 0
                        else np.nan
                    )
                pct_deltas: list[float] = []
                for p in PCT_K_VALUES:
                    suffix = _pct_suffix(p)
                    rec[f"k_at_{suffix}_main"] = float(main_metrics[f"k_at_{suffix}"])
                    rec[f"k_at_{suffix}_pref"] = float(pref_metrics[f"k_at_{suffix}"])
                    rec[f"hits_at_{suffix}_main"] = float(main_metrics[f"hits_at_{suffix}"])
                    rec[f"hits_at_{suffix}_pref"] = float(pref_metrics[f"hits_at_{suffix}"])
                    rec[f"recall_at_{suffix}_main"] = float(main_metrics[f"recall_at_{suffix}"])
                    rec[f"recall_at_{suffix}_pref"] = float(pref_metrics[f"recall_at_{suffix}"])
                    rec[f"delta_hits_at_{suffix}"] = rec[f"hits_at_{suffix}_main"] - rec[f"hits_at_{suffix}_pref"]
                    rec[f"delta_recall_at_{suffix}"] = rec[f"recall_at_{suffix}_main"] - rec[f"recall_at_{suffix}_pref"]
                    rec[f"relative_advantage_at_{suffix}"] = (
                        (rec[f"recall_at_{suffix}_main"] / rec[f"recall_at_{suffix}_pref"]) - 1.0
                        if rec[f"recall_at_{suffix}_pref"] > 0
                        else np.nan
                    )
                    pct_deltas.append(float(rec[f"delta_recall_at_{suffix}"]))
                rec["frontier_delta_fixedK"] = float(np.mean([rec[f"delta_recall_at_{k}"] for k in FIXED_K_VALUES]))
                rec["frontier_delta_pctK"] = float(np.mean(pct_deltas))
                rows.append(rec)
    return pd.DataFrame(rows)


def build_frontier_summary(compare_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    key_cols = ["panel_kind", "dimension", "group", "group_left", "group_right", "horizon"]
    for keys, g in compare_df.groupby(key_cols, dropna=False):
        rec: dict[str, object] = dict(zip(key_cols, keys))
        rec["n_cutoffs"] = int(g["cutoff_year_t"].nunique())
        rec["total_group_edges"] = int(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).sum())
        rec["mean_group_edges"] = float(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).mean())
        rec["mean_total_future_edges"] = float(pd.to_numeric(g["total_future_edges_all"], errors="coerce").fillna(0).mean())
        rec["mean_n_candidates"] = float(pd.to_numeric(g["n_candidates"], errors="coerce").fillna(0).mean())
        rec["display_ok_1d"] = bool(rec["total_group_edges"] >= 500 and rec["n_cutoffs"] >= 3)
        rec["display_ok_2d"] = bool(rec["total_group_edges"] >= 250 and rec["n_cutoffs"] >= 2)
        rec["mrr_main"] = float(pd.to_numeric(g["mrr_main"], errors="coerce").fillna(0).mean())
        rec["mrr_pref"] = float(pd.to_numeric(g["mrr_pref"], errors="coerce").fillna(0).mean())
        rec["delta_mrr"] = float(pd.to_numeric(g["delta_mrr"], errors="coerce").fillna(0).mean())
        rec["relative_advantage_mrr"] = float(
            pd.to_numeric(g["relative_advantage_mrr"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean()
        )
        for k in FIXED_K_VALUES:
            for prefix in ["hits_at", "recall_at"]:
                rec[f"{prefix}_{k}_main"] = float(pd.to_numeric(g[f"{prefix}_{k}_main"], errors="coerce").fillna(0).mean())
                rec[f"{prefix}_{k}_pref"] = float(pd.to_numeric(g[f"{prefix}_{k}_pref"], errors="coerce").fillna(0).mean())
            rec[f"delta_hits_at_{k}"] = float(pd.to_numeric(g[f"delta_hits_at_{k}"], errors="coerce").fillna(0).mean())
            rec[f"delta_recall_at_{k}"] = float(pd.to_numeric(g[f"delta_recall_at_{k}"], errors="coerce").fillna(0).mean())
            rec[f"relative_advantage_at_{k}"] = float(
                pd.to_numeric(g[f"relative_advantage_at_{k}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean()
            )
        for p in PCT_K_VALUES:
            suffix = _pct_suffix(p)
            rec[f"recall_at_{suffix}_main"] = float(pd.to_numeric(g[f"recall_at_{suffix}_main"], errors="coerce").fillna(0).mean())
            rec[f"recall_at_{suffix}_pref"] = float(pd.to_numeric(g[f"recall_at_{suffix}_pref"], errors="coerce").fillna(0).mean())
            rec[f"delta_recall_at_{suffix}"] = float(pd.to_numeric(g[f"delta_recall_at_{suffix}"], errors="coerce").fillna(0).mean())
            rec[f"relative_advantage_at_{suffix}"] = float(
                pd.to_numeric(g[f"relative_advantage_at_{suffix}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean()
            )
            rec[f"k_at_{suffix}_main"] = float(pd.to_numeric(g[f"k_at_{suffix}_main"], errors="coerce").fillna(0).mean())
            rec[f"k_at_{suffix}_pref"] = float(pd.to_numeric(g[f"k_at_{suffix}_pref"], errors="coerce").fillna(0).mean())
        rec["frontier_delta_fixedK"] = float(pd.to_numeric(g["frontier_delta_fixedK"], errors="coerce").fillna(0).mean())
        rec["frontier_delta_pctK"] = float(pd.to_numeric(g["frontier_delta_pctK"], errors="coerce").fillna(0).mean())
        _, lo, hi = _bootstrap_mean_ci_fast(pd.to_numeric(g["frontier_delta_pctK"], errors="coerce").fillna(0), n_boot=500, seed=42)
        rec["frontier_delta_pctK_ci_lo"] = lo
        rec["frontier_delta_pctK_ci_hi"] = hi
        _, lo, hi = _bootstrap_mean_ci_fast(pd.to_numeric(g["delta_recall_at_100"], errors="coerce").fillna(0), n_boot=500, seed=42)
        rec["delta_recall_at_100_ci_lo"] = lo
        rec["delta_recall_at_100_ci_hi"] = hi
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(["dimension", "group", "horizon"]).reset_index(drop=True)


def write_summary_md(frontier_summary: pd.DataFrame, out_path: Path) -> None:
    pooled = frontier_summary[(frontier_summary["dimension"] == "overall") & (frontier_summary["group"] == "All")]
    method = frontier_summary[frontier_summary["dimension"] == "first_method_group"]
    source = frontier_summary[frontier_summary["dimension"] == "first_source"]
    funding = frontier_summary[frontier_summary["dimension"] == "first_has_grant"]
    lines = ["# Benchmark-Panel Heterogeneity Refresh", ""]
    if not pooled.empty:
        lines.append("## Overall frontier")
        for row in pooled.sort_values("horizon").itertuples(index=False):
            vals = []
            for p in PCT_K_VALUES:
                suffix = _pct_suffix(p)
                vals.append(f"{_pct_label_from_suffix(suffix)}={float(getattr(row, f'relative_advantage_at_{suffix}', np.nan))*100:+.1f}%")
            lines.append(f"- h={int(row.horizon)}: " + ", ".join(vals))
        lines.append("")
    if not source.empty:
        lines.append("## Journal tier")
        for row in source[source["group"].isin(["core", "adjacent"])].sort_values(["horizon", "group"]).itertuples(index=False):
            lines.append(f"- {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}")
        lines.append("")
    if not method.empty:
        lines.append("## Method family")
        for row in method[method["display_ok_1d"]].sort_values(["horizon", "frontier_delta_pctK"], ascending=[True, False]).head(9).itertuples(index=False):
            lines.append(f"- {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}")
        lines.append("")
    if not funding.empty:
        lines.append("## Coarse funding split")
        for row in funding[funding["group"].isin(["Funded", "Unfunded"])].sort_values(["horizon", "group"]).itertuples(index=False):
            lines.append(f"- {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}")
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    fig_dir = ensure_output_dir(Path(out_dir) / "figures")

    panel_df = pd.read_parquet(args.panel_path)
    panel_df = _prepare_panel(panel_df)
    panel_df = _merge_first_edge_metadata(panel_df, Path(args.corpus_path), Path(args.paper_meta_path))

    compare_df = build_compare_panel(panel_df)
    frontier_summary = build_frontier_summary(compare_df)

    panel_df.to_parquet(Path(out_dir) / "panel_with_groups.parquet", index=False)
    panel_df.to_csv(Path(out_dir) / "panel_with_groups.csv", index=False)
    compare_df.to_parquet(Path(out_dir) / "compare_panel.parquet", index=False)
    compare_df.to_csv(Path(out_dir) / "compare_panel.csv", index=False)
    frontier_summary.to_parquet(Path(out_dir) / "frontier_summary.parquet", index=False)
    frontier_summary.to_csv(Path(out_dir) / "frontier_summary.csv", index=False)

    plot_pooled_frontier(frontier_summary, pct_k_values=PCT_K_VALUES, out_path=fig_dir / "pooled_frontier_main.png", horizons=MAIN_HORIZONS)
    plot_time_heatmap(frontier_summary, out_path=fig_dir / "time_period_heatmap_main.png", horizons=MAIN_HORIZONS)
    plot_funding_source_interaction(frontier_summary, out_path=fig_dir / "funding_source_interaction_main.png", horizons=MAIN_HORIZONS)
    plot_method_forest(frontier_summary, out_path=fig_dir / "method_theory_forest_main.png", horizons=MAIN_HORIZONS)
    maybe_write_top_funder_appendix(frontier_summary, out_dir=Path(out_dir), main_horizons=MAIN_HORIZONS)
    write_summary_md(frontier_summary, Path(out_dir) / "summary.md")

    print(f"Wrote: {Path(out_dir) / 'frontier_summary.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'summary.md'}")


if __name__ == "__main__":
    main()
