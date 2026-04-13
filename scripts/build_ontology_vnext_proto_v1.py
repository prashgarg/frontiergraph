from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
import re
import sqlite3
from pathlib import Path
import sys
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.context_normalization import normalize_context_value


ENVIRONMENTAL_OUTCOME_FAMILY = {
    "family_id": "environmental_outcomes_family",
    "family_label": "environmental outcomes",
    "family_type": "outcome_family",
    "assignment_reason": "Reviewed seed from repeated shortlist confusion; related environmental outcomes that should remain distinct.",
    "do_not_merge_note": "Keep separate canonical concepts; use family only for grouping and surface interpretation.",
    "member_concept_ids": [
        "FG3C000081",  # environmental quality
        "FG3C000203",  # environmental pollution
        "FG3C000130",  # environmental degradation
        "FG3C000003",  # CO2 emissions
        "FG3C000064",  # ecological footprint
    ],
}
UNCERTAINTY_RISK_FAMILY = {
    "family_id": "uncertainty_risk_family",
    "family_label": "uncertainty and risk concepts",
    "family_type": "mechanism_family",
    "assignment_reason": "Reviewed seed promoted from the candidate-family queue after repeated shortlist collisions around uncertainty measurement objects.",
    "do_not_merge_note": "Keep separate canonical concepts; this family groups adjacent uncertainty concepts without treating them as synonyms.",
    "member_concept_ids": [
        "FG3C000047",  # uncertainty
        "FG3C004120",  # uncertainty measures
    ],
}
INNOVATION_TECHNOLOGY_FAMILY = {
    "family_id": "innovation_technology_family",
    "family_label": "innovation and technology concepts",
    "family_type": "outcome_family",
    "assignment_reason": "Reviewed seed promoted from the candidate-family queue after repeated shortlist collisions across digital, innovation, and technology concepts.",
    "do_not_merge_note": "Keep separate canonical concepts; this family captures adjacent innovation and technology outcomes, not synonyms.",
    "member_concept_ids": [
        "FG3C000068",  # digital economy
        "FG3C000494",  # digital economy development
        "FG3C000226",  # digital transformation
        "FG3C006136",  # innovation level
        "FG3C000013",  # technological innovation
        "FG3C000045",  # technological progress
    ],
}
MACRO_CYCLE_PRICES_FAMILY = {
    "family_id": "macro_cycle_prices_family",
    "family_label": "macro cycle and price concepts",
    "family_type": "outcome_family",
    "assignment_reason": "Reviewed seed promoted from the candidate-family queue after repeated shortlist collisions across macro cycle, growth, inflation, and price concepts.",
    "do_not_merge_note": "Keep separate canonical concepts; these are related macro outcomes and state variables, not mergeable synonyms.",
    "member_concept_ids": [
        "FG3C000051",  # house prices
        "FG3C000002",  # inflation
        "FG3C000110",  # output growth
        "FG3C000674",  # price changes
        "FG3C005776",  # rate of growth
        "FG3C005161",  # state of the business cycle
    ],
}
TRADE_FLOW_OPENNESS_FAMILY = {
    "family_id": "trade_flow_openness_family",
    "family_label": "trade flow and openness concepts",
    "family_type": "outcome_family",
    "assignment_reason": "Reviewed split from the broad trade/urban candidate; these trade-flow concepts are coherent enough to group without merging.",
    "do_not_merge_note": "Keep separate canonical concepts; use family only for grouping and comparison.",
    "member_concept_ids": [
        "FG3C000046",  # exports
        "FG3C000126",  # imports
        "FG3C000017",  # trade openness
    ],
}
STRUCTURAL_TRANSFORMATION_URBANIZATION_FAMILY = {
    "family_id": "structural_transformation_urbanization_family",
    "family_label": "structural transformation and urbanization concepts",
    "family_type": "outcome_family",
    "assignment_reason": "Reviewed split from the broad trade/urban candidate; these structure and transformation concepts are coherent enough to group without merging.",
    "do_not_merge_note": "Keep separate canonical concepts; use family only for grouping and comparison.",
    "member_concept_ids": [
        "FG3C000044",  # industrial structure
        "FG3C000097",  # industrial structure upgrading
        "FG3C000012",  # urbanization
    ],
}
REVIEWED_FAMILY_SPECS = [
    ENVIRONMENTAL_OUTCOME_FAMILY,
    UNCERTAINTY_RISK_FAMILY,
    INNOVATION_TECHNOLOGY_FAMILY,
    MACRO_CYCLE_PRICES_FAMILY,
    TRADE_FLOW_OPENNESS_FAMILY,
    STRUCTURAL_TRANSFORMATION_URBANIZATION_FAMILY,
]

