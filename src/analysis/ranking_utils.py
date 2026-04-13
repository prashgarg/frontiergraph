from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml

from src.analysis.common import CandidateBuildConfig, build_candidate_table
from src.features_pairs import compute_underexplored_pairs
from src.research_allocation_v2 import candidate_layer_mask, normalize_candidate_kind
from src.utils import pair_key


def candidate_cfg_from_config(
    config: dict,
    best_config_path: str | Path | None = None,
) -> CandidateBuildConfig:
    features_cfg = config.get("features", {})
    scoring_cfg = config.get("scoring", {})
    filters_cfg = config.get("filters", {})
    cfg = CandidateBuildConfig(
        tau=int(features_cfg.get("tau", 2)),
        max_path_len=int(features_cfg.get("max_path_len", 2)),
        max_neighbors_per_mediator=int(features_cfg.get("max_neighbors_per_mediator", 120)),
        alpha=float(scoring_cfg.get("alpha", 0.5)),
        beta=float(scoring_cfg.get("beta", 0.2)),
        gamma=float(scoring_cfg.get("gamma", 0.3)),
        delta=float(scoring_cfg.get("delta", 0.2)),
        causal_only=bool(filters_cfg.get("causal_only", False)),
        min_stability=filters_cfg.get("min_stability"),
        candidate_kind=str(filters_cfg.get("candidate_kind", "directed_causal")),
        candidate_family_mode=str(filters_cfg.get("candidate_family_mode", "path_to_direct")),
        path_to_direct_scope=str(filters_cfg.get("path_to_direct_scope", "broad")),
        fully_open_min_cooc_count=int(filters_cfg.get("fully_open_min_cooc_count", 1)),
        fully_open_min_motif_count=int(filters_cfg.get("fully_open_min_motif_count", 1)),
        fully_open_min_path_support_raw=(
            None
            if filters_cfg.get("fully_open_min_path_support_raw") is None
            else float(filters_cfg.get("fully_open_min_path_support_raw"))
        ),
        anchored_broad_start_pct=float(filters_cfg.get("anchored_broad_start_pct", 0.80)),
        anchored_min_resolution_score=float(filters_cfg.get("anchored_min_resolution_score", 0.18)),
        anchored_min_mediator_specificity_score=float(filters_cfg.get("anchored_min_mediator_specificity_score", 0.25)),
        anchored_min_path_support_raw=float(filters_cfg.get("anchored_min_path_support_raw", 2.0)),
        anchored_min_motif_count=int(filters_cfg.get("anchored_min_motif_count", 2)),
        anchored_min_mediator_count=int(filters_cfg.get("anchored_min_mediator_count", 2)),
        compression_mediator_specificity_min=float(filters_cfg.get("compression_mediator_specificity_min", 0.35)),
        compression_endpoint_resolution_min=float(filters_cfg.get("compression_endpoint_resolution_min", 0.15)),
        transparent_weight_support_strength=(
            None
            if scoring_cfg.get("transparent_weight_support_strength") is None
            else float(scoring_cfg.get("transparent_weight_support_strength"))
        ),
        transparent_weight_opportunity=(
            None
            if scoring_cfg.get("transparent_weight_opportunity") is None
            else float(scoring_cfg.get("transparent_weight_opportunity"))
        ),
        transparent_weight_specificity=(
            None
            if scoring_cfg.get("transparent_weight_specificity") is None
            else float(scoring_cfg.get("transparent_weight_specificity"))
        ),
        transparent_weight_resolution=(
            None
            if scoring_cfg.get("transparent_weight_resolution") is None
            else float(scoring_cfg.get("transparent_weight_resolution"))
        ),
        transparent_weight_mediator_specificity=(
            None
            if scoring_cfg.get("transparent_weight_mediator_specificity") is None
            else float(scoring_cfg.get("transparent_weight_mediator_specificity"))
        ),
        transparent_weight_provenance=(
            None
            if scoring_cfg.get("transparent_weight_provenance") is None
            else float(scoring_cfg.get("transparent_weight_provenance"))
        ),
        transparent_weight_topology=(
            None
            if scoring_cfg.get("transparent_weight_topology") is None
            else float(scoring_cfg.get("transparent_weight_topology"))
        ),
        transparent_bonus_fully_open_frontier=float(scoring_cfg.get("transparent_bonus_fully_open_frontier", 0.0)),
        transparent_bonus_contextual_to_ordered=float(scoring_cfg.get("transparent_bonus_contextual_to_ordered", 0.0)),
        transparent_bonus_ordered_to_causal=float(scoring_cfg.get("transparent_bonus_ordered_to_causal", 0.0)),
        transparent_bonus_causal_to_identified=float(scoring_cfg.get("transparent_bonus_causal_to_identified", 0.0)),
        transparent_bonus_ordered_direct_to_path=float(scoring_cfg.get("transparent_bonus_ordered_direct_to_path", 0.0)),
        transparent_bonus_causal_direct_to_path=float(scoring_cfg.get("transparent_bonus_causal_direct_to_path", 0.0)),
        transparent_bonus_identified_direct_to_path=float(scoring_cfg.get("transparent_bonus_identified_direct_to_path", 0.0)),
    )
    if best_config_path and Path(best_config_path).exists():
        payload = yaml.safe_load(Path(best_config_path).read_text(encoding="utf-8")) or {}
        for k, v in payload.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    return cfg


