from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.analysis.common import (
    add_candidate_family_indicator_columns,
    build_candidate_table,
    ensure_output_dir,
    first_appearance_map,
    first_path_appearance_map_for_pairs,
    restrict_positive_set_for_family,
)
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
    pref_attach_ranking_from_universe,
)
from src.utils import load_config, load_corpus


BASE_FEATURES = [
    "score",
]

FAMILY_SPLIT_FEATURES = [
    "progression_depth",
    "subfamily_fully_open_frontier",
    "subfamily_contextual_to_ordered",
    "subfamily_ordered_to_causal",
    "subfamily_causal_to_identified",
    "subfamily_ordered_direct_to_path",
    "subfamily_causal_direct_to_path",
    "subfamily_identified_direct_to_path",
    "scope_fully_open",
    "scope_contextual_progression",
    "scope_anchored_progression",
    "scope_direct_present_path_missing",
    "transparent_score_x_progression_depth",
    "provenance_x_progression_depth",
]

STRUCTURAL_FEATURES = BASE_FEATURES + [
    "path_support_norm",
    "motif_bonus_norm",
    "gap_bonus",
    "hub_penalty",
    "mediator_count",
    "motif_count",
    "cooc_count",
    "cooc_trend_norm",
    "field_same_group",
    "source_direct_out_degree",
    "target_direct_in_degree",
    "source_support_out_degree",
    "target_support_in_degree",
    "support_degree_product",
    "direct_degree_product",
]

DYNAMIC_FEATURES = STRUCTURAL_FEATURES + [
    "support_age_years",
    "recent_support_age_years",
    "source_recent_support_out_degree",
    "target_recent_support_in_degree",
    "source_recent_incident_count",
    "target_recent_incident_count",
    "source_recent_share",
    "target_recent_share",
]

COMPOSITION_FEATURES = DYNAMIC_FEATURES + [
    "source_mean_stability",
    "target_mean_stability",
    "pair_mean_stability",
    "source_evidence_diversity",
    "target_evidence_diversity",
    "pair_evidence_diversity_mean",
    "source_venue_diversity",
    "target_venue_diversity",
    "pair_venue_diversity_mean",
    "source_source_diversity",
    "target_source_diversity",
    "pair_source_diversity_mean",
    "source_mean_fwci",
    "target_mean_fwci",
    "pair_mean_fwci",
]

QUALITY_LAYER_FEATURES = [
    "source_support_total_degree",
    "target_support_total_degree",
    "source_node_age_years",
    "target_node_age_years",
    "focal_mediator_support_total_degree",
    "focal_mediator_incident_count",
    "focal_mediator_age_years",
    "endpoint_broadness_raw",
    "endpoint_resolution_score",
    "focal_mediator_broadness_raw",
    "focal_mediator_specificity_score",
    "endpoint_age_mean_years",
]

QUALITY_FEATURES = COMPOSITION_FEATURES + QUALITY_LAYER_FEATURES

BOUNDARY_GAP_FEATURES = QUALITY_FEATURES + [
    "boundary_flag",
    "gap_like_flag",
    "nearby_closure_density",
]

FEATURE_FAMILIES: dict[str, list[str]] = {
    "base": BASE_FEATURES,
    "structural": STRUCTURAL_FEATURES,
    "dynamic": DYNAMIC_FEATURES,
    "composition": COMPOSITION_FEATURES,
    "quality": QUALITY_FEATURES,
    "boundary_gap": BOUNDARY_GAP_FEATURES,
    "family_aware": STRUCTURAL_FEATURES + FAMILY_SPLIT_FEATURES,
    "family_aware_composition": COMPOSITION_FEATURES + FAMILY_SPLIT_FEATURES,
    "family_aware_quality": QUALITY_FEATURES + FAMILY_SPLIT_FEATURES,
    "family_aware_boundary_gap": BOUNDARY_GAP_FEATURES + FAMILY_SPLIT_FEATURES,
}


@dataclass
class LinearRerankerModel:
    kind: str
    feature_names: list[str]
    means: dict[str, float]
    scales: dict[str, float]
    params: dict[str, float]
    intercept: float = 0.0


def _future_set(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {edge for edge, y in first_year_map.items() if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35.0, 35.0)))


def _safe_numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(float(default)).astype(float)


def _support_graph(train_df: pd.DataFrame) -> pd.DataFrame:
    if train_df.empty:
        return pd.DataFrame(columns=["src_code", "dst_code", "paper_id", "year", "venue", "source", "evidence_type", "stability", "fwci"])
    keep = [c for c in ["src_code", "dst_code", "paper_id", "year", "venue", "source", "evidence_type", "stability", "fwci"] if c in train_df.columns]
    if "edge_kind" not in train_df.columns:
        return train_df[keep].copy()
    directed = train_df[train_df["edge_kind"] == "directed_causal"][keep].copy()
    undirected = train_df[train_df["edge_kind"] == "undirected_noncausal"][keep].copy()
    if undirected.empty:
        return directed
    rev = undirected.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
    return pd.concat([directed, undirected, rev], ignore_index=True)


def _incident_long(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["code", "paper_id", "year", "venue", "source", "evidence_type", "stability", "fwci"])
    common = [c for c in ["paper_id", "year", "venue", "source", "evidence_type", "stability", "fwci"] if c in df.columns]
    src = df[["src_code"] + common].rename(columns={"src_code": "code"})
    dst = df[["dst_code"] + common].rename(columns={"dst_code": "code"})
    out = pd.concat([src, dst], ignore_index=True)
    out["code"] = out["code"].astype(str)
    return out


def _unique_count_map(df: pd.DataFrame, group_col: str, value_col: str, out_name: str) -> pd.DataFrame:
    if df.empty or value_col not in df.columns:
        return pd.DataFrame(columns=[group_col, out_name])
    out = (
        df[[group_col, value_col]]
        .dropna()
        .astype({group_col: str, value_col: str})
        .groupby(group_col, as_index=False)
        .agg(**{out_name: (value_col, "nunique")})
    )
    return out


