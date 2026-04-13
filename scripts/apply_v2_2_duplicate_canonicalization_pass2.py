from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

DEFAULT_ONTOLOGY_JSON = DATA_DIR / "ontology_v2_2_hierarchy_enriched.json"
DEFAULT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_2_guardrailed.parquet"
DEFAULT_DUPLICATES = DATA_DIR / "parent_child_reviewed_duplicate_candidates_v2_2.parquet"

DEFAULT_OUT_AUDIT_PARQUET = DATA_DIR / "duplicate_canonicalization_pass2_v2_2.parquet"
DEFAULT_OUT_AUDIT_CSV = DATA_DIR / "duplicate_canonicalization_pass2_v2_2.csv"
DEFAULT_OUT_HOLDOUT = DATA_DIR / "duplicate_canonicalization_pass2_v2_2_holdout.parquet"
DEFAULT_OUT_ONTOLOGY = DATA_DIR / "ontology_v2_2_hierarchy_enriched_canonicalized.json"
DEFAULT_OUT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_2_guardrailed_canonicalized.parquet"
DEFAULT_NOTE = DATA_DIR / "duplicate_canonicalization_pass2_v2_2.md"


SOURCE_PRIORITY = {
    "jel": 0,
    "openalex_topic": 1,
    "openalex_keyword": 2,
    "wikidata": 3,
    "wikipedia": 4,
    "frontiergraph_v2_1_reviewed_family": 5,
    "frontiergraph_v2_2_guardrailed_child_family": 6,
}

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


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def components(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for node in list(self.parent):
            out[self.find(node)].append(node)
        return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply a conservative second canonicalization pass for ontology v2.2 using "
            "reviewed duplicate candidates and remap ontology + mapping artifacts."
        )
    )
    parser.add_argument("--ontology-json", default=str(DEFAULT_ONTOLOGY_JSON))
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING))
    parser.add_argument("--duplicates", default=str(DEFAULT_DUPLICATES))
    parser.add_argument("--out-audit-parquet", default=str(DEFAULT_OUT_AUDIT_PARQUET))
    parser.add_argument("--out-audit-csv", default=str(DEFAULT_OUT_AUDIT_CSV))
    parser.add_argument("--out-holdout", default=str(DEFAULT_OUT_HOLDOUT))
    parser.add_argument("--out-ontology-json", default=str(DEFAULT_OUT_ONTOLOGY))
    parser.add_argument("--out-mapping", default=str(DEFAULT_OUT_MAPPING))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    parser.add_argument(
        "--max-auto-component-size",
        type=int,
        default=2,
        help=(
            "Maximum connected-component size auto-applied in pass2 canonicalization. "
            "Larger components are held out as potentially over-broad."
        ),
    )
    return parser.parse_args()


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _source_rank(source: Any) -> int:
    source_str = str(source or "").strip().lower()
    return SOURCE_PRIORITY.get(source_str, 99)


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(template|portal|category)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(value: Any) -> list[str]:
    return [token for token in _normalize_text(value).split() if token and token not in STOPWORDS]


def _lexical_jaccard(a: Any, b: Any) -> float:
    a_tokens = set(_tokenize(a))
    b_tokens = set(_tokenize(b))
    if not a_tokens or not b_tokens:
        return 0.0
    return float(len(a_tokens & b_tokens) / len(a_tokens | b_tokens))


def _contains_near(a: Any, b: Any) -> bool:
    a_tokens = _tokenize(a)
    b_tokens = _tokenize(b)
    if not a_tokens or not b_tokens:
        return False
    a_text = " ".join(a_tokens)
    b_text = " ".join(b_tokens)
    return (a_text in b_text or b_text in a_text) and abs(len(a_tokens) - len(b_tokens)) <= 1


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
    existing_items: list[str] = []
    if isinstance(existing, list):
        existing_items = [str(v).strip() for v in existing if str(v).strip()]
    merged = sorted(set(existing_items) | {str(v).strip() for v in new_items if str(v).strip()})
    return merged


