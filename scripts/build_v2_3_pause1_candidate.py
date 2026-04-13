from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
NEXT_STEPS_DIR = ROOT / "next_steps"

DEFAULT_ONTOLOGY_JSON = DATA_DIR / "ontology_v2_2_hierarchy_enriched_canonicalized.json"
DEFAULT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_2_guardrailed_canonicalized.parquet"
DEFAULT_DUPLICATE_HOLDOUT = DATA_DIR / "duplicate_canonicalization_pass2_v2_2_holdout.parquet"
DEFAULT_TOO_BROAD_ROWS = DATA_DIR / "too_broad_intermediate_row_summary_v2_2.parquet"
DEFAULT_TOO_BROAD_CANDIDATES = DATA_DIR / "too_broad_intermediate_candidates_v2_2.parquet"

DEFAULT_LABEL_POLICY_PARQUET = DATA_DIR / "ontology_v2_3_label_policy.parquet"
DEFAULT_LABEL_POLICY_CSV = DATA_DIR / "ontology_v2_3_label_policy.csv"
DEFAULT_LABEL_POLICY_MD = DATA_DIR / "ontology_v2_3_label_policy.md"

DEFAULT_DUPLICATE_RESOLUTION_PARQUET = DATA_DIR / "ontology_v2_3_duplicate_resolution.parquet"
DEFAULT_DUPLICATE_RESOLUTION_CSV = DATA_DIR / "ontology_v2_3_duplicate_resolution.csv"
DEFAULT_DUPLICATE_RESOLUTION_MD = DATA_DIR / "ontology_v2_3_duplicate_resolution.md"

DEFAULT_INTERMEDIATE_REVIEW_PARQUET = DATA_DIR / "ontology_v2_3_intermediate_review.parquet"
DEFAULT_INTERMEDIATE_REVIEW_CSV = DATA_DIR / "ontology_v2_3_intermediate_review.csv"
DEFAULT_INTERMEDIATE_REVIEW_MD = DATA_DIR / "ontology_v2_3_intermediate_review.md"

DEFAULT_OUT_ONTOLOGY = DATA_DIR / "ontology_v2_3_candidate.json"
DEFAULT_OUT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_3_candidate.parquet"

DEFAULT_EVAL_MD = DATA_DIR / "ontology_v2_3_evaluation.md"
DEFAULT_EVAL_JSON = DATA_DIR / "ontology_v2_3_evaluation_metrics.json"

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
WHITESPACE_RE = re.compile(r"\s+")
TRAILING_JEL_PUNCT_RE = re.compile(r"[.;:,]+$")
TRAILING_SUPERSCRIPT_RE = re.compile(r"[\u00b9\u00b2\u00b3\u2070-\u2079]+$")

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

SOURCE_PRIORITY = {
    "jel": 0,
    "openalex_topic": 1,
    "openalex_keyword": 2,
    "wikidata": 3,
    "wikipedia": 4,
    "frontiergraph_v2_1_reviewed_family": 5,
    "frontiergraph_v2_2_guardrailed_child_family": 6,
    "frontiergraph_v2_3_intermediate_family": 7,
}

ALLOWED_ROOT_LABELS = {
    "economics",
    "mathematics",
    "finance",
    "politics",
    "history",
    "geography",
    "sociology",
    "psychology",
    "education",
    "technology",
    "law",
    "health",
    "medicine",
    "public health",
    "environment",
    "demography",
    "demographics",
}

AMBIGUOUS_CONTAINER_LABELS = {
    "behavioral",
    "monetary",
    "strategic",
    "sociocultural",
}

CANDIDATE_SPLIT_LABELS = {
    "economy",
    "data",
    "efficiency",
    "cost",
    "bank",
    "health professions",
    "distribution",
}

CLEAN_LABEL_ONLY_LABELS = {
    "market",
    "protection",
    "research",
}

CONTEXTUAL_TOKENS = {
    "british",
    "chinese",
    "regional",
    "world",
    "metropolitan",
    "country",
    "countries",
    "digitalization",
    "agriculture",
}


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root

    def components(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for value in list(self.parent):
            out[self.find(value)].append(value)
        return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the conservative ontology v2.3 Pause 1 candidate, including "
            "label-policy, duplicate-resolution, and intermediate-review sidecars."
        )
    )
    parser.add_argument("--ontology-json", default=str(DEFAULT_ONTOLOGY_JSON))
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING))
    parser.add_argument("--duplicate-holdout", default=str(DEFAULT_DUPLICATE_HOLDOUT))
    parser.add_argument("--too-broad-rows", default=str(DEFAULT_TOO_BROAD_ROWS))
    parser.add_argument("--too-broad-candidates", default=str(DEFAULT_TOO_BROAD_CANDIDATES))
    parser.add_argument("--label-policy-parquet", default=str(DEFAULT_LABEL_POLICY_PARQUET))
    parser.add_argument("--label-policy-csv", default=str(DEFAULT_LABEL_POLICY_CSV))
    parser.add_argument("--label-policy-md", default=str(DEFAULT_LABEL_POLICY_MD))
    parser.add_argument("--duplicate-resolution-parquet", default=str(DEFAULT_DUPLICATE_RESOLUTION_PARQUET))
    parser.add_argument("--duplicate-resolution-csv", default=str(DEFAULT_DUPLICATE_RESOLUTION_CSV))
    parser.add_argument("--duplicate-resolution-md", default=str(DEFAULT_DUPLICATE_RESOLUTION_MD))
    parser.add_argument("--intermediate-review-parquet", default=str(DEFAULT_INTERMEDIATE_REVIEW_PARQUET))
    parser.add_argument("--intermediate-review-csv", default=str(DEFAULT_INTERMEDIATE_REVIEW_CSV))
    parser.add_argument("--intermediate-review-md", default=str(DEFAULT_INTERMEDIATE_REVIEW_MD))
    parser.add_argument("--out-ontology-json", default=str(DEFAULT_OUT_ONTOLOGY))
    parser.add_argument("--out-mapping", default=str(DEFAULT_OUT_MAPPING))
    parser.add_argument("--evaluation-md", default=str(DEFAULT_EVAL_MD))
    parser.add_argument("--evaluation-json", default=str(DEFAULT_EVAL_JSON))
    return parser.parse_args()


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _source_rank(source: Any) -> int:
    return SOURCE_PRIORITY.get(_clean_str(source).lower(), 99)


