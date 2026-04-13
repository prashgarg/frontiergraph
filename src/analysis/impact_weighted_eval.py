from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map, paired_bootstrap_delta, restrict_positive_set_for_family
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    comparison_rankings_for_cutoff,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
)
from src.utils import load_config, load_corpus


def _future_novel_weight_map(
    edge_year_counts: pd.DataFrame,
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> dict[tuple[str, str], float]:
    positives = {
        edge
        for edge, y in first_year_map.items()
        if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)
    }
    if not positives:
        return {}
    win = edge_year_counts[
        (edge_year_counts["year"] >= int(cutoff_t)) & (edge_year_counts["year"] <= int(cutoff_t + horizon_h))
    ].copy()
    if win.empty:
        return {e: 1.0 for e in positives}
    win["edge"] = list(zip(win["src_code"].astype(str), win["dst_code"].astype(str)))
    agg = win[win["edge"].isin(positives)].groupby("edge", as_index=False).agg(freq=("paper_count", "sum"))
    out: dict[tuple[str, str], float] = {}
    for row in agg.itertuples(index=False):
        # Compress tail influence while preserving impact ordering.
        out[(str(row.edge[0]), str(row.edge[1]))] = float(1.0 + math.log1p(float(row.freq)))
    for e in positives:
        out.setdefault(e, 1.0)
    return out


def evaluate_weighted_ranking(
    ranked_df: pd.DataFrame,
    weight_map: dict[tuple[str, str], float],
    k_values: list[int],
) -> dict[str, float]:
    rank_map = {(str(r.u), str(r.v)): int(i + 1) for i, r in enumerate(ranked_df[["u", "v"]].itertuples(index=False))}
    total_w = float(sum(weight_map.values()))
    denom = total_w if total_w > 0 else 1.0
    out: dict[str, float] = {"n_weighted_positives": float(len(weight_map)), "total_positive_weight": total_w}

    rr = [float(w) / float(rank_map[e]) if e in rank_map else 0.0 for e, w in weight_map.items()]
    out["weighted_mrr"] = float(sum(rr) / denom) if rr else 0.0

    weights_sorted = sorted(weight_map.values(), reverse=True)
    for k in k_values:
        k = int(k)
        hits_w = sum(float(w) for e, w in weight_map.items() if rank_map.get(e, np.inf) <= k)
        out[f"weighted_recall_at_{k}"] = float(hits_w) / denom
        top_edges = [(e, rank_map[e], float(weight_map[e])) for e in weight_map if e in rank_map and rank_map[e] <= k]
        dcg = sum(w / math.log2(r + 1) for _e, r, w in top_edges)
        ideal = sum(float(w) / math.log2(i + 2) for i, w in enumerate(weights_sorted[:k]))
        out[f"ndcg_at_{k}"] = float(dcg / ideal) if ideal > 0 else 0.0
    return out


def compute_impact_panel(
    corpus_df: pd.DataFrame,
    cfg: dict,
    cutoff_years: list[int],
    horizons: list[int],
    k_values: list[int],
) -> pd.DataFrame:
    if corpus_df.empty:
        return pd.DataFrame()
    edge_year_counts = (
        corpus_df.groupby(["src_code", "dst_code", "year"], as_index=False)
        .agg(paper_count=("paper_id", "nunique"))
        .astype({"src_code": str, "dst_code": str})
    )
    tau = int(cfg.get("features", {}).get("tau", 2))
    candidate_cfg = candidate_cfg_from_config(cfg)
    first_year = first_appearance_map(
        corpus_df,
        candidate_kind=candidate_cfg.candidate_kind,
        candidate_family_mode=candidate_cfg.candidate_family_mode,
    )

    rows: list[dict] = []
    for t in cutoff_years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        if train.empty:
            continue
        rankings = comparison_rankings_for_cutoff(train, cutoff_t=int(t), cfg=candidate_cfg, tau=tau)
        main_universe = rankings.get("main", pd.DataFrame(columns=["u", "v"]))
        for h in horizons:
            wmap = _future_novel_weight_map(edge_year_counts, first_year, cutoff_t=int(t), horizon_h=int(h))
            if wmap:
                kept = restrict_positive_set_for_family(
                    set(wmap.keys()),
                    candidate_pairs_df=main_universe,
                    candidate_family_mode=candidate_cfg.candidate_family_mode,
                )
                wmap = {edge: weight for edge, weight in wmap.items() if edge in kept}
            if not wmap:
                continue
            positives = set(wmap.keys())
            for model, ranking in rankings.items():
                if ranking.empty:
                    continue
                base = evaluate_binary_ranking(ranking, positives=positives, k_values=k_values)
                wmetrics = evaluate_weighted_ranking(ranking, weight_map=wmap, k_values=k_values)
                row = {
                    "model": model,
                    "cutoff_year_t": int(t),
                    "horizon": int(h),
                    "n_positives": int(base.get("n_positives", 0)),
                    "total_positive_weight": float(wmetrics.get("total_positive_weight", 0.0)),
                    "mrr": float(base.get("mrr", 0.0)),
                    "weighted_mrr": float(wmetrics.get("weighted_mrr", 0.0)),
                }
                for k in k_values:
                    row[f"recall_at_{k}"] = float(base.get(f"recall_at_{k}", 0.0))
                    row[f"weighted_recall_at_{k}"] = float(wmetrics.get(f"weighted_recall_at_{k}", 0.0))
                    row[f"ndcg_at_{k}"] = float(wmetrics.get(f"ndcg_at_{k}", 0.0))
                rows.append(row)
    return pd.DataFrame(rows)