def _build_lookup(ontology_rows: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for row in ontology_rows:
        rows.append(
            {
                "concept_id": _clean_str(row.get("id")),
                "concept_label": _clean_str(row.get("label")),
                "concept_source": _clean_str(row.get("source")),
                "concept_domain": _clean_str(row.get("domain")),
            }
        )
    return pd.DataFrame(rows).drop_duplicates("concept_id")


def _remap_concept_columns(
    df: pd.DataFrame,
    prefix: str,
    member_to_canonical: dict[str, str],
    lookup: pd.DataFrame,
) -> pd.DataFrame:
    id_col = f"{prefix}id"
    label_col = f"{prefix}label"
    source_col = f"{prefix}source"
    domain_col = f"{prefix}domain"
    if id_col not in df.columns:
        return df

    original_id_col = f"canonicalized_pass2_from_{id_col}"
    original_label_col = f"canonicalized_pass2_from_{label_col}"
    original_source_col = f"canonicalized_pass2_from_{source_col}"
    if original_id_col not in df.columns:
        df[original_id_col] = pd.NA
    if label_col in df.columns and original_label_col not in df.columns:
        df[original_label_col] = pd.NA
    if source_col in df.columns and original_source_col not in df.columns:
        df[original_source_col] = pd.NA

    original_ids = df[id_col].astype("string")
    remapped_ids = original_ids.map(lambda v: member_to_canonical.get(str(v), str(v)) if pd.notna(v) else v)
    changed = original_ids.notna() & remapped_ids.notna() & (original_ids != remapped_ids)
    df.loc[changed, original_id_col] = original_ids[changed]
    if label_col in df.columns:
        df.loc[changed, original_label_col] = df.loc[changed, label_col]
    if source_col in df.columns:
        df.loc[changed, original_source_col] = df.loc[changed, source_col]
    df[id_col] = remapped_ids

    lookup_cols = ["concept_id", "concept_label"]
    if source_col in df.columns:
        lookup_cols.append("concept_source")
    if domain_col in df.columns:
        lookup_cols.append("concept_domain")
    renamed = lookup[lookup_cols].rename(
        columns={
            "concept_id": id_col,
            "concept_label": f"{label_col}__canonical",
            "concept_source": f"{source_col}__canonical",
            "concept_domain": f"{domain_col}__canonical",
        }
    )
    df = df.merge(renamed, on=id_col, how="left")
    if label_col in df.columns:
        replacement = df.pop(f"{label_col}__canonical")
        df[label_col] = replacement.combine_first(df[label_col])
    if source_col in df.columns:
        replacement = df.pop(f"{source_col}__canonical")
        df[source_col] = replacement.combine_first(df[source_col])
    if domain_col in df.columns:
        replacement = df.pop(f"{domain_col}__canonical")
        df[domain_col] = replacement.combine_first(df[domain_col])
    return df


def _remap_explicit_columns(
    df: pd.DataFrame,
    id_col: str,
    label_col: str,
    source_col: str | None,
    domain_col: str | None,
    member_to_canonical: dict[str, str],
    lookup: pd.DataFrame,
) -> pd.DataFrame:
    if id_col not in df.columns:
        return df

    original_id_col = f"canonicalized_pass2_from_{id_col}"
    original_label_col = f"canonicalized_pass2_from_{label_col}"
    original_source_col = f"canonicalized_pass2_from_{source_col}" if source_col else ""
    if original_id_col not in df.columns:
        df[original_id_col] = pd.NA
    if label_col in df.columns and original_label_col not in df.columns:
        df[original_label_col] = pd.NA
    if source_col and source_col in df.columns and original_source_col not in df.columns:
        df[original_source_col] = pd.NA

    original_ids = df[id_col].astype("string")
    remapped_ids = original_ids.map(lambda v: member_to_canonical.get(str(v), str(v)) if pd.notna(v) else v)
    changed = original_ids.notna() & remapped_ids.notna() & (original_ids != remapped_ids)
    df.loc[changed, original_id_col] = original_ids[changed]
    if label_col in df.columns:
        df.loc[changed, original_label_col] = df.loc[changed, label_col]
    if source_col and source_col in df.columns:
        df.loc[changed, original_source_col] = df.loc[changed, source_col]
    df[id_col] = remapped_ids

    lookup_cols = ["concept_id", "concept_label"]
    if source_col and source_col in df.columns:
        lookup_cols.append("concept_source")
    if domain_col and domain_col in df.columns:
        lookup_cols.append("concept_domain")
    renamed = lookup[lookup_cols].rename(
        columns={
            "concept_id": id_col,
            "concept_label": f"{label_col}__canonical",
            "concept_source": f"{source_col}__canonical" if source_col else "concept_source__canonical",
            "concept_domain": f"{domain_col}__canonical" if domain_col else "concept_domain__canonical",
        }
    )
    df = df.merge(renamed, on=id_col, how="left")
    if label_col in df.columns:
        replacement = df.pop(f"{label_col}__canonical")
        df[label_col] = replacement.combine_first(df[label_col])
    if source_col and source_col in df.columns:
        replacement = df.pop(f"{source_col}__canonical")
        df[source_col] = replacement.combine_first(df[source_col])
    if domain_col and domain_col in df.columns:
        replacement = df.pop(f"{domain_col}__canonical")
        df[domain_col] = replacement.combine_first(df[domain_col])
    return df


def _auto_duplicate_decision(row: pd.Series) -> tuple[bool, str]:
    child_label = row.get("child_label", "")
    parent_label = row.get("candidate_parent_label", "")
    channel = str(row.get("candidate_channel", "") or "")
    lexical_jaccard = _lexical_jaccard(child_label, parent_label)
    semantic_cosine = _safe_float(row.get("semantic_cosine"))
    child_norm = _normalize_text(child_label)
    parent_norm = _normalize_text(parent_label)

    if child_norm and parent_norm and child_norm == parent_norm:
        return True, "exact_normalized_label_match"

    if channel == "lexical_ngram_parent":
        if lexical_jaccard >= 0.85:
            return True, "high_lexical_overlap"
        if lexical_jaccard >= 0.60 and _contains_near(child_label, parent_label):
            return True, "near_phrase_match"
        return False, "lexical_overlap_too_weak"

    if channel == "existing_parent_label":
        if lexical_jaccard >= 0.85:
            return True, "existing_parent_high_lexical_overlap"
        return False, "existing_parent_overlap_too_weak"

    if channel in {"jel_code_hierarchy", "openalex_topic_subfield"}:
        if lexical_jaccard >= 0.90:
            return True, "structured_channel_strict_lexical_match"
        return False, "structured_channel_not_lexically_equivalent"

    if channel == "semantic_broader_neighbor":
        if semantic_cosine >= 0.97 and lexical_jaccard >= 0.80:
            return True, "semantic_and_lexical_near_equivalent"
        return False, "semantic_only_duplicate_evidence_too_weak"

    return False, "unsupported_channel_for_auto_merge"


def main() -> None:
    args = parse_args()
    ontology_path = Path(args.ontology_json)
    mapping_path = Path(args.mapping)
    duplicates_path = Path(args.duplicates)
    out_audit_parquet = Path(args.out_audit_parquet)
    out_audit_csv = Path(args.out_audit_csv)
    out_holdout = Path(args.out_holdout)
    out_ontology_json = Path(args.out_ontology_json)
    out_mapping = Path(args.out_mapping)
    note_path = Path(args.note)
    max_component_size = int(args.max_auto_component_size)

    ontology_rows = json.loads(ontology_path.read_text(encoding="utf-8"))
    mapping = pd.read_parquet(mapping_path)
    duplicates = pd.read_parquet(duplicates_path).copy()

    duplicates = duplicates[
        (duplicates["decision"] == "alias_or_duplicate")
        & (duplicates["confidence"].isin(["high", "medium"]))
    ].copy()
    duplicates["child_id"] = duplicates["child_id"].astype(str)
    duplicates["candidate_parent_id"] = duplicates["candidate_parent_id"].astype(str)
    duplicates["lexical_jaccard"] = [
        _lexical_jaccard(a, b) for a, b in zip(duplicates["child_label"], duplicates["candidate_parent_label"])
    ]
    duplicates["semantic_cosine_safe"] = duplicates["semantic_cosine"].map(_safe_float)

    auto_apply: list[bool] = []
    auto_reason: list[str] = []
    for _, row in duplicates.iterrows():
        accepted, reason = _auto_duplicate_decision(row)
        auto_apply.append(bool(accepted))
        auto_reason.append(reason)
    duplicates["auto_apply"] = auto_apply
    duplicates["auto_apply_reason"] = auto_reason
    duplicates["id_pair_valid"] = (
        duplicates["child_id"].astype(str).str.len().gt(0)
        & duplicates["candidate_parent_id"].astype(str).str.len().gt(0)
        & (duplicates["child_id"].astype(str) != duplicates["candidate_parent_id"].astype(str))
    )
    invalid_ids_mask = ~duplicates["id_pair_valid"]
    duplicates.loc[invalid_ids_mask, "auto_apply"] = False
    duplicates.loc[invalid_ids_mask, "auto_apply_reason"] = "invalid_or_missing_concept_id_pair"

    auto_df = duplicates[duplicates["auto_apply"]].copy()
    uf = UnionFind()
    for row in auto_df.itertuples(index=False):
        child_id = str(row.child_id)
        parent_id = str(row.candidate_parent_id)
        if child_id and parent_id and child_id != parent_id:
            uf.union(child_id, parent_id)
    components = uf.components()

    component_size: dict[str, int] = {}
    for root, members in components.items():
        for member in members:
            component_size[member] = len(members)

    duplicates["component_size"] = duplicates["child_id"].map(lambda v: component_size.get(str(v), 1)).astype(int)
    duplicates["component_size"] = duplicates.apply(
        lambda r: max(int(r["component_size"]), component_size.get(str(r["candidate_parent_id"]), 1)),
        axis=1,
    )
    duplicates["component_guardrail_ok"] = duplicates["component_size"] <= max_component_size
    duplicates["applied_in_pass2"] = duplicates["auto_apply"] & duplicates["component_guardrail_ok"]
    duplicates["holdout_reason"] = ""
    duplicates.loc[~duplicates["auto_apply"], "holdout_reason"] = duplicates.loc[
        ~duplicates["auto_apply"], "auto_apply_reason"
    ]
    duplicates.loc[
        duplicates["auto_apply"] & ~duplicates["component_guardrail_ok"],
        "holdout_reason",
    ] = "component_exceeds_max_auto_size"

    applied_pairs = duplicates[duplicates["applied_in_pass2"]][["child_id", "candidate_parent_id"]].drop_duplicates()
    uf_applied = UnionFind()
    for row in applied_pairs.itertuples(index=False):
        if row.child_id and row.candidate_parent_id and row.child_id != row.candidate_parent_id:
            uf_applied.union(str(row.child_id), str(row.candidate_parent_id))
    applied_components = uf_applied.components()

    ontology_by_id = {_clean_str(row.get("id")): row for row in ontology_rows}
    support = (
        mapping.groupby("onto_id", as_index=False)
        .agg(mapped_rows=("label", "size"), mapped_total_freq=("freq", "sum"))
        .rename(columns={"onto_id": "concept_id"})
    )
    support_map = {
        _clean_str(row.concept_id): {
            "mapped_rows": int(row.mapped_rows),
            "mapped_total_freq": float(row.mapped_total_freq),
        }
        for row in support.itertuples(index=False)
    }

    canonical_for_component: dict[str, str] = {}
    member_to_canonical: dict[str, str] = {}
    for root, members in applied_components.items():
        ranked_members = sorted(
            members,
            key=lambda concept_id: (
                -float(support_map.get(concept_id, {}).get("mapped_total_freq", 0.0)),
                -int(support_map.get(concept_id, {}).get("mapped_rows", 0)),
                _source_rank(ontology_by_id.get(concept_id, {}).get("source", "")),
                len(_tokenize(ontology_by_id.get(concept_id, {}).get("label", ""))),
                _clean_str(concept_id),
            ),
        )
        canonical_id = ranked_members[0]
        canonical_for_component[root] = canonical_id
        for concept_id in members:
            if concept_id != canonical_id:
                member_to_canonical[concept_id] = canonical_id

    duplicates["canonical_id"] = ""
    duplicates["canonical_label"] = ""
    duplicates["canonical_source"] = ""

    component_lookup: dict[str, str] = {}
    for root, members in applied_components.items():
        for member in members:
            component_lookup[member] = root

    for idx, row in duplicates.iterrows():
        if not bool(row["applied_in_pass2"]):
            continue
        child_id = str(row["child_id"])
        parent_id = str(row["candidate_parent_id"])
        root = component_lookup.get(child_id) or component_lookup.get(parent_id)
        if not root:
            continue
        canonical_id = canonical_for_component.get(root, "")
        canonical_row = ontology_by_id.get(canonical_id, {})
        duplicates.at[idx, "canonical_id"] = canonical_id
        duplicates.at[idx, "canonical_label"] = _clean_str(canonical_row.get("label"))
        duplicates.at[idx, "canonical_source"] = _clean_str(canonical_row.get("source"))

    canonical_to_members: dict[str, list[str]] = defaultdict(list)
    for member_id, canonical_id in member_to_canonical.items():
        canonical_to_members[canonical_id].append(member_id)

    out_rows: list[dict[str, Any]] = []
    for row in ontology_rows:
        concept_id = _clean_str(row.get("id"))
        if concept_id in member_to_canonical:
            continue

        merged = dict(row)
        source_rows = [_record_source(merged)]
        aliases = {_clean_str(merged.get("label"))}
        member_ids = sorted(set(canonical_to_members.get(concept_id, [])))
        member_labels: list[str] = []
        member_sources: list[str] = []
        for member_id in member_ids:
            member_row = ontology_by_id.get(member_id)
            if not member_row:
                continue
            member_labels.append(_clean_str(member_row.get("label")))
            member_sources.append(_clean_str(member_row.get("source")))
            source_rows.append(_record_source(member_row))
            aliases.add(_clean_str(member_row.get("label")))
            for source_row in member_row.get("_sources", []):
                source_rows.append(_record_source(source_row))
                aliases.add(_clean_str(source_row.get("label")))

        if member_ids:
            merged["_sources"] = _dedupe_sources(source_rows)
            merged["duplicate_pass2_member_ids"] = member_ids
            merged["duplicate_pass2_member_labels"] = sorted({v for v in member_labels if v})
            merged["duplicate_pass2_member_sources"] = sorted({v for v in member_sources if v})
            merged["duplicate_pass2_alias_labels"] = sorted({v for v in aliases if v})
            merged["canonical_member_ids"] = _merge_list_field(merged.get("canonical_member_ids"), member_ids)
            merged["canonical_member_labels"] = _merge_list_field(merged.get("canonical_member_labels"), member_labels)
            merged["canonical_member_sources"] = _merge_list_field(merged.get("canonical_member_sources"), member_sources)
            merged["canonical_alias_labels"] = _merge_list_field(merged.get("canonical_alias_labels"), list(aliases))

        out_rows.append(merged)

    for row in out_rows:
        for id_field in ["effective_parent_id", "effective_root_id"]:
            value = _clean_str(row.get(id_field))
            if not value:
                continue
            row[id_field] = member_to_canonical.get(value, value)

    out_by_id = {_clean_str(row.get("id")): row for row in out_rows}
    for row in out_rows:
        parent_id = _clean_str(row.get("effective_parent_id"))
        if parent_id and parent_id in out_by_id:
            row["effective_parent_label"] = _clean_str(out_by_id[parent_id].get("label"))
        root_id = _clean_str(row.get("effective_root_id"))
        if root_id and root_id in out_by_id:
            row["effective_root_label"] = _clean_str(out_by_id[root_id].get("label"))

    lookup = _build_lookup(out_rows)
    mapping = mapping.copy()
    mapping["canonicalization_pass2_applied"] = mapping["onto_id"].astype("string").isin(set(member_to_canonical)).astype(int)
    for prefix in [
        "onto_",
        "rank2_",
        "rank3_",
        "sf_best_onto_",
        "proposed_onto_",
        "v2_2_parent_onto_",
        "v2_2_original_onto_",
    ]:
        mapping = _remap_concept_columns(mapping, prefix, member_to_canonical, lookup)
    mapping = _remap_explicit_columns(
        mapping,
        id_col="proposed_onto_id_y",
        label_col="proposed_onto_label_y",
        source_col=None,
        domain_col=None,
        member_to_canonical=member_to_canonical,
        lookup=lookup,
    )

    holdout_df = duplicates[~duplicates["applied_in_pass2"]].copy()

    out_audit_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_audit_csv.parent.mkdir(parents=True, exist_ok=True)
    out_holdout.parent.mkdir(parents=True, exist_ok=True)
    out_ontology_json.parent.mkdir(parents=True, exist_ok=True)
    out_mapping.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    duplicates.to_parquet(out_audit_parquet, index=False)
    duplicates.to_csv(out_audit_csv, index=False)
    holdout_df.to_parquet(out_holdout, index=False)
    out_ontology_json.write_text(json.dumps(out_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    mapping.to_parquet(out_mapping, index=False)

    lines = [
        "# Duplicate Canonicalization Pass2 (v2.2)",
        "",
        f"- duplicate candidate rows reviewed: `{len(duplicates):,}`",
        f"- auto-accepted before component guardrail: `{int(duplicates['auto_apply'].sum()):,}`",
        f"- pass2 applied rows after component guardrail: `{int(duplicates['applied_in_pass2'].sum()):,}`",
        f"- rows held out: `{len(holdout_df):,}`",
        f"- max auto component size: `{max_component_size}`",
        f"- merged ontology member concepts: `{len(member_to_canonical):,}`",
        f"- ontology rows before pass2: `{len(ontology_rows):,}`",
        f"- ontology rows after pass2: `{len(out_rows):,}`",
        f"- mapping rows: `{len(mapping):,}`",
        f"- mapping rows with pass2 canonical id remap on primary onto_id: `{int(mapping['canonicalization_pass2_applied'].sum()):,}`",
        "",
        "## Applied Rows by Channel",
        "",
    ]
    applied_channel_counts = duplicates[duplicates["applied_in_pass2"]]["candidate_channel"].value_counts().to_dict()
    for channel, count in applied_channel_counts.items():
        lines.append(f"- `{channel}`: `{int(count):,}`")

    lines.extend(["", "## Holdout Reasons", ""])
    holdout_reason_counts = holdout_df["holdout_reason"].fillna("").replace("", "unspecified_holdout").value_counts().to_dict()
    for reason, count in holdout_reason_counts.items():
        lines.append(f"- `{reason}`: `{int(count):,}`")

    lines.extend(["", "## Top Applied Canonical Concepts", ""])
    applied_pairs_summary = (
        duplicates[duplicates["applied_in_pass2"]]
        .groupby(["canonical_id", "canonical_label", "canonical_source"], as_index=False)
        .agg(applied_rows=("child_id", "size"), unique_members=("child_id", "nunique"))
        .sort_values(["applied_rows", "canonical_label"], ascending=[False, True])
        .head(25)
    )
    if not applied_pairs_summary.empty:
        lines.append(applied_pairs_summary.to_markdown(index=False))
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote pass2 audit parquet: {out_audit_parquet}")
    print(f"Wrote pass2 audit csv: {out_audit_csv}")
    print(f"Wrote pass2 holdout parquet: {out_holdout}")
    print(f"Wrote pass2 ontology json: {out_ontology_json}")
    print(f"Wrote pass2 mapping parquet: {out_mapping}")
    print(f"Wrote pass2 note: {note_path}")


if __name__ == "__main__":
    main()