THEORY_TYPES = {"theory_or_model"}
EMPIRICAL_TYPES = {
    "descriptive_observational",
    "time_series_econometrics",
    "panel_FE_or_TWFE",
    "DiD",
    "experiment",
    "event_study",
    "IV",
    "RDD",
    "qualitative_or_case_study",
    "prediction_or_forecasting",
}
MIXED_TYPES = {"structural_model", "simulation"}
UNKNOWN_TYPES = {"do_not_know", "other"}
MISSING_EVIDENCE_VALUES = {"", "nan", "none", "null", "unknown"}
SUPPORTED_RELATION_TYPES = {"exact", "synonym", "broader", "narrower", "related", "do_not_merge"}
IDENTIFICATION_STRENGTH_ALLOWED = {"descriptive", "suggestive", "stronger_causal", "theory_only", "unknown"}
TAXONOMY_CONFIDENCE_ALLOWED = {1.0, 0.75, 0.5, 0.25}
CONCEPT_TYPE_ALLOWED = {
    "method",
    "data_artifact",
    "metadata_container",
    "substantive_outcome",
    "substantive_mechanism",
}
SUBSTANTIVE_SUBTYPE_ALLOWED = {
    "not_applicable",
    "policy_outcome_or_boundary",
    "event_institution_context",
    "finance_attribute_bundle",
    "quantity_count_object",
    "general_substantive_other",
}
AUDIT_PRIORITY_ALLOWED = {"not_applicable", "high", "medium", "low"}
CONTEXT_ENTITY_TYPE_ALLOWED = {"none", "event", "institution_actor", "geography_context"}
CONTEXT_ALIAS_GEOGRAPHY_TYPES = {"country", "region", "bloc", "country_or_place", "country_or_territory"}
CONTEXT_ALIAS_HIGH_CONFIDENCE_STATUSES = {"canonical", "normalized_alias", "canonical_region", "canonical_bloc"}
CONTEXT_ALIAS_LOW_CONFIDENCE_STATUSES = {"fallback_passthrough"}
CONTEXT_ALIAS_ALLOWED_STATUSES = CONTEXT_ALIAS_HIGH_CONFIDENCE_STATUSES | CONTEXT_ALIAS_LOW_CONFIDENCE_STATUSES
GENERIC_FAMILY_STOPWORDS = {
    "the",
    "and",
    "of",
    "in",
    "to",
    "for",
    "on",
    "with",
    "from",
    "an",
    "a",
}
OUTCOME_FAMILY_TOKENS = {
    "emissions",
    "pollution",
    "degradation",
    "innovation",
    "growth",
    "output",
    "gdp",
    "exports",
    "imports",
    "footprint",
    "inequality",
    "consumption",
    "efficiency",
}
INSTITUTION_FAMILY_TOKENS = {"tax", "taxes", "policy", "regulation", "governance", "institution", "institutions"}
METHOD_FAMILY_TOKENS = {"regression", "estimation", "model", "models", "iv", "did", "rdd", "forecasting"}
CONTEXT_FAMILY_TOKENS = {"country", "countries", "region", "regions", "firm", "household", "population", "geography"}
REVIEW_NOTE_PATTERNS = [
    "next_steps/**/*.md",
    "outputs/paper/27_ontology_vnext_proto_review/*.md",
    "outputs/paper/28_vnext_frontier_question_prototypes/*.md",
    "outputs/paper/29_vnext_object_scored_frontier/*.md",
    "outputs/paper/30_vnext_routed_shortlist/*.md",
]
METHOD_TERMS = {
    "regression",
    "estimation",
    "estimator",
    "model",
    "models",
    "simulation",
    "forecast",
    "forecasts",
    "forecasting",
    "quantile",
    "method",
    "methods",
    "mmqr",
    "iv",
    "did",
    "rdd",
}
DATA_ARTIFACT_EXACT = {
    "data",
    "dataset",
    "panel data",
    "survey data",
    "high frequency data",
    "microdata",
    "available data",
    "us data",
}
METADATA_CONTAINER_EXACT = {
    "existing methods",
    "policy variables",
    "model parameters",
    "study results",
    "this article",
    "parameters",
    "models",
}
OUTCOME_BUCKET_HINTS = {
    "outcome",
    "dependent_variable",
    "exposure",
    "policy",
}
OUTCOME_CONCEPT_TOKENS = OUTCOME_FAMILY_TOKENS | {
    "inflation",
    "urbanization",
    "openness",
    "house",
    "prices",
    "digital",
    "technology",
}
EVENT_CONTEXT_TERMS = {
    "covid",
    "pandemic",
    "outbreak",
    "country",
    "countries",
    "region",
    "regions",
    "africa",
    "oecd",
    "who",
    "organization",
}
INSTITUTION_TERMS = {
    "organization",
    "banking",
    "banks",
    "lenders",
    "government",
    "institution",
    "institutions",
}
FINANCE_ATTRIBUTE_TERMS = {
    "default",
    "defaults",
    "deposit",
    "deposits",
    "lenders",
    "banking",
    "bank",
    "bank-specific",
    "bid-ask",
    "hedging",
    "volatility",
    "asset",
}
COUNT_OBJECT_TERMS = {
    "number",
    "count",
    "counts",
    "quantity",
    "quantities",
    "agents",
    "flights",
    "passengers",
    "trades",
}
POLICY_OUTCOME_TERMS = {
    "co2",
    "emissions",
    "inflation",
    "unemployment",
    "efficiency",
    "inequality",
    "distribution",
    "tax",
    "taxes",
    "quality",
    "innovation",
    "energy",
    "environmental",
}
EVENT_ENTITY_TERMS = {
    "outbreak",
    "pandemic",
    "epidemic",
    "crisis",
    "disaster",
    "war",
    "conflict",
    "lockdown",
}
INSTITUTION_ENTITY_TERMS = {
    "organization",
    "bank",
    "banks",
    "banking",
    "government",
    "ministry",
    "lender",
    "lenders",
    "company",
    "companies",
    "corporation",
    "corporations",
    "firm",
    "firms",
    "institution",
    "institutions",
    "who",
}
GEOGRAPHY_ENTITY_TERMS = {
    "country",
    "countries",
    "region",
    "regions",
    "province",
    "provinces",
    "city",
    "cities",
    "africa",
    "europe",
    "asia",
    "oecd",
    "euro",
    "g7",
    "g20",
    "brics",
    "rural",
    "urban",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the first layered ontology vNext prototype from local active-baseline artifacts.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_patch_v1/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument(
        "--shortlist",
        default="outputs/paper/23_current_path_mediator_shortlist_patch_v1_labels_generic/current_path_mediator_shortlist.csv",
        dest="shortlist_path",
    )
    parser.add_argument(
        "--concept-db",
        default="data/production/frontiergraph_concept_public/concept_hard_app.sqlite",
        dest="concept_db_path",
    )
    parser.add_argument(
        "--out",
        default="data/processed/ontology_vnext_proto_v1",
        dest="out_dir",
    )
    parser.add_argument(
        "--review-out",
        default="outputs/paper/27_ontology_vnext_proto_review",
        dest="review_out_dir",
    )
    parser.add_argument(
        "--interpretation-note",
        default="next_steps/ontology_vnext_proto_v1_interpretation.md",
        dest="interpretation_note_path",
    )
    parser.add_argument(
        "--routed-shortlist",
        default="outputs/paper/30_vnext_routed_shortlist/routed_shortlist.csv",
        dest="routed_shortlist_path",
    )
    parser.add_argument(
        "--context-alias-csv",
        default="data/processed/ontology_vnext_proto_v1/context_alias_table.csv",
        dest="context_alias_csv_path",
    )
    parser.add_argument(
        "--family-review-note",
        default="next_steps/family_candidate_review.md",
        dest="family_review_note_path",
    )
    parser.add_argument(
        "--reviewed-design-family-csv",
        default="next_steps/reviewed_design_family_overrides.csv",
        dest="reviewed_design_family_csv_path",
    )
    parser.add_argument(
        "--reviewed-policy-semantics-csv",
        default="next_steps/reviewed_policy_edge_semantics.csv",
        dest="reviewed_policy_semantics_csv_path",
    )
    parser.add_argument(
        "--reviewed-relation-semantics-csv",
        default="next_steps/reviewed_relation_semantics_overrides.csv",
        dest="reviewed_relation_semantics_csv_path",
    )
    return parser.parse_args()


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _json_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "[]"
    text = str(value)
    return text if text.strip() else "[]"


def _json_text_obj(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "{}"
    text = str(value)
    return text if text.strip() else "{}"


def _dominant_value(series: pd.Series, default: str = "unknown") -> str:
    vals = series.fillna("").astype(str)
    vals = vals[vals.str.strip().ne("")]
    if vals.empty:
        return default
    return str(vals.value_counts().idxmax())


def _dominant_by_pair(frame: pd.DataFrame, value_col: str, output_col: str, default: str = "unknown") -> pd.DataFrame:
    keys = ["src_code", "dst_code"]
    values = frame[keys + [value_col]].copy()
    values[value_col] = values[value_col].fillna("").astype(str)
    values = values[values[value_col].str.strip().ne("")]
    if values.empty:
        return pd.DataFrame(columns=["source_concept_id", "target_concept_id", output_col])
    counts = values.groupby(keys + [value_col], as_index=False).size()
    counts = counts.sort_values(keys + ["size", value_col], ascending=[True, True, False, True])
    dominant = counts.drop_duplicates(keys, keep="first")[keys + [value_col]].rename(
        columns={
            "src_code": "source_concept_id",
            "dst_code": "target_concept_id",
            value_col: output_col,
        }
    )
    return dominant.reset_index(drop=True)


def _tokenize_label(value: Any) -> set[str]:
    text = _normalize_label(value)
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", text)
        if token and token not in GENERIC_FAMILY_STOPWORDS and len(token) >= 2
    }
    return tokens


def _parse_json_list(value: Any) -> list[Any]:
    text = str(value or "").strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _bucket_values(value: Any) -> set[str]:
    out: set[str] = set()
    for item in _parse_json_list(value):
        if isinstance(item, dict):
            label = str(item.get("value", "")).strip()
        else:
            label = str(item).strip()
        if label:
            out.add(_normalize_label(label))
    return out


def _aliases_tokens(value: Any) -> set[str]:
    out: set[str] = set()
    for item in _parse_json_list(value):
        out.update(_tokenize_label(item))
    return out


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return float(len(left & right)) / float(len(union))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def _bucket_taxonomy_confidence(value: Any) -> float:
    score = _safe_float(value, 0.25)
    if score >= 0.875:
        return 1.0
    if score >= 0.625:
        return 0.75
    if score >= 0.375:
        return 0.5
    return 0.25


def _evidence_mode(evidence_type: str) -> str:
    if evidence_type in THEORY_TYPES:
        return "theory"
    if evidence_type in EMPIRICAL_TYPES:
        return "empirics"
    if evidence_type in MIXED_TYPES:
        return "mixed"
    if evidence_type in UNKNOWN_TYPES:
        return "unknown"
    return "unknown"


def _normalize_design_family(evidence_type: Any) -> str:
    raw = str(evidence_type or "").strip()
    if not raw or _normalize_label(raw) in MISSING_EVIDENCE_VALUES:
        return "unknown"
    raw_norm = raw.replace(" ", "_")
    if raw_norm in THEORY_TYPES | EMPIRICAL_TYPES | MIXED_TYPES | UNKNOWN_TYPES:
        return raw_norm
    return "unknown"


def _identification_strength_for_design(design_family: str, causal_presentation: str | None = None) -> str:
    if design_family == "theory_or_model":
        return "theory_only"
    if design_family in {"experiment", "IV", "DiD", "RDD"}:
        return "stronger_causal"
    if design_family in {"event_study", "panel_FE_or_TWFE", "time_series_econometrics", "prediction_or_forecasting", "structural_model", "simulation"}:
        return "suggestive"
    if design_family in {"descriptive_observational", "qualitative_or_case_study"}:
        return "descriptive"
    if design_family == "unknown":
        causal = str(causal_presentation or "").strip().lower()
        if causal in {"explicit_causal", "implicit_causal"}:
            return "suggestive"
        return "unknown"
    return "unknown"


def _taxonomy_for_instance(row: pd.Series) -> dict[str, Any]:
    raw_design_family = _normalize_design_family(row.get("evidence_type"))
    causal_presentation = str(row.get("causal_presentation", "") or "").strip()
    relation_type = str(row.get("relation_type", "") or "").strip()

    if raw_design_family not in {"unknown", "do_not_know", "other"}:
        return {
            "evidence_mode": _evidence_mode(raw_design_family),
            "design_family": raw_design_family,
            "identification_strength": _identification_strength_for_design(raw_design_family, causal_presentation),
            "taxonomy_confidence": 1.0,
            "unknown_reason": "",
        }

    evidence_text = _normalize_label(row.get("evidence_type"))
    if not evidence_text or evidence_text in MISSING_EVIDENCE_VALUES:
        return {
            "evidence_mode": "unknown",
            "design_family": "unknown",
            "identification_strength": _identification_strength_for_design("unknown", causal_presentation),
            "taxonomy_confidence": 0.25,
            "unknown_reason": "missing_raw_evidence_type",
        }

    if evidence_text in {"do not know", "do_not_know"} or raw_design_family == "do_not_know":
        return {
            "evidence_mode": "unknown",
            "design_family": "do_not_know",
            "identification_strength": "unknown",
            "taxonomy_confidence": 0.25,
            "unknown_reason": "missing_raw_evidence_type",
        }

    if evidence_text == "other" or raw_design_family == "other":
        inferred_strength = _identification_strength_for_design("unknown", causal_presentation)
        inferred_confidence = 0.5 if inferred_strength != "unknown" or relation_type else 0.25
        return {
            "evidence_mode": "unknown",
            "design_family": "other",
            "identification_strength": inferred_strength,
            "taxonomy_confidence": inferred_confidence,
            "unknown_reason": "ambiguous_other",
        }

    return {
        "evidence_mode": "unknown",
        "design_family": "unknown",
        "identification_strength": _identification_strength_for_design("unknown", causal_presentation),
        "taxonomy_confidence": 0.25,
        "unknown_reason": "unsupported_design_label",
    }


def _apply_reviewed_evidence_overrides(grouped: pd.DataFrame) -> pd.DataFrame:
    out = grouped.copy()
    dominant_clean_design = out["dominant_evidence_type"].map(_normalize_design_family)
    clean_design_mask = dominant_clean_design.isin(THEORY_TYPES | EMPIRICAL_TYPES | MIXED_TYPES)
    strong_support_mask = (
        pd.to_numeric(out["distinct_paper_support"], errors="coerce").fillna(0).astype(int) >= 20
    ) & (
        pd.to_numeric(out["edge_instance_count"], errors="coerce").fillna(0).astype(int) >= 30
    )
    unresolved_mask = (
        out["edge_design_family"].astype(str).isin({"unknown", "do_not_know", "other"})
        | out["unknown_reason"].astype(str).ne("")
    )
    dominant_match_mask = out["edge_design_family"].astype(str).eq(dominant_clean_design.astype(str))
    can_override_mask = clean_design_mask & strong_support_mask & unresolved_mask

    # If the pair-level dominant design is already clean and strongly supported,
    # treat the canonical edge as resolved at the summary layer.
    set_design_mask = can_override_mask & (
        out["edge_design_family"].astype(str).isin({"unknown", "do_not_know", "other"})
        | dominant_match_mask
    )
    out.loc[set_design_mask, "edge_design_family"] = dominant_clean_design[set_design_mask]
    out.loc[set_design_mask, "edge_evidence_mode"] = dominant_clean_design[set_design_mask].map(_evidence_mode)
    out.loc[set_design_mask, "identification_strength"] = [
        _identification_strength_for_design(design, causal)
        for design, causal in zip(
            out.loc[set_design_mask, "edge_design_family"].astype(str),
            out.loc[set_design_mask, "dominant_causal_presentation"].astype(str),
        )
    ]
    out.loc[set_design_mask, "taxonomy_confidence"] = (
        pd.to_numeric(out.loc[set_design_mask, "taxonomy_confidence"], errors="coerce")
        .fillna(0.25)
        .clip(lower=0.75)
    )
    out.loc[set_design_mask, "unknown_reason"] = ""
    return out


def _apply_reviewed_design_family_resolutions(
    grouped: pd.DataFrame,
    reviewed_design_df: pd.DataFrame,
) -> pd.DataFrame:
    out = grouped.copy()
    out["edge_design_family_original"] = out["edge_design_family"].astype(str)
    out["edge_design_family_resolution_source"] = "none"
    out["edge_design_family_resolution_reason"] = ""
    out["edge_design_family_resolution_confidence"] = 0.0
    if reviewed_design_df.empty:
        return out

    out = out.merge(reviewed_design_df, on=["source_concept_id", "target_concept_id"], how="left")
    matched_mask = out["resolved_design_family"].fillna("").astype(str).ne("")
    if matched_mask.any():
        out.loc[matched_mask, "edge_design_family"] = out.loc[matched_mask, "resolved_design_family"].astype(str)
        out.loc[matched_mask, "edge_evidence_mode"] = out.loc[matched_mask, "edge_design_family"].astype(str).map(_evidence_mode)
        out.loc[matched_mask, "identification_strength"] = [
            _identification_strength_for_design(design, causal)
            for design, causal in zip(
                out.loc[matched_mask, "edge_design_family"].astype(str),
                out.loc[matched_mask, "dominant_causal_presentation"].astype(str),
            )
        ]
        out.loc[matched_mask, "taxonomy_confidence"] = (
            pd.to_numeric(out.loc[matched_mask, "resolution_confidence"], errors="coerce")
            .fillna(0.25)
            .map(_bucket_taxonomy_confidence)
            .astype(float)
        )
        out.loc[matched_mask, "unknown_reason"] = ""
        out.loc[matched_mask, "edge_design_family_resolution_source"] = out.loc[matched_mask, "resolution_source"].astype(str)
        out.loc[matched_mask, "edge_design_family_resolution_reason"] = out.loc[matched_mask, "resolution_reason"].astype(str)
        out.loc[matched_mask, "edge_design_family_resolution_confidence"] = pd.to_numeric(
            out.loc[matched_mask, "resolution_confidence"],
            errors="coerce",
        ).fillna(0.25).astype(float)
    return out.drop(columns=["resolved_design_family", "resolution_confidence", "resolution_source", "resolution_reason"])


def _attach_reviewed_policy_edge_semantics(
    edge_df: pd.DataFrame,
    reviewed_policy_df: pd.DataFrame,
) -> pd.DataFrame:
    out = edge_df.copy()
    if reviewed_policy_df.empty:
        out["policy_edge_semantic_type"] = "none"
        out["policy_edge_semantic_confidence"] = 0.0
        out["policy_edge_semantic_reason"] = ""
        out["regime_guardrail_decision"] = "not_applicable"
        out["regime_guardrail_reason"] = ""
        return out
    out = out.merge(reviewed_policy_df, on=["source_concept_id", "target_concept_id"], how="left")
    out["policy_edge_semantic_type"] = out["policy_edge_semantic_type"].fillna("none").astype(str)
    out["policy_edge_semantic_confidence"] = pd.to_numeric(out["policy_edge_semantic_confidence"], errors="coerce").fillna(0.0).astype(float)
    out["policy_edge_semantic_reason"] = out["policy_edge_semantic_reason"].fillna("").astype(str)
    out["regime_guardrail_decision"] = out["regime_guardrail_decision"].fillna("not_applicable").astype(str)
    out["regime_guardrail_reason"] = out["regime_guardrail_reason"].fillna("").astype(str)
    return out


def _attach_reviewed_relation_semantics(
    edge_df: pd.DataFrame,
    reviewed_relation_df: pd.DataFrame,
) -> pd.DataFrame:
    out = edge_df.copy()
    if reviewed_relation_df.empty:
        out["edge_relation_semantic_type"] = "none"
        out["edge_relation_semantic_confidence"] = 0.0
        out["edge_relation_semantic_reason"] = ""
        return out
    out = out.merge(reviewed_relation_df, on=["source_concept_id", "target_concept_id"], how="left")
    out["edge_relation_semantic_type"] = out["relation_semantic_type"].fillna("none").astype(str)
    out["edge_relation_semantic_confidence"] = pd.to_numeric(out["relation_semantic_confidence"], errors="coerce").fillna(0.0).astype(float)
    out["edge_relation_semantic_reason"] = out["relation_semantic_reason"].fillna("").astype(str)
    out = out.drop(columns=["relation_semantic_type", "relation_semantic_confidence", "relation_semantic_reason", "resolution_source"])
    return out


def _assign_audit_bucket(
    source_type: str,
    target_type: str,
) -> str:
    types = {str(source_type), str(target_type)}
    if "method" in types:
        return "method_artifact"
    if types & {"data_artifact", "metadata_container"}:
        return "metadata_container"
    if types.issubset({"substantive_outcome", "substantive_mechanism"}):
        return "substantive_unresolved"
    return "mixed_or_other"


def _substantive_label_tokens(label: Any) -> set[str]:
    norm = _normalize_label(label)
    tokens = _tokenize_label(norm)
    if "bank specific" in norm:
        tokens.add("bank-specific")
    if "bid ask" in norm:
        tokens.add("bid-ask")
    return tokens


def _classify_substantive_unresolved(
    source_label: Any,
    target_label: Any,
    source_type: str,
    target_type: str,
    source_context_entity_type: str = "none",
    target_context_entity_type: str = "none",
) -> tuple[str, str, str]:
    source_tokens = _substantive_label_tokens(source_label)
    target_tokens = _substantive_label_tokens(target_label)
    all_tokens = source_tokens | target_tokens
    source_norm = _normalize_label(source_label)
    target_norm = _normalize_label(target_label)
    combined_norm = f"{source_norm} {target_norm}".strip()
    type_set = {str(source_type), str(target_type)}
    context_entity_set = {str(source_context_entity_type), str(target_context_entity_type)}

    if (
        context_entity_set & {"event", "institution_actor", "geography_context"}
        or all_tokens & EVENT_CONTEXT_TERMS
        or any(term in combined_norm for term in {"world health organization", "sub-saharan", "country income"})
    ):
        return "event_institution_context", "medium", "label_pattern_event_context"
    if all_tokens & FINANCE_ATTRIBUTE_TERMS:
        return "finance_attribute_bundle", "medium", "label_pattern_finance_attribute"
    if all_tokens & COUNT_OBJECT_TERMS or source_norm.startswith("number of ") or target_norm.startswith("number of "):
        return "quantity_count_object", "low", "label_pattern_quantity_count"
    if "substantive_outcome" in type_set or all_tokens & POLICY_OUTCOME_TERMS:
        return "policy_outcome_or_boundary", "high", "outcome_or_policy_boundary"
    return "general_substantive_other", "medium", "default_substantive_other"


def _nonempty_jsonish(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text and text not in {"[]", "{}", "", "nan", "None"})


def _label_matches_terms(label: Any, terms: set[str]) -> bool:
    tokens = _tokenize_label(label)
    return bool(tokens & terms)


def _label_contains_any(label: Any, phrases: set[str]) -> bool:
    norm = _normalize_label(label)
    return any(phrase in norm for phrase in phrases)


def _load_context_alias_lookup(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    alias_df = pd.read_csv(path)
    required = {"raw_value", "context_type", "status", "normalized_display", "canonical_context_id"}
    if not required.issubset(set(alias_df.columns)):
        return {}
    lookup: dict[str, dict[str, str]] = {}
    for row in alias_df.itertuples(index=False):
        raw_value = str(getattr(row, "raw_value", "") or "").strip()
        if not raw_value:
            continue
        lookup[_normalize_label(raw_value)] = {
            "raw_value": raw_value,
            "normalized_display": str(getattr(row, "normalized_display", "") or "").strip(),
            "context_type": str(getattr(row, "context_type", "") or "").strip(),
            "granularity": str(getattr(row, "granularity", "") or "").strip(),
            "canonical_context_id": str(getattr(row, "canonical_context_id", "") or "").strip(),
            "status": str(getattr(row, "status", "") or "").strip(),
        }
    return lookup


def _load_reviewed_design_family_overrides(path: Path) -> pd.DataFrame:
    required = [
        "source_concept_id",
        "target_concept_id",
        "resolved_design_family",
        "resolution_confidence",
        "resolution_source",
        "resolution_reason",
    ]
    if not path.exists():
        return pd.DataFrame(columns=required)
    df = pd.read_csv(path)
    if not set(required).issubset(set(df.columns)):
        return pd.DataFrame(columns=required)
    out = df[required].copy()
    out["source_concept_id"] = out["source_concept_id"].astype(str)
    out["target_concept_id"] = out["target_concept_id"].astype(str)
    out["resolved_design_family"] = out["resolved_design_family"].map(_normalize_design_family)
    out["resolution_confidence"] = (
        pd.to_numeric(out["resolution_confidence"], errors="coerce").fillna(0.25).map(_bucket_taxonomy_confidence).astype(float)
    )
    out["resolution_source"] = out["resolution_source"].fillna("none").astype(str)
    out["resolution_reason"] = out["resolution_reason"].fillna("").astype(str)
    return out.drop_duplicates(["source_concept_id", "target_concept_id"], keep="last").reset_index(drop=True)


def _load_reviewed_policy_edge_semantics(path: Path) -> pd.DataFrame:
    required = [
        "source_concept_id",
        "target_concept_id",
        "policy_edge_semantic_type",
        "policy_edge_semantic_confidence",
        "policy_edge_semantic_reason",
        "regime_guardrail_decision",
        "regime_guardrail_reason",
    ]
    if not path.exists():
        return pd.DataFrame(columns=required)
    df = pd.read_csv(path)
    if not set(required).issubset(set(df.columns)):
        return pd.DataFrame(columns=required)
    out = df[required].copy()
    out["source_concept_id"] = out["source_concept_id"].astype(str)
    out["target_concept_id"] = out["target_concept_id"].astype(str)
    out["policy_edge_semantic_type"] = out["policy_edge_semantic_type"].fillna("none").astype(str)
    out["policy_edge_semantic_confidence"] = pd.to_numeric(out["policy_edge_semantic_confidence"], errors="coerce").fillna(0.0).astype(float)
    out["policy_edge_semantic_reason"] = out["policy_edge_semantic_reason"].fillna("").astype(str)
    out["regime_guardrail_decision"] = out["regime_guardrail_decision"].fillna("not_applicable").astype(str)
    out["regime_guardrail_reason"] = out["regime_guardrail_reason"].fillna("").astype(str)
    return out.drop_duplicates(["source_concept_id", "target_concept_id"], keep="last").reset_index(drop=True)


def _load_reviewed_relation_semantics(path: Path) -> pd.DataFrame:
    required = [
        "source_concept_id",
        "target_concept_id",
        "relation_semantic_type",
        "relation_semantic_confidence",
        "relation_semantic_reason",
        "resolution_source",
    ]
    if not path.exists():
        return pd.DataFrame(columns=required)
    df = pd.read_csv(path)
    if not set(required).issubset(set(df.columns)):
        return pd.DataFrame(columns=required)
    out = df[required].copy()
    out["source_concept_id"] = out["source_concept_id"].astype(str)
    out["target_concept_id"] = out["target_concept_id"].astype(str)
    out["relation_semantic_type"] = out["relation_semantic_type"].fillna("none").astype(str)
    out["relation_semantic_confidence"] = pd.to_numeric(out["relation_semantic_confidence"], errors="coerce").fillna(0.0).astype(float)
    out["relation_semantic_reason"] = out["relation_semantic_reason"].fillna("").astype(str)
    out["resolution_source"] = out["resolution_source"].fillna("none").astype(str)
    return out.drop_duplicates(["source_concept_id", "target_concept_id"], keep="last").reset_index(drop=True)


def _is_clean_alias_candidate(raw_value: str, payload: dict[str, str]) -> bool:
    status = str(payload.get("status", "") or "")
    if status not in CONTEXT_ALIAS_HIGH_CONFIDENCE_STATUSES:
        return False
    raw = str(raw_value or "").strip()
    normalized_display = str(payload.get("normalized_display", "") or "").strip()
    if not raw:
        return False
    if raw == normalized_display:
        return True
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]{1,9}", raw):
        return True
    return False


def _context_alias_match(
    raw_value: Any,
    context_alias_lookup: dict[str, dict[str, str]],
    *,
    allow_alias: bool,
) -> tuple[str, float, str] | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    payload = context_alias_lookup.get(_normalize_label(raw))
    payload_from_alias_table = payload is not None
    if payload is None:
        normalized = normalize_context_value(raw)
        if normalized.get("context_type") in CONTEXT_ALIAS_GEOGRAPHY_TYPES and normalized.get("status") in CONTEXT_ALIAS_HIGH_CONFIDENCE_STATUSES:
            payload = normalized
        else:
            return None
    context_type = str(payload.get("context_type", "") or "")
    status = str(payload.get("status", "") or "")
    if context_type not in CONTEXT_ALIAS_GEOGRAPHY_TYPES or context_type == "unknown":
        return None
    if allow_alias and not _is_clean_alias_candidate(raw, payload):
        return None
    if context_type == "country":
        return "geography_context", 1.0, "context_alias_country"
    if context_type == "region":
        return "geography_context", 1.0, "context_alias_region"
    if context_type == "bloc":
        return "geography_context", 1.0, "context_alias_bloc"
    if context_type in {"country_or_place", "country_or_territory"}:
        if not payload_from_alias_table:
            return None
        confidence = 0.75 if status in CONTEXT_ALIAS_LOW_CONFIDENCE_STATUSES or context_type == "country_or_place" else 1.0
        return "geography_context", confidence, "context_alias_country_or_place"
    return None


def _infer_context_entity_type(
    label: Any,
    aliases_json: Any,
    bucket_hint: Any,
    context_alias_lookup: dict[str, dict[str, str]],
) -> tuple[str, float, str]:
    del bucket_hint
    label_text = str(label or "")

    if _label_matches_terms(label_text, EVENT_ENTITY_TERMS):
        return "event", 1.0, "label_pattern_event"
    if _label_matches_terms(label_text, INSTITUTION_ENTITY_TERMS):
        return "institution_actor", 1.0, "label_pattern_institution"
    if _label_matches_terms(label_text, GEOGRAPHY_ENTITY_TERMS):
        return "geography_context", 1.0, "label_pattern_geography"
    label_match = _context_alias_match(label_text, context_alias_lookup, allow_alias=False)
    if label_match is not None:
        return label_match
    for item in _parse_json_list(aliases_json):
        alias_match = _context_alias_match(item, context_alias_lookup, allow_alias=True)
        if alias_match is not None:
            return alias_match
    return "none", 0.5, "default_none"


def _apply_concept_type_tags(
    canonical_df: pd.DataFrame,
    family_seed_df: pd.DataFrame,
    context_alias_lookup: dict[str, dict[str, str]],
) -> pd.DataFrame:
    out = canonical_df.copy()
    family_type_lookup = family_seed_df.set_index("member_concept_id")["family_type"].astype(str).to_dict()

    def infer(row: pd.Series) -> tuple[str, float, str]:
        label = str(row.get("preferred_label", "") or "")
        aliases = _parse_json_list(row.get("aliases_json", "[]"))
        alias_text = " ".join(str(item) for item in aliases)
        combined_text = f"{label} {alias_text}".strip()
        norm = _normalize_label(combined_text)
        bucket_hint = _normalize_label(row.get("bucket_hint", ""))
        concept_id = str(row.get("concept_id", "") or "")
        reviewed_family_type = family_type_lookup.get(concept_id, "")

        if norm in METADATA_CONTAINER_EXACT or _label_contains_any(norm, METADATA_CONTAINER_EXACT):
            return "metadata_container", 1.0, "label_pattern_metadata"
        if norm in DATA_ARTIFACT_EXACT or _label_contains_any(norm, DATA_ARTIFACT_EXACT):
            return "data_artifact", 1.0, "label_pattern_data_artifact"
        if _label_matches_terms(combined_text, METHOD_TERMS):
            return "method", 1.0, "label_pattern_method"
        if reviewed_family_type == "outcome_family":
            return "substantive_outcome", 0.75, "reviewed_family_outcome"
        if bucket_hint in OUTCOME_BUCKET_HINTS or _label_matches_terms(combined_text, OUTCOME_CONCEPT_TOKENS):
            return "substantive_outcome", 0.75, "bucket_hint_fallback"
        if reviewed_family_type == "mechanism_family":
            return "substantive_mechanism", 0.75, "reviewed_family_mechanism"
        return "substantive_mechanism", 0.5, "default_mechanism_fallback"

    inferred = out.apply(infer, axis=1)
    out["primary_concept_type"] = inferred.map(lambda item: item[0])
    out["concept_type_confidence"] = inferred.map(lambda item: item[1]).astype(float)
    out["concept_type_reason"] = inferred.map(lambda item: item[2])
    context_inferred = out.apply(
        lambda row: _infer_context_entity_type(
            row.get("preferred_label", ""),
            row.get("aliases_json", "[]"),
            row.get("bucket_hint", ""),
            context_alias_lookup,
        ),
        axis=1,
    )
    out["context_entity_type"] = context_inferred.map(lambda item: item[0])
    out["context_entity_confidence"] = context_inferred.map(lambda item: item[1]).astype(float)
    out["context_entity_reason"] = context_inferred.map(lambda item: item[2])
    return out


def _load_sql_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)


