from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from src.ontology_v1 import (
    canonical_pair,
    counter_cosine_similarity,
    jaccard_similarity,
    normalize_label,
    preferred_label,
    sequence_similarity,
    strip_parenthetical_acronym,
)


PAIRWISE_DIFFERENT_CONCEPTS = {
    canonical_pair("supply shocks", "supply shocks (oil)"),
    canonical_pair("demand shocks", "demand shocks (oil)"),
    canonical_pair("greenhouse gas emissions", "greenhouse gas emissions (co2)"),
    canonical_pair("greenhouse gas emissions (ghg)", "greenhouse gas emissions (co2)"),
}


BLOCKED_AUTO_MERGE_PAIRS = {
    canonical_pair("affordable care act (aca)", "medicaid expansion (aca)"),
    canonical_pair("affordable care act (aca)", "medicaid expansion under the affordable care act (aca)"),
    canonical_pair("patient protection and affordable care act (aca)", "medicaid expansion (aca)"),
    canonical_pair("patient protection and affordable care act (aca)", "medicaid expansion under the affordable care act (aca)"),
    canonical_pair("green total factor productivity (gtfp)", "regional green total factor productivity (gtfp)"),
    canonical_pair("green total factor productivity (gtfp)", "urban green total factor productivity (gtfp)"),
    canonical_pair("green total factor productivity (gtfp)", "enterprise green total factor productivity (gtfp)"),
    canonical_pair("green total factor productivity (gtfp)", "provincial green total factor productivity (gtfp)"),
    canonical_pair("green total factor productivity (gtfp)", "industrial green total factor productivity (gtfp)"),
    canonical_pair("green total factor productivity (gtfp)", "agricultural green total factor productivity (gtfp)"),
    canonical_pair("willingness to pay (wtp)", "marginal willingness to pay (wtp)"),
    canonical_pair("willingness to pay (wtp)", "marginal willingness to pay (mwtp)"),
    canonical_pair("choice experiment (ce)", "carbon emissions (ce)"),
    canonical_pair("choice experiment (ce)", "carbon emissions (co2)"),
    canonical_pair("choice experiment (ce)", "carbon emissions (ces)"),
    canonical_pair("choice experiment (method)", "carbon emissions (co2)"),
    canonical_pair("choice experiment (method)", "carbon emissions (ce)"),
    canonical_pair("choice experiment (survey)", "carbon emissions (co2)"),
    canonical_pair("choice experiments (ce)", "carbon emissions (co2)"),
    canonical_pair("choice experiments (method)", "carbon emissions (co2)"),
    canonical_pair("greenhouse gas emissions (co2)", "carbon emissions (co2)"),
}


ISOLATE_LABELS = {
    "economic growth (gdp)",
    "gross domestic product (gdp)",
    "economic growth (income)",
    "output (gdp)",
    "economic growth (eg)",
    "economic development (gdp)",
    "income (gdp)",
    "economic activity (gdp)",
    "economic activity (output)",
    "economic development (growth)",
    "economic development (income)",
    "economic growth (output)",
    "economic growth (china)",
    "economic growth (ekc)",
    "economic performance (gdp)",
    "economic performance (growth)",
    "economic activity (output)",
    "economic output (gdp)",
    "output (aggregate)",
    "output (growth)",
    "output (production)",
    "per capita gross domestic product (gdp)",
    "income (gdp)",
    "environmental kuznets curve (ekc)",
    "environmental kuznets curve hypothesis (ekc)",
    "environment kuznets curve (ekc)",
    "economic expansion (gdp)",
}


HEAD_AUDIT_MEMO_LINES = [
    "FGC000010 was split aggressively because it conflated GDP, growth, output, income, and EKC labels.",
    "FGC000128 was split at the ACA / Medicaid-expansion boundary; those are related policies, not the same concept.",
    "FGC000147 was split at sector and geography qualifiers (urban/agricultural/enterprise/provincial/regional/industrial).",
    "FGC000169 keeps willingness-to-pay variants together except marginal willingness to pay, which is conceptually narrower.",
    "FGC000170 was split to block CE acronym collisions between choice experiments and carbon-emissions labels.",
]


PAREN_CONTENT_RE = re.compile(r"\(([^()]*)\)")
TOKEN_RE = re.compile(r"[a-z0-9]+")


GENERIC_PAREN_QUALIFIERS = {
    "sample",
    "group",
    "groups",
    "time period",
    "calibrated",
    "survey",
    "method",
    "methods",
    "controls",
    "control",
    "state-level",
}

CONTRAST_TOKEN_GROUPS = [
    {"spot", "futures", "forward"},
    {"product", "process"},
    {"quantity", "quality"},
    {"closeness", "betweenness", "eigenvector", "degree"},
    {"imports", "exports", "import", "export"},
    {"inbound", "outbound"},
    {"upstream", "downstream"},
    {"male", "female", "men", "women"},
]


@dataclass(frozen=True)
class ManualDecision:
    decision: str
    preferred_label_override: str
    review_notes: str


def shortest_standard_label(left_label: str, right_label: str) -> str:
    options = [left_label, right_label]
    options = [item for item in options if item]
    if not options:
        return ""
    return sorted(options, key=lambda item: (len(item), item))[0]


def token_set(label: str) -> set[str]:
    return set(TOKEN_RE.findall(normalize_label(strip_parenthetical_acronym(label))))


def parenthetical_text(label: str) -> str:
    match = PAREN_CONTENT_RE.search(label)
    return normalize_label(match.group(1)) if match else ""


