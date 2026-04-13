from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ontology_v1 import normalize_label
from src.ontology_v2 import token_set
ONTOLOGY_DIR = ROOT / "data/ontology_v2"
EXTRACTIONS_PATH = (
    ROOT
    / "data/production/frontiergraph_extraction_v2"
    / "fwci_core150_adj150/merged"
    / "fwci_core150_adj150_extractions.jsonl.gz"
)
MAPPING_PATH = ONTOLOGY_DIR / "extraction_label_mapping_v2.parquet"
ONTOLOGY_PATH = ONTOLOGY_DIR / "ontology_v2_final.json"
PAPER_OUT_DIR = ROOT / "outputs/paper/45_ontology_grounding_sensitivity"

LINK_THRESHOLD = 0.85
SOFT_THRESHOLD = 0.75
CANDIDATE_THRESHOLD = 0.65
RESCUE_THRESHOLD = 0.50
PRIMARY_THRESHOLD = 0.75

AUDIT_IMPACT_THRESHOLD = 0.90
AMBIGUITY_IMPACT_THRESHOLD = 0.80
AMBIGUITY_GAP_THRESHOLD = 0.02
MAX_CLUSTER_LABELS = 10_000
MAX_DETAILED_AUDIT_ROWS = 12_000
K_NEIGHBORS = 20
NEIGHBOR_SIM_THRESHOLD = 0.72
TOP_K_PAIR_OVERLAP = 100

STOP_TOKENS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
}

GENERIC_LABELS = {
    "factor",
    "factors",
    "government",
    "governments",
    "groups",
    "industry",
    "labor",
    "model",
    "models",
    "output",
    "outputs",
    "parameter",
    "parameters",
    "policymakers",
    "region",
    "regions",
    "returns",
    "sample",
    "samples",
    "temperature",
    "volume",
}

OPERATIONAL_TOKENS = {
    "capita",
    "consumption",
    "efficiency",
    "emissions",
    "expenditure",
    "expenditures",
    "frictions",
    "growth",
    "index",
    "indices",
    "intensity",
    "per",
    "premium",
    "rate",
    "rates",
    "risk",
    "search",
    "sex",
    "share",
    "shares",
    "shock",
    "shocks",
    "uncertainty",
    "use",
    "uses",
    "volatility",
}

BAD_TARGET_TERMS = {
    "dreamspark",
    "manual",
    "phriction",
    "sex manual",
    "sex technology",
    "toxicity",
}

REVIEWABLE_PROPOSALS = {
    "attach_existing_broad",
    "add_alias_to_existing",
    "propose_new_concept_family",
}

