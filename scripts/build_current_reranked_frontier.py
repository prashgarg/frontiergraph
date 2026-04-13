from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import build_candidate_table, ensure_output_dir
from src.analysis.learned_reranker import (
    _feature_list,
    build_candidate_feature_panel,
    enrich_candidate_features,
    fit_glm_logit_reranker,
    fit_pairwise_logit_reranker,
    score_with_reranker,
)
from src.analysis.ranking_utils import candidate_cfg_from_config
from src.utils import load_config, load_corpus


METHOD_PATTERNS = [
    r"\bregression\b",
    r"\bmethod\b",
    r"\bquantile\b",
    r"\bmoments\b",
    r"\bestimator\b",
    r"\bestimators\b",
    r"\bestimation\b",
    r"\btest statistic\b",
    r"\bwald test\b",
    r"\bmoran'?s i\b",
    r"\basymptotic\b",
]

METADATA_PATTERNS = [
    r"\bplace of residence\b",
    r"\bregion of residence\b",
    r"\busual care\b",
    r"\bobserved data\b",
    r"\bparameter values\b",
    r"\bresidence\b",
]

METHOD_REGEX = [re.compile(p, flags=re.IGNORECASE) for p in METHOD_PATTERNS]
METADATA_REGEX = [re.compile(p, flags=re.IGNORECASE) for p in METADATA_PATTERNS]
CODE_RE = re.compile(r"^FG3C\d+$", flags=re.IGNORECASE)

GENERIC_ENDPOINT_LABELS = {
    "policy",
    "distance",
    "economic growth",
    "innovation",
    "employment",
    "wages",
    "health",
    "income",
    "consumption",
    "productivity",
    "investment",
}
GENERIC_ENDPOINT_PATTERNS = [
    r"\bpolicy variables\b",
    r"\bmodel parameters\b",
    r"\bparameters\b",
    r"\bmodels\b",
]

SURFACE_FLAG_WEIGHTS = {
    "method_like": 1,
    "metadata_like": 1,
    "generic_like": 1,
    "unresolved_code": 2,
}
GENERIC_REGEX = [re.compile(p, flags=re.IGNORECASE) for p in GENERIC_ENDPOINT_PATTERNS]

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


@dataclass(frozen=True)
class RegularizerConfig:
    variant: str
    sink_start_pct: float
    sink_lambda: float
    diversify_window: int
    repeat_log_lambda: float
    repeat_linear_lambda: float


@dataclass(frozen=True)
class SurfaceLayerConfig:
    top_window: int = 200
    broad_endpoint_start_pct: float = 0.85
    broad_endpoint_lambda: float = 6.0
    resolution_floor: float = 0.08
    resolution_lambda: float = 4.0
    generic_endpoint_lambda: float = 2.0
    mediator_specificity_floor: float = 0.45
    mediator_specificity_lambda: float = 2.5
    textbook_like_start_pct: float = 0.85
    textbook_like_lambda: float = 4.0
    source_repeat_lambda: float = 2.0
    target_repeat_lambda: float = 2.0
    family_repeat_lambda: float = 6.0
    theme_repeat_lambda: float = 2.0
    theme_pair_repeat_lambda: float = 3.0
    broad_repeat_start_pct: float = 0.85
    broad_repeat_lambda: float = 2.0


def _concept_metadata_map(corpus_df: pd.DataFrame, fallback_csv: str | Path = "site/public/data/v2/central_concepts.csv") -> dict[str, dict[str, str]]:
    meta: dict[str, dict[str, str]] = {}
    src = corpus_df[["src_code", "src_label"]].drop_duplicates()
    dst = corpus_df[["dst_code", "dst_label"]].drop_duplicates()
    for row in src.itertuples(index=False):
        code = str(row.src_code)
        meta.setdefault(code, {})
        meta[code].setdefault("label", str(row.src_label))
    for row in dst.itertuples(index=False):
        code = str(row.dst_code)
        meta.setdefault(code, {})
        meta[code].setdefault("label", str(row.dst_label))

    fallback_path = Path(fallback_csv)
    if fallback_path.exists():
        fallback_df = pd.read_csv(
            fallback_path,
            usecols=["concept_id", "plain_label", "bucket_hint", "alternate_display_labels", "top_units"],
        )
        for row in fallback_df.drop_duplicates("concept_id").itertuples(index=False):
            cid = str(row.concept_id)
            meta.setdefault(cid, {})
            label = str(row.plain_label)
            if "label" not in meta[cid] or not meta[cid]["label"] or meta[cid]["label"] == cid:
                meta[cid]["label"] = label
            meta[cid]["bucket_hint"] = "" if pd.isna(row.bucket_hint) else str(row.bucket_hint)
            meta[cid]["alternate_display_labels"] = "" if pd.isna(row.alternate_display_labels) else str(row.alternate_display_labels)
            meta[cid]["top_units"] = "" if pd.isna(row.top_units) else str(row.top_units)
    return meta


def _code_to_label_map(corpus_df: pd.DataFrame, fallback_csv: str | Path = "site/public/data/v2/central_concepts.csv") -> dict[str, str]:
    meta = _concept_metadata_map(corpus_df=corpus_df, fallback_csv=fallback_csv)
    return {code: payload.get("label", code) for code, payload in meta.items()}


