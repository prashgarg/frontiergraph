from __future__ import annotations

import argparse
import math
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from src.analysis.common import CandidateBuildConfig, ensure_output_dir, set_seed
from src.analysis.ranking_utils import comparison_rankings_for_cutoff
from src.research_allocation_v2 import first_appearance_map_v2
from src.utils import load_config, load_corpus


FIXED_K_DEFAULTS = [10, 50, 100, 500, 1000]
PCT_K_DEFAULTS = [0.0001, 0.0005, 0.001, 0.005]
DEFAULT_MAIN_HORIZONS = [5, 10, 15]
DEFAULT_APPENDIX_HORIZONS = [20]
PRIMARY_DIMS = [
    "overall",
    "cutoff_period",
    "first_year_decade",
    "first_source",
    "first_subfield_group",
    "first_topic_group",
    "first_method_group",
    "first_theory_empirical",
    "first_causal_presentation",
    "first_has_grant",
    "first_fwci_band",
]
INTERACTION_DIMS = [
    "first_subfield_group x cutoff_period",
    "first_has_grant x first_source",
    "first_method_group x cutoff_period",
]
OPTIONAL_DIMS = ["first_funder_group"]
HORIZON_COLORS = {
    3: "#b7d4ea",
    5: "#7fb3d5",
    10: "#3f7fb3",
    15: "#0b3c6f",
    20: "#4b5563",
}

ECON_TOPIC_HINTS = (
    "econom",
    "finance",
    "public",
    "trade",
    "monetary",
    "macro",
    "labor",
    "development",
    "political",
    "business",
    "energy",
    "environment",
    "urban",
    "education",
    "health",
    "inequality",
    "growth",
)


def _mode_or_mixed(values: pd.Series, default: str = "Unknown") -> str:
    vals = values.dropna().astype(str)
    vals = vals[vals != ""]
    if vals.empty:
        return default
    counts = vals.value_counts()
    if len(counts) == 1:
        return str(counts.index[0])
    if int(counts.iloc[0]) == int(counts.iloc[1]):
        return "Mixed"
    return str(counts.index[0])


def _method_group(evidence_type: str) -> str:
    et = str(evidence_type or "Unknown")
    if et in {"experiment", "DiD", "IV", "RDD", "event_study"}:
        return "design_based_causal"
    if et in {"panel_FE_or_TWFE", "time_series_econometrics"}:
        return "panel_or_time_series"
    if et == "theory_or_model":
        return "theory_or_model"
    if et in {"structural_model", "simulation"}:
        return "structural_or_simulation"
    if et in {"descriptive_observational", "prediction_or_forecasting", "qualitative_or_case_study"}:
        return "descriptive_or_predictive"
    if et in {"other", "do_not_know"}:
        return "other_or_unknown"
    return et


def _theory_empirical_bucket(evidence_type: str) -> str:
    et = str(evidence_type or "Unknown")
    if et == "theory_or_model":
        return "theory"
    if et in {"other", "do_not_know"}:
        return "unknown"
    return "empirical"


def _assign_top_groups(series: pd.Series, top_n: int, other_label: str = "Other") -> pd.Series:
    vals = series.fillna("Unknown").astype(str)
    top = vals.value_counts().head(top_n).index.tolist()
    return vals.where(vals.isin(top), other_label)


def _pct_suffix(p: float) -> str:
    value = f"{p * 100:.3f}".rstrip("0").rstrip(".")
    value = value.replace(".", "_")
    return f"pct_{value}"


def _pct_label_from_suffix(suffix: str) -> str:
    raw = suffix.replace("pct_", "").replace("_", ".")
    return f"{raw}%"


def _clean_group_label(value: str) -> str:
    txt = str(value)
    replacements = {
        "True": "Funded",
        "False": "Unfunded",
        "core": "Core",
        "adjacent": "Adjacent",
        "unknown": "Unknown",
        "other_or_unknown": "Other or unknown",
        "panel_or_time_series": "Panel or time series",
        "design_based_causal": "Design-based causal",
        "descriptive_or_predictive": "Descriptive or predictive",
        "structural_or_simulation": "Structural or simulation",
        "theory_or_model": "Theory or model",
    }
    return replacements.get(txt, txt)


def _pretty_label(value: str, wrap: int | None = None) -> str:
    txt = _clean_group_label(value)
    txt = txt.replace("_", " ")
    txt = " ".join(txt.split())
    if txt.lower() == txt:
        txt = txt.title()
    if wrap and len(txt) > wrap:
        return "\n".join(textwrap.wrap(txt, width=wrap))
    return txt


def _prefer_econ_groups(groups_df: pd.DataFrame, top_n: int) -> list[str]:
    if groups_df.empty:
        return []
    work = groups_df.copy()
    work["group_str"] = work["group"].astype(str)
    work["is_econ_facing"] = work["group_str"].str.lower().map(
        lambda text: any(hint in text for hint in ECON_TOPIC_HINTS)
    )
    preferred = work[
        work["is_econ_facing"]
        & ~work["group_str"].isin(["Mixed", "Other", "Unknown", "Other/Unknown"])
    ].sort_values("total_group_edges", ascending=False)
    chosen = preferred["group_str"].head(top_n).tolist()
    if len(chosen) < top_n:
        fallback = work[
            ~work["group_str"].isin(["Mixed", "Other", "Unknown", "Other/Unknown"])
            & ~work["group_str"].isin(chosen)
        ].sort_values("total_group_edges", ascending=False)
        chosen.extend(fallback["group_str"].head(top_n - len(chosen)).tolist())
    return chosen[:top_n]


def _cutoff_period_label(year: int) -> str:
    return f"{int(year // 10) * 10}s"


def _eligible_cutoffs(
    start_year: int,
    end_year: int,
    step: int,
    max_observed_year: int,
    horizons: list[int],
) -> list[int]:
    if step <= 0:
        raise ValueError("cutoff step must be positive")
    max_cutoff = max_observed_year - min(horizons)
    final_end = min(end_year, max_cutoff)
    return [int(y) for y in range(int(start_year), int(final_end) + 1, int(step))]