SOURCE_PRIORITY_BONUS = {
    "jel": 0.40,
    "openalex_topic": 0.30,
    "openalex_keyword": 0.20,
    "wikipedia": 0.05,
    "wikidata": 0.00,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build open-world grounding overlay outputs for ontology v2.")
    parser.add_argument("--mapping", default=str(MAPPING_PATH))
    parser.add_argument("--extractions", default=str(EXTRACTIONS_PATH))
    parser.add_argument("--ontology", default=str(ONTOLOGY_PATH))
    parser.add_argument("--out-dir", default=str(ONTOLOGY_DIR))
    parser.add_argument("--paper-out-dir", default=str(PAPER_OUT_DIR))
    parser.add_argument(
        "--embedding-backend",
        default="tfidf_char_fallback",
        choices=["tfidf_char_fallback"],
        help="Current no-spend backend for rescue clustering.",
    )
    return parser.parse_args()


def score_band(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "unresolved"
    value = float(score)
    if value >= LINK_THRESHOLD:
        return "linked"
    if value >= SOFT_THRESHOLD:
        return "soft"
    if value >= CANDIDATE_THRESHOLD:
        return "candidate"
    if value >= RESCUE_THRESHOLD:
        return "rescue"
    return "unresolved"


def provisional_action(band: str) -> str:
    return {
        "linked": "accept_direct",
        "soft": "accept_soft",
        "candidate": "candidate_broader",
        "rescue": "rescue_review",
        "unresolved": "unresolved_review",
    }[band]


def content_tokens(label: str) -> set[str]:
    return {tok for tok in token_set(label) if tok and tok not in STOP_TOKENS}


def sequence_ratio(left: str, right: str) -> float:
    import difflib

    return difflib.SequenceMatcher(None, left, right).ratio()


def is_probably_generic(label: str) -> bool:
    tokens = content_tokens(label)
    if not tokens:
        return True
    if len(tokens) == 1 and next(iter(tokens)) in GENERIC_LABELS:
        return True
    return normalize_label(label) in GENERIC_LABELS


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def canonical_undirected(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def parse_extractions(extractions_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    label_stats: dict[str, dict[str, Any]] = {}
    edge_rows: list[dict[str, Any]] = []

    def ensure_label(label: str) -> dict[str, Any]:
        if label not in label_stats:
            label_stats[label] = {
                "unique_papers": 0,
                "unique_edge_instances": 0,
                "directed_edge_instances": 0,
                "first_year": None,
                "last_year": None,
            }
        return label_stats[label]

    with gzip.open(extractions_path, "rt", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, start=1):
            rec = json.loads(line)
            output = rec.get("output", {})
            if not isinstance(output, dict):
                continue

            paper_id = str(rec.get("custom_id") or rec.get("openalex_work_id") or "")
            year_raw = rec.get("publication_year")
            year = int(year_raw) if year_raw not in (None, "") else None

            node_to_label: dict[str, str] = {}
            labels_in_paper: set[str] = set()
            for node in output.get("nodes", []):
                label = normalize_label(str(node.get("label", "")).strip())
                node_id = str(node.get("node_id", "")).strip()
                if not label or not node_id:
                    continue
                node_to_label[node_id] = label
                labels_in_paper.add(label)

            for label in labels_in_paper:
                stats = ensure_label(label)
                stats["unique_papers"] += 1
                if year is not None:
                    stats["first_year"] = year if stats["first_year"] is None else min(stats["first_year"], year)
                    stats["last_year"] = year if stats["last_year"] is None else max(stats["last_year"], year)

            seen_incidents: set[tuple[str, str]] = set()
            for edge in output.get("edges", []):
                source_label = node_to_label.get(str(edge.get("source_node_id", "")).strip())
                target_label = node_to_label.get(str(edge.get("target_node_id", "")).strip())
                if not source_label or not target_label:
                    continue
                edge_id = str(edge.get("edge_id") or f"{source_label}->{target_label}")
                directionality = str(edge.get("directionality", "")).strip().lower()
                edge_kind = "directed" if directionality == "directed" else "undirected"

                for label in {source_label, target_label}:
                    incident_key = (label, edge_id)
                    if incident_key in seen_incidents:
                        continue
                    seen_incidents.add(incident_key)
                    stats = ensure_label(label)
                    stats["unique_edge_instances"] += 1
                    if edge_kind == "directed":
                        stats["directed_edge_instances"] += 1

                edge_rows.append(
                    {
                        "paper_id": paper_id,
                        "year": year,
                        "source_label": source_label,
                        "target_label": target_label,
                        "edge_kind": edge_kind,
                    }
                )
            if line_num % 50_000 == 0:
                print(f"  parsed {line_num:,} papers …", flush=True)

    metrics_df = (
        pd.DataFrame(
            [
                {
                    "label": label,
                    **stats,
                }
                for label, stats in label_stats.items()
            ]
        )
        .sort_values("label")
        .reset_index(drop=True)
    )
    edge_df = pd.DataFrame(edge_rows)
    return metrics_df, edge_df


@dataclass
class OntologyConcept:
    concept_id: str
    label: str
    source: str
    domain: str
    normalized_label: str
    labels_norm: set[str]
    tokens: set[str]


def load_ontology(ontology_path: Path) -> tuple[list[OntologyConcept], dict[str, set[int]], dict[str, set[int]]]:
    raw = json.loads(ontology_path.read_text(encoding="utf-8"))
    concepts: list[OntologyConcept] = []
    by_alt_label: dict[str, set[int]] = defaultdict(set)
    by_token: dict[str, set[int]] = defaultdict(set)

    for idx, row in enumerate(raw):
        alt_labels = {normalize_label(str(row.get("label", "")).strip())}
        for source_row in row.get("_sources", []):
            alt = normalize_label(str(source_row.get("label", "")).strip())
            if alt:
                alt_labels.add(alt)
        alt_labels.discard("")
        tokens = set()
        for alt in alt_labels:
            tokens |= content_tokens(alt)
        concept = OntologyConcept(
            concept_id=str(row.get("id")),
            label=str(row.get("label", "")),
            source=str(row.get("source", "")),
            domain=str(row.get("domain", "")),
            normalized_label=normalize_label(str(row.get("label", ""))),
            labels_norm=alt_labels,
            tokens=tokens,
        )
        concepts.append(concept)
        for alt in alt_labels:
            by_alt_label[alt].add(idx)
        for token in tokens:
            by_token[token].add(idx)

    return concepts, by_alt_label, by_token


def lexical_candidate_records(
    label: str,
    concepts: list[OntologyConcept],
    by_alt_label: dict[str, set[int]],
    by_token: dict[str, set[int]],
    exclude_id: str | None = None,
) -> list[dict[str, Any]]:
    normalized = normalize_label(label)
    label_tokens = content_tokens(label)
    candidate_ids = set(by_alt_label.get(normalized, set()))
    for token in label_tokens:
        candidate_ids |= by_token.get(token, set())

    results: list[dict[str, Any]] = []
    for idx in candidate_ids:
        concept = concepts[idx]
        if exclude_id and concept.concept_id == exclude_id:
            continue
        if concept.source in {"wikipedia", "wikidata"} and concept.normalized_label.startswith("the ") and len(concept.tokens) <= 1:
            continue
        overlap = len(label_tokens & concept.tokens)
        exact_alt = normalized in concept.labels_norm
        precision = overlap / max(1, len(concept.tokens))
        recall = overlap / max(1, len(label_tokens))
        seq = sequence_ratio(normalized, concept.normalized_label)
        subset = int(concept.tokens and concept.tokens <= label_tokens)
        score = (
            2.0 * exact_alt
            + 1.1 * recall
            + 0.8 * precision
            + 0.5 * seq
            + 0.3 * subset
            + SOURCE_PRIORITY_BONUS.get(concept.source, 0.0)
        )
        results.append(
            {
                "concept_id": concept.concept_id,
                "concept_label": concept.label,
                "concept_source": concept.source,
                "concept_domain": concept.domain,
                "token_overlap": overlap,
                "precision": precision,
                "recall": recall,
                "sequence_ratio": seq,
                "tokens_subset": bool(subset),
                "lexical_score": score,
            }
        )
    results.sort(
        key=lambda row: (
            row["lexical_score"],
            row["token_overlap"],
            row["recall"],
            row["precision"],
            row["sequence_ratio"],
        ),
        reverse=True,
    )
    return results


def build_grounding_frame(mapping_df: pd.DataFrame, metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = mapping_df.merge(metrics_df, on="label", how="left")
    for col in ["unique_papers", "unique_edge_instances", "directed_edge_instances"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["first_year", "last_year"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["score_band"] = df["score"].map(score_band)
    df["provisional_grounding_action"] = df["score_band"].map(provisional_action)
    df["preserve_raw_label"] = True
    df["rank1_score"] = pd.to_numeric(df["score"], errors="coerce")
    df["rank2_score"] = pd.to_numeric(df["rank2_score"], errors="coerce")
    df["rank_gap"] = (df["rank1_score"] - df["rank2_score"]).fillna(1.0)

    freq_rank = df["freq"].rank(method="average", pct=True)
    paper_rank = df["unique_papers"].rank(method="average", pct=True)
    edge_rank = df["unique_edge_instances"].rank(method="average", pct=True)
    directed_rank = df["directed_edge_instances"].rank(method="average", pct=True)
    df["impact_score"] = (
        0.40 * freq_rank
        + 0.35 * paper_rank
        + 0.20 * edge_rank
        + 0.05 * directed_rank
    ).astype(float)
    return df


def build_audit_universe(df: pd.DataFrame) -> pd.DataFrame:
    low_confidence = df["rank1_score"] < SOFT_THRESHOLD
    mask = (
        (low_confidence & (df["impact_score"] >= AUDIT_IMPACT_THRESHOLD))
        | (low_confidence & (df["freq"] >= 50))
        | (low_confidence & (df["unique_papers"] >= 20))
        | (
            (df["rank1_score"] >= CANDIDATE_THRESHOLD)
            & (df["rank1_score"] < SOFT_THRESHOLD)
            & (df["rank_gap"] <= AMBIGUITY_GAP_THRESHOLD)
            & (df["impact_score"] >= AMBIGUITY_IMPACT_THRESHOLD)
        )
    )
    audit = df.loc[mask].copy()
    return audit.sort_values(["impact_score", "freq", "unique_papers"], ascending=[False, False, False]).reset_index(drop=True)


def row_issue_type(
    row: pd.Series,
    concepts: list[OntologyConcept],
    by_alt_label: dict[str, set[int]],
    by_token: dict[str, set[int]],
) -> dict[str, Any]:
    label = str(row["label"])
    label_tokens = content_tokens(label)
    current_label = str(row.get("onto_label") or "")
    current_tokens = content_tokens(current_label)
    current_overlap = len(label_tokens & current_tokens)
    current_recall = current_overlap / max(1, len(label_tokens))
    current_subset = bool(current_tokens and current_tokens <= label_tokens)
    best_alt = lexical_candidate_records(
        label,
        concepts,
        by_alt_label,
        by_token,
        exclude_id=str(row.get("onto_id") or "") or None,
    )
    best_alt_row = best_alt[0] if best_alt else None
    normalized_label = normalize_label(label)

    suspected_bad_target = any(term in normalize_label(current_label) for term in BAD_TARGET_TERMS)
    exact_alias_elsewhere = best_alt_row and (
        best_alt_row["sequence_ratio"] >= 0.90
        or (best_alt_row["token_overlap"] >= 2 and best_alt_row["recall"] >= 0.60)
    )
    broad_current = bool(current_label) and current_subset and len(label_tokens) > len(current_tokens)
    broad_elsewhere = bool(best_alt_row) and best_alt_row["tokens_subset"] and len(label_tokens) > 1

    if normalized_label in GENERIC_LABELS or is_probably_generic(label):
        issue = "bad_match_or_noise"
    elif broad_current or (broad_elsewhere and best_alt_row and best_alt_row["token_overlap"] >= 1):
        issue = "broader_concept_available"
    elif exact_alias_elsewhere and str(best_alt_row["concept_label"]) != current_label:
        issue = "missing_alias"
    elif (current_recall < 0.25 and suspected_bad_target) or (row["rank1_score"] < RESCUE_THRESHOLD and len(label_tokens) >= 2):
        issue = "missing_concept_family" if row["impact_score"] >= 0.65 else "bad_match_or_noise"
    elif row["rank1_score"] < CANDIDATE_THRESHOLD and len(label_tokens) >= 2 and row["impact_score"] >= 0.60:
        issue = "missing_concept_family"
    else:
        issue = "unclear"

    proposed_onto_id = None
    proposed_onto_label = None
    if issue == "broader_concept_available":
        if broad_current:
            proposed_onto_id = row.get("onto_id")
            proposed_onto_label = current_label
        elif best_alt_row is not None:
            proposed_onto_id = best_alt_row["concept_id"]
            proposed_onto_label = best_alt_row["concept_label"]
    elif issue == "missing_alias" and best_alt_row is not None:
        proposed_onto_id = best_alt_row["concept_id"]
        proposed_onto_label = best_alt_row["concept_label"]

    return {
        "issue_type_initial": issue,
        "current_token_recall": round(current_recall, 4),
        "current_tokens_subset": current_subset,
        "alt_concept_id": best_alt_row["concept_id"] if best_alt_row else None,
        "alt_concept_label": best_alt_row["concept_label"] if best_alt_row else None,
        "alt_concept_domain": best_alt_row["concept_domain"] if best_alt_row else None,
        "alt_lexical_score": round(best_alt_row["lexical_score"], 4) if best_alt_row else None,
        "alt_recall": round(best_alt_row["recall"], 4) if best_alt_row else None,
        "proposed_onto_id": proposed_onto_id,
        "proposed_onto_label": proposed_onto_label,
    }


def coarse_issue_type(row: pd.Series) -> dict[str, Any]:
    label = str(row["label"])
    current_label = str(row.get("onto_label") or "")
    issue = "unclear"
    if is_probably_generic(label):
        issue = "bad_match_or_noise"
    elif score_band(row.get("rank1_score")) == "candidate":
        issue = "broader_concept_available"
    elif score_band(row.get("rank1_score")) == "rescue":
        issue = "missing_concept_family"
    elif score_band(row.get("rank1_score")) == "unresolved":
        issue = "missing_concept_family" if row.get("impact_score", 0.0) >= 0.65 else "bad_match_or_noise"
    return {
        "issue_type_initial": issue,
        "current_token_recall": 0.0,
        "current_tokens_subset": False,
        "alt_concept_id": None,
        "alt_concept_label": None,
        "alt_concept_domain": None,
        "alt_lexical_score": None,
        "alt_recall": None,
        "proposed_onto_id": row.get("onto_id") if issue == "broader_concept_available" else None,
        "proposed_onto_label": current_label if issue == "broader_concept_available" else None,
    }


def cluster_texts_tfidf(texts: list[str]) -> tuple[TfidfVectorizer, Any]:
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def lexical_gate(left: pd.Series, right: pd.Series) -> bool:
    left_tokens = content_tokens(str(left["label"]))
    right_tokens = content_tokens(str(right["label"]))
    if left_tokens & right_tokens:
        return True
    left_targets = {str(left.get("onto_label") or ""), str(left.get("rank2_label") or "")}
    right_targets = {str(right.get("onto_label") or ""), str(right.get("rank2_label") or "")}
    return bool((left_targets - {""}) & (right_targets - {""}))


def union_find_components(size: int, pairs: Iterable[tuple[int, int]]) -> list[list[int]]:
    parent = list(range(size))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in pairs:
        union(a, b)

    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(size):
        groups[find(idx)].append(idx)
    return list(groups.values())


def choose_cluster_medoid(cluster_df: pd.DataFrame, matrix: Any) -> int:
    if len(cluster_df) == 1:
        return int(cluster_df.index[0])
    local = matrix[cluster_df.index.to_numpy()]
    sim = local @ local.T
    weights = cluster_df["freq"].to_numpy(dtype=float)
    weighted_scores = np.asarray(sim.sum(axis=1)).reshape(-1) * weights
    local_idx = int(weighted_scores.argmax())
    return int(cluster_df.index[local_idx])


def cluster_audit_labels(audit_df: pd.DataFrame, backend: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    cluster_universe = audit_df.copy()
    cluster_mode = "audit_universe"
    if len(cluster_universe) > MAX_CLUSTER_LABELS:
        cluster_mode = "audit_top_truncated"
        cluster_universe = cluster_universe.head(MAX_CLUSTER_LABELS).copy()
    if cluster_universe.empty:
        return (
            pd.DataFrame(columns=["label", "cluster_id", "cluster_size", "cluster_representative_label", "cluster_proposal", "cluster_mean_similarity", "cluster_weighted_freq", "dominant_onto_id", "dominant_onto_label", "dominant_share"]),
            pd.DataFrame(columns=["cluster_id", "cluster_size", "cluster_weighted_freq", "cluster_weighted_unique_papers", "cluster_representative_label", "cluster_representative_freq", "cluster_mean_similarity", "dominant_onto_id", "dominant_onto_label", "dominant_share", "cluster_proposal", "member_labels_json"]),
            {"backend": backend, "cluster_mode": cluster_mode, "cluster_universe_size": 0, "cluster_count": 0},
        )

    print(
        f"  clustering {len(cluster_universe):,} labels with backend={backend} ({cluster_mode}) …",
        flush=True,
    )
    vectorizer, matrix = cluster_texts_tfidf(cluster_universe["label"].astype(str).tolist())
    n_neighbors = min(K_NEIGHBORS + 1, len(cluster_universe))
    knn = NearestNeighbors(metric="cosine", n_neighbors=n_neighbors)
    knn.fit(matrix)
    distances, indices = knn.kneighbors(matrix, return_distance=True)

    reciprocal_edges: set[tuple[int, int]] = set()
    neighbor_lookup = {i: set(indices[i][1:]) for i in range(len(cluster_universe))}
    for i in range(len(cluster_universe)):
        left_row = cluster_universe.iloc[i]
        for j_pos in range(1, n_neighbors):
            j = int(indices[i, j_pos])
            if i == j:
                continue
            similarity = 1.0 - float(distances[i, j_pos])
            if similarity < NEIGHBOR_SIM_THRESHOLD:
                continue
            if i not in neighbor_lookup.get(j, set()):
                continue
            right_row = cluster_universe.iloc[j]
            if not lexical_gate(left_row, right_row):
                continue
            reciprocal_edges.add((min(i, j), max(i, j)))
        if (i + 1) % 2_500 == 0:
            print(f"  processed {i + 1:,}/{len(cluster_universe):,} labels for reciprocal neighbors …", flush=True)

    components = union_find_components(len(cluster_universe), reciprocal_edges)
    assignment_rows: list[dict[str, Any]] = []
    cluster_rows: list[dict[str, Any]] = []

    for cluster_num, members in enumerate(sorted(components, key=len, reverse=True), start=1):
        member_df = cluster_universe.iloc[members].copy()
        cluster_id = f"ov2c_{cluster_num:05d}"
        medoid_global_idx = choose_cluster_medoid(member_df, matrix)
        medoid_row = cluster_universe.iloc[medoid_global_idx]
        weighted_freq = int(member_df["freq"].sum())
        weighted_papers = int(member_df["unique_papers"].sum())

        dominant = (
            member_df.groupby(["onto_id", "onto_label"], dropna=False)["freq"]
            .sum()
            .sort_values(ascending=False)
        )
        if len(dominant):
            (dominant_id, dominant_label), dominant_freq = dominant.index[0], float(dominant.iloc[0])
            dominant_share = dominant_freq / max(1.0, float(member_df["freq"].sum()))
        else:
            dominant_id, dominant_label, dominant_share = None, None, 0.0

        mean_sim = 1.0
        if len(member_df) > 1:
            local = matrix[members]
            sim = local @ local.T
            upper = np.asarray(sim[np.triu_indices(len(members), k=1)]).reshape(-1)
            mean_sim = float(np.mean(upper)) if upper.size else 1.0

        proposal = "keep_unresolved"
        representative_tokens = content_tokens(str(medoid_row["label"]))
        dominant_tokens = content_tokens(str(dominant_label or ""))
        dominant_token_count = len(dominant_tokens)
        if dominant_share >= 0.60 and dominant_tokens and dominant_tokens <= representative_tokens:
            if len(representative_tokens) > len(dominant_tokens):
                proposal = "attach_existing_broad"
            elif dominant_token_count >= 2 or sequence_ratio(str(medoid_row["label"]), str(dominant_label or "")) >= 0.90:
                proposal = "add_alias_to_existing"
        elif dominant_share >= 0.60 and mean_sim >= 0.62 and dominant_token_count >= 2:
            proposal = "add_alias_to_existing"
        elif dominant_share < 0.40 and mean_sim >= 0.60 and weighted_freq >= 30:
            proposal = "propose_new_concept_family"
        elif mean_sim < 0.45:
            proposal = "reject_cluster"

        cluster_rows.append(
            {
                "cluster_id": cluster_id,
                "cluster_size": int(len(member_df)),
                "cluster_weighted_freq": weighted_freq,
                "cluster_weighted_unique_papers": weighted_papers,
                "cluster_representative_label": str(medoid_row["label"]),
                "cluster_representative_freq": int(medoid_row["freq"]),
                "cluster_mean_similarity": round(mean_sim, 4),
                "dominant_onto_id": dominant_id,
                "dominant_onto_label": dominant_label,
                "dominant_share": round(dominant_share, 4),
                "cluster_proposal": proposal,
                "member_labels_json": json.dumps(member_df["label"].astype(str).tolist()[:25], ensure_ascii=False),
            }
        )
        for idx in member_df.index:
            assignment_rows.append(
                {
                    "label": str(cluster_universe.loc[idx, "label"]),
                    "cluster_id": cluster_id,
                    "cluster_size": int(len(member_df)),
                    "cluster_representative_label": str(medoid_row["label"]),
                    "cluster_proposal": proposal,
                    "cluster_mean_similarity": round(mean_sim, 4),
                    "cluster_weighted_freq": weighted_freq,
                    "dominant_onto_id": dominant_id,
                    "dominant_onto_label": dominant_label,
                    "dominant_share": round(dominant_share, 4),
                }
            )

    assignment_df = pd.DataFrame(assignment_rows)
    clusters_df = pd.DataFrame(cluster_rows).sort_values(
        ["cluster_weighted_freq", "cluster_size"], ascending=[False, False]
    ).reset_index(drop=True)
    meta = {
        "backend": backend,
        "cluster_mode": cluster_mode,
        "cluster_universe_size": int(len(cluster_universe)),
        "cluster_count": int(len(clusters_df)),
    }
    return assignment_df, clusters_df, meta


def finalize_audit(audit_df: pd.DataFrame, cluster_assignments: pd.DataFrame) -> pd.DataFrame:
    audit = audit_df.merge(cluster_assignments, on="label", how="left")

    final_issue = []
    final_proposed_id = []
    final_proposed_label = []
    for _, row in audit.iterrows():
        issue = str(row["issue_type_initial"])
        proposal = str(row.get("cluster_proposal") or "")
        proposed_id = row.get("proposed_onto_id")
        proposed_label = row.get("proposed_onto_label")
        cluster_size_raw = row.get("cluster_size")
        cluster_size = 0 if pd.isna(cluster_size_raw) else int(cluster_size_raw)
        cluster_mean = safe_float(row.get("cluster_mean_similarity"), 0.0)
        dominant_share = safe_float(row.get("dominant_share"), 0.0)
        strong_cluster = cluster_size > 0 and cluster_size <= 200 and cluster_mean >= 0.62

        if proposal == "attach_existing_broad" and strong_cluster and dominant_share >= 0.60:
            issue = "broader_concept_available"
            if pd.isna(proposed_id) or proposed_id in (None, ""):
                proposed_id = row.get("dominant_onto_id") or row.get("onto_id")
                proposed_label = row.get("dominant_onto_label") or row.get("onto_label")
        elif proposal == "add_alias_to_existing" and strong_cluster and dominant_share >= 0.60:
            issue = "missing_alias"
            if pd.isna(proposed_id) or proposed_id in (None, ""):
                proposed_id = row.get("dominant_onto_id") or row.get("alt_concept_id") or row.get("onto_id")
                proposed_label = row.get("dominant_onto_label") or row.get("alt_concept_label") or row.get("onto_label")
        elif proposal == "propose_new_concept_family" and strong_cluster:
            issue = "missing_concept_family"
        elif proposal == "reject_cluster" and issue not in {"broader_concept_available", "missing_alias"}:
            issue = "bad_match_or_noise"

        current_target_norm = normalize_label(str(row.get("onto_label") or ""))
        proposed_target_norm = normalize_label(str(proposed_label or ""))
        if (
            issue in {"missing_alias", "broader_concept_available"}
            and proposed_target_norm
            and proposed_target_norm == current_target_norm
            and any(term in current_target_norm for term in BAD_TARGET_TERMS)
        ):
            issue = "missing_concept_family"
            proposed_id = None
            proposed_label = None
        final_issue.append(issue)
        final_proposed_id.append(proposed_id)
        final_proposed_label.append(proposed_label)

    audit["issue_type"] = final_issue
    audit["proposed_onto_id"] = final_proposed_id
    audit["proposed_onto_label"] = final_proposed_label
    return audit.sort_values(["impact_score", "freq", "unique_papers"], ascending=[False, False, False]).reset_index(drop=True)


def build_overlay_outputs(audit_df: pd.DataFrame, clusters_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    overlay_rows = []
    proposal_rows = []

    for _, row in audit_df.iterrows():
        issue = str(row["issue_type"])
        overlay_action = None
        if issue == "broader_concept_available" and pd.notna(row.get("proposed_onto_id")):
            overlay_action = "attach_existing_broad"
        elif issue == "missing_alias" and pd.notna(row.get("proposed_onto_id")):
            overlay_action = "add_alias_to_existing"
        elif issue == "missing_concept_family":
            overlay_action = "propose_new_concept_family"
        elif issue == "bad_match_or_noise":
            overlay_action = "reject_cluster"
        elif issue == "unclear":
            overlay_action = "keep_unresolved"
        if overlay_action is None:
            continue
        overlay_rows.append(
            {
                "label": row["label"],
                "label_raw": row["label_raw"],
                "freq": int(row["freq"]),
                "unique_papers": int(row["unique_papers"]),
                "impact_score": float(row["impact_score"]),
                "score_band": row["score_band"],
                "issue_type": issue,
                "cluster_id": row.get("cluster_id"),
                "overlay_action": overlay_action,
                "proposed_onto_id": row.get("proposed_onto_id"),
                "proposed_onto_label": row.get("proposed_onto_label"),
                "preserve_raw_label": True,
            }
        )

    for _, row in clusters_df.iterrows():
        if row["cluster_proposal"] not in {"propose_new_concept_family", "keep_unresolved"}:
            continue
        proposal_rows.append(
            {
                "cluster_id": row["cluster_id"],
                "cluster_proposal": row["cluster_proposal"],
                "cluster_representative_label": row["cluster_representative_label"],
                "cluster_size": int(row["cluster_size"]),
                "cluster_weighted_freq": int(row["cluster_weighted_freq"]),
                "cluster_weighted_unique_papers": int(row["cluster_weighted_unique_papers"]),
                "cluster_mean_similarity": float(row["cluster_mean_similarity"]),
                "member_labels_json": row["member_labels_json"],
            }
        )

    overlay_df = pd.DataFrame(overlay_rows).sort_values(
        ["impact_score", "freq"], ascending=[False, False]
    ).reset_index(drop=True)
    proposals_df = pd.DataFrame(proposal_rows).sort_values(
        ["cluster_weighted_freq", "cluster_size"], ascending=[False, False]
    ).reset_index(drop=True)
    return overlay_df, proposals_df


def build_nano_queue(audit_df: pd.DataFrame, clusters_df: pd.DataFrame) -> pd.DataFrame:
    queue_rows = []

    medoid_clusters = clusters_df[
        clusters_df["cluster_proposal"].isin(REVIEWABLE_PROPOSALS)
    ].copy()
    medoid_clusters = medoid_clusters.head(2000)
    for _, row in medoid_clusters.iterrows():
        queue_rows.append(
            {
                "review_item_type": "cluster_medoid",
                "cluster_id": row["cluster_id"],
                "label": row["cluster_representative_label"],
                "freq": int(row["cluster_weighted_freq"]),
                "impact_score": np.nan,
                "score_band": None,
                "rank1_label": row.get("dominant_onto_label"),
                "rank1_score": np.nan,
                "rank2_label": None,
                "rank2_score": np.nan,
                "rank_gap": np.nan,
                "proposed_action": row["cluster_proposal"],
                "issue_type": None,
                "nano_decision": None,
                "nano_reason": None,
                "review_status": "queued",
            }
        )

    ambiguous_rows = audit_df[
        audit_df["score_band"].isin({"candidate", "rescue"})
        & (audit_df["rank_gap"] <= AMBIGUITY_GAP_THRESHOLD)
        & (audit_df["impact_score"] >= AUDIT_IMPACT_THRESHOLD)
    ].copy()
    ambiguous_rows = ambiguous_rows.head(10_000)
    for _, row in ambiguous_rows.iterrows():
        queue_rows.append(
            {
                "review_item_type": "row",
                "cluster_id": row.get("cluster_id"),
                "label": row["label"],
                "freq": int(row["freq"]),
                "impact_score": float(row["impact_score"]),
                "score_band": row["score_band"],
                "rank1_label": row.get("onto_label"),
                "rank1_score": safe_float(row.get("rank1_score"), np.nan),
                "rank2_label": row.get("rank2_label"),
                "rank2_score": safe_float(row.get("rank2_score"), np.nan),
                "rank_gap": safe_float(row.get("rank_gap"), np.nan),
                "proposed_action": row.get("issue_type"),
                "issue_type": row.get("issue_type"),
                "nano_decision": None,
                "nano_reason": None,
                "review_status": "queued",
            }
        )

    unresolved_rows = audit_df[
        (audit_df["score_band"] == "unresolved")
        & audit_df["cluster_proposal"].isin({"propose_new_concept_family", "keep_unresolved"})
        & (audit_df["impact_score"] >= AUDIT_IMPACT_THRESHOLD)
    ].copy()
    unresolved_rows = unresolved_rows.head(2_000)
    for _, row in unresolved_rows.iterrows():
        queue_rows.append(
            {
                "review_item_type": "unresolved_row",
                "cluster_id": row.get("cluster_id"),
                "label": row["label"],
                "freq": int(row["freq"]),
                "impact_score": float(row["impact_score"]),
                "score_band": row["score_band"],
                "rank1_label": row.get("onto_label"),
                "rank1_score": safe_float(row.get("rank1_score"), np.nan),
                "rank2_label": row.get("rank2_label"),
                "rank2_score": safe_float(row.get("rank2_score"), np.nan),
                "rank_gap": safe_float(row.get("rank_gap"), np.nan),
                "proposed_action": row.get("issue_type"),
                "issue_type": row.get("issue_type"),
                "nano_decision": None,
                "nano_reason": None,
                "review_status": "queued",
            }
        )

    queue_df = pd.DataFrame(queue_rows)
    if queue_df.empty:
        return queue_df
    queue_df = queue_df.drop_duplicates(subset=["review_item_type", "cluster_id", "label"]).reset_index(drop=True)
    return queue_df


def accepted_attachment_maps(
    grounding_df: pd.DataFrame,
    overlay_df: pd.DataFrame,
    threshold: float,
) -> tuple[dict[str, str], dict[str, str]]:
    threshold_only = grounding_df.loc[grounding_df["rank1_score"] >= threshold, ["label", "onto_id"]].dropna()
    threshold_map = dict(zip(threshold_only["label"], threshold_only["onto_id"]))

    overlay_accept = overlay_df[
        overlay_df["overlay_action"].isin({"attach_existing_broad", "add_alias_to_existing"})
        & overlay_df["proposed_onto_id"].notna()
    ]
    overlay_map = dict(zip(overlay_accept["label"], overlay_accept["proposed_onto_id"]))

    with_overlay = dict(threshold_map)
    for label, onto_id in overlay_map.items():
        with_overlay.setdefault(label, onto_id)
    return threshold_map, with_overlay


def summarize_pairs(edge_df: pd.DataFrame, attachment_map: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = edge_df.copy()
    frame["src_attach"] = frame["source_label"].map(attachment_map)
    frame["dst_attach"] = frame["target_label"].map(attachment_map)
    grounded = frame[frame["src_attach"].notna() & frame["dst_attach"].notna()].copy()

    directed = grounded[grounded["edge_kind"] == "directed"].copy()
    directed["pair_key"] = directed["src_attach"].astype(str) + "->" + directed["dst_attach"].astype(str)
    directed_pairs = (
        directed.groupby("pair_key", as_index=False)
        .agg(edge_rows=("pair_key", "size"), distinct_papers=("paper_id", "nunique"))
        .sort_values(["distinct_papers", "edge_rows", "pair_key"], ascending=[False, False, True])
        .reset_index(drop=True)
    )

    undirected = grounded[grounded["edge_kind"] != "directed"].copy()
    pair_keys = []
    for _, row in undirected.iterrows():
        left, right = canonical_undirected(str(row["src_attach"]), str(row["dst_attach"]))
        pair_keys.append(f"{left}--{right}")
    undirected["pair_key"] = pair_keys
    undirected_pairs = (
        undirected.groupby("pair_key", as_index=False)
        .agg(edge_rows=("pair_key", "size"), distinct_papers=("paper_id", "nunique"))
        .sort_values(["distinct_papers", "edge_rows", "pair_key"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    return directed_pairs, undirected_pairs


def build_threshold_sensitivity(
    grounding_df: pd.DataFrame,
    overlay_df: pd.DataFrame,
    edge_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    benchmark_rows = []
    baseline_threshold = PRIMARY_THRESHOLD
    _, baseline_map = accepted_attachment_maps(grounding_df, overlay_df, baseline_threshold)
    baseline_directed, baseline_undirected = summarize_pairs(edge_df, baseline_map)
    baseline_directed_top = set(baseline_directed.head(TOP_K_PAIR_OVERLAP)["pair_key"])
    baseline_undirected_top = set(baseline_undirected.head(TOP_K_PAIR_OVERLAP)["pair_key"])

    for threshold in [0.85, 0.75, 0.65, 0.50]:
        threshold_map, overlay_map = accepted_attachment_maps(grounding_df, overlay_df, threshold)
        threshold_labels = set(threshold_map)
        overlay_labels = set(overlay_map)

        threshold_df = grounding_df[grounding_df["label"].isin(threshold_labels)]
        overlay_df_slice = grounding_df[grounding_df["label"].isin(overlay_labels)]
        directed_pairs, undirected_pairs = summarize_pairs(edge_df, overlay_map)

        top_directed = set(directed_pairs.head(TOP_K_PAIR_OVERLAP)["pair_key"])
        top_undirected = set(undirected_pairs.head(TOP_K_PAIR_OVERLAP)["pair_key"])
        directed_overlap = len(top_directed & baseline_directed_top) / max(1, len(baseline_directed_top))
        undirected_overlap = len(top_undirected & baseline_undirected_top) / max(1, len(baseline_undirected_top))

        rows.append(
            {
                "threshold": threshold,
                "threshold_labels_with_attachment": int(len(threshold_df)),
                "threshold_occurrences_with_attachment": int(threshold_df["freq"].sum()),
                "overlay_labels_with_attachment": int(len(overlay_df_slice)),
                "overlay_occurrences_with_attachment": int(overlay_df_slice["freq"].sum()),
                "raw_label_preservation_rate": 1.0,
                "raw_edge_preservation_rate": 1.0,
                "unique_grounded_concepts": int(len(set(overlay_map.values()))),
                "grounded_directed_pairs": int(len(directed_pairs)),
                "grounded_undirected_pairs": int(len(undirected_pairs)),
                "top100_directed_overlap_vs_0_75": round(directed_overlap, 4),
                "top100_undirected_overlap_vs_0_75": round(undirected_overlap, 4),
            }
        )
        benchmark_rows.extend(
            [
                {
                    "threshold": threshold,
                    "pair_kind": "directed",
                    "grounded_pairs": int(len(directed_pairs)),
                    "grounded_top100_overlap_vs_0_75": round(directed_overlap, 4),
                    "distinct_pair_papers_top100": int(directed_pairs.head(TOP_K_PAIR_OVERLAP)["distinct_papers"].sum()),
                },
                {
                    "threshold": threshold,
                    "pair_kind": "undirected",
                    "grounded_pairs": int(len(undirected_pairs)),
                    "grounded_top100_overlap_vs_0_75": round(undirected_overlap, 4),
                    "distinct_pair_papers_top100": int(undirected_pairs.head(TOP_K_PAIR_OVERLAP)["distinct_papers"].sum()),
                },
            ]
        )

    return pd.DataFrame(rows), pd.DataFrame(benchmark_rows)


def write_rescue_markdown(path: Path, audit_df: pd.DataFrame, cluster_meta: dict[str, Any]) -> None:
    lines = [
        "# Grounding Rescue Audit v2",
        "",
        "This is the first open-world grounding rescue pass for ontology v2.",
        "",
        "Key design choices:",
        "- raw extracted labels are always preserved",
        "- broader grounding is acceptable",
        "- low-score labels are not silently deleted",
        f"- clustering backend in this no-spend pass: `{cluster_meta['backend']}`",
        f"- clustering universe mode: `{cluster_meta['cluster_mode']}`",
        f"- clustered labels in this pass: `{cluster_meta['cluster_universe_size']:,}`",
        "",
    ]

    for issue in [
        "broader_concept_available",
        "missing_alias",
        "missing_concept_family",
        "bad_match_or_noise",
        "unclear",
    ]:
        sub = audit_df[audit_df["issue_type"] == issue].head(20)
        lines.append(f"## {issue}")
        lines.append("")
        if sub.empty:
            lines.append("- none in current audit universe")
            lines.append("")
            continue
        for _, row in sub.iterrows():
            lines.append(
                f"- `{row['label']}` | freq `{int(row['freq'])}` | papers `{int(row['unique_papers'])}` | "
                f"score `{safe_float(row['rank1_score']):.3f}` | rank-1 `{row.get('onto_label')}` | "
                f"proposal `{row.get('proposed_onto_label') or row.get('cluster_proposal') or 'NA'}`"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sensitivity_markdown(path: Path, summary_df: pd.DataFrame) -> None:
    lines = [
        "# Ontology Grounding Sensitivity",
        "",
        "This sensitivity pass varies the accepted grounding threshold while keeping the raw extraction graph fixed.",
        "",
        "| Threshold | Threshold labels | Overlay labels | Threshold occurrences | Overlay occurrences | Unique grounded concepts | Directed pair overlap vs 0.75 | Undirected pair overlap vs 0.75 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary_df.iterrows():
        lines.append(
            f"| `{row['threshold']:.2f}` | {int(row['threshold_labels_with_attachment']):,} | {int(row['overlay_labels_with_attachment']):,} | "
            f"{int(row['threshold_occurrences_with_attachment']):,} | {int(row['overlay_occurrences_with_attachment']):,} | "
            f"{int(row['unique_grounded_concepts']):,} | {row['top100_directed_overlap_vs_0_75']:.3f} | {row['top100_undirected_overlap_vs_0_75']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- the raw graph stays fixed across thresholds",
            "- only the ontology-grounded interpretation layer changes",
            "- overlay counts include broader-grounding and alias rescues from the audit layer",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_nano_markdown(path: Path, queue_df: pd.DataFrame) -> None:
    lines = [
        "# Nano Grounding Review Queue v2",
        "",
        "This file stages the nano review queue after the heuristic rescue layer exists.",
        "",
        "This pass does not spend API budget automatically. It builds a ranked queue for a later nano false-positive filter and selective promotion run.",
        "",
    ]
    if queue_df.empty:
        lines.append("- queue is empty")
    else:
        counts = queue_df["review_item_type"].value_counts()
        for item_type, count in counts.items():
            lines.append(f"- `{item_type}`: `{int(count):,}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decisions_markdown(path: Path, summary_df: pd.DataFrame, cluster_meta: dict[str, Any], audit_df: pd.DataFrame) -> None:
    lines = [
        "# Open-World Grounding Decisions v2",
        "",
        "This note records the key design choices in the first open-world grounding pass.",
        "",
        "## Why the mapping is no longer binary",
        "- low-similarity labels can still represent real economics concepts",
        "- broader grounding is often better than deletion",
        "- unresolved-but-real labels must stay in the graph to avoid fake novelty",
        "",
        "## Threshold bands",
        "- `>= 0.85`: linked",
        "- `0.75–0.85`: soft",
        "- `0.65–0.75`: candidate",
        "- `0.50–0.65`: rescue",
        "- `< 0.50`: unresolved",
        "",
        "## First-pass implementation choice",
        f"- clustering backend: `{cluster_meta['backend']}`",
        f"- clustering universe mode: `{cluster_meta['cluster_mode']}`",
        "- the base v2 ontology remains unchanged",
        "- enrichment is expressed as overlays and concept-family proposals",
        "",
        "## Current examples surfaced by the audit",
    ]
    for label in [
        "female sex",
        "financial frictions",
        "search frictions",
        "credit constraints",
        "information frictions",
        "economic policy uncertainty (epu) index",
        "unobserved heterogeneity",
    ]:
        sub = audit_df[audit_df["label"] == label]
        if sub.empty:
            continue
        row = sub.iloc[0]
        lines.append(
            f"- `{label}` -> issue `{row['issue_type']}` | rank-1 `{row.get('onto_label')}` | proposal `{row.get('proposed_onto_label') or row.get('cluster_proposal') or 'NA'}`"
        )
    lines.extend(
        [
            "",
            "## Sensitivity takeaway",
        ]
    )
    for _, row in summary_df.iterrows():
        lines.append(
            f"- threshold `{row['threshold']:.2f}`: threshold-attached occurrences `{int(row['threshold_occurrences_with_attachment']):,}`, "
            f"overlay-attached occurrences `{int(row['overlay_occurrences_with_attachment']):,}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    mapping_path = Path(args.mapping)
    extractions_path = Path(args.extractions)
    ontology_path = Path(args.ontology)
    out_dir = Path(args.out_dir)
    paper_out_dir = Path(args.paper_out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    paper_out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading base mapping …", flush=True)
    mapping_df = pd.read_parquet(mapping_path)

    print("Parsing raw extractions for label impact metrics …", flush=True)
    metrics_df, edge_df = parse_extractions(extractions_path)

    print("Building grounding layer …", flush=True)
    grounding_df = build_grounding_frame(mapping_df, metrics_df)

    print("Loading ontology and lexical indices …", flush=True)
    concepts, by_alt_label, by_token = load_ontology(ontology_path)

    print("Building rescue audit universe …", flush=True)
    audit_df = build_audit_universe(grounding_df)
    print(f"  audit universe rows: {len(audit_df):,}", flush=True)
    detailed_n = min(MAX_DETAILED_AUDIT_ROWS, len(audit_df))
    print(f"  detailed lexical rescue scoring rows: {detailed_n:,}", flush=True)
    detailed_rows = [
        row_issue_type(row, concepts, by_alt_label, by_token)
        for _, row in audit_df.head(detailed_n).iterrows()
    ]
    coarse_rows = [coarse_issue_type(row) for _, row in audit_df.iloc[detailed_n:].iterrows()]
    audit_df = pd.concat(
        [audit_df.reset_index(drop=True), pd.DataFrame(detailed_rows + coarse_rows)],
        axis=1,
    )

    print("Clustering high-impact rescue labels …", flush=True)
    cluster_assignments, clusters_df, cluster_meta = cluster_audit_labels(audit_df, args.embedding_backend)
    audit_df = finalize_audit(audit_df, cluster_assignments)

    print("Building overlay outputs and missing-concept proposals …", flush=True)
    overlay_df, proposals_df = build_overlay_outputs(audit_df, clusters_df)

    print("Building nano review queue …", flush=True)
    nano_queue_df = build_nano_queue(audit_df, clusters_df)

    print("Running threshold sensitivity …", flush=True)
    sensitivity_summary_df, benchmark_sensitivity_df = build_threshold_sensitivity(grounding_df, overlay_df, edge_df)

    print("Writing artifacts …", flush=True)
    grounding_df.to_parquet(out_dir / "extraction_label_grounding_v2.parquet", index=False)
    audit_df.to_parquet(out_dir / "grounding_rescue_audit_v2.parquet", index=False)
    cluster_assignments.to_parquet(out_dir / "unresolved_label_clusters_v2.parquet", index=False)
    clusters_df.to_parquet(out_dir / "unresolved_label_cluster_summaries_v2.parquet", index=False)
    overlay_df.to_parquet(out_dir / "ontology_enrichment_overlay_v2.parquet", index=False)
    proposals_df.to_parquet(out_dir / "ontology_missing_concept_proposals_v2.parquet", index=False)
    nano_queue_df.to_parquet(out_dir / "nano_grounding_review_v2.parquet", index=False)

    sensitivity_summary_df.to_csv(paper_out_dir / "summary.csv", index=False)
    benchmark_sensitivity_df.to_csv(paper_out_dir / "benchmark_sensitivity.csv", index=False)

    write_rescue_markdown(out_dir / "grounding_rescue_audit_v2.md", audit_df, cluster_meta)
    write_nano_markdown(out_dir / "nano_grounding_review_summary_v2.md", nano_queue_df)
    write_sensitivity_markdown(paper_out_dir / "summary.md", sensitivity_summary_df)
    write_decisions_markdown(out_dir / "open_world_grounding_decisions.md", sensitivity_summary_df, cluster_meta, audit_df)

    print("Done.")
    print(f"Grounding rows: {len(grounding_df):,}")
    print(f"Audit rows: {len(audit_df):,}")
    print(f"Cluster count: {len(clusters_df):,}")
    print(f"Overlay rows: {len(overlay_df):,}")
    print(f"Proposal rows: {len(proposals_df):,}")
    print(f"Nano queue rows: {len(nano_queue_df):,}")


if __name__ == "__main__":
    main()