def _endpoint_flag_reasons(code: str, concept_meta: dict[str, dict[str, str]]) -> list[str]:
    payload = concept_meta.get(str(code), {})
    label = str(payload.get("label", code) or "").strip()
    text = " | ".join(
        [
            label,
            payload.get("bucket_hint", ""),
            payload.get("alternate_display_labels", ""),
            payload.get("top_units", ""),
        ]
    ).lower()
    reasons: list[str] = []
    if CODE_RE.match(label):
        reasons.append("unresolved_code")
    if any(pattern.search(text) for pattern in METHOD_REGEX):
        reasons.append("method_like")
    if any(pattern.search(text) for pattern in METADATA_REGEX):
        reasons.append("metadata_like")
    if label.lower() in GENERIC_ENDPOINT_LABELS or any(pattern.search(text) for pattern in GENERIC_REGEX):
        reasons.append("generic_like")
    return reasons


def _mediator_flag_reasons(code: str, concept_meta: dict[str, dict[str, str]]) -> list[str]:
    if not str(code or "").strip():
        return []
    payload = concept_meta.get(str(code), {})
    label = str(payload.get("label", code) or "").strip()
    text = " | ".join(
        [
            label,
            payload.get("bucket_hint", ""),
            payload.get("alternate_display_labels", ""),
            payload.get("top_units", ""),
        ]
    ).lower()
    reasons: list[str] = []
    if CODE_RE.match(label):
        reasons.append("unresolved_code")
    if any(pattern.search(text) for pattern in METHOD_REGEX):
        reasons.append("method_like")
    if label.lower() in GENERIC_ENDPOINT_LABELS or any(pattern.search(text) for pattern in GENERIC_REGEX):
        reasons.append("generic_like")
    return reasons


def _flag_penalty(value: str) -> int:
    if not value:
        return 0
    flags = [part for part in str(value).split("|") if part]
    return int(sum(SURFACE_FLAG_WEIGHTS.get(flag, 0) for flag in flags))


def _load_sink_regularizer_configs(path: str | Path | None) -> dict[int, RegularizerConfig]:
    if not path:
        return {}
    cfg_path = Path(path)
    if not cfg_path.exists():
        return {}
    df = pd.read_csv(cfg_path)
    required = {
        "horizon",
        "sink_start_pct",
        "sink_lambda",
        "diversify_window",
        "repeat_log_lambda",
        "repeat_linear_lambda",
    }
    if not required.issubset(df.columns):
        return {}
    out: dict[int, RegularizerConfig] = {}
    for row in df.itertuples(index=False):
        out[int(row.horizon)] = RegularizerConfig(
            variant=str(getattr(row, "variant", "sink_plus_diversification") or "sink_plus_diversification"),
            sink_start_pct=float(row.sink_start_pct),
            sink_lambda=float(row.sink_lambda),
            diversify_window=int(row.diversify_window),
            repeat_log_lambda=float(row.repeat_log_lambda),
            repeat_linear_lambda=float(row.repeat_linear_lambda),
        )
    return out


def _clean_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"[.;:,]+\s*$", "", text).strip()
    return text


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


def _apply_diversification_only(
    df: pd.DataFrame,
    cfg: RegularizerConfig,
    rank_col: str = "reranker_rank",
) -> pd.DataFrame:
    ordered = df.sort_values([rank_col, "u", "v"], ascending=[True, True, True]).reset_index(drop=True).copy()
    ordered["source_family"] = ordered["u_label"].map(_normalize_family_label)
    ordered["target_family"] = ordered["v_label"].map(_normalize_family_label)
    ordered["semantic_family_key"] = ordered["source_family"].astype(str) + "__" + ordered["target_family"].astype(str)
    ordered["source_theme"] = ordered["u_label"].map(_theme_for_label)
    ordered["target_theme"] = ordered["v_label"].map(_theme_for_label)
    ordered["theme_pair_key"] = ordered["source_theme"].astype(str) + "__" + ordered["target_theme"].astype(str)

    top_window = ordered.head(int(cfg.diversify_window)).copy()
    tail = ordered.iloc[int(cfg.diversify_window) :].copy()
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
        work["diversification_penalty"] = work["theme_penalty"].astype(float) + work["redundancy_penalty"].astype(float)
        work["regularized_priority"] = -(work[rank_col].astype(float) + work["diversification_penalty"].astype(float))
        pick = work.sort_values(["regularized_priority", rank_col, "u", "v"], ascending=[False, True, True, True]).iloc[0]
        selected_rows.append(pick)
        source_counts[str(pick["source_family"])] += 1
        target_counts[str(pick["target_family"])] += 1
        family_counts[str(pick["semantic_family_key"])] += 1
        source_theme_counts[str(pick["source_theme"])] += 1
        target_theme_counts[str(pick["target_theme"])] += 1
        theme_pair_counts[str(pick["theme_pair_key"])] += 1
        remaining = remaining[~(remaining["u"].astype(str).eq(str(pick["u"])) & remaining["v"].astype(str).eq(str(pick["v"])))].copy()

    selected_df = pd.DataFrame(selected_rows).reset_index(drop=True)
    if tail.empty:
        out = selected_df.copy()
    else:
        tail = tail.copy()
        tail["diversification_penalty"] = 0.0
        tail["regularized_priority"] = -(tail[rank_col].astype(float))
        out = pd.concat([selected_df, tail], ignore_index=True)
    out["sink_score"] = 0.0
    out["sink_score_pct"] = 0.0
    out["sink_excess"] = 0.0
    out["sink_penalty"] = 0.0
    out["base_priority"] = -(out[rank_col].astype(float))
    out["regularized_rank"] = out.index + 1
    return out


