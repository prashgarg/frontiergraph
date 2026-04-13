from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.learned_reranker import (
    _feature_list,
    build_candidate_feature_panel,
    fit_glm_logit_reranker,
    fit_pairwise_logit_reranker,
    score_with_reranker,
)
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking
from src.utils import load_config, load_corpus


ENV_PATTERNS = [
    r"\bcarbon\b",
    r"\bco2\b",
    r"\bemissions?\b",
    r"\bclimate\b",
    r"\benvironment",
    r"\bpollution\b",
    r"\becological\b",
    r"\bgreen\b",
    r"\brenewable\b",
    r"\benergy\b",
    r"\bsustainab",
]
INNOV_PATTERNS = [r"\binnovation\b", r"\btechnolog", r"\bdigital\b"]
MACRO_PATTERNS = [r"\bbusiness cycle\b", r"\bgrowth\b", r"\binflation\b", r"\bhouse prices?\b", r"\bprice changes?\b", r"\bproductivity\b", r"\boutput\b"]
FIN_PATTERNS = [r"\bfinancial\b", r"\bfinance\b", r"\btax\b", r"\bbonds?\b", r"\binvestment\b", r"\bdebt\b"]
DEMAND_PATTERNS = [r"\bwages?\b", r"\bincome\b", r"\bemployment\b", r"\bwillingness to pay\b", r"\bconsumption\b"]
TRADE_PATTERNS = [r"\btrade\b", r"\bimports?\b", r"\bexports?\b", r"\bglobal", r"\burban", r"\bcity\b", r"\btourism\b", r"\bindustrial structure\b"]
UNCERTAINTY_PATTERNS = [r"\buncertainty\b", r"\brisk\b"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest a light diversification layer on the best learned reranker.")
    parser.add_argument("--corpus", default="data/processed/research_allocation_v2/hybrid_corpus.parquet", dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best-config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper-meta", default="data/processed/research_allocation_v2/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--panel-cache", default="outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet", dest="panel_cache")
    parser.add_argument("--tuning-best", default="outputs/paper/24_learned_reranker_tuning_patch_v2/tuning_best_configs.csv", dest="tuning_best_path")
    parser.add_argument("--benchmark-summary", default="outputs/paper/42_benchmark_strategy_review/benchmark_strategy_summary.csv", dest="benchmark_summary_path")
    parser.add_argument("--concepts-csv", default="site/public/data/v2/central_concepts.csv", dest="concepts_csv")
    parser.add_argument("--pool-size", type=int, default=10000, dest="pool_size")
    parser.add_argument("--k-values", default="50,100", dest="k_values")
    parser.add_argument("--diversify-window", type=int, default=1000, dest="diversify_window")
    parser.add_argument("--cutoff-years", default="1995,2000,2005,2010,2015", dest="cutoff_years")
    parser.add_argument("--horizons", default="", dest="horizons")
    parser.add_argument("--candidate-family-mode", default="", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="", dest="path_to_direct_scope")
    parser.add_argument("--out", default="outputs/paper/43_reranker_diversification_backtest", dest="out_dir")
    parser.add_argument("--note", default="next_steps/reranker_diversification_note.md", dest="note_path")
    return parser.parse_args()


def _parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _load_label_map(corpus_df: pd.DataFrame, concepts_csv: str | Path) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for left, right in [("src_code", "src_label"), ("dst_code", "dst_label")]:
        if left in corpus_df.columns and right in corpus_df.columns:
            tmp = corpus_df[[left, right]].drop_duplicates()
            for row in tmp.itertuples(index=False):
                code = str(getattr(row, left))
                label = str(getattr(row, right))
                if code and label and code not in label_map:
                    label_map[code] = label
    concepts_path = Path(concepts_csv)
    if concepts_path.exists():
        concepts_df = pd.read_csv(concepts_path, usecols=["concept_id", "plain_label"])
        for row in concepts_df.drop_duplicates("concept_id").itertuples(index=False):
            label_map.setdefault(str(row.concept_id), str(row.plain_label))
    return label_map


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_family_label(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "gdp": "gdp",
        "gross domestic product gdp": "gdp",
        "gross domestic product": "gdp",
        "economic growth gdp": "gdp",
        "co2 emissions": "carbon emissions",
        "carbon emissions co2 emissions": "carbon emissions",
        "willingness to pay wtp": "willingness to pay",
        "environmental quality co2 emissions": "environmental quality",
    }
    return alias_map.get(text, text)


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _theme_for_label(label: str) -> str:
    text = _normalize_family_label(label)
    if _match_any(text, ENV_PATTERNS):
        return "environment_climate"
    if _match_any(text, INNOV_PATTERNS):
        return "innovation_technology"
    if _match_any(text, MACRO_PATTERNS):
        return "macro_cycle_prices"
    if _match_any(text, FIN_PATTERNS):
        return "finance_tax"
    if _match_any(text, DEMAND_PATTERNS):
        return "labor_income_demand"
    if _match_any(text, TRADE_PATTERNS):
        return "trade_urban_structure"
    if _match_any(text, UNCERTAINTY_PATTERNS):
        return "uncertainty_risk"
    return "other"


def _fit_model(
    model_kind: str,
    train_rows: pd.DataFrame,
    feature_names: list[str],
    alpha: float,
) -> Any:
    if model_kind == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if model_kind == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=2,
            max_pairs_per_cutoff=2000,
            seed=42,
        )
    raise ValueError(f"Unsupported model_kind: {model_kind}")


def _annotate_keys(df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    out["source_label"] = out["u"].astype(str).map(label_map).fillna(out["u"].astype(str))
    out["target_label"] = out["v"].astype(str).map(label_map).fillna(out["v"].astype(str))
    out["source_family"] = out["source_label"].map(_normalize_family_label)
    out["target_family"] = out["target_label"].map(_normalize_family_label)
    out["semantic_family_key"] = out["source_family"].astype(str) + "__" + out["target_family"].astype(str)
    out["source_theme"] = out["source_label"].map(_theme_for_label)
    out["target_theme"] = out["target_label"].map(_theme_for_label)
    out["theme_pair_key"] = out["source_theme"].astype(str) + "__" + out["target_theme"].astype(str)
    co2_tokens = ("co2", "carbon", "emissions", "climate")
    out["co2_centered"] = [
        int(any(token in f"{_normalize_family_label(src)} {_normalize_family_label(dst)}" for token in co2_tokens))
        for src, dst in zip(out["source_label"], out["target_label"])
    ]
    return out


def _diversify(df: pd.DataFrame, diversify_window: int) -> pd.DataFrame:
    ordered = df.sort_values(["reranker_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
    top_window = ordered.head(int(diversify_window)).copy()
    tail = ordered.iloc[int(diversify_window) :].copy()
    remaining = top_window.copy()
    selected_rows: list[pd.Series] = []
    source_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    source_theme_counts: Counter[str] = Counter()
    target_theme_counts: Counter[str] = Counter()
    theme_pair_counts: Counter[str] = Counter()

    while not remaining.empty:
        work = remaining.copy()
        work["theme_penalty"] = (
            work["source_theme"].astype(str).map(lambda x: 2 * max(source_theme_counts[x] - 2, 0))
            + work["target_theme"].astype(str).map(lambda x: 2 * max(target_theme_counts[x] - 2, 0))
            + work["theme_pair_key"].astype(str).map(lambda x: 3 * theme_pair_counts[x])
        )
        work["redundancy_penalty"] = (
            work["semantic_family_key"].astype(str).map(lambda x: 12 * family_counts[x])
            + work["source_family"].astype(str).map(lambda x: 4 * source_counts[x])
            + work["target_family"].astype(str).map(lambda x: 4 * target_counts[x])
        )
        work["adjusted_priority"] = work["reranker_rank"].astype(float) + work["theme_penalty"].astype(float) + work["redundancy_penalty"].astype(float)
        pick = work.sort_values(["adjusted_priority", "reranker_rank", "u", "v"], ascending=[True, True, True, True]).iloc[0]
        selected_rows.append(pick)
        source_counts[str(pick["source_family"])] += 1
        target_counts[str(pick["target_family"])] += 1
        family_counts[str(pick["semantic_family_key"])] += 1
        source_theme_counts[str(pick["source_theme"])] += 1
        target_theme_counts[str(pick["target_theme"])] += 1
        theme_pair_counts[str(pick["theme_pair_key"])] += 1
        remaining = remaining[~(remaining["u"].astype(str).eq(str(pick["u"])) & remaining["v"].astype(str).eq(str(pick["v"])))].copy()

    top_out = pd.DataFrame(selected_rows).reset_index(drop=True)
    top_out["diversified_rank"] = top_out.index + 1
    if tail.empty:
        return top_out

    tail = tail.copy()
    tail["diversified_rank"] = range(len(top_out) + 1, len(top_out) + len(tail) + 1)
    return pd.concat([top_out, tail], ignore_index=True)


def _coverage_stats(df: pd.DataFrame, prefix: str) -> dict[str, Any]:
    n = len(df)
    target_counts = df["target_label"].astype(str).value_counts() if n else pd.Series(dtype=float)
    return {
        f"{prefix}_rows": int(n),
        f"{prefix}_unique_theme_pair_keys": int(df["theme_pair_key"].astype(str).nunique()) if n else 0,
        f"{prefix}_unique_semantic_family_keys": int(df["semantic_family_key"].astype(str).nunique()) if n else 0,
        f"{prefix}_top_target_share": float(target_counts.iloc[0] / n) if n and not target_counts.empty else 0.0,
        f"{prefix}_co2_centered_share": float(df["co2_centered"].mean()) if n else 0.0,
    }


def _metrics_for(ranked_df: pd.DataFrame, positives: set[tuple[str, str]], rank_col: str, score_col: str, k_values: list[int]) -> dict[str, float]:
    tmp = ranked_df[["u", "v", score_col, rank_col]].copy().rename(columns={score_col: "score", rank_col: "rank"})
    tmp = tmp.sort_values("rank", ascending=True).reset_index(drop=True)
    return evaluate_binary_ranking(tmp, positives=positives, k_values=k_values)


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    k_values = _parse_int_list(args.k_values)

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    if args.candidate_family_mode:
        cfg.candidate_family_mode = str(args.candidate_family_mode)
    if args.path_to_direct_scope:
        cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_path = Path(args.paper_meta_path)
    paper_meta_df = pd.read_parquet(paper_meta_path) if paper_meta_path.exists() else None
    label_map = _load_label_map(corpus_df, args.concepts_csv)

    panel_cache = Path(args.panel_cache)
    if panel_cache.exists():
        panel_df = pd.read_parquet(panel_cache)
    else:
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            cutoff_years=[int(x.strip()) for x in str(args.cutoff_years).split(",") if x.strip()],
            horizons=[int(x.strip()) for x in str(args.horizons).split(",") if x.strip()] if str(args.horizons).strip() else sorted(pd.read_csv(args.tuning_best_path)["horizon"].dropna().astype(int).unique().tolist()),
            pool_sizes=[int(args.pool_size)],
            paper_meta_df=paper_meta_df,
        )
        panel_cache.parent.mkdir(parents=True, exist_ok=True)
        panel_df.to_parquet(panel_cache, index=False)

    best_df = pd.read_csv(args.tuning_best_path)
    benchmark_summary_df = pd.read_csv(args.benchmark_summary_path)
    pool_flag = f"in_pool_{int(args.pool_size)}"
    if pool_flag not in panel_df.columns:
        raise SystemExit(f"Missing pool flag {pool_flag} in historical panel.")

    backtest_rows: list[dict[str, Any]] = []
    example_rows: list[pd.DataFrame] = []

    for best in best_df.itertuples(index=False):
        horizon = int(best.horizon)
        feature_family = str(best.feature_family)
        model_kind = str(best.model_kind)
        alpha = float(best.alpha)
        horizon_df = panel_df[(panel_df["horizon"] == horizon) & (panel_df[pool_flag].astype(int) == 1)].copy()
        if horizon_df.empty:
            continue
        for cutoff_t in sorted(horizon_df["cutoff_year_t"].dropna().unique()):
            eval_rows = horizon_df[horizon_df["cutoff_year_t"] == int(cutoff_t)].copy()
            train_rows = horizon_df[horizon_df["cutoff_year_t"] < int(cutoff_t)].copy()
            if eval_rows.empty or train_rows.empty or train_rows["appears_within_h"].nunique() < 2:
                continue
            feature_names = [c for c in _feature_list(feature_family) if c in train_rows.columns and c in eval_rows.columns]
            if not feature_names:
                continue
            model = _fit_model(model_kind=model_kind, train_rows=train_rows, feature_names=feature_names, alpha=alpha)
            if model is None:
                continue
            scored = score_with_reranker(eval_rows, model).rename(columns={"score": "reranker_score", "rank": "reranker_rank"})
            merged = eval_rows.merge(scored, on=["u", "v"], how="left")
            merged = _annotate_keys(merged, label_map=label_map)
            merged = merged.sort_values(["reranker_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
            diversified = _diversify(merged, diversify_window=int(args.diversify_window))

            positives = {(str(row.u), str(row.v)) for row in eval_rows[eval_rows["appears_within_h"].astype(int) == 1][["u", "v"]].itertuples(index=False)}
            orig_metrics = _metrics_for(merged, positives=positives, rank_col="reranker_rank", score_col="reranker_score", k_values=k_values)
            div_metrics = _metrics_for(diversified, positives=positives, rank_col="diversified_rank", score_col="reranker_score", k_values=k_values)
            top50_orig = merged.head(50)
            top50_div = diversified.head(50)
            top100_orig = merged.head(100)
            top100_div = diversified.head(100)

            row = {
                "horizon": horizon,
                "cutoff_year_t": int(cutoff_t),
                "candidate_family_mode": str(cfg.candidate_family_mode),
                "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
                "concentration_variant": "diversification_only",
                "diversify_window": int(args.diversify_window),
                "model_kind": model_kind,
                "feature_family": feature_family,
                "alpha": alpha,
                "n_eval_rows": int(len(eval_rows)),
                "n_positives": int(len(positives)),
                "reranker_precision_at_50": float(orig_metrics.get("precision_at_50", 0.0)),
                "reranker_precision_at_100": float(orig_metrics.get("precision_at_100", 0.0)),
                "reranker_recall_at_100": float(orig_metrics.get("recall_at_100", 0.0)),
                "reranker_mrr": float(orig_metrics.get("mrr", 0.0)),
                "diversified_precision_at_50": float(div_metrics.get("precision_at_50", 0.0)),
                "diversified_precision_at_100": float(div_metrics.get("precision_at_100", 0.0)),
                "diversified_recall_at_100": float(div_metrics.get("recall_at_100", 0.0)),
                "diversified_mrr": float(div_metrics.get("mrr", 0.0)),
                "delta_precision_at_50": float(div_metrics.get("precision_at_50", 0.0) - orig_metrics.get("precision_at_50", 0.0)),
                "delta_precision_at_100": float(div_metrics.get("precision_at_100", 0.0) - orig_metrics.get("precision_at_100", 0.0)),
                "delta_recall_at_100": float(div_metrics.get("recall_at_100", 0.0) - orig_metrics.get("recall_at_100", 0.0)),
                "delta_mrr": float(div_metrics.get("mrr", 0.0) - orig_metrics.get("mrr", 0.0)),
            }
            row.update(_coverage_stats(top50_orig, "top50_reranker"))
            row.update(_coverage_stats(top50_div, "top50_diversified"))
            row.update(_coverage_stats(top100_orig, "top100_reranker"))
            row.update(_coverage_stats(top100_div, "top100_diversified"))
            row["top50_theme_pair_gain"] = int(row["top50_diversified_unique_theme_pair_keys"] - row["top50_reranker_unique_theme_pair_keys"])
            row["top50_semantic_family_gain"] = int(row["top50_diversified_unique_semantic_family_keys"] - row["top50_reranker_unique_semantic_family_keys"])
            row["top100_theme_pair_gain"] = int(row["top100_diversified_unique_theme_pair_keys"] - row["top100_reranker_unique_theme_pair_keys"])
            row["top100_semantic_family_gain"] = int(row["top100_diversified_unique_semantic_family_keys"] - row["top100_reranker_unique_semantic_family_keys"])
            row["top100_top_target_share_delta"] = float(row["top100_diversified_top_target_share"] - row["top100_reranker_top_target_share"])
            row["top100_co2_share_delta"] = float(row["top100_diversified_co2_centered_share"] - row["top100_reranker_co2_centered_share"])
            backtest_rows.append(row)

            examples = diversified.head(10).copy()
            examples["cutoff_year_t"] = int(cutoff_t)
            examples["horizon"] = horizon
            examples["model_kind"] = model_kind
            examples["feature_family"] = feature_family
            example_rows.append(
                examples[
                    [
                        "cutoff_year_t",
                        "horizon",
                        "model_kind",
                        "feature_family",
                        "u",
                        "v",
                        "source_label",
                        "target_label",
                        "reranker_rank",
                        "diversified_rank",
                        "theme_pair_key",
                        "semantic_family_key",
                    ]
                ]
            )

    if not backtest_rows:
        raise SystemExit("No diversification backtest rows were produced.")

    backtest_df = pd.DataFrame(backtest_rows).sort_values(["horizon", "cutoff_year_t"]).reset_index(drop=True)
    examples_df = pd.concat(example_rows, ignore_index=True) if example_rows else pd.DataFrame()
    backtest_df.to_csv(out_dir / "reranker_diversification_by_cutoff.csv", index=False)
    if not examples_df.empty:
        examples_df.to_csv(out_dir / "diversified_top10_examples.csv", index=False)

    summary_df = (
        backtest_df.groupby("horizon", as_index=False)
        .agg(
            candidate_family_mode=("candidate_family_mode", "first"),
            path_to_direct_scope=("path_to_direct_scope", "first"),
            concentration_variant=("concentration_variant", "first"),
            diversify_window=("diversify_window", "first"),
            mean_reranker_precision_at_100=("reranker_precision_at_100", "mean"),
            mean_diversified_precision_at_100=("diversified_precision_at_100", "mean"),
            mean_reranker_recall_at_100=("reranker_recall_at_100", "mean"),
            mean_diversified_recall_at_100=("diversified_recall_at_100", "mean"),
            mean_reranker_mrr=("reranker_mrr", "mean"),
            mean_diversified_mrr=("diversified_mrr", "mean"),
            mean_delta_precision_at_100=("delta_precision_at_100", "mean"),
            mean_delta_recall_at_100=("delta_recall_at_100", "mean"),
            mean_delta_mrr=("delta_mrr", "mean"),
            mean_top100_reranker_unique_theme_pair_keys=("top100_reranker_unique_theme_pair_keys", "mean"),
            mean_top100_diversified_unique_theme_pair_keys=("top100_diversified_unique_theme_pair_keys", "mean"),
            mean_top100_reranker_unique_semantic_family_keys=("top100_reranker_unique_semantic_family_keys", "mean"),
            mean_top100_diversified_unique_semantic_family_keys=("top100_diversified_unique_semantic_family_keys", "mean"),
            mean_top50_theme_pair_gain=("top50_theme_pair_gain", "mean"),
            mean_top100_theme_pair_gain=("top100_theme_pair_gain", "mean"),
            mean_top100_semantic_family_gain=("top100_semantic_family_gain", "mean"),
            mean_top100_top_target_share_delta=("top100_top_target_share_delta", "mean"),
            mean_top100_co2_share_delta=("top100_co2_share_delta", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values("horizon")
    )
    summary_df.to_csv(out_dir / "reranker_diversification_summary.csv", index=False)
    recommended_df = summary_df.copy()
    recommended_df["sink_start_pct"] = 0.995
    recommended_df["sink_lambda"] = 0.0
    recommended_df["repeat_log_lambda"] = 0.0
    recommended_df["repeat_linear_lambda"] = 0.0
    recommended_df["config_id"] = recommended_df["diversify_window"].map(lambda w: f"diversification_only_w{int(w)}")
    recommended_df[
        [
            "horizon",
            "candidate_family_mode",
            "path_to_direct_scope",
            "concentration_variant",
            "config_id",
            "diversify_window",
            "sink_start_pct",
            "sink_lambda",
            "repeat_log_lambda",
            "repeat_linear_lambda",
            "mean_diversified_precision_at_100",
            "mean_diversified_recall_at_100",
            "mean_diversified_mrr",
            "mean_top100_diversified_unique_theme_pair_keys",
            "mean_top100_diversified_unique_semantic_family_keys",
            "mean_top100_top_target_share_delta",
            "n_cutoffs",
        ]
    ].to_csv(out_dir / "recommended_diversification_only_configs.csv", index=False)

    comparison_rows: list[dict[str, Any]] = []
    for row in summary_df.itertuples(index=False):
        horizon_block = benchmark_summary_df[benchmark_summary_df["horizon"] == int(row.horizon)].copy()
        for comp in ["degree_recency", "pref_attach", "directed_closure"]:
            comp_row = horizon_block[horizon_block["model"] == comp]
            if comp_row.empty:
                continue
            comp_row = comp_row.iloc[0]
            comparison_rows.append(
                {
                    "horizon": int(row.horizon),
                    "comparison_model": comp,
                    "delta_precision_at_100_vs_diversified_reranker": float(row.mean_diversified_precision_at_100 - comp_row["mean_precision_at_100"]),
                    "delta_recall_at_100_vs_diversified_reranker": float(row.mean_diversified_recall_at_100 - comp_row["mean_recall_at_100"]),
                    "delta_mrr_vs_diversified_reranker": float(row.mean_diversified_mrr - comp_row["mean_mrr"]),
                }
            )
    compare_df = pd.DataFrame(
        comparison_rows,
        columns=[
            "horizon",
            "comparison_model",
            "delta_precision_at_100_vs_diversified_reranker",
            "delta_recall_at_100_vs_diversified_reranker",
            "delta_mrr_vs_diversified_reranker",
        ],
    )
    compare_df.to_csv(out_dir / "reranker_diversification_vs_transparent.csv", index=False)

    review_lines = [
        "# Reranker Diversification Backtest",
        "",
        "This pass tests whether the light shortlist-diversification rule can sit on top of the best learned reranker without undoing the rescued benchmark performance.",
        "",
    ]
    for row in summary_df.itertuples(index=False):
        review_lines.extend(
            [
                f"## Horizon {int(row.horizon)}",
                f"- reranker precision@100: `{float(row.mean_reranker_precision_at_100):.3f}`",
                f"- diversified reranker precision@100: `{float(row.mean_diversified_precision_at_100):.3f}`",
                f"- delta precision@100: `{float(row.mean_delta_precision_at_100):+.3f}`",
                f"- delta recall@100: `{float(row.mean_delta_recall_at_100):+.6f}`",
                f"- delta MRR: `{float(row.mean_delta_mrr):+.6f}`",
                f"- mean top-50 theme-pair gain: `{float(row.mean_top50_theme_pair_gain):.2f}`",
                f"- mean top-100 theme-pair gain: `{float(row.mean_top100_theme_pair_gain):.2f}`",
                f"- mean top-100 top-target share delta: `{float(row.mean_top100_top_target_share_delta):+.3f}`",
                f"- mean top-100 CO2 share delta: `{float(row.mean_top100_co2_share_delta):+.3f}`",
                "",
            ]
        )
    (out_dir / "reranker_diversification_review.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")

    summary_payload = {
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "horizons": sorted(summary_df["horizon"].astype(int).tolist()),
        "n_cutoffs": int(backtest_df["cutoff_year_t"].nunique()),
        "diversify_window": int(args.diversify_window),
        "mean_delta_precision_at_100_by_horizon": {
            str(int(row.horizon)): float(row.mean_delta_precision_at_100) for row in summary_df.itertuples(index=False)
        },
        "mean_top50_theme_pair_gain_by_horizon": {
            str(int(row.horizon)): float(row.mean_top50_theme_pair_gain) for row in summary_df.itertuples(index=False)
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Reranker Diversification Note",
        "",
        "## Question",
        "",
        "Can a light diversification layer widen idea coverage on the historical reranker benchmark without giving back the rescued benchmark performance?",
        "",
    ]
    for row in summary_df.itertuples(index=False):
        horizon_compare = compare_df[compare_df["horizon"] == int(row.horizon)].copy()
        if horizon_compare.empty:
            beats_p_text = "not evaluated in this pass"
            beats_r_text = "not evaluated in this pass"
            beats_m_text = "not evaluated in this pass"
        else:
            beats_p = horizon_compare[horizon_compare["delta_precision_at_100_vs_diversified_reranker"] > 0]["comparison_model"].tolist()
            beats_r = horizon_compare[horizon_compare["delta_recall_at_100_vs_diversified_reranker"] > 0]["comparison_model"].tolist()
            beats_m = horizon_compare[horizon_compare["delta_mrr_vs_diversified_reranker"] > 0]["comparison_model"].tolist()
            beats_p_text = ", ".join(beats_p) if beats_p else "none"
            beats_r_text = ", ".join(beats_r) if beats_r else "none"
            beats_m_text = ", ".join(beats_m) if beats_m else "none"
        note_lines.extend(
            [
                f"## Horizon {int(row.horizon)}",
                f"- diversified reranker precision@100: `{float(row.mean_diversified_precision_at_100):.3f}`",
                f"- diversified reranker recall@100: `{float(row.mean_diversified_recall_at_100):.6f}`",
                f"- diversified reranker MRR: `{float(row.mean_diversified_mrr):.6f}`",
                f"- delta precision@100 vs undiversified reranker: `{float(row.mean_delta_precision_at_100):+.3f}`",
                f"- delta recall@100 vs undiversified reranker: `{float(row.mean_delta_recall_at_100):+.6f}`",
                f"- delta MRR vs undiversified reranker: `{float(row.mean_delta_mrr):+.6f}`",
                f"- still beats strong transparent baselines on precision@100: {beats_p_text}",
                f"- still beats strong transparent baselines on recall@100: {beats_r_text}",
                f"- still beats strong transparent baselines on MRR: {beats_m_text}",
                f"- mean top-50 theme-pair gain: `{float(row.mean_top50_theme_pair_gain):.2f}`",
                f"- mean top-100 top-target share delta: `{float(row.mean_top100_top_target_share_delta):+.3f}`",
                "",
            ]
        )

    note_lines.extend(
        [
            "## Interpretation",
            "",
            "This is a post-ranking screening layer, not a new benchmark model. The right question is whether it widens idea coverage at an acceptable cost once the reranker has already done the hard ranking work.",
            "",
            "## Recommendation",
            "",
            "If the performance losses remain modest while theme coverage improves, present diversification as a light screening extension rather than as part of the benchmark winner itself.",
        ]
    )
    Path(args.note_path).write_text("\n".join(note_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
