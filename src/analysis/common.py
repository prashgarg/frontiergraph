from __future__ import annotations

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


def first_appearance_map(corpus_df: pd.DataFrame) -> dict[tuple[str, str], int]:
    g = corpus_df.groupby(["src_code", "dst_code"], as_index=False).agg(first_year=("year", "min"))
    return {(str(r.src_code), str(r.dst_code)): int(r.first_year) for r in g.itertuples(index=False)}


def future_edges_for(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {
        edge
        for edge, y in first_year_map.items()
        if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)
    }


def check_no_leakage(
    corpus_df: pd.DataFrame,
    cutoff_t: int,
    horizon_h: int,
    first_year_map: dict[tuple[str, str], int] | None = None,
) -> bool:
    fmap = first_year_map if first_year_map is not None else first_appearance_map(corpus_df)
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
    boundary_bonus: float = 0.0
    boundary_quota: float = 0.0
    boundary_quota_max_rank: int = 1000
    causal_only: bool = False
    min_stability: float | None = None


def build_candidate_table(
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: CandidateBuildConfig,
) -> pd.DataFrame:
    if train_df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])
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
