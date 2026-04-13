from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src.features_motifs import compute_motif_features
from src.features_pairs import compute_underexplored_pairs
from src.features_paths import compute_path_features
from src.research_allocation_v2 import (
    build_candidate_table_v2,
    candidate_layer_mask,
    check_no_leakage_v2,
    first_candidate_event_year_map_v2,
    first_appearance_map_v2,
    first_path_appearance_map_for_pairs_v2,
    future_edges_for_v2,
    normalize_candidate_family_mode,
)
from src.scoring import compute_candidate_scores


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)


def ensure_output_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize_text(value: str) -> str:
    v = str(value or "").lower()
    v = re.sub(r"[^a-z0-9\s]", " ", v)
    v = re.sub(r"\s+", " ", v).strip()
    return v


def tokenize(value: str) -> set[str]:
    txt = normalize_text(value)
    if not txt:
        return set()
    return {t for t in txt.split(" ") if t}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    uni = len(a.union(b))
    return inter / float(uni) if uni else 0.0


def percentile_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    if len(values) == 0:
        return (float("nan"), float("nan"))
    lo = float(np.quantile(values, alpha / 2))
    hi = float(np.quantile(values, 1 - alpha / 2))
    return lo, hi


def bootstrap_mean_ci(
    values: Iterable[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=float)
    n = arr.size
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    mean = float(np.mean(arr))
    lo, hi = percentile_ci(means, alpha=alpha)
    return mean, lo, hi


def paired_bootstrap_delta(
    a: Iterable[float],
    b: Iterable[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    arr_a = np.asarray(list(a), dtype=float)
    arr_b = np.asarray(list(b), dtype=float)
    mask = np.isfinite(arr_a) & np.isfinite(arr_b)
    arr_a = arr_a[mask]
    arr_b = arr_b[mask]
    if arr_a.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    diff = arr_a - arr_b
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot, dtype=float)
    n = diff.size
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        deltas[i] = float(np.mean(diff[idx]))
    delta = float(np.mean(diff))
    lo, hi = percentile_ci(deltas, alpha=alpha)
    # Two-sided bootstrap p-value against 0.
    p = float(2 * min(np.mean(deltas <= 0), np.mean(deltas >= 0)))
    p = min(1.0, p)
    return delta, lo, hi, p


def first_appearance_map(
    corpus_df: pd.DataFrame,
    candidate_kind: str = "directed_causal",
    candidate_family_mode: str = "path_to_direct",
) -> dict[tuple[str, str], int]:
    if "edge_kind" in corpus_df.columns:
        return first_candidate_event_year_map_v2(
            corpus_df,
            candidate_kind=candidate_kind,
            candidate_family_mode=candidate_family_mode,
        )
    g = corpus_df.groupby(["src_code", "dst_code"], as_index=False).agg(first_year=("year", "min"))
    return {(str(r.src_code), str(r.dst_code)): int(r.first_year) for r in g.itertuples(index=False)}


def future_edges_for(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return future_edges_for_v2(first_year_map, cutoff_t=cutoff_t, horizon_h=horizon_h)


def first_path_appearance_map_for_pairs(
    corpus_df: pd.DataFrame,
    target_pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], int]:
    return first_path_appearance_map_for_pairs_v2(corpus_df, target_pairs)


def restrict_positive_set_for_family(
    positives: set[tuple[str, str]],
    candidate_pairs_df: pd.DataFrame | None,
    candidate_family_mode: str = "path_to_direct",
) -> set[tuple[str, str]]:
    family_mode = normalize_candidate_family_mode(candidate_family_mode)
    if family_mode != "direct_to_path":
        return set(positives)
    if candidate_pairs_df is None or candidate_pairs_df.empty:
        return set()
    universe = {
        (str(r.u), str(r.v))
        for r in candidate_pairs_df[["u", "v"]].drop_duplicates().itertuples(index=False)
    }
    return set(positives).intersection(universe)


def check_no_leakage(
    corpus_df: pd.DataFrame,
    cutoff_t: int,
    horizon_h: int,
    candidate_kind: str = "directed_causal",
    candidate_family_mode: str = "path_to_direct",
    first_year_map: dict[tuple[str, str], int] | None = None,
) -> bool:
    if "edge_kind" in corpus_df.columns:
        fmap = (
            first_year_map
            if first_year_map is not None
            else first_candidate_event_year_map_v2(
                corpus_df,
                candidate_kind=candidate_kind,
                candidate_family_mode=candidate_family_mode,
            )
        )
        return check_no_leakage_v2(
            corpus_df,
            cutoff_t=cutoff_t,
            horizon_h=horizon_h,
            candidate_kind=candidate_kind,
            candidate_family_mode=candidate_family_mode,
            first_year_map=fmap,
        )
    fmap = (
        first_year_map
        if first_year_map is not None
        else first_appearance_map(
            corpus_df,
            candidate_kind=candidate_kind,
            candidate_family_mode=candidate_family_mode,
        )
    )
    train_edges = set(
        zip(
            corpus_df.loc[corpus_df["year"] <= (cutoff_t - 1), "src_code"].astype(str),
            corpus_df.loc[corpus_df["year"] <= (cutoff_t - 1), "dst_code"].astype(str),
        )
    )
    positives = future_edges_for(fmap, cutoff_t=cutoff_t, horizon_h=horizon_h)
    return len(train_edges.intersection(positives)) == 0


def _apply_weight_transform(
    train_df: pd.DataFrame,
    cutoff_t: int,
    recency_decay_lambda: float = 0.0,
    stability_coef: float = 0.0,
    causal_bonus: float = 0.0,
) -> pd.DataFrame:
    df = train_df.copy()
    base_w = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0).astype(float)
    age = np.maximum(0.0, float(cutoff_t - 1) - pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(float))
    recency_factor = np.exp(-float(recency_decay_lambda) * age) if recency_decay_lambda > 0 else 1.0
    stability = pd.to_numeric(df["stability"], errors="coerce").fillna(0.0).clip(0.0, 1.0).astype(float)
    stability_factor = 1.0 + float(stability_coef) * stability
    causal_factor = 1.0 + float(causal_bonus) * df["is_causal"].astype(bool).astype(float)
    df["weight"] = base_w * recency_factor * stability_factor * causal_factor
    return df


def _cooc_trajectory_proxy(
    pairs_df: pd.DataFrame,
) -> pd.DataFrame:
    if pairs_df.empty:
        return pd.DataFrame(columns=["u", "v", "cooc_trend_raw"])
    span = (pairs_df["last_year_seen"].fillna(0) - pairs_df["first_year_seen"].fillna(0) + 1).clip(lower=1).astype(float)
    out = pairs_df[["u", "v"]].copy()
    out["cooc_trend_raw"] = pairs_df["cooc_count"].astype(float) / span
    return out


def _safe_numeric(series: pd.Series | float | int, default: float = 0.0) -> pd.Series:
    if isinstance(series, pd.Series):
        return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(float(default)).astype(float)
    return pd.Series([float(series)], dtype=float)


def _min_max_scale(series: pd.Series) -> pd.Series:
    vals = _safe_numeric(series)
    if vals.empty:
        return vals
    lo = float(vals.min())
    hi = float(vals.max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo + 1e-12:
        return pd.Series(np.zeros(len(vals), dtype=float), index=vals.index)
    return ((vals - lo) / (hi - lo)).clip(0.0, 1.0).astype(float)


def _transparent_degree_maps_v2(train_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    if train_df.empty:
        return {
            "source_support_out_degree": {},
            "target_support_in_degree": {},
            "source_direct_out_degree": {},
            "target_direct_in_degree": {},
            "support_total_degree": {},
            "node_first_seen_year": {},
        }

    if "edge_kind" not in train_df.columns:
        support_df = train_df[["src_code", "dst_code"]].copy()
        direct_df = train_df[train_df["is_causal"].astype(bool)][["src_code", "dst_code"]].copy()
    else:
        ordered = train_df[candidate_layer_mask(train_df, "ordered_claim")][["src_code", "dst_code"]].copy()
        contextual = train_df[candidate_layer_mask(train_df, "contextual_pair")][["src_code", "dst_code"]].copy()
        rev = contextual.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
        support_df = pd.concat([ordered, contextual, rev], ignore_index=True)
        direct_df = train_df[candidate_layer_mask(train_df, "causal_claim")][["src_code", "dst_code"]].copy()

    maps: dict[str, dict[str, float]] = {
        "source_support_out_degree": {},
        "target_support_in_degree": {},
        "source_direct_out_degree": {},
        "target_direct_in_degree": {},
        "support_total_degree": {},
        "node_first_seen_year": {},
    }
    if not support_df.empty:
        out_deg = support_df.groupby("src_code")["dst_code"].nunique()
        in_deg = support_df.groupby("dst_code")["src_code"].nunique()
        maps["source_support_out_degree"] = {str(idx): float(val) for idx, val in out_deg.items()}
        maps["target_support_in_degree"] = {str(idx): float(val) for idx, val in in_deg.items()}
        total_deg = out_deg.add(in_deg, fill_value=0.0)
        maps["support_total_degree"] = {str(idx): float(val) for idx, val in total_deg.items()}
        if "year" in train_df.columns:
            src_year = train_df[["src_code", "year"]].rename(columns={"src_code": "code"})
            dst_year = train_df[["dst_code", "year"]].rename(columns={"dst_code": "code"})
            node_year = pd.concat([src_year, dst_year], ignore_index=True)
            if not node_year.empty:
                first_seen = (
                    node_year.assign(code=node_year["code"].astype(str), year=pd.to_numeric(node_year["year"], errors="coerce"))
                    .dropna(subset=["year"])
                    .groupby("code")["year"]
                    .min()
                )
                maps["node_first_seen_year"] = {str(idx): float(val) for idx, val in first_seen.items()}
    if not direct_df.empty:
        maps["source_direct_out_degree"] = {
            str(idx): float(val)
            for idx, val in direct_df.groupby("src_code")["dst_code"].nunique().items()
        }
        maps["target_direct_in_degree"] = {
            str(idx): float(val)
            for idx, val in direct_df.groupby("dst_code")["src_code"].nunique().items()
        }
    return maps


def _transparent_topology_component(local_topology: pd.Series, family_mode: str) -> pd.Series:
    family = normalize_candidate_family_mode(family_mode)
    if family == "direct_to_path":
        mapping = {
            "branched": 1.0,
            "branched_multi_step": 0.9,
            "serial_multi_step": 0.8,
            "serial_path": 0.7,
            "sparse_local": 0.1,
        }
    else:
        mapping = {
            "serial_path": 1.0,
            "serial_multi_step": 0.9,
            "branched_multi_step": 0.75,
            "branched": 0.6,
            "sparse_local": 0.2,
        }
    return local_topology.astype(str).map(mapping).fillna(0.0).astype(float)


def _transparent_provenance_component(status: pd.Series, family_mode: str) -> pd.Series:
    family = normalize_candidate_family_mode(family_mode)
    if family == "direct_to_path":
        mapping = {
            "strict_direct_present__path_missing": 0.8,
            "main_direct_present__path_missing": 0.5,
            "ordered_direct_present__path_missing": 0.2,
        }
    else:
        mapping = {
            "main_present__strict_missing": 0.9,
            "ordered_present__main_missing": 0.8,
            "contextual_present__ordered_missing__main_missing": 0.5,
            "fully_open": 0.0,
        }
    return status.astype(str).map(mapping).fillna(0.0).astype(float)


KNOWN_CANDIDATE_SUBFAMILIES = [
    "fully_open_frontier",
    "contextual_to_ordered",
    "ordered_to_causal",
    "causal_to_identified",
    "ordered_direct_to_path",
    "causal_direct_to_path",
    "identified_direct_to_path",
]

KNOWN_CANDIDATE_SCOPE_BUCKETS = [
    "fully_open",
    "contextual_progression",
    "anchored_progression",
    "direct_present_path_missing",
]

TRANSPARENT_COMPONENT_COLUMNS = [
    "transparent_support_strength_component",
    "transparent_opportunity_component",
    "transparent_specificity_component",
    "transparent_resolution_component",
    "transparent_mediator_specificity_component",
    "transparent_provenance_component",
    "transparent_topology_component",
]


def _transparent_component_defaults(family_mode: str) -> dict[str, float]:
    family = normalize_candidate_family_mode(family_mode)
    if family == "direct_to_path":
        return {
            "transparent_weight_support_strength": 0.18,
            "transparent_weight_opportunity": 0.34,
            "transparent_weight_specificity": 0.10,
            "transparent_weight_resolution": 0.12,
            "transparent_weight_mediator_specificity": 0.10,
            "transparent_weight_provenance": 0.08,
            "transparent_weight_topology": 0.08,
        }
    return {
        "transparent_weight_support_strength": 0.28,
        "transparent_weight_opportunity": 0.14,
        "transparent_weight_specificity": 0.12,
        "transparent_weight_resolution": 0.16,
        "transparent_weight_mediator_specificity": 0.12,
        "transparent_weight_provenance": 0.10,
        "transparent_weight_topology": 0.08,
    }


def add_candidate_family_indicator_columns(candidate_df: pd.DataFrame) -> pd.DataFrame:
    if candidate_df.empty:
        return candidate_df.copy()
    out = candidate_df.copy()
    subfamily = out.get("candidate_subfamily", pd.Series("", index=out.index)).astype(str)
    scope_bucket = out.get("candidate_scope_bucket", pd.Series("", index=out.index)).astype(str)
    depth_map = {
        "fully_open_frontier": 0.0,
        "contextual_to_ordered": 1.0,
        "ordered_to_causal": 2.0,
        "causal_to_identified": 3.0,
        "ordered_direct_to_path": 1.0,
        "causal_direct_to_path": 2.0,
        "identified_direct_to_path": 3.0,
    }
    out["progression_depth"] = subfamily.map(depth_map).fillna(0.0).astype(float)
    for value in KNOWN_CANDIDATE_SUBFAMILIES:
        out[f"subfamily_{value}"] = subfamily.eq(value).astype(float)
    for value in KNOWN_CANDIDATE_SCOPE_BUCKETS:
        out[f"scope_{value}"] = scope_bucket.eq(value).astype(float)
    out["transparent_score_x_progression_depth"] = (
        _safe_numeric(out.get("score", pd.Series(0.0, index=out.index)))
        * _safe_numeric(out["progression_depth"])
    ).astype(float)
    out["provenance_x_progression_depth"] = (
        _safe_numeric(out.get("transparent_provenance_component", pd.Series(0.0, index=out.index)))
        * _safe_numeric(out["progression_depth"])
    ).astype(float)
    return out


def transparent_score_param_dict(
    cfg: CandidateBuildConfig | None = None,
    family_mode: str = "path_to_direct",
) -> dict[str, float]:
    defaults = _transparent_component_defaults(family_mode)
    payload: dict[str, float] = dict(defaults)
    for name in [
        "transparent_bonus_fully_open_frontier",
        "transparent_bonus_contextual_to_ordered",
        "transparent_bonus_ordered_to_causal",
        "transparent_bonus_causal_to_identified",
        "transparent_bonus_ordered_direct_to_path",
        "transparent_bonus_causal_direct_to_path",
        "transparent_bonus_identified_direct_to_path",
    ]:
        payload[name] = 0.0
    if cfg is None:
        return payload
    for key in list(defaults.keys()) + [
        "transparent_bonus_fully_open_frontier",
        "transparent_bonus_contextual_to_ordered",
        "transparent_bonus_ordered_to_causal",
        "transparent_bonus_causal_to_identified",
        "transparent_bonus_ordered_direct_to_path",
        "transparent_bonus_causal_direct_to_path",
        "transparent_bonus_identified_direct_to_path",
    ]:
        value = getattr(cfg, key, None)
        if value is None:
            continue
        payload[key] = float(value)
    return payload


def score_with_transparent_component_params(
    candidate_df: pd.DataFrame,
    params: dict[str, float],
) -> pd.DataFrame:
    if candidate_df.empty:
        return candidate_df.copy()
    out = add_candidate_family_indicator_columns(candidate_df)
    for col in TRANSPARENT_COMPONENT_COLUMNS:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = _safe_numeric(out[col])
    for col in [
        "subfamily_fully_open_frontier",
        "subfamily_contextual_to_ordered",
        "subfamily_ordered_to_causal",
        "subfamily_causal_to_identified",
        "subfamily_ordered_direct_to_path",
        "subfamily_causal_direct_to_path",
        "subfamily_identified_direct_to_path",
    ]:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = _safe_numeric(out[col])
    out["score"] = (
        float(params.get("transparent_weight_support_strength", 0.0)) * out["transparent_support_strength_component"]
        + float(params.get("transparent_weight_opportunity", 0.0)) * out["transparent_opportunity_component"]
        + float(params.get("transparent_weight_specificity", 0.0)) * out["transparent_specificity_component"]
        + float(params.get("transparent_weight_resolution", 0.0)) * out["transparent_resolution_component"]
        + float(params.get("transparent_weight_mediator_specificity", 0.0)) * out["transparent_mediator_specificity_component"]
        + float(params.get("transparent_weight_provenance", 0.0)) * out["transparent_provenance_component"]
        + float(params.get("transparent_weight_topology", 0.0)) * out["transparent_topology_component"]
        + float(params.get("transparent_bonus_fully_open_frontier", 0.0)) * out["subfamily_fully_open_frontier"]
        + float(params.get("transparent_bonus_contextual_to_ordered", 0.0)) * out["subfamily_contextual_to_ordered"]
        + float(params.get("transparent_bonus_ordered_to_causal", 0.0)) * out["subfamily_ordered_to_causal"]
        + float(params.get("transparent_bonus_causal_to_identified", 0.0)) * out["subfamily_causal_to_identified"]
        + float(params.get("transparent_bonus_ordered_direct_to_path", 0.0)) * out["subfamily_ordered_direct_to_path"]
        + float(params.get("transparent_bonus_causal_direct_to_path", 0.0)) * out["subfamily_causal_direct_to_path"]
        + float(params.get("transparent_bonus_identified_direct_to_path", 0.0)) * out["subfamily_identified_direct_to_path"]
    ).astype(float)
    out = out.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
    out["rank"] = out.index + 1
    return out


def _apply_transparent_model_v2(
    candidate_df: pd.DataFrame,
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: CandidateBuildConfig,
) -> pd.DataFrame:
    if candidate_df.empty:
        return candidate_df.copy()
    out = candidate_df.copy()
    maps = _transparent_degree_maps_v2(train_df)

    out["source_support_out_degree"] = out["u"].astype(str).map(maps["source_support_out_degree"]).fillna(0.0).astype(float)
    out["target_support_in_degree"] = out["v"].astype(str).map(maps["target_support_in_degree"]).fillna(0.0).astype(float)
    out["source_direct_out_degree"] = out["u"].astype(str).map(maps["source_direct_out_degree"]).fillna(0.0).astype(float)
    out["target_direct_in_degree"] = out["v"].astype(str).map(maps["target_direct_in_degree"]).fillna(0.0).astype(float)
    out["source_support_total_degree"] = out["u"].astype(str).map(maps["support_total_degree"]).fillna(0.0).astype(float)
    out["target_support_total_degree"] = out["v"].astype(str).map(maps["support_total_degree"]).fillna(0.0).astype(float)

    out["support_degree_product_raw"] = np.log1p(out["source_support_out_degree"] * out["target_support_in_degree"])
    out["direct_degree_product_raw"] = np.log1p(out["source_direct_out_degree"] * out["target_direct_in_degree"])
    out["support_degree_product_norm"] = _min_max_scale(out["support_degree_product_raw"])
    out["direct_degree_product_norm"] = _min_max_scale(out["direct_degree_product_raw"])
    mediator_key = out.get("focal_mediator_id", out.get("focal_mediator_label", pd.Series("", index=out.index))).astype(str)
    out["focal_mediator_support_total_degree"] = mediator_key.map(maps["support_total_degree"]).fillna(0.0).astype(float)
    src_year = out["u"].astype(str).map(maps["node_first_seen_year"])
    dst_year = out["v"].astype(str).map(maps["node_first_seen_year"])
    med_year = mediator_key.map(maps["node_first_seen_year"])
    out["source_node_age_years"] = np.maximum(0.0, float(cutoff_t) - _safe_numeric(src_year, default=float(cutoff_t)))
    out["target_node_age_years"] = np.maximum(0.0, float(cutoff_t) - _safe_numeric(dst_year, default=float(cutoff_t)))
    out["focal_mediator_age_years"] = np.maximum(0.0, float(cutoff_t) - _safe_numeric(med_year, default=float(cutoff_t)))

    endpoint_broadness_raw = (
        0.5 * np.log1p(out["source_support_total_degree"])
        + 0.5 * np.log1p(out["target_support_total_degree"])
    ).astype(float)
    mediator_broadness_raw = np.log1p(out["focal_mediator_support_total_degree"]).astype(float)
    mediator_present = mediator_key.ne("") & out["focal_mediator_support_total_degree"].gt(0.0)
    mediator_specificity = 1.0 - _min_max_scale(mediator_broadness_raw)
    mediator_specificity = mediator_specificity.where(mediator_present, 0.5)

    out["endpoint_broadness_raw"] = endpoint_broadness_raw
    out["endpoint_resolution_score"] = (1.0 - _min_max_scale(endpoint_broadness_raw)).clip(0.0, 1.0).astype(float)
    out["focal_mediator_broadness_raw"] = mediator_broadness_raw
    out["focal_mediator_specificity_score"] = mediator_specificity.clip(0.0, 1.0).astype(float)
    out["transparent_specificity_component"] = (
        1.0 - _safe_numeric(out.get("hub_penalty", pd.Series(0.0, index=out.index)))
    ).clip(0.0, 1.0)
    out["transparent_resolution_component"] = out["endpoint_resolution_score"].astype(float)
    out["transparent_mediator_specificity_component"] = out["focal_mediator_specificity_score"].astype(float)
    out["transparent_topology_component"] = _transparent_topology_component(
        out.get("local_topology_class", pd.Series("sparse_local", index=out.index)),
        cfg.candidate_family_mode,
    )
    out["transparent_provenance_component"] = _transparent_provenance_component(
        out.get("candidate_status_at_t", pd.Series("", index=out.index)),
        cfg.candidate_family_mode,
    )

    family_mode = normalize_candidate_family_mode(cfg.candidate_family_mode)
    if family_mode == "direct_to_path":
        out["transparent_support_strength_component"] = (
            0.70 * _safe_numeric(out.get("direct_support_norm", pd.Series(0.0, index=out.index)))
            + 0.30 * _safe_numeric(out.get("cooc_trend_norm", pd.Series(0.0, index=out.index)))
        ).astype(float)
        out["transparent_opportunity_component"] = (
            0.65 * out["support_degree_product_norm"]
            + 0.35 * out["direct_degree_product_norm"]
        ).astype(float)
    else:
        out["transparent_support_strength_component"] = (
            0.45 * _safe_numeric(out.get("path_support_norm", pd.Series(0.0, index=out.index)))
            + 0.25 * _safe_numeric(out.get("motif_bonus_norm", pd.Series(0.0, index=out.index)))
            + 0.15 * _safe_numeric(out.get("gap_bonus", pd.Series(0.0, index=out.index)))
            + 0.15 * _safe_numeric(out.get("cooc_trend_norm", pd.Series(0.0, index=out.index)))
        ).astype(float)
        out["transparent_opportunity_component"] = (
            0.75 * out["support_degree_product_norm"]
            + 0.25 * out["direct_degree_product_norm"]
        ).astype(float)
    params = transparent_score_param_dict(cfg=cfg, family_mode=family_mode)
    return score_with_transparent_component_params(out, params=params)


def _annotate_candidate_generation_v3_fields(
    candidate_df: pd.DataFrame,
    cfg: "CandidateBuildConfig",
) -> pd.DataFrame:
    if candidate_df.empty:
        return candidate_df.copy()
    out = candidate_df.copy()
    family_mode = normalize_candidate_family_mode(getattr(cfg, "candidate_family_mode", "path_to_direct"))
    resolution = _safe_numeric(out.get("endpoint_resolution_score", pd.Series(0.0, index=out.index)))
    mediator_spec = _safe_numeric(out.get("focal_mediator_specificity_score", pd.Series(0.5, index=out.index)), default=0.5)
    broadness_raw = _safe_numeric(out.get("endpoint_broadness_raw", pd.Series(0.0, index=out.index)))
    out["endpoint_broadness_pct"] = _min_max_scale(broadness_raw).clip(0.0, 1.0).astype(float)
    path_support_raw = _safe_numeric(out.get("path_support_raw", pd.Series(0.0, index=out.index)))
    motif_count = pd.to_numeric(out.get("motif_count", pd.Series(0, index=out.index)), errors="coerce").fillna(0).astype(int)
    mediator_count = pd.to_numeric(out.get("mediator_count", pd.Series(0, index=out.index)), errors="coerce").fillna(0).astype(int)
    status = out.get("candidate_status_at_t", pd.Series("", index=out.index)).astype(str)
    subfamily = out.get("candidate_subfamily", pd.Series("", index=out.index)).astype(str)
    scope_bucket = out.get("candidate_scope_bucket", pd.Series("", index=out.index)).astype(str)

    mediator_id = out.get("focal_mediator_id", pd.Series("", index=out.index)).fillna("").astype(str).str.strip()
    mediator_label = out.get("focal_mediator_label", pd.Series("", index=out.index)).fillna("").astype(str).str.strip()
    mediator_present = mediator_id.ne("") | mediator_label.ne("")

    anchored_flag = (
        scope_bucket.eq("anchored_progression")
        | subfamily.isin(["ordered_to_causal", "causal_to_identified"])
    )
    strong_structure = (
        (path_support_raw >= float(getattr(cfg, "anchored_min_path_support_raw", 2.0)))
        | (motif_count >= int(getattr(cfg, "anchored_min_motif_count", 2)))
        | (mediator_count >= int(getattr(cfg, "anchored_min_mediator_count", 2)))
    )
    strong_resolution = resolution >= float(getattr(cfg, "anchored_min_resolution_score", 0.18))
    strong_mediator = mediator_spec >= float(getattr(cfg, "anchored_min_mediator_specificity_score", 0.25))
    broad_anchored = anchored_flag & (
        out["endpoint_broadness_pct"].astype(float) >= float(getattr(cfg, "anchored_broad_start_pct", 0.80))
    )
    keep_gate = (~broad_anchored) | strong_structure | strong_resolution | strong_mediator

    out["candidate_generation_gate_failed"] = (~keep_gate).astype(int)
    out["candidate_generation_gate_reason"] = np.where(
        keep_gate,
        "",
        np.where(
            broad_anchored & (~strong_structure) & (~strong_mediator) & (~strong_resolution),
            "broad_anchored_low_signal",
            "other_gate",
        ),
    )

    compression_med_cut = float(getattr(cfg, "compression_mediator_specificity_min", 0.35))
    compression_res_cut = float(getattr(cfg, "compression_endpoint_resolution_min", 0.15))
    mediator_set_flag = mediator_count >= 2
    if family_mode == "direct_to_path":
        focal_question_type = pd.Series("direct_path_thickening", index=out.index)
    else:
        focal_question_type = np.where(
            mediator_present & (mediator_spec >= compression_med_cut),
            "endpoint_plus_mediator",
            np.where(mediator_set_flag, "endpoint_plus_mediator_set", "endpoint"),
        )
        focal_question_type = pd.Series(focal_question_type, index=out.index)
    out["focal_question_type"] = focal_question_type.astype(str)

    topology_bonus = np.tanh(path_support_raw / 4.0).astype(float)
    out["compression_confidence"] = (
        0.55 * resolution.astype(float)
        + 0.30 * mediator_spec.astype(float)
        + 0.15 * topology_bonus
    ).clip(0.0, 1.0).astype(float)

    compressed_triplets: list[str] = []
    for row in out.itertuples(index=False):
        if str(getattr(row, "focal_question_type", "")) == "direct_path_thickening":
            compressed_triplets.append(
                json.dumps(
                    {
                        "source": str(getattr(row, "u", "")),
                        "target": str(getattr(row, "v", "")),
                        "type": "direct_path_thickening",
                    },
                    ensure_ascii=True,
                )
            )
            continue
        med_id = str(getattr(row, "focal_mediator_id", "") or "").strip()
        med_label_val = str(getattr(row, "focal_mediator_label", "") or "").strip()
        if med_id or med_label_val:
            compressed_triplets.append(
                json.dumps(
                    {
                        "source": str(getattr(row, "u", "")),
                        "mediator": med_id,
                        "mediator_label": med_label_val,
                        "target": str(getattr(row, "v", "")),
                        "type": str(getattr(row, "focal_question_type", "")),
                    },
                    ensure_ascii=True,
                )
            )
        else:
            compressed_triplets.append(
                json.dumps(
                    {
                        "source": str(getattr(row, "u", "")),
                        "target": str(getattr(row, "v", "")),
                        "type": str(getattr(row, "focal_question_type", "")),
                    },
                    ensure_ascii=True,
                )
            )
    out["compressed_triplet_json"] = compressed_triplets
    out["compression_failure_reason"] = np.where(
        family_mode == "direct_to_path",
        "",
        np.where(
            (resolution < compression_res_cut) & mediator_present & (mediator_spec < compression_med_cut),
            "broad_endpoints_and_generic_mediator",
            np.where(
                resolution < compression_res_cut,
                "broad_endpoints",
                np.where(mediator_present & (mediator_spec < compression_med_cut), "generic_mediator", ""),
            ),
        ),
    )
    return out


@dataclass
class CandidateBuildConfig:
    tau: int = 2
    max_path_len: int = 2
    max_neighbors_per_mediator: int = 120
    alpha: float = 0.5
    beta: float = 0.2
    gamma: float = 0.3
    delta: float = 0.2
    cooc_trend_coef: float = 0.0
    recency_decay_lambda: float = 0.0
    stability_coef: float = 0.0
    causal_bonus: float = 0.0
    field_hub_penalty_scale: float = 0.0
    include_details: bool = False
    boundary_bonus: float = 0.0
    boundary_quota: float = 0.0
    boundary_quota_max_rank: int = 1000
    causal_only: bool = False
    min_stability: float | None = None
    candidate_kind: str = "directed_causal"
    candidate_family_mode: str = "path_to_direct"
    path_to_direct_scope: str = "broad"
    fully_open_min_cooc_count: int = 1
    fully_open_min_motif_count: int = 1
    fully_open_min_path_support_raw: float | None = 5.0
    anchored_broad_start_pct: float = 0.80
    anchored_min_resolution_score: float = 0.18
    anchored_min_mediator_specificity_score: float = 0.25
    anchored_min_path_support_raw: float = 2.0
    anchored_min_motif_count: int = 2
    anchored_min_mediator_count: int = 2
    compression_mediator_specificity_min: float = 0.35
    compression_endpoint_resolution_min: float = 0.15
    transparent_weight_support_strength: float | None = None
    transparent_weight_opportunity: float | None = None
    transparent_weight_specificity: float | None = None
    transparent_weight_resolution: float | None = None
    transparent_weight_mediator_specificity: float | None = None
    transparent_weight_provenance: float | None = None
    transparent_weight_topology: float | None = None
    transparent_bonus_fully_open_frontier: float = 0.0
    transparent_bonus_contextual_to_ordered: float = 0.0
    transparent_bonus_ordered_to_causal: float = 0.0
    transparent_bonus_causal_to_identified: float = 0.0
    transparent_bonus_ordered_direct_to_path: float = 0.0
    transparent_bonus_causal_direct_to_path: float = 0.0
    transparent_bonus_identified_direct_to_path: float = 0.0


def build_candidate_table(
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: CandidateBuildConfig,
) -> pd.DataFrame:
    if train_df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])
    if "edge_kind" in train_df.columns:
        scored = build_candidate_table_v2(train_df, cutoff_t=cutoff_t, cfg=cfg)
        if scored.empty:
            return scored
        scored = _apply_transparent_model_v2(scored, train_df=train_df, cutoff_t=cutoff_t, cfg=cfg)
        scored = _annotate_candidate_generation_v3_fields(scored, cfg=cfg)
        if scored.empty:
            return scored
        scored = scored[scored["candidate_generation_gate_failed"].astype(int) == 0].copy()
        if scored.empty:
            return scored
        scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
        scored["rank"] = scored.index + 1
        if normalize_candidate_family_mode(cfg.candidate_family_mode) == "path_to_direct":
            scope = str(getattr(cfg, "path_to_direct_scope", "broad") or "broad").strip().lower()
            if scope not in {"anchored", "broad"}:
                raise ValueError(f"Unsupported path_to_direct_scope: {scope}")
            if scope == "anchored" and str(getattr(cfg, "candidate_kind", "")).strip() in {
                "directed_causal",
                "causal_claim",
                "identified_causal_claim",
            }:
                keep_statuses = {"ordered_present__main_missing", "main_present__strict_missing"}
                scored = scored[scored.get("candidate_status_at_t", pd.Series("", index=scored.index)).astype(str).isin(keep_statuses)].copy()
                if scored.empty:
                    return scored
                scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
                scored["rank"] = scored.index + 1
        scored["cutoff_year_t"] = int(cutoff_t)
        return scored
    df = train_df.copy()
    if cfg.causal_only:
        df = df[df["is_causal"]]
    if cfg.min_stability is not None:
        df = df[df["stability"].fillna(-math.inf) >= float(cfg.min_stability)]
    if df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])

    wdf = _apply_weight_transform(
        df,
        cutoff_t=cutoff_t,
        recency_decay_lambda=cfg.recency_decay_lambda,
        stability_coef=cfg.stability_coef,
        causal_bonus=cfg.causal_bonus,
    )
    pairs = compute_underexplored_pairs(wdf, tau=cfg.tau)
    paths = compute_path_features(
        wdf,
        max_len=cfg.max_path_len,
        max_neighbors_per_mediator=cfg.max_neighbors_per_mediator,
    )
    motifs = compute_motif_features(
        wdf,
        max_neighbors_per_mediator=cfg.max_neighbors_per_mediator,
    )
    scored = compute_candidate_scores(
        pairs_df=pairs,
        paths_df=paths,
        motifs_df=motifs,
        alpha=cfg.alpha,
        beta=cfg.beta,
        gamma=cfg.gamma,
        delta=cfg.delta,
    )
    if scored.empty:
        return scored

    if cfg.cooc_trend_coef != 0:
        trend = _cooc_trajectory_proxy(pairs)
        scored = scored.merge(trend, how="left", on=["u", "v"])
        scored["cooc_trend_raw"] = scored["cooc_trend_raw"].fillna(0.0)
        tmin = float(scored["cooc_trend_raw"].min())
        tmax = float(scored["cooc_trend_raw"].max())
        if math.isclose(tmin, tmax):
            scored["cooc_trend_norm"] = 0.0 if tmax <= 0 else 1.0
        else:
            scored["cooc_trend_norm"] = (scored["cooc_trend_raw"] - tmin) / (tmax - tmin)
        scored["score"] = scored["score"] + float(cfg.cooc_trend_coef) * scored["cooc_trend_norm"]
    else:
        scored["cooc_trend_raw"] = 0.0
        scored["cooc_trend_norm"] = 0.0

    if cfg.field_hub_penalty_scale != 0:
        same_field = scored["u"].astype(str).str[0] == scored["v"].astype(str).str[0]
        scored["field_same_group"] = same_field.astype(int)
        scored["score"] = scored["score"] - float(cfg.field_hub_penalty_scale) * scored["hub_penalty"] * scored[
            "field_same_group"
        ]
    else:
        scored["field_same_group"] = 0

    scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
    scored["rank"] = scored.index + 1
    scored["cutoff_year_t"] = int(cutoff_t)
    return scored