def _compute_sink_targets(df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "target_direct_in_degree",
        "target_support_in_degree",
        "target_incident_count",
        "target_evidence_diversity",
        "target_venue_diversity",
        "target_source_diversity",
    ]
    targets = df[["v", "v_label"] + metric_cols].drop_duplicates("v").copy()
    for col in metric_cols:
        targets[f"{col}_pct"] = targets[col].rank(method="average", pct=True)
    targets["sink_score"] = targets[[f"{c}_pct" for c in metric_cols]].mean(axis=1)
    targets["sink_score_pct"] = targets["sink_score"].rank(method="average", pct=True)
    return targets[["v", "sink_score", "sink_score_pct"]]


def _apply_sink_regularizer(
    df: pd.DataFrame,
    cfg: RegularizerConfig,
    rank_col: str = "reranker_rank",
    score_col: str = "reranker_score",
) -> pd.DataFrame:
    if str(cfg.variant) == "diversification_only":
        return _apply_diversification_only(df, cfg, rank_col=rank_col)
    g = df.copy().reset_index(drop=True)
    n = len(g)
    g["reranker_pct"] = 1.0 - (g[rank_col].astype(float) - 1.0) / max(n - 1, 1)
    if cfg.sink_lambda > 0:
        width = max(1.0 - float(cfg.sink_start_pct), 1e-9)
        g["sink_excess"] = ((g["sink_score_pct"].astype(float) - cfg.sink_start_pct) / width).clip(lower=0.0, upper=1.0)
        g["sink_penalty"] = cfg.sink_lambda * g["sink_excess"]
    else:
        g["sink_excess"] = 0.0
        g["sink_penalty"] = 0.0
    g["base_priority"] = g["reranker_pct"] - g["sink_penalty"]
    g = g.sort_values(["base_priority", score_col], ascending=[False, False]).reset_index(drop=True)

    if cfg.repeat_log_lambda <= 0 and cfg.repeat_linear_lambda <= 0:
        out = g.copy()
        out["diversification_penalty"] = 0.0
        out["regularized_priority"] = out["base_priority"]
        out["regularized_rank"] = out.index + 1
        return out

    top = g.head(int(cfg.diversify_window)).copy()
    rest = g.iloc[int(cfg.diversify_window):].copy()
    selected_rows: list[pd.Series] = []
    target_counts: dict[str, int] = {}

    while not top.empty:
        penalties = top["v"].astype(str).map(
            lambda target: (
                cfg.repeat_log_lambda * math.log1p(target_counts.get(target, 0))
                + cfg.repeat_linear_lambda * max(target_counts.get(target, 0) - 1, 0)
            )
        )
        top = top.assign(
            diversification_penalty=penalties.astype(float),
            regularized_priority=top["base_priority"] - penalties.astype(float),
        )
        chosen_idx = top.sort_values(
            ["regularized_priority", "base_priority", score_col],
            ascending=[False, False, False],
        ).index[0]
        chosen = top.loc[chosen_idx]
        selected_rows.append(chosen)
        target = str(chosen["v"])
        target_counts[target] = target_counts.get(target, 0) + 1
        top = top.drop(index=chosen_idx)

    selected_df = pd.DataFrame(selected_rows)
    if rest.empty:
        out = selected_df.copy()
    else:
        rest = rest.assign(diversification_penalty=0.0, regularized_priority=rest["base_priority"])
        out = pd.concat([selected_df, rest], ignore_index=True)
    out = out.reset_index(drop=True)
    out["regularized_rank"] = out.index + 1
    return out


def _annotate_surface_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["source_family"] = out["u_label"].map(_normalize_family_label)
    out["target_family"] = out["v_label"].map(_normalize_family_label)
    out["semantic_family_key"] = out["source_family"].astype(str) + "__" + out["target_family"].astype(str)
    out["source_theme"] = out["u_label"].map(_theme_for_label)
    out["target_theme"] = out["v_label"].map(_theme_for_label)
    out["theme_pair_key"] = out["source_theme"].astype(str) + "__" + out["target_theme"].astype(str)
    return out


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


