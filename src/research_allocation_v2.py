from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils import min_max_normalize, pair_key


CAUSAL_METHODS = {
    "experiment",
    "did",
    "iv",
    "rdd",
    "event_study",
    "panel_fe_or_twfe",
}

CAUSAL_PRESENTATIONS = {"explicit_causal", "implicit_causal"}

LEGACY_CANDIDATE_KIND_TO_LAYER = {
    "undirected_noncausal": "contextual_pair",
    "directed_causal": "identified_causal_claim",
}

CANONICAL_CANDIDATE_KINDS = {
    "contextual_pair",
    "ordered_claim",
    "causal_claim",
    "identified_causal_claim",
}

CANONICAL_CANDIDATE_FAMILY_MODES = {
    "path_to_direct",
    "direct_to_path",
}

PREPOSITION_TOKENS = {
    "in",
    "for",
    "of",
    "under",
    "with",
    "without",
    "among",
    "between",
    "across",
    "during",
    "after",
    "before",
    "via",
}

TRAILING_QUALIFIER_TOKENS = {
    "effect",
    "effects",
    "shock",
    "shocks",
    "rate",
    "rates",
    "index",
    "indices",
    "model",
    "models",
    "measure",
    "measures",
    "policy",
    "policies",
    "constraint",
    "constraints",
    "requirement",
    "requirements",
    "scheme",
    "schemes",
    "regulation",
    "regulations",
    "variable",
    "variables",
}


def _norm_method(value: Any) -> str:
    return str(value or "").strip().lower()


def is_directed_causal_method(value: Any) -> bool:
    return _norm_method(value) in CAUSAL_METHODS


def normalize_candidate_kind(value: Any) -> str:
    kind = str(value or "").strip()
    if not kind:
        return "identified_causal_claim"
    return LEGACY_CANDIDATE_KIND_TO_LAYER.get(kind, kind)


def candidate_layer_mask(df: pd.DataFrame, candidate_kind: str) -> pd.Series:
    kind = normalize_candidate_kind(candidate_kind)
    if kind not in CANONICAL_CANDIDATE_KINDS:
        raise ValueError(f"Unsupported candidate_kind: {candidate_kind}")

    edge_kind = df.get("edge_kind", pd.Series("", index=df.index)).fillna("").astype(str)
    directionality = df.get("directionality_raw", pd.Series("unclear", index=df.index)).fillna("unclear").astype(str)
    causal_presentation = (
        df.get("causal_presentation", pd.Series("other", index=df.index)).fillna("other").astype(str)
    )

    if kind == "contextual_pair":
        return edge_kind == "undirected_noncausal"
    if kind == "ordered_claim":
        return directionality == "directed"
    if kind == "causal_claim":
        return (directionality == "directed") & causal_presentation.isin(CAUSAL_PRESENTATIONS)
    return edge_kind == "directed_causal"


def normalize_candidate_family_mode(value: Any) -> str:
    mode = str(value or "").strip()
    if not mode:
        return "path_to_direct"
    if mode not in CANONICAL_CANDIDATE_FAMILY_MODES:
        raise ValueError(f"Unsupported candidate_family_mode: {value}")
    return mode


def dominant_value(values: list[str], default: str = "unspecified") -> str:
    cleaned = [str(v) for v in values if str(v).strip()]
    if not cleaned:
        return default
    return Counter(cleaned).most_common(1)[0][0]


def top_counts(values: list[str], limit: int = 3) -> list[dict[str, Any]]:
    counter = Counter([str(v) for v in values if str(v).strip()])
    return [{"value": key, "count": int(count)} for key, count in counter.most_common(limit)]


def derive_weight(group: pd.DataFrame) -> float:
    base = float(len(group))
    if bool(group["uses_data"].fillna(0).astype(int).max()):
        base += 0.25
    if group["causal_presentation"].isin(["explicit_causal", "implicit_causal"]).any():
        base += 0.25
    if group["statistical_significance"].eq("significant").any():
        base += 0.10
    if (~group["evidence_method"].isin(["do_not_know", "other"])).any():
        base += 0.10
    return base


def derive_stability_row(row: pd.Series) -> float:
    claim_base = {
        "effect_present": 0.95,
        "conditional_effect": 0.82,
        "mixed_or_ambiguous": 0.62,
        "no_effect": 0.55,
        "question_only": 0.22,
        "other": 0.40,
    }.get(str(row.get("claim_status", "")), 0.40)
    explicitness_adj = {
        "result_only": 0.08,
        "question_and_result": 0.04,
        "background_claim": -0.18,
        "implied": -0.05,
        "question_only": -0.10,
    }.get(str(row.get("explicitness", "")), 0.0)
    tent_adj = {
        "certain": 0.05,
        "tentative": -0.05,
        "mixed_or_qualified": -0.08,
        "unclear": -0.10,
    }.get(str(row.get("tentativeness", "")), 0.0)
    causal_adj = {
        "explicit_causal": 0.05,
        "implicit_causal": 0.02,
        "noncausal": 0.0,
        "unclear": -0.03,
    }.get(str(row.get("causal_presentation", "")), 0.0)
    score = claim_base + explicitness_adj + tent_adj + causal_adj
    return float(max(0.0, min(1.0, score)))


def derive_stability_series(df: pd.DataFrame) -> pd.Series:
    claim_base = df["claim_status"].astype(str).map(
        {
            "effect_present": 0.95,
            "conditional_effect": 0.82,
            "mixed_or_ambiguous": 0.62,
            "no_effect": 0.55,
            "question_only": 0.22,
            "other": 0.40,
        }
    ).fillna(0.40)
    explicitness_adj = df["explicitness"].astype(str).map(
        {
            "result_only": 0.08,
            "question_and_result": 0.04,
            "background_claim": -0.18,
            "implied": -0.05,
            "question_only": -0.10,
        }
    ).fillna(0.0)
    tent_adj = df["tentativeness"].astype(str).map(
        {
            "certain": 0.05,
            "tentative": -0.05,
            "mixed_or_qualified": -0.08,
            "unclear": -0.10,
        }
    ).fillna(0.0)
    causal_adj = df["causal_presentation"].astype(str).map(
        {
            "explicit_causal": 0.05,
            "implicit_causal": 0.02,
            "noncausal": 0.0,
            "unclear": -0.03,
        }
    ).fillna(0.0)
    return (claim_base + explicitness_adj + tent_adj + causal_adj).clip(lower=0.0, upper=1.0).astype(float)


def _sql_frame(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, conn)


def _normalize_label_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower()).strip()


def _strip_parenthetical(label: str) -> str:
    return _normalize_label_text(re.sub(r"\s*\([^)]*\)", " ", str(label or "")))


def _build_head_exact_map(head_concepts: pd.DataFrame) -> dict[str, str]:
    alias_to_candidates: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for row in head_concepts.itertuples(index=False):
        concept_id = str(row.concept_id)
        support = int(getattr(row, "instance_support", 0) or 0)
        aliases = {_normalize_label_text(getattr(row, "preferred_label", ""))}
        try:
            aliases_json = json.loads(getattr(row, "aliases_json", "[]") or "[]")
            aliases.update({_normalize_label_text(alias) for alias in aliases_json})
        except Exception:
            pass
        for alias in aliases:
            if alias:
                alias_to_candidates[alias].append((concept_id, support))
    exact_map: dict[str, str] = {}
    for alias, candidates in alias_to_candidates.items():
        ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
        if len({cid for cid, _ in ranked}) == 1:
            exact_map[alias] = ranked[0][0]
            continue
        if len(ranked) >= 2 and ranked[0][1] > max(1, ranked[1][1]) * 2:
            exact_map[alias] = ranked[0][0]
    return exact_map


def _fallback_mapping_for_label(label: str, exact_map: dict[str, str]) -> tuple[str | None, str | None, float]:
    original = _normalize_label_text(label)
    if not original:
        return None, None, 0.0
    if original in exact_map:
        return exact_map[original], "v2_exact_alias_backoff", 0.80

    stripped = _strip_parenthetical(original)
    if stripped and stripped != original and stripped in exact_map:
        return exact_map[stripped], "v2_strip_paren_backoff", 0.68

    tokens = stripped.split() if stripped else original.split()
    for idx, token in enumerate(tokens):
        if token in PREPOSITION_TOKENS and idx >= 1:
            base = " ".join(tokens[:idx]).strip()
            if base in exact_map:
                return exact_map[base], "v2_preposition_backoff", 0.60
            break

    suffix_tokens = list(tokens)
    removed = 0
    while suffix_tokens and suffix_tokens[-1] in TRAILING_QUALIFIER_TOKENS and len(suffix_tokens) > 1:
        suffix_tokens = suffix_tokens[:-1]
        removed += 1
        base = " ".join(suffix_tokens).strip()
        if base in exact_map and len(suffix_tokens) >= 2:
            return exact_map[base], "v2_suffix_backoff", max(0.50, 0.60 - 0.05 * removed)

    return None, None, 0.0


