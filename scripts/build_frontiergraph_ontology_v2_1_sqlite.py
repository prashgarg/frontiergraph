from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
EXTRACTION_DB = ROOT / "data" / "production" / "frontiergraph_extraction_v2" / "fwci_core150_adj150" / "merged" / "fwci_core150_adj150_extractions.sqlite"

ONTOLOGY_JSON = DATA_DIR / "ontology_v2_1.json"
MAPPING_V2_1 = DATA_DIR / "extraction_label_mapping_v2_1.parquet"
PROMOTED_FAMILIES = DATA_DIR / "ontology_v2_1_promoted_families.parquet"

OUT_DIR = ROOT / "data" / "production" / "frontiergraph_ontology_v2_1"
OUT_DB = OUT_DIR / "ontology_v2_1.sqlite"
NOTE_PATH = DATA_DIR / "ontology_v2_1_sqlite_note.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ontology v2.1 sqlite bundle from ontology + mapping artifacts.")
    parser.add_argument("--ontology-json", default=str(ONTOLOGY_JSON))
    parser.add_argument("--mapping", default=str(MAPPING_V2_1))
    parser.add_argument("--promoted-families", default=str(PROMOTED_FAMILIES))
    parser.add_argument("--extraction-db", default=str(EXTRACTION_DB))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--out-db", default=str(OUT_DB))
    parser.add_argument("--note", default=str(NOTE_PATH))
    parser.add_argument("--mapping-action-column", default="v2_1_mapping_action")
    parser.add_argument(
        "--hierarchy-mode",
        choices=["raw", "effective"],
        default="raw",
        help="Choose whether head_concepts parent/root labels come from raw legacy hierarchy fields or effective reviewed fields.",
    )
    parser.add_argument(
        "--version-label",
        default="v2.1",
        help="Short label used in the output note title for this sqlite materialization run.",
    )
    return parser.parse_args()


def normalize_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower()).strip()


def top_values(series: pd.Series, limit: int = 10) -> list[str]:
    values = [str(v).strip() for v in series if pd.notna(v) and str(v).strip()]
    return [value for value, _ in Counter(values).most_common(limit)]


def resolve_promote_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if str(col).startswith("promote_to_"):
            return str(col)
    return None


def resolve_label_column(df: pd.DataFrame) -> str | None:
    for col in ["family_label", "child_label", "label"]:
        if col in df.columns:
            return str(col)
    return None


def choose_hierarchy_labels(row: dict[str, Any], hierarchy_mode: str) -> tuple[str, str]:
    raw_parent = str(row.get("parent_label", "") or "")
    raw_root = str(row.get("root_label", "") or "")
    effective_parent = str(row.get("effective_parent_label", "") or "")
    effective_root = str(row.get("effective_root_label", "") or "")

    if hierarchy_mode == "effective":
        chosen_parent = effective_parent or raw_parent
        chosen_root = effective_root or raw_root or chosen_parent
        return chosen_parent, chosen_root

    return raw_parent, raw_root