def main_ranking_for_cutoff(
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: CandidateBuildConfig,
) -> pd.DataFrame:
    out = build_candidate_table(train_df, cutoff_t=cutoff_t, cfg=cfg)
    if out.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    out = apply_boundary_rerank(
        out,
        boundary_bonus=float(getattr(cfg, "boundary_bonus", 0.0)),
        boundary_quota=float(getattr(cfg, "boundary_quota", 0.0)),
        quota_max_rank=int(getattr(cfg, "boundary_quota_max_rank", 1000)),
    )
    keep = [
        c
        for c in [
            "candidate_id",
            "candidate_kind",
            "candidate_kind_input",
            "candidate_family_mode",
            "candidate_family_mode_input",
            "candidate_layer",
            "candidate_family",
            "candidate_subfamily",
            "candidate_scope_bucket",
            "candidate_status_at_t",
            "focal_question_type",
            "compression_confidence",
            "compressed_triplet_json",
            "compression_failure_reason",
            "candidate_generation_gate_failed",
            "candidate_generation_gate_reason",
            "main_anchor_layer",
            "strict_anchor_layer",
            "u",
            "v",
            "source_id",
            "target_id",
            "source_label",
            "target_label",
            "pair_key",
            "score",
            "rank",
            "cooc_count",
            "support_paper_count",
            "support_year_min",
            "support_year_max",
            "path_support_norm",
            "motif_bonus_norm",
            "gap_bonus",
            "hub_penalty",
            "direct_support_norm",
            "mediator_count",
            "motif_count",
            "top_mediators_json",
            "top_paths_json",
            "evidence_motif_tags_json",
            "local_topology_class",
            "closure_state",
            "source_support_out_degree",
            "target_support_in_degree",
            "source_direct_out_degree",
            "target_direct_in_degree",
            "support_degree_product_norm",
            "direct_degree_product_norm",
            "transparent_support_strength_component",
            "transparent_opportunity_component",
            "transparent_specificity_component",
            "transparent_resolution_component",
            "transparent_mediator_specificity_component",
            "transparent_provenance_component",
            "transparent_topology_component",
            "source_support_total_degree",
            "target_support_total_degree",
            "endpoint_broadness_raw",
            "endpoint_broadness_pct",
            "endpoint_resolution_score",
            "focal_mediator_support_total_degree",
            "focal_mediator_broadness_raw",
            "focal_mediator_specificity_score",
            "source_node_age_years",
            "target_node_age_years",
            "focal_mediator_age_years",
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
            "contextual_support_count",
            "ordered_support_count",
            "causal_claim_support_count",
            "identified_causal_support_count",
            "direct_literature_status_main",
            "direct_literature_status_strict",
            "ordered_direct_literature_status",
            "contextual_direct_literature_status",
        ]
        if c in out.columns
    ]
    return out[keep].copy()