def _bootstrap_mean_ci_fast(
    values: pd.Series | np.ndarray | list[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    if arr.size == 1:
        value = float(arr[0])
        return value, value, value
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(int(n_boot), arr.size))
    means = arr[idx].mean(axis=1)
    mean = float(arr.mean())
    lo = float(np.quantile(means, alpha / 2))
    hi = float(np.quantile(means, 1 - alpha / 2))
    return mean, lo, hi


def _rank_subset_metrics(
    rank_map: dict[tuple[str, str], int],
    positives: set[tuple[str, str]],
    fixed_k_values: list[int],
    pct_k_map: dict[str, int],
) -> dict[str, float]:
    n_pos = len(positives)
    ranks = np.asarray([float(rank_map.get(edge, np.inf)) for edge in positives], dtype=float)
    finite = np.isfinite(ranks)
    out: dict[str, float] = {"n_positives": float(n_pos), "n_candidates": float(len(rank_map))}
    total = max(1, n_pos)
    for k in fixed_k_values:
        hits = int(np.sum(finite & (ranks <= int(k))))
        out[f"hits_at_{int(k)}"] = float(hits)
        out[f"recall_at_{int(k)}"] = float(hits) / float(total)
    for suffix, k in pct_k_map.items():
        hits = int(np.sum(finite & (ranks <= int(k))))
        out[f"hits_at_{suffix}"] = float(hits)
        out[f"recall_at_{suffix}"] = float(hits) / float(total)
        out[f"k_at_{suffix}"] = float(k)
    rr = np.where(finite, 1.0 / ranks, 0.0)
    out["mrr"] = float(rr.mean() if rr.size else 0.0)
    return out


def build_first_edge_metadata(corpus_df: pd.DataFrame, paper_meta_df: pd.DataFrame, candidate_kind: str) -> pd.DataFrame:
    kind_df = corpus_df[corpus_df["edge_kind"] == candidate_kind].copy()
    if kind_df.empty:
        return pd.DataFrame(columns=["u", "v", "first_year"])

    first_year_df = (
        kind_df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(first_year=("year", "min"))
        .rename(columns={"src_code": "u", "dst_code": "v"})
    )
    first_rows = kind_df.merge(
        first_year_df,
        left_on=["src_code", "dst_code", "year"],
        right_on=["u", "v", "first_year"],
        how="inner",
    )
    first_rows = first_rows.merge(paper_meta_df, on="paper_id", how="left", suffixes=("", "_paper"))
    first_rows["method_group"] = first_rows["evidence_type"].map(_method_group)
    first_rows["theory_empirical"] = first_rows["evidence_type"].map(_theory_empirical_bucket)
    if "has_grant" not in first_rows.columns:
        first_rows["has_grant"] = False
    first_rows["has_grant"] = first_rows["has_grant"].fillna(False).astype(bool)
    if "first_funder" not in first_rows.columns:
        first_rows["first_funder"] = "Unknown"
    if "fwci" not in first_rows.columns:
        first_rows["fwci"] = np.nan
    if "cited_by_count" not in first_rows.columns:
        first_rows["cited_by_count"] = np.nan
    if "primary_subfield_display_name" not in first_rows.columns:
        first_rows["primary_subfield_display_name"] = "Unknown"
    if "primary_topic_display_name" not in first_rows.columns:
        first_rows["primary_topic_display_name"] = "Unknown"
    if "source_paper" not in first_rows.columns and "source" not in first_rows.columns:
        first_rows["source"] = "Unknown"

    rows: list[dict] = []
    for (u, v, first_year), g in first_rows.groupby(["u", "v", "first_year"], dropna=False):
        rows.append(
            {
                "u": str(u),
                "v": str(v),
                "first_year": int(first_year),
                "first_year_decade": f"{int(first_year // 10) * 10}s",
                "first_source": _mode_or_mixed(g["source_paper"] if "source_paper" in g.columns else g["source"]),
                "first_subfield": _mode_or_mixed(g["primary_subfield_display_name"]),
                "first_topic": _mode_or_mixed(g["primary_topic_display_name"]),
                "first_method_group": _mode_or_mixed(g["method_group"]),
                "first_evidence_type": _mode_or_mixed(g["evidence_type"]),
                "first_theory_empirical": _mode_or_mixed(g["theory_empirical"]),
                "first_causal_presentation": _mode_or_mixed(g["causal_presentation"]),
                "first_has_grant": "Funded" if bool(g["has_grant"].any()) else "Unfunded",
                "first_funder": _mode_or_mixed(g["first_funder"]),
                "first_fwci_mean": float(pd.to_numeric(g["fwci"], errors="coerce").mean()),
                "first_cited_by_mean": float(pd.to_numeric(g["cited_by_count"], errors="coerce").mean()),
                "n_first_year_papers": int(g["paper_id"].nunique()),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["first_subfield_group"] = _assign_top_groups(out["first_subfield"], top_n=12)
    out["first_topic_group"] = _assign_top_groups(out["first_topic"], top_n=12)
    out["first_funder_group"] = _assign_top_groups(out["first_funder"].replace("Unknown", np.nan), top_n=6, other_label="Other/Unknown").fillna("Other/Unknown")
    fwci = pd.to_numeric(out["first_fwci_mean"], errors="coerce")
    if fwci.notna().sum() >= 4:
        out["first_fwci_band"] = pd.qcut(fwci.rank(method="first"), q=4, labels=["low", "mid_low", "mid_high", "high"])
    else:
        out["first_fwci_band"] = "Unknown"
    out["first_fwci_band"] = out["first_fwci_band"].astype(str)
    for col in [
        "first_source",
        "first_subfield_group",
        "first_method_group",
        "first_theory_empirical",
        "first_causal_presentation",
        "first_funder_group",
    ]:
        out[col] = out[col].fillna("Unknown").astype(str)
    return out


def _dimension_columns(meta_df: pd.DataFrame) -> dict[str, pd.Series]:
    out = {
        "overall": pd.Series(["All"] * len(meta_df), index=meta_df.index, dtype=object),
        "cutoff_period": meta_df["cutoff_period"].astype(str),
        "first_year_decade": meta_df["first_year_decade"].astype(str),
        "first_source": meta_df["first_source"].astype(str),
        "first_subfield_group": meta_df["first_subfield_group"].astype(str),
        "first_topic_group": meta_df["first_topic_group"].astype(str),
        "first_method_group": meta_df["first_method_group"].astype(str),
        "first_theory_empirical": meta_df["first_theory_empirical"].astype(str),
        "first_causal_presentation": meta_df["first_causal_presentation"].astype(str),
        "first_has_grant": meta_df["first_has_grant"].astype(str),
        "first_fwci_band": meta_df["first_fwci_band"].astype(str),
        "first_funder_group": meta_df["first_funder_group"].astype(str),
    }
    out["first_subfield_group x cutoff_period"] = meta_df["first_subfield_group"].astype(str) + " | " + meta_df["cutoff_period"].astype(str)
    out["first_has_grant x first_source"] = meta_df["first_has_grant"].astype(str) + " | " + meta_df["first_source"].astype(str)
    out["first_method_group x cutoff_period"] = meta_df["first_method_group"].astype(str) + " | " + meta_df["cutoff_period"].astype(str)
    return out


def _group_parts(dimension: str, group: str) -> tuple[str | None, str | None]:
    if " x " not in dimension:
        return None, None
    parts = str(group).split(" | ", 1)
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def compute_subgroup_panel(
    corpus_df: pd.DataFrame,
    cfg: CandidateBuildConfig,
    candidate_kind: str,
    years: list[int],
    horizons: list[int],
    edge_meta_df: pd.DataFrame,
    fixed_k_values: list[int],
    pct_k_values: list[float],
    dimensions: list[str],
) -> pd.DataFrame:
    tau = int(cfg.tau)
    first_year_map = first_appearance_map_v2(corpus_df, candidate_kind=candidate_kind)
    max_observed_year = int(pd.to_numeric(corpus_df["year"], errors="coerce").max())
    rows: list[dict] = []
    for t in years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        if train.empty:
            continue
        rankings = comparison_rankings_for_cutoff(train, cutoff_t=int(t), cfg=cfg, tau=tau)
        rank_maps = {
            model: {(str(r.u), str(r.v)): int(i + 1) for i, r in enumerate(ranking[["u", "v"]].itertuples(index=False))}
            for model, ranking in rankings.items()
        }
        for h in horizons:
            if int(t + h) > max_observed_year:
                continue
            positives = {edge for edge, y in first_year_map.items() if int(t) <= int(y) <= int(t + h)}
            if not positives:
                continue
            pos_df = pd.DataFrame(list(positives), columns=["u", "v"])
            meta = edge_meta_df.merge(pos_df, on=["u", "v"], how="inner")
            if meta.empty:
                continue
            meta = meta.copy()
            meta["cutoff_period"] = _cutoff_period_label(int(t))
            dim_cols = _dimension_columns(meta)
            for dim in dimensions:
                if dim not in dim_cols:
                    continue
                tmp = meta.assign(_group=dim_cols[dim].fillna("Unknown").astype(str))
                for group_value, sub in tmp.groupby("_group", dropna=False):
                    edges_df = sub[["u", "v"]].drop_duplicates()
                    group_edges = {(str(r.u), str(r.v)) for r in edges_df.itertuples(index=False)}
                    if not group_edges:
                        continue
                    left, right = _group_parts(dim, str(group_value))
                    for model, rank_map in rank_maps.items():
                        pct_k_map = {suffix: max(10, int(math.ceil(float(p) * max(1, len(rank_map))))) for suffix, p in [(_pct_suffix(x), x) for x in pct_k_values]}
                        metrics = _rank_subset_metrics(rank_map=rank_map, positives=group_edges, fixed_k_values=fixed_k_values, pct_k_map=pct_k_map)
                        rows.append(
                            {
                                "panel_kind": candidate_kind,
                                "candidate_kind": candidate_kind,
                                "cutoff_year_t": int(t),
                                "cutoff_period": _cutoff_period_label(int(t)),
                                "horizon": int(h),
                                "dimension": str(dim),
                                "group": str(group_value),
                                "group_left": left,
                                "group_right": right,
                                "model": str(model),
                                "total_future_edges_all": int(len(positives)),
                                "n_group_edges": int(len(group_edges)),
                                **metrics,
                            }
                        )
    return pd.DataFrame(rows)


def _metric_columns(panel_df: pd.DataFrame, prefix: str) -> list[str]:
    return sorted([c for c in panel_df.columns if c.startswith(prefix)])


def build_pooled_panel(kind_panel_df: pd.DataFrame) -> pd.DataFrame:
    if kind_panel_df.empty:
        return pd.DataFrame()
    hit_cols = _metric_columns(kind_panel_df, "hits_at_")
    recall_cols = _metric_columns(kind_panel_df, "recall_at_")
    k_cols = _metric_columns(kind_panel_df, "k_at_")
    rows: list[dict] = []
    key_cols = ["cutoff_year_t", "cutoff_period", "horizon", "dimension", "group", "group_left", "group_right", "model"]
    for keys, g in kind_panel_df.groupby(key_cols, dropna=False):
        rec: dict[str, object] = dict(zip(key_cols, keys))
        weight = pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).astype(float).to_numpy()
        denom = float(weight.sum())
        rec["panel_kind"] = "pooled"
        rec["candidate_kind"] = "pooled"
        rec["n_group_edges"] = int(denom)
        rec["total_future_edges_all"] = int(pd.to_numeric(g["total_future_edges_all"], errors="coerce").fillna(0).sum())
        rec["n_positives"] = float(denom)
        rec["n_candidates"] = float(np.average(pd.to_numeric(g["n_candidates"], errors="coerce").fillna(0), weights=np.where(weight > 0, weight, 1.0)))
        for col in hit_cols:
            rec[col] = float(pd.to_numeric(g[col], errors="coerce").fillna(0).sum())
        for col in recall_cols:
            hit_col = col.replace("recall_at_", "hits_at_")
            rec[col] = float(rec.get(hit_col, 0.0)) / float(max(1, rec["n_group_edges"]))
        for col in k_cols:
            rec[col] = float(np.average(pd.to_numeric(g[col], errors="coerce").fillna(0), weights=np.where(weight > 0, weight, 1.0)))
        mrr_values = pd.to_numeric(g["mrr"], errors="coerce").fillna(0).to_numpy(dtype=float)
        rec["mrr"] = float(np.average(mrr_values, weights=np.where(weight > 0, weight, 1.0)))
        rows.append(rec)
    return pd.DataFrame(rows)


def build_model_summary(panel_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    hit_cols = _metric_columns(panel_df, "hits_at_")
    recall_cols = _metric_columns(panel_df, "recall_at_")
    k_cols = _metric_columns(panel_df, "k_at_")
    rows: list[dict] = []
    key_cols = ["panel_kind", "dimension", "group", "group_left", "group_right", "model", "horizon"]
    for keys, g in panel_df.groupby(key_cols, dropna=False):
        rec: dict[str, object] = dict(zip(key_cols, keys))
        rec["n_cutoffs"] = int(g["cutoff_year_t"].nunique())
        rec["total_group_edges"] = int(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).sum())
        rec["mean_group_edges"] = float(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).mean())
        rec["mean_total_future_edges"] = float(pd.to_numeric(g["total_future_edges_all"], errors="coerce").fillna(0).mean())
        rec["mean_n_candidates"] = float(pd.to_numeric(g["n_candidates"], errors="coerce").fillna(0).mean())
        rec["mrr"] = float(pd.to_numeric(g["mrr"], errors="coerce").fillna(0).mean())
        for col in hit_cols + recall_cols + k_cols:
            rec[col] = float(pd.to_numeric(g[col], errors="coerce").fillna(0).mean())
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(["panel_kind", "dimension", "group", "horizon", "model"]).reset_index(drop=True)


def build_compare_panel(panel_df: pd.DataFrame, fixed_k_values: list[int], pct_k_values: list[float]) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    m = panel_df[panel_df["model"] == "main"].copy()
    p = panel_df[panel_df["model"] == "pref_attach"].copy()
    if m.empty or p.empty:
        return pd.DataFrame()
    key_cols = ["panel_kind", "cutoff_year_t", "cutoff_period", "horizon", "dimension", "group", "group_left", "group_right"]
    joined = m.merge(p, on=key_cols, suffixes=("_main", "_pref"), how="inner")
    if joined.empty:
        return pd.DataFrame()
    for k in fixed_k_values:
        joined[f"delta_recall_at_{k}"] = joined[f"recall_at_{k}_main"] - joined[f"recall_at_{k}_pref"]
        joined[f"delta_hits_at_{k}"] = joined[f"hits_at_{k}_main"] - joined[f"hits_at_{k}_pref"]
        denom = joined[f"recall_at_{k}_pref"].replace(0, np.nan)
        joined[f"relative_advantage_at_{k}"] = (joined[f"recall_at_{k}_main"] / denom) - 1.0
    pct_suffixes = [_pct_suffix(p) for p in pct_k_values]
    for suffix in pct_suffixes:
        joined[f"delta_recall_at_{suffix}"] = joined[f"recall_at_{suffix}_main"] - joined[f"recall_at_{suffix}_pref"]
        joined[f"delta_hits_at_{suffix}"] = joined[f"hits_at_{suffix}_main"] - joined[f"hits_at_{suffix}_pref"]
        denom = joined[f"recall_at_{suffix}_pref"].replace(0, np.nan)
        joined[f"relative_advantage_at_{suffix}"] = (joined[f"recall_at_{suffix}_main"] / denom) - 1.0
    joined["delta_mrr"] = joined["mrr_main"] - joined["mrr_pref"]
    joined["relative_advantage_mrr"] = (joined["mrr_main"] / joined["mrr_pref"].replace(0, np.nan)) - 1.0
    fixed_delta_cols = [f"delta_recall_at_{k}" for k in fixed_k_values]
    pct_delta_cols = [f"delta_recall_at_{suffix}" for suffix in pct_suffixes]
    joined["frontier_delta_fixedK"] = joined[fixed_delta_cols].mean(axis=1)
    joined["frontier_delta_pctK"] = joined[pct_delta_cols].mean(axis=1)
    keep = key_cols + [
        "n_group_edges_main",
        "total_future_edges_all_main",
        "n_candidates_main",
        "n_group_edges_pref",
        "total_future_edges_all_pref",
        "n_candidates_pref",
        "mrr_main",
        "mrr_pref",
        "delta_mrr",
        "relative_advantage_mrr",
        "frontier_delta_fixedK",
        "frontier_delta_pctK",
    ]
    for k in fixed_k_values:
        keep.extend(
            [
                f"hits_at_{k}_main",
                f"hits_at_{k}_pref",
                f"recall_at_{k}_main",
                f"recall_at_{k}_pref",
                f"delta_hits_at_{k}",
                f"delta_recall_at_{k}",
                f"relative_advantage_at_{k}",
            ]
        )
    for suffix in pct_suffixes:
        keep.extend(
            [
                f"hits_at_{suffix}_main",
                f"hits_at_{suffix}_pref",
                f"recall_at_{suffix}_main",
                f"recall_at_{suffix}_pref",
                f"delta_hits_at_{suffix}",
                f"delta_recall_at_{suffix}",
                f"relative_advantage_at_{suffix}",
                f"k_at_{suffix}_main",
                f"k_at_{suffix}_pref",
            ]
        )
    out = joined[keep].rename(
        columns={
            "n_group_edges_main": "n_group_edges",
            "total_future_edges_all_main": "total_future_edges_all",
            "n_candidates_main": "n_candidates",
        }
    )
    return out.sort_values(["panel_kind", "dimension", "group", "horizon", "cutoff_year_t"]).reset_index(drop=True)


def build_frontier_summary(compare_df: pd.DataFrame, fixed_k_values: list[int], pct_k_values: list[float], n_boot: int, seed: int) -> pd.DataFrame:
    if compare_df.empty:
        return pd.DataFrame()
    pct_suffixes = [_pct_suffix(p) for p in pct_k_values]
    rows: list[dict] = []
    key_cols = ["panel_kind", "dimension", "group", "group_left", "group_right", "horizon"]
    for keys, g in compare_df.groupby(key_cols, dropna=False):
        rec: dict[str, object] = dict(zip(key_cols, keys))
        rec["n_cutoffs"] = int(g["cutoff_year_t"].nunique())
        rec["total_group_edges"] = int(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).sum())
        rec["mean_group_edges"] = float(pd.to_numeric(g["n_group_edges"], errors="coerce").fillna(0).mean())
        rec["mean_total_future_edges"] = float(pd.to_numeric(g["total_future_edges_all"], errors="coerce").fillna(0).mean())
        rec["mean_n_candidates"] = float(pd.to_numeric(g["n_candidates"], errors="coerce").fillna(0).mean())
        rec["display_ok_1d"] = bool(rec["total_group_edges"] >= 500 and rec["n_cutoffs"] >= 3)
        rec["display_ok_2d"] = bool(rec["total_group_edges"] >= 250 and rec["n_cutoffs"] >= 2)
        for k in fixed_k_values:
            for prefix in ["hits_at", "recall_at"]:
                rec[f"{prefix}_{k}_main"] = float(pd.to_numeric(g[f"{prefix}_{k}_main"], errors="coerce").fillna(0).mean())
                rec[f"{prefix}_{k}_pref"] = float(pd.to_numeric(g[f"{prefix}_{k}_pref"], errors="coerce").fillna(0).mean())
            rec[f"delta_hits_at_{k}"] = float(pd.to_numeric(g[f"delta_hits_at_{k}"], errors="coerce").fillna(0).mean())
            rec[f"delta_recall_at_{k}"] = float(pd.to_numeric(g[f"delta_recall_at_{k}"], errors="coerce").fillna(0).mean())
            rec[f"relative_advantage_at_{k}"] = float(pd.to_numeric(g[f"relative_advantage_at_{k}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean())
        for suffix in pct_suffixes:
            rec[f"recall_at_{suffix}_main"] = float(pd.to_numeric(g[f"recall_at_{suffix}_main"], errors="coerce").fillna(0).mean())
            rec[f"recall_at_{suffix}_pref"] = float(pd.to_numeric(g[f"recall_at_{suffix}_pref"], errors="coerce").fillna(0).mean())
            rec[f"delta_recall_at_{suffix}"] = float(pd.to_numeric(g[f"delta_recall_at_{suffix}"], errors="coerce").fillna(0).mean())
            rec[f"relative_advantage_at_{suffix}"] = float(pd.to_numeric(g[f"relative_advantage_at_{suffix}"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean())
            rec[f"k_at_{suffix}_main"] = float(pd.to_numeric(g[f"k_at_{suffix}_main"], errors="coerce").fillna(0).mean())
            rec[f"k_at_{suffix}_pref"] = float(pd.to_numeric(g[f"k_at_{suffix}_pref"], errors="coerce").fillna(0).mean())
        rec["mrr_main"] = float(pd.to_numeric(g["mrr_main"], errors="coerce").fillna(0).mean())
        rec["mrr_pref"] = float(pd.to_numeric(g["mrr_pref"], errors="coerce").fillna(0).mean())
        rec["delta_mrr"] = float(pd.to_numeric(g["delta_mrr"], errors="coerce").fillna(0).mean())
        rec["relative_advantage_mrr"] = float(pd.to_numeric(g["relative_advantage_mrr"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().mean())
        rec["frontier_delta_fixedK"] = float(pd.to_numeric(g["frontier_delta_fixedK"], errors="coerce").fillna(0).mean())
        rec["frontier_delta_pctK"] = float(pd.to_numeric(g["frontier_delta_pctK"], errors="coerce").fillna(0).mean())

        _, lo, hi = _bootstrap_mean_ci_fast(pd.to_numeric(g["delta_recall_at_100"], errors="coerce").fillna(0), n_boot=n_boot, seed=seed)
        rec["delta_recall_at_100_ci_lo"] = lo
        rec["delta_recall_at_100_ci_hi"] = hi
        _, lo, hi = _bootstrap_mean_ci_fast(pd.to_numeric(g["delta_mrr"], errors="coerce").fillna(0), n_boot=n_boot, seed=seed)
        rec["delta_mrr_ci_lo"] = lo
        rec["delta_mrr_ci_hi"] = hi
        _, lo, hi = _bootstrap_mean_ci_fast(pd.to_numeric(g["frontier_delta_pctK"], errors="coerce").fillna(0), n_boot=n_boot, seed=seed)
        rec["frontier_delta_pctK_ci_lo"] = lo
        rec["frontier_delta_pctK_ci_hi"] = hi
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(["panel_kind", "dimension", "group", "horizon"]).reset_index(drop=True)


def _two_slope_norm(values: np.ndarray) -> TwoSlopeNorm:
    finite = values[np.isfinite(values)]
    vmax = float(np.nanmax(np.abs(finite))) if finite.size else 1.0
    vmax = max(vmax, 1e-9)
    return TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)


def _render_heatmap(
    value_frame: pd.DataFrame,
    annot_frame: pd.DataFrame,
    out_path: Path,
    cbar_label: str,
    fmt: str = "{:+.3f}",
    annot_fmt: str = "{:+.1f}",
    x_label_map: dict[object, str] | None = None,
    y_wrap: int = 24,
    y_label_map: dict[object, str] | None = None,
) -> None:
    if value_frame.empty:
        return
    annot_frame = annot_frame.reindex(index=value_frame.index, columns=value_frame.columns)
    fig, ax = plt.subplots(figsize=(max(6.5, 1.3 * len(value_frame.columns)), max(4.2, 0.55 * len(value_frame.index) + 1.3)))
    values = value_frame.to_numpy(dtype=float)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("#e5e7eb")
    norm = _two_slope_norm(values)
    img = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=cmap, norm=norm)
    ax.set_xticks(np.arange(len(value_frame.columns)))
    if x_label_map is None:
        x_labels = [str(c) for c in value_frame.columns]
    else:
        x_labels = [x_label_map.get(c, str(c)) for c in value_frame.columns]
    ax.set_xticklabels(x_labels, fontsize=10)
    ax.set_yticks(np.arange(len(value_frame.index)))
    y_labels: list[str] = []
    for idx in value_frame.index:
        if y_label_map is not None and idx in y_label_map:
            y_labels.append(y_label_map[idx])
        else:
            y_labels.append(_pretty_label(idx, wrap=y_wrap))
    ax.set_yticklabels(y_labels, fontsize=9)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if np.isfinite(values[i, j]):
                ann = annot_frame.iloc[i, j]
                txt = f"{fmt.format(values[i, j])}\n{annot_fmt.format(float(ann))}"
                rgba = cmap(norm(values[i, j]))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                txt_color = "#f9fafb" if luminance < 0.52 else "#111827"
                ax.text(
                    j,
                    i,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=8.2,
                    fontweight="semibold",
                    color=txt_color,
                )
            else:
                ax.text(j, i, "sparse", ha="center", va="center", fontsize=7, color="#6b7280")
    cbar = fig.colorbar(img, ax=ax, fraction=0.025, pad=0.02)
    cbar.ax.set_ylabel(cbar_label, rotation=270, labelpad=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_pooled_frontier(frontier_summary: pd.DataFrame, pct_k_values: list[float], out_path: Path, horizons: list[int]) -> None:
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "overall")
        & (frontier_summary["group"] == "All")
        & (frontier_summary["horizon"].isin(horizons))
    ].copy()
    if subset.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    fixed_rows: list[dict] = []
    pct_rows: list[dict] = []
    for row in subset.itertuples(index=False):
        for k in FIXED_K_DEFAULTS:
            fixed_rows.append({"horizon": int(row.horizon), "x": int(k), "delta": 100.0 * float(getattr(row, f"relative_advantage_at_{k}", np.nan))})
        for p in pct_k_values:
            suffix = _pct_suffix(p)
            pct_rows.append({"horizon": int(row.horizon), "x": _pct_label_from_suffix(suffix), "delta": 100.0 * float(getattr(row, f"relative_advantage_at_{suffix}", np.nan))})
    fixed_df = pd.DataFrame(fixed_rows)
    pct_df = pd.DataFrame(pct_rows)
    for horizon, g in fixed_df.groupby("horizon"):
        axes[0].plot(g["x"], g["delta"], marker="o", linewidth=2.5, color=HORIZON_COLORS.get(int(horizon), "#0b3c6f"), label=f"h={int(horizon)}")
    pct_order = [_pct_label_from_suffix(_pct_suffix(p)) for p in pct_k_values]
    for horizon, g in pct_df.groupby("horizon"):
        gg = g.set_index("x").reindex(pct_order).reset_index()
        axes[1].plot(np.arange(len(gg)), gg["delta"], marker="o", linewidth=2.5, color=HORIZON_COLORS.get(int(horizon), "#0b3c6f"), label=f"h={int(horizon)}")
    axes[0].axhline(0.0, color="#6b7280", linewidth=1)
    axes[1].axhline(0.0, color="#6b7280", linewidth=1)
    axes[0].set_xlabel("Shortlist size K")
    axes[1].set_xlabel("Share of candidate universe")
    axes[0].set_ylabel("Relative recall advantage over PA (%)")
    axes[1].set_xticks(np.arange(len(pct_order)))
    axes[1].set_xticklabels(pct_order, rotation=0)
    axes[0].legend(frameon=False, ncol=min(3, len(horizons)))
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_topic_heatmap(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    dimension = "first_topic_group" if (frontier_summary["dimension"] == "first_topic_group").any() else "first_subfield_group"
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == dimension)
        & (frontier_summary["horizon"].isin(horizons))
        & (frontier_summary["display_ok_2d"])
    ].copy()
    if subset.empty:
        return
    group_support = (
        subset.groupby("group", as_index=False)
        .agg(total_group_edges=("total_group_edges", "sum"))
        .sort_values("total_group_edges", ascending=False)
    )
    top_groups = _prefer_econ_groups(group_support, top_n=12)
    subset = subset[subset["group"].isin(top_groups)]
    if subset.empty:
        return
    val = subset.pivot(index="group", columns="horizon", values="frontier_delta_pctK")
    ann = 10000.0 * subset.pivot(index="group", columns="horizon", values="delta_recall_at_100")
    _render_heatmap(
        val,
        ann,
        out_path=out_path,
        fmt="{:+.4f}",
        annot_fmt="{:+.1f}bp",
        cbar_label="Frontier delta (percentile-K)",
        x_label_map={3: "3y", 5: "5y", 10: "10y", 15: "15y", 20: "20y"},
        y_wrap=28,
    )


def plot_time_heatmap(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "cutoff_period")
        & (frontier_summary["horizon"].isin(horizons))
        & (frontier_summary["display_ok_2d"])
    ].copy()
    if subset.empty:
        return
    y_label_map = {
        "1990s": "1990--1999",
        "2000s": "2000--2009",
        "2010s": "2010--2015",
    }
    val = 100.0 * subset.pivot(index="group", columns="horizon", values="frontier_delta_pctK")
    ann = 100.0 * subset.pivot(index="group", columns="horizon", values="delta_recall_at_100")
    _render_heatmap(
        val,
        ann,
        out_path=out_path,
        fmt="{:+.1f}%",
        annot_fmt="Top 100 {:+.1f} pp",
        cbar_label="Average recall advantage on broader shortlists (%)",
        x_label_map={3: "3y", 5: "5y", 10: "10y", 15: "15y", 20: "20y"},
        y_wrap=12,
        y_label_map=y_label_map,
    )


def plot_funding_source_interaction(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "first_has_grant x first_source")
        & (frontier_summary["horizon"].isin(horizons))
    ].copy()
    if subset.empty:
        return
    wanted = ["Funded | core", "Unfunded | core", "Funded | adjacent", "Unfunded | adjacent"]
    subset = subset[subset["group"].isin(wanted)].copy()
    if subset.empty:
        return
    subset["group"] = subset["group"].map(lambda x: " | ".join(_clean_group_label(p) for p in str(x).split(" | ")))
    y_label_map = {
        "Funded | Core": "Funded\nCore journals",
        "Unfunded | Core": "Unfunded\nCore journals",
        "Funded | Adjacent": "Funded\nAdjacent journals",
        "Unfunded | Adjacent": "Unfunded\nAdjacent journals",
    }
    val = 100.0 * subset.pivot(index="group", columns="horizon", values="frontier_delta_pctK")
    ann = 100.0 * subset.pivot(index="group", columns="horizon", values="delta_recall_at_100")
    _render_heatmap(
        val,
        ann,
        out_path=out_path,
        fmt="{:+.1f}%",
        annot_fmt="Top 100 {:+.1f} pp",
        cbar_label="Average recall advantage on broader shortlists (%)",
        x_label_map={3: "3y", 5: "5y", 10: "10y", 15: "15y", 20: "20y"},
        y_wrap=18,
        y_label_map=y_label_map,
    )


def _plot_forest_block(block: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    if block.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    order = (
        block.groupby("group", as_index=False)
        .agg(metric=("frontier_delta_pctK", "mean"), support=("total_group_edges", "sum"))
        .sort_values(["metric", "support"], ascending=[True, False])["group"]
        .tolist()
    )
    y_map = {group: idx for idx, group in enumerate(order)}
    offsets = np.linspace(-0.22, 0.22, num=len(horizons))
    for off, horizon in zip(offsets, horizons):
        g = block[block["horizon"] == horizon]
        y = np.array([y_map[val] for val in g["group"]], dtype=float) + off
        x = 100.0 * g["frontier_delta_pctK"].to_numpy(dtype=float)
        lo = x - 100.0 * g["frontier_delta_pctK_ci_lo"].to_numpy(dtype=float)
        hi = 100.0 * g["frontier_delta_pctK_ci_hi"].to_numpy(dtype=float) - x
        ax.errorbar(x, y, xerr=np.vstack([lo, hi]), fmt="o", capsize=2.5, label=f"h={int(horizon)}", color=HORIZON_COLORS.get(int(horizon), "#0b3c6f"))
    ax.axvline(0.0, color="#9ca3af", linewidth=1)
    ax.set_yticks(np.arange(len(order)))
    ax.set_yticklabels([_pretty_label(label, wrap=24) for label in order], fontsize=9)
    ax.set_xlabel("Average recall advantage on broader shortlists (%)")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_method_forest(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    block = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "first_method_group")
        & (frontier_summary["horizon"].isin(horizons))
        & (frontier_summary["display_ok_1d"])
        & (~frontier_summary["group"].isin(["Mixed"]))
    ].copy()
    _plot_forest_block(block, out_path=out_path, horizons=horizons)


def plot_theory_forest_appendix(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    block = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "first_theory_empirical")
        & (frontier_summary["horizon"].isin(horizons))
        & (frontier_summary["display_ok_1d"])
    ].copy()
    _plot_forest_block(block, out_path=out_path, horizons=horizons)


