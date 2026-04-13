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
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
    pref_attach_ranking_from_universe,
)
from src.utils import load_config, load_corpus


TOP_K = 100
METRIC_KS = [50, 100, 500, 1000]
EARLY_CUTOFF_MAX = 1995


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Widen the effective-corpus benchmark to 1990-2015 and compare early versus late eras."
    )
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument(
        "--best-config",
        default="outputs/paper/69_v2_2_effective_model_search/best_config.yaml",
        dest="best_config_path",
    )
    parser.add_argument(
        "--adopted-configs",
        default="outputs/paper/83_quality_confirm_path_to_direct_effective/adopted_surface_backtest_configs.csv",
        dest="adopted_configs_path",
    )
    parser.add_argument(
        "--paper-meta",
        default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet",
        dest="paper_meta_path",
    )
    parser.add_argument("--years", default="1985,1990,1995,2000,2005,2010,2015")
    parser.add_argument("--report-years", default="1990,1995,2000,2005,2010,2015", dest="report_years")
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--pool-size", type=int, default=5000, dest="pool_size")
    parser.add_argument("--feature-panel", default="", dest="feature_panel_path")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument("--max-path-len", type=int, default=None, dest="max_path_len")
    parser.add_argument(
        "--include-details",
        action="store_true",
        dest="include_details",
        help="Populate readable path/mediator details in the saved historical feature panel.",
    )
    parser.add_argument("--pairwise-negatives-per-positive", type=int, default=2)
    parser.add_argument("--pairwise-max-pairs-per-cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _log(msg: str) -> None:
    print(msg, flush=True)


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


def _era_label(cutoff_t: int) -> str:
    return "early_1990_1995" if int(cutoff_t) <= EARLY_CUTOFF_MAX else "late_2000_2015"


def _top_diagnostics(ranked_df: pd.DataFrame, eval_rows: pd.DataFrame, top_k: int = TOP_K) -> dict[str, float]:
    if ranked_df.empty:
        return {
            "top_k": int(top_k),
            "top_share_realized": 0.0,
            "top_mean_endpoint_broadness_pct": 0.0,
            "top_mean_endpoint_resolution_score": 0.0,
            "top_mean_mediator_specificity_score": 0.0,
            "top_mean_support_age_years": 0.0,
            "top_mean_recent_support_age_years": 0.0,
            "top_mean_pair_mean_stability": 0.0,
            "top_mean_pair_evidence_diversity": 0.0,
            "top_mean_pair_venue_diversity": 0.0,
            "top_mean_pair_source_diversity": 0.0,
            "top_mean_pair_mean_fwci": 0.0,
            "top_mean_source_recent_share": 0.0,
            "top_mean_target_recent_share": 0.0,
            "top_share_boundary_flag": 0.0,
            "top_share_gap_like_flag": 0.0,
            "top_share_anchored_progression": 0.0,
        }
    top = ranked_df.head(int(top_k)).copy()
    merged = top.merge(
        eval_rows[
            [
                "u",
                "v",
                "appears_within_h",
                "endpoint_broadness_pct",
                "endpoint_resolution_score",
                "focal_mediator_specificity_score",
                "support_age_years",
                "recent_support_age_years",
                "pair_mean_stability",
                "pair_evidence_diversity_mean",
                "pair_venue_diversity_mean",
                "pair_source_diversity_mean",
                "pair_mean_fwci",
                "source_recent_share",
                "target_recent_share",
                "boundary_flag",
                "gap_like_flag",
                "scope_anchored_progression",
            ]
        ],
        on=["u", "v"],
        how="left",
    )
    return {
        "top_k": int(top_k),
        "top_share_realized": float(pd.to_numeric(merged["appears_within_h"], errors="coerce").fillna(0.0).mean()),
        "top_mean_endpoint_broadness_pct": float(pd.to_numeric(merged["endpoint_broadness_pct"], errors="coerce").fillna(0.0).mean()),
        "top_mean_endpoint_resolution_score": float(pd.to_numeric(merged["endpoint_resolution_score"], errors="coerce").fillna(0.0).mean()),
        "top_mean_mediator_specificity_score": float(pd.to_numeric(merged["focal_mediator_specificity_score"], errors="coerce").fillna(0.0).mean()),
        "top_mean_support_age_years": float(pd.to_numeric(merged["support_age_years"], errors="coerce").fillna(0.0).mean()),
        "top_mean_recent_support_age_years": float(pd.to_numeric(merged["recent_support_age_years"], errors="coerce").fillna(0.0).mean()),
        "top_mean_pair_mean_stability": float(pd.to_numeric(merged["pair_mean_stability"], errors="coerce").fillna(0.0).mean()),
        "top_mean_pair_evidence_diversity": float(pd.to_numeric(merged["pair_evidence_diversity_mean"], errors="coerce").fillna(0.0).mean()),
        "top_mean_pair_venue_diversity": float(pd.to_numeric(merged["pair_venue_diversity_mean"], errors="coerce").fillna(0.0).mean()),
        "top_mean_pair_source_diversity": float(pd.to_numeric(merged["pair_source_diversity_mean"], errors="coerce").fillna(0.0).mean()),
        "top_mean_pair_mean_fwci": float(pd.to_numeric(merged["pair_mean_fwci"], errors="coerce").fillna(0.0).mean()),
        "top_mean_source_recent_share": float(pd.to_numeric(merged["source_recent_share"], errors="coerce").fillna(0.0).mean()),
        "top_mean_target_recent_share": float(pd.to_numeric(merged["target_recent_share"], errors="coerce").fillna(0.0).mean()),
        "top_share_boundary_flag": float(pd.to_numeric(merged["boundary_flag"], errors="coerce").fillna(0.0).mean()),
        "top_share_gap_like_flag": float(pd.to_numeric(merged["gap_like_flag"], errors="coerce").fillna(0.0).mean()),
        "top_share_anchored_progression": float(pd.to_numeric(merged["scope_anchored_progression"], errors="coerce").fillna(0.0).mean()),
    }


def _evaluate_model(
    model_name: str,
    ranked_df: pd.DataFrame,
    eval_rows: pd.DataFrame,
    cutoff_t: int,
    horizon: int,
    n_train_cutoffs: int,
    n_train_rows: int,
    n_train_pos: int,
) -> dict[str, Any]:
    positives = {
        (str(r.u), str(r.v))
        for r in eval_rows.loc[eval_rows["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
    }
    metrics = evaluate_binary_ranking(ranked_df, positives=positives, k_values=METRIC_KS)
    return {
        "model": str(model_name),
        "cutoff_year_t": int(cutoff_t),
        "era": _era_label(int(cutoff_t)),
        "horizon": int(horizon),
        "n_train_cutoffs": int(n_train_cutoffs),
        "n_train_rows": int(n_train_rows),
        "n_train_pos": int(n_train_pos),
        "n_eval_rows": int(len(eval_rows)),
        "n_eval_pos": int(len(positives)),
        **{k: float(v) for k, v in metrics.items()},
        **_top_diagnostics(ranked_df, eval_rows, top_k=TOP_K),
    }


def _write_summary_md(
    overall_df: pd.DataFrame,
    era_df: pd.DataFrame,
    delta_df: pd.DataFrame,
    out_path: Path,
    report_years: list[int],
    warmup_years: list[int],
) -> None:
    lines = [
        "# Widened Effective Benchmark (1990-2015)",
        "",
        "This note widens the current effective-corpus benchmark to 1990-2015 while using 1985 only as an internal warm-up cutoff for reranker training.",
        "",
        f"- Reported cutoffs: {', '.join(str(x) for x in report_years)}",
        f"- Internal warm-up only: {', '.join(str(x) for x in warmup_years) if warmup_years else 'none'}",
        "",
    ]
    if overall_df.empty:
        lines.append("No results were produced.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    lines.append("## Overall mean performance")
    lines.append("")
    for row in overall_df.sort_values(["horizon", "model"]).itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}, {row.model}: "
            f"MRR={float(row.mean_mrr):.5f}, "
            f"R@100={float(row.mean_recall_at_100):.5f}, "
            f"top100 realized share={float(row.mean_top_share_realized):.3f}, "
            f"top100 broadness pct={float(row.mean_top_mean_endpoint_broadness_pct):.3f}, "
            f"n_cutoffs={int(row.n_cutoffs)}"
        )
    lines.append("")
    lines.append("## Early vs late")
    lines.append("")
    for row in era_df.sort_values(["horizon", "model", "era"]).itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}, {row.model}, {row.era}: "
            f"mean R@100={float(row.mean_recall_at_100):.5f}, "
            f"sd R@100={float(row.sd_recall_at_100):.5f}, "
            f"mean eval positives={float(row.mean_n_eval_pos):.1f}, "
            f"top100 support age={float(row.mean_top_mean_support_age_years):.2f}, "
            f"top100 recent share={(float(row.mean_top_mean_source_recent_share) + float(row.mean_top_mean_target_recent_share)) / 2.0:.3f}"
        )
    if not delta_df.empty:
        lines.append("")
        lines.append("## Late minus early deltas")
        lines.append("")
        for row in delta_df.sort_values(["horizon", "model"]).itertuples(index=False):
            lines.append(
                f"- h={int(row.horizon)}, {row.model}: "
                f"delta R@100={float(row.delta_mean_recall_at_100):+.5f}, "
                f"delta sd R@100={float(row.delta_sd_recall_at_100):+.5f}, "
                f"delta eval positives={float(row.delta_mean_n_eval_pos):+.1f}, "
                f"delta top100 support age={float(row.delta_mean_top_mean_support_age_years):+.2f}, "
                f"delta top100 broadness pct={float(row.delta_mean_top_mean_endpoint_broadness_pct):+.3f}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)

    _log(f"[widened] out_dir={out_dir}")
    _log(f"[widened] loading corpus from {args.corpus_path}")
    corpus_df = load_corpus(args.corpus_path)
    _log(f"[widened] corpus rows={len(corpus_df):,}")
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    cfg.candidate_family_mode = str(args.candidate_family_mode)
    cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    if args.max_path_len is not None:
        cfg.max_path_len = int(args.max_path_len)
    if hasattr(cfg, "include_details"):
        cfg.include_details = bool(args.include_details)
    _log(
        f"[widened] candidate_family_mode={cfg.candidate_family_mode} "
        f"candidate_kind={cfg.candidate_kind} path_to_direct_scope={getattr(cfg, 'path_to_direct_scope', '')} "
        f"max_path_len={getattr(cfg, 'max_path_len', 'n/a')} "
        f"include_details={getattr(cfg, 'include_details', False)}"
    )
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None
    if paper_meta_df is not None:
        _log(f"[widened] paper_meta rows={len(paper_meta_df):,}")
    else:
        _log("[widened] paper_meta missing; continuing without it")

    horizons = parse_horizons(args.horizons, default=[5, 10, 15])
    max_year = int(corpus_df["year"].max())
    all_years = parse_cutoff_years(
        _parse_ints(args.years),
        min_year=int(corpus_df["year"].min()),
        max_year=max_year,
        max_h=min(horizons),
        step=5,
    )
    report_years = [int(x) for x in _parse_ints(args.report_years) if int(x) in all_years]
    warmup_years = [int(x) for x in all_years if int(x) not in report_years]
    adopted = _load_adopted_configs(Path(args.adopted_configs_path))
    use_horizons = [int(h) for h in horizons if int(h) in adopted]
    if not use_horizons:
        raise ValueError("No adopted reranker configs found for requested horizons")
    _log(f"[widened] adopted horizons={sorted(adopted)} using={use_horizons}")

    feature_panel_path = Path(args.feature_panel_path) if args.feature_panel_path else None
    if feature_panel_path and feature_panel_path.exists():
        _log(f"[widened] loading precomputed feature panel from {feature_panel_path}")
        panel_df = pd.read_parquet(feature_panel_path)
    else:
        _log(
            f"[widened] building feature panel years={all_years} report_years={report_years} "
            f"horizons={use_horizons} pool={args.pool_size}"
        )
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            cutoff_years=all_years,
            horizons=use_horizons,
            pool_sizes=[int(args.pool_size)],
            paper_meta_df=paper_meta_df,
        )
    if panel_df.empty:
        raise ValueError("Candidate feature panel is empty")
    _log(f"[widened] feature panel rows={len(panel_df):,}")

    pool_flag = f"in_pool_{int(args.pool_size)}"
    panel_df = panel_df[panel_df[pool_flag].astype(int) == 1].copy()
    panel_df["era"] = panel_df["cutoff_year_t"].astype(int).map(_era_label)
    _log(f"[widened] filtered panel rows in pool={len(panel_df):,}")

    rows: list[dict[str, Any]] = []
    for horizon in use_horizons:
        _log(f"[widened] evaluating horizon={horizon}")
        spec = adopted[int(horizon)]
        block = panel_df[
            (panel_df["horizon"].astype(int) == int(horizon))
            & ((panel_df["cutoff_year_t"].astype(int) + int(horizon)) <= max_year)
        ].copy()
        if block.empty:
            _log(f"[widened] horizon={horizon} has empty block after filtering")
            continue
        for cutoff_t in report_years:
            _log(f"[widened] horizon={horizon} cutoff={cutoff_t}")
            eval_rows = block[block["cutoff_year_t"].astype(int) == int(cutoff_t)].copy()
            train_rows = block[block["cutoff_year_t"].astype(int) < int(cutoff_t)].copy()
            if eval_rows.empty or train_rows.empty:
                _log(f"[widened] horizon={horizon} cutoff={cutoff_t} skipped: empty eval/train rows")
                continue
            positives = int(eval_rows["appears_within_h"].astype(int).sum())
            if positives <= 0 or train_rows["appears_within_h"].sum() <= 0 or train_rows["appears_within_h"].nunique() < 2:
                _log(f"[widened] horizon={horizon} cutoff={cutoff_t} skipped: insufficient positives or train variation")
                continue

            transparent = (
                eval_rows[["u", "v", "transparent_score"]]
                .rename(columns={"transparent_score": "score"})
                .sort_values(["score", "u", "v"], ascending=[False, True, True])
                .reset_index(drop=True)
            )
            transparent["rank"] = transparent.index + 1
            rows.append(
                _evaluate_model(
                    model_name="transparent",
                    ranked_df=transparent,
                    eval_rows=eval_rows,
                    cutoff_t=int(cutoff_t),
                    horizon=int(horizon),
                    n_train_cutoffs=int(train_rows["cutoff_year_t"].astype(int).nunique()),
                    n_train_rows=int(len(train_rows)),
                    n_train_pos=int(train_rows["appears_within_h"].astype(int).sum()),
                )
            )

            train_corpus = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
            pref = pref_attach_ranking_from_universe(
                train_corpus,
                candidate_pairs_df=eval_rows[[c for c in ["u", "v", "candidate_kind"] if c in eval_rows.columns]].copy(),
            )
            rows.append(
                _evaluate_model(
                    model_name="pref_attach",
                    ranked_df=pref,
                    eval_rows=eval_rows,
                    cutoff_t=int(cutoff_t),
                    horizon=int(horizon),
                    n_train_cutoffs=int(train_rows["cutoff_year_t"].astype(int).nunique()),
                    n_train_rows=int(len(train_rows)),
                    n_train_pos=int(train_rows["appears_within_h"].astype(int).sum()),
                )
            )

            model = _fit_model(
                train_rows=train_rows,
                model_kind=str(spec["model_kind"]),
                feature_family=str(spec["feature_family"]),
                alpha=float(spec["alpha"]),
                pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
                pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
                seed=int(args.seed) + int(cutoff_t) + int(horizon),
            )
            if model is None:
                _log(f"[widened] horizon={horizon} cutoff={cutoff_t} model fit returned None")
                continue
            reranked = score_with_reranker(eval_rows, model)
            rows.append(
                _evaluate_model(
                    model_name=f"adopted_{spec['model_kind']}_{spec['feature_family']}",
                    ranked_df=reranked,
                    eval_rows=eval_rows,
                    cutoff_t=int(cutoff_t),
                    horizon=int(horizon),
                    n_train_cutoffs=int(train_rows["cutoff_year_t"].astype(int).nunique()),
                    n_train_rows=int(len(train_rows)),
                    n_train_pos=int(train_rows["appears_within_h"].astype(int).sum()),
                )
            )

    cutoff_df = pd.DataFrame(rows)
    if cutoff_df.empty:
        raise ValueError("No cutoff-level results were generated")

    overall_df = (
        cutoff_df.groupby(["model", "horizon"], as_index=False)
        .agg(
            mean_mrr=("mrr", "mean"),
            mean_recall_at_50=("recall_at_50", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_recall_at_500=("recall_at_500", "mean"),
            mean_n_eval_pos=("n_eval_pos", "mean"),
            mean_top_share_realized=("top_share_realized", "mean"),
            mean_top_mean_endpoint_broadness_pct=("top_mean_endpoint_broadness_pct", "mean"),
            mean_top_mean_endpoint_resolution_score=("top_mean_endpoint_resolution_score", "mean"),
            mean_top_mean_mediator_specificity_score=("top_mean_mediator_specificity_score", "mean"),
            mean_top_mean_support_age_years=("top_mean_support_age_years", "mean"),
            mean_top_mean_recent_support_age_years=("top_mean_recent_support_age_years", "mean"),
            mean_top_mean_pair_mean_stability=("top_mean_pair_mean_stability", "mean"),
            mean_top_mean_pair_evidence_diversity=("top_mean_pair_evidence_diversity", "mean"),
            mean_top_mean_source_recent_share=("top_mean_source_recent_share", "mean"),
            mean_top_mean_target_recent_share=("top_mean_target_recent_share", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "model"])
        .reset_index(drop=True)
    )

    era_df = (
        cutoff_df.groupby(["model", "horizon", "era"], as_index=False)
        .agg(
            mean_mrr=("mrr", "mean"),
            sd_mrr=("mrr", "std"),
            mean_recall_at_100=("recall_at_100", "mean"),
            sd_recall_at_100=("recall_at_100", "std"),
            mean_n_eval_pos=("n_eval_pos", "mean"),
            mean_top_mean_endpoint_broadness_pct=("top_mean_endpoint_broadness_pct", "mean"),
            mean_top_mean_endpoint_resolution_score=("top_mean_endpoint_resolution_score", "mean"),
            mean_top_mean_support_age_years=("top_mean_support_age_years", "mean"),
            mean_top_mean_recent_support_age_years=("top_mean_recent_support_age_years", "mean"),
            mean_top_mean_pair_mean_stability=("top_mean_pair_mean_stability", "mean"),
            mean_top_mean_pair_evidence_diversity=("top_mean_pair_evidence_diversity", "mean"),
            mean_top_mean_source_recent_share=("top_mean_source_recent_share", "mean"),
            mean_top_mean_target_recent_share=("top_mean_target_recent_share", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "model", "era"])
        .reset_index(drop=True)
    )
    for col in ["sd_mrr", "sd_recall_at_100"]:
        era_df[col] = era_df[col].fillna(0.0)

    early = era_df[era_df["era"] == "early_1990_1995"].copy()
    late = era_df[era_df["era"] == "late_2000_2015"].copy()
    delta_df = pd.merge(
        late,
        early,
        on=["model", "horizon"],
        how="inner",
        suffixes=("_late", "_early"),
    )
    for base_col in [
        "mean_mrr",
        "sd_mrr",
        "mean_recall_at_100",
        "sd_recall_at_100",
        "mean_n_eval_pos",
        "mean_top_mean_endpoint_broadness_pct",
        "mean_top_mean_endpoint_resolution_score",
        "mean_top_mean_support_age_years",
        "mean_top_mean_recent_support_age_years",
        "mean_top_mean_pair_mean_stability",
        "mean_top_mean_pair_evidence_diversity",
        "mean_top_mean_source_recent_share",
        "mean_top_mean_target_recent_share",
    ]:
        delta_df[f"delta_{base_col}"] = delta_df[f"{base_col}_late"] - delta_df[f"{base_col}_early"]
    delta_cols = ["model", "horizon"] + [c for c in delta_df.columns if c.startswith("delta_")]
    delta_df = delta_df[delta_cols].sort_values(["horizon", "model"]).reset_index(drop=True)

    manifest = {
        "corpus_path": args.corpus_path,
        "config_path": args.config_path,
        "best_config_path": args.best_config_path,
        "adopted_configs_path": args.adopted_configs_path,
        "paper_meta_path": args.paper_meta_path,
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "max_path_len": int(getattr(cfg, "max_path_len", 2)),
        "include_details": bool(getattr(cfg, "include_details", False)),
        "pool_size": int(args.pool_size),
        "panel_cutoff_years": [int(x) for x in all_years],
        "report_cutoff_years": [int(x) for x in report_years],
        "warmup_cutoff_years": [int(x) for x in warmup_years],
        "horizons": [int(x) for x in use_horizons],
    }

    if feature_panel_path and feature_panel_path.exists():
        _log(f"[widened] reusing cached feature panel from {feature_panel_path}")
    else:
        panel_df.to_parquet(Path(out_dir) / "historical_feature_panel.parquet", index=False)
    cutoff_df.to_csv(Path(out_dir) / "widened_cutoff_eval.csv", index=False)
    overall_df.to_csv(Path(out_dir) / "widened_overall_summary.csv", index=False)
    era_df.to_csv(Path(out_dir) / "widened_era_summary.csv", index=False)
    delta_df.to_csv(Path(out_dir) / "widened_early_vs_late_delta.csv", index=False)
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_summary_md(overall_df, era_df, delta_df, Path(out_dir) / "widened_summary.md", report_years, warmup_years)
    _log(f"[widened] wrote: {Path(out_dir) / 'widened_overall_summary.csv'}")


if __name__ == "__main__":
    main()
