from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.learned_reranker import (
    build_candidate_feature_panel,
    walk_forward_reranker_eval,
)
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    parse_cutoff_years,
    parse_horizons,
)
from src.utils import load_config, load_corpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Focused learned-reranker tuning on the frozen research-allocation graph.")
    parser.add_argument("--corpus", default="data/processed/research_allocation_v2/hybrid_corpus.parquet", dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper_meta", default="data/processed/research_allocation_v2/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--feature-panel", default="", dest="feature_panel_path")
    parser.add_argument("--years", type=int, nargs="*", default=[1990, 1995, 2000, 2005, 2010, 2015])
    parser.add_argument("--horizons", default="5,10")
    parser.add_argument("--pool_sizes", default="10000")
    parser.add_argument("--feature_families", default="structural,composition,boundary_gap")
    parser.add_argument("--model_kinds", default="glm_logit,pairwise_logit")
    parser.add_argument("--alphas", default="0.01,0.05,0.10,0.20")
    parser.add_argument("--candidate-family-mode", default="", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="", dest="path_to_direct_scope")
    parser.add_argument("--max-path-len", type=int, default=None, dest="max_path_len")
    parser.add_argument("--pairwise_negatives_per_positive", type=int, default=2)
    parser.add_argument("--pairwise_max_pairs_per_cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _log(msg: str) -> None:
    print(msg, flush=True)


def _write_summary_markdown(summary_df: pd.DataFrame, best_df: pd.DataFrame, out_path: Path) -> None:
    def _get(row: object, name: str, default: float = float("nan")) -> float:
        return float(getattr(row, name, default))

    lines = [
        "# Learned Reranker Tuning Summary",
        "",
        "This note summarizes the focused frozen-ontology reranker tuning pass.",
        "",
    ]
    if best_df.empty:
        lines.append("No valid tuning results were produced.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    lines.append("## Best configurations by horizon")
    for row in best_df.sort_values(["horizon", "selection_objective"], ascending=[True, False]).itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}: alpha={float(row.alpha):.3f}, {row.model_kind} + {row.feature_family}, "
            f"pool={int(row.pool_size)} | MRR={float(row.mean_mrr):.6f}, "
            f"Recall@100={float(row.mean_recall_at_100):.6f}, "
            f"delta Recall@100 vs transparent={_get(row, 'mean_delta_recall_at_100_vs_transparent', 0.0):+.6f}, "
            f"delta Recall@100 vs pref={_get(row, 'mean_delta_recall_at_100_vs_pref', 0.0):+.6f}, "
            f"delta MRR vs transparent={_get(row, 'mean_delta_mrr_vs_transparent', 0.0):+.6f}, "
            f"delta MRR vs pref={_get(row, 'mean_delta_mrr_vs_pref', 0.0):+.6f}"
        )
    lines.extend(["", "## Top tuned variants", ""])
    cols = [
        "alpha",
        "model_kind",
        "feature_family",
        "pool_size",
        "horizon",
        "mean_mrr",
        "mean_recall_at_100",
        "mean_delta_mrr_vs_transparent",
        "mean_delta_recall_at_100_vs_transparent",
        "n_cutoffs",
    ]
    top = summary_df.sort_values(["horizon", "selection_objective"], ascending=[True, False])[cols + ["selection_objective"]].groupby("horizon").head(5)
    for row in top.itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)} | alpha={float(row.alpha):.3f} | {row.model_kind} + {row.feature_family} | "
            f"MRR={float(row.mean_mrr):.6f}, Recall@100={float(row.mean_recall_at_100):.6f}, "
            f"delta MRR vs transparent={_get(row, 'mean_delta_mrr_vs_transparent', 0.0):+.6f}, "
            f"delta MRR vs pref={_get(row, 'mean_delta_mrr_vs_pref', 0.0):+.6f}, "
            f"delta Recall@100 vs transparent={_get(row, 'mean_delta_recall_at_100_vs_transparent', 0.0):+.6f}, "
            f"delta Recall@100 vs pref={_get(row, 'mean_delta_recall_at_100_vs_pref', 0.0):+.6f}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pick_best(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    df = summary_df.copy()
    df["selection_objective"] = df["mean_mrr"].astype(float) + 1.5 * df["mean_recall_at_100"].astype(float)
    keep_cols = [
        "alpha",
        "model_kind",
        "feature_family",
        "pool_size",
        "horizon",
        "mean_mrr",
        "mean_recall_at_50",
        "mean_recall_at_100",
        "mean_recall_at_500",
        "mean_recall_at_1000",
        "mean_delta_mrr_vs_transparent",
        "mean_delta_mrr_vs_pref",
        "mean_delta_recall_at_100_vs_transparent",
        "mean_delta_recall_at_100_vs_pref",
        "n_cutoffs",
        "total_eval_pos",
        "selection_objective",
    ]
    out = (
        df.sort_values(["horizon", "selection_objective"], ascending=[True, False])
        .groupby("horizon", as_index=False)
        .head(1)[keep_cols]
        .reset_index(drop=True)
    )
    return out


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)

    _log(f"[reranker] out_dir={out_dir}")
    _log(f"[reranker] loading corpus from {args.corpus_path}")
    corpus_df = load_corpus(args.corpus_path)
    _log(f"[reranker] corpus rows={len(corpus_df):,}")
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    if args.candidate_family_mode:
        cfg.candidate_family_mode = str(args.candidate_family_mode)
    if args.path_to_direct_scope:
        cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    if args.max_path_len is not None:
        cfg.max_path_len = int(args.max_path_len)
    _log(
        f"[reranker] candidate_family_mode={cfg.candidate_family_mode} "
        f"candidate_kind={cfg.candidate_kind} path_to_direct_scope={getattr(cfg, 'path_to_direct_scope', '')} "
        f"max_path_len={getattr(cfg, 'max_path_len', 'n/a')}"
    )
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None
    if paper_meta_df is not None:
        _log(f"[reranker] paper_meta rows={len(paper_meta_df):,}")
    else:
        _log("[reranker] paper_meta missing; continuing without it")

    horizons = parse_horizons(args.horizons, default=[5, 10])
    pool_sizes = [int(x.strip()) for x in str(args.pool_sizes).split(",") if x.strip()]
    feature_family_names = [x.strip() for x in str(args.feature_families).split(",") if x.strip()]
    model_kinds = [x.strip() for x in str(args.model_kinds).split(",") if x.strip()]
    alphas = [float(x.strip()) for x in str(args.alphas).split(",") if x.strip()]
    cutoff_years = parse_cutoff_years(
        args.years,
        min_year=int(corpus_df["year"].min()),
        max_year=int(corpus_df["year"].max()),
        max_h=max(horizons),
        step=5,
    )

    feature_panel_path = Path(args.feature_panel_path) if args.feature_panel_path else None
    if feature_panel_path and feature_panel_path.exists():
        _log(f"[reranker] loading precomputed feature panel from {feature_panel_path}")
        panel_df = pd.read_parquet(feature_panel_path)
    else:
        _log(
            f"[reranker] building feature panel years={cutoff_years} horizons={horizons} "
            f"pool_sizes={pool_sizes}"
        )
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            cutoff_years=cutoff_years,
            horizons=horizons,
            pool_sizes=pool_sizes,
            paper_meta_df=paper_meta_df,
        )
    _log(f"[reranker] feature panel rows={len(panel_df):,}")
    if feature_panel_path and not feature_panel_path.exists():
        try:
            panel_df.to_parquet(feature_panel_path, index=False)
            _log(f"[reranker] wrote feature panel cache to {feature_panel_path}")
        except Exception as exc:  # noqa: BLE001
            _log(f"[reranker] failed to cache feature panel to {feature_panel_path}: {exc}")

    cutoff_frames: list[pd.DataFrame] = []
    summary_frames: list[pd.DataFrame] = []
    for alpha in alphas:
        _log(f"[reranker] evaluating alpha={alpha:.3f}")
        cutoff_df, summary_df = walk_forward_reranker_eval(
            panel_df=panel_df,
            corpus_df=corpus_df,
            feature_family_names=feature_family_names,
            model_kinds=model_kinds,
            pool_sizes=pool_sizes,
            alpha=float(alpha),
            pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
            pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
            seed=int(args.seed),
        )
        if cutoff_df.empty or summary_df.empty:
            continue
        cutoff_df = cutoff_df.copy()
        summary_df = summary_df.copy()
        cutoff_df["alpha"] = float(alpha)
        summary_df["alpha"] = float(alpha)
        summary_df["selection_objective"] = summary_df["mean_mrr"].astype(float) + 1.5 * summary_df["mean_recall_at_100"].astype(float)
        cutoff_frames.append(cutoff_df)
        summary_frames.append(summary_df)
        _log(
            f"[reranker] alpha={alpha:.3f} produced cutoff_rows={len(cutoff_df):,} "
            f"summary_rows={len(summary_df):,}"
        )

    all_cutoff_df = pd.concat(cutoff_frames, ignore_index=True) if cutoff_frames else pd.DataFrame()
    all_summary_df = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    best_df = _pick_best(all_summary_df)

    if not all_cutoff_df.empty:
        all_cutoff_df.to_csv(Path(out_dir) / "tuning_cutoff_eval.csv", index=False)
    if not all_summary_df.empty:
        all_summary_df.to_csv(Path(out_dir) / "tuning_summary.csv", index=False)
    if not best_df.empty:
        best_df.to_csv(Path(out_dir) / "tuning_best_configs.csv", index=False)
        paper_cols = [
            "horizon",
            "alpha",
            "model_kind",
            "feature_family",
            "pool_size",
            "mean_mrr",
            "mean_recall_at_100",
            "mean_delta_mrr_vs_transparent",
            "mean_delta_mrr_vs_pref",
            "mean_delta_recall_at_100_vs_transparent",
            "mean_delta_recall_at_100_vs_pref",
            "selection_objective",
        ]
        best_df[[c for c in paper_cols if c in best_df.columns]].to_csv(Path(out_dir) / "tuning_paper_summary.csv", index=False)
    _write_summary_markdown(all_summary_df, best_df, Path(out_dir) / "tuning_summary.md")

    manifest = {
        "cutoff_years": cutoff_years,
        "horizons": horizons,
        "pool_sizes": pool_sizes,
        "feature_families": feature_family_names,
        "model_kinds": model_kinds,
        "alphas": alphas,
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "max_path_len": int(getattr(cfg, "max_path_len", 2)),
        "n_panel_rows": int(len(panel_df)),
        "n_eval_rows": int(len(all_cutoff_df)),
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _log(f"[reranker] wrote: {Path(out_dir) / 'tuning_summary.csv'}")


if __name__ == "__main__":
    main()
