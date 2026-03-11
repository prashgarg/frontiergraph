from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.ontology_v1 import (
    canonical_pair,
    counter_cosine_similarity,
    jaccard_similarity,
    label_signatures,
    normalize_label,
    sequence_similarity,
)
from src.ontology_v2 import CONTRAST_TOKEN_GROUPS, cosine_similarity, lexical_contradiction, token_set


PROTECTED_PHRASE_PAIRS = {
    canonical_pair("inflation", "inflation expectations"),
}

STRONG_SIGNATURE_KEYS = ("normalized_label", "no_paren_signature", "punctuation_signature", "singular_signature")
WEAK_SIGNATURE_KEYS = ("paren_acronym", "initialism_signature")


@dataclass(frozen=True)
class ConceptProfile:
    concept_id: str
    preferred_label: str
    labels: tuple[str, ...]
    normalized_label: str
    signature_sets: dict[str, set[str]]
    token_set: set[str]
    vector: np.ndarray | None
    neighbors: set[str]
    countries: set[str]
    units: set[str]
    bucket_profile: dict[str, int]
    support: int


def parse_json_object(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def parse_value_list(text: str | None) -> list[str]:
    loaded = parse_json_object(text, [])
    if isinstance(loaded, list):
        values: list[str] = []
        for item in loaded:
            if isinstance(item, dict):
                value = item.get("value")
                if value:
                    values.append(str(value))
            elif item:
                values.append(str(item))
        return values
    if isinstance(loaded, str) and loaded.strip():
        return [loaded.strip()]
    return []


def parse_bucket_profile(text: str | None) -> dict[str, int]:
    loaded = parse_json_object(text, {})
    if not isinstance(loaded, dict):
        return {}
    return {str(key): int(value) for key, value in loaded.items() if value}


def build_signature_sets(labels: list[str]) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {key: set() for key in STRONG_SIGNATURE_KEYS + WEAK_SIGNATURE_KEYS}
    for label in labels:
        sigs = label_signatures(label)
        for key, value in sigs.items():
            if key in values and value:
                values[key].add(value)
    return values


def build_concept_profile(
    *,
    concept_id: str,
    preferred_label: str,
    aliases_json: str | None,
    top_countries: str | None,
    top_units: str | None,
    bucket_profile_json: str | None,
    support: int,
    neighbors: set[str],
    vector: np.ndarray | None,
) -> ConceptProfile:
    aliases = [str(item) for item in parse_json_object(aliases_json, []) if str(item).strip()]
    labels = [preferred_label] + [item for item in aliases if item != preferred_label]
    signature_sets = build_signature_sets(labels)
    tokens = set()
    for label in labels:
        tokens |= token_set(label)
    return ConceptProfile(
        concept_id=concept_id,
        preferred_label=preferred_label,
        labels=tuple(labels),
        normalized_label=normalize_label(preferred_label),
        signature_sets=signature_sets,
        token_set=tokens,
        vector=vector,
        neighbors=neighbors,
        countries=set(parse_value_list(top_countries)),
        units=set(parse_value_list(top_units)),
        bucket_profile=parse_bucket_profile(bucket_profile_json),
        support=int(support or 0),
    )


def pair_key(left_id: str, right_id: str) -> str:
    left, right = canonical_pair(str(left_id), str(right_id))
    return f"{left}__{right}"


def _signature_overlap(left: ConceptProfile, right: ConceptProfile, keys: tuple[str, ...]) -> bool:
    return any(left.signature_sets.get(key, set()) & right.signature_sets.get(key, set()) for key in keys)


def protected_contrast(left: ConceptProfile, right: ConceptProfile) -> str:
    left_tokens = left.token_set
    right_tokens = right.token_set
    for group in CONTRAST_TOKEN_GROUPS:
        left_group = left_tokens & group
        right_group = right_tokens & group
        if left_group and right_group and left_group != right_group:
            return "contrastive_tokens"
    pair = canonical_pair(left.normalized_label, right.normalized_label)
    if pair in PROTECTED_PHRASE_PAIRS:
        return "protected_phrase_pair"
    return ""


def hard_same_family_reason(left: ConceptProfile, right: ConceptProfile, reviewed_pairs: dict[tuple[str, str], str]) -> str:
    pair = canonical_pair(left.normalized_label, right.normalized_label)
    reviewed = reviewed_pairs.get(pair, "")
    if reviewed == "different_concept":
        return ""
    protection = protected_contrast(left, right)
    if protection:
        return ""
    if reviewed == "same_concept":
        return "manual_same_concept_review"
    if left.normalized_label == right.normalized_label:
        return "exact_normalized_label"
    if _signature_overlap(left, right, ("normalized_label",)):
        return "alias_normalized_overlap"
    if _signature_overlap(left, right, ("no_paren_signature",)):
        return "no_paren_signature_overlap"
    if _signature_overlap(left, right, ("punctuation_signature", "singular_signature")):
        return "formatting_or_singular_variant"
    left_paren = left.signature_sets.get("paren_acronym", set())
    right_paren = right.signature_sets.get("paren_acronym", set())
    left_initial = left.signature_sets.get("initialism_signature", set())
    right_initial = right.signature_sets.get("initialism_signature", set())
    if (left_paren & right_paren) or (left_paren & right_initial) or (right_paren & left_initial):
        if sequence_similarity(left.normalized_label, right.normalized_label) >= 0.60:
            return "explicit_acronym_equivalence"
    return ""


def alias_overlap_score(left: ConceptProfile, right: ConceptProfile) -> float:
    if _signature_overlap(left, right, ("normalized_label", "no_paren_signature")):
        return 1.0
    if _signature_overlap(left, right, ("punctuation_signature", "singular_signature")):
        return 0.8
    if _signature_overlap(left, right, ("paren_acronym", "initialism_signature")):
        return 0.6
    return 0.0


def containment_ratio(left_tokens: set[str], right_tokens: set[str]) -> float:
    if not left_tokens or not right_tokens:
        return 0.0
    inter = left_tokens & right_tokens
    denom = min(len(left_tokens), len(right_tokens))
    if denom <= 0:
        return 0.0
    return len(inter) / denom


def substring_containment_ratio(left: ConceptProfile, right: ConceptProfile) -> float:
    left_label = left.normalized_label.strip()
    right_label = right.normalized_label.strip()
    if not left_label or not right_label:
        return 0.0
    shorter, longer = sorted((left_label, right_label), key=len)
    if shorter == longer:
        return 1.0
    if shorter in longer:
        return len(shorter) / max(len(longer), 1)
    return 0.0


def significant_token_overlap(left_tokens: set[str], right_tokens: set[str]) -> float:
    if not left_tokens or not right_tokens:
        return 0.0
    shared = left_tokens & right_tokens
    if len(shared) < 2:
        return 0.0
    return len(shared) / max(min(len(left_tokens), len(right_tokens)), 1)


def bucket_similarity(left: ConceptProfile, right: ConceptProfile) -> float:
    return counter_cosine_similarity(left.bucket_profile, right.bucket_profile)


def context_overlap(left: ConceptProfile, right: ConceptProfile) -> float:
    country_overlap = jaccard_similarity(left.countries, right.countries)
    unit_overlap = jaccard_similarity(left.units, right.units)
    return 0.5 * country_overlap + 0.5 * unit_overlap


def neighbor_overlap(left: ConceptProfile, right: ConceptProfile) -> float:
    return jaccard_similarity(left.neighbors, right.neighbors)


def soft_duplicate_metrics(
    left: ConceptProfile,
    right: ConceptProfile,
    reviewed_pairs: dict[tuple[str, str], str],
) -> dict[str, float | int | str]:
    protection = protected_contrast(left, right)
    hard_reason = hard_same_family_reason(left, right, reviewed_pairs)
    lexical_overlap = jaccard_similarity(left.token_set, right.token_set)
    containment = containment_ratio(left.token_set, right.token_set)
    substring_overlap = substring_containment_ratio(left, right)
    shared_token_overlap = significant_token_overlap(left.token_set, right.token_set)
    alias_overlap = alias_overlap_score(left, right)
    embedding_similarity = 0.0
    if left.vector is not None and right.vector is not None:
        embedding_similarity = max(0.0, cosine_similarity(left.vector, right.vector))
    overlap_neighbors = neighbor_overlap(left, right)
    overlap_context = context_overlap(left, right)
    overlap_bucket = bucket_similarity(left, right)
    contradiction = 1 if lexical_contradiction(left.preferred_label, right.preferred_label) else 0

    score = (
        0.35 * embedding_similarity
        + 0.22 * containment
        + 0.15 * substring_overlap
        + 0.10 * lexical_overlap
        + 0.03 * shared_token_overlap
        + 0.15 * alias_overlap
        + 0.10 * overlap_neighbors
        + 0.03 * overlap_context
        + 0.02 * overlap_bucket
    )
    if contradiction:
        score *= 0.5
    if protection:
        score *= 0.15
    score = max(0.0, min(1.0, score))
    return {
        "hard_same_family": 1 if hard_reason else 0,
        "hard_same_family_reason": hard_reason,
        "soft_duplicate_score": score,
        "duplicate_penalty": score,
        "contrastive_protection": 1 if protection else 0,
        "contrastive_reason": protection,
        "embedding_similarity": embedding_similarity,
        "lexical_overlap": lexical_overlap,
        "containment_ratio": containment,
        "substring_containment_ratio": substring_overlap,
        "shared_token_overlap": shared_token_overlap,
        "alias_overlap": alias_overlap,
        "neighbor_overlap": overlap_neighbors,
        "context_overlap": overlap_context,
        "bucket_similarity": overlap_bucket,
        "lexical_contradiction": contradiction,
    }
