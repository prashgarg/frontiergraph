from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

DEFAULT_ONTOLOGY_JSON = DATA_DIR / "ontology_v2_1.json"
DEFAULT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_1.parquet"
DEFAULT_CANONICALIZATION = DATA_DIR / "cross_source_canonicalization_applied_v2_1.csv"
DEFAULT_OUT_ONTOLOGY = DATA_DIR / "ontology_v2_1_canonicalized.json"
DEFAULT_OUT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_1_canonicalized.parquet"
DEFAULT_NOTE = DATA_DIR / "canonicalization_application_note_v2_1.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply conservative cross-source canonicalization remaps to ontology v2.1.")
    parser.add_argument("--ontology-json", default=str(DEFAULT_ONTOLOGY_JSON))
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING))
    parser.add_argument("--canonicalization-csv", default=str(DEFAULT_CANONICALIZATION))
    parser.add_argument("--out-ontology-json", default=str(DEFAULT_OUT_ONTOLOGY))
    parser.add_argument("--out-mapping", default=str(DEFAULT_OUT_MAPPING))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    return parser.parse_args()


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


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
        key = (_clean_str(item.get("source")), _clean_str(item.get("id")), _clean_str(item.get("label")))
        if not any(key):
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({"source": key[0], "id": key[1], "label": key[2]})
    return out


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

    original_id_col = f"canonicalized_from_{prefix}id"
    original_label_col = f"canonicalized_from_{prefix}label"
    original_source_col = f"canonicalized_from_{prefix}source"
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

    original_id_col = f"canonicalized_from_{id_col}"
    original_label_col = f"canonicalized_from_{label_col}"
    original_source_col = f"canonicalized_from_{source_col}" if source_col else ""
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


def main() -> None:
    args = parse_args()
    ontology_path = Path(args.ontology_json)
    mapping_path = Path(args.mapping)
    canonicalization_path = Path(args.canonicalization_csv)
    out_ontology_path = Path(args.out_ontology_json)
    out_mapping_path = Path(args.out_mapping)
    note_path = Path(args.note)

    ontology_rows = json.loads(ontology_path.read_text(encoding="utf-8"))
    mapping = pd.read_parquet(mapping_path)
    canonicalization = pd.read_csv(canonicalization_path)

    member_to_canonical = {
        _clean_str(row.member_id): _clean_str(row.canonical_id)
        for row in canonicalization.itertuples(index=False)
        if _clean_str(row.member_id) and _clean_str(row.canonical_id)
    }
    canonical_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in canonicalization.to_dict(orient="records"):
        canonical_groups[_clean_str(row["canonical_id"])].append(row)

    ontology_by_id = {_clean_str(row["id"]): row for row in ontology_rows}
    consumed_members = set(member_to_canonical)
    out_rows: list[dict[str, Any]] = []
    merge_summary_rows: list[dict[str, Any]] = []

    for row in ontology_rows:
        concept_id = _clean_str(row["id"])
        if concept_id in consumed_members:
            continue
        merged = dict(row)
        if concept_id in canonical_groups:
            aliases = {merged.get("label", "")}
            source_rows = [_record_source(merged)]
            for source_row in merged.get("_sources", []):
                source_rows.append(_record_source(source_row))
                aliases.add(_clean_str(source_row.get("label")))
            member_rows = canonical_groups[concept_id]
            member_ids: list[str] = []
            member_labels: list[str] = []
            member_sources: list[str] = []
            for item in member_rows:
                member_id = _clean_str(item["member_id"])
                member_ids.append(member_id)
                member_labels.append(_clean_str(item["member_label"]))
                member_sources.append(_clean_str(item["member_source"]))
                aliases.add(_clean_str(item["member_label"]))
                member_row = ontology_by_id.get(member_id)
                if member_row is not None:
                    source_rows.append(_record_source(member_row))
                    aliases.add(_clean_str(member_row.get("label")))
                    for source_row in member_row.get("_sources", []):
                        source_rows.append(_record_source(source_row))
                        aliases.add(_clean_str(source_row.get("label")))
            merged["_sources"] = _dedupe_sources(source_rows)
            merged["canonical_member_ids"] = sorted(set(member_ids))
            merged["canonical_member_labels"] = sorted({v for v in member_labels if v})
            merged["canonical_member_sources"] = sorted({v for v in member_sources if v})
            merged["canonical_alias_labels"] = sorted({v for v in aliases if _clean_str(v)})
            merge_summary_rows.append(
                {
                    "canonical_id": concept_id,
                    "canonical_label": _clean_str(merged.get("label")),
                    "canonical_source": _clean_str(merged.get("source")),
                    "member_count": len(member_rows),
                    "member_ids_json": json.dumps(sorted(set(member_ids)), ensure_ascii=False),
                    "member_labels_json": json.dumps(sorted({v for v in member_labels if v}), ensure_ascii=False),
                    "member_sources_json": json.dumps(sorted({v for v in member_sources if v}), ensure_ascii=False),
                }
            )
        out_rows.append(merged)

    lookup = _build_lookup(out_rows)
    mapping = mapping.copy()
    mapping["canonicalization_applied"] = mapping["onto_id"].astype("string").isin(set(member_to_canonical)).astype(int)
    mapping = _remap_concept_columns(mapping, "onto_", member_to_canonical, lookup)
    for prefix in ["rank2_", "rank3_", "sf_best_onto_", "proposed_onto_"]:
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

    out_ontology_path.parent.mkdir(parents=True, exist_ok=True)
    out_mapping_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    out_ontology_path.write_text(json.dumps(out_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    mapping.to_parquet(out_mapping_path, index=False)

    merge_summary = pd.DataFrame(merge_summary_rows).sort_values(
        ["member_count", "canonical_label"], ascending=[False, True]
    ).reset_index(drop=True)
    merge_summary_path = note_path.with_suffix(".parquet")
    merge_summary.to_parquet(merge_summary_path, index=False)

    lines = [
        "# Ontology v2.1 Canonicalization Application",
        "",
        f"- input ontology rows: `{len(ontology_rows):,}`",
        f"- output ontology rows: `{len(out_rows):,}`",
        f"- duplicate merges applied: `{len(canonicalization):,}`",
        f"- canonical concepts touched: `{len(canonical_groups):,}`",
        f"- mapping rows: `{len(mapping):,}`",
        f"- mapping rows with remapped primary concept ids: `{int(mapping['canonicalization_applied'].sum()):,}`",
        "",
        "## Top canonical merges",
        "",
    ]
    for row in merge_summary.head(20).itertuples(index=False):
        members = ", ".join(json.loads(row.member_labels_json)[:5])
        lines.append(
            f"- `{row.canonical_label}` ({row.canonical_source}) absorbed `{int(row.member_count)}` duplicate source records: {members}"
        )
    lines.append("")
    lines.append(f"- merge summary parquet: `{merge_summary_path}`")
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote canonicalized ontology: {out_ontology_path}")
    print(f"Wrote canonicalized mapping: {out_mapping_path}")
    print(f"Wrote canonicalization note: {note_path}")


if __name__ == "__main__":
    main()