def _mean_map(df: pd.DataFrame, group_col: str, value_col: str, out_name: str) -> pd.DataFrame:
    if df.empty or value_col not in df.columns:
        return pd.DataFrame(columns=[group_col, out_name])
    out = (
        df[[group_col, value_col]]
        .assign(**{value_col: _safe_numeric(df[value_col])})
        .groupby(group_col, as_index=False)
        .agg(**{out_name: (value_col, "mean")})
    )
    out[group_col] = out[group_col].astype(str)
    return out


def _build_endpoint_feature_maps(
    train_df: pd.DataFrame,
    cutoff_t: int,
    paper_meta_df: pd.DataFrame | None = None,
    recent_window: int = 5,
) -> dict[str, dict[str, float]]:
    df = train_df.copy()
    if paper_meta_df is not None and not paper_meta_df.empty and "paper_id" in paper_meta_df.columns and "fwci" in paper_meta_df.columns:
        meta = paper_meta_df[["paper_id", "fwci"]].drop_duplicates("paper_id").copy()
        df = df.merge(meta, on="paper_id", how="left")
    elif "fwci" not in df.columns:
        df["fwci"] = np.nan

    support_df = _support_graph(df)
    direct_df = df[df["edge_kind"] == "directed_causal"].copy() if "edge_kind" in df.columns else df[df["is_causal"].astype(bool)].copy()
    recent_cut = int(cutoff_t) - int(recent_window)
    support_recent = support_df[support_df["year"] >= recent_cut].copy()
    direct_recent = direct_df[direct_df["year"] >= recent_cut].copy()
    incident_all = _incident_long(support_df)
    incident_recent = _incident_long(support_recent)

    maps: dict[str, dict[str, float]] = {}

    def add_series_map(name: str, series: pd.Series) -> None:
        maps[name] = {str(idx): float(val) for idx, val in series.items()}

    if not direct_df.empty:
        add_series_map("source_direct_out_degree", direct_df.groupby("src_code")["dst_code"].nunique())
        add_series_map("target_direct_in_degree", direct_df.groupby("dst_code")["src_code"].nunique())
    else:
        maps["source_direct_out_degree"] = {}
        maps["target_direct_in_degree"] = {}

    if not support_df.empty:
        out_deg = support_df.groupby("src_code")["dst_code"].nunique()
        in_deg = support_df.groupby("dst_code")["src_code"].nunique()
        add_series_map("source_support_out_degree", out_deg)
        add_series_map("target_support_in_degree", in_deg)
        add_series_map("support_total_degree", out_deg.add(in_deg, fill_value=0.0))
    else:
        maps["source_support_out_degree"] = {}
        maps["target_support_in_degree"] = {}
        maps["support_total_degree"] = {}

    if not support_recent.empty:
        add_series_map("source_recent_support_out_degree", support_recent.groupby("src_code")["dst_code"].nunique())
        add_series_map("target_recent_support_in_degree", support_recent.groupby("dst_code")["src_code"].nunique())
    else:
        maps["source_recent_support_out_degree"] = {}
        maps["target_recent_support_in_degree"] = {}

    if not incident_all.empty:
        add_series_map("incident_count", incident_all.groupby("code")["paper_id"].nunique())
        add_series_map("mean_stability", incident_all.groupby("code")["stability"].mean())
        add_series_map("evidence_diversity", incident_all.groupby("code")["evidence_type"].nunique())
        add_series_map("venue_diversity", incident_all.groupby("code")["venue"].nunique())
        add_series_map("source_diversity", incident_all.groupby("code")["source"].nunique())
        add_series_map("mean_fwci", incident_all.groupby("code")["fwci"].mean())
        add_series_map("first_seen_year", incident_all.groupby("code")["year"].min())
    else:
        for name in ["incident_count", "mean_stability", "evidence_diversity", "venue_diversity", "source_diversity", "mean_fwci", "first_seen_year"]:
            maps[name] = {}

    if not incident_recent.empty:
        add_series_map("recent_incident_count", incident_recent.groupby("code")["paper_id"].nunique())
    else:
        maps["recent_incident_count"] = {}

    return maps