def _boundary_flag(df: pd.DataFrame) -> pd.Series:
    cooc = pd.to_numeric(df.get("cooc_count", 0), errors="coerce").fillna(0.0).astype(float)
    cross = df["u"].astype(str).str[0] != df["v"].astype(str).str[0]
    return (cross & (cooc <= 0.0)).astype(int)


def apply_boundary_rerank(
    scored_df: pd.DataFrame,
    boundary_bonus: float = 0.0,
    boundary_quota: float = 0.0,
    quota_max_rank: int = 1000,
) -> pd.DataFrame:
    if scored_df.empty:
        return scored_df.copy()
    g = scored_df.copy()
    if "score" not in g.columns:
        g["score"] = 0.0
    g["boundary_flag"] = _boundary_flag(g)
    g["score_adj"] = g["score"].astype(float) + float(boundary_bonus) * g["boundary_flag"].astype(float)

    if float(boundary_quota) <= 0:
        g = g.sort_values("score_adj", ascending=False).reset_index(drop=True)
        g["rank"] = g.index + 1
        g = g.drop(columns=["score_adj"])
        return g

    b = g[g["boundary_flag"] == 1].sort_values("score_adj", ascending=False).reset_index(drop=True)
    n = g[g["boundary_flag"] == 0].sort_values("score_adj", ascending=False).reset_index(drop=True)
    ib = 0
    inn = 0
    sel_b = 0
    rows: list[dict] = []
    total = len(g)
    q = max(0.0, min(1.0, float(boundary_quota)))
    max_rank = max(1, int(quota_max_rank))

    for r in range(1, total + 1):
        enforce = r <= max_rank
        required_b = int(np.ceil(q * float(r))) if enforce else int(np.ceil(q * float(max_rank)))
        pick_boundary = enforce and (sel_b < required_b) and (ib < len(b))
        if pick_boundary:
            row = b.iloc[ib].to_dict()
            ib += 1
            sel_b += 1
            rows.append(row)
            continue

        has_b = ib < len(b)
        has_n = inn < len(n)
        if has_b and has_n:
            if float(b.iloc[ib]["score_adj"]) >= float(n.iloc[inn]["score_adj"]):
                row = b.iloc[ib].to_dict()
                ib += 1
                sel_b += 1
            else:
                row = n.iloc[inn].to_dict()
                inn += 1
            rows.append(row)
        elif has_b:
            row = b.iloc[ib].to_dict()
            ib += 1
            sel_b += 1
            rows.append(row)
        elif has_n:
            row = n.iloc[inn].to_dict()
            inn += 1
            rows.append(row)
        else:
            break

    out = pd.DataFrame(rows)
    out = out.reset_index(drop=True)
    out["rank"] = out.index + 1
    out = out.drop(columns=["score_adj"])
    return out


def build_all_pairs(nodes: Iterable[str]) -> pd.DataFrame:
    arr = np.array(sorted(set(str(n) for n in nodes)), dtype=object)
    if arr.size == 0:
        return pd.DataFrame(columns=["u", "v"])
    u = np.repeat(arr, arr.size)
    v = np.tile(arr, arr.size)
    mask = u != v
    return pd.DataFrame({"u": u[mask], "v": v[mask]})