def main() -> None:
    args = parse_args()
    ontology_json = Path(args.ontology_json)
    mapping_path = Path(args.mapping)
    promoted_path = Path(args.promoted_families)
    extraction_db = Path(args.extraction_db)
    out_dir = Path(args.out_dir)
    out_db = Path(args.out_db)
    note_path = Path(args.note)
    mapping_action_col = str(args.mapping_action_column)
    hierarchy_mode = str(args.hierarchy_mode)
    version_label = str(args.version_label)

    out_dir.mkdir(parents=True, exist_ok=True)

    print("[v2.1-sqlite] loading ontology + mapping artifacts", flush=True)
    ontology_rows = json.loads(ontology_json.read_text(encoding="utf-8"))
    mapping = pd.read_parquet(mapping_path)
    promoted = pd.read_parquet(promoted_path)
    promote_col = resolve_promote_column(promoted)
    if promote_col:
        promoted = promoted[promoted[promote_col].fillna(False).astype(bool)].copy()
    else:
        promoted = promoted.iloc[0:0].copy()

    print("[v2.1-sqlite] reading extraction DB tables", flush=True)
    econ = sqlite3.connect(extraction_db)
    try:
        works = pd.read_sql_query(
            """
            SELECT custom_id, publication_year
            FROM works
            """,
            econ,
        )
        nodes = pd.read_sql_query(
            """
            SELECT custom_id, node_id, label, unit_of_analysis_json, countries_json, context_note
            FROM nodes
            """,
            econ,
        )
    finally:
        econ.close()

    print(f"[v2.1-sqlite] works={len(works):,} nodes={len(nodes):,}", flush=True)
    nodes["normalized_label"] = nodes["label"].map(normalize_label)
    label_map = mapping[
        [
            "label",
            "onto_id",
            "onto_label",
            "onto_source",
            "onto_domain",
            "match_kind",
            "matched_via",
            "score",
            mapping_action_col,
        ]
    ].copy()
    label_map = label_map.rename(
        columns={
            "onto_id": "concept_id",
            "onto_label": "concept_label",
            "onto_source": "concept_source",
            "onto_domain": "concept_domain",
            "matched_via": "mapping_source",
            "score": "confidence",
            mapping_action_col: "mapping_action",
        }
    )

    instance_mappings = nodes.merge(label_map, left_on="normalized_label", right_on="label", how="left")
    print(f"[v2.1-sqlite] node-level mappings joined: {len(instance_mappings):,}", flush=True)
    instance_mappings = instance_mappings[
        [
            "custom_id",
            "node_id",
            "normalized_label",
            "concept_id",
            "mapping_source",
            "confidence",
            "mapping_action",
        ]
    ].copy()
    instance_mappings["mapping_source"] = instance_mappings["mapping_source"].fillna("")
    instance_mappings["confidence"] = pd.to_numeric(instance_mappings["confidence"], errors="coerce")
    print(
        f"[v2.1-sqlite] mapped node instances: {int(instance_mappings['concept_id'].notna().sum()):,} / {len(instance_mappings):,}",
        flush=True,
    )

    mapped_nodes = nodes.merge(
        instance_mappings[["custom_id", "node_id", "concept_id"]],
        on=["custom_id", "node_id"],
        how="left",
    )
    mapped_nodes = mapped_nodes.merge(works, on="custom_id", how="left")
    concept_instances = mapped_nodes[mapped_nodes["concept_id"].notna()].copy()
    print(f"[v2.1-sqlite] concept instances with context: {len(concept_instances):,}", flush=True)
    concept_support = (
        concept_instances.groupby("concept_id", as_index=False)
        .agg(
            instance_support=("node_id", "size"),
            distinct_paper_support=("custom_id", "nunique"),
        )
        .set_index("concept_id")
    )
    print(f"[v2.1-sqlite] concept support aggregated: {len(concept_support):,}", flush=True)

    promoted_label_col = resolve_label_column(promoted)
    promoted_alias_map: dict[str, list[str]] = {}
    if promoted_label_col and "aliases_json" in promoted.columns:
        for row in promoted.itertuples(index=False):
            label = str(getattr(row, promoted_label_col, "")).strip()
            if not label:
                continue
            try:
                aliases = json.loads(getattr(row, "aliases_json", "[]"))
            except json.JSONDecodeError:
                aliases = []
            promoted_alias_map[normalize_label(label)] = aliases

    head_rows: list[dict[str, Any]] = []
    for row in ontology_rows:
        concept_id = str(row["id"])
        raw_parent_label = str(row.get("parent_label", "") or "")
        raw_root_label = str(row.get("root_label", "") or "")
        effective_parent_label = str(row.get("effective_parent_label", "") or "")
        effective_root_label = str(row.get("effective_root_label", "") or "")
        parent_label, root_label = choose_hierarchy_labels(row, hierarchy_mode=hierarchy_mode)
        aliases = {str(row.get("label", "")).strip()}
        for source_row in row.get("_sources", []):
            label = str(source_row.get("label", "")).strip()
            if label:
                aliases.add(label)
        promoted_aliases = promoted_alias_map.get(normalize_label(row.get("label")), [])
        aliases.update({str(v).strip() for v in promoted_aliases if str(v).strip()})
        if concept_id in concept_support.index:
            instance_support = int(concept_support.at[concept_id, "instance_support"])
            distinct_paper_support = int(concept_support.at[concept_id, "distinct_paper_support"])
        else:
            instance_support = 0
            distinct_paper_support = 0
        head_rows.append(
            {
                "concept_id": concept_id,
                "preferred_label": str(row.get("display_label", "") or row.get("label", "")),
                "aliases_json": json.dumps(sorted(aliases), ensure_ascii=False),
                "instance_support": instance_support,
                "distinct_paper_support": distinct_paper_support,
                "review_status": "promoted_family" if "family" in str(row.get("source", "")).lower() else "base_ontology",
                "source": str(row.get("source", "")),
                "domain": str(row.get("domain", "")),
                "description": str(row.get("description", "")),
                "parent_label": parent_label,
                "root_label": root_label,
                "raw_parent_label": raw_parent_label,
                "raw_root_label": raw_root_label,
                "effective_parent_label": effective_parent_label,
                "effective_root_label": effective_root_label,
                "hierarchy_mode": hierarchy_mode,
            }
        )
    head_concepts = pd.DataFrame(head_rows)
    print(f"[v2.1-sqlite] head concepts prepared: {len(head_concepts):,}", flush=True)

    context_rows: list[dict[str, Any]] = []
    for concept_id, group in concept_instances.groupby("concept_id", sort=False):
        country_values = top_values(group["countries_json"], limit=5)
        unit_values = top_values(group["unit_of_analysis_json"], limit=5)
        note_values = top_values(group["context_note"], limit=5)
        years = pd.to_numeric(group["publication_year"], errors="coerce").dropna()
        context_rows.append(
            {
                "concept_id": str(concept_id),
                "context_fingerprint": "default",
                "count_support": int(len(group)),
                "countries_json": json.dumps(country_values, ensure_ascii=False),
                "unit_of_analysis_json": json.dumps(unit_values, ensure_ascii=False),
                "year_range_json": json.dumps(
                    {
                        "min_year": int(years.min()) if not years.empty else None,
                        "max_year": int(years.max()) if not years.empty else None,
                    },
                    ensure_ascii=False,
                ),
                "context_notes_json": json.dumps(note_values, ensure_ascii=False),
            }
        )
    context_fingerprints = pd.DataFrame(context_rows)
    print(f"[v2.1-sqlite] context fingerprints prepared: {len(context_fingerprints):,}", flush=True)

    if out_db.exists():
        out_db.unlink()
    conn = sqlite3.connect(out_db)
    try:
        conn.executescript(
            """
            CREATE TABLE head_concepts (
                concept_id TEXT PRIMARY KEY,
                preferred_label TEXT NOT NULL,
                aliases_json TEXT NOT NULL,
                instance_support INTEGER NOT NULL,
                distinct_paper_support INTEGER NOT NULL,
                review_status TEXT NOT NULL,
                source TEXT NOT NULL,
                domain TEXT NOT NULL,
                description TEXT NOT NULL,
                parent_label TEXT NOT NULL,
                root_label TEXT NOT NULL,
                raw_parent_label TEXT NOT NULL,
                raw_root_label TEXT NOT NULL,
                effective_parent_label TEXT NOT NULL,
                effective_root_label TEXT NOT NULL,
                hierarchy_mode TEXT NOT NULL
            );
            CREATE TABLE instance_mappings_soft (
                custom_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                normalized_label TEXT NOT NULL,
                concept_id TEXT,
                mapping_source TEXT NOT NULL,
                confidence REAL,
                PRIMARY KEY (custom_id, node_id)
            );
            CREATE TABLE tail_force_mappings (
                normalized_label TEXT NOT NULL PRIMARY KEY,
                candidate_concept_id TEXT NOT NULL,
                mapping_source TEXT NOT NULL,
                cosine_similarity REAL
            );
            CREATE TABLE context_fingerprints (
                concept_id TEXT NOT NULL,
                context_fingerprint TEXT NOT NULL,
                count_support INTEGER NOT NULL,
                countries_json TEXT NOT NULL,
                unit_of_analysis_json TEXT NOT NULL,
                year_range_json TEXT NOT NULL,
                context_notes_json TEXT NOT NULL,
                PRIMARY KEY (concept_id, context_fingerprint)
            );
            CREATE INDEX idx_instance_mappings_soft_concept_id ON instance_mappings_soft(concept_id);
            CREATE INDEX idx_instance_mappings_soft_label ON instance_mappings_soft(normalized_label);
            CREATE INDEX idx_head_concepts_label ON head_concepts(preferred_label);
            """
        )
        print("[v2.1-sqlite] writing head_concepts", flush=True)
        head_concepts.to_sql("head_concepts", conn, if_exists="append", index=False, chunksize=500, method="multi")
        print("[v2.1-sqlite] writing instance_mappings_soft", flush=True)
        instance_mappings[
            ["custom_id", "node_id", "normalized_label", "concept_id", "mapping_source", "confidence"]
        ].to_sql("instance_mappings_soft", conn, if_exists="append", index=False, chunksize=100, method="multi")
        print("[v2.1-sqlite] writing context_fingerprints", flush=True)
        context_fingerprints.to_sql("context_fingerprints", conn, if_exists="append", index=False, chunksize=100, method="multi")
        conn.commit()
    finally:
        conn.close()

    lines = [
        f"# Ontology {version_label} SQLite Note",
        "",
        f"- hierarchy mode: `{hierarchy_mode}`",
        f"- ontology rows: `{len(ontology_rows):,}`",
        f"- head concepts rows: `{len(head_concepts):,}`",
        f"- node instance mappings: `{len(instance_mappings):,}`",
        f"- mapped node instances: `{int(instance_mappings['concept_id'].notna().sum()):,}`",
        f"- promoted family rows in ontology: `{int((head_concepts['review_status'] == 'promoted_family').sum()):,}`",
        f"- context fingerprints: `{len(context_fingerprints):,}`",
        f"- head concepts with non-empty selected parent label: `{int(head_concepts['parent_label'].astype(str).str.len().gt(0).sum()):,}`",
        f"- head concepts with non-empty selected root label: `{int(head_concepts['root_label'].astype(str).str.len().gt(0).sum()):,}`",
        "",
        "## Mapping action counts",
    ]
    action_counts = (
        nodes.merge(label_map[["label", "mapping_action"]], left_on="normalized_label", right_on="label", how="left")["mapping_action"]
        .fillna("carry_forward_base_mapping")
        .value_counts()
    )
    for action, count in action_counts.items():
        lines.append(f"- `{action}`: `{int(count):,}`")
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote ontology sqlite: {out_db}")
    print(f"Head concepts: {len(head_concepts):,}")
    print(f"Mapped nodes: {int(instance_mappings['concept_id'].notna().sum()):,} / {len(instance_mappings):,}")


if __name__ == "__main__":
    main()