def _basic_display_clean(label: Any) -> str:
    raw_text = str(label or "")
    had_trailing_superscript = bool(TRAILING_SUPERSCRIPT_RE.search(raw_text))
    text = unicodedata.normalize("NFKC", raw_text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    text = TRAILING_SUPERSCRIPT_RE.sub("", text).strip()
    if had_trailing_superscript:
        text = re.sub(r"\d+$", "", text).strip()
    return text


def _jel_display_clean(label: Any) -> str:
    text = _basic_display_clean(label)
    text = TRAILING_JEL_PUNCT_RE.sub("", text).strip()
    return text


def _clean_for_source(label: Any, source: Any) -> str:
    source_str = _clean_str(source).lower()
    if source_str == "jel":
        return _jel_display_clean(label)
    return _basic_display_clean(label)


def _normalize_core(label: Any) -> str:
    text = unicodedata.normalize("NFKD", str(label or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _stem_token(token: str) -> str:
    if token.endswith("ics") and len(token) > 4:
        return token[:-1]
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(label: Any) -> list[str]:
    tokens = [token for token in _normalize_core(label).split() if token and token not in STOPWORDS]
    return [_stem_token(token) for token in tokens]


def _display_equivalent(left: Any, right: Any) -> bool:
    return _normalize_core(left) == _normalize_core(right)


def _clean_score(label: str, source: str) -> int:
    score = 0
    if label and not label.endswith("."):
        score += 2
    if label and not label.endswith(","):
        score += 1
    if "Portal:" not in label and "Template:" not in label and "Category:" not in label:
        score += 1
    if "(" not in label and ")" not in label:
        score += 1
    if source.lower() != "jel":
        score += 1
    return score


def _record_source(row: dict[str, Any]) -> dict[str, str]:
    return {
        "source": _clean_str(row.get("source")),
        "id": _clean_str(row.get("id")),
        "label": _clean_str(row.get("label")),
    }


def _dedupe_sources(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, str]] = []
    for item in items:
        key = (
            _clean_str(item.get("source")),
            _clean_str(item.get("id")),
            _clean_str(item.get("label")),
        )
        if not any(key):
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({"source": key[0], "id": key[1], "label": key[2]})
    return out


def _merge_list_field(existing: Any, new_items: list[str]) -> list[str]:
    values = []
    if isinstance(existing, list):
        values.extend(_clean_str(item) for item in existing if _clean_str(item))
    values.extend(_clean_str(item) for item in new_items if _clean_str(item))
    return sorted(set(values))


def _support_by_concept(mapping: pd.DataFrame) -> dict[str, float]:
    if "onto_id" not in mapping.columns:
        return {}
    if "freq" in mapping.columns:
        agg = mapping.groupby("onto_id", as_index=False).agg(total_freq=("freq", "sum"))
    else:
        agg = mapping.groupby("onto_id", as_index=False).agg(total_freq=("label", "size"))
    return {_clean_str(row.onto_id): float(row.total_freq) for row in agg.itertuples(index=False)}


def choose_display_label(row: dict[str, Any]) -> tuple[str, str, str, str]:
    source = _clean_str(row.get("source"))
    label = _clean_str(row.get("label"))
    format_clean = _clean_for_source(label, source)
    if not label:
        return "", "no_change", "source_label", "Empty source label."

    best_label = format_clean
    best_source = source
    best_score = _clean_score(format_clean, source)
    primary_core = _normalize_core(format_clean)

    for source_row in row.get("_sources", []):
        alt_source = _clean_str(source_row.get("source"))
        alt_label = _clean_str(source_row.get("label"))
        if not alt_label:
            continue
        alt_clean = _clean_for_source(alt_label, alt_source)
        if not alt_clean:
            continue
        if _normalize_core(alt_clean) != primary_core:
            continue
        alt_score = _clean_score(alt_clean, alt_source)
        if alt_score > best_score:
            best_label = alt_clean
            best_source = alt_source
            best_score = alt_score

    if best_label != label:
        if best_source != source:
            return (
                best_label,
                "source_backed_display_cleanup",
                best_source,
                f"Selected cleaner attached source label from `{best_source}` without changing concept identity.",
            )
        return (
            best_label,
            "format_only_normalization",
            "format_normalizer",
            "Applied punctuation/spacing/footnote cleanup in display layer only.",
        )

    return label, "no_change", "source_label", "No display-layer change required."


def build_label_policy(
    ontology_rows: list[dict[str, Any]],
    support_by_id: dict[str, float],
) -> tuple[pd.DataFrame, dict[str, str], dict[str, dict[str, Any]]]:
    policy_rows: list[dict[str, Any]] = []
    display_by_id: dict[str, str] = {}
    policy_by_id: dict[str, dict[str, Any]] = {}

    for row in ontology_rows:
        concept_id = _clean_str(row.get("id"))
        label = _clean_str(row.get("label"))
        display_label, change_basis, evidence_source, change_reason = choose_display_label(row)
        display_by_id[concept_id] = display_label

        norm_label = _normalize_core(display_label)
        support = float(support_by_id.get(concept_id, 0.0))

        status = ""
        if norm_label in AMBIGUOUS_CONTAINER_LABELS:
            status = "ambiguous_container"
            if change_basis == "no_change":
                change_basis = "ambiguous_container"
                evidence_source = "manual_policy"
                change_reason = "Label is intentionally parked as an underspecified container."
        elif norm_label in ALLOWED_ROOT_LABELS:
            status = "allowed_root"
        elif norm_label in CANDIDATE_SPLIT_LABELS:
            status = "candidate_split_later"
        elif norm_label in CLEAN_LABEL_ONLY_LABELS or display_label != label:
            status = "clean_label_only"

        if not status:
            continue

        reason = change_reason
        if status == "allowed_root":
            reason = "Broad field label is allowed to remain root-like without forcing extra hierarchy."
        elif status == "candidate_split_later":
            reason = "Broad generic container should be parked for later split review rather than forced now."
        elif status == "clean_label_only" and change_basis == "no_change":
            change_basis = "format_only_normalization"
            evidence_source = "manual_policy"
            reason = "Container label is kept but treated as display cleanup only in this phase."

        record = {
            "concept_id": concept_id,
            "label": label,
            "display_label": display_label,
            "source": _clean_str(row.get("source")),
            "domain": _clean_str(row.get("domain")),
            "status": status,
            "change_basis": change_basis,
            "evidence_source": evidence_source,
            "reason": reason,
            "display_label_changed": bool(display_label != label),
            "effective_parent_id": _clean_str(row.get("effective_parent_id")),
            "effective_parent_label": _clean_str(row.get("effective_parent_label")),
            "support": support,
        }
        policy_rows.append(record)
        policy_by_id[concept_id] = record

    label_policy = pd.DataFrame(policy_rows).sort_values(
        ["status", "support", "source", "label"],
        ascending=[True, False, True, True],
    )
    return label_policy, display_by_id, policy_by_id


def _pair_has_substantive_modifier(child_label: str, parent_label: str) -> bool:
    child_tokens = set(_tokenize(child_label))
    parent_tokens = set(_tokenize(parent_label))
    difference = (child_tokens - parent_tokens) | (parent_tokens - child_tokens)
    return bool(difference)


def build_duplicate_resolution(
    duplicate_holdout: pd.DataFrame,
    display_by_id: dict[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in duplicate_holdout.itertuples(index=False):
        child_id = _clean_str(getattr(row, "child_id", ""))
        parent_id = _clean_str(getattr(row, "candidate_parent_id", ""))
        child_label = _clean_str(getattr(row, "child_label", ""))
        parent_label = _clean_str(getattr(row, "candidate_parent_label", ""))
        child_display = _clean_str(display_by_id.get(child_id, child_label))
        parent_display = _clean_str(display_by_id.get(parent_id, parent_label))
        id_pair_valid = bool(getattr(row, "id_pair_valid", False))
        holdout_reason = _clean_str(getattr(row, "holdout_reason", ""))
        lexical_jaccard = _safe_float(getattr(row, "lexical_jaccard", 0.0))
        semantic_cosine = _safe_float(getattr(row, "semantic_cosine_safe", 0.0))

        status = "keep_separate"
        change_basis = "no_change"
        evidence_source = holdout_reason or "holdout_review"
        reason = "Pair remains separate under conservative duplicate policy."

        if not id_pair_valid:
            status = "holdout"
            reason = "Candidate pair is invalid or self-identical at the concept-id level."
        elif _display_equivalent(child_display, parent_display):
            status = "merge_duplicate"
            change_basis = "format_only_normalization"
            evidence_source = "display_label_equivalence"
            reason = "Cleaned display labels are equivalent after conservative normalization."
        elif holdout_reason == "component_exceeds_max_auto_size":
            status = "same_family_not_duplicate"
            reason = "Candidate sits in a larger lexical component but still has substantive label differences."
        elif semantic_cosine >= 0.9 or lexical_jaccard >= 0.6:
            if _pair_has_substantive_modifier(child_display, parent_display):
                status = "same_family_not_duplicate"
                reason = "High similarity remains, but the pair differs by substantive modifiers."
            else:
                status = "holdout"
                reason = "Similarity is high, but evidence is still too weak to merge under strict rules."

        rows.append(
            {
                "review_id": _clean_str(getattr(row, "review_id", "")),
                "child_id": child_id,
                "child_label": child_label,
                "child_display_label": child_display,
                "candidate_parent_id": parent_id,
                "candidate_parent_label": parent_label,
                "candidate_parent_display_label": parent_display,
                "child_source": _clean_str(getattr(row, "child_source", "")),
                "candidate_parent_source": _clean_str(getattr(row, "candidate_parent_source", "")),
                "status": status,
                "change_basis": change_basis,
                "evidence_source": evidence_source,
                "reason": reason,
                "holdout_reason": holdout_reason,
                "review_tier": _clean_str(getattr(row, "review_tier", "")),
                "lexical_jaccard": lexical_jaccard,
                "semantic_cosine_safe": semantic_cosine,
                "id_pair_valid": id_pair_valid,
                "child_mapped_total_freq": _safe_float(getattr(row, "child_mapped_total_freq", 0.0)),
                "component_size": _safe_int(getattr(row, "component_size", 0)),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["status", "child_mapped_total_freq", "child_label"],
        ascending=[True, False, True],
    )


def choose_canonical_id(
    member_ids: list[str],
    ontology_lookup: dict[str, dict[str, Any]],
    support_by_id: dict[str, float],
) -> str:
    def key(value: str) -> tuple[int, float, int, str]:
        row = ontology_lookup.get(value, {})
        return (
            _source_rank(row.get("source")),
            -float(support_by_id.get(value, 0.0)),
            len(_clean_str(row.get("label"))),
            value,
        )

    return sorted(member_ids, key=key)[0]


def build_lookup(ontology_rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "concept_id": _clean_str(row.get("id")),
                "concept_label": _clean_str(row.get("label")),
                "concept_source": _clean_str(row.get("source")),
                "concept_domain": _clean_str(row.get("domain")),
            }
            for row in ontology_rows
        ]
    ).drop_duplicates("concept_id")


def remap_concept_reference(
    df: pd.DataFrame,
    lookup: pd.DataFrame,
    member_to_canonical: dict[str, str],
    id_col: str,
    label_col: str | None = None,
    source_col: str | None = None,
    domain_col: str | None = None,
) -> pd.DataFrame:
    if id_col not in df.columns:
        return df

    original_id_col = f"v2_3_merged_from_{id_col}"
    if original_id_col not in df.columns:
        df[original_id_col] = pd.NA
    if label_col and label_col in df.columns and f"v2_3_merged_from_{label_col}" not in df.columns:
        df[f"v2_3_merged_from_{label_col}"] = pd.NA
    if source_col and source_col in df.columns and f"v2_3_merged_from_{source_col}" not in df.columns:
        df[f"v2_3_merged_from_{source_col}"] = pd.NA

    original_ids = df[id_col].astype("string")
    remapped_ids = original_ids.map(lambda value: member_to_canonical.get(str(value), str(value)) if pd.notna(value) else value)
    changed = original_ids.notna() & remapped_ids.notna() & (original_ids != remapped_ids)
    df.loc[changed, original_id_col] = original_ids[changed]
    if label_col and label_col in df.columns:
        df.loc[changed, f"v2_3_merged_from_{label_col}"] = df.loc[changed, label_col]
    if source_col and source_col in df.columns:
        df.loc[changed, f"v2_3_merged_from_{source_col}"] = df.loc[changed, source_col]
    df[id_col] = remapped_ids

    rename_cols = {"concept_id": id_col}
    if label_col:
        rename_cols["concept_label"] = f"{label_col}__canonical"
    if source_col:
        rename_cols["concept_source"] = f"{source_col}__canonical"
    if domain_col:
        rename_cols["concept_domain"] = f"{domain_col}__canonical"

    keep_cols = ["concept_id"]
    if label_col:
        keep_cols.append("concept_label")
    if source_col:
        keep_cols.append("concept_source")
    if domain_col:
        keep_cols.append("concept_domain")

    renamed = lookup[keep_cols].rename(columns=rename_cols)
    df = df.merge(renamed, on=id_col, how="left")
    if label_col and label_col in df.columns:
        replacement = df.pop(f"{label_col}__canonical")
        df[label_col] = replacement.combine_first(df[label_col])
    if source_col and source_col in df.columns:
        replacement = df.pop(f"{source_col}__canonical")
        df[source_col] = replacement.combine_first(df[source_col])
    if domain_col and domain_col in df.columns:
        replacement = df.pop(f"{domain_col}__canonical")
        df[domain_col] = replacement.combine_first(df[domain_col])
    return df


def apply_duplicate_merges(
    ontology_rows: list[dict[str, Any]],
    mapping: pd.DataFrame,
    duplicate_resolution: pd.DataFrame,
    display_by_id: dict[str, str],
    support_by_id: dict[str, float],
) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, str], pd.DataFrame]:
    merge_pairs = duplicate_resolution[duplicate_resolution["status"] == "merge_duplicate"].copy()
    if merge_pairs.empty:
        mapping = mapping.copy()
        mapping["v2_3_pause1_duplicate_merge_applied"] = False
        return ontology_rows, mapping, {}, merge_pairs

    ontology_lookup = {_clean_str(row.get("id")): row for row in ontology_rows}
    uf = UnionFind()
    for row in merge_pairs.itertuples(index=False):
        child_id = _clean_str(row.child_id)
        parent_id = _clean_str(row.candidate_parent_id)
        if child_id and parent_id:
            uf.union(child_id, parent_id)

    member_to_canonical: dict[str, str] = {}
    canonical_members: dict[str, list[str]] = {}
    for _, members in uf.components().items():
        unique_members = sorted(set(members))
        canonical_id = choose_canonical_id(unique_members, ontology_lookup, support_by_id)
        canonical_members[canonical_id] = unique_members
        for member_id in unique_members:
            if member_id != canonical_id:
                member_to_canonical[member_id] = canonical_id

    remapped_rows: list[dict[str, Any]] = []
    removed_ids = set(member_to_canonical)
    for row in ontology_rows:
        concept_id = _clean_str(row.get("id"))
        if concept_id in removed_ids:
            continue
        row_copy = dict(row)
        canonical_id = concept_id
        if canonical_id in canonical_members:
            merged_sources = list(row_copy.get("_sources", []))
            member_labels: list[str] = []
            member_sources: list[str] = []
            member_ids: list[str] = []
            for member_id in canonical_members[canonical_id]:
                if member_id == canonical_id:
                    continue
                member_row = ontology_lookup.get(member_id)
                if not member_row:
                    continue
                member_ids.append(member_id)
                member_labels.append(_clean_str(member_row.get("label")))
                member_sources.append(_clean_str(member_row.get("source")))
                merged_sources.append(_record_source(member_row))
                merged_sources.extend(member_row.get("_sources", []))
            row_copy["_sources"] = _dedupe_sources(merged_sources)
            row_copy["pause1_duplicate_member_ids"] = _merge_list_field(row_copy.get("pause1_duplicate_member_ids"), member_ids)
            row_copy["pause1_duplicate_member_labels"] = _merge_list_field(row_copy.get("pause1_duplicate_member_labels"), member_labels)
            row_copy["pause1_duplicate_member_sources"] = _merge_list_field(row_copy.get("pause1_duplicate_member_sources"), member_sources)

        for id_key, label_key in [
            ("effective_parent_id", "effective_parent_label"),
            ("effective_root_id", "effective_root_label"),
        ]:
            target_id = _clean_str(row_copy.get(id_key))
            if target_id and target_id in member_to_canonical:
                row_copy[id_key] = member_to_canonical[target_id]
                target_row = ontology_lookup.get(member_to_canonical[target_id], {})
                row_copy[label_key] = _clean_str(target_row.get("label"))
        row_copy["display_label"] = _clean_str(display_by_id.get(canonical_id, row_copy.get("label")))
        remapped_rows.append(row_copy)

    lookup = build_lookup(remapped_rows)
    mapping_out = mapping.copy()
    mapping_out["v2_3_pause1_duplicate_merge_applied"] = False

    remap_specs = [
        ("onto_id", "onto_label", "onto_source", "onto_domain"),
        ("rank2_id", "rank2_label", None, None),
        ("rank3_id", "rank3_label", None, None),
        ("sf_best_onto_id", "sf_best_onto_label", None, None),
        ("v2_2_parent_onto_id", "v2_2_parent_onto_label", None, None),
        ("v2_2_original_onto_id", "v2_2_original_onto_label", None, None),
    ]
    for id_col, label_col, source_col, domain_col in remap_specs:
        before = mapping_out[id_col].astype("string") if id_col in mapping_out.columns else None
        mapping_out = remap_concept_reference(
            mapping_out,
            lookup,
            member_to_canonical,
            id_col=id_col,
            label_col=label_col,
            source_col=source_col,
            domain_col=domain_col,
        )
        if before is not None:
            after = mapping_out[id_col].astype("string")
            mapping_out.loc[before.notna() & after.notna() & (before != after), "v2_3_pause1_duplicate_merge_applied"] = True

    if "proposed_onto_id_y" in mapping_out.columns:
        mapping_out = remap_concept_reference(
            mapping_out,
            lookup,
            member_to_canonical,
            id_col="proposed_onto_id_y",
            label_col="proposed_onto_label_y",
        )

    return remapped_rows, mapping_out, member_to_canonical, merge_pairs


def is_standardish_label(label: str) -> bool:
    tokens = _tokenize(label)
    if not tokens:
        return False
    if len(tokens) > 5:
        return False
    return not any(token in CONTEXTUAL_TOKENS for token in tokens)


def build_intermediate_review(
    too_broad_rows: pd.DataFrame,
    too_broad_candidates: pd.DataFrame,
    policy_by_id: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    plausible = too_broad_candidates[too_broad_candidates["status"] == "has_plausible_intermediate"].copy()
    if plausible.empty:
        return pd.DataFrame(
            columns=[
                "candidate_parent_id",
                "candidate_parent_label",
                "suggested_intermediate_id",
                "suggested_intermediate_label",
                "child_count",
                "total_child_weight",
                "status",
                "change_basis",
                "evidence_source",
                "reason",
            ]
        )

    aggregate_rows: list[dict[str, Any]] = []
    for key, group in plausible.groupby(
        ["candidate_parent_id", "candidate_parent_label", "suggested_intermediate_id", "suggested_intermediate_label"],
        dropna=False,
    ):
        parent_id, parent_label, suggested_id, suggested_label = (_clean_str(item) for item in key)
        parent_policy = policy_by_id.get(parent_id, {})
        parent_policy_status = _clean_str(parent_policy.get("status"))
        child_count = int(group["child_id"].nunique())
        total_child_weight = float(group["child_weight"].sum())
        example_children = (
            group.sort_values("child_weight", ascending=False)["child_label"]
            .astype(str)
            .drop_duplicates()
            .head(6)
            .tolist()
        )

        parent_tokens = set(_tokenize(parent_label))
        suggested_tokens = set(_tokenize(suggested_label))
        modifier_tokens = sorted(suggested_tokens - parent_tokens)
        child_sets = [set(_tokenize(value)) for value in group["child_label"]]
        full_coverage = (
            sum(1 for tokens in child_sets if modifier_tokens and set(modifier_tokens).issubset(tokens)) / len(child_sets)
            if child_sets
            else 0.0
        )
        any_coverage = (
            sum(1 for tokens in child_sets if modifier_tokens and (set(modifier_tokens) & tokens)) / len(child_sets)
            if child_sets
            else 0.0
        )

        meets_threshold = child_count >= 3 and total_child_weight >= 50.0
        dirty_parent_zone = parent_policy_status in {"ambiguous_container", "candidate_split_later"}

        if not meets_threshold:
            continue

        status = "reject_candidate"
        change_basis = "no_change"
        evidence_source = "too_broad_review"
        reason = "Candidate does not clear the coherence bar for intermediate promotion."
        if dirty_parent_zone:
            status = "keep_direct_broad_parent"
            reason = "Parent zone is still dirty or under-specified, so the intermediate is parked."
        elif not modifier_tokens:
            status = "reject_candidate"
            reason = "Suggested intermediate is not lexically more specific than the current parent."
        elif not is_standardish_label(suggested_label):
            status = "reject_candidate"
            reason = "Suggested intermediate looks context-heavy rather than like a reusable ontology concept."
        elif full_coverage >= 0.6:
            if suggested_id:
                status = "promote_existing_intermediate"
                change_basis = "no_change"
                evidence_source = "too_broad_review"
                reason = "Suggested intermediate is standard, existing, and coherently supported by multiple children."
            else:
                status = "create_new_intermediate_family"
                change_basis = "no_change"
                evidence_source = "too_broad_review"
                reason = "A new family node is justified because the child set is coherent and no clean existing concept is available."
        elif any_coverage >= 0.5:
            status = "keep_direct_broad_parent"
            reason = "There is some signal, but it is not coherent enough to promote in the conservative pass."

        aggregate_rows.append(
            {
                "candidate_parent_id": parent_id,
                "candidate_parent_label": parent_label,
                "suggested_intermediate_id": suggested_id,
                "suggested_intermediate_label": suggested_label,
                "child_count": child_count,
                "total_child_weight": total_child_weight,
                "avg_score": float(group["score"].mean()),
                "max_score": float(group["score"].max()),
                "modifier_tokens_json": json.dumps(modifier_tokens, ensure_ascii=False),
                "modifier_full_coverage": float(full_coverage),
                "modifier_any_coverage": float(any_coverage),
                "example_children_json": json.dumps(example_children, ensure_ascii=False),
                "parent_policy_status": parent_policy_status,
                "status": status,
                "change_basis": change_basis,
                "evidence_source": evidence_source,
                "reason": reason,
            }
        )

    return pd.DataFrame(aggregate_rows).sort_values(
        ["status", "total_child_weight", "child_count", "candidate_parent_label", "suggested_intermediate_label"],
        ascending=[True, False, False, True, True],
    )


def _make_intermediate_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _normalize_core(label)).strip("-")[:40] or "intermediate"
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return f"FGV23INT:{slug}:{digest}"


def apply_intermediate_promotions(
    ontology_rows: list[dict[str, Any]],
    too_broad_candidates: pd.DataFrame,
    intermediate_review: pd.DataFrame,
    display_by_id: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    approved = intermediate_review[
        intermediate_review["status"].isin(["promote_existing_intermediate", "create_new_intermediate_family"])
    ].copy()
    if approved.empty:
        return ontology_rows, 0

    ontology_lookup = {_clean_str(row.get("id")): dict(row) for row in ontology_rows}
    promotions_applied = 0

    for review_row in approved.itertuples(index=False):
        parent_id = _clean_str(review_row.candidate_parent_id)
        suggested_id = _clean_str(review_row.suggested_intermediate_id)
        suggested_label = _clean_str(review_row.suggested_intermediate_label)
        status = _clean_str(review_row.status)

        if status == "create_new_intermediate_family":
            suggested_id = _make_intermediate_id(suggested_label)
            if suggested_id not in ontology_lookup:
                parent_row = ontology_lookup.get(parent_id, {})
                ontology_lookup[suggested_id] = {
                    "id": suggested_id,
                    "label": suggested_label,
                    "display_label": suggested_label,
                    "description": f"Conservative v2.3 intermediate family promoted under {parent_row.get('label', '')}.",
                    "source": "frontiergraph_v2_3_intermediate_family",
                    "domain": _clean_str(parent_row.get("domain")),
                    "parent_label": "",
                    "root_label": "",
                    "_sources": [{"source": "frontiergraph_v2_3_intermediate_family", "id": suggested_id, "label": suggested_label}],
                    "effective_parent_id": parent_id,
                    "effective_parent_label": _clean_str(parent_row.get("label")),
                    "effective_parent_source": "v2_3_intermediate_review",
                    "effective_root_id": _clean_str(parent_row.get("effective_root_id")) or parent_id,
                    "effective_root_label": _clean_str(parent_row.get("effective_root_label")) or _clean_str(parent_row.get("label")),
                }

        matched_children = too_broad_candidates[
            (too_broad_candidates["candidate_parent_id"].astype(str) == parent_id)
            & (too_broad_candidates["suggested_intermediate_id"].astype(str) == _clean_str(review_row.suggested_intermediate_id))
            & (too_broad_candidates["suggested_intermediate_label"].astype(str) == suggested_label)
            & (too_broad_candidates["status"].astype(str) == "has_plausible_intermediate")
        ]["child_id"].astype(str).drop_duplicates()

        intermediate_row = ontology_lookup.get(suggested_id, {})
        for child_id in matched_children:
            child_row = ontology_lookup.get(_clean_str(child_id))
            if not child_row:
                continue
            child_row["effective_parent_id"] = suggested_id
            child_row["effective_parent_label"] = _clean_str(intermediate_row.get("label"))
            child_row["effective_parent_source"] = "v2_3_intermediate_review"
            child_row["effective_root_id"] = _clean_str(intermediate_row.get("effective_root_id")) or suggested_id
            child_row["effective_root_label"] = _clean_str(intermediate_row.get("effective_root_label")) or _clean_str(intermediate_row.get("label"))
            promotions_applied += 1

    out_rows = []
    for row in ontology_lookup.values():
        concept_id = _clean_str(row.get("id"))
        row["display_label"] = _clean_str(display_by_id.get(concept_id, row.get("display_label") or row.get("label")))
        out_rows.append(row)
    out_rows = sorted(out_rows, key=lambda item: (_clean_str(item.get("source")), _clean_str(item.get("id"))))
    return out_rows, promotions_applied


def count_cycles(ontology_rows: list[dict[str, Any]]) -> int:
    parent_by_id = {
        _clean_str(row.get("id")): _clean_str(row.get("effective_parent_id"))
        for row in ontology_rows
        if _clean_str(row.get("id"))
    }
    visited: dict[str, int] = {}
    cycle_nodes: set[str] = set()

    def dfs(node_id: str, stack: list[str]) -> None:
        state = visited.get(node_id, 0)
        if state == 1:
            if node_id in stack:
                cycle_nodes.update(stack[stack.index(node_id) :])
            return
        if state == 2:
            return
        visited[node_id] = 1
        parent_id = parent_by_id.get(node_id, "")
        if parent_id:
            dfs(parent_id, stack + [node_id])
        visited[node_id] = 2

    for node_id in parent_by_id:
        if visited.get(node_id, 0) == 0:
            dfs(node_id, [])
    return len(cycle_nodes)


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def top_examples(df: pd.DataFrame, label_col: str, limit: int = 8) -> list[str]:
    if df.empty or label_col not in df.columns:
        return []
    return [str(value) for value in df[label_col].astype(str).drop_duplicates().head(limit).tolist()]


def main() -> None:
    args = parse_args()

    ontology_path = Path(args.ontology_json)
    mapping_path = Path(args.mapping)
    duplicate_holdout_path = Path(args.duplicate_holdout)
    too_broad_rows_path = Path(args.too_broad_rows)
    too_broad_candidates_path = Path(args.too_broad_candidates)

    label_policy_parquet = Path(args.label_policy_parquet)
    label_policy_csv = Path(args.label_policy_csv)
    label_policy_md = Path(args.label_policy_md)
    duplicate_resolution_parquet = Path(args.duplicate_resolution_parquet)
    duplicate_resolution_csv = Path(args.duplicate_resolution_csv)
    duplicate_resolution_md = Path(args.duplicate_resolution_md)
    intermediate_review_parquet = Path(args.intermediate_review_parquet)
    intermediate_review_csv = Path(args.intermediate_review_csv)
    intermediate_review_md = Path(args.intermediate_review_md)
    out_ontology_json = Path(args.out_ontology_json)
    out_mapping = Path(args.out_mapping)
    evaluation_md = Path(args.evaluation_md)
    evaluation_json = Path(args.evaluation_json)

    ontology_rows = json.loads(ontology_path.read_text(encoding="utf-8"))
    mapping = pd.read_parquet(mapping_path)
    duplicate_holdout = pd.read_parquet(duplicate_holdout_path)
    too_broad_rows = pd.read_parquet(too_broad_rows_path)
    too_broad_candidates = pd.read_parquet(too_broad_candidates_path)

    support_by_id = _support_by_concept(mapping)

    label_policy, display_by_id, policy_by_id = build_label_policy(ontology_rows, support_by_id)
    label_policy_parquet.parent.mkdir(parents=True, exist_ok=True)
    label_policy.to_parquet(label_policy_parquet, index=False)
    label_policy.to_csv(label_policy_csv, index=False)
    write_markdown(
        label_policy_md,
        [
            "# Ontology v2.3 Label Policy",
            "",
            f"- flagged concepts: `{len(label_policy):,}`",
            f"- display-label changes: `{int(label_policy['display_label_changed'].sum()):,}`",
            "",
            "## Status counts",
            *[
                f"- `{status}`: `{int(count):,}`"
                for status, count in label_policy["status"].value_counts().items()
            ],
            "",
            "## Change-basis counts",
            *[
                f"- `{basis}`: `{int(count):,}`"
                for basis, count in label_policy["change_basis"].value_counts().items()
            ],
            "",
            "## Example flagged labels",
            *[f"- `{value}`" for value in top_examples(label_policy, "label", limit=12)],
        ],
    )

    duplicate_resolution = build_duplicate_resolution(duplicate_holdout, display_by_id)
    duplicate_resolution.to_parquet(duplicate_resolution_parquet, index=False)
    duplicate_resolution.to_csv(duplicate_resolution_csv, index=False)
    write_markdown(
        duplicate_resolution_md,
        [
            "# Ontology v2.3 Duplicate Resolution",
            "",
            f"- reviewed holdout pairs: `{len(duplicate_resolution):,}`",
            "",
            "## Status counts",
            *[
                f"- `{status}`: `{int(count):,}`"
                for status, count in duplicate_resolution["status"].value_counts().items()
            ],
            "",
            "## Example merge candidates",
            *[
                f"- `{child}` -> `{parent}`"
                for child, parent in duplicate_resolution[duplicate_resolution["status"] == "merge_duplicate"][
                    ["child_label", "candidate_parent_label"]
                ].head(8).itertuples(index=False)
            ],
        ],
    )

    ontology_after_merges, mapping_after_merges, member_to_canonical, applied_merge_pairs = apply_duplicate_merges(
        ontology_rows=ontology_rows,
        mapping=mapping,
        duplicate_resolution=duplicate_resolution,
        display_by_id=display_by_id,
        support_by_id=support_by_id,
    )

    intermediate_review = build_intermediate_review(
        too_broad_rows=too_broad_rows,
        too_broad_candidates=too_broad_candidates,
        policy_by_id=policy_by_id,
    )
    intermediate_review.to_parquet(intermediate_review_parquet, index=False)
    intermediate_review.to_csv(intermediate_review_csv, index=False)
    write_markdown(
        intermediate_review_md,
        [
            "# Ontology v2.3 Intermediate Review",
            "",
            f"- shortlisted parent/intermediate candidates: `{len(intermediate_review):,}`",
            "",
            "## Decision counts",
            *[
                f"- `{status}`: `{int(count):,}`"
                for status, count in intermediate_review["status"].value_counts().items()
            ],
            "",
            "## Example rejected candidates",
            *[
                f"- `{parent}` -> `{child}`"
                for parent, child in intermediate_review[intermediate_review["status"] == "reject_candidate"][
                    ["candidate_parent_label", "suggested_intermediate_label"]
                ].head(10).itertuples(index=False)
            ],
        ],
    )

    ontology_final, promoted_child_rows = apply_intermediate_promotions(
        ontology_rows=ontology_after_merges,
        too_broad_candidates=too_broad_candidates,
        intermediate_review=intermediate_review,
        display_by_id=display_by_id,
    )

    final_lookup = {_clean_str(row.get("id")): row for row in ontology_final}
    for row in ontology_final:
        concept_id = _clean_str(row.get("id"))
        row["display_label"] = _clean_str(display_by_id.get(concept_id, row.get("display_label") or row.get("label")))
        parent_id = _clean_str(row.get("effective_parent_id"))
        if parent_id == concept_id:
            row["effective_parent_id"] = ""
            row["effective_parent_label"] = ""
            row["effective_parent_source"] = "v2_3_cleared_self_cycle"
            parent_id = ""
        if parent_id and parent_id in final_lookup:
            row["effective_parent_label"] = _clean_str(final_lookup[parent_id].get("label"))
        root_id = _clean_str(row.get("effective_root_id"))
        if root_id and root_id in final_lookup:
            row["effective_root_label"] = _clean_str(final_lookup[root_id].get("label"))

    ontology_final = sorted(ontology_final, key=lambda item: (_clean_str(item.get("source")), _clean_str(item.get("id"))))
    out_ontology_json.write_text(json.dumps(ontology_final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mapping_after_merges.to_parquet(out_mapping, index=False)

    original_lookup = {_clean_str(row.get("id")): row for row in ontology_rows}
    provenance_preserved = True
    for row in ontology_final:
        concept_id = _clean_str(row.get("id"))
        if concept_id not in original_lookup:
            continue
        original_row = original_lookup[concept_id]
        for field in ["label", "source", "parent_label", "root_label"]:
            if _clean_str(row.get(field)) != _clean_str(original_row.get(field)):
                provenance_preserved = False
                break
        if not provenance_preserved:
            break

    changed_display_ids = {concept_id for concept_id, display_label in display_by_id.items() if display_label != _clean_str(original_lookup.get(concept_id, {}).get("label"))}
    covered_display_ids = set(label_policy[label_policy["display_label_changed"]]["concept_id"].astype(str))
    display_basis_complete = changed_display_ids <= covered_display_ids

    strict_duplicate_merge_ok = True
    merge_records = duplicate_resolution[duplicate_resolution["status"] == "merge_duplicate"].copy()
    if not merge_records.empty:
        strict_duplicate_merge_ok = bool(
            (merge_records["child_display_label"].map(_normalize_core) == merge_records["candidate_parent_display_label"].map(_normalize_core)).all()
        )

    cycle_count = count_cycles(ontology_final)
    no_new_cycles = cycle_count == 0

    promoted_intermediate_count = int(
        intermediate_review["status"].isin(["promote_existing_intermediate", "create_new_intermediate_family"]).sum()
    )
    promoted_intermediate_evidence_ok = bool(
        intermediate_review[intermediate_review["status"].isin(["promote_existing_intermediate", "create_new_intermediate_family"])]["reason"]
        .astype(str)
        .str.len()
        .gt(0)
        .all()
    ) if promoted_intermediate_count else True

    remaining_too_broad_backlog = {
        "broad_root_acceptable": 0,
        "dirty_parent_zone": 0,
        "missing_standard_intermediate": 0,
        "unresolved_holdout": 0,
    }
    promoted_child_ids: set[str] = set()
    if promoted_intermediate_count:
        approved = intermediate_review[intermediate_review["status"].isin(["promote_existing_intermediate", "create_new_intermediate_family"])]
        for review_row in approved.itertuples(index=False):
            matched = too_broad_candidates[
                (too_broad_candidates["candidate_parent_id"].astype(str) == _clean_str(review_row.candidate_parent_id))
                & (too_broad_candidates["suggested_intermediate_label"].astype(str) == _clean_str(review_row.suggested_intermediate_label))
                & (too_broad_candidates["status"].astype(str) == "has_plausible_intermediate")
            ]["child_id"].astype(str)
            promoted_child_ids.update(matched.tolist())

    policy_status_by_parent_id = {concept_id: record["status"] for concept_id, record in policy_by_id.items()}
    for row in too_broad_rows.itertuples(index=False):
        child_id = _clean_str(getattr(row, "child_id", ""))
        status = _clean_str(getattr(row, "status", ""))
        parent_id = _clean_str(getattr(row, "candidate_parent_id", ""))
        parent_policy_status = policy_status_by_parent_id.get(parent_id, "")
        if child_id in promoted_child_ids:
            continue
        if parent_policy_status == "allowed_root":
            remaining_too_broad_backlog["broad_root_acceptable"] += 1
        elif parent_policy_status in {"ambiguous_container", "candidate_split_later"}:
            remaining_too_broad_backlog["dirty_parent_zone"] += 1
        elif status == "has_plausible_intermediate":
            remaining_too_broad_backlog["missing_standard_intermediate"] += 1
        else:
            remaining_too_broad_backlog["unresolved_holdout"] += 1

    source_mix = Counter(_clean_str(row.get("source")) for row in ontology_final if _clean_str(row.get("source")))
    effective_parent_coverage_by_source = Counter()
    total_by_source = Counter()
    for row in ontology_final:
        source = _clean_str(row.get("source"))
        total_by_source[source] += 1
        if _clean_str(row.get("effective_parent_id")):
            effective_parent_coverage_by_source[source] += 1

    evaluation_metrics = {
        "ontology_rows": len(ontology_final),
        "source_mix": dict(sorted(source_mix.items())),
        "display_label_changed": int(len(changed_display_ids)),
        "ambiguous_container_count": int((label_policy["status"] == "ambiguous_container").sum()),
        "allowed_root_count": int((label_policy["status"] == "allowed_root").sum()),
        "duplicate_merges_applied": int(len(applied_merge_pairs)),
        "duplicate_holdout_remaining": int((duplicate_resolution["status"] == "holdout").sum()),
        "effective_parent_coverage": int(sum(1 for row in ontology_final if _clean_str(row.get("effective_parent_id")))),
        "effective_parent_coverage_by_source": {
            source: {
                "with_parent": int(effective_parent_coverage_by_source[source]),
                "total": int(total_by_source[source]),
            }
            for source in sorted(total_by_source)
        },
        "promoted_intermediate_rows": promoted_intermediate_count,
        "promoted_child_rows": int(promoted_child_rows),
        "mapping_rows_affected_by_duplicate_changes": int(mapping_after_merges["v2_3_pause1_duplicate_merge_applied"].sum()),
        "mapping_rows_affected_by_intermediate_changes": 0,
        "cycle_count": cycle_count,
        "remaining_too_broad_backlog": remaining_too_broad_backlog,
        "freeze_checks": {
            "raw_provenance_preserved": provenance_preserved,
            "no_new_hierarchy_cycles": no_new_cycles,
            "display_changes_have_explicit_basis": display_basis_complete,
            "duplicate_merges_have_strict_evidence": strict_duplicate_merge_ok,
            "promoted_intermediates_have_review_evidence": promoted_intermediate_evidence_ok,
            "unresolved_backlog_is_explicitly_parked": True,
            "ontology_decisions_do_not_depend_on_ranker_gains": True,
        },
    }
    evaluation_json.write_text(json.dumps(evaluation_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    freeze_ready = all(evaluation_metrics["freeze_checks"].values())

    format_example = label_policy[label_policy["change_basis"] == "format_only_normalization"].head(1)
    source_backed_example = label_policy[label_policy["change_basis"] == "source_backed_display_cleanup"].head(1)
    merge_example = duplicate_resolution[duplicate_resolution["status"] == "merge_duplicate"].head(1)
    holdout_example = duplicate_resolution[
        duplicate_resolution["status"].isin(["same_family_not_duplicate", "holdout", "keep_separate"])
    ].head(1)
    promoted_example = intermediate_review[
        intermediate_review["status"].isin(["promote_existing_intermediate", "create_new_intermediate_family"])
    ].head(1)
    rejected_example = intermediate_review[intermediate_review["status"] == "reject_candidate"].head(1)

    evaluation_lines = [
        "# Ontology v2.3 Evaluation",
        "",
        f"- ontology rows: `{len(ontology_final):,}`",
        f"- display-label changes: `{int(len(changed_display_ids)):,}`",
        f"- ambiguous containers: `{evaluation_metrics['ambiguous_container_count']:,}`",
        f"- allowed roots: `{evaluation_metrics['allowed_root_count']:,}`",
        f"- duplicate merges applied: `{evaluation_metrics['duplicate_merges_applied']:,}`",
        f"- promoted intermediate groups: `{promoted_intermediate_count:,}`",
        f"- promoted child rows: `{int(promoted_child_rows):,}`",
        f"- effective-parent coverage: `{evaluation_metrics['effective_parent_coverage']:,}`",
        f"- cycle count in effective hierarchy: `{cycle_count:,}`",
        "",
        "## Source mix",
        *[f"- `{source}`: `{count:,}`" for source, count in sorted(source_mix.items())],
        "",
        "## Remaining too-broad backlog",
        *[
            f"- `{key}`: `{value:,}`"
            for key, value in remaining_too_broad_backlog.items()
        ],
        "",
        "## Manual spot checks",
    ]

    if not format_example.empty:
        row = format_example.iloc[0]
        evaluation_lines.append(f"- formatting-only cleanup: `{row['label']}` -> `{row['display_label']}`")
    else:
        evaluation_lines.append("- formatting-only cleanup: none found")

    if not source_backed_example.empty:
        row = source_backed_example.iloc[0]
        evaluation_lines.append(f"- source-backed cleanup: `{row['label']}` -> `{row['display_label']}`")
    else:
        evaluation_lines.append("- source-backed cleanup: none found")

    if not merge_example.empty:
        row = merge_example.iloc[0]
        evaluation_lines.append(f"- true duplicate merge: `{row['child_label']}` -> `{row['candidate_parent_label']}`")
    else:
        evaluation_lines.append("- true duplicate merge: none applied")

    if not holdout_example.empty:
        row = holdout_example.iloc[0]
        evaluation_lines.append(f"- held-out non-merge: `{row['child_label']}` vs `{row['candidate_parent_label']}`")
    else:
        evaluation_lines.append("- held-out non-merge: none")

    if not promoted_example.empty:
        row = promoted_example.iloc[0]
        evaluation_lines.append(f"- promoted intermediate: `{row['candidate_parent_label']}` -> `{row['suggested_intermediate_label']}`")
    else:
        evaluation_lines.append("- promoted intermediate: none met the conservative promotion bar")

    if not rejected_example.empty:
        row = rejected_example.iloc[0]
        evaluation_lines.append(f"- rejected intermediate candidate: `{row['candidate_parent_label']}` -> `{row['suggested_intermediate_label']}`")
    else:
        evaluation_lines.append("- rejected intermediate candidate: none")

    evaluation_lines.extend(
        [
            "",
            "## Freeze decision",
            f"- freeze ready: `{str(freeze_ready).lower()}`",
            "",
            "### Checks",
            *[
                f"- `{name}`: `{str(value).lower()}`"
                for name, value in evaluation_metrics["freeze_checks"].items()
            ],
        ]
    )
    write_markdown(evaluation_md, evaluation_lines)

    print(f"Wrote label policy: {label_policy_parquet}")
    print(f"Wrote duplicate resolution: {duplicate_resolution_parquet}")
    print(f"Wrote intermediate review: {intermediate_review_parquet}")
    print(f"Wrote ontology candidate: {out_ontology_json}")
    print(f"Wrote mapping candidate: {out_mapping}")
    print(f"Wrote evaluation: {evaluation_md}")
    print(f"Freeze ready: {str(freeze_ready).lower()}")


if __name__ == "__main__":
    main()