def missing_pairs(train_df: pd.DataFrame, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    if all_pairs_df.empty:
        return all_pairs_df.copy()
    existing = (
        train_df[["src_code", "dst_code"]]
        .drop_duplicates()
        .rename(columns={"src_code": "u", "dst_code": "v"})
        .astype(str)
    )
    merged = all_pairs_df.merge(existing.assign(_exists=1), on=["u", "v"], how="left")
    return merged[merged["_exists"].isna()][["u", "v"]].reset_index(drop=True)


def cooc_gap_ranking(train_df: pd.DataFrame, tau: int, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    base = missing_pairs(train_df, all_pairs_df)
    if base.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    pairs = compute_underexplored_pairs(train_df, tau=tau)
    gap_map = {pair_key(str(r.u), str(r.v)): float(r.gap_bonus) for r in pairs.itertuples(index=False)}
    base["score"] = [gap_map.get(pair_key(str(r.u), str(r.v)), 1.0) for r in base.itertuples(index=False)]
    base = base.sort_values("score", ascending=False).reset_index(drop=True)
    base["rank"] = base.index + 1
    return base


def cooc_gap_ranking_from_universe(
    train_df: pd.DataFrame,
    candidate_pairs_df: pd.DataFrame,
    tau: int,
) -> pd.DataFrame:
    if candidate_pairs_df.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    if "edge_kind" in train_df.columns:
        base = candidate_pairs_df[["u", "v"]].drop_duplicates().copy()
        context_counts = compute_underexplored_pairs(train_df, tau=tau)
        gap_map = {pair_key(str(r.u), str(r.v)): float(r.gap_bonus) for r in context_counts.itertuples(index=False)}
        base["score"] = [gap_map.get(pair_key(str(r.u), str(r.v)), 0.0) for r in base.itertuples(index=False)]
        base = base.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
        base["rank"] = base.index + 1
        return base
    return cooc_gap_ranking(train_df, tau=tau, all_pairs_df=candidate_pairs_df[["u", "v"]].drop_duplicates())


def pref_attach_ranking(train_df: pd.DataFrame, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    base = missing_pairs(train_df, all_pairs_df)
    if base.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    out_deg = train_df.groupby("src_code", as_index=False).agg(out_degree=("dst_code", "nunique"))
    in_deg = train_df.groupby("dst_code", as_index=False).agg(in_degree=("src_code", "nunique"))
    out_map = {str(r.src_code): int(r.out_degree) for r in out_deg.itertuples(index=False)}
    in_map = {str(r.dst_code): int(r.in_degree) for r in in_deg.itertuples(index=False)}
    base["score"] = [float(out_map.get(str(r.u), 0) * in_map.get(str(r.v), 0)) for r in base.itertuples(index=False)]
    base = base.sort_values("score", ascending=False).reset_index(drop=True)
    base["rank"] = base.index + 1
    return base


def pref_attach_ranking_from_universe(
    train_df: pd.DataFrame,
    candidate_pairs_df: pd.DataFrame,
) -> pd.DataFrame:
    if candidate_pairs_df.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    base = candidate_pairs_df[["u", "v"]].drop_duplicates().copy()
    if "edge_kind" in train_df.columns:
        candidate_kind = None
        if "candidate_kind" in candidate_pairs_df.columns and not candidate_pairs_df["candidate_kind"].empty:
            candidate_kind = normalize_candidate_kind(candidate_pairs_df["candidate_kind"].iloc[0])
        if candidate_kind == "contextual_pair":
            degree_df = (
                train_df[candidate_layer_mask(train_df, "contextual_pair")][["src_code", "dst_code"]]
                .melt(value_vars=["src_code", "dst_code"], value_name="code")
                .groupby("code", as_index=False)
                .agg(degree=("code", "size"))
            )
            degree_map = {str(r.code): int(r.degree) for r in degree_df.itertuples(index=False)}
            base["score"] = [float(degree_map.get(str(r.u), 0) * degree_map.get(str(r.v), 0)) for r in base.itertuples(index=False)]
        else:
            support_df = train_df.copy()
            if "edge_kind" in support_df.columns:
                ordered = support_df[candidate_layer_mask(support_df, "ordered_claim")][["src_code", "dst_code"]].copy()
                contextual = support_df[candidate_layer_mask(support_df, "contextual_pair")][["src_code", "dst_code"]].copy()
                rev = contextual.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
                support_df = pd.concat([ordered, contextual, rev], ignore_index=True)
            out_deg = support_df.groupby("src_code", as_index=False).agg(out_degree=("dst_code", "nunique"))
            in_deg = support_df.groupby("dst_code", as_index=False).agg(in_degree=("src_code", "nunique"))
            out_map = {str(r.src_code): int(r.out_degree) for r in out_deg.itertuples(index=False)}
            in_map = {str(r.dst_code): int(r.in_degree) for r in in_deg.itertuples(index=False)}
            base["score"] = [float(out_map.get(str(r.u), 0) * in_map.get(str(r.v), 0)) for r in base.itertuples(index=False)]
        base = base.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
        base["rank"] = base.index + 1
        return base
    return pref_attach_ranking(train_df, all_pairs_df=base)


def comparison_rankings_for_cutoff(
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: CandidateBuildConfig,
    tau: int,
) -> dict[str, pd.DataFrame]:
    main = main_ranking_for_cutoff(train_df, cutoff_t=cutoff_t, cfg=cfg)
    if main.empty:
        empty = pd.DataFrame(columns=["u", "v", "score", "rank"])
        return {"main": empty, "cooc_gap": empty.copy(), "pref_attach": empty.copy()}
    universe = main[
        [
            c
            for c in main.columns
            if c in [
                "u",
                "v",
                "candidate_kind",
                "candidate_family_mode",
                "candidate_layer",
                "candidate_family",
                "cooc_count",
            ]
        ]
    ].copy()
    return {
        "main": main,
        "cooc_gap": cooc_gap_ranking_from_universe(train_df, candidate_pairs_df=universe, tau=tau),
        "pref_attach": pref_attach_ranking_from_universe(train_df, candidate_pairs_df=universe),
    }


def evaluate_binary_ranking(
    ranked_df: pd.DataFrame,
    positives: set[tuple[str, str]],
    k_values: list[int],
) -> dict[str, float]:
    rank_map = {(str(r.u), str(r.v)): int(i + 1) for i, r in enumerate(ranked_df[["u", "v"]].itertuples(index=False))}
    n_pos = len(positives)
    out: dict[str, float] = {"n_positives": float(n_pos), "n_missing_edges": float(len(ranked_df))}
    total = max(1, n_pos)
    for k in k_values:
        hits = sum(1 for edge in positives if rank_map.get(edge, np.inf) <= int(k))
        out[f"hits_at_{k}"] = float(hits)
        out[f"precision_at_{k}"] = float(hits) / float(max(1, int(k)))
        out[f"recall_at_{k}"] = float(hits) / float(total)
    rr = [1.0 / rank_map[e] if e in rank_map else 0.0 for e in positives]
    out["mrr"] = float(np.mean(rr) if rr else 0.0)
    return out


def parse_horizons(raw: str | Iterable[int], default: list[int] | None = None) -> list[int]:
    if isinstance(raw, str):
        hs = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    else:
        hs = [int(x) for x in raw]
    hs = sorted(set(h for h in hs if h > 0))
    if hs:
        return hs
    return default or [3, 5, 10]


def parse_cutoff_years(
    requested: list[int] | None,
    min_year: int,
    max_year: int,
    max_h: int,
    step: int = 1,
) -> list[int]:
    lo = int(min_year + 1)
    hi = int(max_year - max_h)
    if requested:
        out = sorted({int(y) for y in requested if lo <= int(y) <= hi})
        return out
    return list(range(lo, hi + 1, max(1, int(step))))


def serialize_cfg(cfg: CandidateBuildConfig) -> dict:
    return asdict(cfg)