def _apply_surface_shortlist_layer(df: pd.DataFrame, cfg: SurfaceLayerConfig) -> pd.DataFrame:
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

    top_window = ordered.head(int(cfg.top_window)).copy()
    tail = ordered.iloc[int(cfg.top_window) :].copy()
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
        broad_repeat_indicator = (
            work["endpoint_broadness_pct"].astype(float) >= float(cfg.broad_repeat_start_pct)
        ).astype(float)
        work["broad_repeat_penalty"] = broad_repeat_indicator * (
            work["source_family"].astype(str).map(lambda x: float(cfg.broad_repeat_lambda) * source_counts[x])
            + work["target_family"].astype(str).map(lambda x: float(cfg.broad_repeat_lambda) * target_counts[x])
        )
        work["paperworthiness_dynamic_penalty"] = (
            work["source_family"].astype(str).map(lambda x: float(cfg.source_repeat_lambda) * source_counts[x])
            + work["target_family"].astype(str).map(lambda x: float(cfg.target_repeat_lambda) * target_counts[x])
            + work["semantic_family_key"].astype(str).map(lambda x: float(cfg.family_repeat_lambda) * family_counts[x])
            + work["source_theme"].astype(str).map(lambda x: float(cfg.theme_repeat_lambda) * max(source_theme_counts[x] - 1, 0))
            + work["target_theme"].astype(str).map(lambda x: float(cfg.theme_repeat_lambda) * max(target_theme_counts[x] - 1, 0))
            + work["theme_pair_key"].astype(str).map(lambda x: float(cfg.theme_pair_repeat_lambda) * theme_pair_counts[x])
            + work["broad_repeat_penalty"].astype(float)
        )
        work["paper_surface_penalty"] = work["paperworthiness_static_penalty"].astype(float) + work["paperworthiness_dynamic_penalty"].astype(float)
        work["paper_surface_priority"] = work["frontier_rank"].astype(float) + work["paper_surface_penalty"].astype(float)
        pick = work.sort_values(["paper_surface_priority", "frontier_rank", "u", "v"], ascending=[True, True, True, True]).iloc[0]
        selected_rows.append(pick)
        source_counts[str(pick["source_family"])] += 1
        target_counts[str(pick["target_family"])] += 1
        family_counts[str(pick["semantic_family_key"])] += 1
        source_theme_counts[str(pick["source_theme"])] += 1
        target_theme_counts[str(pick["target_theme"])] += 1
        theme_pair_counts[str(pick["theme_pair_key"])] += 1
        remaining = remaining[~(remaining["u"].astype(str).eq(str(pick["u"])) & remaining["v"].astype(str).eq(str(pick["v"])))].copy()

    surfaced_top = pd.DataFrame(selected_rows).reset_index(drop=True)
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


def _annotate_mediators_json(raw: Any, code_to_label: dict[str, str]) -> str:
    if pd.isna(raw):
        return "[]"
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return "[]"
    elif isinstance(raw, list):
        payload = raw
    else:
        return "[]"

    out: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        mediator = str(item.get("mediator", "") or "")
        label = _clean_text(code_to_label.get(mediator, mediator))
        patched = dict(item)
        patched["label"] = label
        out.append(patched)
    return json.dumps(out, ensure_ascii=False)