def manual_pair_decision(left_label: str, right_label: str) -> ManualDecision:
    pair = canonical_pair(left_label, right_label)
    if pair in PAIRWISE_DIFFERENT_CONCEPTS:
        return ManualDecision(
            decision="different_concept",
            preferred_label_override="",
            review_notes="Manual Codex adjudication: narrower or materially different concept despite lexical overlap.",
        )

    left_base = normalize_label(strip_parenthetical_acronym(left_label))
    right_base = normalize_label(strip_parenthetical_acronym(right_label))
    left_paren = parenthetical_text(left_label)
    right_paren = parenthetical_text(right_label)

    if left_base == right_base:
        preferred = shortest_standard_label(left_label, right_label)
        return ManualDecision(
            decision="same_concept",
            preferred_label_override=preferred,
            review_notes="Manual Codex adjudication: punctuation/plural/acronym family with identical base concept.",
        )

    left_tokens = token_set(left_label)
    right_tokens = token_set(right_label)
    if ("non" in left_tokens) ^ ("non" in right_tokens):
        return ManualDecision(
            decision="different_concept",
            preferred_label_override="",
            review_notes="Manual Codex adjudication: negation or contrast marker creates a materially different concept.",
        )
    for group in CONTRAST_TOKEN_GROUPS:
        left_group = left_tokens & group
        right_group = right_tokens & group
        if left_group and right_group and left_group != right_group:
            return ManualDecision(
                decision="different_concept",
                preferred_label_override="",
                review_notes="Manual Codex adjudication: contrastive modifier indicates a different concept.",
            )

    shared_tokens = left_tokens & right_tokens
    if sequence_similarity(left_base, right_base) >= 0.88 and shared_tokens:
        preferred = shortest_standard_label(left_label, right_label)
        note = "Manual Codex adjudication: near-identical lexical family and no substantive concept drift."
        if left_paren in GENERIC_PAREN_QUALIFIERS or right_paren in GENERIC_PAREN_QUALIFIERS:
            note = "Manual Codex adjudication: generic parenthetical qualifier treated as scope/context, not a new concept."
        return ManualDecision(
            decision="same_concept",
            preferred_label_override=preferred,
            review_notes=note,
        )

    return ManualDecision(
        decision="different_concept",
        preferred_label_override="",
        review_notes="Manual Codex adjudication: lexical overlap is not enough to merge conservatively.",
    )


def build_embedding_text(row: dict[str, Any]) -> str:
    def top_values(json_text: str, limit: int = 3) -> list[str]:
        if not json_text:
            return []
        values = []
        for item in json.loads(json_text):
            if isinstance(item, dict):
                value = item.get("value")
                if value:
                    values.append(str(value))
            elif item:
                values.append(str(item))
            if len(values) >= limit:
                break
        return values

    preferred = row["preferred_label"]
    variants = top_values(row.get("top_raw_variants_json", "[]"), limit=3)
    in_neighbors = top_values(row.get("top_in_neighbors_json", "[]"), limit=3)
    out_neighbors = top_values(row.get("top_out_neighbors_json", "[]"), limit=3)
    countries = top_values(row.get("top_countries_json", "[]"), limit=2)
    units = top_values(row.get("top_units_json", "[]"), limit=2)
    bucket_profile = row.get("bucket_profile_json", "{}")
    return "\n".join(
        [
            f"label: {preferred}",
            f"variants: {', '.join(variants) if variants else 'NA'}",
            f"in_neighbors: {', '.join(in_neighbors) if in_neighbors else 'NA'}",
            f"out_neighbors: {', '.join(out_neighbors) if out_neighbors else 'NA'}",
            f"countries: {', '.join(countries) if countries else 'NA'}",
            f"units: {', '.join(units) if units else 'NA'}",
            f"bucket: {bucket_profile}",
        ]
    )


def parse_vector(text: str) -> np.ndarray:
    return np.asarray(json.loads(text), dtype=np.float32)


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = np.linalg.norm(left)
    right_norm = np.linalg.norm(right)
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def lexical_contradiction(left_label: str, right_label: str) -> bool:
    left_tokens = token_set(left_label)
    right_tokens = token_set(right_label)
    overlap = jaccard_similarity(left_tokens, right_tokens)
    if overlap >= 0.25:
        return False
    return sequence_similarity(normalize_label(left_label), normalize_label(right_label)) < 0.55


def graph_context_similarity(left_row: dict[str, Any], right_row: dict[str, Any]) -> float:
    relationship_similarity = counter_cosine_similarity(
        json.loads(left_row["relationship_type_profile_json"]),
        json.loads(right_row["relationship_type_profile_json"]),
    )
    edge_role_similarity = counter_cosine_similarity(
        json.loads(left_row["edge_role_profile_json"]),
        json.loads(right_row["edge_role_profile_json"]),
    )
    bucket_similarity = counter_cosine_similarity(
        json.loads(left_row["bucket_profile_json"]),
        json.loads(right_row["bucket_profile_json"]),
    )
    left_countries = {item["value"] for item in json.loads(left_row["top_countries_json"])}
    right_countries = {item["value"] for item in json.loads(right_row["top_countries_json"])}
    left_units = {item["value"] for item in json.loads(left_row["top_units_json"])}
    right_units = {item["value"] for item in json.loads(right_row["top_units_json"])}
    country_overlap = jaccard_similarity(left_countries, right_countries)
    unit_overlap = jaccard_similarity(left_units, right_units)
    return float(
        0.35 * relationship_similarity
        + 0.25 * edge_role_similarity
        + 0.20 * bucket_similarity
        + 0.10 * country_overlap
        + 0.10 * unit_overlap
    )


def select_cluster_preferred_label(label_counts: Counter[str]) -> str:
    return preferred_label(label_counts)


def chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    chunk: list[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def safe_margin(best: float, second_best: float | None) -> float:
    if second_best is None:
        return best
    return best - second_best


def bool_to_int(value: bool) -> int:
    return 1 if value else 0
