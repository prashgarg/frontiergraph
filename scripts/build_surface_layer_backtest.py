from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_current_reranked_frontier import (
    SurfaceLayerConfig,
    _annotate_mediators_json,
    _annotate_paths_json,
    _annotate_surface_keys,
    _apply_sink_regularizer,
    _apply_surface_shortlist_layer,
    _compute_sink_targets,
    _concept_metadata_map,
    _endpoint_flag_reasons,
    _flag_penalty,
    _load_sink_regularizer_configs,
    _mediator_flag_reasons,
)
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


STATIC_PARAM_ORDER = [
    "top_window",
    "broad_endpoint_start_pct",
    "broad_endpoint_lambda",
    "resolution_floor",
    "resolution_lambda",
    "generic_endpoint_lambda",
    "mediator_specificity_floor",
    "mediator_specificity_lambda",
    "textbook_like_start_pct",
    "textbook_like_lambda",
]

DYNAMIC_PARAM_ORDER = [
    "source_repeat_lambda",
    "target_repeat_lambda",
    "family_repeat_lambda",
    "theme_repeat_lambda",
    "theme_pair_repeat_lambda",
    "broad_repeat_start_pct",
    "broad_repeat_lambda",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune and backtest the post-frontier surface layer on the frozen research-allocation graph.")
    parser.add_argument("--corpus", default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet", dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best-config", default="outputs/paper/69_v2_2_effective_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper-meta", default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--tuning-best", default="outputs/paper/83_quality_confirm_path_to_direct_effective/tuning_best_configs.csv", dest="tuning_best_path")
    parser.add_argument("--panel-cache", default="outputs/paper/84_surface_layer_backtest_path_to_direct/historical_feature_panel.parquet", dest="panel_cache")
    parser.add_argument("--concentration-configs", default="outputs/paper/77_method_v2_concentration_path_to_direct/selected_concentration/recommended_concentration_configs.csv", dest="concentration_configs")
    parser.add_argument("--cutoff-years", default="2000,2005,2010,2015", dest="cutoff_years")
    parser.add_argument("--horizons", default="5,10,15", dest="horizons")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument("--pool-size", type=int, default=5000, dest="pool_size")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pairwise-negatives-per-positive", type=int, default=2, dest="pairwise_negatives_per_positive")
    parser.add_argument("--pairwise-max-pairs-per-cutoff", type=int, default=2000, dest="pairwise_max_pairs_per_cutoff")
    parser.add_argument("--out", default="outputs/paper/84_surface_layer_backtest_path_to_direct", dest="out_dir")
    return parser.parse_args()


def _parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _fit_model(
    model_kind: str,
    train_rows: pd.DataFrame,
    feature_names: list[str],
    alpha: float,
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
):
    if model_kind == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if model_kind == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=int(pairwise_negatives_per_positive),
            max_pairs_per_cutoff=int(pairwise_max_pairs_per_cutoff),
            seed=int(seed),
        )
    raise ValueError(f"Unsupported model_kind: {model_kind}")


def _config_to_id(cfg: SurfaceLayerConfig) -> str:
    payload = {name: getattr(cfg, name) for name in STATIC_PARAM_ORDER + DYNAMIC_PARAM_ORDER}
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def _distance_from_defaults(cfg: SurfaceLayerConfig, defaults: SurfaceLayerConfig) -> float:
    distance = 0.0
    for name in STATIC_PARAM_ORDER + DYNAMIC_PARAM_ORDER:
        distance += abs(float(getattr(cfg, name)) - float(getattr(defaults, name)))
    return float(distance)


def _coalesce_merge_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        left = f"{col}_x"
        right = f"{col}_y"
        if col in out.columns:
            continue
        if left in out.columns and right in out.columns:
            out[col] = out[right].combine_first(out[left])
        elif right in out.columns:
            out[col] = out[right]
        elif left in out.columns:
            out[col] = out[left]
        drop_cols = [name for name in [left, right] if name in out.columns]
        if drop_cols:
            out = out.drop(columns=drop_cols)
    return out


def _diagnostic_stats(df: pd.DataFrame, prefix: str, cfg: SurfaceLayerConfig, top_k: int = 100) -> dict[str, Any]:
    required_cols = {
        "theme_pair_key",
        "semantic_family_key",
        "endpoint_broadness_pct",
        "endpoint_broadness_raw",
        "endpoint_resolution_score",
        "paper_surface_penalty",
        "generic_mediator_penalty",
        "textbook_like_penalty",
    }
    work = df.copy()
    if not work.empty and any(col not in work.columns for col in required_cols):
        enriched = _apply_surface_shortlist_layer(work.copy(), cfg)
        merge_cols = [col for col in required_cols if col in enriched.columns and col not in work.columns]
        if merge_cols:
            work = work.merge(enriched[["u", "v"] + merge_cols], on=["u", "v"], how="left")
    work = _coalesce_merge_columns(work, list(required_cols))
    top = work.head(int(top_k)).copy()
    if not top.empty and ("theme_pair_key" not in top.columns or "semantic_family_key" not in top.columns):
        top = _annotate_surface_keys(top)
    for col in required_cols:
        if col not in top.columns:
            top[col] = 0.0
    target_counts = top["v_label"].astype(str).value_counts()
    return {
        f"{prefix}_unique_theme_pair_keys": int(top["theme_pair_key"].astype(str).nunique()) if not top.empty else 0,
        f"{prefix}_unique_semantic_family_keys": int(top["semantic_family_key"].astype(str).nunique()) if not top.empty else 0,
        f"{prefix}_unique_sources": int(top["u_label"].astype(str).nunique()) if not top.empty else 0,
        f"{prefix}_unique_targets": int(top["v_label"].astype(str).nunique()) if not top.empty else 0,
        f"{prefix}_top_target_share": float(target_counts.iloc[0] / len(top)) if len(top) and not target_counts.empty else 0.0,
        f"{prefix}_green_share": float(top["theme_pair_key"].astype(str).str.contains("environment_climate").mean()) if len(top) else 0.0,
        f"{prefix}_wtp_share": float(top["semantic_family_key"].astype(str).str.contains("willingness to pay").mean()) if len(top) else 0.0,
        f"{prefix}_broad_endpoint_share": float((top["endpoint_broadness_pct"].astype(float) >= float(cfg.broad_endpoint_start_pct)).mean()) if len(top) else 0.0,
        f"{prefix}_generic_endpoint_share": float((top["surface_penalty"].astype(float) > 0).mean()) if len(top) else 0.0,
        f"{prefix}_generic_mediator_share": float((top["generic_mediator_penalty"].astype(float) > 0).mean()) if len(top) else 0.0,
        f"{prefix}_textbook_like_share": float((top["textbook_like_penalty"].astype(float) > 0).mean()) if len(top) else 0.0,
        f"{prefix}_mean_endpoint_broadness": float(top["endpoint_broadness_raw"].astype(float).mean()) if len(top) else 0.0,
        f"{prefix}_mean_endpoint_resolution": float(top["endpoint_resolution_score"].astype(float).mean()) if len(top) else 0.0,
        f"{prefix}_mean_surface_penalty": float(top["paper_surface_penalty"].astype(float).mean()) if len(top) else 0.0,
    }


def _metric_stats(ranked_df: pd.DataFrame, positives: set[tuple[str, str]]) -> dict[str, float]:
    tmp = ranked_df[["u", "v", "score", "rank"]].copy()
    tmp = tmp.sort_values("rank", ascending=True).reset_index(drop=True)
    return evaluate_binary_ranking(tmp, positives=positives, k_values=[100])


def _selection_sort_key(row: pd.Series, defaults: SurfaceLayerConfig) -> tuple[Any, ...]:
    return (
        float(row["mean_surface_top100_top_target_share"]),
        -float(row["mean_surface_top100_unique_theme_pair_keys"]),
        float(row["mean_surface_top100_broad_endpoint_share"]),
        float(row["mean_surface_top100_textbook_like_share"]),
        float(row["mean_surface_top100_generic_mediator_share"]),
        float(row["distance_from_defaults"]),
    )


def _static_config_id(cfg: SurfaceLayerConfig) -> str:
    payload = {name: getattr(cfg, name) for name in STATIC_PARAM_ORDER}
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def _prepare_surface_annotations(df: pd.DataFrame, cfg: SurfaceLayerConfig) -> pd.DataFrame:
    ordered = _annotate_surface_keys(df).sort_values(["frontier_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True).copy()
    if "endpoint_broadness_raw" in ordered.columns:
        broadness = ordered["endpoint_broadness_raw"].astype(float).fillna(0.0)
    else:
        source_deg = ordered["source_support_out_degree"].astype(float).fillna(0.0) if "source_support_out_degree" in ordered.columns else 0.0
        target_deg = ordered["target_support_in_degree"].astype(float).fillna(0.0) if "target_support_in_degree" in ordered.columns else 0.0
        broadness = pd.Series(source_deg, index=ordered.index).map(lambda x: math.log1p(float(x))) + pd.Series(target_deg, index=ordered.index).map(lambda x: math.log1p(float(x)))
        ordered["endpoint_broadness_raw"] = broadness.astype(float)
    if len(ordered) > 1:
        ordered["endpoint_broadness_pct"] = broadness.rank(method="average", pct=True)
    else:
        ordered["endpoint_broadness_pct"] = 0.0
    width = max(1.0 - float(cfg.broad_endpoint_start_pct), 1e-9)
    ordered["broad_endpoint_excess"] = ((ordered["endpoint_broadness_pct"].astype(float) - float(cfg.broad_endpoint_start_pct)) / width).clip(lower=0.0, upper=1.0)
    ordered["broad_endpoint_penalty"] = float(cfg.broad_endpoint_lambda) * ordered["broad_endpoint_excess"].astype(float)

    if "endpoint_resolution_score" in ordered.columns:
        resolution_score = ordered["endpoint_resolution_score"].astype(float).fillna(0.0)
    elif "transparent_specificity_component" in ordered.columns:
        resolution_score = ordered["transparent_specificity_component"].astype(float).fillna(0.0).clip(lower=0.0, upper=1.0)
        ordered["endpoint_resolution_score"] = resolution_score.astype(float)
    else:
        resolution_score = (1.0 / (1.0 + broadness.astype(float))).clip(lower=0.0, upper=1.0)
        ordered["endpoint_resolution_score"] = resolution_score.astype(float)
    resolution_floor = max(float(cfg.resolution_floor), 1e-9)
    ordered["resolution_shortfall"] = ((float(cfg.resolution_floor) - resolution_score.astype(float)) / resolution_floor).clip(lower=0.0, upper=1.0)
    ordered["resolution_penalty"] = float(cfg.resolution_lambda) * ordered["resolution_shortfall"].astype(float)

    ordered["generic_endpoint_penalty"] = float(cfg.generic_endpoint_lambda) * ordered["surface_penalty"].astype(float).clip(lower=0.0)

    if "focal_mediator" in ordered.columns:
        mediator_present = ordered["focal_mediator"].astype(str).str.strip().ne("")
    elif "focal_mediator_id" in ordered.columns:
        mediator_present = ordered["focal_mediator_id"].astype(str).str.strip().ne("")
    elif "focal_mediator_label" in ordered.columns:
        mediator_present = ordered["focal_mediator_label"].astype(str).str.strip().ne("")
    else:
        mediator_present = pd.Series(False, index=ordered.index)
    mediator_spec = ordered["focal_mediator_specificity_score"].astype(float).fillna(0.5) if "focal_mediator_specificity_score" in ordered.columns else pd.Series(0.5, index=ordered.index)
    mediator_floor = max(float(cfg.mediator_specificity_floor), 1e-9)
    ordered["mediator_specificity_shortfall"] = (((float(cfg.mediator_specificity_floor) - mediator_spec) / mediator_floor).clip(lower=0.0, upper=1.0) * mediator_present.astype(float))
    mediator_flag_penalty = ordered["focal_mediator_flag_penalty"].astype(float).fillna(0.0) if "focal_mediator_flag_penalty" in ordered.columns else pd.Series(0.0, index=ordered.index)
    ordered["generic_mediator_penalty"] = float(cfg.mediator_specificity_lambda) * (
        ordered["mediator_specificity_shortfall"].astype(float) + 0.25 * mediator_flag_penalty.clip(lower=0.0, upper=2.0)
    )

    anchored_flag = (
        ordered.get("candidate_scope_bucket", pd.Series("", index=ordered.index)).astype(str).eq("anchored_progression")
        | ordered.get("candidate_subfamily", pd.Series("", index=ordered.index)).astype(str).isin(["ordered_to_causal", "causal_to_identified"])
    ).astype(float)
    textbook_width = max(1.0 - float(cfg.textbook_like_start_pct), 1e-9)
    ordered["textbook_like_broad_excess"] = (
        (ordered["endpoint_broadness_pct"].astype(float) - float(cfg.textbook_like_start_pct)) / textbook_width
    ).clip(lower=0.0, upper=1.0)
    generic_endpoint_indicator = (ordered["surface_penalty"].astype(float) > 0).astype(float)
    ordered["textbook_like_raw"] = anchored_flag * ordered["textbook_like_broad_excess"].astype(float) * pd.concat(
        [
            ordered["resolution_shortfall"].astype(float),
            ordered["mediator_specificity_shortfall"].astype(float),
            (generic_endpoint_indicator / 2.0).astype(float),
        ],
        axis=1,
    ).max(axis=1)
    ordered["textbook_like_penalty"] = float(cfg.textbook_like_lambda) * ordered["textbook_like_raw"].astype(float)
    ordered["broad_repeat_start_pct"] = float(cfg.broad_repeat_start_pct)

    ordered["paperworthiness_static_penalty"] = (
        ordered["broad_endpoint_penalty"].astype(float)
        + ordered["resolution_penalty"].astype(float)
        + ordered["generic_endpoint_penalty"].astype(float)
        + ordered["generic_mediator_penalty"].astype(float)
        + ordered["textbook_like_penalty"].astype(float)
    )
    return ordered


def _apply_surface_dynamic(prepared: pd.DataFrame, cfg: SurfaceLayerConfig) -> pd.DataFrame:
    ordered = prepared.copy()
    top_window = ordered.head(int(cfg.top_window)).copy()
    tail = ordered.iloc[int(cfg.top_window) :].copy()
    if top_window.empty:
        surfaced = tail.copy()
        surfaced["surface_rank"] = range(1, len(surfaced) + 1)
        return surfaced

    n_top = len(top_window)
    active = np.ones(n_top, dtype=bool)
    selected_idx: list[int] = []
    broad_repeat_penalties = np.zeros(n_top, dtype=float)
    dynamic_penalties = np.zeros(n_top, dtype=float)
    surface_penalties = np.zeros(n_top, dtype=float)
    surface_priorities = np.zeros(n_top, dtype=float)

    frontier_rank = top_window["frontier_rank"].astype(float).to_numpy()
    static_penalty = top_window["paperworthiness_static_penalty"].astype(float).to_numpy()
    endpoint_broadness_pct = top_window["endpoint_broadness_pct"].astype(float).to_numpy()
    broad_indicator = (endpoint_broadness_pct >= float(cfg.broad_repeat_start_pct)).astype(float)

    source_codes, _ = pd.factorize(top_window["source_family"].astype(str), sort=False)
    target_codes, _ = pd.factorize(top_window["target_family"].astype(str), sort=False)
    family_codes, _ = pd.factorize(top_window["semantic_family_key"].astype(str), sort=False)
    source_theme_codes, _ = pd.factorize(top_window["source_theme"].astype(str), sort=False)
    target_theme_codes, _ = pd.factorize(top_window["target_theme"].astype(str), sort=False)
    theme_pair_codes, _ = pd.factorize(top_window["theme_pair_key"].astype(str), sort=False)

    source_counts = np.zeros(int(source_codes.max()) + 1, dtype=float)
    target_counts = np.zeros(int(target_codes.max()) + 1, dtype=float)
    family_counts = np.zeros(int(family_codes.max()) + 1, dtype=float)
    source_theme_counts = np.zeros(int(source_theme_codes.max()) + 1, dtype=float)
    target_theme_counts = np.zeros(int(target_theme_codes.max()) + 1, dtype=float)
    theme_pair_counts = np.zeros(int(theme_pair_codes.max()) + 1, dtype=float)

    for _ in range(n_top):
        broad_repeat = broad_indicator * float(cfg.broad_repeat_lambda) * (
            source_counts[source_codes] + target_counts[target_codes]
        )
        dynamic = (
            float(cfg.source_repeat_lambda) * source_counts[source_codes]
            + float(cfg.target_repeat_lambda) * target_counts[target_codes]
            + float(cfg.family_repeat_lambda) * family_counts[family_codes]
            + float(cfg.theme_repeat_lambda) * np.maximum(source_theme_counts[source_theme_codes] - 1.0, 0.0)
            + float(cfg.theme_repeat_lambda) * np.maximum(target_theme_counts[target_theme_codes] - 1.0, 0.0)
            + float(cfg.theme_pair_repeat_lambda) * theme_pair_counts[theme_pair_codes]
            + broad_repeat
        )
        penalty = static_penalty + dynamic
        priority = frontier_rank + penalty
        priority = np.where(active, priority, np.inf)
        best_i = int(np.argmin(priority))
        active[best_i] = False
        selected_idx.append(best_i)
        broad_repeat_penalties[best_i] = broad_repeat[best_i]
        dynamic_penalties[best_i] = dynamic[best_i]
        surface_penalties[best_i] = penalty[best_i]
        surface_priorities[best_i] = priority[best_i]
        source_counts[source_codes[best_i]] += 1.0
        target_counts[target_codes[best_i]] += 1.0
        family_counts[family_codes[best_i]] += 1.0
        source_theme_counts[source_theme_codes[best_i]] += 1.0
        target_theme_counts[target_theme_codes[best_i]] += 1.0
        theme_pair_counts[theme_pair_codes[best_i]] += 1.0

    surfaced_top = top_window.iloc[selected_idx].copy().reset_index(drop=True)
    surfaced_top["broad_repeat_penalty"] = [broad_repeat_penalties[i] for i in selected_idx]
    surfaced_top["paperworthiness_dynamic_penalty"] = [dynamic_penalties[i] for i in selected_idx]
    surfaced_top["paper_surface_penalty"] = [surface_penalties[i] for i in selected_idx]
    surfaced_top["paper_surface_priority"] = [surface_priorities[i] for i in selected_idx]
    if tail.empty:
        surfaced = surfaced_top.copy()
    else:
        tail = tail.copy()
        tail["broad_repeat_penalty"] = 0.0
        tail["paperworthiness_dynamic_penalty"] = 0.0
        tail["paper_surface_penalty"] = tail["paperworthiness_static_penalty"].astype(float)
        tail["paper_surface_priority"] = tail["frontier_rank"].astype(float) + tail["paper_surface_penalty"].astype(float)
        surfaced = pd.concat([surfaced_top, tail], ignore_index=True)
    surfaced = surfaced.reset_index(drop=True)
    surfaced["surface_rank"] = surfaced.index + 1
    return surfaced


def _stage_a_static_configs(defaults: SurfaceLayerConfig) -> list[SurfaceLayerConfig]:
    grid = {
        "top_window": [100, 200, 300],
        "broad_endpoint_start_pct": [0.85, 0.90],
        "broad_endpoint_lambda": [3.0, 6.0, 9.0],
        "resolution_floor": [0.08, 0.12],
        "resolution_lambda": [2.0, 4.0, 6.0],
        "generic_endpoint_lambda": [1.0, 2.0, 3.0],
        "mediator_specificity_floor": [0.45, 0.55],
        "mediator_specificity_lambda": [1.5, 2.5, 3.5],
        "textbook_like_start_pct": [0.80, 0.85],
        "textbook_like_lambda": [2.0, 4.0, 6.0],
    }
    out: dict[str, SurfaceLayerConfig] = {_config_to_id(defaults): defaults}
    for name in STATIC_PARAM_ORDER:
        for value in grid[name]:
            candidate = replace(defaults, **{name: value})
            out[_config_to_id(candidate)] = candidate
    return list(out.values())


def _stage_b_dynamic_configs(base_cfg: SurfaceLayerConfig) -> list[SurfaceLayerConfig]:
    source_repeat = [1.0, 2.0]
    target_repeat = [2.0, 4.0]
    family_repeat = [4.0, 6.0, 8.0]
    theme_repeat = [1.0, 2.0]
    theme_pair_repeat = [2.0, 3.0, 4.0]
    broad_repeat_start = [0.85, 0.90]
    broad_repeat_lambda = [0.0, 2.0, 4.0]
    out: dict[str, SurfaceLayerConfig] = {}
    for sr in source_repeat:
        for tr in target_repeat:
            for fr in family_repeat:
                for thr in theme_repeat:
                    for tpr in theme_pair_repeat:
                        for brs in broad_repeat_start:
                            for brl in broad_repeat_lambda:
                                candidate = replace(
                                    base_cfg,
                                    source_repeat_lambda=sr,
                                    target_repeat_lambda=tr,
                                    family_repeat_lambda=fr,
                                    theme_repeat_lambda=thr,
                                    theme_pair_repeat_lambda=tpr,
                                    broad_repeat_start_pct=brs,
                                    broad_repeat_lambda=brl,
                                )
                                out[_config_to_id(candidate)] = candidate
    return list(out.values())


def _prepare_eval_blocks(
    panel_df: pd.DataFrame,
    tuning_df: pd.DataFrame,
    pool_size: int,
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
    concentration_cfgs: dict[int, Any],
    concept_meta: dict[str, dict[str, str]],
    code_to_label: dict[str, str],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for row in tuning_df.itertuples(index=False):
        horizon = int(row.horizon)
        pool_flag = f"in_pool_{int(pool_size)}"
        horizon_df = panel_df[(panel_df["horizon"] == horizon) & (panel_df[pool_flag].astype(int) == 1)].copy()
        if horizon_df.empty:
            continue
        for cutoff_t in sorted(horizon_df["cutoff_year_t"].dropna().unique()):
            eval_rows = horizon_df[horizon_df["cutoff_year_t"] == int(cutoff_t)].copy()
            train_rows = horizon_df[horizon_df["cutoff_year_t"] < int(cutoff_t)].copy()
            if eval_rows.empty or train_rows.empty or train_rows["appears_within_h"].nunique() < 2:
                continue
            feature_names = [c for c in _feature_list(str(row.feature_family)) if c in train_rows.columns and c in eval_rows.columns]
            if not feature_names:
                continue
            model = _fit_model(
                model_kind=str(row.model_kind),
                train_rows=train_rows,
                feature_names=feature_names,
                alpha=float(row.alpha),
                pairwise_negatives_per_positive=pairwise_negatives_per_positive,
                pairwise_max_pairs_per_cutoff=pairwise_max_pairs_per_cutoff,
                seed=seed + horizon + int(cutoff_t),
            )
            scored = score_with_reranker(eval_rows, model).rename(columns={"score": "reranker_score", "rank": "reranker_rank"})
            merged = eval_rows.merge(scored, on=["u", "v"], how="left")
            merged["u_label"] = merged.get("source_label", merged["u"].astype(str)).astype(str)
            merged["v_label"] = merged.get("target_label", merged["v"].astype(str)).astype(str)
            if "top_mediators_json" in merged.columns:
                merged["top_mediators_json"] = merged["top_mediators_json"].map(lambda raw: _annotate_mediators_json(raw, code_to_label))
            if "top_paths_json" in merged.columns:
                merged["top_paths_json"] = merged["top_paths_json"].map(lambda raw: _annotate_paths_json(raw, code_to_label))
            merged["u_endpoint_flags"] = merged["u"].astype(str).map(lambda code: "|".join(_endpoint_flag_reasons(code, concept_meta)))
            merged["v_endpoint_flags"] = merged["v"].astype(str).map(lambda code: "|".join(_endpoint_flag_reasons(code, concept_meta)))
            merged["u_endpoint_penalty"] = merged["u_endpoint_flags"].map(_flag_penalty)
            merged["v_endpoint_penalty"] = merged["v_endpoint_flags"].map(_flag_penalty)
            merged["surface_penalty"] = merged["u_endpoint_penalty"].astype(int) + merged["v_endpoint_penalty"].astype(int)
            merged["surface_flagged"] = (merged["surface_penalty"].astype(int) > 0).astype(int)
            mediator_col = "focal_mediator"
            if mediator_col not in merged.columns and "focal_mediator_id" in merged.columns:
                mediator_col = "focal_mediator_id"
            if mediator_col in merged.columns:
                merged["focal_mediator_flags"] = merged[mediator_col].astype(str).map(lambda code: "|".join(_mediator_flag_reasons(code, concept_meta)))
                merged["focal_mediator_flag_penalty"] = merged["focal_mediator_flags"].map(_flag_penalty)
            else:
                merged["focal_mediator_flags"] = ""
                merged["focal_mediator_flag_penalty"] = 0

            regularizer_cfg = concentration_cfgs.get(horizon)
            if regularizer_cfg is not None:
                sink_targets = _compute_sink_targets(merged)
                merged = merged.merge(sink_targets, on="v", how="left")
                merged["sink_score"] = merged["sink_score"].fillna(0.0)
                merged["sink_score_pct"] = merged["sink_score_pct"].fillna(0.0)
                merged = _apply_sink_regularizer(merged, regularizer_cfg, rank_col="reranker_rank", score_col="reranker_score")
                merged["frontier_rank"] = merged["regularized_rank"].astype(int)
            else:
                merged["sink_score"] = 0.0
                merged["sink_score_pct"] = 0.0
                merged["sink_excess"] = 0.0
                merged["sink_penalty"] = 0.0
                merged["base_priority"] = 0.0
                merged["diversification_penalty"] = 0.0
                merged["regularized_priority"] = 0.0
                merged["regularized_rank"] = merged["reranker_rank"].astype(int)
                merged["frontier_rank"] = merged["reranker_rank"].astype(int)

            positives = {
                (str(r.u), str(r.v))
                for r in eval_rows[eval_rows["appears_within_h"].astype(int) == 1][["u", "v"]].itertuples(index=False)
            }
            blocks.append(
                {
                    "horizon": horizon,
                    "cutoff_year_t": int(cutoff_t),
                    "model_kind": str(row.model_kind),
                    "feature_family": str(row.feature_family),
                    "alpha": float(row.alpha),
                    "pool_size": int(pool_size),
                    "base_df": merged.sort_values(["frontier_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True),
                    "positives": positives,
                }
            )
    return blocks


def _evaluate_surface_configs(
    eval_blocks: list[dict[str, Any]],
    cfgs: list[SurfaceLayerConfig],
    defaults: SurfaceLayerConfig,
    stage_name: str,
    allowed_horizons_by_config: dict[str, set[int]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff_rows: list[dict[str, Any]] = []
    diag_rows: list[dict[str, Any]] = []
    prepared_cache: dict[tuple[str, int, int], pd.DataFrame] = {}
    for cfg in cfgs:
        config_id = _config_to_id(cfg)
        static_id = _static_config_id(cfg)
        allowed_horizons = None if allowed_horizons_by_config is None else allowed_horizons_by_config.get(config_id)
        for block in eval_blocks:
            if allowed_horizons is not None and int(block["horizon"]) not in allowed_horizons:
                continue
            cache_key = (static_id, int(block["horizon"]), int(block["cutoff_year_t"]))
            if cache_key not in prepared_cache:
                prepared_cache[cache_key] = _prepare_surface_annotations(block["base_df"], cfg)
            surfaced = _apply_surface_dynamic(prepared_cache[cache_key], cfg)

            baseline_ranked = surfaced.sort_values(["frontier_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True).copy()
            baseline_ranked["rank"] = baseline_ranked["frontier_rank"].astype(int)
            baseline_ranked["score"] = -baseline_ranked["frontier_rank"].astype(float)
            baseline_metrics = _metric_stats(baseline_ranked, positives=block["positives"])

            surfaced_ranked = surfaced.sort_values(["surface_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True).copy()
            surfaced_ranked["rank"] = surfaced_ranked["surface_rank"].astype(int)
            surfaced_ranked["score"] = -surfaced_ranked["surface_rank"].astype(float)
            surface_metrics = _metric_stats(surfaced_ranked, positives=block["positives"])

            baseline_diag = _diagnostic_stats(baseline_ranked, "baseline_top100", cfg)
            surface_diag = _diagnostic_stats(surfaced_ranked, "surface_top100", cfg)

            row = {
                "stage": stage_name,
                "config_id": config_id,
                "horizon": int(block["horizon"]),
                "cutoff_year_t": int(block["cutoff_year_t"]),
                "model_kind": str(block["model_kind"]),
                "feature_family": str(block["feature_family"]),
                "alpha": float(block["alpha"]),
                "pool_size": int(block["pool_size"]),
                "n_eval_rows": int(len(block["base_df"])),
                "n_positives": int(len(block["positives"])),
                "baseline_mrr": float(baseline_metrics.get("mrr", 0.0)),
                "surface_mrr": float(surface_metrics.get("mrr", 0.0)),
                "delta_mrr": float(surface_metrics.get("mrr", 0.0) - baseline_metrics.get("mrr", 0.0)),
                "baseline_recall_at_100": float(baseline_metrics.get("recall_at_100", 0.0)),
                "surface_recall_at_100": float(surface_metrics.get("recall_at_100", 0.0)),
                "delta_recall_at_100": float(surface_metrics.get("recall_at_100", 0.0) - baseline_metrics.get("recall_at_100", 0.0)),
                "distance_from_defaults": _distance_from_defaults(cfg, defaults),
            }
            for name in STATIC_PARAM_ORDER + DYNAMIC_PARAM_ORDER:
                row[name] = float(getattr(cfg, name))
            row.update(baseline_diag)
            row.update(surface_diag)
            cutoff_rows.append(row)

            diag_row = {
                "stage": stage_name,
                "config_id": config_id,
                "horizon": int(block["horizon"]),
                "cutoff_year_t": int(block["cutoff_year_t"]),
            }
            diag_row.update(baseline_diag)
            diag_row.update(surface_diag)
            diag_rows.append(diag_row)
    return pd.DataFrame(cutoff_rows), pd.DataFrame(diag_rows)


def _select_stage_a_top(summary_df: pd.DataFrame, defaults: SurfaceLayerConfig, top_n: int = 5) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for horizon, group in summary_df.groupby("horizon"):
        survivors = group[
            (group["mean_delta_recall_at_100"].astype(float) >= -0.002)
            & (group["mean_delta_mrr"].astype(float) >= -0.0002)
        ].copy()
        if survivors.empty:
            survivors = group.copy()
        survivors = survivors.sort_values(
            by=["mean_surface_top100_top_target_share", "mean_surface_top100_unique_theme_pair_keys", "mean_surface_top100_broad_endpoint_share", "mean_surface_top100_textbook_like_share", "mean_surface_top100_generic_mediator_share", "distance_from_defaults"],
            ascending=[True, False, True, True, True, True],
        )
        out[int(horizon)] = survivors["config_id"].head(int(top_n)).astype(str).tolist()
    return out


def _select_best(summary_df: pd.DataFrame, defaults: SurfaceLayerConfig) -> pd.DataFrame:
    keep = summary_df[
        (summary_df["mean_delta_recall_at_100"].astype(float) >= -0.002)
        & (summary_df["mean_delta_mrr"].astype(float) >= -0.0002)
    ].copy()
    if keep.empty:
        keep = summary_df.copy()
    best_rows: list[pd.Series] = []
    for horizon, group in keep.groupby("horizon"):
        sorted_group = sorted(
            [row for _, row in group.iterrows()],
            key=lambda row: _selection_sort_key(row, defaults),
        )
        best_rows.append(sorted_group[0])
    return pd.DataFrame(best_rows).sort_values("horizon").reset_index(drop=True)


def _summarize(cutoff_df: pd.DataFrame, defaults: SurfaceLayerConfig) -> pd.DataFrame:
    summary_df = (
        cutoff_df.groupby(["stage", "config_id", "horizon"], as_index=False)
        .agg(
            model_kind=("model_kind", "first"),
            feature_family=("feature_family", "first"),
            alpha=("alpha", "first"),
            pool_size=("pool_size", "first"),
            n_cutoffs=("cutoff_year_t", "nunique"),
            mean_baseline_mrr=("baseline_mrr", "mean"),
            mean_surface_mrr=("surface_mrr", "mean"),
            mean_delta_mrr=("delta_mrr", "mean"),
            mean_baseline_recall_at_100=("baseline_recall_at_100", "mean"),
            mean_surface_recall_at_100=("surface_recall_at_100", "mean"),
            mean_delta_recall_at_100=("delta_recall_at_100", "mean"),
            mean_baseline_top100_unique_theme_pair_keys=("baseline_top100_unique_theme_pair_keys", "mean"),
            mean_surface_top100_unique_theme_pair_keys=("surface_top100_unique_theme_pair_keys", "mean"),
            mean_baseline_top100_unique_semantic_family_keys=("baseline_top100_unique_semantic_family_keys", "mean"),
            mean_surface_top100_unique_semantic_family_keys=("surface_top100_unique_semantic_family_keys", "mean"),
            mean_baseline_top100_unique_sources=("baseline_top100_unique_sources", "mean"),
            mean_surface_top100_unique_sources=("surface_top100_unique_sources", "mean"),
            mean_baseline_top100_unique_targets=("baseline_top100_unique_targets", "mean"),
            mean_surface_top100_unique_targets=("surface_top100_unique_targets", "mean"),
            mean_baseline_top100_top_target_share=("baseline_top100_top_target_share", "mean"),
            mean_surface_top100_top_target_share=("surface_top100_top_target_share", "mean"),
            mean_baseline_top100_green_share=("baseline_top100_green_share", "mean"),
            mean_surface_top100_green_share=("surface_top100_green_share", "mean"),
            mean_baseline_top100_wtp_share=("baseline_top100_wtp_share", "mean"),
            mean_surface_top100_wtp_share=("surface_top100_wtp_share", "mean"),
            mean_baseline_top100_broad_endpoint_share=("baseline_top100_broad_endpoint_share", "mean"),
            mean_surface_top100_broad_endpoint_share=("surface_top100_broad_endpoint_share", "mean"),
            mean_baseline_top100_generic_endpoint_share=("baseline_top100_generic_endpoint_share", "mean"),
            mean_surface_top100_generic_endpoint_share=("surface_top100_generic_endpoint_share", "mean"),
            mean_baseline_top100_generic_mediator_share=("baseline_top100_generic_mediator_share", "mean"),
            mean_surface_top100_generic_mediator_share=("surface_top100_generic_mediator_share", "mean"),
            mean_baseline_top100_textbook_like_share=("baseline_top100_textbook_like_share", "mean"),
            mean_surface_top100_textbook_like_share=("surface_top100_textbook_like_share", "mean"),
            mean_surface_top100_mean_endpoint_broadness=("surface_top100_mean_endpoint_broadness", "mean"),
            mean_surface_top100_mean_endpoint_resolution=("surface_top100_mean_endpoint_resolution", "mean"),
            mean_surface_top100_mean_surface_penalty=("surface_top100_mean_surface_penalty", "mean"),
            distance_from_defaults=("distance_from_defaults", "first"),
            top_window=("top_window", "first"),
            broad_endpoint_start_pct=("broad_endpoint_start_pct", "first"),
            broad_endpoint_lambda=("broad_endpoint_lambda", "first"),
            resolution_floor=("resolution_floor", "first"),
            resolution_lambda=("resolution_lambda", "first"),
            generic_endpoint_lambda=("generic_endpoint_lambda", "first"),
            mediator_specificity_floor=("mediator_specificity_floor", "first"),
            mediator_specificity_lambda=("mediator_specificity_lambda", "first"),
            textbook_like_start_pct=("textbook_like_start_pct", "first"),
            textbook_like_lambda=("textbook_like_lambda", "first"),
            source_repeat_lambda=("source_repeat_lambda", "first"),
            target_repeat_lambda=("target_repeat_lambda", "first"),
            family_repeat_lambda=("family_repeat_lambda", "first"),
            theme_repeat_lambda=("theme_repeat_lambda", "first"),
            theme_pair_repeat_lambda=("theme_pair_repeat_lambda", "first"),
            broad_repeat_start_pct=("broad_repeat_start_pct", "first"),
            broad_repeat_lambda=("broad_repeat_lambda", "first"),
        )
        .sort_values(["horizon", "stage", "config_id"])
        .reset_index(drop=True)
    )
    return summary_df


def _write_summary_markdown(summary_df: pd.DataFrame, best_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Surface Layer Backtest Summary",
        "",
        "This note summarizes the balanced shortlist-quality backtest for the generic post-frontier surface layer.",
        "",
    ]
    for row in best_df.itertuples(index=False):
        lines.append(f"## Horizon {int(row.horizon)}")
        lines.append(
            f"- selected config `{row.config_id}` from stage `{row.stage}` using {row.model_kind} + {row.feature_family} (alpha={float(row.alpha):.3f})"
        )
        lines.append(
            f"- mean Recall@100: `{float(row.mean_baseline_recall_at_100):.6f} -> {float(row.mean_surface_recall_at_100):.6f}` (delta `{float(row.mean_delta_recall_at_100):+.6f}`)"
        )
        lines.append(
            f"- mean MRR: `{float(row.mean_baseline_mrr):.6f} -> {float(row.mean_surface_mrr):.6f}` (delta `{float(row.mean_delta_mrr):+.6f}`)"
        )
        lines.append(
            f"- mean top-100 top-target share: `{float(row.mean_baseline_top100_top_target_share):.3f} -> {float(row.mean_surface_top100_top_target_share):.3f}`"
        )
        lines.append(
            f"- mean top-100 unique theme pairs: `{float(row.mean_baseline_top100_unique_theme_pair_keys):.2f} -> {float(row.mean_surface_top100_unique_theme_pair_keys):.2f}`"
        )
        lines.append(
            f"- mean top-100 broad-endpoint share: `{float(row.mean_baseline_top100_broad_endpoint_share):.3f} -> {float(row.mean_surface_top100_broad_endpoint_share):.3f}`"
        )
        lines.append(
            f"- mean top-100 textbook-like share: `{float(row.mean_baseline_top100_textbook_like_share):.3f} -> {float(row.mean_surface_top100_textbook_like_share):.3f}`"
        )
        lines.append(
            f"- mean top-100 generic mediator share: `{float(row.mean_baseline_top100_generic_mediator_share):.3f} -> {float(row.mean_surface_top100_generic_mediator_share):.3f}`"
        )
        lines.append(
            f"- diagnostics only: WTP share `{float(row.mean_baseline_top100_wtp_share):.3f} -> {float(row.mean_surface_top100_wtp_share):.3f}`, green share `{float(row.mean_baseline_top100_green_share):.3f} -> {float(row.mean_surface_top100_green_share):.3f}`"
        )
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    cutoff_years = _parse_int_list(args.cutoff_years)
    horizons = _parse_int_list(args.horizons)
    defaults = SurfaceLayerConfig()

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    candidate_cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    candidate_cfg.candidate_family_mode = str(args.candidate_family_mode)
    candidate_cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None
    concept_meta = _concept_metadata_map(corpus_df)
    code_to_label = {code: payload.get("label", code) for code, payload in concept_meta.items()}

    panel_cache = Path(args.panel_cache)
    if panel_cache.exists():
        panel_df = pd.read_parquet(panel_cache)
    else:
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=candidate_cfg,
            cutoff_years=cutoff_years,
            horizons=horizons,
            pool_sizes=[int(args.pool_size)],
            paper_meta_df=paper_meta_df,
        )
        panel_cache.parent.mkdir(parents=True, exist_ok=True)
        panel_df.to_parquet(panel_cache, index=False)

    tuning_df = pd.read_csv(args.tuning_best_path)
    tuning_df = tuning_df[tuning_df["horizon"].astype(int).isin(horizons)].copy()
    if tuning_df.empty:
        raise SystemExit("No reranker configs found for requested horizons.")
    concentration_cfgs = _load_sink_regularizer_configs(args.concentration_configs)

    eval_blocks = _prepare_eval_blocks(
        panel_df=panel_df,
        tuning_df=tuning_df,
        pool_size=int(args.pool_size),
        pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
        pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
        seed=int(args.seed),
        concentration_cfgs=concentration_cfgs,
        concept_meta=concept_meta,
        code_to_label=code_to_label,
    )
    if not eval_blocks:
        raise SystemExit("No evaluation blocks were produced for the surface-layer backtest.")

    stage_a_cfgs = _stage_a_static_configs(defaults)
    stage_a_cutoff_df, stage_a_diag_df = _evaluate_surface_configs(eval_blocks, stage_a_cfgs, defaults, "stage_a")
    stage_a_summary_df = _summarize(stage_a_cutoff_df, defaults)
    stage_a_top = _select_stage_a_top(stage_a_summary_df, defaults, top_n=5)

    cfg_lookup = {_config_to_id(cfg): cfg for cfg in stage_a_cfgs}
    stage_b_cfgs: list[SurfaceLayerConfig] = []
    stage_b_allowed_horizons: dict[str, set[int]] = {}
    for horizon, config_ids in stage_a_top.items():
        for config_id in config_ids:
            base_cfg = cfg_lookup[config_id]
            for candidate in _stage_b_dynamic_configs(base_cfg):
                stage_b_cfgs.append(candidate)
                stage_b_allowed_horizons.setdefault(_config_to_id(candidate), set()).add(int(horizon))
    dedup_stage_b = {_config_to_id(cfg): cfg for cfg in stage_b_cfgs}
    stage_b_cutoff_df, stage_b_diag_df = _evaluate_surface_configs(
        eval_blocks,
        list(dedup_stage_b.values()),
        defaults,
        "stage_b",
        allowed_horizons_by_config=stage_b_allowed_horizons,
    )
    stage_b_summary_df = _summarize(stage_b_cutoff_df, defaults)

    all_cutoff_df = pd.concat([stage_a_cutoff_df, stage_b_cutoff_df], ignore_index=True)
    all_summary_df = pd.concat([stage_a_summary_df, stage_b_summary_df], ignore_index=True)
    all_diag_df = pd.concat([stage_a_diag_df, stage_b_diag_df], ignore_index=True)
    best_df = _select_best(all_summary_df, defaults)

    all_cutoff_df.to_csv(Path(out_dir) / "surface_cutoff_eval.csv", index=False)
    all_summary_df.to_csv(Path(out_dir) / "surface_summary.csv", index=False)
    all_diag_df.to_csv(Path(out_dir) / "surface_top100_diagnostics.csv", index=False)
    best_df.to_csv(Path(out_dir) / "surface_best_configs.csv", index=False)
    _write_summary_markdown(all_summary_df, best_df, Path(out_dir) / "surface_summary.md")

    summary_payload = {
        "candidate_family_mode": str(candidate_cfg.candidate_family_mode),
        "path_to_direct_scope": str(candidate_cfg.path_to_direct_scope),
        "pool_size": int(args.pool_size),
        "cutoff_years": cutoff_years,
        "horizons": horizons,
        "n_eval_blocks": len(eval_blocks),
        "stage_a_configs": len(stage_a_cfgs),
        "stage_b_configs": len(dedup_stage_b),
        "selected_config_ids_by_horizon": {str(int(row.horizon)): str(row.config_id) for row in best_df.itertuples(index=False)},
    }
    (Path(out_dir) / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