def _augment_with_lexical_fallback(mappings: pd.DataFrame, head_concepts: pd.DataFrame) -> pd.DataFrame:
    if mappings.empty or head_concepts.empty:
        return mappings
    out = mappings.copy()
    unresolved_mask = out["concept_id"].isna()
    if not unresolved_mask.any():
        return out
    exact_map = _build_head_exact_map(head_concepts)
    fallback_map: dict[str, tuple[str, str, float]] = {}
    unresolved_labels = out.loc[unresolved_mask, "normalized_label"].dropna().astype(str).unique().tolist()
    for normalized_label in unresolved_labels:
        concept_id, mapping_source, confidence = _fallback_mapping_for_label(normalized_label, exact_map)
        if concept_id is not None:
            fallback_map[normalized_label] = (concept_id, mapping_source or "", float(confidence))
    if not fallback_map:
        return out
    label_series = out["normalized_label"].astype(str)
    concept_map = {label: value[0] for label, value in fallback_map.items()}
    source_map = {label: value[1] for label, value in fallback_map.items()}
    confidence_map = {label: value[2] for label, value in fallback_map.items()}
    fill_mask = unresolved_mask & label_series.isin(concept_map)
    out.loc[fill_mask, "concept_id"] = label_series.loc[fill_mask].map(concept_map)
    out.loc[fill_mask, "mapping_source"] = label_series.loc[fill_mask].map(source_map)
    out.loc[fill_mask, "confidence"] = label_series.loc[fill_mask].map(confidence_map)
    return out


def _augment_with_force_mappings(mappings: pd.DataFrame, force_mappings: pd.DataFrame) -> pd.DataFrame:
    if mappings.empty or force_mappings.empty:
        return mappings
    out = mappings.copy()
    unresolved_mask = out["concept_id"].isna()
    if not unresolved_mask.any():
        return out
    force_df = force_mappings[["normalized_label", "candidate_concept_id", "mapping_source", "cosine_similarity"]].drop_duplicates(
        subset=["normalized_label"],
        keep="last",
    )
    concept_map = force_df.set_index("normalized_label")["candidate_concept_id"].to_dict()
    source_map = force_df.set_index("normalized_label")["mapping_source"].to_dict()
    confidence_map = force_df.set_index("normalized_label")["cosine_similarity"].to_dict()
    label_series = out["normalized_label"].astype(str)
    fill_mask = unresolved_mask & label_series.isin(concept_map)
    out.loc[fill_mask, "concept_id"] = label_series.loc[fill_mask].map(concept_map)
    out.loc[fill_mask, "mapping_source"] = label_series.loc[fill_mask].map(source_map)
    out.loc[fill_mask, "confidence"] = label_series.loc[fill_mask].map(confidence_map)
    return out