def enrich_candidate_features(
    candidate_df: pd.DataFrame,
    train_df: pd.DataFrame,
    cutoff_t: int,
    paper_meta_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if candidate_df.empty:
        return candidate_df.copy()
    out = add_candidate_family_indicator_columns(candidate_df)
    maps = _build_endpoint_feature_maps(train_df=train_df, cutoff_t=cutoff_t, paper_meta_df=paper_meta_df)

    def pull(name: str, col: str) -> pd.Series:
        return out[col].astype(str).map(maps.get(name, {})).fillna(0.0).astype(float)

    out["source_direct_out_degree"] = pull("source_direct_out_degree", "u")
    out["target_direct_in_degree"] = pull("target_direct_in_degree", "v")
    out["source_support_out_degree"] = pull("source_support_out_degree", "u")
    out["target_support_in_degree"] = pull("target_support_in_degree", "v")
    out["source_support_total_degree"] = pull("support_total_degree", "u")
    out["target_support_total_degree"] = pull("support_total_degree", "v")
    out["source_recent_support_out_degree"] = pull("source_recent_support_out_degree", "u")
    out["target_recent_support_in_degree"] = pull("target_recent_support_in_degree", "v")
    out["source_incident_count"] = pull("incident_count", "u")
    out["target_incident_count"] = pull("incident_count", "v")
    out["source_recent_incident_count"] = pull("recent_incident_count", "u")
    out["target_recent_incident_count"] = pull("recent_incident_count", "v")
    out["source_mean_stability"] = pull("mean_stability", "u")
    out["target_mean_stability"] = pull("mean_stability", "v")
    out["source_evidence_diversity"] = pull("evidence_diversity", "u")
    out["target_evidence_diversity"] = pull("evidence_diversity", "v")
    out["source_venue_diversity"] = pull("venue_diversity", "u")
    out["target_venue_diversity"] = pull("venue_diversity", "v")
    out["source_source_diversity"] = pull("source_diversity", "u")
    out["target_source_diversity"] = pull("source_diversity", "v")
    out["source_mean_fwci"] = pull("mean_fwci", "u")
    out["target_mean_fwci"] = pull("mean_fwci", "v")
    out["source_node_age_years"] = np.maximum(0.0, float(cutoff_t) - pull("first_seen_year", "u"))
    out["target_node_age_years"] = np.maximum(0.0, float(cutoff_t) - pull("first_seen_year", "v"))

    mediator_key = out.get("focal_mediator_id", out.get("focal_mediator_label", pd.Series("", index=out.index))).astype(str)
    out["focal_mediator_support_total_degree"] = mediator_key.map(maps.get("support_total_degree", {})).fillna(0.0).astype(float)
    out["focal_mediator_incident_count"] = mediator_key.map(maps.get("incident_count", {})).fillna(0.0).astype(float)
    out["focal_mediator_age_years"] = np.maximum(
        0.0,
        float(cutoff_t) - mediator_key.map(maps.get("first_seen_year", {})).fillna(float(cutoff_t)).astype(float),
    )

    out["support_age_years"] = np.maximum(0.0, float(cutoff_t) - _safe_numeric(out.get("first_year_seen", pd.Series(np.nan, index=out.index))))
    out["recent_support_age_years"] = np.maximum(0.0, float(cutoff_t) - _safe_numeric(out.get("last_year_seen", pd.Series(np.nan, index=out.index))))
    out["support_degree_product"] = out["source_support_out_degree"] * out["target_support_in_degree"]
    out["direct_degree_product"] = out["source_direct_out_degree"] * out["target_direct_in_degree"]
    out["source_recent_share"] = out["source_recent_incident_count"] / np.maximum(out["source_incident_count"], 1.0)
    out["target_recent_share"] = out["target_recent_incident_count"] / np.maximum(out["target_incident_count"], 1.0)
    out["pair_mean_stability"] = 0.5 * (out["source_mean_stability"] + out["target_mean_stability"])
    out["pair_evidence_diversity_mean"] = 0.5 * (out["source_evidence_diversity"] + out["target_evidence_diversity"])
    out["pair_venue_diversity_mean"] = 0.5 * (out["source_venue_diversity"] + out["target_venue_diversity"])
    out["pair_source_diversity_mean"] = 0.5 * (out["source_source_diversity"] + out["target_source_diversity"])
    out["pair_mean_fwci"] = 0.5 * (out["source_mean_fwci"] + out["target_mean_fwci"])
    out["endpoint_broadness_raw"] = (
        0.25 * np.log1p(out["source_support_total_degree"])
        + 0.25 * np.log1p(out["target_support_total_degree"])
        + 0.25 * np.log1p(out["source_incident_count"])
        + 0.25 * np.log1p(out["target_incident_count"])
    ).astype(float)
    out["endpoint_resolution_score"] = (1.0 - _safe_numeric(out["endpoint_broadness_raw"]).rank(pct=True, method="average")).clip(0.0, 1.0)
    out["focal_mediator_broadness_raw"] = (
        np.log1p(out["focal_mediator_support_total_degree"]) + np.log1p(out["focal_mediator_incident_count"])
    ).astype(float)
    mediator_present = mediator_key.ne("") & (
        (out["focal_mediator_support_total_degree"] > 0.0) | (out["focal_mediator_incident_count"] > 0.0)
    )
    med_rank = _safe_numeric(out["focal_mediator_broadness_raw"]).rank(pct=True, method="average")
    out["focal_mediator_specificity_score"] = (1.0 - med_rank).where(mediator_present, 0.5).clip(0.0, 1.0)
    out["endpoint_age_mean_years"] = 0.5 * (out["source_node_age_years"] + out["target_node_age_years"])
    out["boundary_flag"] = ((out["field_same_group"].astype(float) <= 0.0) & (_safe_numeric(out["cooc_count"]) <= 0.0)).astype(int)
    out["gap_like_flag"] = ((_safe_numeric(out["gap_bonus"]) > 0.0) & (_safe_numeric(out["path_support_norm"]) > 0.0)).astype(int)
    out["nearby_closure_density"] = _safe_numeric(out["motif_count"]) / np.maximum(_safe_numeric(out["mediator_count"]), 1.0)
    out["transparent_score_x_progression_depth"] = _safe_numeric(out["score"]) * _safe_numeric(out["progression_depth"])
    out["provenance_x_progression_depth"] = _safe_numeric(out.get("transparent_provenance_component", 0.0)) * _safe_numeric(out["progression_depth"])

    all_feature_cols = sorted({c for cols in FEATURE_FAMILIES.values() for c in cols})
    for col in all_feature_cols:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = _safe_numeric(out[col])
    return out


def build_candidate_feature_panel(
    corpus_df: pd.DataFrame,
    cfg: Any,
    cutoff_years: list[int],
    horizons: list[int],
    pool_sizes: list[int],
    paper_meta_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if corpus_df.empty:
        return pd.DataFrame()
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    pool_sizes = sorted(set(int(k) for k in pool_sizes if int(k) > 0))
    if not pool_sizes:
        raise ValueError("pool_sizes must contain at least one positive integer")
    max_pool = int(max(pool_sizes))
    candidate_family_mode = str(getattr(cfg, "candidate_family_mode", "path_to_direct"))
    if debug_timing:
        print(
            f"[build_candidate_feature_panel] start family={candidate_family_mode} "
            f"cutoffs={cutoff_years} horizons={horizons} pools={pool_sizes}",
            flush=True,
        )
    feature_blocks: list[pd.DataFrame] = []
    target_pairs: set[tuple[str, str]] = set()

    for t in cutoff_years:
        cutoff_t0 = time.perf_counter()
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)].copy()
        if train.empty:
            if debug_timing:
                print(f"[build_candidate_feature_panel] cutoff={t} skipped empty train", flush=True)
            continue
        if debug_timing:
            print(f"[build_candidate_feature_panel] cutoff={t} train_rows={len(train):,}", flush=True)
        feature_df = build_candidate_table(train, cutoff_t=int(t), cfg=cfg)
        if feature_df.empty:
            if debug_timing:
                print(
                    f"[build_candidate_feature_panel] cutoff={t} produced empty feature table "
                    f"elapsed={time.perf_counter()-cutoff_t0:.2f}s",
                    flush=True,
                )
            continue
        feature_df = feature_df.sort_values("score", ascending=False).head(max_pool).reset_index(drop=True)
        if debug_timing:
            print(
                f"[build_candidate_feature_panel] cutoff={t} feature_rows={len(feature_df):,} "
                f"after top-{max_pool} elapsed={time.perf_counter()-cutoff_t0:.2f}s",
                flush=True,
            )
        feature_df = enrich_candidate_features(feature_df, train_df=train, cutoff_t=int(t), paper_meta_df=paper_meta_df)
        feature_df["cutoff_year_t"] = int(t)
        feature_df["transparent_rank"] = np.arange(1, len(feature_df) + 1)
        feature_df["transparent_score"] = _safe_numeric(feature_df["score"])
        for pool in pool_sizes:
            feature_df[f"in_pool_{int(pool)}"] = (feature_df["transparent_rank"] <= int(pool)).astype(int)
        edge_keys = {(str(r.u), str(r.v)) for r in feature_df[["u", "v"]].drop_duplicates().itertuples(index=False)}
        target_pairs.update(edge_keys)
        feature_blocks.append(feature_df)
        if debug_timing:
            print(
                f"[build_candidate_feature_panel] cutoff={t} complete elapsed={time.perf_counter()-cutoff_t0:.2f}s",
                flush=True,
            )

    if not feature_blocks:
        return pd.DataFrame()
    first_year_t0 = time.perf_counter()
    if candidate_family_mode == "direct_to_path":
        first_year = first_path_appearance_map_for_pairs(corpus_df, target_pairs)
    else:
        first_year = first_appearance_map(
            corpus_df,
            candidate_kind=str(getattr(cfg, "candidate_kind", "directed_causal")),
            candidate_family_mode=candidate_family_mode,
        )
    if debug_timing:
        print(
            f"[build_candidate_feature_panel] first_year_map={len(first_year):,} "
            f"targets={len(target_pairs):,} elapsed={time.perf_counter()-first_year_t0:.2f}s",
            flush=True,
        )
    rows: list[pd.DataFrame] = []
    for feature_df in feature_blocks:
        edge_keys = list(zip(feature_df["u"].astype(str), feature_df["v"].astype(str)))
        realized_year = pd.Series([first_year.get((u, v)) for u, v in edge_keys], index=feature_df.index, dtype="float")
        feature_df = feature_df.copy()
        feature_df["first_realized_year"] = realized_year
        cutoff_t = int(feature_df["cutoff_year_t"].iloc[0])
        for h in horizons:
            positives = _future_set(first_year, cutoff_t=cutoff_t, horizon_h=int(h))
            positives = restrict_positive_set_for_family(
                positives,
                candidate_pairs_df=feature_df,
                candidate_family_mode=candidate_family_mode,
            )
            part = feature_df.copy()
            part["horizon"] = int(h)
            part["appears_within_h"] = [int((u, v) in positives) for u, v in edge_keys]
            rows.append(part)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True).copy()
    all_feature_cols = sorted({c for cols in FEATURE_FAMILIES.values() for c in cols})
    for col in all_feature_cols:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = _safe_numeric(out[col])
    out["pair_id"] = out["u"].astype(str) + "->" + out["v"].astype(str)
    if debug_timing:
        print(
            f"[build_candidate_feature_panel] done rows={len(out):,} total_elapsed={time.perf_counter()-t0:.2f}s",
            flush=True,
        )
    return out


