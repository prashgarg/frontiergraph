from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map, paired_bootstrap_delta
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    build_all_pairs,
    cooc_gap_ranking,
    evaluate_binary_ranking,
    main_ranking_for_cutoff,
    parse_cutoff_years,
    parse_horizons,
    pref_attach_ranking,
)
from src.utils import load_config, load_corpus


def _future_novel_edges(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {edge for edge, y in first_year_map.items() if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)}


def compute_attention_panel(
    corpus_df: pd.DataFrame,
    cfg: dict,
    cutoff_years: list[int],
    horizons: list[int],
    k_values: list[int],
) -> pd.DataFrame:
    if corpus_df.empty:
        return pd.DataFrame()
    first_year = first_appearance_map(corpus_df)
    tau = int(cfg.get("features", {}).get("tau", 2))
    candidate_cfg = candidate_cfg_from_config(cfg)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(all_nodes)

    rows: list[dict] = []
    for t in cutoff_years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        if train.empty:
            continue
        rankings = {
            "main": main_ranking_for_cutoff(train, cutoff_t=int(t), cfg=candidate_cfg),
            "cooc_gap": cooc_gap_ranking(train, tau=tau, all_pairs_df=all_pairs),
            "pref_attach": pref_attach_ranking(train, all_pairs_df=all_pairs),
        }
        for h in horizons:
            positives = _future_novel_edges(first_year, cutoff_t=int(t), horizon_h=int(h))
            if not positives:
                continue
            for model, ranking in rankings.items():
                if ranking.empty:
                    continue
                metrics = evaluate_binary_ranking(ranking, positives=positives, k_values=k_values)
                n_missing = float(metrics.get("n_missing_edges", len(ranking)))
                n_pos = float(metrics.get("n_positives", len(positives)))
                random_precision = float(n_pos / n_missing) if n_missing > 0 else np.nan
                for k in k_values:
                    top = ranking.head(int(k)).copy()
                    p = float(metrics.get(f"precision_at_{k}", 0.0))
                    r = float(metrics.get(f"recall_at_{k}", 0.0))
                    lift = float(p / random_precision) if random_precision and random_precision > 0 else np.nan
                    row = {
                        "model": model,
                        "cutoff_year_t": int(t),
                        "horizon": int(h),
                        "k": int(k),
                        "n_missing_edges": int(n_missing),
                        "n_future_edges": int(n_pos),
                        "hits_at_k": int(metrics.get(f"hits_at_{k}", 0.0)),
                        "precision_at_k": p,
                        "recall_at_k": r,
                        "mrr": float(metrics.get("mrr", 0.0)),
                        "random_precision": random_precision,
                        "lift_vs_random_precision": lift,
                        "yield_per_100_attention": float(100.0 * p),
                        "source_field_coverage_k": int(top["u"].astype(str).str[0].nunique()) if not top.empty else 0,
                        "target_field_coverage_k": int(top["v"].astype(str).str[0].nunique()) if not top.empty else 0,
                        "cross_field_share_k": float((top["u"].astype(str).str[0] != top["v"].astype(str).str[0]).mean())
                        if not top.empty
                        else 0.0,
                    }
                    rows.append(row)
    return pd.DataFrame(rows)