def _load_canonical_concepts(concept_db_path: Path, corpus_df: pd.DataFrame, shortlist_df: pd.DataFrame) -> pd.DataFrame:
    conn = sqlite3.connect(f"file:{concept_db_path}?mode=ro", uri=True)
    try:
        nodes_df = _load_sql_table(conn, "nodes")
        node_details_df = _load_sql_table(conn, "node_details")
    finally:
        conn.close()

    nodes_df = nodes_df.rename(columns={"code": "concept_id", "label": "node_label", "bucket_hint": "node_bucket_hint"})
    canonical = node_details_df.merge(nodes_df, on="concept_id", how="outer")
    canonical["preferred_label"] = canonical["preferred_label"].fillna(canonical["node_label"]).fillna(canonical["concept_id"])
    canonical["bucket_hint"] = canonical["bucket_hint"].fillna(canonical["node_bucket_hint"]).fillna("")
    canonical["aliases_json"] = canonical["aliases_json"].fillna("[]")
    canonical["mapping_sources_json"] = canonical["mapping_sources_json"].fillna("[]")
    canonical["bucket_profile_json"] = canonical["bucket_profile_json"].fillna("[]")
    canonical["top_countries"] = canonical["top_countries"].fillna("[]")
    canonical["top_units"] = canonical["top_units"].fillna("[]")
    canonical["representative_contexts_json"] = canonical["representative_contexts_json"].fillna("[]")
    canonical["representative_years_json"] = canonical["representative_years_json"].fillna("[]")
    canonical["mapping_variant"] = canonical["mapping_variant"].fillna("unknown")
    canonical["instance_support"] = pd.to_numeric(canonical["instance_support"], errors="coerce").fillna(0).astype(int)
    canonical["distinct_paper_support"] = pd.to_numeric(canonical["distinct_paper_support"], errors="coerce").fillna(0).astype(int)
    canonical["mean_confidence"] = pd.to_numeric(canonical["mean_confidence"], errors="coerce").fillna(1.0).astype(float)
    canonical["low_confidence_share"] = pd.to_numeric(canonical["low_confidence_share"], errors="coerce").fillna(0.0).astype(float)
    canonical = canonical[
        [
            "concept_id",
            "preferred_label",
            "aliases_json",
            "instance_support",
            "distinct_paper_support",
            "mean_confidence",
            "low_confidence_share",
            "mapping_sources_json",
            "bucket_hint",
            "bucket_profile_json",
            "top_countries",
            "top_units",
            "representative_contexts_json",
            "representative_years_json",
            "mapping_variant",
        ]
    ].drop_duplicates("concept_id")

    active_ids = set(corpus_df["src_code"].astype(str)).union(set(corpus_df["dst_code"].astype(str)))
    shortlist_ids: set[str] = set()
    for pair_key in shortlist_df["pair_key"].dropna().astype(str):
        left, right = pair_key.split("__", 1)
        shortlist_ids.add(left)
        shortlist_ids.add(right)
    needed_ids = active_ids.union(shortlist_ids)
    existing_ids = set(canonical["concept_id"].astype(str))
    missing_ids = sorted(needed_ids - existing_ids)
    if missing_ids:
        label_lookup = {}
        for row in corpus_df[["src_code", "src_label"]].drop_duplicates().itertuples(index=False):
            label_lookup.setdefault(str(row.src_code), str(row.src_label))
        for row in corpus_df[["dst_code", "dst_label"]].drop_duplicates().itertuples(index=False):
            label_lookup.setdefault(str(row.dst_code), str(row.dst_label))
        fallback = pd.DataFrame(
            [
                {
                    "concept_id": concept_id,
                    "preferred_label": label_lookup.get(concept_id, concept_id),
                    "aliases_json": json.dumps([label_lookup.get(concept_id, concept_id)]),
                    "instance_support": 0,
                    "distinct_paper_support": 0,
                    "mean_confidence": 1.0,
                    "low_confidence_share": 0.0,
                    "mapping_sources_json": json.dumps([{"value": "corpus_fallback", "count": 1}]),
                    "bucket_hint": "",
                    "bucket_profile_json": "[]",
                    "top_countries": "[]",
                    "top_units": "[]",
                    "representative_contexts_json": "[]",
                    "representative_years_json": "[]",
                    "mapping_variant": "corpus_fallback",
                }
                for concept_id in missing_ids
            ]
        )
        canonical = pd.concat([canonical, fallback], ignore_index=True)
    return canonical.sort_values(["concept_id"]).reset_index(drop=True)