def build_path_to_direct_ripeness_panel(
    candidate_panel_df: pd.DataFrame,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    if candidate_panel_df.empty:
        return pd.DataFrame()
    horizons = sorted(set(int(h) for h in (horizons or sorted(candidate_panel_df["horizon"].unique()))))
    feature_cols = [c for c in candidate_panel_df.columns if c not in {"horizon", "appears_within_h"} and not c.startswith("appears_within_h_")]
    base = (
        candidate_panel_df[feature_cols]
        .sort_values(["cutoff_year_t", "pair_id"])
        .drop_duplicates(subset=["cutoff_year_t", "pair_id"], keep="first")
        .reset_index(drop=True)
    )
    for h in horizons:
        sub = candidate_panel_df[candidate_panel_df["horizon"] == int(h)][["cutoff_year_t", "pair_id", "appears_within_h"]].rename(
            columns={"appears_within_h": f"direct_closure_h{int(h)}"}
        )
        base = base.merge(sub, on=["cutoff_year_t", "pair_id"], how="left")
        base[f"direct_closure_h{int(h)}"] = base[f"direct_closure_h{int(h)}"].fillna(0).astype(int)
    base = base.sort_values(["pair_id", "cutoff_year_t"]).reset_index(drop=True)
    for col in ["path_support_norm", "mediator_count", "motif_bonus_norm", "nearby_closure_density"]:
        lag = base.groupby("pair_id")[col].shift(1)
        base[f"delta_{col}"] = (_safe_numeric(base[col]) - _safe_numeric(lag, default=0.0)).astype(float)
    base["ripeness_score_simple"] = (
        0.35 * _safe_numeric(base["path_support_norm"])
        + 0.20 * _safe_numeric(base["motif_bonus_norm"])
        + 0.20 * np.tanh(_safe_numeric(base["mediator_count"]) / 5.0)
        + 0.15 * np.tanh(_safe_numeric(base["delta_path_support_norm"]))
        + 0.10 * np.tanh(_safe_numeric(base["delta_mediator_count"]))
    )
    return base


def _build_direct_state(edge_df: pd.DataFrame) -> tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, set[str]], dict[str, set[str]]]:
    direct_pairs = {(str(r.src_code), str(r.dst_code)) for r in edge_df[["src_code", "dst_code"]].drop_duplicates().itertuples(index=False)}
    incoming: dict[str, set[str]] = {}
    outgoing: dict[str, set[str]] = {}
    for u, v in direct_pairs:
        outgoing.setdefault(u, set()).add(v)
        incoming.setdefault(v, set()).add(u)
    path_pairs: set[tuple[str, str]] = set()
    for w in set(incoming).intersection(outgoing):
        for u in incoming[w]:
            for v in outgoing[w]:
                if u != v:
                    path_pairs.add((u, v))
    return direct_pairs, path_pairs, incoming, outgoing