def _annotate_paths_json(raw: Any, code_to_label: dict[str, str]) -> str:
    if pd.isna(raw):
        return "[]"
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return "[]"
    elif isinstance(raw, list):
        payload = raw
    else:
        return "[]"

    out: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        path_codes = item.get("path", [])
        if not isinstance(path_codes, list):
            path_codes = []
        patched = dict(item)
        patched["path_labels"] = [_clean_text(code_to_label.get(str(code), str(code))) for code in path_codes]
        out.append(patched)
    return json.dumps(out, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit best frozen-ontology rerankers and score the current frontier.")
    parser.add_argument("--corpus", default="data/processed/research_allocation_v2/hybrid_corpus.parquet", dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper_meta", default="data/processed/research_allocation_v2/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--tuning_best", default="outputs/paper/14_learned_reranker_tuning/tuning_best_configs.csv", dest="tuning_best_path")
    parser.add_argument("--cutoff_years", type=int, nargs="*", default=[1990, 1995, 2000, 2005, 2010, 2015])
    parser.add_argument("--pool_sizes", default="10000")
    parser.add_argument("--candidate-family-mode", default="", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="", dest="path_to_direct_scope")
    parser.add_argument("--pairwise_negatives_per_positive", type=int, default=2)
    parser.add_argument("--pairwise_max_pairs_per_cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--panel-cache", default="", dest="panel_cache")
    parser.add_argument("--sink-regularizer-configs", default="", dest="sink_regularizer_configs")
    parser.add_argument("--surface-top-window", type=int, default=200, dest="surface_top_window")
    parser.add_argument("--surface-broadness-start-pct", type=float, default=0.85, dest="surface_broadness_start_pct")
    parser.add_argument("--surface-broadness-lambda", type=float, default=6.0, dest="surface_broadness_lambda")
    parser.add_argument("--surface-resolution-floor", type=float, default=0.08, dest="surface_resolution_floor")
    parser.add_argument("--surface-resolution-lambda", type=float, default=4.0, dest="surface_resolution_lambda")
    parser.add_argument("--surface-generic-endpoint-lambda", type=float, default=2.0, dest="surface_generic_endpoint_lambda")
    parser.add_argument("--surface-mediator-specificity-floor", type=float, default=0.45, dest="surface_mediator_specificity_floor")
    parser.add_argument("--surface-mediator-specificity-lambda", type=float, default=2.5, dest="surface_mediator_specificity_lambda")
    parser.add_argument("--surface-textbook-like-start-pct", type=float, default=0.85, dest="surface_textbook_like_start_pct")
    parser.add_argument("--surface-textbook-like-lambda", type=float, default=4.0, dest="surface_textbook_like_lambda")
    parser.add_argument("--surface-source-repeat-lambda", type=float, default=2.0, dest="surface_source_repeat_lambda")
    parser.add_argument("--surface-target-repeat-lambda", type=float, default=2.0, dest="surface_target_repeat_lambda")
    parser.add_argument("--surface-family-repeat-lambda", type=float, default=6.0, dest="surface_family_repeat_lambda")
    parser.add_argument("--surface-theme-repeat-lambda", type=float, default=2.0, dest="surface_theme_repeat_lambda")
    parser.add_argument("--surface-theme-pair-repeat-lambda", type=float, default=3.0, dest="surface_theme_pair_repeat_lambda")
    parser.add_argument("--surface-broad-repeat-start-pct", type=float, default=0.85, dest="surface_broad_repeat_start_pct")
    parser.add_argument("--surface-broad-repeat-lambda", type=float, default=2.0, dest="surface_broad_repeat_lambda")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


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


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    sink_regularizer_cfgs = _load_sink_regularizer_configs(args.sink_regularizer_configs)
    surface_cfg = SurfaceLayerConfig(
        top_window=int(args.surface_top_window),
        broad_endpoint_start_pct=float(args.surface_broadness_start_pct),
        broad_endpoint_lambda=float(args.surface_broadness_lambda),
        resolution_floor=float(args.surface_resolution_floor),
        resolution_lambda=float(args.surface_resolution_lambda),
        generic_endpoint_lambda=float(args.surface_generic_endpoint_lambda),
        mediator_specificity_floor=float(args.surface_mediator_specificity_floor),
        mediator_specificity_lambda=float(args.surface_mediator_specificity_lambda),
        textbook_like_start_pct=float(args.surface_textbook_like_start_pct),
        textbook_like_lambda=float(args.surface_textbook_like_lambda),
        source_repeat_lambda=float(args.surface_source_repeat_lambda),
        target_repeat_lambda=float(args.surface_target_repeat_lambda),
        family_repeat_lambda=float(args.surface_family_repeat_lambda),
        theme_repeat_lambda=float(args.surface_theme_repeat_lambda),
        theme_pair_repeat_lambda=float(args.surface_theme_pair_repeat_lambda),
        broad_repeat_start_pct=float(args.surface_broad_repeat_start_pct),
        broad_repeat_lambda=float(args.surface_broad_repeat_lambda),
    )

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    candidate_cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    if args.candidate_family_mode:
        candidate_cfg.candidate_family_mode = str(args.candidate_family_mode)
    if args.path_to_direct_scope:
        candidate_cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None
    best_df = pd.read_csv(args.tuning_best_path)
    if best_df.empty:
        raise SystemExit("No best tuning configurations found.")

    pool_sizes = [int(x.strip()) for x in str(args.pool_sizes).split(",") if x.strip()]
    historical_horizons = sorted(set(int(x) for x in best_df["horizon"].tolist()))
    panel_cache_path = Path(str(args.panel_cache)) if str(args.panel_cache).strip() else None
    if panel_cache_path is not None and panel_cache_path.exists():
        panel_df = pd.read_parquet(panel_cache_path)
        panel_df = panel_df[
            panel_df["horizon"].astype(int).isin(historical_horizons)
        ].copy()
    else:
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=candidate_cfg,
            cutoff_years=[int(x) for x in args.cutoff_years],
            horizons=historical_horizons,
            pool_sizes=pool_sizes,
            paper_meta_df=paper_meta_df,
        )
    if panel_df.empty:
        raise SystemExit("Historical panel is empty; cannot fit rerankers.")

    current_cutoff_t = int(corpus_df["year"].max()) + 1
    train_corpus = corpus_df[corpus_df["year"] <= (current_cutoff_t - 1)].copy()
    concept_meta = _concept_metadata_map(corpus_df)
    code_to_label = {code: payload.get("label", code) for code, payload in concept_meta.items()}
    cfg_current = copy.deepcopy(candidate_cfg)
    if hasattr(cfg_current, "include_details"):
        setattr(cfg_current, "include_details", True)
    current_df = build_candidate_table(train_corpus, cutoff_t=current_cutoff_t, cfg=cfg_current)
    if current_df.empty:
        raise SystemExit("Current candidate table is empty.")
    max_pool = max(pool_sizes)
    current_df = current_df.sort_values("score", ascending=False).head(max_pool).reset_index(drop=True)
    current_df = enrich_candidate_features(current_df, train_df=train_corpus, cutoff_t=current_cutoff_t, paper_meta_df=paper_meta_df)
    current_df["transparent_rank"] = current_df.index + 1
    current_df["transparent_score"] = current_df["score"].astype(float)

    outputs: list[pd.DataFrame] = []
    summary_rows: list[dict] = []
    for row in best_df.itertuples(index=False):
        horizon = int(row.horizon)
        pool_size = int(row.pool_size)
        pool_flag = f"in_pool_{pool_size}"
        if pool_flag not in panel_df.columns:
            continue
        train_rows = panel_df[(panel_df["horizon"] == horizon) & (panel_df[pool_flag].astype(int) == 1)].copy()
        feature_names = [c for c in _feature_list(str(row.feature_family)) if c in train_rows.columns and c in current_df.columns]
        model = _fit_model(
            model_kind=str(row.model_kind),
            train_rows=train_rows,
            feature_names=feature_names,
            alpha=float(row.alpha),
            pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
            pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
            seed=int(args.seed) + horizon,
        )
        if model is None:
            continue
        eval_rows = current_df.head(pool_size).copy()
        ranked = score_with_reranker(eval_rows, model).rename(columns={"score": "reranker_score", "rank": "reranker_rank"})
        merged = eval_rows.merge(ranked, on=["u", "v"], how="left")
        merged["horizon"] = horizon
        merged["model_kind"] = str(row.model_kind)
        merged["feature_family"] = str(row.feature_family)
        merged["alpha"] = float(row.alpha)
        merged["pool_size"] = pool_size
        merged["rank_delta"] = merged["transparent_rank"].astype(int) - merged["reranker_rank"].astype(int)
        merged["abs_rank_delta"] = merged["rank_delta"].abs()
        merged["u_label"] = merged["u"].astype(str).map(code_to_label).fillna(merged["u"].astype(str)).map(_clean_text)
        merged["v_label"] = merged["v"].astype(str).map(code_to_label).fillna(merged["v"].astype(str)).map(_clean_text)
        if "top_mediators_json" in merged.columns:
            merged["top_mediators_json"] = merged["top_mediators_json"].map(lambda raw: _annotate_mediators_json(raw, code_to_label))
        if "top_paths_json" in merged.columns:
            merged["top_paths_json"] = merged["top_paths_json"].map(lambda raw: _annotate_paths_json(raw, code_to_label))
        merged["u_endpoint_flags"] = merged["u"].astype(str).map(lambda code: "|".join(_endpoint_flag_reasons(code, concept_meta)))
        merged["v_endpoint_flags"] = merged["v"].astype(str).map(lambda code: "|".join(_endpoint_flag_reasons(code, concept_meta)))
        merged["u_endpoint_flag_count"] = merged["u_endpoint_flags"].map(lambda s: 0 if not s else len(str(s).split("|")))
        merged["v_endpoint_flag_count"] = merged["v_endpoint_flags"].map(lambda s: 0 if not s else len(str(s).split("|")))
        merged["u_endpoint_penalty"] = merged["u_endpoint_flags"].map(_flag_penalty)
        merged["v_endpoint_penalty"] = merged["v_endpoint_flags"].map(_flag_penalty)
        merged["surface_penalty"] = merged["u_endpoint_penalty"].astype(int) + merged["v_endpoint_penalty"].astype(int)
        merged["surface_flagged"] = (merged["surface_penalty"].astype(int) > 0).astype(int)
        if "focal_mediator" in merged.columns:
            merged["focal_mediator_flags"] = merged["focal_mediator"].astype(str).map(lambda code: "|".join(_mediator_flag_reasons(code, concept_meta)))
            merged["focal_mediator_flag_penalty"] = merged["focal_mediator_flags"].map(_flag_penalty)
        else:
            merged["focal_mediator_flags"] = ""
            merged["focal_mediator_flag_penalty"] = 0
        regularizer_cfg = sink_regularizer_cfgs.get(horizon)
        if regularizer_cfg is not None:
            sink_targets = _compute_sink_targets(merged)
            merged = merged.merge(sink_targets, on="v", how="left")
            merged["sink_score"] = merged["sink_score"].fillna(0.0)
            merged["sink_score_pct"] = merged["sink_score_pct"].fillna(0.0)
            merged = _apply_sink_regularizer(merged, regularizer_cfg)
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
        merged = merged.sort_values(["frontier_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
        surfaced = _apply_surface_shortlist_layer(merged, surface_cfg)
        merged = merged.merge(surfaced[["u", "v", "surface_rank"]], on=["u", "v"], how="left")
        surface_merge_cols = [
            "paper_surface_penalty",
            "paper_surface_priority",
            "paperworthiness_static_penalty",
            "paperworthiness_dynamic_penalty",
            "broad_endpoint_penalty",
            "resolution_penalty",
            "generic_endpoint_penalty",
            "generic_mediator_penalty",
            "textbook_like_penalty",
            "textbook_like_raw",
            "broad_repeat_start_pct",
            "broad_repeat_penalty",
            "endpoint_broadness_pct",
            "mediator_specificity_shortfall",
            "resolution_shortfall",
            "source_family",
            "target_family",
            "semantic_family_key",
            "source_theme",
            "target_theme",
            "theme_pair_key",
        ]
        missing_surface_cols = [col for col in surface_merge_cols if col not in merged.columns]
        if missing_surface_cols:
            merged = merged.merge(
                surfaced[["u", "v"] + missing_surface_cols],
                on=["u", "v"],
                how="left",
            )
        merged = _coalesce_merge_columns(
            merged,
            [
                "endpoint_broadness_pct",
                "source_family",
                "target_family",
                "semantic_family_key",
                "source_theme",
                "target_theme",
                "theme_pair_key",
            ],
        )
        if any(col not in merged.columns for col in ["source_family", "target_family", "semantic_family_key", "source_theme", "target_theme", "theme_pair_key"]):
            merged = _annotate_surface_keys(merged)
        merged = merged.sort_values(["surface_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
        outputs.append(merged)
        top = merged.nsmallest(100, "frontier_rank")
        surfaced_top = merged.nsmallest(100, "surface_rank")
        summary_rows.append(
            {
                "horizon": horizon,
                "model_kind": str(row.model_kind),
                "feature_family": str(row.feature_family),
                "alpha": float(row.alpha),
                "pool_size": pool_size,
                "top100_mean_rank_delta": float(top["rank_delta"].mean()),
                "top100_median_rank_delta": float(top["rank_delta"].median()),
                "top100_max_rank_gain": int(top["rank_delta"].max()),
                "top100_max_rank_drop": int(top["rank_delta"].min()),
                "top100_surface_flagged_share": float(top["surface_flagged"].mean()),
                "top100_mean_sink_penalty": float(top["sink_penalty"].mean()),
                "top100_mean_diversification_penalty": float(top["diversification_penalty"].mean()),
                "surface_top100_green_share": float(
                    surfaced_top["theme_pair_key"].astype(str).str.contains("environment_climate").mean()
                ),
                "surface_top100_wtp_share": float(
                    surfaced_top["semantic_family_key"].astype(str).str.contains("willingness to pay").mean()
                ),
                "surface_top100_unique_theme_pair_keys": int(surfaced_top["theme_pair_key"].astype(str).nunique()),
                "surface_top100_unique_semantic_family_keys": int(surfaced_top["semantic_family_key"].astype(str).nunique()),
                "surface_top100_unique_sources": int(surfaced_top["u_label"].astype(str).nunique()),
                "surface_top100_unique_targets": int(surfaced_top["v_label"].astype(str).nunique()),
                "surface_top100_top_target_share": float(surfaced_top["v_label"].astype(str).value_counts(normalize=True).iloc[0]) if not surfaced_top.empty else 0.0,
                "surface_top100_broad_endpoint_share": float(
                    (surfaced_top["endpoint_broadness_pct"].astype(float) >= surface_cfg.broad_endpoint_start_pct).mean()
                ),
                "surface_top100_generic_endpoint_share": float((surfaced_top["surface_penalty"].astype(float) > 0).mean()),
                "surface_top100_generic_mediator_share": float((surfaced_top["generic_mediator_penalty"].astype(float) > 0).mean()),
                "surface_top100_textbook_like_share": float((surfaced_top["textbook_like_penalty"].astype(float) > 0).mean()),
                "surface_top100_mean_endpoint_broadness": float(surfaced_top["endpoint_broadness_raw"].astype(float).mean()),
                "surface_top100_mean_endpoint_resolution": float(surfaced_top["endpoint_resolution_score"].astype(float).mean()),
                "surface_top100_mean_paper_surface_penalty": float(surfaced_top["paper_surface_penalty"].astype(float).mean()),
            }
        )

    if not outputs:
        raise SystemExit("No current reranked frontier outputs were produced.")

    all_outputs = pd.concat(outputs, ignore_index=True)
    summary_df = pd.DataFrame(summary_rows)
    all_outputs.to_parquet(Path(out_dir) / "current_reranked_frontier.parquet", index=False)
    all_outputs.to_csv(Path(out_dir) / "current_reranked_frontier.csv", index=False)
    summary_df.to_csv(Path(out_dir) / "current_reranked_frontier_summary.csv", index=False)

    lines = [
        "# Current Reranked Frontier",
        "",
        "This note applies the best tuned frozen-ontology rerankers to the current frontier candidate pool.",
        "",
    ]
    for horizon in sorted(all_outputs["horizon"].dropna().unique()):
        sub = all_outputs[all_outputs["horizon"] == int(horizon)].copy()
        if sub.empty:
            continue
        meta = sub.iloc[0]
        lines.append(
            f"## Horizon {int(horizon)}"
        )
        lines.append(
            f"- model: {meta['model_kind']} + {meta['feature_family']} (alpha={float(meta['alpha']):.3f}, pool={int(meta['pool_size'])})"
        )
        lines.append(
            f"- paper-facing surfacing layer: top_window={surface_cfg.top_window}, broad_start_pct={surface_cfg.broad_endpoint_start_pct:.2f}, broad_lambda={surface_cfg.broad_endpoint_lambda:.2f}, resolution_floor={surface_cfg.resolution_floor:.2f}, resolution_lambda={surface_cfg.resolution_lambda:.2f}, generic_endpoint_lambda={surface_cfg.generic_endpoint_lambda:.2f}, mediator_floor={surface_cfg.mediator_specificity_floor:.2f}, mediator_lambda={surface_cfg.mediator_specificity_lambda:.2f}, textbook_start_pct={surface_cfg.textbook_like_start_pct:.2f}, textbook_lambda={surface_cfg.textbook_like_lambda:.2f}, source_repeat_lambda={surface_cfg.source_repeat_lambda:.2f}, target_repeat_lambda={surface_cfg.target_repeat_lambda:.2f}, family_repeat_lambda={surface_cfg.family_repeat_lambda:.2f}, theme_repeat_lambda={surface_cfg.theme_repeat_lambda:.2f}, theme_pair_repeat_lambda={surface_cfg.theme_pair_repeat_lambda:.2f}, broad_repeat_start_pct={surface_cfg.broad_repeat_start_pct:.2f}, broad_repeat_lambda={surface_cfg.broad_repeat_lambda:.2f}"
        )
        if int(horizon) in sink_regularizer_cfgs:
            reg_cfg = sink_regularizer_cfgs[int(horizon)]
            lines.append(
                f"- concentration layer: variant={reg_cfg.variant}, start_pct={reg_cfg.sink_start_pct:.4f}, sink_lambda={reg_cfg.sink_lambda:.4f}, window={reg_cfg.diversify_window}, repeat_log={reg_cfg.repeat_log_lambda:.4f}, repeat_linear={reg_cfg.repeat_linear_lambda:.4f}"
            )
        lines.append(f"- flagged share in surfaced top 100: {float(sub.head(100)['surface_flagged'].mean()):.3f}")
        lines.append(f"- green/climate share in surfaced top 100: {float(sub.head(100)['theme_pair_key'].astype(str).str.contains('environment_climate').mean()):.3f}")
        lines.append(f"- willingness-to-pay share in surfaced top 100: {float(sub.head(100)['semantic_family_key'].astype(str).str.contains('willingness to pay').mean()):.3f}")
        lines.append(f"- broad-endpoint share in surfaced top 100: {float((sub.head(100)['endpoint_broadness_pct'].astype(float) >= surface_cfg.broad_endpoint_start_pct).mean()):.3f}")
        lines.append(f"- textbook-like share in surfaced top 100: {float((sub.head(100)['textbook_like_penalty'].astype(float) > 0).mean()):.3f}")
        lines.append("- Top 10 surfaced candidates:")
        for cand in sub.head(10).itertuples(index=False):
            extras: list[str] = []
            if cand.u_endpoint_flags:
                extras.append(f"u_flags={cand.u_endpoint_flags}")
            if cand.v_endpoint_flags:
                extras.append(f"v_flags={cand.v_endpoint_flags}")
            if getattr(cand, "focal_mediator_flags", ""):
                extras.append(f"m_flags={cand.focal_mediator_flags}")
            extra_txt = f" | {', '.join(extras)}" if extras else ""
            lines.append(
                f"  - {cand.u_label} -> {cand.v_label} | surface_rank={int(cand.surface_rank)}, frontier_rank={int(cand.frontier_rank)}, reranker_rank={int(cand.reranker_rank)}, transparent_rank={int(cand.transparent_rank)}, rank_delta={int(cand.rank_delta)}, sink_penalty={float(cand.sink_penalty):.4f}, diversification_penalty={float(cand.diversification_penalty):.4f}, paper_penalty={float(getattr(cand, 'paper_surface_penalty', 0.0)):.4f}{extra_txt}"
            )
        lines.append("")
    (Path(out_dir) / "current_reranked_frontier.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "current_cutoff_t": current_cutoff_t,
        "historical_cutoff_years": [int(x) for x in args.cutoff_years],
        "candidate_family_mode": str(candidate_cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(candidate_cfg, "path_to_direct_scope", "")),
        "tuning_best_path": args.tuning_best_path,
        "panel_cache": str(panel_cache_path) if panel_cache_path is not None else "",
        "sink_regularizer_configs": args.sink_regularizer_configs,
        "pool_sizes": pool_sizes,
        "surface_layer_config": {
            "top_window": surface_cfg.top_window,
            "broad_endpoint_start_pct": surface_cfg.broad_endpoint_start_pct,
            "broad_endpoint_lambda": surface_cfg.broad_endpoint_lambda,
            "resolution_floor": surface_cfg.resolution_floor,
            "resolution_lambda": surface_cfg.resolution_lambda,
            "generic_endpoint_lambda": surface_cfg.generic_endpoint_lambda,
            "mediator_specificity_floor": surface_cfg.mediator_specificity_floor,
            "mediator_specificity_lambda": surface_cfg.mediator_specificity_lambda,
            "textbook_like_start_pct": surface_cfg.textbook_like_start_pct,
            "textbook_like_lambda": surface_cfg.textbook_like_lambda,
            "source_repeat_lambda": surface_cfg.source_repeat_lambda,
            "target_repeat_lambda": surface_cfg.target_repeat_lambda,
            "family_repeat_lambda": surface_cfg.family_repeat_lambda,
            "theme_repeat_lambda": surface_cfg.theme_repeat_lambda,
            "theme_pair_repeat_lambda": surface_cfg.theme_pair_repeat_lambda,
            "broad_repeat_start_pct": surface_cfg.broad_repeat_start_pct,
            "broad_repeat_lambda": surface_cfg.broad_repeat_lambda,
        },
        "n_rows": int(len(all_outputs)),
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote: {Path(out_dir) / 'current_reranked_frontier.csv'}")


if __name__ == "__main__":
    main()