def _build_family_seed_table(canonical_df: pd.DataFrame) -> pd.DataFrame:
    label_lookup = canonical_df.set_index("concept_id")["preferred_label"].astype(str).to_dict()
    rows: list[dict[str, Any]] = []
    for spec in REVIEWED_FAMILY_SPECS:
        for concept_id in spec["member_concept_ids"]:
            rows.append(
                {
                    "family_id": spec["family_id"],
                    "family_label": spec["family_label"],
                    "family_type": spec["family_type"],
                    "member_concept_id": concept_id,
                    "member_label": label_lookup.get(concept_id, concept_id),
                    "assignment_reason": spec["assignment_reason"],
                    "do_not_merge_note": spec["do_not_merge_note"],
                    "review_status": "approved",
                }
            )
    return pd.DataFrame(rows).sort_values(["family_id", "member_concept_id"]).reset_index(drop=True)


def _build_concept_families(canonical_df: pd.DataFrame, family_seed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seed_lookup = family_seed_df.set_index("member_concept_id")[
        ["family_id", "family_label", "family_type"]
    ].to_dict(orient="index")
    label_lookup = canonical_df.set_index("concept_id")["preferred_label"].astype(str).to_dict()
    for concept_id, concept_label in label_lookup.items():
        if concept_id in seed_lookup:
            seed = seed_lookup[concept_id]
            rows.append(
                {
                    "family_id": seed["family_id"],
                    "family_label": seed["family_label"],
                    "family_type": seed["family_type"],
                    "member_concept_id": concept_id,
                    "member_label": concept_label,
                    "family_assignment_source": "reviewed_seed",
                }
            )
        else:
            rows.append(
                {
                    "family_id": f"self_family__{concept_id}",
                    "family_label": concept_label,
                    "family_type": "self_family",
                    "member_concept_id": concept_id,
                    "member_label": concept_label,
                    "family_assignment_source": "self_family_fallback",
                }
            )
    return pd.DataFrame(rows).sort_values(["family_id", "member_concept_id"]).reset_index(drop=True)


def _build_mention_proxy(corpus_df: pd.DataFrame, canonical_df: pd.DataFrame, family_df: pd.DataFrame) -> pd.DataFrame:
    family_lookup = family_df.set_index("member_concept_id")[["family_id", "family_label"]].to_dict(orient="index")
    label_lookup = canonical_df.set_index("concept_id")["preferred_label"].astype(str).to_dict()

    base_cols = ["paper_id", "year", "title", "venue", "source", "edge_kind", "src_code", "dst_code"]

    src = corpus_df[base_cols + ["src_label"]].copy()
    src["endpoint_role"] = "source"
    src["raw_label"] = src["src_label"].astype(str)
    src["concept_id"] = src["src_code"].astype(str)

    dst = corpus_df[base_cols + ["dst_label"]].copy()
    dst["endpoint_role"] = "target"
    dst["raw_label"] = dst["dst_label"].astype(str)
    dst["concept_id"] = dst["dst_code"].astype(str)

    mentions = pd.concat([src, dst], ignore_index=True)
    mentions["canonical_label"] = mentions["concept_id"].map(label_lookup).fillna(mentions["raw_label"])
    mentions["normalized_label"] = mentions["raw_label"].map(_normalize_label)
    mentions["mapping_kind"] = "exact_canonical_proxy"
    mentions["mapping_source"] = "hybrid_corpus_active_baseline"
    mentions["mapping_confidence"] = 1.0
    mentions["family_id"] = mentions["concept_id"].map(lambda cid: family_lookup.get(cid, {}).get("family_id", f"self_family__{cid}"))
    mentions["family_label"] = mentions["concept_id"].map(lambda cid: family_lookup.get(cid, {}).get("family_label", label_lookup.get(cid, cid)))
    mentions["mention_proxy_id"] = (
        mentions["paper_id"].astype(str)
        + "__"
        + mentions["src_code"].astype(str)
        + "__"
        + mentions["dst_code"].astype(str)
        + "__"
        + mentions["edge_kind"].astype(str)
        + "__"
        + mentions["endpoint_role"]
    )
    return mentions[
        [
            "mention_proxy_id",
            "paper_id",
            "year",
            "title",
            "venue",
            "source",
            "endpoint_role",
            "raw_label",
            "normalized_label",
            "concept_id",
            "canonical_label",
            "mapping_kind",
            "mapping_source",
            "mapping_confidence",
            "family_id",
            "family_label",
        ]
    ].reset_index(drop=True)


def _build_mapping_table(mention_proxy_df: pd.DataFrame) -> pd.DataFrame:
    mappings = mention_proxy_df[
        [
            "mention_proxy_id",
            "concept_id",
            "mapping_source",
            "mapping_confidence",
            "family_id",
        ]
    ].copy()
    mappings["mapping_kind"] = "exact"
    return mappings[
        [
            "mention_proxy_id",
            "concept_id",
            "mapping_kind",
            "mapping_source",
            "mapping_confidence",
            "family_id",
        ]
    ].reset_index(drop=True)


def _build_context_signatures(canonical_df: pd.DataFrame) -> pd.DataFrame:
    context_df = canonical_df[
        [
            "concept_id",
            "top_countries",
            "top_units",
            "representative_contexts_json",
            "representative_years_json",
            "bucket_profile_json",
            "distinct_paper_support",
        ]
    ].copy()
    context_df = context_df.rename(
        columns={
            "top_countries": "top_geographies_json",
            "top_units": "top_units_json",
            "distinct_paper_support": "context_support",
        }
    )
    for col in [
        "top_geographies_json",
        "top_units_json",
        "representative_contexts_json",
        "representative_years_json",
        "bucket_profile_json",
    ]:
        context_df[col] = context_df[col].map(_json_text)
    return context_df.sort_values(["concept_id"]).reset_index(drop=True)


def _load_review_note_mentions(concept_labels: dict[str, str]) -> dict[str, set[str]]:
    note_hits: dict[str, set[str]] = defaultdict(set)
    paths: list[Path] = []
    for pattern in REVIEW_NOTE_PATTERNS:
        paths.extend(sorted(Path(".").glob(pattern)))
    unique_paths = []
    seen_paths: set[Path] = set()
    for path in paths:
        if path in seen_paths or not path.exists():
            continue
        seen_paths.add(path)
        unique_paths.append(path)
    for path in unique_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        for concept_id, label in concept_labels.items():
            norm_label = _normalize_label(label)
            if len(norm_label) < 4:
                continue
            if norm_label in text:
                note_hits[concept_id].add(str(path))
    return note_hits


def _family_type_from_tokens(tokens: set[str]) -> str:
    if tokens & OUTCOME_FAMILY_TOKENS:
        return "outcome_family"
    if tokens & INSTITUTION_FAMILY_TOKENS:
        return "institution_family"
    if tokens & METHOD_FAMILY_TOKENS:
        return "method_family"
    if tokens & CONTEXT_FAMILY_TOKENS:
        return "context_family"
    return "mechanism_family"


def _candidate_family_label(member_labels: list[str], theme_tags: set[str]) -> str:
    token_counter: Counter[str] = Counter()
    for label in member_labels:
        token_counter.update(_tokenize_label(label))
    shared_tokens = [token for token, count in token_counter.items() if count >= 2]
    if shared_tokens:
        top_tokens = sorted(shared_tokens, key=lambda token: (-token_counter[token], token))[:2]
        return f"{' '.join(top_tokens)} concepts"
    clean_tags = [tag.replace("_", " ") for tag in sorted(theme_tags) if tag and tag != "nan"]
    if clean_tags:
        return f"{clean_tags[0]} concepts"
    if member_labels:
        return f"{member_labels[0]} related concepts"
    return "candidate family"


def _build_family_candidates(
    canonical_df: pd.DataFrame,
    enriched_df: pd.DataFrame,
    family_seed_df: pd.DataFrame,
    routed_shortlist_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    label_lookup = canonical_df.set_index("concept_id")["preferred_label"].astype(str).to_dict()
    aliases_lookup = canonical_df.set_index("concept_id")["aliases_json"].to_dict()
    bucket_hint_lookup = canonical_df.set_index("concept_id")["bucket_hint"].fillna("").astype(str).to_dict()
    bucket_profile_lookup = canonical_df.set_index("concept_id")["bucket_profile_json"].to_dict()

    routed_df = pd.read_csv(routed_shortlist_path) if routed_shortlist_path.exists() else pd.DataFrame()
    active_seed_members = set(family_seed_df["member_concept_id"].astype(str))

    partner_sets: dict[str, set[str]] = defaultdict(set)
    theme_sets: dict[str, set[str]] = defaultdict(set)
    usage_counts: Counter[str] = Counter()

    for row in enriched_df[["source_concept_id", "target_concept_id", "source_bucket_hint", "target_bucket_hint"]].itertuples(index=False):
        src = str(row.source_concept_id)
        dst = str(row.target_concept_id)
        partner_sets[src].add(dst)
        partner_sets[dst].add(src)
        usage_counts[src] += 1
        usage_counts[dst] += 1

    for col in ["source_theme", "target_theme", "source_family", "target_family"]:
        if col in enriched_df.columns:
            source_or_target = "source_concept_id" if col.startswith("source_") else "target_concept_id"
            for row in enriched_df[[source_or_target, col]].dropna().itertuples(index=False):
                concept_id = str(getattr(row, source_or_target))
                tag = str(getattr(row, col)).strip()
                if tag:
                    theme_sets[concept_id].add(tag)

    if not routed_df.empty:
        for row in routed_df[["pair_key", "routed_object_family"]].dropna().itertuples(index=False):
            src, dst = str(row.pair_key).split("__", 1)
            tag = f"route::{row.routed_object_family}"
            theme_sets[src].add(tag)
            theme_sets[dst].add(tag)

    # Keep the candidate queue focused on concepts that do not already belong to
    # an active reviewed family.
    concept_ids = sorted(set(usage_counts) - active_seed_members)
    note_hits = _load_review_note_mentions({concept_id: label_lookup.get(concept_id, concept_id) for concept_id in concept_ids})

    candidate_pairs: list[dict[str, Any]] = []
    pair_edges: list[tuple[str, str]] = []
    for left_id, right_id in combinations(concept_ids, 2):
        if left_id in active_seed_members and right_id in active_seed_members:
            continue
        left_label = label_lookup.get(left_id, left_id)
        right_label = label_lookup.get(right_id, right_id)
        left_tokens = _tokenize_label(left_label)
        right_tokens = _tokenize_label(right_label)
        left_alias_tokens = _aliases_tokens(aliases_lookup.get(left_id, "[]"))
        right_alias_tokens = _aliases_tokens(aliases_lookup.get(right_id, "[]"))
        semantic_score = (
            0.45 * _jaccard(left_tokens, right_tokens)
            + 0.20 * _jaccard(left_alias_tokens, right_alias_tokens)
            + 0.15 * float(bucket_hint_lookup.get(left_id, "") == bucket_hint_lookup.get(right_id, "") and bucket_hint_lookup.get(left_id, "") != "")
            + 0.20 * _jaccard(_bucket_values(bucket_profile_lookup.get(left_id, "[]")), _bucket_values(bucket_profile_lookup.get(right_id, "[]")))
        )
        collision_score = (
            0.45 * _jaccard(partner_sets.get(left_id, set()), partner_sets.get(right_id, set()))
            + 0.25 * _jaccard(theme_sets.get(left_id, set()), theme_sets.get(right_id, set()))
            + 0.30 * min(float(len(note_hits.get(left_id, set()) & note_hits.get(right_id, set()))) / 3.0, 1.0)
        )
        combined_score = 0.6 * semantic_score + 0.4 * collision_score
        if combined_score < 0.28 or (semantic_score < 0.15 and collision_score < 0.20):
            continue
        candidate_pairs.append(
            {
                "left_concept_id": left_id,
                "left_label": left_label,
                "right_concept_id": right_id,
                "right_label": right_label,
                "semantic_score": round(semantic_score, 4),
                "collision_score": round(collision_score, 4),
                "combined_score": round(combined_score, 4),
                "shared_note_count": int(len(note_hits.get(left_id, set()) & note_hits.get(right_id, set()))),
            }
        )
        pair_edges.append((left_id, right_id))

    adjacency: dict[str, set[str]] = defaultdict(set)
    for left_id, right_id in pair_edges:
        adjacency[left_id].add(right_id)
        adjacency[right_id].add(left_id)

    visited: set[str] = set()
    candidate_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    family_index = 1
    pair_lookup = {
        tuple(sorted((row["left_concept_id"], row["right_concept_id"]))): row
        for row in candidate_pairs
    }

    for concept_id in concept_ids:
        if concept_id in visited or concept_id not in adjacency:
            continue
        stack = [concept_id]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency.get(current, set()) - visited))
        if len(component) < 2 or len(component) > 8:
            continue
        member_labels = [label_lookup.get(cid, cid) for cid in component]
        theme_tags = set().union(*(theme_sets.get(cid, set()) for cid in component))
        family_label = _candidate_family_label(member_labels, theme_tags)
        candidate_family_id = f"candidate_family__{family_index:03d}"
        family_index += 1
        component_tokens = set().union(*(_tokenize_label(label) for label in member_labels))
        family_type = _family_type_from_tokens(component_tokens)

        member_pair_rows = [
            pair_lookup[tuple(sorted((left_id, right_id)))]
            for left_id, right_id in combinations(sorted(component), 2)
            if tuple(sorted((left_id, right_id))) in pair_lookup
        ]
        family_semantic_score = sum(row["semantic_score"] for row in member_pair_rows) / float(len(member_pair_rows) or 1)
        family_collision_score = sum(row["collision_score"] for row in member_pair_rows) / float(len(member_pair_rows) or 1)
        assignment_reason = (
            f"Generated from shortlist collisions and semantic overlap; component size {len(component)} with mean semantic score {family_semantic_score:.2f} and mean collision score {family_collision_score:.2f}."
        )
        do_not_merge_note = "Candidate family only; keep member concepts separate unless a later review explicitly promotes a synonym relation."

        for member_id in sorted(component):
            candidate_rows.append(
                {
                    "candidate_family_id": candidate_family_id,
                    "member_concept_id": member_id,
                    "member_label": label_lookup.get(member_id, member_id),
                    "proposed_family_label": family_label,
                    "family_type": family_type,
                    "semantic_score": round(family_semantic_score, 4),
                    "collision_score": round(family_collision_score, 4),
                    "combined_score": round(0.6 * family_semantic_score + 0.4 * family_collision_score, 4),
                    "do_not_merge_note": do_not_merge_note,
                    "assignment_reason": assignment_reason,
                    "candidate_status": "proposed",
                }
            )
        for pair_row in member_pair_rows:
            relation_rows.append(
                {
                    "left_concept_id": pair_row["left_concept_id"],
                    "left_label": pair_row["left_label"],
                    "right_concept_id": pair_row["right_concept_id"],
                    "right_label": pair_row["right_label"],
                    "relation_type": "related",
                    "relation_source": "candidate_generator",
                    "relation_confidence": pair_row["combined_score"],
                    "proposed_family_id": candidate_family_id,
                    "proposed_family_label": family_label,
                    "relation_note": "Generated candidate relation from semantic overlap and repeated shortlist/review collisions.",
                    "review_status": "pending_review",
                }
            )

    if not candidate_rows:
        theme_member_map: dict[str, list[str]] = defaultdict(list)
        for concept_id in concept_ids:
            for tag in theme_sets.get(concept_id, set()):
                if not tag or tag == "other" or tag.startswith("route::"):
                    continue
                theme_member_map[tag].append(concept_id)

        seen_member_sets: set[tuple[str, ...]] = set()
        for theme_tag, members in sorted(theme_member_map.items()):
            unique_members = sorted(set(members), key=lambda cid: (-usage_counts.get(cid, 0), label_lookup.get(cid, cid)))
            if len(unique_members) < 2:
                continue
            if len(unique_members) > 6:
                unique_members = unique_members[:6]
            member_key = tuple(sorted(unique_members))
            if member_key in seen_member_sets:
                continue
            seen_member_sets.add(member_key)
            member_labels = [label_lookup.get(cid, cid) for cid in unique_members]
            pair_stats = []
            for left_id, right_id in combinations(unique_members, 2):
                left_tokens = _tokenize_label(label_lookup.get(left_id, left_id))
                right_tokens = _tokenize_label(label_lookup.get(right_id, right_id))
                left_alias_tokens = _aliases_tokens(aliases_lookup.get(left_id, "[]"))
                right_alias_tokens = _aliases_tokens(aliases_lookup.get(right_id, "[]"))
                semantic_score = (
                    0.55 * _jaccard(left_tokens, right_tokens)
                    + 0.20 * _jaccard(left_alias_tokens, right_alias_tokens)
                    + 0.25 * float(bucket_hint_lookup.get(left_id, "") == bucket_hint_lookup.get(right_id, "") and bucket_hint_lookup.get(left_id, "") != "")
                )
                collision_score = (
                    0.55 * _jaccard(partner_sets.get(left_id, set()), partner_sets.get(right_id, set()))
                    + 0.45 * _jaccard(theme_sets.get(left_id, set()), theme_sets.get(right_id, set()))
                )
                pair_stats.append((semantic_score, collision_score, left_id, right_id))
            if not pair_stats:
                continue
            family_semantic_score = sum(item[0] for item in pair_stats) / float(len(pair_stats))
            family_collision_score = sum(item[1] for item in pair_stats) / float(len(pair_stats))
            combined_score = 0.6 * family_semantic_score + 0.4 * family_collision_score
            if combined_score < 0.12:
                continue
            candidate_family_id = f"candidate_family__{family_index:03d}"
            family_index += 1
            family_label = theme_tag.replace("_", " ") + " concepts"
            family_type = _family_type_from_tokens(set().union(*(_tokenize_label(label) for label in member_labels)))
            assignment_reason = (
                f"Theme-based fallback candidate from repeated shortlist grouping under `{theme_tag}` with mean semantic score {family_semantic_score:.2f} and mean collision score {family_collision_score:.2f}."
            )
            do_not_merge_note = "Theme-based family candidate only; review concept boundaries before promoting to an active family."
            for member_id in unique_members:
                candidate_rows.append(
                    {
                        "candidate_family_id": candidate_family_id,
                        "member_concept_id": member_id,
                        "member_label": label_lookup.get(member_id, member_id),
                        "proposed_family_label": family_label,
                        "family_type": family_type,
                        "semantic_score": round(family_semantic_score, 4),
                        "collision_score": round(family_collision_score, 4),
                        "combined_score": round(combined_score, 4),
                        "do_not_merge_note": do_not_merge_note,
                        "assignment_reason": assignment_reason,
                        "candidate_status": "theme_proposed",
                    }
                )
            for semantic_score, collision_score, left_id, right_id in pair_stats:
                relation_rows.append(
                    {
                        "left_concept_id": left_id,
                        "left_label": label_lookup.get(left_id, left_id),
                        "right_concept_id": right_id,
                        "right_label": label_lookup.get(right_id, right_id),
                        "relation_type": "related",
                        "relation_source": "theme_fallback",
                        "relation_confidence": round(0.6 * semantic_score + 0.4 * collision_score, 4),
                        "proposed_family_id": candidate_family_id,
                        "proposed_family_label": family_label,
                        "relation_note": "Theme-based fallback candidate from repeated shortlist grouping.",
                        "review_status": "pending_review",
                    }
                )

    candidate_df = pd.DataFrame(candidate_rows).sort_values(
        ["combined_score", "collision_score", "candidate_family_id", "member_label"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True) if candidate_rows else pd.DataFrame(columns=[
        "candidate_family_id",
        "member_concept_id",
        "member_label",
        "proposed_family_label",
        "family_type",
        "semantic_score",
        "collision_score",
        "combined_score",
        "do_not_merge_note",
        "assignment_reason",
        "candidate_status",
    ])
    relation_df = pd.DataFrame(relation_rows)
    return candidate_df, relation_df


def _build_edge_evidence_profiles(
    corpus_df: pd.DataFrame,
    concept_db_path: Path,
    canonical_df: pd.DataFrame,
    reviewed_design_df: pd.DataFrame,
    reviewed_policy_df: pd.DataFrame,
    reviewed_relation_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = corpus_df[
        [
            "src_code",
            "dst_code",
            "paper_id",
            "edge_instance_count",
            "weight",
            "stability",
            "evidence_type",
            "relation_type",
            "causal_presentation",
        ]
    ].copy()
    instance_taxonomy = frame.copy()
    taxonomy_payload = instance_taxonomy.apply(_taxonomy_for_instance, axis=1)
    instance_taxonomy["evidence_mode"] = taxonomy_payload.map(lambda payload: payload["evidence_mode"])
    instance_taxonomy["design_family"] = taxonomy_payload.map(lambda payload: payload["design_family"])
    instance_taxonomy["identification_strength"] = taxonomy_payload.map(lambda payload: payload["identification_strength"])
    instance_taxonomy["taxonomy_confidence"] = taxonomy_payload.map(lambda payload: payload["taxonomy_confidence"]).astype(float)
    instance_taxonomy["unknown_reason"] = taxonomy_payload.map(lambda payload: payload["unknown_reason"])
    frame["edge_instance_count"] = pd.to_numeric(frame["edge_instance_count"], errors="coerce").fillna(0).astype(int)
    frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce").fillna(0.0).astype(float)
    frame["stability"] = pd.to_numeric(frame["stability"], errors="coerce").fillna(0.0).astype(float)
    frame["weighted_stability"] = frame["stability"] * frame["edge_instance_count"].clip(lower=1)
    grouped = (
        frame.groupby(["src_code", "dst_code"], as_index=False)
        .agg(
            edge_instance_count=("edge_instance_count", "sum"),
            weight=("weight", "sum"),
            distinct_paper_support=("paper_id", "nunique"),
            weighted_stability=("weighted_stability", "sum"),
        )
        .rename(columns={"src_code": "source_concept_id", "dst_code": "target_concept_id"})
    )
    dominant_evidence = _dominant_by_pair(frame, "evidence_type", "dominant_evidence_type")
    dominant_relation = _dominant_by_pair(frame, "relation_type", "dominant_relation_type")
    dominant_causal = _dominant_by_pair(frame, "causal_presentation", "dominant_causal_presentation")
    grouped = grouped.merge(dominant_evidence, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_relation, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_causal, on=["source_concept_id", "target_concept_id"], how="left")
    grouped["dominant_evidence_type"] = grouped["dominant_evidence_type"].fillna("unknown")
    grouped["dominant_relation_type"] = grouped["dominant_relation_type"].fillna("unknown")
    grouped["dominant_causal_presentation"] = grouped["dominant_causal_presentation"].fillna("unknown")
    denom = grouped["edge_instance_count"].clip(lower=1).astype(float)
    grouped["stability"] = grouped["weighted_stability"] / denom
    taxonomy_summary = (
        instance_taxonomy.groupby(["src_code", "dst_code"], as_index=False)
        .agg(
            taxonomy_confidence=("taxonomy_confidence", "mean"),
            unresolved_share=(
                "design_family",
                lambda s: float(pd.Series(s).astype(str).isin({"unknown", "do_not_know", "other"}).mean()),
            ),
        )
        .rename(columns={"src_code": "source_concept_id", "dst_code": "target_concept_id"})
    )
    dominant_design = _dominant_by_pair(instance_taxonomy.rename(columns={"design_family": "_design"}), "_design", "design_family")
    dominant_mode = _dominant_by_pair(instance_taxonomy.rename(columns={"evidence_mode": "_mode"}), "_mode", "evidence_mode")
    dominant_strength = _dominant_by_pair(instance_taxonomy.rename(columns={"identification_strength": "_strength"}), "_strength", "identification_strength")
    dominant_unknown_reason = _dominant_by_pair(instance_taxonomy.rename(columns={"unknown_reason": "_reason"}), "_reason", "unknown_reason")
    grouped = grouped.merge(taxonomy_summary, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_design, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_mode, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_strength, on=["source_concept_id", "target_concept_id"], how="left")
    grouped = grouped.merge(dominant_unknown_reason, on=["source_concept_id", "target_concept_id"], how="left")
    grouped["edge_evidence_mode"] = grouped["evidence_mode"].fillna("unknown").astype(str)
    grouped["edge_design_family"] = grouped["design_family"].fillna("unknown").astype(str)
    grouped["identification_strength"] = grouped["identification_strength"].fillna("unknown").astype(str)
    grouped["taxonomy_confidence"] = grouped["taxonomy_confidence"].map(_bucket_taxonomy_confidence).astype(float)
    grouped["unknown_reason"] = grouped["unknown_reason"].fillna("").astype(str)
    conflicting_mask = grouped["edge_design_family"].eq("unknown") & grouped["dominant_causal_presentation"].isin(["explicit_causal", "implicit_causal"])
    grouped.loc[conflicting_mask & grouped["unknown_reason"].eq(""), "unknown_reason"] = "conflicting_signals"
    grouped = _apply_reviewed_evidence_overrides(grouped)
    grouped = _apply_reviewed_design_family_resolutions(grouped, reviewed_design_df)
    grouped["taxonomy_confidence"] = grouped["taxonomy_confidence"].map(_bucket_taxonomy_confidence).astype(float)
    unresolved_summary_mask = grouped["edge_design_family"].astype(str).isin({"unknown", "do_not_know", "other"})
    grouped.loc[unresolved_summary_mask, "taxonomy_confidence"] = (
        pd.to_numeric(grouped.loc[unresolved_summary_mask, "taxonomy_confidence"], errors="coerce")
        .fillna(0.25)
        .clip(upper=0.5)
        .map(_bucket_taxonomy_confidence)
        .astype(float)
    )

    conn = sqlite3.connect(f"file:{concept_db_path}?mode=ro", uri=True)
    try:
        edge_profiles = _load_sql_table(conn, "concept_edge_profiles")
        edge_contexts = _load_sql_table(conn, "concept_edge_contexts")
    finally:
        conn.close()

    merged = grouped.merge(edge_profiles, on=["source_concept_id", "target_concept_id"], how="left")
    merged = merged.merge(edge_contexts, on=["source_concept_id", "target_concept_id"], how="left")
    for col in [
        "directionality_json",
        "relationship_type_json",
        "causal_presentation_json",
        "edge_role_json",
        "claim_status_json",
        "dominant_countries_json",
        "dominant_units_json",
        "dominant_years_json",
        "context_note_examples_json",
    ]:
        merged[col] = merged[col].fillna("[]")
    merged = _attach_reviewed_policy_edge_semantics(merged, reviewed_policy_df)
    merged = _attach_reviewed_relation_semantics(merged, reviewed_relation_df)
    keep_cols = [
        "source_concept_id",
        "target_concept_id",
        "edge_instance_count",
        "weight",
        "stability",
        "distinct_paper_support",
        "edge_evidence_mode",
        "edge_design_family",
        "edge_design_family_original",
        "edge_design_family_resolution_source",
        "edge_design_family_resolution_reason",
        "edge_design_family_resolution_confidence",
        "identification_strength",
        "taxonomy_confidence",
        "unknown_reason",
        "dominant_evidence_type",
        "dominant_relation_type",
        "dominant_causal_presentation",
        "directionality_json",
        "relationship_type_json",
        "causal_presentation_json",
        "edge_role_json",
        "claim_status_json",
        "dominant_countries_json",
        "dominant_units_json",
        "dominant_years_json",
        "context_note_examples_json",
        "policy_edge_semantic_type",
        "policy_edge_semantic_confidence",
        "policy_edge_semantic_reason",
        "regime_guardrail_decision",
        "regime_guardrail_reason",
        "edge_relation_semantic_type",
        "edge_relation_semantic_confidence",
        "edge_relation_semantic_reason",
    ]
    merged = merged[keep_cols].reset_index(drop=True)
    concept_type_lookup = canonical_df.set_index("concept_id")["primary_concept_type"].astype(str).to_dict()
    context_entity_lookup = canonical_df.set_index("concept_id")["context_entity_type"].astype(str).to_dict()
    label_lookup = canonical_df.set_index("concept_id")["preferred_label"].astype(str).to_dict()
    unknown_audit = merged[
        merged["edge_design_family"].astype(str).isin({"unknown", "do_not_know", "other"})
        | merged["unknown_reason"].astype(str).ne("")
    ].copy()
    unknown_audit["source_label"] = unknown_audit["source_concept_id"].map(label_lookup).fillna(unknown_audit["source_concept_id"])
    unknown_audit["target_label"] = unknown_audit["target_concept_id"].map(label_lookup).fillna(unknown_audit["target_concept_id"])
    unknown_audit["source_primary_concept_type"] = unknown_audit["source_concept_id"].map(concept_type_lookup).fillna("substantive_mechanism")
    unknown_audit["target_primary_concept_type"] = unknown_audit["target_concept_id"].map(concept_type_lookup).fillna("substantive_mechanism")
    unknown_audit["source_context_entity_type"] = unknown_audit["source_concept_id"].map(context_entity_lookup).fillna("none")
    unknown_audit["target_context_entity_type"] = unknown_audit["target_concept_id"].map(context_entity_lookup).fillna("none")
    unknown_audit["audit_bucket"] = unknown_audit.apply(
        lambda row: _assign_audit_bucket(row["source_primary_concept_type"], row["target_primary_concept_type"]),
        axis=1,
    )
    substantive_meta = unknown_audit.apply(
        lambda row: _classify_substantive_unresolved(
            row["source_label"],
            row["target_label"],
            row["source_primary_concept_type"],
            row["target_primary_concept_type"],
            row["source_context_entity_type"],
            row["target_context_entity_type"],
        ) if row["audit_bucket"] == "substantive_unresolved" else ("not_applicable", "not_applicable", "not_applicable"),
        axis=1,
    )
    unknown_audit["substantive_subtype"] = substantive_meta.map(lambda item: item[0])
    unknown_audit["audit_priority"] = substantive_meta.map(lambda item: item[1])
    unknown_audit["audit_reason"] = substantive_meta.map(lambda item: item[2])
    unknown_audit = unknown_audit.sort_values(
        ["audit_bucket", "audit_priority", "substantive_subtype", "taxonomy_confidence", "distinct_paper_support", "weight"],
        ascending=[True, True, True, True, False, False],
    ).reset_index(drop=True)
    instance_keep = instance_taxonomy.rename(
        columns={
            "src_code": "source_concept_id",
            "dst_code": "target_concept_id",
            "evidence_type": "raw_evidence_type",
            "relation_type": "raw_relation_type",
            "causal_presentation": "raw_causal_presentation",
        }
    )[
        [
            "source_concept_id",
            "target_concept_id",
            "paper_id",
            "raw_evidence_type",
            "raw_relation_type",
            "raw_causal_presentation",
            "evidence_mode",
            "design_family",
            "identification_strength",
            "taxonomy_confidence",
            "unknown_reason",
        ]
    ].reset_index(drop=True)
    return merged, instance_keep, unknown_audit


def _build_family_relation_table(
    family_seed_df: pd.DataFrame,
    candidate_relation_df: pd.DataFrame,
) -> pd.DataFrame:
    seed_rows: list[dict[str, Any]] = []
    for family_id, sub in family_seed_df.groupby("family_id"):
        members = sub[["member_concept_id", "member_label"]].drop_duplicates().to_dict(orient="records")
        for left, right in combinations(members, 2):
            seed_rows.append(
                {
                    "left_concept_id": left["member_concept_id"],
                    "left_label": left["member_label"],
                    "right_concept_id": right["member_concept_id"],
                    "right_label": right["member_label"],
                    "relation_type": "do_not_merge",
                    "relation_source": "reviewed_seed",
                    "relation_confidence": 1.0,
                    "proposed_family_id": family_id,
                    "proposed_family_label": sub["family_label"].iloc[0],
                    "relation_note": "Reviewed family members are related but must remain separate canonical concepts.",
                    "review_status": "approved",
                }
            )
    base = pd.DataFrame(seed_rows)
    if candidate_relation_df.empty:
        return base.sort_values(["proposed_family_id", "left_label", "right_label"]).reset_index(drop=True)
    merged = pd.concat([base, candidate_relation_df], ignore_index=True)
    return merged.sort_values(
        ["proposed_family_id", "review_status", "relation_confidence", "left_label", "right_label"],
        ascending=[True, True, False, True, True],
    ).reset_index(drop=True)


def _enrich_shortlist(
    shortlist_df: pd.DataFrame,
    canonical_df: pd.DataFrame,
    family_df: pd.DataFrame,
    context_df: pd.DataFrame,
    edge_df: pd.DataFrame,
) -> pd.DataFrame:
    pair_ids = shortlist_df["pair_key"].astype(str).str.split("__", n=1, expand=True)
    enriched = shortlist_df.copy()
    enriched["source_concept_id"] = pair_ids[0]
    enriched["target_concept_id"] = pair_ids[1]

    family_lookup = family_df.rename(
        columns={
            "member_concept_id": "concept_id",
            "family_id": "family_id_tmp",
            "family_label": "family_label_tmp",
            "family_type": "family_type_tmp",
        }
    )[["concept_id", "family_id_tmp", "family_label_tmp", "family_type_tmp"]]
    canonical_lookup = canonical_df.rename(
        columns={
            "concept_id": "concept_id_tmp",
            "preferred_label": "canonical_label_tmp",
            "bucket_hint": "bucket_hint_tmp",
            "primary_concept_type": "primary_concept_type_tmp",
            "concept_type_confidence": "concept_type_confidence_tmp",
            "concept_type_reason": "concept_type_reason_tmp",
            "context_entity_type": "context_entity_type_tmp",
            "context_entity_confidence": "context_entity_confidence_tmp",
            "context_entity_reason": "context_entity_reason_tmp",
        }
    )[[
        "concept_id_tmp",
        "canonical_label_tmp",
        "bucket_hint_tmp",
        "primary_concept_type_tmp",
        "concept_type_confidence_tmp",
        "concept_type_reason_tmp",
        "context_entity_type_tmp",
        "context_entity_confidence_tmp",
        "context_entity_reason_tmp",
    ]]
    context_lookup = context_df.rename(
        columns={
            "concept_id": "concept_id_ctx",
            "top_geographies_json": "top_geographies_json_tmp",
            "top_units_json": "top_units_json_tmp",
            "representative_contexts_json": "representative_contexts_json_tmp",
            "representative_years_json": "representative_years_json_tmp",
            "bucket_profile_json": "bucket_profile_json_tmp",
            "context_support": "context_support_tmp",
        }
    )

    enriched = enriched.merge(
        canonical_lookup,
        left_on="source_concept_id",
        right_on="concept_id_tmp",
        how="left",
    ).drop(columns=["concept_id_tmp"])
    enriched = enriched.rename(
        columns={
            "canonical_label_tmp": "source_canonical_label",
            "bucket_hint_tmp": "source_bucket_hint",
            "primary_concept_type_tmp": "source_primary_concept_type",
            "concept_type_confidence_tmp": "source_concept_type_confidence",
            "concept_type_reason_tmp": "source_concept_type_reason",
            "context_entity_type_tmp": "source_context_entity_type",
            "context_entity_confidence_tmp": "source_context_entity_confidence",
            "context_entity_reason_tmp": "source_context_entity_reason",
        }
    )
    enriched = enriched.merge(
        canonical_lookup,
        left_on="target_concept_id",
        right_on="concept_id_tmp",
        how="left",
    ).drop(columns=["concept_id_tmp"])
    enriched = enriched.rename(
        columns={
            "canonical_label_tmp": "target_canonical_label",
            "bucket_hint_tmp": "target_bucket_hint",
            "primary_concept_type_tmp": "target_primary_concept_type",
            "concept_type_confidence_tmp": "target_concept_type_confidence",
            "concept_type_reason_tmp": "target_concept_type_reason",
            "context_entity_type_tmp": "target_context_entity_type",
            "context_entity_confidence_tmp": "target_context_entity_confidence",
            "context_entity_reason_tmp": "target_context_entity_reason",
        }
    )

    enriched = enriched.merge(
        family_lookup,
        left_on="source_concept_id",
        right_on="concept_id",
        how="left",
    ).drop(columns=["concept_id"])
    enriched = enriched.rename(
        columns={
            "family_id_tmp": "source_family_id",
            "family_label_tmp": "source_family_label",
            "family_type_tmp": "source_family_type",
        }
    )
    enriched = enriched.merge(
        family_lookup,
        left_on="target_concept_id",
        right_on="concept_id",
        how="left",
    ).drop(columns=["concept_id"])
    enriched = enriched.rename(
        columns={
            "family_id_tmp": "target_family_id",
            "family_label_tmp": "target_family_label",
            "family_type_tmp": "target_family_type",
        }
    )

    enriched = enriched.merge(
        context_lookup,
        left_on="source_concept_id",
        right_on="concept_id_ctx",
        how="left",
    ).drop(columns=["concept_id_ctx"])
    enriched = enriched.rename(
        columns={
            "top_geographies_json_tmp": "source_top_geographies_json",
            "top_units_json_tmp": "source_top_units_json",
            "representative_contexts_json_tmp": "source_representative_contexts_json",
            "representative_years_json_tmp": "source_representative_years_json",
            "bucket_profile_json_tmp": "source_bucket_profile_json",
            "context_support_tmp": "source_context_support",
        }
    )
    enriched = enriched.merge(
        context_lookup,
        left_on="target_concept_id",
        right_on="concept_id_ctx",
        how="left",
    ).drop(columns=["concept_id_ctx"])
    enriched = enriched.rename(
        columns={
            "top_geographies_json_tmp": "target_top_geographies_json",
            "top_units_json_tmp": "target_top_units_json",
            "representative_contexts_json_tmp": "target_representative_contexts_json",
            "representative_years_json_tmp": "target_representative_years_json",
            "bucket_profile_json_tmp": "target_bucket_profile_json",
            "context_support_tmp": "target_context_support",
        }
    )

    exact_edge = edge_df.copy()
    exact_edge["edge_join_method"] = "exact_pair"
    enriched = enriched.merge(exact_edge, on=["source_concept_id", "target_concept_id"], how="left")
    missing_edge_mask = enriched["edge_evidence_mode"].isna()
    if missing_edge_mask.any():
        reverse_edge = edge_df.rename(
            columns={
                "source_concept_id": "target_concept_id",
                "target_concept_id": "source_concept_id",
            }
        ).copy()
        reverse_edge["edge_join_method"] = "reverse_pair"
        reverse_hits = enriched.loc[missing_edge_mask, ["source_concept_id", "target_concept_id"]].merge(
            reverse_edge,
            on=["source_concept_id", "target_concept_id"],
            how="left",
        )
        reverse_hits.index = enriched.index[missing_edge_mask]
        for col in reverse_hits.columns:
            if col in {"source_concept_id", "target_concept_id"}:
                continue
            if col not in enriched.columns:
                enriched[col] = pd.NA
            enriched.loc[missing_edge_mask, col] = reverse_hits[col]
    for col in [
        "source_top_geographies_json",
        "source_top_units_json",
        "source_representative_contexts_json",
        "source_representative_years_json",
        "source_bucket_profile_json",
        "target_top_geographies_json",
        "target_top_units_json",
        "target_representative_contexts_json",
        "target_representative_years_json",
        "target_bucket_profile_json",
    ]:
        enriched[col] = enriched[col].fillna("[]")
    for col in [
        "directionality_json",
        "relationship_type_json",
        "causal_presentation_json",
        "edge_role_json",
        "claim_status_json",
        "dominant_countries_json",
        "dominant_units_json",
        "dominant_years_json",
        "context_note_examples_json",
    ]:
        if col in enriched.columns:
            enriched[col] = enriched[col].fillna("[]")
    for col in ["identification_strength", "unknown_reason"]:
        if col in enriched.columns:
            enriched[col] = enriched[col].fillna("unknown" if col == "identification_strength" else "")
    for col, default in [
        ("edge_design_family_original", ""),
        ("edge_design_family_resolution_source", "none"),
        ("edge_design_family_resolution_reason", ""),
        ("policy_edge_semantic_type", "none"),
        ("policy_edge_semantic_reason", ""),
        ("regime_guardrail_decision", "not_applicable"),
        ("regime_guardrail_reason", ""),
        ("edge_relation_semantic_type", "none"),
        ("edge_relation_semantic_reason", ""),
    ]:
        if col in enriched.columns:
            enriched[col] = enriched[col].fillna(default)
    for col in [
        "source_primary_concept_type",
        "target_primary_concept_type",
        "source_concept_type_reason",
        "target_concept_type_reason",
        "source_context_entity_type",
        "target_context_entity_type",
        "source_context_entity_reason",
        "target_context_entity_reason",
    ]:
        if col in enriched.columns:
            enriched[col] = enriched[col].fillna("")
    for col in [
        "source_concept_type_confidence",
        "target_concept_type_confidence",
        "source_context_entity_confidence",
        "target_context_entity_confidence",
        "edge_design_family_resolution_confidence",
        "policy_edge_semantic_confidence",
        "edge_relation_semantic_confidence",
    ]:
        if col in enriched.columns:
            default = 0.5 if col in {
                "source_concept_type_confidence",
                "target_concept_type_confidence",
                "source_context_entity_confidence",
                "target_context_entity_confidence",
            } else 0.0
            enriched[col] = pd.to_numeric(enriched[col], errors="coerce").fillna(default).astype(float)
    if "taxonomy_confidence" in enriched.columns:
        enriched["taxonomy_confidence"] = pd.to_numeric(enriched["taxonomy_confidence"], errors="coerce").fillna(0.25).astype(float)
    enriched["edge_causal_profile_json"] = enriched.apply(
        lambda row: json.dumps(
            {
                "directionality_json": _json_text(row.get("directionality_json", "[]")),
                "relationship_type_json": _json_text(row.get("relationship_type_json", "[]")),
                "causal_presentation_json": _json_text(row.get("causal_presentation_json", "[]")),
                "edge_role_json": _json_text(row.get("edge_role_json", "[]")),
                "claim_status_json": _json_text(row.get("claim_status_json", "[]")),
                "dominant_relation_type": str(row.get("dominant_relation_type", "") or ""),
                "dominant_causal_presentation": str(row.get("dominant_causal_presentation", "") or ""),
                "identification_strength": str(row.get("identification_strength", "") or ""),
                "taxonomy_confidence": _safe_float(row.get("taxonomy_confidence", 0.25), 0.25),
                "unknown_reason": str(row.get("unknown_reason", "") or ""),
            },
            ensure_ascii=False,
        ),
        axis=1,
    )
    enriched["edge_context_coverage_json"] = enriched.apply(
        lambda row: json.dumps(
            {
                "dominant_countries_json": _json_text(row.get("dominant_countries_json", "[]")),
                "dominant_units_json": _json_text(row.get("dominant_units_json", "[]")),
                "dominant_years_json": _json_text(row.get("dominant_years_json", "[]")),
                "context_note_examples_json": _json_text(row.get("context_note_examples_json", "[]")),
            },
            ensure_ascii=False,
        ),
        axis=1,
    )
    return enriched


def _coverage_summary(
    canonical_df: pd.DataFrame,
    family_seed_df: pd.DataFrame,
    family_df: pd.DataFrame,
    family_candidate_df: pd.DataFrame,
    family_relation_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    edge_instance_taxonomy_df: pd.DataFrame,
    edge_unknown_audit_df: pd.DataFrame,
    enriched_df: pd.DataFrame,
    reviewed_design_df: pd.DataFrame,
    reviewed_policy_df: pd.DataFrame,
    reviewed_relation_df: pd.DataFrame,
) -> dict[str, Any]:
    source_canonical_ok = enriched_df["source_canonical_label"].notna().mean()
    target_canonical_ok = enriched_df["target_canonical_label"].notna().mean()
    source_family_ok = enriched_df["source_family_id"].notna().mean()
    target_family_ok = enriched_df["target_family_id"].notna().mean()
    endpoint_context_ok = pd.concat(
        [
            enriched_df["source_top_geographies_json"].map(_nonempty_jsonish) | enriched_df["source_top_units_json"].map(_nonempty_jsonish),
            enriched_df["target_top_geographies_json"].map(_nonempty_jsonish) | enriched_df["target_top_units_json"].map(_nonempty_jsonish),
        ],
        ignore_index=True,
    ).mean()
    edge_evidence_ok = enriched_df["edge_evidence_mode"].fillna("").astype(str).str.strip().ne("").mean()
    concept_family_counts = family_df.groupby("member_concept_id")["family_id"].nunique()
    env_members = family_df[family_df["family_id"] == ENVIRONMENTAL_OUTCOME_FAMILY["family_id"]]["member_concept_id"].astype(str).tolist()
    summary = {
        "canonical_concepts_rows": int(len(canonical_df)),
        "reviewed_family_count": int(family_seed_df["family_id"].nunique()),
        "family_seed_rows": int(len(family_seed_df)),
        "concept_families_rows": int(len(family_df)),
        "family_candidate_rows": int(len(family_candidate_df)),
        "family_relation_rows": int(len(family_relation_df)),
        "mapping_rows": int(len(mapping_df)),
        "edge_instance_taxonomy_rows": int(len(edge_instance_taxonomy_df)),
        "edge_unknown_audit_rows": int(len(edge_unknown_audit_df)),
        "reviewed_design_family_override_rows": int(len(reviewed_design_df)),
        "reviewed_policy_semantic_rows": int(len(reviewed_policy_df)),
        "reviewed_relation_semantic_rows": int(len(reviewed_relation_df)),
        "reviewed_policy_semantic_keep_rows": int(
            reviewed_policy_df["regime_guardrail_decision"].astype(str).eq("keep").sum()
        ) if len(reviewed_policy_df) else 0,
        "reviewed_policy_semantic_drop_rows": int(
            reviewed_policy_df["regime_guardrail_decision"].astype(str).eq("drop").sum()
        ) if len(reviewed_policy_df) else 0,
        "enriched_shortlist_rows": int(len(enriched_df)),
        "source_canonical_join_share": float(source_canonical_ok),
        "target_canonical_join_share": float(target_canonical_ok),
        "source_family_join_share": float(source_family_ok),
        "target_family_join_share": float(target_family_ok),
        "endpoint_context_coverage_share": float(endpoint_context_ok),
        "edge_evidence_coverage_share": float(edge_evidence_ok),
        "concepts_with_multiple_families": int((concept_family_counts > 1).sum()),
        "environmental_family_member_count": int(len(env_members)),
        "environmental_family_members": env_members,
        "mapping_kind_values": sorted(mapping_df["mapping_kind"].dropna().astype(str).unique().tolist()),
        "concept_type_values": sorted(canonical_df["primary_concept_type"].dropna().astype(str).unique().tolist()),
        "concept_type_confidence_values": sorted({float(v) for v in pd.to_numeric(canonical_df["concept_type_confidence"], errors="coerce").dropna().tolist()}),
        "context_entity_type_values": sorted(canonical_df["context_entity_type"].dropna().astype(str).unique().tolist()) if "context_entity_type" in canonical_df.columns else [],
        "edge_evidence_mode_values": sorted(enriched_df["edge_evidence_mode"].dropna().astype(str).unique().tolist()),
        "edge_relation_semantic_type_values": sorted(enriched_df["edge_relation_semantic_type"].dropna().astype(str).unique().tolist()) if "edge_relation_semantic_type" in enriched_df.columns else [],
        "identification_strength_values": sorted(enriched_df["identification_strength"].dropna().astype(str).unique().tolist()),
        "taxonomy_confidence_values": sorted({float(v) for v in pd.to_numeric(enriched_df["taxonomy_confidence"], errors="coerce").dropna().tolist()}),
        "audit_bucket_values": sorted(edge_unknown_audit_df["audit_bucket"].dropna().astype(str).unique().tolist()) if "audit_bucket" in edge_unknown_audit_df.columns else [],
        "substantive_subtype_values": sorted(edge_unknown_audit_df["substantive_subtype"].dropna().astype(str).unique().tolist()) if "substantive_subtype" in edge_unknown_audit_df.columns else [],
        "audit_priority_values": sorted(edge_unknown_audit_df["audit_priority"].dropna().astype(str).unique().tolist()) if "audit_priority" in edge_unknown_audit_df.columns else [],
        "family_relation_type_values": sorted(family_relation_df["relation_type"].dropna().astype(str).unique().tolist()),
        "checks": {
            "canonical_join_complete": bool(source_canonical_ok == 1.0 and target_canonical_ok == 1.0),
            "family_join_complete": bool(source_family_ok == 1.0 and target_family_ok == 1.0),
            "endpoint_context_at_least_90pct": bool(endpoint_context_ok >= 0.90),
            "edge_evidence_at_least_90pct": bool(edge_evidence_ok >= 0.90),
            "single_family_per_concept": bool((concept_family_counts <= 1).all()),
            "environmental_boundary_members_remain_separate": bool(set(env_members) == set(ENVIRONMENTAL_OUTCOME_FAMILY["member_concept_ids"])),
            "mapping_kind_exact_only": bool(set(mapping_df["mapping_kind"].astype(str)) == {"exact"}),
            "concept_types_allowed_only": bool(set(canonical_df["primary_concept_type"].dropna().astype(str)).issubset(CONCEPT_TYPE_ALLOWED)),
            "concept_type_confidence_allowed_only": bool(set(float(v) for v in pd.to_numeric(canonical_df["concept_type_confidence"], errors="coerce").dropna().tolist()).issubset(TAXONOMY_CONFIDENCE_ALLOWED)),
            "context_entity_types_allowed_only": bool(set(canonical_df["context_entity_type"].dropna().astype(str)).issubset(CONTEXT_ENTITY_TYPE_ALLOWED)) if "context_entity_type" in canonical_df.columns else False,
            "edge_evidence_mode_allowed_only": bool(set(enriched_df["edge_evidence_mode"].dropna().astype(str)).issubset({"theory", "empirics", "mixed", "unknown"})),
            "identification_strength_allowed_only": bool(set(enriched_df["identification_strength"].dropna().astype(str)).issubset(IDENTIFICATION_STRENGTH_ALLOWED)),
            "taxonomy_confidence_allowed_only": bool(set(float(v) for v in pd.to_numeric(enriched_df["taxonomy_confidence"], errors="coerce").dropna().tolist()).issubset(TAXONOMY_CONFIDENCE_ALLOWED)),
            "audit_bucket_allowed_only": bool(set(edge_unknown_audit_df["audit_bucket"].dropna().astype(str)).issubset({"method_artifact", "metadata_container", "substantive_unresolved", "mixed_or_other"})) if "audit_bucket" in edge_unknown_audit_df.columns else False,
            "substantive_subtype_allowed_only": bool(set(edge_unknown_audit_df["substantive_subtype"].dropna().astype(str)).issubset(SUBSTANTIVE_SUBTYPE_ALLOWED)) if "substantive_subtype" in edge_unknown_audit_df.columns else False,
            "audit_priority_allowed_only": bool(set(edge_unknown_audit_df["audit_priority"].dropna().astype(str)).issubset(AUDIT_PRIORITY_ALLOWED)) if "audit_priority" in edge_unknown_audit_df.columns else False,
            "family_relation_types_allowed_only": bool(set(family_relation_df["relation_type"].dropna().astype(str)).issubset(SUPPORTED_RELATION_TYPES)),
        },
    }
    return summary


def _select_examples(enriched_df: pd.DataFrame, filter_func, limit: int) -> pd.DataFrame:
    sub = enriched_df[filter_func(enriched_df)].sort_values(["horizon", "shortlist_rank"]).head(limit).copy()
    return sub


def _write_review_markdown(enriched_df: pd.DataFrame, summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Ontology vNext Prototype Review",
        "",
        "This note enriches the active shortlist with a layered family view, node-context signatures, and edge-evidence overlays.",
        "",
        "## Coverage checks",
        f"- source canonical join share: `{summary['source_canonical_join_share']:.3f}`",
        f"- target canonical join share: `{summary['target_canonical_join_share']:.3f}`",
        f"- source family join share: `{summary['source_family_join_share']:.3f}`",
        f"- target family join share: `{summary['target_family_join_share']:.3f}`",
        f"- endpoint context coverage share: `{summary['endpoint_context_coverage_share']:.3f}`",
        f"- edge evidence coverage share: `{summary['edge_evidence_coverage_share']:.3f}`",
        "",
    ]
    for label, passed in summary["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} | `{label}`")

    def add_section(title: str, sub: pd.DataFrame) -> None:
        lines.extend(["", f"## {title}", ""])
        if sub.empty:
            lines.append("- none")
            return
        for row in sub.itertuples(index=False):
            lines.append(
                f"- `h={int(row.horizon)}` `#{int(row.shortlist_rank)}` {row.display_title}  \n"
                f"  Families: `{row.source_family_label}` -> `{row.target_family_label}`  \n"
                f"  Concept types: `{row.source_primary_concept_type}` -> `{row.target_primary_concept_type}`  \n"
                f"  Context entity types: `{row.source_context_entity_type}` -> `{row.target_context_entity_type}`  \n"
                f"  Source context: geographies `{row.source_top_geographies_json}`, units `{row.source_top_units_json}`  \n"
                f"  Target context: geographies `{row.target_top_geographies_json}`, units `{row.target_top_units_json}`  \n"
                f"  Edge evidence: mode `{row.edge_evidence_mode}`, design `{row.edge_design_family}`, id-strength `{row.identification_strength}`, confidence `{float(row.taxonomy_confidence):.2f}`, join `{row.edge_join_method}`  \n"
                f"  Why: {row.display_why}"
            )

    add_section(
        "Environmental Family Examples",
        _select_examples(
            enriched_df,
            lambda df: (
                df["source_family_id"].eq(ENVIRONMENTAL_OUTCOME_FAMILY["family_id"])
                | df["target_family_id"].eq(ENVIRONMENTAL_OUTCOME_FAMILY["family_id"])
            ),
            10,
        ),
    )
    add_section(
        "Willingness-To-Pay Examples",
        _select_examples(
            enriched_df,
            lambda df: (
                df["source_label"].fillna("").str.contains("willingness to pay", case=False)
                | df["target_label"].fillna("").str.contains("willingness to pay", case=False)
            ),
            5,
        ),
    )
    add_section(
        "Macro/GDP/Growth Examples",
        _select_examples(
            enriched_df,
            lambda df: (
                df["display_title"].fillna("").str.contains("GDP|growth|business cycle|output", case=False, regex=True)
                | df["display_why"].fillna("").str.contains("GDP|growth|business cycle|output", case=False, regex=True)
            ),
            5,
        ),
    )
    add_section(
        "Non-Environmental Strong Examples",
        _select_examples(
            enriched_df,
            lambda df: ~(
                df["source_family_id"].eq(ENVIRONMENTAL_OUTCOME_FAMILY["family_id"])
                | df["target_family_id"].eq(ENVIRONMENTAL_OUTCOME_FAMILY["family_id"])
            ),
            5,
        ),
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_interpretation_note(summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Ontology vNext Prototype Interpretation",
        "",
        "## What the current ontology loses by flattening",
        "",
        "The active frontier uses a single canonical concept layer as its main object.",
        "That is good for tractability, but it discards three distinctions we now know matter:",
        "",
        "- related-but-not-identical concepts inside the same family",
        "- context attached to a concept, such as geography or unit of analysis",
        "- evidence attached to an edge, such as theory vs empirics or stronger vs weaker causal presentation",
        "",
        "## What this prototype already recovers",
        "",
        "This prototype adds those distinctions without changing ranking.",
        "",
        f"- family layer: `{summary['reviewed_family_count']}` reviewed families are active, including an environmental outcome family with `{summary['environmental_family_member_count']}` separate canonical members",
        f"- concept types: `{', '.join(summary['concept_type_values'])}` now exist as an internal overlay on canonical concepts",
        f"- node context: endpoint context coverage is `{summary['endpoint_context_coverage_share']:.1%}` on the active shortlist",
        f"- edge evidence: pair-level evidence coverage is `{summary['edge_evidence_coverage_share']:.1%}` on the active shortlist",
        "",
        "So the prototype does not yet produce a new frontier, but it already makes the current frontier more interpretable.",
        "",
        "## Why this matters for path/mechanism questions",
        "",
        "A path question is stronger if we can tell whether the linked concepts sit in the same broader family,",
        "whether they tend to appear in the same kinds of settings, and whether the observed support is mostly theory, empirics, or mixed evidence.",
        "",
        "That means a future frontier can ask not only:",
        "- what direct relation is missing?",
        "- what mechanism is missing?",
        "",
        "but also:",
        "- what family member is underexplored relative to its siblings?",
        "- what context transfer is missing?",
        "- what empirical confirmation is missing for a theory-heavy relation?",
        "",
        "## New frontier types this enables later",
        "",
        "- family-aware frontier questions",
        "- context-transfer questions",
        "- missing empirical confirmation questions",
        "- evidence-type expansion questions",
        "",
        "## Bottom line",
        "",
        "The prototype confirms that the next ontology gains should come from preserving more structure,",
        "not from continuing to hand-clean labels one family at a time.",
        "The natural next move after this prototype is to connect family/context/evidence fields to a future ranking or surfacing layer, not to replace the active baseline immediately.",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_family_review_note(family_seed_df: pd.DataFrame, candidate_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Family Candidate Review",
        "",
        "This note records the reviewed seed layer plus the reusable candidate-family queue.",
        "",
        "## Design rule",
        "",
        "Active family membership still comes only from reviewed seeds.",
        "Candidate families are a reusable review queue, not live ontology membership.",
        "",
        "## Active reviewed seeds",
        "",
    ]
    seed_summary = (
        family_seed_df.groupby(["family_id", "family_label", "family_type"], as_index=False)
        .agg(
            member_count=("member_concept_id", "nunique"),
            members=("member_label", lambda s: ", ".join(sorted(set(map(str, s))))),
        )
        .sort_values(["member_count", "family_label"], ascending=[False, True])
    )
    for row in seed_summary.itertuples(index=False):
        lines.append(
            f"- `{row.family_label}` | type `{row.family_type}` | members `{int(row.member_count)}`  \n"
            f"  Members: {row.members}"
        )
    lines.extend(
        [
            "",
        "## What the candidate generator uses",
        "",
        "- semantic overlap across preferred labels and aliases",
        "- bucket-hint / bucket-profile similarity",
        "- shortlist partner overlap",
        "- co-mentions across internal review notes",
        "",
        "## Top candidate families",
        "",
        ]
    )
    if candidate_df.empty:
        lines.append("- none")
    else:
        summary_df = (
            candidate_df.groupby(["candidate_family_id", "proposed_family_label", "family_type"], as_index=False)
            .agg(
                member_count=("member_concept_id", "nunique"),
                mean_semantic_score=("semantic_score", "mean"),
                mean_collision_score=("collision_score", "mean"),
                mean_combined_score=("combined_score", "mean"),
                members=("member_label", lambda s: ", ".join(sorted(set(map(str, s))))),
            )
            .sort_values(["mean_combined_score", "member_count"], ascending=[False, False])
        )
        for row in summary_df.head(12).itertuples(index=False):
            lines.append(
                f"- `{row.proposed_family_label}` | type `{row.family_type}` | members `{int(row.member_count)}` | "
                f"semantic `{row.mean_semantic_score:.2f}` | collision `{row.mean_collision_score:.2f}` | combined `{row.mean_combined_score:.2f}`  \n"
                f"  Members: {row.members}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    review_out_dir = Path(args.review_out_dir)
    interpretation_note_path = Path(args.interpretation_note_path)
    family_review_note_path = Path(args.family_review_note_path)
    context_alias_csv_path = Path(args.context_alias_csv_path)
    reviewed_design_family_csv_path = Path(args.reviewed_design_family_csv_path)
    reviewed_policy_semantics_csv_path = Path(args.reviewed_policy_semantics_csv_path)
    reviewed_relation_semantics_csv_path = Path(args.reviewed_relation_semantics_csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    review_out_dir.mkdir(parents=True, exist_ok=True)
    interpretation_note_path.parent.mkdir(parents=True, exist_ok=True)
    family_review_note_path.parent.mkdir(parents=True, exist_ok=True)

    print("[proto] loading corpus", flush=True)
    corpus_df = pd.read_parquet(args.corpus_path)
    print("[proto] loading shortlist", flush=True)
    shortlist_df = pd.read_csv(args.shortlist_path)
    concept_db_path = Path(args.concept_db_path)

    print("[proto] building canonical concepts", flush=True)
    canonical_df = _load_canonical_concepts(concept_db_path, corpus_df=corpus_df, shortlist_df=shortlist_df)
    print("[proto] building family seeds", flush=True)
    family_seed_df = _build_family_seed_table(canonical_df)
    print("[proto] loading context alias lookup", flush=True)
    context_alias_lookup = _load_context_alias_lookup(context_alias_csv_path)
    print("[proto] loading reviewed edge typing inputs", flush=True)
    reviewed_design_df = _load_reviewed_design_family_overrides(reviewed_design_family_csv_path)
    reviewed_policy_df = _load_reviewed_policy_edge_semantics(reviewed_policy_semantics_csv_path)
    reviewed_relation_df = _load_reviewed_relation_semantics(reviewed_relation_semantics_csv_path)
    print("[proto] tagging concept types", flush=True)
    canonical_df = _apply_concept_type_tags(canonical_df, family_seed_df, context_alias_lookup)
    print("[proto] building concept families", flush=True)
    family_df = _build_concept_families(canonical_df, family_seed_df)
    print("[proto] building mention proxy", flush=True)
    mention_proxy_df = _build_mention_proxy(corpus_df, canonical_df, family_df)
    print("[proto] building mapping table", flush=True)
    mapping_df = _build_mapping_table(mention_proxy_df)
    print("[proto] building context signatures", flush=True)
    context_df = _build_context_signatures(canonical_df)
    print("[proto] building edge evidence profiles", flush=True)
    edge_df, edge_instance_taxonomy_df, edge_unknown_audit_df = _build_edge_evidence_profiles(
        corpus_df,
        concept_db_path,
        canonical_df,
        reviewed_design_df,
        reviewed_policy_df,
        reviewed_relation_df,
    )
    print("[proto] enriching shortlist", flush=True)
    enriched_df = _enrich_shortlist(shortlist_df, canonical_df, family_df, context_df, edge_df)
    print("[proto] building family candidates", flush=True)
    family_candidate_df, candidate_relation_df = _build_family_candidates(
        canonical_df,
        enriched_df,
        family_seed_df,
        Path(args.routed_shortlist_path),
    )
    print("[proto] building family relation table", flush=True)
    family_relation_df = _build_family_relation_table(family_seed_df, candidate_relation_df)
    print("[proto] computing summary", flush=True)
    summary = _coverage_summary(
        canonical_df,
        family_seed_df,
        family_df,
        family_candidate_df,
        family_relation_df,
        mapping_df,
        edge_instance_taxonomy_df,
        edge_unknown_audit_df,
        enriched_df,
        reviewed_design_df,
        reviewed_policy_df,
        reviewed_relation_df,
    )

    print("[proto] writing artifact tables", flush=True)
    canonical_df.to_parquet(out_dir / "canonical_concepts.parquet", index=False)
    mention_proxy_df.to_parquet(out_dir / "mention_proxy.parquet", index=False)
    family_seed_df.to_parquet(out_dir / "family_seed_table.parquet", index=False)
    family_df.to_parquet(out_dir / "concept_families.parquet", index=False)
    family_candidate_df.to_parquet(out_dir / "family_candidate_table.parquet", index=False)
    family_relation_df.to_parquet(out_dir / "family_relation_table.parquet", index=False)
    mapping_df.to_parquet(out_dir / "mapping_table.parquet", index=False)
    context_df.to_parquet(out_dir / "concept_context_signatures.parquet", index=False)
    edge_df.to_parquet(out_dir / "edge_evidence_profiles.parquet", index=False)
    edge_instance_taxonomy_df.to_parquet(out_dir / "edge_instance_taxonomy.parquet", index=False)
    edge_unknown_audit_df.to_parquet(out_dir / "evidence_unknown_audit.parquet", index=False)
    edge_df.to_parquet(out_dir / "canonical_edge_evidence_summary.parquet", index=False)

    print("[proto] writing review pack", flush=True)
    enriched_df.to_csv(review_out_dir / "enriched_shortlist.csv", index=False)
    (review_out_dir / "prototype_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_review_markdown(enriched_df, summary, review_out_dir / "enriched_shortlist.md")
    _write_interpretation_note(summary, interpretation_note_path)
    _write_family_review_note(family_seed_df, family_candidate_df, family_review_note_path)

    manifest = {
        "corpus_path": args.corpus_path,
        "shortlist_path": args.shortlist_path,
        "routed_shortlist_path": args.routed_shortlist_path,
        "context_alias_csv_path": args.context_alias_csv_path,
        "reviewed_design_family_csv_path": args.reviewed_design_family_csv_path,
        "reviewed_policy_semantics_csv_path": args.reviewed_policy_semantics_csv_path,
        "concept_db_path": args.concept_db_path,
        "out_dir": str(out_dir),
        "review_out_dir": str(review_out_dir),
        "interpretation_note_path": str(interpretation_note_path),
        "family_review_note_path": str(family_review_note_path),
        "summary": summary,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote prototype artifacts to {out_dir}")
    print(f"Wrote enriched review pack to {review_out_dir}")


if __name__ == "__main__":
    main()