def build_direct_to_path_panel(
    corpus_df: pd.DataFrame,
    cutoff_years: list[int],
    horizons: list[int],
) -> pd.DataFrame:
    directed = corpus_df[corpus_df["edge_kind"] == "causal_claim"][["year", "src_code", "dst_code"]].copy() if "edge_kind" in corpus_df.columns else corpus_df[corpus_df["is_causal"].astype(bool)][["year", "src_code", "dst_code"]].copy()
    if directed.empty:
        return pd.DataFrame()
    first_year = first_appearance_map(
        corpus_df,
        candidate_kind="causal_claim",
        candidate_family_mode="path_to_direct",
    )
    cache: dict[int, tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, set[str]], dict[str, set[str]]]] = {}

    def state_for(end_year: int) -> tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, set[str]], dict[str, set[str]]]:
        key = int(end_year)
        if key not in cache:
            cache[key] = _build_direct_state(directed[directed["year"] <= key])
        return cache[key]

    rows: list[dict[str, Any]] = []
    max_year = int(directed["year"].max())
    for t in cutoff_years:
        train_direct, train_paths, incoming, outgoing = state_for(int(t) - 1)
        eligible = train_direct.difference(train_paths)
        if not eligible:
            continue
        current_degrees_out = {u: len(vs) for u, vs in outgoing.items()}
        current_degrees_in = {v: len(us) for v, us in incoming.items()}
        for u, v in eligible:
            row = {
                "cutoff_year_t": int(t),
                "u": str(u),
                "v": str(v),
                "pair_id": f"{u}->{v}",
                "direct_age_years": max(0.0, float(t) - float(first_year.get((u, v), t))),
                "source_out_degree": float(current_degrees_out.get(str(u), 0.0)),
                "target_in_degree": float(current_degrees_in.get(str(v), 0.0)),
                "support_potential": float(current_degrees_out.get(str(u), 0.0) * current_degrees_in.get(str(v), 0.0)),
            }
            for h in horizons:
                if int(t + h) > max_year:
                    row[f"path_thickens_h{int(h)}"] = 0
                    continue
                future_direct, future_paths, _, _ = state_for(int(t + h))
                row[f"path_thickens_h{int(h)}"] = int((str(u), str(v)) in future_paths and (str(u), str(v)) in future_direct)
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["ripeness_score_simple"] = 0.6 * np.tanh(_safe_numeric(out["support_potential"]) / 25.0) + 0.4 * np.tanh(_safe_numeric(out["direct_age_years"]) / 10.0)
    return out


def summarize_ripeness_quantiles(
    panel_df: pd.DataFrame,
    score_col: str,
    outcome_cols: list[str],
    n_quantiles: int = 5,
) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    score = _safe_numeric(panel_df[score_col])
    if score.nunique() < 2:
        return pd.DataFrame()
    ranked = score.rank(method="first")
    buckets = pd.qcut(ranked, q=min(int(n_quantiles), int(ranked.nunique())), labels=False, duplicates="drop")
    work = panel_df.copy()
    work["quantile"] = pd.to_numeric(buckets, errors="coerce")
    rows: list[dict[str, Any]] = []
    for outcome_col in outcome_cols:
        if outcome_col not in work.columns:
            continue
        block = (
            work.dropna(subset=["quantile"])
            .groupby("quantile", as_index=False)
            .agg(
                mean_score=(score_col, "mean"),
                realization_rate=(outcome_col, "mean"),
                n_rows=(outcome_col, "size"),
            )
        )
        block["outcome"] = outcome_col
        rows.append(block)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _standardize(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    feature_names: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], dict[str, float]]:
    train_x = train_df[feature_names].copy()
    eval_x = eval_df[feature_names].copy()
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    for col in feature_names:
        mu = float(_safe_numeric(train_x[col]).mean())
        sigma = float(_safe_numeric(train_x[col]).std(ddof=0))
        if not np.isfinite(sigma) or sigma <= 1e-12:
            sigma = 1.0
        means[col] = mu
        scales[col] = sigma
        train_x[col] = (_safe_numeric(train_x[col]) - mu) / sigma
        eval_x[col] = (_safe_numeric(eval_x[col]) - mu) / sigma
    return train_x, eval_x, means, scales


