from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.learned_reranker import (
    FEATURE_FAMILIES,
    build_candidate_feature_panel,
    fit_glm_logit_reranker,
    fit_pairwise_logit_reranker,
    score_with_reranker,
)
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking, parse_cutoff_years, parse_horizons
from src.utils import load_config, load_corpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate reranker depth usage versus retrieval pool size.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument(
        "--adopted-configs",
        default="outputs/paper/83_quality_confirm_path_to_direct_effective/adopted_surface_backtest_configs.csv",
        dest="adopted_configs_path",
    )
    parser.add_argument("--paper-meta", default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--years", default="2000,2005,2010,2015")
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--pool-sizes", default="500,2000,5000,10000", dest="pool_sizes")
    parser.add_argument("--k-values", default="20,50,100,250,500", dest="k_values")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument("--pairwise-negatives-per-positive", type=int, default=2)
    parser.add_argument("--pairwise-max-pairs-per-cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _parse_ints(raw: str) -> list[int]:
    return [int(float(x.strip())) for x in str(raw).split(",") if x.strip()]


def _load_adopted_configs(path: Path) -> dict[int, dict[str, Any]]:
    df = pd.read_csv(path)
    out: dict[int, dict[str, Any]] = {}
    for row in df.itertuples(index=False):
        out[int(row.horizon)] = {
            "model_kind": str(row.model_kind),
            "feature_family": str(row.feature_family),
            "alpha": float(row.alpha),
        }
    return out


def _fit_model(
    train_rows: pd.DataFrame,
    model_kind: str,
    feature_family: str,
    alpha: float,
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
) -> Any | None:
    feature_names = [c for c in FEATURE_FAMILIES[str(feature_family)] if c in train_rows.columns]
    if not feature_names:
        return None
    if str(model_kind) == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if str(model_kind) == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=int(pairwise_negatives_per_positive),
            max_pairs_per_cutoff=int(pairwise_max_pairs_per_cutoff),
            seed=int(seed),
        )
    raise ValueError(f"Unsupported model_kind: {model_kind}")


def _depth_metrics(scored_eval: pd.DataFrame, top_n: int = 100) -> dict[str, float]:
    top = scored_eval.head(int(top_n)).copy()
    if top.empty:
        return {
            "mean_transparent_rank_top100": 0.0,
            "median_transparent_rank_top100": 0.0,
            "max_transparent_rank_top100": 0.0,
            "share_transparent_gt_100_top100": 0.0,
            "share_transparent_gt_500_top100": 0.0,
            "share_transparent_gt_1000_top100": 0.0,
            "share_transparent_gt_2000_top100": 0.0,
            "share_transparent_gt_5000_top100": 0.0,
        }
    tr = pd.to_numeric(top["transparent_rank"], errors="coerce").fillna(0).astype(float)
    return {
        "mean_transparent_rank_top100": float(tr.mean()),
        "median_transparent_rank_top100": float(tr.median()),
        "max_transparent_rank_top100": float(tr.max()),
        "share_transparent_gt_100_top100": float((tr > 100).mean()),
        "share_transparent_gt_500_top100": float((tr > 500).mean()),
        "share_transparent_gt_1000_top100": float((tr > 1000).mean()),
        "share_transparent_gt_2000_top100": float((tr > 2000).mean()),
        "share_transparent_gt_5000_top100": float((tr > 5000).mean()),
    }


def _write_summary_md(summary_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Reranker Pool Depth Evaluation",
        "",
        "This note evaluates how much the reranker benefits from larger retrieval pools and how deep into the transparent ranking the surfaced top-100 draws.",
        "",
    ]
    if summary_df.empty:
        lines.append("No results were produced.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    for horizon in sorted(summary_df["horizon"].unique()):
        lines.append(f"## h={int(horizon)}")
        sub = summary_df.loc[summary_df["horizon"] == int(horizon)].sort_values("pool_size")
        for row in sub.itertuples(index=False):
            lines.append(
                f"- pool={int(row.pool_size)}, n_cutoffs={int(row.n_cutoffs)}: "
                f"conditional R@100={float(row.mean_recall_at_100):.6f}, "
                f"R@100 vs top10000={float(row.mean_recall_at_100_vs_maxpool):.6f}, "
                f"pool ceiling vs top10000={float(row.mean_pool_recall_ceiling_vs_maxpool):.6f}, "
                f"mean transparent rank in reranked top100={float(row.mean_transparent_rank_top100):.1f}, "
                f"share >500={float(row.mean_share_transparent_gt_500_top100):.3f}, "
                f"share >1000={float(row.mean_share_transparent_gt_1000_top100):.3f}, "
                f"share >2000={float(row.mean_share_transparent_gt_2000_top100):.3f}"
            )
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    cfg.candidate_family_mode = str(args.candidate_family_mode)
    cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None

    horizons = parse_horizons(args.horizons, default=[5, 10, 15])
    years = parse_cutoff_years(
        _parse_ints(args.years),
        min_year=int(corpus_df["year"].min()),
        max_year=int(corpus_df["year"].max()),
        max_h=min(horizons),
        step=5,
    )
    pool_sizes = sorted(set(int(x) for x in _parse_ints(args.pool_sizes) if int(x) > 0))
    k_values = sorted(set(int(x) for x in _parse_ints(args.k_values) if int(x) > 0))
    max_year = int(corpus_df["year"].max())

    adopted = _load_adopted_configs(Path(args.adopted_configs_path))
    use_horizons = [int(h) for h in horizons if int(h) in adopted]
    if not use_horizons:
        raise ValueError("No adopted reranker configs found for requested horizons")
    max_pool = int(max(pool_sizes))

    panel_df = build_candidate_feature_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=years,
        horizons=use_horizons,
        pool_sizes=pool_sizes,
        paper_meta_df=paper_meta_df,
    )
    if panel_df.empty:
        raise ValueError("Candidate feature panel is empty")

    results: list[dict[str, Any]] = []
    for horizon in use_horizons:
        spec = adopted[int(horizon)]
        valid_horizon_df = panel_df[
            (panel_df["horizon"].astype(int) == int(horizon))
            & ((panel_df["cutoff_year_t"].astype(int) + int(horizon)) <= max_year)
        ].copy()
        if valid_horizon_df.empty:
            continue
        for pool_size in pool_sizes:
            pool_flag = f"in_pool_{int(pool_size)}"
            if pool_flag not in valid_horizon_df.columns:
                continue
            block = valid_horizon_df[valid_horizon_df[pool_flag].astype(int) == 1].copy()
            if block.empty:
                continue
            cutoffs = sorted(int(x) for x in block["cutoff_year_t"].dropna().unique())
            for cutoff_t in cutoffs:
                eval_rows = block[block["cutoff_year_t"].astype(int) == int(cutoff_t)].copy()
                train_rows = block[block["cutoff_year_t"].astype(int) < int(cutoff_t)].copy()
                maxpool_rows = valid_horizon_df[
                    (valid_horizon_df["cutoff_year_t"].astype(int) == int(cutoff_t))
                    & (valid_horizon_df[f"in_pool_{int(max_pool)}"].astype(int) == 1)
                ].copy()
                if eval_rows.empty or train_rows.empty:
                    continue
                if train_rows["appears_within_h"].sum() <= 0 or train_rows["appears_within_h"].nunique() < 2:
                    continue
                model = _fit_model(
                    train_rows=train_rows,
                    model_kind=str(spec["model_kind"]),
                    feature_family=str(spec["feature_family"]),
                    alpha=float(spec["alpha"]),
                    pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
                    pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
                    seed=int(args.seed) + int(cutoff_t) + int(horizon) + int(pool_size),
                )
                if model is None:
                    continue
                scored = score_with_reranker(eval_rows, model)
                enriched = scored.merge(
                    eval_rows[["u", "v", "transparent_rank", "appears_within_h"]],
                    on=["u", "v"],
                    how="left",
                ).sort_values(["rank", "u", "v"]).reset_index(drop=True)
                positives = {
                    (str(r.u), str(r.v))
                    for r in eval_rows.loc[eval_rows["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
                }
                maxpool_positives = {
                    (str(r.u), str(r.v))
                    for r in maxpool_rows.loc[maxpool_rows["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
                }
                metrics = evaluate_binary_ranking(
                    enriched[["u", "v", "score", "rank"]].copy(),
                    positives=positives,
                    k_values=k_values,
                )
                metrics_vs_maxpool = evaluate_binary_ranking(
                    enriched[["u", "v", "score", "rank"]].copy(),
                    positives=maxpool_positives,
                    k_values=k_values,
                )
                row: dict[str, Any] = {
                    "horizon": int(horizon),
                    "cutoff_year_t": int(cutoff_t),
                    "pool_size": int(pool_size),
                    "model_kind": str(spec["model_kind"]),
                    "feature_family": str(spec["feature_family"]),
                    "alpha": float(spec["alpha"]),
                    "n_train_rows": int(len(train_rows)),
                    "n_eval_rows": int(len(eval_rows)),
                    "n_eval_pos": int(eval_rows["appears_within_h"].sum()),
                    "n_maxpool_pos": int(len(maxpool_positives)),
                    "pool_positive_rate": float(eval_rows["appears_within_h"].astype(int).mean()),
                    "pool_recall_ceiling_vs_maxpool": float(len(positives)) / float(max(1, len(maxpool_positives))),
                }
                row.update({k: float(v) for k, v in metrics.items()})
                for k, v in metrics_vs_maxpool.items():
                    row[f"{k}_vs_maxpool"] = float(v)
                row.update(_depth_metrics(enriched, top_n=100))
                results.append(row)

    cutoff_df = pd.DataFrame(results)
    if cutoff_df.empty:
        raise ValueError("No pool-depth evaluation rows were produced")
    summary_df = (
        cutoff_df.groupby(["horizon", "pool_size", "model_kind", "feature_family", "alpha"], as_index=False)
        .agg(
            n_cutoffs=("cutoff_year_t", "nunique"),
            mean_mrr=("mrr", "mean"),
            mean_recall_at_20=("recall_at_20", "mean"),
            mean_recall_at_50=("recall_at_50", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_recall_at_250=("recall_at_250", "mean"),
            mean_recall_at_500=("recall_at_500", "mean"),
            mean_mrr_vs_maxpool=("mrr_vs_maxpool", "mean"),
            mean_recall_at_20_vs_maxpool=("recall_at_20_vs_maxpool", "mean"),
            mean_recall_at_50_vs_maxpool=("recall_at_50_vs_maxpool", "mean"),
            mean_recall_at_100_vs_maxpool=("recall_at_100_vs_maxpool", "mean"),
            mean_recall_at_250_vs_maxpool=("recall_at_250_vs_maxpool", "mean"),
            mean_recall_at_500_vs_maxpool=("recall_at_500_vs_maxpool", "mean"),
            mean_precision_at_100=("precision_at_100", "mean"),
            mean_pool_positive_rate=("pool_positive_rate", "mean"),
            mean_pool_recall_ceiling_vs_maxpool=("pool_recall_ceiling_vs_maxpool", "mean"),
            mean_transparent_rank_top100=("mean_transparent_rank_top100", "mean"),
            mean_median_transparent_rank_top100=("median_transparent_rank_top100", "mean"),
            mean_max_transparent_rank_top100=("max_transparent_rank_top100", "mean"),
            mean_share_transparent_gt_100_top100=("share_transparent_gt_100_top100", "mean"),
            mean_share_transparent_gt_500_top100=("share_transparent_gt_500_top100", "mean"),
            mean_share_transparent_gt_1000_top100=("share_transparent_gt_1000_top100", "mean"),
            mean_share_transparent_gt_2000_top100=("share_transparent_gt_2000_top100", "mean"),
            mean_share_transparent_gt_5000_top100=("share_transparent_gt_5000_top100", "mean"),
        )
        .sort_values(["horizon", "pool_size"])
        .reset_index(drop=True)
    )

    cutoff_df.to_csv(Path(out_dir) / "reranker_pool_depth_cutoff_eval.csv", index=False)
    summary_df.to_csv(Path(out_dir) / "reranker_pool_depth_summary.csv", index=False)
    _write_summary_md(summary_df, Path(out_dir) / "reranker_pool_depth_summary.md")

    manifest = {
        "corpus_path": args.corpus_path,
        "paper_meta_path": args.paper_meta_path,
        "config_path": args.config_path,
        "best_config_path": args.best_config_path,
        "adopted_configs_path": args.adopted_configs_path,
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "years_requested": _parse_ints(args.years),
        "years_used": [int(x) for x in years],
        "horizons_requested": [int(x) for x in horizons],
        "horizons_evaluated": [int(x) for x in use_horizons],
        "pool_sizes": [int(x) for x in pool_sizes],
        "k_values": [int(x) for x in k_values],
        "n_panel_rows": int(len(panel_df)),
        "n_eval_rows": int(len(cutoff_df)),
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote: {Path(out_dir) / 'reranker_pool_depth_summary.csv'}")


if __name__ == "__main__":
    main()