def compute_attention_summary(panel_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    out = (
        panel_df.groupby(["model", "horizon", "k"], as_index=False)
        .agg(
            mean_precision=("precision_at_k", "mean"),
            mean_recall=("recall_at_k", "mean"),
            mean_mrr=("mrr", "mean"),
            mean_lift_vs_random=("lift_vs_random_precision", "mean"),
            mean_yield_per_100=("yield_per_100_attention", "mean"),
            mean_source_field_coverage=("source_field_coverage_k", "mean"),
            mean_target_field_coverage=("target_field_coverage_k", "mean"),
            mean_cross_field_share=("cross_field_share_k", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "k", "mean_precision"], ascending=[True, True, False])
    )
    return out


def compute_attention_significance(
    panel_df: pd.DataFrame,
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for horizon in sorted(panel_df["horizon"].unique()):
        for k in sorted(panel_df["k"].unique()):
            m = panel_df[(panel_df["model"] == "main") & (panel_df["horizon"] == horizon) & (panel_df["k"] == k)]
            p = panel_df[
                (panel_df["model"] == "pref_attach") & (panel_df["horizon"] == horizon) & (panel_df["k"] == k)
            ]
            if m.empty or p.empty:
                continue
            joined = m[["cutoff_year_t", "precision_at_k", "recall_at_k"]].merge(
                p[["cutoff_year_t", "precision_at_k", "recall_at_k"]],
                on="cutoff_year_t",
                suffixes=("_main", "_pref"),
                how="inner",
            )
            if joined.empty:
                continue
            for metric in ["precision_at_k", "recall_at_k"]:
                delta, lo, hi, pval = paired_bootstrap_delta(
                    joined[f"{metric}_main"],
                    joined[f"{metric}_pref"],
                    n_boot=n_boot,
                    seed=seed,
                )
                rows.append(
                    {
                        "horizon": int(horizon),
                        "k": int(k),
                        "metric": metric,
                        "model_a": "main",
                        "model_b": "pref_attach",
                        "delta": float(delta),
                        "ci_lo": float(lo),
                        "ci_hi": float(hi),
                        "p_value": float(pval),
                        "n_pairs": int(len(joined)),
                    }
                )
    return pd.DataFrame(rows)


def plot_attention_frontiers(summary_df: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_paths: list[Path] = []
    if summary_df.empty:
        return out_paths
    for horizon in sorted(summary_df["horizon"].unique()):
        sub = summary_df[summary_df["horizon"] == horizon].copy()
        if sub.empty:
            continue
        plt.figure(figsize=(8, 5))
        for model, g in sub.groupby("model"):
            gg = g.sort_values("k")
            plt.plot(gg["k"], gg["mean_precision"], marker="o", label=model)
        plt.xscale("log")
        plt.xlabel("Attention budget K (top-K)")
        plt.ylabel("Mean precision@K")
        plt.title(f"Attention Yield Frontier (h={int(horizon)})")
        plt.legend()
        plt.tight_layout()
        p1 = out_dir / f"attention_precision_frontier_h{int(horizon)}.png"
        plt.savefig(p1, dpi=150)
        plt.close()
        out_paths.append(p1)

        plt.figure(figsize=(8, 5))
        for model, g in sub.groupby("model"):
            gg = g.sort_values("k")
            plt.plot(gg["k"], gg["mean_lift_vs_random"], marker="o", label=model)
        plt.xscale("log")
        plt.xlabel("Attention budget K (top-K)")
        plt.ylabel("Mean lift vs random precision")
        plt.title(f"Attention Lift Frontier (h={int(horizon)})")
        plt.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        plt.legend()
        plt.tight_layout()
        p2 = out_dir / f"attention_lift_frontier_h{int(horizon)}.png"
        plt.savefig(p2, dpi=150)
        plt.close()
        out_paths.append(p2)
    return out_paths


def write_hypothesis_brief(
    summary_df: pd.DataFrame,
    sig_df: pd.DataFrame,
    out_path: Path,
) -> None:
    lines = [
        "# Workstream 07: Attention Allocation Hypotheses",
        "",
        "## Hypotheses",
        "1. At fixed attention budget K, the main model yields higher precision than preferential attachment.",
        "2. The main model preserves or improves field coverage while increasing yield.",
        "3. Lift vs random remains >1 across horizons, indicating non-trivial ranking value in sparse search spaces.",
        "",
        "## Task Outputs",
        "- `attention_panel`: cutoff-level portfolio yield metrics.",
        "- `attention_summary`: mean frontier and diversity profiles.",
        "- `attention_significance`: paired bootstrap deltas vs preferential attachment.",
        "",
    ]
    if not summary_df.empty:
        key = summary_df[(summary_df["model"] == "main") & (summary_df["k"] == 100)].sort_values("horizon")
        if not key.empty:
            lines.append("## Main Model Snapshot (K=100)")
            for r in key.itertuples(index=False):
                lines.append(
                    f"- h={int(r.horizon)}: precision={float(r.mean_precision):.6f}, "
                    f"recall={float(r.mean_recall):.6f}, lift_vs_random={float(r.mean_lift_vs_random):.2f}x"
                )
            lines.append("")
    if not sig_df.empty:
        hit = sig_df[(sig_df["metric"] == "precision_at_k") & (sig_df["k"] == 100)]
        if not hit.empty:
            pass_count = int((hit["delta"] > 0).sum())
            lines.append(
                f"- Main beats pref_attach on precision@100 in {pass_count}/{len(hit)} horizon-level paired comparisons."
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attention-allocation frontier analysis for missing-claim rankings.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="3,5,10,15")
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
    # Lock scoring knobs to selected best configuration.
    cfg["features"]["tau"] = int(candidate_cfg.tau)
    cfg["features"]["max_path_len"] = int(candidate_cfg.max_path_len)
    cfg["features"]["max_neighbors_per_mediator"] = int(candidate_cfg.max_neighbors_per_mediator)
    cfg["scoring"]["alpha"] = float(candidate_cfg.alpha)
    cfg["scoring"]["beta"] = float(candidate_cfg.beta)
    cfg["scoring"]["gamma"] = float(candidate_cfg.gamma)
    cfg["scoring"]["delta"] = float(candidate_cfg.delta)
    cfg["filters"]["causal_only"] = bool(candidate_cfg.causal_only)
    cfg["filters"]["min_stability"] = candidate_cfg.min_stability

    horizons = parse_horizons(args.horizons, default=[3, 5, 10, 15])
    min_y, max_y = int(corpus_df["year"].min()), int(corpus_df["year"].max())
    years = parse_cutoff_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons), step=1)
    if not years:
        raise SystemExit("No valid cutoff years available for attention analysis.")

    panel = compute_attention_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=years,
        horizons=horizons,
        k_values=sorted(set(int(k) for k in args.k_values)),
    )
    summary = compute_attention_summary(panel)
    sig = compute_attention_significance(panel, n_boot=args.n_boot, seed=args.seed)
    figs = plot_attention_frontiers(summary, out_dir=out_dir)
    brief = out_dir / "hypotheses_and_tasks.md"
    write_hypothesis_brief(summary, sig, brief)

    panel_pq = out_dir / "attention_panel.parquet"
    panel_csv = out_dir / "attention_panel.csv"
    sum_pq = out_dir / "attention_summary.parquet"
    sum_csv = out_dir / "attention_summary.csv"
    sig_pq = out_dir / "attention_significance.parquet"
    sig_csv = out_dir / "attention_significance.csv"

    panel.to_parquet(panel_pq, index=False)
    panel.to_csv(panel_csv, index=False)
    summary.to_parquet(sum_pq, index=False)
    summary.to_csv(sum_csv, index=False)
    sig.to_parquet(sig_pq, index=False)
    sig.to_csv(sig_csv, index=False)

    print(f"Wrote: {panel_pq}")
    print(f"Wrote: {panel_csv}")
    print(f"Wrote: {sum_pq}")
    print(f"Wrote: {sum_csv}")
    print(f"Wrote: {sig_pq}")
    print(f"Wrote: {sig_csv}")
    print(f"Wrote: {brief}")
    for f in figs:
        print(f"Wrote figure: {f}")


if __name__ == "__main__":
    main()