def summarize_impact_panel(panel_df: pd.DataFrame, k_values: list[int]) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    agg_cols = {
        "mrr": "mean",
        "weighted_mrr": "mean",
        "n_positives": "mean",
        "total_positive_weight": "mean",
    }
    for k in k_values:
        agg_cols[f"recall_at_{k}"] = "mean"
        agg_cols[f"weighted_recall_at_{k}"] = "mean"
        agg_cols[f"ndcg_at_{k}"] = "mean"
    out = panel_df.groupby(["model", "horizon"], as_index=False).agg(agg_cols)
    out["lift_weighted_mrr_over_mrr"] = out["weighted_mrr"] / out["mrr"].replace(0.0, np.nan)
    for k in k_values:
        out[f"lift_weighted_recall_over_recall_at_{k}"] = out[f"weighted_recall_at_{k}"] / out[
            f"recall_at_{k}"
        ].replace(0.0, np.nan)
    return out.sort_values(["horizon", "weighted_mrr"], ascending=[True, False]).reset_index(drop=True)


def impact_significance(
    panel_df: pd.DataFrame,
    k_values: list[int],
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for horizon in sorted(panel_df["horizon"].unique()):
        m = panel_df[(panel_df["model"] == "main") & (panel_df["horizon"] == horizon)]
        p = panel_df[(panel_df["model"] == "pref_attach") & (panel_df["horizon"] == horizon)]
        if m.empty or p.empty:
            continue
        join = m.merge(p, on=["cutoff_year_t", "horizon"], suffixes=("_main", "_pref"), how="inner")
        if join.empty:
            continue
        metrics = ["weighted_mrr"] + [f"weighted_recall_at_{k}" for k in k_values] + [f"ndcg_at_{k}" for k in k_values]
        for metric in metrics:
            if f"{metric}_main" not in join.columns or f"{metric}_pref" not in join.columns:
                continue
            delta, lo, hi, pval = paired_bootstrap_delta(
                join[f"{metric}_main"],
                join[f"{metric}_pref"],
                n_boot=n_boot,
                seed=seed,
            )
            rows.append(
                {
                    "horizon": int(horizon),
                    "metric": metric,
                    "model_a": "main",
                    "model_b": "pref_attach",
                    "delta": float(delta),
                    "ci_lo": float(lo),
                    "ci_hi": float(hi),
                    "p_value": float(pval),
                    "n_pairs": int(len(join)),
                }
            )
    return pd.DataFrame(rows)


def plot_impact_frontiers(summary_df: pd.DataFrame, k_values: list[int], out_dir: Path) -> list[Path]:
    out_paths: list[Path] = []
    if summary_df.empty:
        return out_paths
    for horizon in sorted(summary_df["horizon"].unique()):
        sub = summary_df[summary_df["horizon"] == horizon]
        if sub.empty:
            continue
        plt.figure(figsize=(8, 5))
        for model, g in sub.groupby("model"):
            xs = np.array(sorted(k_values), dtype=int)
            ys = np.array([float(g.iloc[0][f"weighted_recall_at_{int(k)}"]) for k in xs], dtype=float)
            plt.plot(xs, ys, marker="o", label=model)
        plt.xscale("log")
        plt.xlabel("K")
        plt.ylabel("Weighted Recall@K")
        plt.title(f"Impact-Weighted Recall Frontier (h={int(horizon)})")
        plt.legend()
        plt.tight_layout()
        p1 = out_dir / f"impact_weighted_recall_frontier_h{int(horizon)}.png"
        plt.savefig(p1, dpi=150)
        plt.close()
        out_paths.append(p1)

        plt.figure(figsize=(8, 5))
        vals = sub.set_index("model")["weighted_mrr"].sort_values(ascending=False)
        vals.plot(kind="bar", color="tab:orange")
        plt.ylabel("Weighted MRR")
        plt.title(f"Weighted MRR by Model (h={int(horizon)})")
        plt.tight_layout()
        p2 = out_dir / f"impact_weighted_mrr_h{int(horizon)}.png"
        plt.savefig(p2, dpi=150)
        plt.close()
        out_paths.append(p2)
    return out_paths


def write_hypothesis_brief(summary_df: pd.DataFrame, sig_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Workstream 08: Impact-Weighted Evaluation",
        "",
        "## Hypotheses",
        "1. Main ranking captures higher-impact future edges better than preferential attachment.",
        "2. Impact-weighted gains can exist even when binary recall gaps are small.",
        "3. NDCG improves if high-impact edges are pulled into top ranks.",
        "",
    ]
    if not summary_df.empty:
        lines.append("## Summary Snapshot")
        for r in summary_df[summary_df["model"] == "main"].sort_values("horizon").itertuples(index=False):
            lines.append(
                f"- h={int(r.horizon)}: weighted_mrr={float(r.weighted_mrr):.6f}, "
                f"mrr={float(r.mrr):.6f}, lift={float(r.lift_weighted_mrr_over_mrr):.2f}x"
            )
        lines.append("")
    if not sig_df.empty:
        key = sig_df[sig_df["metric"] == "weighted_mrr"]
        if not key.empty:
            wins = int((key["delta"] > 0).sum())
            lines.append(f"- Main beats pref_attach on weighted MRR in {wins}/{len(key)} horizons.")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Impact-weighted evaluation of missing-claim rankings.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument("--k_values", type=int, nargs="+", default=[50, 100, 500, 1000])
    parser.add_argument("--n_boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    cfg = load_config(args.config_path)
    candidate_cfg = candidate_cfg_from_config(cfg, best_config_path=args.best_config_path)
    cfg["features"] = dict(cfg.get("features", {}))
    cfg["scoring"] = dict(cfg.get("scoring", {}))
    cfg["filters"] = dict(cfg.get("filters", {}))
    cfg["features"]["tau"] = int(candidate_cfg.tau)
    cfg["features"]["max_path_len"] = int(candidate_cfg.max_path_len)
    cfg["features"]["max_neighbors_per_mediator"] = int(candidate_cfg.max_neighbors_per_mediator)
    cfg["scoring"]["alpha"] = float(candidate_cfg.alpha)
    cfg["scoring"]["beta"] = float(candidate_cfg.beta)
    cfg["scoring"]["gamma"] = float(candidate_cfg.gamma)
    cfg["scoring"]["delta"] = float(candidate_cfg.delta)
    cfg["filters"]["causal_only"] = bool(candidate_cfg.causal_only)
    cfg["filters"]["min_stability"] = candidate_cfg.min_stability

    horizons = parse_horizons(args.horizons, default=[3, 5, 10])
    min_y, max_y = int(corpus_df["year"].min()), int(corpus_df["year"].max())
    years = parse_cutoff_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons), step=1)
    if not years:
        raise SystemExit("No valid cutoff years available for impact-weighted evaluation.")
    k_values = sorted(set(int(k) for k in args.k_values))

    panel = compute_impact_panel(corpus_df, cfg=cfg, cutoff_years=years, horizons=horizons, k_values=k_values)
    summary = summarize_impact_panel(panel, k_values=k_values)
    sig = impact_significance(panel, k_values=k_values, n_boot=args.n_boot, seed=args.seed)
    panel_pq = out_dir / "impact_panel.parquet"
    panel_csv = out_dir / "impact_panel.csv"
    sum_pq = out_dir / "impact_summary.parquet"
    sum_csv = out_dir / "impact_summary.csv"
    sig_pq = out_dir / "impact_significance.parquet"
    sig_csv = out_dir / "impact_significance.csv"

    panel.to_parquet(panel_pq, index=False)
    panel.to_csv(panel_csv, index=False)
    summary.to_parquet(sum_pq, index=False)
    summary.to_csv(sum_csv, index=False)
    sig.to_parquet(sig_pq, index=False)
    sig.to_csv(sig_csv, index=False)

    figs: list[Path] = []
    try:
        figs = plot_impact_frontiers(summary, k_values=k_values, out_dir=out_dir)
    except Exception as exc:
        print(f"Warning: failed to render impact-weighted figures: {exc}")

    brief = out_dir / "hypotheses_and_tasks.md"
    try:
        write_hypothesis_brief(summary, sig, brief)
    except Exception as exc:
        print(f"Warning: failed to write impact-weighted brief: {exc}")

    print(f"Wrote: {panel_pq}")
    print(f"Wrote: {panel_csv}")
    print(f"Wrote: {sum_pq}")
    print(f"Wrote: {sum_csv}")
    print(f"Wrote: {sig_pq}")
    print(f"Wrote: {sig_csv}")
    if brief.exists():
        print(f"Wrote: {brief}")
    for f in figs:
        print(f"Wrote figure: {f}")


if __name__ == "__main__":
    main()