def fit_glm_logit_reranker(
    train_df: pd.DataFrame,
    feature_names: list[str],
    alpha: float = 0.05,
) -> LinearRerankerModel | None:
    if train_df.empty or train_df["appears_within_h"].nunique() < 2:
        return None
    train_x, _, means, scales = _standardize(train_df, train_df, feature_names)
    y = _safe_numeric(train_df["appears_within_h"]).astype(float)
    pos = float(y.sum())
    neg = float(len(y) - pos)
    if pos <= 0 or neg <= 0:
        return None
    weights = np.where(y > 0, len(y) / (2.0 * pos), len(y) / (2.0 * neg))
    design = sm.add_constant(train_x, has_constant="add")
    try:
        fit = sm.GLM(y, design, family=sm.families.Binomial(), freq_weights=weights).fit_regularized(
            alpha=float(alpha),
            L1_wt=0.0,
            maxiter=200,
        )
    except Exception:
        try:
            fit = sm.GLM(y, design, family=sm.families.Binomial(), freq_weights=weights).fit()
        except Exception:
            return None
    params = pd.Series(fit.params, index=design.columns)
    intercept = float(params.get("const", 0.0))
    coefs = {col: float(params.get(col, 0.0)) for col in feature_names}
    return LinearRerankerModel(kind="glm_logit", feature_names=feature_names, means=means, scales=scales, params=coefs, intercept=intercept)


def _build_pairwise_training_matrix(
    train_df: pd.DataFrame,
    feature_names: list[str],
    negatives_per_positive: int = 2,
    max_pairs_per_cutoff: int = 2000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.Series, dict[str, float], dict[str, float]] | tuple[None, None, None, None]:
    if train_df.empty or train_df["appears_within_h"].nunique() < 2:
        return None, None, None, None
    train_x, _, means, scales = _standardize(train_df, train_df, feature_names)
    work = train_df.reset_index(drop=True).copy()
    work_features = train_x.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    x_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    for cutoff_t, idx in work.groupby("cutoff_year_t").groups.items():
        idx_arr = np.asarray(list(idx), dtype=int)
        pos_idx = idx_arr[work.loc[idx_arr, "appears_within_h"].astype(int).to_numpy() == 1]
        neg_idx = idx_arr[work.loc[idx_arr, "appears_within_h"].astype(int).to_numpy() == 0]
        if len(pos_idx) == 0 or len(neg_idx) == 0:
            continue
        pair_budget = min(int(max_pairs_per_cutoff), int(len(pos_idx) * negatives_per_positive))
        if pair_budget <= 0:
            continue
        sampled_pos = rng.choice(pos_idx, size=pair_budget, replace=True)
        sampled_neg = rng.choice(neg_idx, size=pair_budget, replace=True)
        pos_mat = work_features.iloc[sampled_pos][feature_names].to_numpy(dtype=float)
        neg_mat = work_features.iloc[sampled_neg][feature_names].to_numpy(dtype=float)
        diff = pos_mat - neg_mat
        x_rows.append(diff)
        y_rows.extend([1] * len(diff))
        x_rows.append(-diff)
        y_rows.extend([0] * len(diff))
    if not x_rows:
        return None, None, None, None
    x_mat = np.vstack(x_rows)
    y = pd.Series(y_rows, dtype=float)
    x_df = pd.DataFrame(x_mat, columns=feature_names)
    return x_df, y, means, scales


def fit_pairwise_logit_reranker(
    train_df: pd.DataFrame,
    feature_names: list[str],
    alpha: float = 0.05,
    negatives_per_positive: int = 2,
    max_pairs_per_cutoff: int = 2000,
    seed: int = 42,
) -> LinearRerankerModel | None:
    x_df, y, means, scales = _build_pairwise_training_matrix(
        train_df=train_df,
        feature_names=feature_names,
        negatives_per_positive=negatives_per_positive,
        max_pairs_per_cutoff=max_pairs_per_cutoff,
        seed=seed,
    )
    if x_df is None or y is None or y.nunique() < 2:
        return None
    try:
        fit = sm.GLM(y, x_df, family=sm.families.Binomial()).fit_regularized(alpha=float(alpha), L1_wt=0.0, maxiter=200)
    except Exception:
        try:
            fit = sm.GLM(y, x_df, family=sm.families.Binomial()).fit()
        except Exception:
            return None
    params = pd.Series(fit.params, index=x_df.columns)
    coefs = {col: float(params.get(col, 0.0)) for col in feature_names}
    return LinearRerankerModel(kind="pairwise_logit", feature_names=feature_names, means=means or {}, scales=scales or {}, params=coefs, intercept=0.0)


def score_with_reranker(
    eval_df: pd.DataFrame,
    model: LinearRerankerModel,
) -> pd.DataFrame:
    if eval_df.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    x = eval_df[model.feature_names].copy()
    for col in model.feature_names:
        mu = float(model.means.get(col, 0.0))
        sigma = float(model.scales.get(col, 1.0))
        if not np.isfinite(sigma) or sigma <= 1e-12:
            sigma = 1.0
        x[col] = (_safe_numeric(x[col]) - mu) / sigma
    linear = np.zeros(len(x), dtype=float) + float(model.intercept)
    for col in model.feature_names:
        linear += float(model.params.get(col, 0.0)) * x[col].to_numpy(dtype=float)
    if model.kind == "glm_logit":
        score = _sigmoid(linear)
    else:
        score = linear
    out = eval_df[["u", "v"]].copy()
    out["score"] = score
    out = out.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
    out["rank"] = out.index + 1
    return out


def _feature_list(name: str) -> list[str]:
    if name not in FEATURE_FAMILIES:
        raise ValueError(f"Unknown feature family: {name}")
    return FEATURE_FAMILIES[name]