def plot_subfield_time_interaction(frontier_summary: pd.DataFrame, out_path: Path, horizons: list[int]) -> None:
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "first_subfield_group x cutoff_period")
        & (frontier_summary["horizon"].isin(horizons))
        & (frontier_summary["display_ok_2d"])
    ].copy()
    if subset.empty:
        return
    subset["subfield"] = subset["group_left"].astype(str)
    subset["period"] = subset["group_right"].astype(str)
    top_subfields = (
        subset.groupby("subfield", as_index=False)
        .agg(total_group_edges=("total_group_edges", "sum"))
        .sort_values("total_group_edges", ascending=False)
        .head(10)["subfield"]
        .tolist()
    )
    subset = subset[subset["subfield"].isin(top_subfields)].copy()
    fig, axes = plt.subplots(1, len(horizons), figsize=(6.5 * len(horizons), 6), sharey=True)
    if len(horizons) == 1:
        axes = [axes]
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("#e5e7eb")
    for ax, horizon in zip(axes, horizons):
        block = subset[subset["horizon"] == horizon]
        heat = block.pivot(index="subfield", columns="period", values="frontier_delta_pctK")
        values = heat.to_numpy(dtype=float)
        norm = _two_slope_norm(values)
        img = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=cmap, norm=norm)
        ax.set_title("")
        ax.set_xticks(np.arange(len(heat.columns)))
        ax.set_xticklabels(heat.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(np.arange(len(heat.index)))
        ax.set_yticklabels([_pretty_label(v, wrap=24) for v in heat.index], fontsize=9)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                if np.isfinite(values[i, j]):
                    ax.text(j, i, f"{values[i, j]:+.3f}", ha="center", va="center", fontsize=7)
        fig.colorbar(img, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_kind_split_frontier(frontier_summary: pd.DataFrame, pct_k_values: list[float], out_path: Path, horizons: list[int]) -> None:
    subset = frontier_summary[
        frontier_summary["panel_kind"].isin(["directed_causal", "undirected_noncausal"])
        & (frontier_summary["dimension"] == "overall")
        & (frontier_summary["group"] == "All")
        & (frontier_summary["horizon"].isin(horizons))
    ].copy()
    if subset.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    colors = {"directed_causal": "#0b3c6f", "undirected_noncausal": "#5b8bb2"}
    for kind, block in subset.groupby("panel_kind"):
        for horizon in sorted(block["horizon"].unique()):
            g = block[block["horizon"] == horizon].copy()
            label = f"{kind.replace('_', ' ')} h={int(horizon)}"
            axes[0].plot(FIXED_K_DEFAULTS, [float(g.iloc[0][f"delta_recall_at_{k}"]) for k in FIXED_K_DEFAULTS], marker="o", linewidth=1.8, color=colors.get(kind, "#111827"), alpha=0.4 + 0.15 * horizons.index(horizon), label=label)
            pct_labels = [_pct_label_from_suffix(_pct_suffix(p)) for p in pct_k_values]
            axes[1].plot(np.arange(len(pct_labels)), [float(g.iloc[0][f"delta_recall_at_{_pct_suffix(p)}"]) for p in pct_k_values], marker="o", linewidth=1.8, color=colors.get(kind, "#111827"), alpha=0.4 + 0.15 * horizons.index(horizon), label=label)
    axes[0].axhline(0.0, color="#6b7280", linewidth=1)
    axes[1].axhline(0.0, color="#6b7280", linewidth=1)
    axes[1].set_xticks(np.arange(len(pct_k_values)))
    axes[1].set_xticklabels([_pct_label_from_suffix(_pct_suffix(p)) for p in pct_k_values])
    axes[0].set_ylabel("Main minus preferential attachment")
    axes[0].legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _validate_monotonicity(panel_df: pd.DataFrame, fixed_k_values: list[int], pct_k_values: list[float]) -> dict[str, int]:
    fixed_errors = 0
    pct_errors = 0
    pct_suffixes = [_pct_suffix(p) for p in pct_k_values]
    for row in panel_df.itertuples(index=False):
        fixed = [float(getattr(row, f"recall_at_{k}")) for k in fixed_k_values]
        pct = [float(getattr(row, f"recall_at_{suffix}")) for suffix in pct_suffixes]
        if any(fixed[i] > fixed[i + 1] + 1e-12 for i in range(len(fixed) - 1)):
            fixed_errors += 1
        if any(pct[i] > pct[i + 1] + 1e-12 for i in range(len(pct) - 1)):
            pct_errors += 1
    return {"fixed_k_monotonicity_failures": int(fixed_errors), "pct_k_monotonicity_failures": int(pct_errors)}


def write_takeaways(frontier_summary: pd.DataFrame, out_path: Path, main_horizons: list[int]) -> None:
    lines = ["# Heterogeneity Atlas Takeaways", ""]
    if frontier_summary.empty:
        lines.append("No heterogeneity summary available.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    pooled = frontier_summary[frontier_summary["panel_kind"] == "pooled"].copy()
    if pooled.empty:
        lines.append("No pooled summary available.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    main = pooled[pooled["horizon"].isin(main_horizons)].copy()
    wins = main[(main["frontier_delta_pctK_ci_lo"] > 0) & (main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=False).head(6)
    losses = main[(main["frontier_delta_pctK_ci_hi"] < 0) & (main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=True).head(6)
    flips = main[(main["delta_recall_at_100"] < 0) & (main["frontier_delta_pctK"] > 0) & (main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=False).head(6)
    lines.append("## Where the main model wins or nearly wins")
    for row in wins.itertuples(index=False):
        lines.append(f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}, delta Recall@100={float(row.delta_recall_at_100):+.4f}")
    lines.append("")
    lines.append("## Where preferential attachment remains strongest")
    for row in losses.itertuples(index=False):
        lines.append(f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}, delta Recall@100={float(row.delta_recall_at_100):+.4f}")
    lines.append("")
    lines.append("## Where percentile-K softens the headline")
    for row in flips.itertuples(index=False):
        lines.append(f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f} while delta Recall@100 remains {float(row.delta_recall_at_100):+.4f}")
    lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_memo(
    frontier_summary: pd.DataFrame,
    out_path: Path,
    main_horizons: list[int],
    appendix_horizons: list[int],
) -> None:
    lines = ["# Heterogeneity Atlas Memo", ""]
    if frontier_summary.empty:
        lines.append("No heterogeneity outputs were generated.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    pooled = frontier_summary[frontier_summary["panel_kind"] == "pooled"].copy()
    main = pooled[pooled["horizon"].isin(main_horizons)].copy()
    appendix = pooled[pooled["horizon"].isin(appendix_horizons)].copy()
    if main.empty:
        lines.append("No pooled main-horizon results were generated.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    best = main[(main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=False).head(8)
    worst = main[(main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=True).head(8)
    percentile_flips = main[(main["frontier_delta_pctK"] > 0) & (main["delta_recall_at_100"] < 0) & (main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=False).head(8)
    robust_wins = main[(main["panel_kind"] == "pooled") & (main["frontier_delta_pctK_ci_lo"] > 0) & (main["display_ok_1d"])].sort_values("frontier_delta_pctK", ascending=False).head(8)
    lines.append("## Where the main model beats or ties preferential attachment")
    for row in best.itertuples(index=False):
        lines.append(
            f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f} "
            f"[{float(row.frontier_delta_pctK_ci_lo):+.4f}, {float(row.frontier_delta_pctK_ci_hi):+.4f}], "
            f"delta Recall@100={float(row.delta_recall_at_100):+.4f}, delta hits@100={float(row.delta_hits_at_100):+.1f}."
        )
    lines.append("")
    lines.append("## Where preferential attachment remains strongest")
    for row in worst.itertuples(index=False):
        lines.append(
            f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}, "
            f"delta Recall@100={float(row.delta_recall_at_100):+.4f}, delta MRR={float(row.delta_mrr):+.6f}."
        )
    lines.append("")
    lines.append("## Where percentile-based shortlists change the story")
    for row in percentile_flips.itertuples(index=False):
        lines.append(
            f"- {row.dimension} / {row.group}, h={int(row.horizon)}: percentile frontier delta={float(row.frontier_delta_pctK):+.4f} "
            f"even though Recall@100 remains {float(row.delta_recall_at_100):+.4f}."
        )
    lines.append("")
    lines.append("## Long-horizon extensions")
    if appendix.empty:
        lines.append("- No long-horizon rows survived the support thresholds.")
    else:
        for row in appendix[appendix["display_ok_1d"]].sort_values("frontier_delta_pctK", ascending=False).head(6).itertuples(index=False):
            lines.append(
                f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f}, "
                f"delta Recall@100={float(row.delta_recall_at_100):+.4f}."
            )
    lines.append("")
    lines.append("## Patterns that survive kind-split robustness")
    directed = frontier_summary[
        (frontier_summary["panel_kind"] == "directed_causal")
        & (frontier_summary["horizon"].isin(main_horizons))
        & (frontier_summary["display_ok_1d"])
    ][["dimension", "group", "horizon", "frontier_delta_pctK"]].rename(columns={"frontier_delta_pctK": "directed_frontier"})
    undirected = frontier_summary[
        (frontier_summary["panel_kind"] == "undirected_noncausal")
        & (frontier_summary["horizon"].isin(main_horizons))
        & (frontier_summary["display_ok_1d"])
    ][["dimension", "group", "horizon", "frontier_delta_pctK"]].rename(columns={"frontier_delta_pctK": "undirected_frontier"})
    overlap = directed.merge(undirected, on=["dimension", "group", "horizon"], how="inner")
    overlap["same_sign"] = np.sign(overlap["directed_frontier"]).eq(np.sign(overlap["undirected_frontier"]))
    overlap = overlap[overlap["same_sign"]].copy()
    if overlap.empty:
        lines.append("- No well-supported subgroup shows the same sign in both candidate kinds.")
    else:
        for row in overlap.sort_values("directed_frontier", ascending=False).head(8).itertuples(index=False):
            lines.append(
                f"- {row.dimension} / {row.group}, h={int(row.horizon)}: directed={float(row.directed_frontier):+.4f}, "
                f"undirected={float(row.undirected_frontier):+.4f}."
            )
    lines.append("")
    if not robust_wins.empty:
        lines.append("## Strongest pooled wins with positive bootstrap lower bounds")
        for row in robust_wins.itertuples(index=False):
            lines.append(
                f"- {row.dimension} / {row.group}, h={int(row.horizon)}: frontier delta={float(row.frontier_delta_pctK):+.4f} "
                f"with CI [{float(row.frontier_delta_pctK_ci_lo):+.4f}, {float(row.frontier_delta_pctK_ci_hi):+.4f}]."
            )
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def maybe_write_top_funder_appendix(frontier_summary: pd.DataFrame, out_dir: Path, main_horizons: list[int]) -> None:
    subset = frontier_summary[
        (frontier_summary["panel_kind"] == "pooled")
        & (frontier_summary["dimension"] == "first_funder_group")
        & (frontier_summary["total_group_edges"] >= 500)
        & (frontier_summary["display_ok_1d"])
    ].copy()
    if subset.empty:
        return
    subset.to_csv(out_dir / "top_funder_summary.csv", index=False)
    main = subset[subset["horizon"].isin(main_horizons)].copy()
    support = (
        main.groupby("group", as_index=False)
        .agg(
            min_edges=("total_group_edges", "min"),
            min_cutoffs=("n_cutoffs", "min"),
            mean_frontier=("frontier_delta_pctK", "mean"),
        )
    )
    support = support[(support["min_edges"] >= 800) & (support["min_cutoffs"] >= 3)]
    support = support[~support["group"].isin(["Unknown", "Other/Unknown"])]
    if support.empty:
        return
    top = support.sort_values("mean_frontier", ascending=False).head(4)["group"].tolist()
    bottom = support.sort_values("mean_frontier", ascending=True).head(4)["group"].tolist()
    selected = top + [g for g in bottom if g not in top]
    picked = main[main["group"].isin(selected)].copy()
    picked.to_csv(out_dir / "top_funder_extremes.csv", index=False)
    val = picked.pivot(index="group", columns="horizon", values="frontier_delta_pctK")
    ann = 10000.0 * picked.pivot(index="group", columns="horizon", values="delta_recall_at_100")
    order = support.set_index("group").loc[selected].sort_values("mean_frontier", ascending=False).index.tolist()
    val = val.reindex(order)
    ann = ann.reindex(order)
    _render_heatmap(
        val,
        ann,
        out_path=out_dir / "figures" / "top_funder_heatmap_appendix.png",
        fmt="{:+.4f}",
        annot_fmt="{:+.1f}bp",
        cbar_label="Frontier delta (percentile-K)",
        x_label_map={5: "5y", 10: "10y", 15: "15y", 20: "20y"},
        y_wrap=22,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heterogeneity atlas for the research-allocation benchmark.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--paper_meta", required=True, dest="paper_meta_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--cutoff-start", type=int, default=1980)
    parser.add_argument("--cutoff-end", type=int, default=2020)
    parser.add_argument("--cutoff-step", type=int, default=5)
    parser.add_argument("--horizons", default="5,10,15,20")
    parser.add_argument("--main-horizons", default="5,10,15")
    parser.add_argument("--appendix-horizons", default="20")
    parser.add_argument("--fixed-k-values", default="10,50,100,500,1000")
    parser.add_argument("--pct-k-values", default="0.0001,0.0005,0.001,0.005")
    parser.add_argument(
        "--dimensions",
        default=",".join(PRIMARY_DIMS + INTERACTION_DIMS + OPTIONAL_DIMS),
        help="Comma-separated heterogeneity dimensions to compute.",
    )
    parser.add_argument(
        "--candidate-kinds",
        nargs="+",
        default=["directed_causal", "undirected_noncausal"],
        choices=["directed_causal", "undirected_noncausal"],
    )
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    out_dir = ensure_output_dir(args.out_dir)
    fig_dir = ensure_output_dir(Path(out_dir) / "figures")

    corpus_df = load_corpus(args.corpus_path)
    paper_meta_df = pd.read_parquet(args.paper_meta_path)
    config = load_config(args.config_path)
    horizons = [int(x.strip()) for x in str(args.horizons).split(",") if x.strip()]
    main_horizons = [int(x.strip()) for x in str(args.main_horizons).split(",") if x.strip()]
    appendix_horizons = [int(x.strip()) for x in str(args.appendix_horizons).split(",") if x.strip()]
    fixed_k_values = [int(x.strip()) for x in str(args.fixed_k_values).split(",") if x.strip()]
    pct_k_values = [float(x.strip()) for x in str(args.pct_k_values).split(",") if x.strip()]
    dimensions = [x.strip() for x in str(args.dimensions).split(",") if x.strip()]
    max_observed_year = int(pd.to_numeric(corpus_df["year"], errors="coerce").max())
    years = _eligible_cutoffs(
        start_year=int(args.cutoff_start),
        end_year=int(args.cutoff_end),
        step=int(args.cutoff_step),
        max_observed_year=max_observed_year,
        horizons=horizons,
    )

    kind_panels: list[pd.DataFrame] = []
    edge_meta_frames: list[pd.DataFrame] = []
    for candidate_kind in args.candidate_kinds:
        cfg = CandidateBuildConfig(
            tau=int(config.get("features", {}).get("tau", 2)),
            max_path_len=int(config.get("features", {}).get("max_path_len", 2)),
            max_neighbors_per_mediator=int(config.get("features", {}).get("max_neighbors_per_mediator", 120)),
            alpha=float(config.get("scoring", {}).get("alpha", 0.5)),
            beta=float(config.get("scoring", {}).get("beta", 0.2)),
            gamma=float(config.get("scoring", {}).get("gamma", 0.3)),
            delta=float(config.get("scoring", {}).get("delta", 0.2)),
            causal_only=bool(config.get("filters", {}).get("causal_only", False)),
            min_stability=config.get("filters", {}).get("min_stability"),
            candidate_kind=candidate_kind,
        )
        edge_meta = build_first_edge_metadata(corpus_df, paper_meta_df, candidate_kind=candidate_kind)
        edge_meta["candidate_kind"] = candidate_kind
        edge_meta_frames.append(edge_meta)
        panel = compute_subgroup_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            candidate_kind=candidate_kind,
            years=years,
            horizons=horizons,
            edge_meta_df=edge_meta,
            fixed_k_values=fixed_k_values,
            pct_k_values=pct_k_values,
            dimensions=dimensions,
        )
        kind_panels.append(panel)

    kind_split_panel = pd.concat(kind_panels, ignore_index=True) if kind_panels else pd.DataFrame()
    pooled_panel = build_pooled_panel(kind_split_panel)
    all_panel = pd.concat([kind_split_panel, pooled_panel], ignore_index=True) if not pooled_panel.empty else kind_split_panel.copy()
    edge_meta_all = pd.concat(edge_meta_frames, ignore_index=True) if edge_meta_frames else pd.DataFrame()

    model_summary = build_model_summary(all_panel)
    compare_panel = build_compare_panel(all_panel, fixed_k_values=fixed_k_values, pct_k_values=pct_k_values)
    frontier_summary = build_frontier_summary(compare_panel, fixed_k_values=fixed_k_values, pct_k_values=pct_k_values, n_boot=int(args.n_boot), seed=int(args.seed))
    interaction_summary = frontier_summary[frontier_summary["dimension"].isin(INTERACTION_DIMS)].copy()

    monotonicity = _validate_monotonicity(all_panel, fixed_k_values=fixed_k_values, pct_k_values=pct_k_values)
    qc_df = pd.DataFrame([{"cutoff_year_min": min(years) if years else np.nan, "cutoff_year_max": max(years) if years else np.nan, **monotonicity}])

    kind_split_panel.to_parquet(Path(out_dir) / "kind_split_panel.parquet", index=False)
    kind_split_panel.to_csv(Path(out_dir) / "kind_split_panel.csv", index=False)
    pooled_panel.to_parquet(Path(out_dir) / "pooled_panel.parquet", index=False)
    pooled_panel.to_csv(Path(out_dir) / "pooled_panel.csv", index=False)
    model_summary.to_parquet(Path(out_dir) / "subgroup_summary.parquet", index=False)
    model_summary.to_csv(Path(out_dir) / "subgroup_summary.csv", index=False)
    interaction_summary.to_parquet(Path(out_dir) / "interaction_summary.parquet", index=False)
    interaction_summary.to_csv(Path(out_dir) / "interaction_summary.csv", index=False)
    frontier_summary.to_parquet(Path(out_dir) / "frontier_summary.parquet", index=False)
    frontier_summary.to_csv(Path(out_dir) / "frontier_summary.csv", index=False)
    compare_panel.to_parquet(Path(out_dir) / "compare_panel.parquet", index=False)
    compare_panel.to_csv(Path(out_dir) / "compare_panel.csv", index=False)
    edge_meta_all.to_parquet(Path(out_dir) / "first_edge_metadata.parquet", index=False)
    edge_meta_all.to_csv(Path(out_dir) / "first_edge_metadata.csv", index=False)
    qc_df.to_csv(Path(out_dir) / "qc_checks.csv", index=False)

    plot_pooled_frontier(frontier_summary, pct_k_values=pct_k_values, out_path=fig_dir / "pooled_frontier_main.png", horizons=main_horizons)
    plot_pooled_frontier(frontier_summary, pct_k_values=pct_k_values, out_path=fig_dir / "pooled_frontier_appendix.png", horizons=appendix_horizons)
    plot_topic_heatmap(frontier_summary, out_path=fig_dir / "subfield_heatmap_main.png", horizons=main_horizons)
    plot_time_heatmap(frontier_summary, out_path=fig_dir / "time_period_heatmap_main.png", horizons=main_horizons)
    plot_funding_source_interaction(frontier_summary, out_path=fig_dir / "funding_source_interaction_main.png", horizons=main_horizons)
    plot_method_forest(frontier_summary, out_path=fig_dir / "method_theory_forest_main.png", horizons=main_horizons)
    plot_theory_forest_appendix(frontier_summary, out_path=fig_dir / "theory_empirical_forest_appendix.png", horizons=main_horizons)
    plot_subfield_time_interaction(frontier_summary, out_path=fig_dir / "subfield_time_interaction_main.png", horizons=[5, 10])
    plot_kind_split_frontier(frontier_summary, pct_k_values=pct_k_values, out_path=fig_dir / "kind_split_frontier_appendix.png", horizons=horizons)
    maybe_write_top_funder_appendix(frontier_summary, out_dir=Path(out_dir), main_horizons=main_horizons)

    write_takeaways(frontier_summary, Path(out_dir) / "takeaways.md", main_horizons=main_horizons)
    write_memo(
        frontier_summary,
        Path(out_dir) / "heterogeneity_memo.md",
        main_horizons=main_horizons,
        appendix_horizons=appendix_horizons,
    )

    print(f"Wrote: {Path(out_dir) / 'pooled_panel.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'kind_split_panel.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'subgroup_summary.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'interaction_summary.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'frontier_summary.parquet'}")
    print(f"Wrote: {Path(out_dir) / 'takeaways.md'}")
    print(f"Wrote: {Path(out_dir) / 'heterogeneity_memo.md'}")


if __name__ == "__main__":
    main()