def load_large_corpus_frames(
    extraction_db: str | Path,
    ontology_db: str | Path,
    mapping_table: str = "instance_mappings_soft",
    force_mapping_table: str | None = "tail_force_mappings",
) -> pd.DataFrame:
    t0 = time.perf_counter()
    econ = sqlite3.connect(f"file:{Path(extraction_db)}?mode=ro", uri=True)
    onto = sqlite3.connect(f"file:{Path(ontology_db)}?mode=ro", uri=True)
    try:
        works = _sql_frame(
            econ,
            """
            SELECT custom_id, title, publication_year, bucket, source_display_name
            FROM works
            """,
        )
        print(f"[load] works read in {time.perf_counter() - t0:.1f}s ({len(works)} rows)", flush=True)
        t1 = time.perf_counter()
        nodes = _sql_frame(
            econ,
            """
            SELECT custom_id, node_id, label, unit_of_analysis_json, countries_json, context_note
            FROM nodes
            """,
        )
        print(f"[load] nodes read in {time.perf_counter() - t1:.1f}s ({len(nodes)} rows)", flush=True)
        t2 = time.perf_counter()
        edges = _sql_frame(
            econ,
            """
            SELECT custom_id, edge_id, source_node_id, target_node_id, directionality, relationship_type,
                   causal_presentation, claim_status, explicitness, statistical_significance,
                   evidence_method, uses_data, tentativeness
            FROM edges
            """,
        )
        print(f"[load] edges read in {time.perf_counter() - t2:.1f}s ({len(edges)} rows)", flush=True)
        t3 = time.perf_counter()
        mappings = _sql_frame(
            onto,
            f"""
            SELECT m.custom_id, m.node_id, m.normalized_label, m.concept_id, m.mapping_source, m.confidence,
                   hc.preferred_label AS concept_label, hc.aliases_json
            FROM {mapping_table} m
            LEFT JOIN head_concepts hc ON hc.concept_id = m.concept_id
            """,
        )
        print(f"[load] mappings read in {time.perf_counter() - t3:.1f}s ({len(mappings)} rows)", flush=True)
        t4 = time.perf_counter()
        head_concepts = _sql_frame(
            onto,
            """
            SELECT concept_id, preferred_label, aliases_json, instance_support
            FROM head_concepts
            """,
        )
        print(f"[load] head concepts read in {time.perf_counter() - t4:.1f}s ({len(head_concepts)} rows)", flush=True)
        t5 = time.perf_counter()
        force_mappings = pd.DataFrame()
        if force_mapping_table:
            available_tables = {
                row[0]
                for row in onto.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            if force_mapping_table in available_tables:
                force_mappings = _sql_frame(
                    onto,
                    f"""
                    SELECT normalized_label, candidate_concept_id, mapping_source, cosine_similarity
                    FROM {force_mapping_table}
                    """,
                )
        print(f"[load] force mappings read in {time.perf_counter() - t5:.1f}s ({len(force_mappings)} rows)", flush=True)
    finally:
        econ.close()
        onto.close()

    t6 = time.perf_counter()
    mappings = _augment_with_lexical_fallback(mappings, head_concepts)
    mappings = _augment_with_force_mappings(mappings, force_mappings)
    print(f"[load] fallback augmentation in {time.perf_counter() - t6:.1f}s", flush=True)
    t7 = time.perf_counter()
    node_map = mappings[mappings["concept_id"].notna()].copy()
    mapped_nodes = nodes.merge(node_map, how="inner", on=["custom_id", "node_id"])
    mapped_nodes = mapped_nodes.merge(works, how="left", on="custom_id")
    print(f"[load] mapped nodes built in {time.perf_counter() - t7:.1f}s ({len(mapped_nodes)} rows)", flush=True)
    t8 = time.perf_counter()

    src_nodes = mapped_nodes.rename(
        columns={
            "node_id": "source_node_id",
            "concept_id": "source_concept_id",
            "concept_label": "source_concept_label",
            "countries_json": "source_countries_json",
            "unit_of_analysis_json": "source_units_json",
            "context_note": "source_context_note",
        }
    )
    dst_nodes = mapped_nodes.rename(
        columns={
            "node_id": "target_node_id",
            "concept_id": "target_concept_id",
            "concept_label": "target_concept_label",
            "countries_json": "target_countries_json",
            "unit_of_analysis_json": "target_units_json",
            "context_note": "target_context_note",
        }
    )

    edge_instances = (
        edges.merge(
            src_nodes[
                [
                    "custom_id",
                    "source_node_id",
                    "source_concept_id",
                    "source_concept_label",
                    "source_countries_json",
                    "source_units_json",
                    "source_context_note",
                ]
            ],
            how="inner",
            on=["custom_id", "source_node_id"],
        )
        .merge(
            dst_nodes[
                [
                    "custom_id",
                    "target_node_id",
                    "target_concept_id",
                    "target_concept_label",
                    "target_countries_json",
                    "target_units_json",
                    "target_context_note",
                ]
            ],
            how="inner",
            on=["custom_id", "target_node_id"],
        )
        .merge(works, how="left", on="custom_id")
    )
    edge_instances = edge_instances[
        edge_instances["source_concept_id"] != edge_instances["target_concept_id"]
    ].copy()
    print(f"[load] edge instances joined in {time.perf_counter() - t8:.1f}s ({len(edge_instances)} rows)", flush=True)
    t9 = time.perf_counter()
    edge_instances["derived_stability"] = derive_stability_series(edge_instances)
    print(f"[load] stability derived in {time.perf_counter() - t9:.1f}s", flush=True)
    return edge_instances


def build_hybrid_corpus(edge_instances: pd.DataFrame) -> pd.DataFrame:
    if edge_instances.empty:
        return pd.DataFrame()

    rows = edge_instances.copy()
    rows["paper_id"] = rows["custom_id"].astype(str)
    rows["year"] = pd.to_numeric(rows["publication_year"], errors="coerce").fillna(0).astype(int)
    rows["title"] = rows["title"].fillna("").astype(str)
    rows["authors"] = ""
    rows["venue"] = rows["source_display_name"].fillna("").astype(str)
    rows["source"] = rows["bucket"].fillna("").astype(str)
    rows["src_code"] = rows["source_concept_id"].astype(str)
    rows["dst_code"] = rows["target_concept_id"].astype(str)
    rows["src_label"] = rows["source_concept_label"].fillna(rows["src_code"]).astype(str)
    rows["dst_label"] = rows["target_concept_label"].fillna(rows["dst_code"]).astype(str)
    rows["directionality_raw"] = rows["directionality"].fillna("unclear").astype(str)
    rows["relation_type"] = rows["relationship_type"].fillna("other").astype(str)
    rows["evidence_type"] = rows["evidence_method"].fillna("do_not_know").astype(str)
    rows["edge_kind"] = rows["evidence_type"].map(
        lambda value: "directed_causal" if is_directed_causal_method(value) else "undirected_noncausal"
    )
    rows["is_causal"] = rows["edge_kind"] == "directed_causal"

    undirected_mask = rows["edge_kind"] == "undirected_noncausal"
    swap_mask = undirected_mask & (rows["src_code"] > rows["dst_code"])
    swap_cols = [("src_code", "dst_code"), ("src_label", "dst_label")]
    for left, right in swap_cols:
        left_vals = rows.loc[swap_mask, left].copy()
        rows.loc[swap_mask, left] = rows.loc[swap_mask, right].values
        rows.loc[swap_mask, right] = left_vals.values

    key_cols = [
        "paper_id",
        "year",
        "title",
        "authors",
        "venue",
        "source",
        "src_code",
        "dst_code",
        "src_label",
        "dst_label",
        "edge_kind",
    ]
    rows["uses_data_flag"] = rows["uses_data"].fillna(0).astype(int)
    rows["causal_signal_flag"] = rows["causal_presentation"].isin(["explicit_causal", "implicit_causal"]).astype(int)
    rows["significant_flag"] = rows["statistical_significance"].eq("significant").astype(int)
    rows["informative_method_flag"] = (~rows["evidence_type"].isin(["do_not_know", "other"])).astype(int)

    grouped = (
        rows.groupby(key_cols, sort=False)
        .agg(
            relation_type=("relation_type", "first"),
            evidence_type=("evidence_type", "first"),
            causal_presentation=("causal_presentation", "first"),
            directionality_raw=("directionality_raw", "first"),
            edge_instance_count=("paper_id", "size"),
            stability=("derived_stability", "mean"),
            uses_data_flag=("uses_data_flag", "max"),
            causal_signal_flag=("causal_signal_flag", "max"),
            significant_flag=("significant_flag", "max"),
            informative_method_flag=("informative_method_flag", "max"),
        )
        .reset_index()
    )
    grouped["is_causal"] = grouped["edge_kind"] == "directed_causal"
    grouped["weight"] = (
        grouped["edge_instance_count"].astype(float)
        + 0.25 * grouped["uses_data_flag"].astype(float)
        + 0.25 * grouped["causal_signal_flag"].astype(float)
        + 0.10 * grouped["significant_flag"].astype(float)
        + 0.10 * grouped["informative_method_flag"].astype(float)
    )
    out = grouped.drop(
        columns=["uses_data_flag", "causal_signal_flag", "significant_flag", "informative_method_flag"]
    ).sort_values(
        ["year", "paper_id", "src_code", "dst_code", "edge_kind"],
        ascending=[True, True, True, True, True],
    )
    return out.reset_index(drop=True)


def build_hybrid_manifest(
    hybrid_corpus: pd.DataFrame,
    source_selected_papers: int,
    source_min_year: int,
    source_max_year: int,
    extracted_papers: int,
    extracted_edges: int,
) -> dict[str, Any]:
    if hybrid_corpus.empty:
        return {}
    directed_pairs = hybrid_corpus[hybrid_corpus["edge_kind"] == "directed_causal"][
        ["src_code", "dst_code"]
    ].drop_duplicates()
    undirected_pairs = hybrid_corpus[hybrid_corpus["edge_kind"] == "undirected_noncausal"][
        ["src_code", "dst_code"]
    ].drop_duplicates()
    kind_counts = []
    for kind, frame in hybrid_corpus.groupby("edge_kind", sort=False):
        kind_counts.append(
            {
                "edge_kind": str(kind),
                "normalized_rows": int(len(frame)),
                "distinct_pairs": int(frame[["src_code", "dst_code"]].drop_duplicates().shape[0]),
                "unique_papers": int(frame["paper_id"].nunique()),
            }
        )
    return {
        "source_selected_papers": int(source_selected_papers),
        "source_year_min": int(source_min_year),
        "source_year_max": int(source_max_year),
        "papers_with_extracted_edges": int(extracted_papers),
        "raw_extracted_edges": int(extracted_edges),
        "normalized_benchmark_papers": int(hybrid_corpus["paper_id"].nunique()),
        "normalized_hybrid_rows": int(len(hybrid_corpus)),
        "normalized_directed_rows": int((hybrid_corpus["edge_kind"] == "directed_causal").sum()),
        "normalized_undirected_rows": int((hybrid_corpus["edge_kind"] == "undirected_noncausal").sum()),
        "unique_papers_in_hybrid_corpus": int(hybrid_corpus["paper_id"].nunique()),
        "unique_concepts_in_hybrid_corpus": int(
            pd.Index(hybrid_corpus["src_code"]).union(pd.Index(hybrid_corpus["dst_code"])).nunique()
        ),
        "unique_directed_causal_pairs": int(len(directed_pairs)),
        "unique_undirected_noncausal_pairs": int(len(undirected_pairs)),
        "edge_kind_counts": kind_counts,
        "field_weighted_citation_impact_note": "FWCI denotes field-weighted citation impact.",
    }


def _pair_cooccurrence_context(
    df: pd.DataFrame,
    allowed_pairs: set[tuple[str, str]] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "cooc_count",
                "first_year_seen",
                "last_year_seen",
                "support_source_mix_json",
                "support_method_mix_json",
            ]
        )

    paper_nodes: dict[str, set[str]] = {}
    paper_year: dict[str, int] = {}
    paper_sources: defaultdict[str, list[str]] = defaultdict(list)
    paper_methods: defaultdict[str, list[str]] = defaultdict(list)
    keep = [c for c in ["paper_id", "year", "src_code", "dst_code", "source", "evidence_type"] if c in df.columns]
    for row in df[keep].itertuples(index=False):
        pid = str(row.paper_id)
        if pid not in paper_nodes:
            paper_nodes[pid] = set()
            paper_year[pid] = int(row.year)
        paper_nodes[pid].add(str(row.src_code))
        paper_nodes[pid].add(str(row.dst_code))
        paper_year[pid] = min(paper_year[pid], int(row.year))
        if hasattr(row, "source"):
            paper_sources[pid].append(str(getattr(row, "source", "")))
        if hasattr(row, "evidence_type"):
            paper_methods[pid].append(str(getattr(row, "evidence_type", "")))

    records: list[tuple[str, str, int, str, str]] = []
    for pid, nodes in paper_nodes.items():
        ordered = sorted(nodes)
        if len(ordered) < 2:
            continue
        year = paper_year[pid]
        source_mix_json = json.dumps(top_counts(paper_sources.get(pid, []), limit=5), ensure_ascii=True)
        method_mix_json = json.dumps(top_counts(paper_methods.get(pid, []), limit=5), ensure_ascii=True)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                key = (ordered[i], ordered[j])
                if allowed_pairs is not None and key not in allowed_pairs:
                    continue
                records.append((key[0], key[1], year, source_mix_json, method_mix_json))
    if not records:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "cooc_count",
                "first_year_seen",
                "last_year_seen",
                "support_source_mix_json",
                "support_method_mix_json",
            ]
        )
    pairs = pd.DataFrame(records, columns=["u", "v", "year", "source_mix_json", "method_mix_json"])

    def _merge_count_json(values: pd.Series) -> str:
        counter: Counter[str] = Counter()
        for value in values.dropna():
            for item in json.loads(str(value) or "[]"):
                counter[str(item.get("value", ""))] += int(item.get("count", 0))
        return json.dumps(
            [{"value": key, "count": int(count)} for key, count in counter.most_common(5) if key],
            ensure_ascii=True,
        )

    out = (
        pairs.groupby(["u", "v"], as_index=False)
        .agg(
            cooc_count=("year", "size"),
            first_year_seen=("year", "min"),
            last_year_seen=("year", "max"),
            support_source_mix_json=("source_mix_json", _merge_count_json),
            support_method_mix_json=("method_mix_json", _merge_count_json),
        )
        .sort_values(["cooc_count", "u", "v"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    return out


def _aggregate_layer_edges(train_df: pd.DataFrame, candidate_kind: str) -> pd.DataFrame:
    kind = normalize_candidate_kind(candidate_kind)
    subset = train_df[candidate_layer_mask(train_df, kind)].copy()
    if subset.empty:
        return pd.DataFrame(columns=["src_code", "dst_code", "edge_weight", "edge_count"])
    if kind == "contextual_pair":
        swap_mask = subset["src_code"].astype(str) > subset["dst_code"].astype(str)
        for left, right in [("src_code", "dst_code"), ("src_label", "dst_label")]:
            if left in subset.columns and right in subset.columns:
                left_vals = subset.loc[swap_mask, left].copy()
                subset.loc[swap_mask, left] = subset.loc[swap_mask, right].values
                subset.loc[swap_mask, right] = left_vals.values
    grouped = (
        subset.groupby(["src_code", "dst_code"], as_index=False)
        .agg(edge_weight=("weight", "sum"), edge_count=("paper_id", "size"))
        .astype({"src_code": str, "dst_code": str})
    )
    return grouped


def _aggregate_support(train_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    contextual_agg = _aggregate_layer_edges(train_df, "contextual_pair")
    ordered_agg = _aggregate_layer_edges(train_df, "ordered_claim")
    causal_claim_agg = _aggregate_layer_edges(train_df, "causal_claim")
    identified_agg = _aggregate_layer_edges(train_df, "identified_causal_claim")

    if contextual_agg.empty:
        support_edges = ordered_agg.copy()
    else:
        rev = contextual_agg.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
        support_edges = pd.concat([ordered_agg, contextual_agg, rev], ignore_index=True)
        support_edges = (
            support_edges.groupby(["src_code", "dst_code"], as_index=False)
            .agg(edge_weight=("edge_weight", "sum"), edge_count=("edge_count", "sum"))
        )
    return {
        "contextual_pair": contextual_agg,
        "ordered_claim": ordered_agg,
        "causal_claim": causal_claim_agg,
        "identified_causal_claim": identified_agg,
        "support_edges": support_edges,
    }


def _ordered_path_features(
    support_edges: pd.DataFrame,
    excluded_edges: set[tuple[str, str]] | set[tuple[str, str]],
    max_len: int = 2,
    max_neighbors_per_mediator: int = 120,
    include_details: bool = True,
) -> pd.DataFrame:
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    if support_edges.empty:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "path_support_raw",
                "mediator_count",
                "hub_penalty_raw",
                "top_mediators_json",
                "top_paths_json",
            ]
        )

    in_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    out_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    support_edge_set = set(zip(support_edges["src_code"], support_edges["dst_code"]))
    for row in support_edges.itertuples(index=False):
        in_map[str(row.dst_code)].append((str(row.src_code), float(row.edge_weight)))
        out_map[str(row.src_code)].append((str(row.dst_code), float(row.edge_weight)))
    deg_map = {n: len(in_map.get(n, [])) + len(out_map.get(n, [])) for n in set(in_map) | set(out_map)}

    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for w in sorted(set(in_map.keys()) & set(out_map.keys())):
        ins = sorted(in_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        outs = sorted(out_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        if not ins or not outs:
            continue
        hub_discount = 1.0 / (1.0 + np.log1p(float(deg_map.get(w, 0))))
        for u, in_w in ins:
            for v, out_w in outs:
                if u == v or (u, v) in excluded_edges:
                    continue
                contrib = float(in_w * out_w)
                support = contrib * hub_discount
                penalty = contrib * (1.0 - hub_discount)
                key = (u, v)
                slot = candidates.setdefault(
                    key,
                    {
                        "path_support_raw": 0.0,
                        "hub_penalty_raw": 0.0,
                        "mediators": defaultdict(float) if include_details else None,
                        "paths": [] if include_details else None,
                    },
                )
                slot["path_support_raw"] += support
                slot["hub_penalty_raw"] += penalty
                if include_details:
                    slot["mediators"][w] += support
                    slot["paths"].append({"path": [u, w, v], "score": support, "len": 2})

    if max_len >= 3:
        l3_cap = min(max_neighbors_per_mediator, 30)
        out_limited = {
            src: sorted(targets, key=lambda t: t[1], reverse=True)[:l3_cap]
            for src, targets in out_map.items()
        }
        for u, uv_targets in out_limited.items():
            for w1, u_w1 in uv_targets:
                for w2, w1_w2 in out_limited.get(w1, []):
                    for v, w2_v in out_limited.get(w2, []):
                        if u == v or (u, v) in excluded_edges:
                            continue
                        hub1 = 1.0 + np.log1p(float(deg_map.get(w1, 0)))
                        hub2 = 1.0 + np.log1p(float(deg_map.get(w2, 0)))
                        hub_discount = 1.0 / (hub1 * hub2)
                        contrib = float(u_w1 * w1_w2 * w2_v)
                        support = contrib * hub_discount
                        penalty = contrib * (1.0 - hub_discount)
                        key = (u, v)
                        slot = candidates.setdefault(
                            key,
                            {
                                "path_support_raw": 0.0,
                                "hub_penalty_raw": 0.0,
                                "mediators": defaultdict(float) if include_details else None,
                                "paths": [] if include_details else None,
                            },
                        )
                        slot["path_support_raw"] += support
                        slot["hub_penalty_raw"] += penalty
                        if include_details:
                            slot["paths"].append({"path": [u, w1, w2, v], "score": support, "len": 3})

    rows: list[dict[str, Any]] = []
    for (u, v), payload in candidates.items():
        mediators_json = "[]"
        top_paths_json = "[]"
        mediator_count = 0
        if include_details:
            mediators = [
                {"mediator": mediator, "score": float(score)}
                for mediator, score in sorted(payload["mediators"].items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            top_paths = sorted(payload["paths"], key=lambda item: float(item["score"]), reverse=True)[:10]
            mediators_json = json.dumps(mediators, ensure_ascii=True)
            top_paths_json = json.dumps(top_paths, ensure_ascii=True)
            mediator_count = int(len(payload["mediators"]))
        rows.append(
            {
                "u": u,
                "v": v,
                "path_support_raw": float(payload["path_support_raw"]),
                "mediator_count": mediator_count,
                "hub_penalty_raw": float(payload["hub_penalty_raw"]),
                "top_mediators_json": mediators_json,
                "top_paths_json": top_paths_json,
            }
        )
    out = pd.DataFrame(rows)
    if debug_timing:
        t1 = time.perf_counter()
        print(
            f"[_ordered_path_features] support={len(support_edges)} excluded={len(excluded_edges)} "
            f"candidates={len(out)} total={t1-t0:.2f}s",
            flush=True,
        )
    return out


def _ordered_motif_features(
    support_edges: pd.DataFrame,
    excluded_edges: set[tuple[str, str]] | set[tuple[str, str]],
    max_neighbors_per_mediator: int = 120,
    include_details: bool = True,
) -> pd.DataFrame:
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    if support_edges.empty:
        return pd.DataFrame(columns=["u", "v", "motif_count", "motif_bonus_raw", "top_motif_mediators_json"])

    edge_agg = (
        support_edges.groupby(["src_code", "dst_code"], as_index=False)
        .agg(edge_count=("edge_count", "sum"), edge_weight=("edge_weight", "sum"))
        .sort_values("edge_count", ascending=False)
    )
    in_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    out_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in edge_agg.itertuples(index=False):
        in_map[str(row.dst_code)].append((str(row.src_code), float(row.edge_count)))
        out_map[str(row.src_code)].append((str(row.dst_code), float(row.edge_count)))

    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for w in sorted(set(in_map) & set(out_map)):
        ins = sorted(in_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        outs = sorted(out_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        for u, in_count in ins:
            for v, out_count in outs:
                if u == v or (u, v) in excluded_edges:
                    continue
                contrib = float(np.sqrt(in_count * out_count))
                slot = candidates.setdefault(
                    (u, v),
                    {"motif_count": 0, "motif_bonus_raw": 0.0, "mediators": defaultdict(float) if include_details else None},
                )
                slot["motif_count"] += 1
                slot["motif_bonus_raw"] += contrib
                if include_details:
                    slot["mediators"][w] += contrib

    rows: list[dict[str, Any]] = []
    for (u, v), payload in candidates.items():
        mediator_json = "[]"
        if include_details:
            mediator_list = [
                {"mediator": mediator, "score": float(score)}
                for mediator, score in sorted(payload["mediators"].items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            mediator_json = json.dumps(mediator_list, ensure_ascii=True)
        rows.append(
            {
                "u": u,
                "v": v,
                "motif_count": int(payload["motif_count"]),
                "motif_bonus_raw": float(payload["motif_bonus_raw"]),
                "top_motif_mediators_json": mediator_json,
            }
        )
    out = pd.DataFrame(rows)
    if debug_timing:
        t1 = time.perf_counter()
        print(
            f"[_ordered_motif_features] support={len(support_edges)} excluded={len(excluded_edges)} "
            f"candidates={len(out)} total={t1-t0:.2f}s",
            flush=True,
        )
    return out


def _canonicalize_ordered_features(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    if df.empty:
        return df
    if normalize_candidate_kind(kind) != "contextual_pair":
        return df.copy()

    rows: list[dict[str, Any]] = []
    grouped = df.groupby(df.apply(lambda row: pair_key(str(row["u"]), str(row["v"])), axis=1), sort=False)
    for key, group in grouped:
        u, v = key
        out: dict[str, Any] = {"u": u, "v": v}
        if "path_support_raw" in group.columns:
            out["path_support_raw"] = float(group["path_support_raw"].sum())
            out["hub_penalty_raw"] = float(group["hub_penalty_raw"].sum())
            out["mediator_count"] = int(group["mediator_count"].sum())
            mediators: Counter[str] = Counter()
            paths: list[dict[str, Any]] = []
            for value in group["top_mediators_json"].fillna("[]"):
                for item in json.loads(value):
                    mediators[str(item["mediator"])] += float(item["score"])
            for value in group["top_paths_json"].fillna("[]"):
                paths.extend(json.loads(value))
            out["top_mediators_json"] = json.dumps(
                [{"mediator": mediator, "score": float(score)} for mediator, score in mediators.most_common(10)],
                ensure_ascii=True,
            )
            out["top_paths_json"] = json.dumps(sorted(paths, key=lambda item: float(item["score"]), reverse=True)[:10], ensure_ascii=True)
        if "motif_bonus_raw" in group.columns:
            out["motif_bonus_raw"] = float(group["motif_bonus_raw"].sum())
            out["motif_count"] = int(group["motif_count"].sum())
            mediators: Counter[str] = Counter()
            for value in group["top_motif_mediators_json"].fillna("[]"):
                for item in json.loads(value):
                    mediators[str(item["mediator"])] += float(item["score"])
            out["top_motif_mediators_json"] = json.dumps(
                [{"mediator": mediator, "score": float(score)} for mediator, score in mediators.most_common(10)],
                ensure_ascii=True,
            )
        rows.append(out)
    return pd.DataFrame(rows)


def _cooc_gap_bonus(context_count: float, tau: float) -> float:
    if tau <= 0:
        return 0.0
    return float(max(0.0, min(1.0, float(context_count) / float(tau))))


def _cfg_value(cfg: Any, key: str, default: Any) -> Any:
    if is_dataclass(cfg):
        return getattr(cfg, key, default)
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def build_candidate_table_v2(
    train_df: pd.DataFrame,
    cutoff_t: int,
    cfg: Any,
) -> pd.DataFrame:
    if train_df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])

    candidate_kind_input = str(_cfg_value(cfg, "candidate_kind", "directed_causal"))
    candidate_kind = normalize_candidate_kind(candidate_kind_input)
    candidate_family_mode_input = str(_cfg_value(cfg, "candidate_family_mode", "path_to_direct"))
    candidate_family_mode = normalize_candidate_family_mode(candidate_family_mode_input)
    tau = float(_cfg_value(cfg, "tau", 2))
    max_path_len = int(_cfg_value(cfg, "max_path_len", 2))
    max_neighbors_per_mediator = int(_cfg_value(cfg, "max_neighbors_per_mediator", 120))
    alpha = float(_cfg_value(cfg, "alpha", 0.5))
    beta = float(_cfg_value(cfg, "beta", 0.2))
    gamma = float(_cfg_value(cfg, "gamma", 0.3))
    delta = float(_cfg_value(cfg, "delta", 0.2))
    cooc_trend_coef = float(_cfg_value(cfg, "cooc_trend_coef", 0.0))
    recency_decay_lambda = float(_cfg_value(cfg, "recency_decay_lambda", 0.0))
    stability_coef = float(_cfg_value(cfg, "stability_coef", 0.0))
    causal_bonus = float(_cfg_value(cfg, "causal_bonus", 0.0))
    field_hub_penalty_scale = float(_cfg_value(cfg, "field_hub_penalty_scale", 0.0))
    fully_open_min_cooc_count = int(_cfg_value(cfg, "fully_open_min_cooc_count", 1))
    fully_open_min_motif_count = int(_cfg_value(cfg, "fully_open_min_motif_count", 1))
    fully_open_min_path_support_raw_cfg = _cfg_value(cfg, "fully_open_min_path_support_raw", 5.0)
    fully_open_min_path_support_raw = (
        None if fully_open_min_path_support_raw_cfg is None else float(fully_open_min_path_support_raw_cfg)
    )
    min_stability = _cfg_value(cfg, "min_stability", None)
    include_details = bool(_cfg_value(cfg, "include_details", False))
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    if debug_timing:
        print(
            (
                f"[build_candidate_table_v2] cutoff={cutoff_t} kind={candidate_kind} "
                f"input={candidate_kind_input} family_mode={candidate_family_mode} start"
            ),
            flush=True,
        )

    df = train_df.copy()
    if min_stability is not None:
        df = df[df["stability"].fillna(-math.inf) >= float(min_stability)]
    if df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])

    base_w = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0).astype(float)
    age = np.maximum(0.0, float(cutoff_t - 1) - pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(float))
    recency_factor = np.exp(-recency_decay_lambda * age) if recency_decay_lambda > 0 else 1.0
    stability = pd.to_numeric(df["stability"], errors="coerce").fillna(0.0).clip(0.0, 1.0).astype(float)
    stability_factor = 1.0 + stability_coef * stability
    causal_factor = 1.0 + causal_bonus * df["is_causal"].astype(bool).astype(float)
    df["weight"] = base_w * recency_factor * stability_factor * causal_factor

    t1 = time.perf_counter()
    if debug_timing:
        print(f"[build_candidate_table_v2] cutoff={cutoff_t} prep={t1-t0:.2f}s rows={len(df)}", flush=True)
    support_payload = _aggregate_support(df)
    support_edges = support_payload["support_edges"]
    t2 = time.perf_counter()
    if debug_timing:
        print(
            f"[build_candidate_table_v2] cutoff={cutoff_t} agg={t2-t1:.2f}s "
            f"ordered={len(support_payload['ordered_claim'])} contextual={len(support_payload['contextual_pair'])} "
            f"causal={len(support_payload['causal_claim'])} strict={len(support_payload['identified_causal_claim'])} "
            f"support={len(support_edges)}",
            flush=True,
        )
    target_agg = support_payload[candidate_kind]
    if candidate_family_mode == "path_to_direct":
        if candidate_kind != "contextual_pair":
            excluded = set((str(r.src_code), str(r.dst_code)) for r in target_agg.itertuples(index=False))
            path_df = _ordered_path_features(
                support_edges,
                excluded_edges=excluded,
                max_len=max_path_len,
                max_neighbors_per_mediator=max_neighbors_per_mediator,
                include_details=include_details,
            )
            motif_df = _ordered_motif_features(
                support_edges,
                excluded_edges=excluded,
                max_neighbors_per_mediator=max_neighbors_per_mediator,
                include_details=include_details,
            )
        else:
            excluded = set(pair_key(str(r.src_code), str(r.dst_code)) for r in target_agg.itertuples(index=False))
            ordered_path_df = _ordered_path_features(
                support_edges,
                excluded_edges=excluded,
                max_len=max_path_len,
                max_neighbors_per_mediator=max_neighbors_per_mediator,
                include_details=include_details,
            )
            ordered_motif_df = _ordered_motif_features(
                support_edges,
                excluded_edges=excluded,
                max_neighbors_per_mediator=max_neighbors_per_mediator,
                include_details=include_details,
            )
            path_df = _canonicalize_ordered_features(ordered_path_df, kind=candidate_kind)
            motif_df = _canonicalize_ordered_features(ordered_motif_df, kind=candidate_kind)
        candidate_df = pd.concat(
            [path_df[["u", "v"]] if not path_df.empty else pd.DataFrame(columns=["u", "v"]),
             motif_df[["u", "v"]] if not motif_df.empty else pd.DataFrame(columns=["u", "v"])],
            ignore_index=True,
        ).drop_duplicates(ignore_index=True)
    else:
        if candidate_kind == "contextual_pair":
            raise ValueError("direct_to_path is not supported for contextual_pair candidates")
        path_df = pd.DataFrame(columns=["u", "v", "path_support_raw", "hub_penalty_raw", "mediator_count", "top_mediators_json", "top_paths_json"])
        motif_df = pd.DataFrame(columns=["u", "v", "motif_count", "motif_bonus_raw", "top_motif_mediators_json"])
        all_path_df = _ordered_path_features(
            support_edges,
            excluded_edges=set(),
            max_len=max_path_len,
            max_neighbors_per_mediator=max_neighbors_per_mediator,
            include_details=include_details,
        )
        all_motif_df = _ordered_motif_features(
            support_edges,
            excluded_edges=set(),
            max_neighbors_per_mediator=max_neighbors_per_mediator,
            include_details=include_details,
        )
        path_supported_pairs = {
            (str(r.u), str(r.v)) for r in all_path_df[["u", "v"]].itertuples(index=False)
        } if not all_path_df.empty else set()
        motif_supported_pairs = {
            (str(r.u), str(r.v)) for r in all_motif_df[["u", "v"]].itertuples(index=False)
        } if not all_motif_df.empty else set()
        excluded_existing_path_pairs = path_supported_pairs.union(motif_supported_pairs)
        candidate_df = (
            target_agg[["src_code", "dst_code"]]
            .rename(columns={"src_code": "u", "dst_code": "v"})
            .astype(str)
        )
        if excluded_existing_path_pairs:
            candidate_df = candidate_df[
                ~candidate_df.apply(lambda row: (str(row["u"]), str(row["v"])) in excluded_existing_path_pairs, axis=1)
            ].copy()
        candidate_df = candidate_df.drop_duplicates(ignore_index=True)
    t3 = time.perf_counter()
    if debug_timing:
        print(
            f"[build_candidate_table_v2] cutoff={cutoff_t} struct={t3-t2:.2f}s "
            f"path={len(path_df)} motif={len(motif_df)}",
            flush=True,
        )

    candidate_keys: set[tuple[str, str]] = set((str(r.u), str(r.v)) for r in candidate_df[["u", "v"]].itertuples(index=False))
    if not candidate_keys:
        return pd.DataFrame(columns=["u", "v", "score"])

    allowed_context_pairs = {pair_key(u, v) for u, v in candidate_keys}
    context_pairs = _pair_cooccurrence_context(df, allowed_pairs=allowed_context_pairs)
    t4 = time.perf_counter()
    if debug_timing:
        print(
            f"[build_candidate_table_v2] cutoff={cutoff_t} context={t4-t3:.2f}s "
            f"cands={len(candidate_keys)} context_rows={len(context_pairs)}",
            flush=True,
        )
    context_map = {
        pair_key(str(row.u), str(row.v)): (
            int(row.cooc_count),
            int(row.first_year_seen),
            int(row.last_year_seen),
        )
        for row in context_pairs.itertuples(index=False)
    }

    out = candidate_df.copy()
    out["candidate_kind"] = candidate_kind
    out["candidate_kind_input"] = candidate_kind_input
    out["candidate_family_mode"] = candidate_family_mode
    out["candidate_family_mode_input"] = candidate_family_mode_input
    out["candidate_layer"] = candidate_kind
    out["main_anchor_layer"] = "causal_claim"
    out["strict_anchor_layer"] = "identified_causal_claim"
    if candidate_family_mode == "direct_to_path":
        out["main_anchor_event"] = "path_emergence"
        out["strict_anchor_event"] = "path_emergence"
        out["evaluation_target_main"] = "future_path_emergence_around_existing_causal_claim"
        out["evaluation_target_strict"] = "future_path_emergence_around_existing_identified_causal_claim"
    else:
        out["main_anchor_event"] = "first_appearance"
        out["strict_anchor_event"] = "first_appearance"
        out["evaluation_target_main"] = "future_first_appearance_in_causal_claim"
        out["evaluation_target_strict"] = "future_first_appearance_in_identified_causal_claim"

    if not path_df.empty:
        out = out.merge(
            path_df[
                ["u", "v", "path_support_raw", "hub_penalty_raw", "mediator_count", "top_mediators_json", "top_paths_json"]
            ],
            on=["u", "v"],
            how="left",
        )
    else:
        out["path_support_raw"] = 0.0
        out["hub_penalty_raw"] = 0.0
        out["mediator_count"] = 0
        out["top_mediators_json"] = "[]"
        out["top_paths_json"] = "[]"

    if not motif_df.empty:
        out = out.merge(
            motif_df[["u", "v", "motif_count", "motif_bonus_raw", "top_motif_mediators_json"]],
            on=["u", "v"],
            how="left",
        )
    else:
        out["motif_count"] = 0
        out["motif_bonus_raw"] = 0.0
        out["top_motif_mediators_json"] = "[]"

    if not context_pairs.empty:
        context_join = context_pairs.rename(columns={"u": "context_u", "v": "context_v"})
        u_arr = out["u"].astype(str).to_numpy()
        v_arr = out["v"].astype(str).to_numpy()
        out["context_u"] = np.where(u_arr <= v_arr, u_arr, v_arr)
        out["context_v"] = np.where(u_arr <= v_arr, v_arr, u_arr)
        out = out.merge(context_join, on=["context_u", "context_v"], how="left")
        out = out.drop(columns=["context_u", "context_v"])
    else:
        out["cooc_count"] = 0
        out["first_year_seen"] = np.nan
        out["last_year_seen"] = np.nan
        out["support_source_mix_json"] = "[]"
        out["support_method_mix_json"] = "[]"

    out["path_support_raw"] = pd.to_numeric(out["path_support_raw"], errors="coerce").fillna(0.0)
    out["hub_penalty_raw"] = pd.to_numeric(out["hub_penalty_raw"], errors="coerce").fillna(0.0)
    out["motif_bonus_raw"] = pd.to_numeric(out["motif_bonus_raw"], errors="coerce").fillna(0.0)
    out["mediator_count"] = pd.to_numeric(out["mediator_count"], errors="coerce").fillna(0).astype(int)
    out["motif_count"] = pd.to_numeric(out["motif_count"], errors="coerce").fillna(0).astype(int)
    out["cooc_count"] = pd.to_numeric(out["cooc_count"], errors="coerce").fillna(0).astype(int)
    out["top_mediators_json"] = out["top_mediators_json"].fillna("[]")
    out["top_paths_json"] = out["top_paths_json"].fillna("[]")
    out["top_motif_mediators_json"] = out["top_motif_mediators_json"].fillna("[]")
    out["support_source_mix_json"] = out.get("support_source_mix_json", "[]")
    out["support_method_mix_json"] = out.get("support_method_mix_json", "[]")
    span = (
        pd.to_numeric(out["last_year_seen"], errors="coerce").fillna(0)
        - pd.to_numeric(out["first_year_seen"], errors="coerce").fillna(0)
        + 1
    ).clip(lower=1)
    out["cooc_trend_raw"] = out["cooc_count"].astype(float) / span.astype(float)
    out["gap_bonus"] = np.clip(out["cooc_count"].astype(float) / float(max(tau, 1)), 0.0, 1.0)
    out = out[
        (out["u"] != out["v"])
        & ((out["path_support_raw"] > 0) | (out["motif_bonus_raw"] > 0) | (out["gap_bonus"] > 0))
    ].copy()
    if out.empty:
        return out

    out["path_support_norm"] = min_max_normalize(out["path_support_raw"])
    out["motif_bonus_norm"] = min_max_normalize(out["motif_bonus_raw"])
    out["hub_penalty"] = min_max_normalize(out["hub_penalty_raw"])
    out["cooc_trend_norm"] = min_max_normalize(out["cooc_trend_raw"])
    out["field_same_group"] = (out["u"].astype(str).str[0] == out["v"].astype(str).str[0]).astype(int)
    out["score"] = (
        alpha * out["path_support_norm"]
        + beta * out["gap_bonus"]
        + gamma * out["motif_bonus_norm"]
        - delta * out["hub_penalty"]
        + cooc_trend_coef * out["cooc_trend_norm"]
        - field_hub_penalty_scale * out["hub_penalty"] * out["field_same_group"]
    )

    label_rows = pd.concat(
        [
            df[["src_code", "src_label"]].rename(columns={"src_code": "code", "src_label": "label"}),
            df[["dst_code", "dst_label"]].rename(columns={"dst_code": "code", "dst_label": "label"}),
        ],
        ignore_index=True,
    ).dropna(subset=["code"])
    label_map = (
        label_rows.assign(code=label_rows["code"].astype(str), label=label_rows["label"].astype(str))
        .drop_duplicates(subset=["code", "label"])
        .groupby("code", as_index=False)
        .agg(label=("label", "first"))
    )
    code_to_label = {str(r.code): str(r.label) for r in label_map.itertuples(index=False)}

    def _direct_maps(frame: pd.DataFrame, undirected: bool = False) -> tuple[dict[Any, int], dict[Any, float]]:
        count_map: dict[Any, int] = {}
        weight_map: dict[Any, float] = {}
        for row in frame.itertuples(index=False):
            key: Any = pair_key(str(row.src_code), str(row.dst_code)) if undirected else (str(row.src_code), str(row.dst_code))
            count_map[key] = int(row.edge_count)
            weight_map[key] = float(row.edge_weight)
        return count_map, weight_map

    contextual_count_map, contextual_weight_map = _direct_maps(support_payload["contextual_pair"], undirected=True)
    ordered_count_map, ordered_weight_map = _direct_maps(support_payload["ordered_claim"])
    causal_count_map, causal_weight_map = _direct_maps(support_payload["causal_claim"])
    strict_count_map, strict_weight_map = _direct_maps(support_payload["identified_causal_claim"])
    direct_count_map_by_kind = {
        "contextual_pair": contextual_count_map,
        "ordered_claim": ordered_count_map,
        "causal_claim": causal_count_map,
        "identified_causal_claim": strict_count_map,
    }
    direct_weight_map_by_kind = {
        "contextual_pair": contextual_weight_map,
        "ordered_claim": ordered_weight_map,
        "causal_claim": causal_weight_map,
        "identified_causal_claim": strict_weight_map,
    }

    def _focal_mediator_json(value: str) -> tuple[str | None, str | None]:
        items = json.loads(str(value or "[]"))
        if not items:
            return None, None
        mediator = str(items[0].get("mediator", "")).strip()
        if not mediator:
            return None, None
        return mediator, code_to_label.get(mediator, mediator)

    def _candidate_status(row: pd.Series) -> str:
        if candidate_family_mode == "direct_to_path":
            strict_present = int(row["identified_causal_support_count"]) > 0
            main_present = int(row["causal_claim_support_count"]) > 0
            if strict_present:
                return "strict_direct_present__path_missing"
            if main_present:
                return "main_direct_present__path_missing"
            return "ordered_direct_present__path_missing"
        main_present = int(row["causal_claim_support_count"]) > 0
        strict_present = int(row["identified_causal_support_count"]) > 0
        ordered_present = int(row["ordered_support_count"]) > 0
        contextual_present = int(row["contextual_support_count"]) > 0
        if strict_present and not main_present:
            return "strict_present__main_missing"
        if main_present and not strict_present:
            return "main_present__strict_missing"
        if ordered_present and not main_present:
            return "ordered_present__main_missing"
        if contextual_present and not ordered_present and not main_present:
            return "contextual_present__ordered_missing__main_missing"
        return "fully_open"

    def _closure_state(row: pd.Series) -> str:
        if candidate_family_mode == "direct_to_path":
            return "path_gap"
        status = row["candidate_status_at_t"]
        if status == "strict_present__main_missing":
            return "strict_gap"
        if status == "main_present__strict_missing":
            return "identification_gap"
        if status == "ordered_present__main_missing":
            return "causal_gap"
        if status == "contextual_present__ordered_missing__main_missing":
            return "relation_gap"
        return "open"

    def _candidate_family(row: pd.Series) -> str:
        if candidate_family_mode == "direct_to_path":
            return "direct_to_path"
        status = row["candidate_status_at_t"]
        if status in {"ordered_present__main_missing", "main_present__strict_missing"}:
            return "mediator_expansion"
        if status == "strict_present__main_missing":
            return "pending_family_assignment"
        return "path_to_direct"

    def _candidate_subfamily(row: pd.Series) -> str:
        status = row["candidate_status_at_t"]
        if candidate_family_mode == "direct_to_path":
            if status == "strict_direct_present__path_missing":
                return "identified_direct_to_path"
            if status == "main_direct_present__path_missing":
                return "causal_direct_to_path"
            return "ordered_direct_to_path"
        if status == "main_present__strict_missing":
            return "causal_to_identified"
        if status == "ordered_present__main_missing":
            return "ordered_to_causal"
        if status == "contextual_present__ordered_missing__main_missing":
            return "contextual_to_ordered"
        return "fully_open_frontier"

    def _candidate_scope_bucket(row: pd.Series) -> str:
        status = row["candidate_status_at_t"]
        if candidate_family_mode == "direct_to_path":
            return "direct_present_path_missing"
        if status in {"ordered_present__main_missing", "main_present__strict_missing"}:
            return "anchored_progression"
        if status == "contextual_present__ordered_missing__main_missing":
            return "contextual_progression"
        return "fully_open"

    def _evidence_tags(row: pd.Series) -> str:
        tags: list[str] = []
        try:
            top_paths = json.loads(str(row["top_paths_json"] or "[]"))
        except json.JSONDecodeError:
            top_paths = []
        lengths = {int(item.get("len", 0)) for item in top_paths if int(item.get("len", 0)) > 0}
        if 2 in lengths:
            tags.append("directed_chain2")
        if any(length >= 3 for length in lengths):
            tags.append("directed_chain3")
        if int(row["motif_count"]) > 0:
            tags.append("branching_neighborhood")
        if int(row["mediator_count"]) >= 2:
            tags.append("parallel_mediators")
        if int(row["ordered_support_count"]) == 0 and float(row["path_support_raw"]) > 0:
            tags.append("open_triad")
        return json.dumps(sorted(set(tags)), ensure_ascii=True)

    def _local_topology(row: pd.Series) -> str:
        tags = set(json.loads(str(row["evidence_motif_tags_json"] or "[]")))
        if "parallel_mediators" in tags and "directed_chain3" in tags:
            return "branched_multi_step"
        if "parallel_mediators" in tags or "branching_neighborhood" in tags:
            return "branched"
        if "directed_chain3" in tags:
            return "serial_multi_step"
        if "directed_chain2" in tags:
            return "serial_path"
        return "sparse_local"

    out["pair_key"] = [pair_key(str(r.u), str(r.v)) for r in out.itertuples(index=False)]
    out["source_id"] = out["u"].astype(str)
    out["target_id"] = out["v"].astype(str)
    out["source_label"] = out["source_id"].map(code_to_label).fillna(out["source_id"])
    out["target_label"] = out["target_id"].map(code_to_label).fillna(out["target_id"])
    out["candidate_id"] = [
        f"{candidate_kind}:{candidate_family_mode}:{int(cutoff_t)}:{str(r.u)}->{str(r.v)}"
        for r in out[["u", "v"]].itertuples(index=False)
    ]
    out["contextual_support_count"] = [
        int(contextual_count_map.get(pair_key(str(r.u), str(r.v)), 0)) for r in out.itertuples(index=False)
    ]
    out["ordered_support_count"] = [
        int(ordered_count_map.get((str(r.u), str(r.v)), 0)) for r in out.itertuples(index=False)
    ]
    out["causal_claim_support_count"] = [
        int(causal_count_map.get((str(r.u), str(r.v)), 0)) for r in out.itertuples(index=False)
    ]
    out["identified_causal_support_count"] = [
        int(strict_count_map.get((str(r.u), str(r.v)), 0)) for r in out.itertuples(index=False)
    ]
    out["contextual_support_weight"] = [
        float(contextual_weight_map.get(pair_key(str(r.u), str(r.v)), 0.0)) for r in out.itertuples(index=False)
    ]
    out["ordered_support_weight"] = [
        float(ordered_weight_map.get((str(r.u), str(r.v)), 0.0)) for r in out.itertuples(index=False)
    ]
    out["causal_claim_support_weight"] = [
        float(causal_weight_map.get((str(r.u), str(r.v)), 0.0)) for r in out.itertuples(index=False)
    ]
    out["identified_causal_support_weight"] = [
        float(strict_weight_map.get((str(r.u), str(r.v)), 0.0)) for r in out.itertuples(index=False)
    ]
    direct_lookup_key = (
        out["pair_key"] if candidate_kind == "contextual_pair" else list(zip(out["u"].astype(str), out["v"].astype(str)))
    )
    out["direct_support_count"] = [
        int(direct_count_map_by_kind[candidate_kind].get(key, 0)) for key in direct_lookup_key
    ]
    out["direct_support_raw"] = [
        float(direct_weight_map_by_kind[candidate_kind].get(key, 0.0)) for key in direct_lookup_key
    ]
    out["support_paper_count"] = out["cooc_count"].astype(int)
    out["support_year_min"] = pd.to_numeric(out["first_year_seen"], errors="coerce").fillna(0).astype(int)
    out["support_year_max"] = pd.to_numeric(out["last_year_seen"], errors="coerce").fillna(0).astype(int)
    out["direct_literature_status_main"] = np.where(out["causal_claim_support_count"] > 0, "present", "missing")
    out["direct_literature_status_strict"] = np.where(out["identified_causal_support_count"] > 0, "present", "missing")
    out["ordered_direct_literature_status"] = np.where(out["ordered_support_count"] > 0, "present", "missing")
    out["contextual_direct_literature_status"] = np.where(out["contextual_support_count"] > 0, "present", "missing")
    out["candidate_status_at_t"] = out.apply(_candidate_status, axis=1)
    if candidate_family_mode == "path_to_direct":
        out = out[out["candidate_status_at_t"] != "strict_present__main_missing"].copy()
        if out.empty:
            return out
    out["closure_state"] = out.apply(_closure_state, axis=1)
    out["candidate_family"] = out.apply(_candidate_family, axis=1)
    out["candidate_subfamily"] = out.apply(_candidate_subfamily, axis=1)
    out["candidate_scope_bucket"] = out.apply(_candidate_scope_bucket, axis=1)
    if candidate_family_mode == "path_to_direct":
        fully_open_mask = out["candidate_subfamily"].astype(str).eq("fully_open_frontier")
        if fully_open_mask.any():
            contextual_motif_ok = (
                (pd.to_numeric(out["cooc_count"], errors="coerce").fillna(0).astype(int) >= int(fully_open_min_cooc_count))
                & (pd.to_numeric(out["motif_count"], errors="coerce").fillna(0).astype(int) >= int(fully_open_min_motif_count))
            )
            if fully_open_min_path_support_raw is None:
                strong_path_ok = pd.Series(False, index=out.index)
            else:
                strong_path_ok = (
                    pd.to_numeric(out["path_support_raw"], errors="coerce").fillna(0.0).astype(float)
                    >= float(fully_open_min_path_support_raw)
                )
            keep_mask = (~fully_open_mask) | contextual_motif_ok | strong_path_ok
            out = out[keep_mask].copy()
            if out.empty:
                return out
    out["evidence_motif_tags_json"] = out.apply(_evidence_tags, axis=1)
    out["local_topology_class"] = out.apply(_local_topology, axis=1)
    focal_pairs = [_focal_mediator_json(value) for value in out["top_mediators_json"]]
    out["focal_mediator_id"] = [item[0] for item in focal_pairs]
    out["focal_mediator_label"] = [item[1] for item in focal_pairs]

    out["direct_support_norm"] = min_max_normalize(out["direct_support_raw"])

    if candidate_family_mode == "direct_to_path":
        out["score"] = (
            0.60 * out["direct_support_norm"]
            + 0.25 * out["cooc_trend_norm"]
            + 0.15 * out["gap_bonus"]
        )

    out = out.sort_values("score", ascending=False).reset_index(drop=True)
    out["rank"] = out.index + 1
    t5 = time.perf_counter()
    if debug_timing:
        print(
            (
                f"[build_candidate_table_v2] cutoff={cutoff_t} kind={candidate_kind} "
                f"rows={len(df)} support={len(support_edges)} path={len(path_df)} motif={len(motif_df)} "
                f"cands={len(candidate_keys)} context={len(context_pairs)} "
                f"prep={t1-t0:.2f}s agg={t2-t1:.2f}s struct={t3-t2:.2f}s "
                f"context={t4-t3:.2f}s score={t5-t4:.2f}s total={t5-t0:.2f}s"
            ),
            flush=True,
        )
    return out


def first_appearance_map_v2(
    corpus_df: pd.DataFrame,
    candidate_kind: str = "directed_causal",
) -> dict[tuple[str, str], int]:
    kind = normalize_candidate_kind(candidate_kind)
    subset = corpus_df[candidate_layer_mask(corpus_df, kind)].copy()
    if subset.empty:
        return {}
    if kind == "contextual_pair":
        swap_mask = subset["src_code"].astype(str) > subset["dst_code"].astype(str)
        for left, right in [("src_code", "dst_code"), ("src_label", "dst_label")]:
            if left in subset.columns and right in subset.columns:
                left_vals = subset.loc[swap_mask, left].copy()
                subset.loc[swap_mask, left] = subset.loc[swap_mask, right].values
                subset.loc[swap_mask, right] = left_vals.values
    grouped = subset.groupby(["src_code", "dst_code"], as_index=False).agg(first_year=("year", "min"))
    return {(str(r.src_code), str(r.dst_code)): int(r.first_year) for r in grouped.itertuples(index=False)}


def first_path_appearance_map_v2(
    corpus_df: pd.DataFrame,
) -> dict[tuple[str, str], int]:
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    if corpus_df.empty:
        return {}

    ordered = corpus_df[candidate_layer_mask(corpus_df, "ordered_claim")][["year", "src_code", "dst_code"]].copy()
    contextual = corpus_df[candidate_layer_mask(corpus_df, "contextual_pair")][["year", "src_code", "dst_code"]].copy()
    if debug_timing:
        print(
            (
                f"[first_path_appearance_map_v2] corpus_rows={len(corpus_df):,} "
                f"ordered_rows={len(ordered):,} contextual_rows={len(contextual):,}"
            ),
            flush=True,
        )
    if not contextual.empty:
        swap_mask = contextual["src_code"].astype(str) > contextual["dst_code"].astype(str)
        left_vals = contextual.loc[swap_mask, "src_code"].copy()
        contextual.loc[swap_mask, "src_code"] = contextual.loc[swap_mask, "dst_code"].values
        contextual.loc[swap_mask, "dst_code"] = left_vals.values
        rev = contextual.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
        support_df = pd.concat([ordered, contextual, rev], ignore_index=True)
    else:
        support_df = ordered.copy()
    if support_df.empty:
        return {}

    support_df["year"] = pd.to_numeric(support_df["year"], errors="coerce").fillna(0).astype(int)
    support_df["src_code"] = support_df["src_code"].astype(str)
    support_df["dst_code"] = support_df["dst_code"].astype(str)
    support_df = support_df.drop_duplicates(subset=["year", "src_code", "dst_code"]).sort_values(
        ["year", "src_code", "dst_code"]
    )
    if debug_timing:
        years = support_df["year"]
        print(
            (
                f"[first_path_appearance_map_v2] support_rows={len(support_df):,} "
                f"years={int(years.min())}-{int(years.max())} "
                f"prep_elapsed={time.perf_counter()-t0:.2f}s"
            ),
            flush=True,
        )

    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    existing_edges: set[tuple[str, str]] = set()
    first_year_map: dict[tuple[str, str], int] = {}

    year_groups = support_df.groupby("year", sort=True)
    total_years = int(support_df["year"].nunique())
    for idx, (year, block) in enumerate(year_groups, start=1):
        batch_edges = {(str(r.src_code), str(r.dst_code)) for r in block.itertuples(index=False)}
        new_edges = batch_edges.difference(existing_edges)
        if not new_edges:
            if debug_timing and (idx == 1 or idx == total_years or idx % 5 == 0):
                print(
                    (
                        f"[first_path_appearance_map_v2] year={int(year)} "
                        f"progress={idx}/{total_years} new_edges=0 "
                        f"existing={len(existing_edges):,} pairs={len(first_year_map):,} "
                        f"elapsed={time.perf_counter()-t0:.2f}s"
                    ),
                    flush=True,
                )
            continue
        for u, v in new_edges:
            existing_edges.add((u, v))
            outgoing[u].add(v)
            incoming[v].add(u)
        for a, b in new_edges:
            for u in incoming.get(a, set()):
                if u != b and (u, b) not in first_year_map:
                    first_year_map[(u, b)] = int(year)
            for v in outgoing.get(b, set()):
                if a != v and (a, v) not in first_year_map:
                    first_year_map[(a, v)] = int(year)
        if debug_timing and (idx == 1 or idx == total_years or idx % 5 == 0):
            print(
                (
                    f"[first_path_appearance_map_v2] year={int(year)} "
                    f"progress={idx}/{total_years} new_edges={len(new_edges):,} "
                    f"existing={len(existing_edges):,} pairs={len(first_year_map):,} "
                    f"elapsed={time.perf_counter()-t0:.2f}s"
                ),
                flush=True,
            )
    if debug_timing:
        print(
            (
                f"[first_path_appearance_map_v2] done pairs={len(first_year_map):,} "
                f"total_elapsed={time.perf_counter()-t0:.2f}s"
            ),
            flush=True,
        )
    return first_year_map


def first_path_appearance_map_for_pairs_v2(
    corpus_df: pd.DataFrame,
    target_pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], int]:
    debug_timing = os.environ.get("FG_TIMING", "").strip() not in {"", "0", "false", "False"}
    t0 = time.perf_counter()
    if corpus_df.empty or not target_pairs:
        return {}

    target_pairs = {(str(u), str(v)) for u, v in target_pairs if str(u) != str(v)}
    if not target_pairs:
        return {}

    ordered = corpus_df[candidate_layer_mask(corpus_df, "ordered_claim")][["year", "src_code", "dst_code"]].copy()
    contextual = corpus_df[candidate_layer_mask(corpus_df, "contextual_pair")][["year", "src_code", "dst_code"]].copy()
    if not contextual.empty:
        swap_mask = contextual["src_code"].astype(str) > contextual["dst_code"].astype(str)
        left_vals = contextual.loc[swap_mask, "src_code"].copy()
        contextual.loc[swap_mask, "src_code"] = contextual.loc[swap_mask, "dst_code"].values
        contextual.loc[swap_mask, "dst_code"] = left_vals.values
        rev = contextual.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
        support_df = pd.concat([ordered, contextual, rev], ignore_index=True)
    else:
        support_df = ordered.copy()
    if support_df.empty:
        return {}

    support_df["year"] = pd.to_numeric(support_df["year"], errors="coerce").fillna(0).astype(int)
    support_df["src_code"] = support_df["src_code"].astype(str)
    support_df["dst_code"] = support_df["dst_code"].astype(str)
    support_df = support_df.drop_duplicates(subset=["year", "src_code", "dst_code"]).sort_values(
        ["year", "src_code", "dst_code"]
    )

    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    existing_edges: set[tuple[str, str]] = set()
    first_year_map: dict[tuple[str, str], int] = {}
    remaining = set(target_pairs)

    if debug_timing:
        years = support_df["year"]
        print(
            (
                f"[first_path_appearance_map_for_pairs_v2] targets={len(target_pairs):,} "
                f"support_rows={len(support_df):,} years={int(years.min())}-{int(years.max())}"
            ),
            flush=True,
        )

    year_groups = support_df.groupby("year", sort=True)
    total_years = int(support_df["year"].nunique())
    for idx, (year, block) in enumerate(year_groups, start=1):
        batch_edges = {(str(r.src_code), str(r.dst_code)) for r in block.itertuples(index=False)}
        new_edges = batch_edges.difference(existing_edges)
        if not new_edges:
            if debug_timing and (idx == 1 or idx == total_years or idx % 5 == 0):
                print(
                    (
                        f"[first_path_appearance_map_for_pairs_v2] year={int(year)} "
                        f"progress={idx}/{total_years} found={len(first_year_map):,}/{len(target_pairs):,} "
                        f"elapsed={time.perf_counter()-t0:.2f}s"
                    ),
                    flush=True,
                )
            continue
        for u, v in new_edges:
            existing_edges.add((u, v))
            outgoing[u].add(v)
            incoming[v].add(u)
        for a, b in new_edges:
            for u in incoming.get(a, set()):
                pair = (u, b)
                if u != b and pair in remaining:
                    first_year_map[pair] = int(year)
                    remaining.remove(pair)
            for v in outgoing.get(b, set()):
                pair = (a, v)
                if a != v and pair in remaining:
                    first_year_map[pair] = int(year)
                    remaining.remove(pair)
        if debug_timing and (idx == 1 or idx == total_years or idx % 5 == 0):
            print(
                (
                    f"[first_path_appearance_map_for_pairs_v2] year={int(year)} "
                    f"progress={idx}/{total_years} found={len(first_year_map):,}/{len(target_pairs):,} "
                    f"remaining={len(remaining):,} elapsed={time.perf_counter()-t0:.2f}s"
                ),
                flush=True,
            )
        if not remaining:
            break
    if debug_timing:
        print(
            (
                f"[first_path_appearance_map_for_pairs_v2] done found={len(first_year_map):,}/{len(target_pairs):,} "
                f"total_elapsed={time.perf_counter()-t0:.2f}s"
            ),
            flush=True,
        )
    return first_year_map


def first_candidate_event_year_map_v2(
    corpus_df: pd.DataFrame,
    candidate_kind: str = "directed_causal",
    candidate_family_mode: str = "path_to_direct",
) -> dict[tuple[str, str], int]:
    family_mode = normalize_candidate_family_mode(candidate_family_mode)
    if family_mode == "direct_to_path":
        return first_path_appearance_map_v2(corpus_df)
    return first_appearance_map_v2(corpus_df, candidate_kind=candidate_kind)


def future_edges_for_v2(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {
        edge
        for edge, year in first_year_map.items()
        if int(cutoff_t) <= int(year) <= int(cutoff_t + horizon_h)
    }


def check_no_leakage_v2(
    corpus_df: pd.DataFrame,
    cutoff_t: int,
    horizon_h: int,
    candidate_kind: str = "directed_causal",
    candidate_family_mode: str = "path_to_direct",
    first_year_map: dict[tuple[str, str], int] | None = None,
) -> bool:
    kind = normalize_candidate_kind(candidate_kind)
    family_mode = normalize_candidate_family_mode(candidate_family_mode)
    fmap = (
        first_year_map
        if first_year_map is not None
        else first_candidate_event_year_map_v2(
            corpus_df,
            candidate_kind=kind,
            candidate_family_mode=family_mode,
        )
    )
    train_edges = {
        edge
        for edge, year in fmap.items()
        if int(year) <= int(cutoff_t - 1)
    }
    positives = future_edges_for_v2(fmap, cutoff_t=cutoff_t, horizon_h=horizon_h)
    return len(train_edges.intersection(positives)) == 0