def walk_forward_reranker_eval(
    panel_df: pd.DataFrame,
    corpus_df: pd.DataFrame,
    feature_family_names: list[str],
    model_kinds: list[str],
    pool_sizes: list[int],
    alpha: float = 0.05,
    pairwise_negatives_per_positive: int = 2,
    pairwise_max_pairs_per_cutoff: int = 2000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    results: list[dict[str, Any]] = []
    baseline_cache: dict[tuple[int, int, int], dict[str, float]] = {}

    def baseline_metrics(cutoff_t: int, horizon: int, pool_size: int, eval_rows: pd.DataFrame) -> dict[str, float]:
        key = (int(cutoff_t), int(horizon), int(pool_size))
        if key in baseline_cache:
            return baseline_cache[key]
        positives = {(str(r.u), str(r.v)) for r in eval_rows[eval_rows["appears_within_h"] == 1][["u", "v"]].itertuples(index=False)}
        transparent = (
            eval_rows[["u", "v", "transparent_score"]]
            .rename(columns={"transparent_score": "score"})
            .sort_values(["score", "u", "v"], ascending=[False, True, True])
            .reset_index(drop=True)
        )
        transparent["rank"] = transparent.index + 1
        train = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
        universe = eval_rows[[c for c in ["u", "v", "candidate_kind"] if c in eval_rows.columns]].copy()
        pref = pref_attach_ranking_from_universe(train, candidate_pairs_df=universe)
        transparent_m = evaluate_binary_ranking(transparent, positives=positives, k_values=[50, 100, 500, 1000])
        pref_m = evaluate_binary_ranking(pref, positives=positives, k_values=[50, 100, 500, 1000])
        out = {}
        for name, metrics in [("transparent", transparent_m), ("pref_attach", pref_m)]:
            for metric_name, metric_val in metrics.items():
                out[f"{name}_{metric_name}"] = float(metric_val)
        baseline_cache[key] = out
        return out

    cutoffs = sorted(int(x) for x in panel_df["cutoff_year_t"].dropna().unique())
    horizons = sorted(int(x) for x in panel_df["horizon"].dropna().unique())

    for pool_size in sorted(set(int(k) for k in pool_sizes)):
        pool_flag = f"in_pool_{pool_size}"
        if pool_flag not in panel_df.columns:
            continue
        pool_df = panel_df[panel_df[pool_flag].astype(int) == 1].copy()
        if pool_df.empty:
            continue
        for horizon in horizons:
            horizon_df = pool_df[pool_df["horizon"] == int(horizon)].copy()
            if horizon_df.empty:
                continue
            for cutoff_t in cutoffs:
                eval_rows = horizon_df[horizon_df["cutoff_year_t"] == int(cutoff_t)].copy()
                if eval_rows.empty:
                    continue
                train_rows = horizon_df[horizon_df["cutoff_year_t"] < int(cutoff_t)].copy()
                base = baseline_metrics(int(cutoff_t), int(horizon), int(pool_size), eval_rows)
                if train_rows["appears_within_h"].sum() <= 0 or train_rows["appears_within_h"].nunique() < 2:
                    continue
                for feature_family_name in feature_family_names:
                    feature_names = [c for c in _feature_list(feature_family_name) if c in train_rows.columns]
                    if not feature_names:
                        continue
                    for model_kind in model_kinds:
                        if model_kind == "glm_logit":
                            model = fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=alpha)
                        elif model_kind == "pairwise_logit":
                            model = fit_pairwise_logit_reranker(
                                train_rows,
                                feature_names=feature_names,
                                alpha=alpha,
                                negatives_per_positive=pairwise_negatives_per_positive,
                                max_pairs_per_cutoff=pairwise_max_pairs_per_cutoff,
                                seed=seed + int(cutoff_t) + int(horizon) + int(pool_size),
                            )
                        else:
                            raise ValueError(f"Unsupported model_kind: {model_kind}")
                        if model is None:
                            continue
                        ranked = score_with_reranker(eval_rows, model)
                        positives = {(str(r.u), str(r.v)) for r in eval_rows[eval_rows["appears_within_h"] == 1][["u", "v"]].itertuples(index=False)}
                        metrics = evaluate_binary_ranking(ranked, positives=positives, k_values=[50, 100, 500, 1000])
                        row: dict[str, Any] = {
                            "model_kind": model_kind,
                            "feature_family": feature_family_name,
                            "pool_size": int(pool_size),
                            "cutoff_year_t": int(cutoff_t),
                            "horizon": int(horizon),
                            "n_train_rows": int(len(train_rows)),
                            "n_train_pos": int(train_rows["appears_within_h"].sum()),
                            "n_eval_rows": int(len(eval_rows)),
                            "n_eval_pos": int(eval_rows["appears_within_h"].sum()),
                        }
                        for k, v in metrics.items():
                            row[k] = float(v)
                        for k, v in base.items():
                            row[k] = float(v)
                        row["delta_mrr_vs_transparent"] = float(row.get("mrr", 0.0) - row.get("transparent_mrr", 0.0))
                        row["delta_mrr_vs_pref"] = float(row.get("mrr", 0.0) - row.get("pref_attach_mrr", 0.0))
                        for k in [50, 100, 500, 1000]:
                            row[f"delta_recall_at_{k}_vs_transparent"] = float(row.get(f"recall_at_{k}", 0.0) - row.get(f"transparent_recall_at_{k}", 0.0))
                            row[f"delta_recall_at_{k}_vs_pref"] = float(row.get(f"recall_at_{k}", 0.0) - row.get(f"pref_attach_recall_at_{k}", 0.0))
                        results.append(row)

    cutoff_df = pd.DataFrame(results)
    if cutoff_df.empty:
        return cutoff_df, pd.DataFrame()
    summary_df = (
        cutoff_df.groupby(["model_kind", "feature_family", "pool_size", "horizon"], as_index=False)
        .agg(
            mean_mrr=("mrr", "mean"),
            mean_recall_at_50=("recall_at_50", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_recall_at_500=("recall_at_500", "mean"),
            mean_recall_at_1000=("recall_at_1000", "mean"),
            mean_delta_mrr_vs_transparent=("delta_mrr_vs_transparent", "mean"),
            mean_delta_mrr_vs_pref=("delta_mrr_vs_pref", "mean"),
            mean_delta_recall_at_100_vs_transparent=("delta_recall_at_100_vs_transparent", "mean"),
            mean_delta_recall_at_100_vs_pref=("delta_recall_at_100_vs_pref", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
            total_eval_pos=("n_eval_pos", "sum"),
        )
        .sort_values(["pool_size", "horizon", "mean_mrr"], ascending=[True, True, False])
        .reset_index(drop=True)
    )
    return cutoff_df, summary_df


def _pick_best_configs(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    scored = summary_df.copy()
    scored["selection_objective"] = (
        1.0 * scored["mean_mrr"].astype(float)
        + 1.0 * scored["mean_recall_at_100"].astype(float)
        + 0.5 * scored["mean_delta_recall_at_100_vs_pref"].astype(float)
        + 0.5 * scored["mean_delta_recall_at_100_vs_transparent"].astype(float)
    )
    best = (
        scored.sort_values(["pool_size", "horizon", "selection_objective"], ascending=[True, True, False])
        .groupby(["pool_size", "horizon"], as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    return best


def _write_markdown_summary(
    summary_df: pd.DataFrame,
    best_df: pd.DataFrame,
    out_path: Path,
) -> None:
    lines = [
        "# Learned Reranker Summary",
        "",
        "This note summarizes the first frozen-ontology learned-reranker pass.",
        "",
    ]
    if summary_df.empty:
        lines.append("No reranker results were generated.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    lines.append("## Best configuration by pool and horizon")
    for row in best_df.itertuples(index=False):
        lines.append(
            f"- pool={int(row.pool_size)}, h={int(row.horizon)}: {row.model_kind} + {row.feature_family} | "
            f"MRR={float(row.mean_mrr):.6f}, Recall@100={float(row.mean_recall_at_100):.6f}, "
            f"delta Recall@100 vs transparent={float(row.mean_delta_recall_at_100_vs_transparent):+.6f}, "
            f"delta Recall@100 vs pref_attach={float(row.mean_delta_recall_at_100_vs_pref):+.6f}"
        )
    lines.append("")
    lines.append("## Model families tested")
    for (model_kind, feature_family), block in summary_df.groupby(["model_kind", "feature_family"]):
        lines.append(
            f"- {model_kind} + {feature_family}: mean main-horizon MRR={float(block[block['horizon'].isin([5, 10])]['mean_mrr'].mean()):.6f}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Learned reranker on top of frozen-ontology retrieval candidates.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper_meta", default=None, dest="paper_meta_path")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="5,10")
    parser.add_argument("--pool_sizes", default="10000,20000")
    parser.add_argument("--feature_families", default="base,structural,dynamic,composition,boundary_gap")
    parser.add_argument("--model_kinds", default="glm_logit,pairwise_logit")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--pairwise_negatives_per_positive", type=int, default=2)
    parser.add_argument("--pairwise_max_pairs_per_cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None
    horizons = parse_horizons(args.horizons, default=[5, 10])
    pool_sizes = [int(x.strip()) for x in str(args.pool_sizes).split(",") if x.strip()]
    feature_family_names = [x.strip() for x in str(args.feature_families).split(",") if x.strip()]
    model_kinds = [x.strip() for x in str(args.model_kinds).split(",") if x.strip()]
    min_y = int(corpus_df["year"].min())
    max_y = int(corpus_df["year"].max())
    cutoff_years = parse_cutoff_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons), step=5)

    panel_df = build_candidate_feature_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=cutoff_years,
        horizons=horizons,
        pool_sizes=pool_sizes,
        paper_meta_df=paper_meta_df,
    )
    cutoff_df, summary_df = walk_forward_reranker_eval(
        panel_df=panel_df,
        corpus_df=corpus_df,
        feature_family_names=feature_family_names,
        model_kinds=model_kinds,
        pool_sizes=pool_sizes,
        alpha=float(args.alpha),
        pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
        pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
        seed=int(args.seed),
    )
    best_df = _pick_best_configs(summary_df)
    path_panel = build_path_to_direct_ripeness_panel(panel_df, horizons=[h for h in horizons if h in {3, 5, 10}] or horizons)
    path_quantiles = summarize_ripeness_quantiles(
        path_panel,
        score_col="ripeness_score_simple",
        outcome_cols=[c for c in path_panel.columns if c.startswith("direct_closure_h")],
    )
    direct_path_panel = build_direct_to_path_panel(corpus_df=corpus_df, cutoff_years=cutoff_years, horizons=[h for h in horizons if h in {3, 5, 10}] or horizons)
    direct_path_quantiles = summarize_ripeness_quantiles(
        direct_path_panel,
        score_col="ripeness_score_simple",
        outcome_cols=[c for c in direct_path_panel.columns if c.startswith("path_thickens_h")],
    )

    panel_df.to_parquet(Path(out_dir) / "candidate_feature_panel.parquet", index=False)
    panel_df.to_csv(Path(out_dir) / "candidate_feature_panel.csv", index=False)
    cutoff_df.to_csv(Path(out_dir) / "reranker_cutoff_eval.csv", index=False)
    summary_df.to_csv(Path(out_dir) / "reranker_summary.csv", index=False)
    best_df.to_csv(Path(out_dir) / "reranker_best_configs.csv", index=False)
    path_panel.to_csv(Path(out_dir) / "path_to_direct_ripeness_panel.csv", index=False)
    path_quantiles.to_csv(Path(out_dir) / "path_to_direct_ripeness_quantiles.csv", index=False)
    direct_path_panel.to_csv(Path(out_dir) / "direct_to_path_panel.csv", index=False)
    direct_path_quantiles.to_csv(Path(out_dir) / "direct_to_path_ripeness_quantiles.csv", index=False)
    _write_markdown_summary(summary_df, best_df, Path(out_dir) / "learned_reranker_summary.md")
    manifest = {
        "cutoff_years": [int(x) for x in cutoff_years],
        "horizons": [int(x) for x in horizons],
        "pool_sizes": [int(x) for x in pool_sizes],
        "feature_families": feature_family_names,
        "model_kinds": model_kinds,
        "n_panel_rows": int(len(panel_df)),
        "n_eval_rows": int(len(cutoff_df)),
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote: {Path(out_dir) / 'reranker_summary.csv'}")


if __name__ == "__main__":
    main()
