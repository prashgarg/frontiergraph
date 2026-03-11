from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ontology_v1 import (
    canonical_pair,
    context_fingerprint,
    counter_cosine_similarity,
    jaccard_similarity,
    label_signatures,
    preferred_label,
    sequence_similarity,
    top_items,
)


DEFAULT_INPUT_SQLITE = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_ontology_v1"
DEFAULT_ONTOLOGY_VERSION = "v1"

NORMALIZATION_RULES = [
    ("unicode_nfkc", "Apply Unicode NFKC normalization to labels.", 1, 1),
    ("casefold", "Casefold labels for matching while preserving original surface labels elsewhere.", 2, 1),
    ("dash_normalization", "Normalize em/en/minus variants to ASCII hyphen.", 3, 1),
    ("ampersand_to_and", "Replace ampersands with 'and' before token normalization.", 4, 1),
    ("punctuation_normalization", "Remove or normalize non-alphanumeric punctuation while preserving parentheses for acronym handling.", 5, 1),
    ("parenthetical_acronym_signature", "Use trailing parenthetical acronyms only as auxiliary lexical signatures, not canonical labels.", 6, 1),
    ("conservative_singular_signature", "Use a conservative singularized signature only for candidate generation, not canonical labels.", 7, 1),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FrontierGraph ontology v1 from the merged extraction corpus.")
    parser.add_argument("--input-sqlite", default=DEFAULT_INPUT_SQLITE)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--ontology-version", default=DEFAULT_ONTOLOGY_VERSION)
    parser.add_argument("--target-heads", type=int, default=10000)
    parser.add_argument("--min-distinct-papers", type=int, default=5)
    parser.add_argument("--coverage-target", type=float, default=0.85)
    parser.add_argument("--max-head-pool-labels", type=int, default=25000)
    parser.add_argument("--neighbor-topk", type=int, default=15)
    parser.add_argument("--export-top-heads", type=int, default=500)
    parser.add_argument("--export-top-edges", type=int, default=500)
    parser.add_argument("--progress-every", type=int, default=50000)
    return parser.parse_args()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def json_loads(text: str) -> Any:
    return json.loads(text) if text else []


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE normalization_rules (
            rule_name TEXT PRIMARY KEY,
            rule_description TEXT NOT NULL,
            rule_order INTEGER NOT NULL,
            active INTEGER NOT NULL
        );

        CREATE TABLE reject_labels (
            normalized_label TEXT PRIMARY KEY,
            reject_reason TEXT NOT NULL,
            decision_source TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE node_instances (
            custom_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            label TEXT NOT NULL,
            normalized_label TEXT NOT NULL,
            no_paren_signature TEXT NOT NULL,
            punctuation_signature TEXT NOT NULL,
            singular_signature TEXT NOT NULL,
            paren_acronym TEXT NOT NULL,
            initialism_signature TEXT NOT NULL,
            surface_forms_json TEXT NOT NULL,
            unit_of_analysis_json TEXT NOT NULL,
            start_year_json TEXT NOT NULL,
            end_year_json TEXT NOT NULL,
            countries_json TEXT NOT NULL,
            context_note TEXT NOT NULL,
            context_fingerprint TEXT NOT NULL,
            publication_year INTEGER NOT NULL,
            bucket TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_display_name TEXT NOT NULL,
            PRIMARY KEY (custom_id, node_id)
        );

        CREATE TABLE edge_instances (
            custom_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            source_normalized_label TEXT NOT NULL,
            target_normalized_label TEXT NOT NULL,
            directionality TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            causal_presentation TEXT NOT NULL,
            edge_role TEXT NOT NULL,
            publication_year INTEGER NOT NULL,
            bucket TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_display_name TEXT NOT NULL,
            PRIMARY KEY (custom_id, edge_id)
        );

        CREATE TABLE node_strings (
            normalized_label TEXT PRIMARY KEY,
            preferred_label TEXT NOT NULL,
            no_paren_signature TEXT NOT NULL,
            punctuation_signature TEXT NOT NULL,
            singular_signature TEXT NOT NULL,
            paren_acronym TEXT NOT NULL,
            initialism_signature TEXT NOT NULL,
            instance_count INTEGER NOT NULL,
            distinct_papers INTEGER NOT NULL,
            distinct_journals INTEGER NOT NULL,
            first_year INTEGER NOT NULL,
            last_year INTEGER NOT NULL,
            top_raw_variants_json TEXT NOT NULL DEFAULT '[]',
            top_surface_forms_json TEXT NOT NULL DEFAULT '[]',
            bucket_counts_json TEXT NOT NULL DEFAULT '{}',
            top_units_json TEXT NOT NULL DEFAULT '[]',
            top_countries_json TEXT NOT NULL DEFAULT '[]',
            top_context_notes_json TEXT NOT NULL DEFAULT '[]',
            top_in_neighbors_json TEXT NOT NULL DEFAULT '[]',
            top_out_neighbors_json TEXT NOT NULL DEFAULT '[]',
            relationship_type_profile_json TEXT NOT NULL DEFAULT '{}',
            edge_role_profile_json TEXT NOT NULL DEFAULT '{}',
            bucket_profile_json TEXT NOT NULL DEFAULT '{}',
            in_head_pool INTEGER NOT NULL DEFAULT 0,
            head_pool_reason TEXT NOT NULL DEFAULT '',
            cumulative_instance_share REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE string_embeddings (
            normalized_label TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            text_used TEXT NOT NULL,
            vector_json TEXT NOT NULL,
            embedded_at TEXT NOT NULL,
            PRIMARY KEY (normalized_label, embedding_model)
        );

        CREATE TABLE candidate_pairs (
            left_normalized_label TEXT NOT NULL,
            right_normalized_label TEXT NOT NULL,
            lexical_score REAL NOT NULL,
            signature_overlap_json TEXT NOT NULL,
            embedding_cosine REAL,
            embedding_rank INTEGER,
            neighbor_jaccard REAL NOT NULL,
            relationship_profile_similarity REAL NOT NULL,
            edge_role_profile_similarity REAL NOT NULL,
            country_overlap REAL NOT NULL,
            unit_overlap REAL NOT NULL,
            bucket_profile_similarity REAL NOT NULL,
            combined_score REAL NOT NULL,
            decision_status TEXT NOT NULL,
            decision_source TEXT NOT NULL,
            notes TEXT NOT NULL,
            PRIMARY KEY (left_normalized_label, right_normalized_label)
        );

        CREATE TABLE head_concepts (
            concept_id TEXT PRIMARY KEY,
            preferred_label TEXT NOT NULL,
            aliases_json TEXT NOT NULL,
            aliases_count INTEGER NOT NULL,
            cluster_size INTEGER NOT NULL,
            instance_support INTEGER NOT NULL,
            distinct_paper_support INTEGER NOT NULL,
            head_status TEXT NOT NULL,
            review_status TEXT NOT NULL,
            cluster_member_labels_json TEXT NOT NULL,
            representative_contexts_json TEXT NOT NULL,
            exemplar_papers_json TEXT NOT NULL,
            selection_rank INTEGER NOT NULL,
            ontology_version TEXT NOT NULL
        );

        CREATE TABLE instance_mappings (
            custom_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            normalized_label TEXT NOT NULL,
            concept_id TEXT,
            mapping_source TEXT NOT NULL,
            confidence REAL NOT NULL,
            ontology_version TEXT NOT NULL,
            PRIMARY KEY (custom_id, node_id)
        );

        CREATE TABLE review_decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            left_normalized_label TEXT NOT NULL,
            right_normalized_label TEXT NOT NULL,
            proposed_decision TEXT NOT NULL,
            final_decision TEXT,
            decision_source TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            prompt_version TEXT,
            model TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
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

        CREATE INDEX idx_node_instances_normalized_label ON node_instances(normalized_label);
        CREATE INDEX idx_node_instances_bucket ON node_instances(bucket);
        CREATE INDEX idx_node_instances_year ON node_instances(publication_year);
        CREATE INDEX idx_edge_instances_src ON edge_instances(source_normalized_label);
        CREATE INDEX idx_edge_instances_dst ON edge_instances(target_normalized_label);
        CREATE INDEX idx_instance_mappings_concept ON instance_mappings(concept_id);
        """
    )
    return conn


def copy_node_instances(conn: sqlite3.Connection, input_sqlite: Path, progress_every: int) -> dict[str, int]:
    conn.execute("ATTACH DATABASE ? AS src", (str(input_sqlite),))
    conn.executemany("INSERT INTO normalization_rules(rule_name, rule_description, rule_order, active) VALUES (?, ?, ?, ?)", NORMALIZATION_RULES)

    cursor = conn.execute(
        """
        SELECT
            n.custom_id,
            n.node_id,
            n.label,
            n.surface_forms_json,
            n.unit_of_analysis_json,
            n.start_year_json,
            n.end_year_json,
            n.countries_json,
            n.context_note,
            w.publication_year,
            w.bucket,
            w.source_id,
            w.source_display_name
        FROM src.nodes n
        JOIN src.works w USING (custom_id)
        ORDER BY n.custom_id, n.node_id
        """
    )
    insert_sql = """
        INSERT INTO node_instances (
            custom_id, node_id, label, normalized_label, no_paren_signature, punctuation_signature,
            singular_signature, paren_acronym, initialism_signature, surface_forms_json,
            unit_of_analysis_json, start_year_json, end_year_json, countries_json, context_note,
            context_fingerprint, publication_year, bucket, source_id, source_display_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    batch: list[tuple[Any, ...]] = []
    count = 0
    for row in cursor:
        (
            custom_id,
            node_id,
            label,
            surface_forms_json,
            unit_of_analysis_json,
            start_year_json,
            end_year_json,
            countries_json,
            context_note,
            publication_year,
            bucket,
            source_id,
            source_display_name,
        ) = row
        sig = label_signatures(label)
        batch.append(
            (
                custom_id,
                node_id,
                label,
                sig["normalized_label"],
                sig["no_paren_signature"],
                sig["punctuation_signature"],
                sig["singular_signature"],
                sig["paren_acronym"],
                sig["initialism_signature"],
                surface_forms_json,
                unit_of_analysis_json,
                start_year_json,
                end_year_json,
                countries_json,
                context_note,
                context_fingerprint(
                    countries_json=countries_json,
                    unit_of_analysis_json=unit_of_analysis_json,
                    start_year_json=start_year_json,
                    end_year_json=end_year_json,
                    context_note=context_note,
                ),
                int(publication_year),
                bucket,
                source_id,
                source_display_name,
            )
        )
        count += 1
        if len(batch) >= 5000:
            conn.executemany(insert_sql, batch)
            conn.commit()
            batch.clear()
            if count % progress_every == 0:
                print(json.dumps({"stage": "node_instances", "rows": count}, ensure_ascii=False))
    if batch:
        conn.executemany(insert_sql, batch)
        conn.commit()

    conn.execute(
        """
        INSERT INTO edge_instances (
            custom_id, edge_id, source_node_id, target_node_id, source_normalized_label, target_normalized_label,
            directionality, relationship_type, causal_presentation, edge_role,
            publication_year, bucket, source_id, source_display_name
        )
        SELECT
            e.custom_id,
            e.edge_id,
            e.source_node_id,
            e.target_node_id,
            sn.normalized_label,
            tn.normalized_label,
            e.directionality,
            e.relationship_type,
            e.causal_presentation,
            e.edge_role,
            w.publication_year,
            w.bucket,
            w.source_id,
            w.source_display_name
        FROM src.edges e
        JOIN node_instances sn ON sn.custom_id = e.custom_id AND sn.node_id = e.source_node_id
        JOIN node_instances tn ON tn.custom_id = e.custom_id AND tn.node_id = e.target_node_id
        JOIN src.works w USING (custom_id)
        """
    )
    conn.commit()
    counts = {
        "node_instances": int(conn.execute("SELECT COUNT(*) FROM node_instances").fetchone()[0]),
        "edge_instances": int(conn.execute("SELECT COUNT(*) FROM edge_instances").fetchone()[0]),
    }
    conn.execute("DETACH DATABASE src")
    return counts


def build_node_strings_base(conn: sqlite3.Connection) -> dict[str, int]:
    conn.executescript(
        """
        DROP TABLE IF EXISTS variant_counts;
        DROP TABLE IF EXISTS preferred_variants;
        CREATE TEMP TABLE variant_counts AS
        SELECT normalized_label, label, COUNT(*) AS label_instance_count
        FROM node_instances
        GROUP BY normalized_label, label;

        CREATE TEMP TABLE preferred_variants AS
        SELECT normalized_label, label AS preferred_label
        FROM (
            SELECT
                normalized_label,
                label,
                label_instance_count,
                ROW_NUMBER() OVER (
                    PARTITION BY normalized_label
                    ORDER BY label_instance_count DESC, LENGTH(label), label
                ) AS rn
            FROM variant_counts
        )
        WHERE rn = 1;
        """
    )
    cursor = conn.execute(
        """
        SELECT
            ni.normalized_label,
            pv.preferred_label,
            MIN(ni.no_paren_signature),
            MIN(ni.punctuation_signature),
            MIN(ni.singular_signature),
            MIN(ni.paren_acronym),
            MIN(ni.initialism_signature),
            COUNT(*) AS instance_count,
            COUNT(DISTINCT ni.custom_id) AS distinct_papers,
            COUNT(DISTINCT ni.source_display_name) AS distinct_journals,
            MIN(ni.publication_year) AS first_year,
            MAX(ni.publication_year) AS last_year
        FROM node_instances ni
        JOIN preferred_variants pv USING (normalized_label)
        GROUP BY
            ni.normalized_label,
            pv.preferred_label
        ORDER BY instance_count DESC, ni.normalized_label
        """
    )
    insert_sql = """
        INSERT INTO node_strings (
            normalized_label, preferred_label, no_paren_signature, punctuation_signature, singular_signature,
            paren_acronym, initialism_signature, instance_count, distinct_papers, distinct_journals,
            first_year, last_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = list(cursor.fetchall())
    conn.executemany(insert_sql, rows)
    conn.commit()
    return {
        "node_strings": int(conn.execute("SELECT COUNT(*) FROM node_strings").fetchone()[0]),
    }


def mark_head_pool(
    conn: sqlite3.Connection,
    min_distinct_papers: int,
    coverage_target: float,
    max_head_pool_labels: int,
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT normalized_label, instance_count, distinct_papers
        FROM node_strings
        ORDER BY instance_count DESC, normalized_label
        """
    ).fetchall()
    total_instances = sum(int(row[1]) for row in rows)
    threshold_labels = {str(row[0]) for row in rows if int(row[2]) >= min_distinct_papers}
    threshold_instances = sum(int(row[1]) for row in rows if str(row[0]) in threshold_labels)
    threshold_share = (threshold_instances / total_instances) if total_instances else 0.0

    selected_labels = set(threshold_labels)
    additional_added = 0
    additional_instances = 0

    if len(selected_labels) < max_head_pool_labels and threshold_share < coverage_target:
        for normalized_label, instance_count, _distinct_papers in rows:
            normalized_label = str(normalized_label)
            if normalized_label in selected_labels:
                continue
            if len(selected_labels) >= max_head_pool_labels:
                break
            selected_labels.add(normalized_label)
            additional_added += 1
            additional_instances += int(instance_count)

    cumulative = 0
    updates: list[tuple[int, str, float, str]] = []
    in_pool = 0
    in_pool_instances = 0
    for normalized_label, instance_count, distinct_papers in rows:
        instance_count = int(instance_count)
        normalized_label = str(normalized_label)
        cumulative += instance_count
        cum_share = cumulative / total_instances if total_instances else 0.0
        selected = normalized_label in selected_labels
        if normalized_label in threshold_labels:
            reason = "distinct_papers_threshold"
        elif selected:
            reason = "coverage_mass_capped"
        else:
            reason = ""
        if selected:
            in_pool += 1
            in_pool_instances += instance_count
        updates.append((1 if selected else 0, reason, cum_share, normalized_label))
    conn.executemany(
        "UPDATE node_strings SET in_head_pool = ?, head_pool_reason = ?, cumulative_instance_share = ? WHERE normalized_label = ?",
        updates,
    )
    conn.commit()
    return {
        "head_pool_labels": in_pool,
        "head_pool_instance_coverage": (in_pool_instances / total_instances) if total_instances else 0.0,
        "threshold_head_pool_labels": len(threshold_labels),
        "threshold_head_pool_instance_coverage": threshold_share,
        "additional_coverage_labels": additional_added,
        "additional_coverage_instances": additional_instances,
        "max_head_pool_labels": max_head_pool_labels,
        "total_node_instances": total_instances,
    }


def load_pool_labels(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT normalized_label FROM node_strings WHERE in_head_pool = 1")}


def enrich_pool_summaries(conn: sqlite3.Connection, pool_labels: set[str]) -> None:
    if not pool_labels:
        return
    conn.execute("DROP TABLE IF EXISTS pool_labels")
    conn.execute("CREATE TEMP TABLE pool_labels(normalized_label TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO pool_labels(normalized_label) VALUES (?)", [(label,) for label in sorted(pool_labels)])

    raw_variants: dict[str, Counter[str]] = defaultdict(Counter)
    surface_forms: dict[str, Counter[str]] = defaultdict(Counter)
    units: dict[str, Counter[str]] = defaultdict(Counter)
    countries: dict[str, Counter[str]] = defaultdict(Counter)
    context_notes: dict[str, Counter[str]] = defaultdict(Counter)
    bucket_counts: dict[str, Counter[str]] = defaultdict(Counter)

    cursor = conn.execute(
        """
        SELECT
            normalized_label,
            label,
            surface_forms_json,
            unit_of_analysis_json,
            countries_json,
            context_note,
            bucket
        FROM node_instances
        WHERE normalized_label IN (SELECT normalized_label FROM pool_labels)
        """
    )
    for normalized_label, label, surface_forms_json, unit_json, countries_json, context_note, bucket in cursor:
        raw_variants[normalized_label][label] += 1
        for item in json_loads(surface_forms_json):
            surface_forms[normalized_label][str(item)] += 1
        for item in json_loads(unit_json):
            units[normalized_label][str(item)] += 1
        for item in json_loads(countries_json):
            countries[normalized_label][str(item)] += 1
        if context_note and context_note != "NA":
            context_notes[normalized_label][str(context_note)] += 1
        bucket_counts[normalized_label][str(bucket)] += 1

    out_neighbors: dict[str, Counter[str]] = defaultdict(Counter)
    in_neighbors: dict[str, Counter[str]] = defaultdict(Counter)
    relationship_profiles: dict[str, Counter[str]] = defaultdict(Counter)
    edge_role_profiles: dict[str, Counter[str]] = defaultdict(Counter)
    cursor = conn.execute(
        """
        SELECT
            source_normalized_label,
            target_normalized_label,
            relationship_type,
            edge_role
        FROM edge_instances
        WHERE source_normalized_label IN (SELECT normalized_label FROM pool_labels)
           OR target_normalized_label IN (SELECT normalized_label FROM pool_labels)
        """
    )
    for src_label, dst_label, relationship_type, edge_role in cursor:
        if src_label in pool_labels:
            out_neighbors[src_label][dst_label] += 1
            relationship_profiles[src_label][relationship_type] += 1
            edge_role_profiles[src_label][edge_role] += 1
        if dst_label in pool_labels:
            in_neighbors[dst_label][src_label] += 1
            relationship_profiles[dst_label][relationship_type] += 1
            edge_role_profiles[dst_label][edge_role] += 1

    updates = []
    for label in sorted(pool_labels):
        updates.append(
            (
                json.dumps(top_items(raw_variants[label]), ensure_ascii=False),
                json.dumps(top_items(surface_forms[label]), ensure_ascii=False),
                json.dumps(dict(sorted(bucket_counts[label].items())), ensure_ascii=False),
                json.dumps(top_items(units[label]), ensure_ascii=False),
                json.dumps(top_items(countries[label]), ensure_ascii=False),
                json.dumps(top_items(context_notes[label]), ensure_ascii=False),
                json.dumps(top_items(in_neighbors[label]), ensure_ascii=False),
                json.dumps(top_items(out_neighbors[label]), ensure_ascii=False),
                json.dumps(dict(sorted(relationship_profiles[label].items())), ensure_ascii=False),
                json.dumps(dict(sorted(edge_role_profiles[label].items())), ensure_ascii=False),
                json.dumps(dict(sorted(bucket_counts[label].items())), ensure_ascii=False),
                label,
            )
        )
    conn.executemany(
        """
        UPDATE node_strings
        SET
            top_raw_variants_json = ?,
            top_surface_forms_json = ?,
            bucket_counts_json = ?,
            top_units_json = ?,
            top_countries_json = ?,
            top_context_notes_json = ?,
            top_in_neighbors_json = ?,
            top_out_neighbors_json = ?,
            relationship_type_profile_json = ?,
            edge_role_profile_json = ?,
            bucket_profile_json = ?
        WHERE normalized_label = ?
        """,
        updates,
    )
    conn.commit()


def build_candidate_pairs(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT
            normalized_label,
            preferred_label,
            no_paren_signature,
            punctuation_signature,
            singular_signature,
            paren_acronym,
            initialism_signature,
            instance_count,
            distinct_papers,
            top_in_neighbors_json,
            top_out_neighbors_json,
            relationship_type_profile_json,
            edge_role_profile_json,
            top_countries_json,
            top_units_json,
            bucket_profile_json
        FROM node_strings
        WHERE in_head_pool = 1
        ORDER BY instance_count DESC, normalized_label
        """
    ).fetchall()

    metadata: dict[str, dict[str, Any]] = {}
    signature_groups: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    for row in rows:
        (
            normalized_label,
            preferred_label_value,
            no_paren_signature,
            punctuation_signature_value,
            singular_signature_value,
            paren_acronym,
            initialism_signature_value,
            instance_count,
            distinct_papers,
            top_in_neighbors_json,
            top_out_neighbors_json,
            relationship_profile_json,
            edge_role_profile_json,
            top_countries_json,
            top_units_json,
            bucket_profile_json,
        ) = row
        metadata[normalized_label] = {
            "preferred_label": preferred_label_value,
            "instance_count": int(instance_count),
            "distinct_papers": int(distinct_papers),
            "neighbors": {item["value"] for item in json_loads(top_in_neighbors_json)} | {item["value"] for item in json_loads(top_out_neighbors_json)},
            "relationship_profile": {str(k): int(v) for k, v in json.loads(relationship_profile_json).items()},
            "edge_role_profile": {str(k): int(v) for k, v in json.loads(edge_role_profile_json).items()},
            "countries": {item["value"] for item in json_loads(top_countries_json)},
            "units": {item["value"] for item in json_loads(top_units_json)},
            "bucket_profile": {str(k): int(v) for k, v in json.loads(bucket_profile_json).items()},
        }
        signature_map = {
            "no_paren_signature": no_paren_signature,
            "punctuation_signature": punctuation_signature_value,
            "singular_signature": singular_signature_value,
            "paren_acronym": paren_acronym,
        }
        for signature_type, signature_value in signature_map.items():
            if signature_value and signature_value != normalized_label:
                signature_groups[(signature_type, signature_value)].append((normalized_label, int(instance_count)))

    pair_payloads: dict[tuple[str, str], dict[str, Any]] = {}
    lexical_scores = {
        "no_paren_signature": 0.99,
        "paren_acronym": 0.99,
        "punctuation_signature": 0.95,
        "singular_signature": 0.92,
    }

    for (signature_type, _signature_value), members in signature_groups.items():
        if len(members) < 2:
            continue
        members_sorted = sorted(members, key=lambda item: (-item[1], item[0]))
        anchor = members_sorted[0][0]
        for other, _count in members_sorted[1:]:
            pair = canonical_pair(anchor, other)
            payload = pair_payloads.setdefault(
                pair,
                {
                    "reasons": set(),
                    "lexical_score": 0.0,
                },
            )
            payload["reasons"].add(signature_type)
            payload["lexical_score"] = max(payload["lexical_score"], lexical_scores[signature_type])

    rows_to_insert: list[tuple[Any, ...]] = []
    for left_label, right_label in sorted(pair_payloads):
        meta_left = metadata[left_label]
        meta_right = metadata[right_label]
        reasons = sorted(pair_payloads[(left_label, right_label)]["reasons"])
        lexical_score = float(pair_payloads[(left_label, right_label)]["lexical_score"])
        neighbor_jaccard = jaccard_similarity(meta_left["neighbors"], meta_right["neighbors"])
        relationship_similarity = counter_cosine_similarity(meta_left["relationship_profile"], meta_right["relationship_profile"])
        edge_role_similarity = counter_cosine_similarity(meta_left["edge_role_profile"], meta_right["edge_role_profile"])
        country_overlap = jaccard_similarity(meta_left["countries"], meta_right["countries"])
        unit_overlap = jaccard_similarity(meta_left["units"], meta_right["units"])
        bucket_similarity = counter_cosine_similarity(meta_left["bucket_profile"], meta_right["bucket_profile"])
        lexical_text_similarity = sequence_similarity(left_label, right_label)
        combined_score = (
            0.55 * lexical_score
            + 0.10 * lexical_text_similarity
            + 0.10 * neighbor_jaccard
            + 0.10 * relationship_similarity
            + 0.05 * edge_role_similarity
            + 0.05 * country_overlap
            + 0.05 * max(unit_overlap, bucket_similarity)
        )
        strong_reason = any(reason in {"no_paren_signature", "paren_acronym"} for reason in reasons)
        min_support = min(meta_left["distinct_papers"], meta_right["distinct_papers"])
        graph_support = max(neighbor_jaccard, relationship_similarity, edge_role_similarity, bucket_similarity)
        if strong_reason and (min_support < 20 or graph_support >= 0.05):
            decision_status = "accepted_auto"
            notes = "Strong lexical family and no graph contradiction."
        elif lexical_score >= 0.95 and lexical_text_similarity >= 0.88 and graph_support >= 0.20:
            decision_status = "accepted_auto"
            notes = "Lexical near-match with supportive graph/context similarity."
        elif lexical_score >= 0.90 and lexical_text_similarity >= 0.80 and (
            graph_support >= 0.08 or country_overlap >= 0.20 or unit_overlap >= 0.20
        ):
            decision_status = "needs_llm_review"
            notes = "Plausible merge with non-trivial but insufficient supporting evidence."
        else:
            decision_status = "candidate_only"
            notes = "Lexical candidate retained for audit but not auto-merged."
        rows_to_insert.append(
            (
                left_label,
                right_label,
                lexical_score,
                json.dumps(reasons, ensure_ascii=False),
                None,
                None,
                neighbor_jaccard,
                relationship_similarity,
                edge_role_similarity,
                country_overlap,
                unit_overlap,
                bucket_similarity,
                combined_score,
                decision_status,
                "deterministic_lexical_graph_v1",
                notes,
            )
        )

    conn.executemany(
        """
        INSERT INTO candidate_pairs (
            left_normalized_label, right_normalized_label, lexical_score, signature_overlap_json,
            embedding_cosine, embedding_rank, neighbor_jaccard, relationship_profile_similarity,
            edge_role_profile_similarity, country_overlap, unit_overlap, bucket_profile_similarity,
            combined_score, decision_status, decision_source, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows_to_insert,
    )
    conn.commit()
    return {
        "candidate_pairs": len(rows_to_insert),
        "accepted_auto_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs WHERE decision_status = 'accepted_auto'").fetchone()[0]),
        "needs_llm_review_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs WHERE decision_status = 'needs_llm_review'").fetchone()[0]),
    }


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, value: str) -> None:
        self.parent.setdefault(value, value)

    def find(self, value: str) -> str:
        parent = self.parent.setdefault(value, value)
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def build_heads_and_mappings(conn: sqlite3.Connection, target_heads: int, ontology_version: str) -> dict[str, Any]:
    pool_rows = conn.execute(
        """
        SELECT normalized_label, preferred_label, instance_count, distinct_papers,
               no_paren_signature, punctuation_signature, singular_signature, paren_acronym, initialism_signature
        FROM node_strings
        WHERE in_head_pool = 1
        ORDER BY instance_count DESC, normalized_label
        """
    ).fetchall()
    pool_meta = {row[0]: row for row in pool_rows}
    uf = UnionFind()
    for normalized_label, *_ in pool_rows:
        uf.add(normalized_label)
    for left_label, right_label in conn.execute(
        "SELECT left_normalized_label, right_normalized_label FROM candidate_pairs WHERE decision_status = 'accepted_auto'"
    ):
        uf.union(left_label, right_label)

    clusters: dict[str, list[str]] = defaultdict(list)
    for normalized_label in pool_meta:
        clusters[uf.find(normalized_label)].append(normalized_label)

    cluster_rows: list[dict[str, Any]] = []
    for root, members in clusters.items():
        members_sorted = sorted(members, key=lambda label: (-int(pool_meta[label][2]), label))
        aliases = [pool_meta[label][1] for label in members_sorted]
        preferred = preferred_label(Counter(aliases))
        cluster_rows.append(
            {
                "root": root,
                "members": members_sorted,
                "preferred_label": preferred,
                "cluster_size": len(members_sorted),
                "instance_support": sum(int(pool_meta[label][2]) for label in members_sorted),
                "distinct_paper_support": sum(int(pool_meta[label][3]) for label in members_sorted),
            }
        )
    cluster_rows.sort(key=lambda row: (-row["instance_support"], -row["distinct_paper_support"], row["preferred_label"]))

    accepted_clusters = cluster_rows[:target_heads]
    accepted_root_to_concept: dict[str, str] = {}
    accepted_label_to_concept: dict[str, tuple[str, str, float]] = {}
    for rank, row in enumerate(accepted_clusters, start=1):
        concept_id = f"FGC{rank:06d}"
        accepted_root_to_concept[row["root"]] = concept_id
        preferred_norm = row["members"][0]
        for label in row["members"]:
            mapping_source = "exact" if label == preferred_norm else "lexical"
            confidence = 1.0 if label == preferred_norm else 0.98
            accepted_label_to_concept[label] = (concept_id, mapping_source, confidence)

    signature_maps: dict[str, dict[str, set[str]]] = {
        "no_paren_signature": defaultdict(set),
        "punctuation_signature": defaultdict(set),
        "singular_signature": defaultdict(set),
        "paren_acronym": defaultdict(set),
    }
    for label, row in pool_meta.items():
        if label not in accepted_label_to_concept:
            continue
        concept_id, _, _ = accepted_label_to_concept[label]
        signature_maps["no_paren_signature"][row[4]].add(concept_id)
        signature_maps["punctuation_signature"][row[5]].add(concept_id)
        signature_maps["singular_signature"][row[6]].add(concept_id)
        if row[7]:
            signature_maps["paren_acronym"][row[7]].add(concept_id)

    concept_insert_rows: list[tuple[Any, ...]] = []
    for rank, row in enumerate(accepted_clusters, start=1):
        concept_id = accepted_root_to_concept[row["root"]]
        members = row["members"]
        member_placeholders = ",".join("?" for _ in members)
        rep_contexts = conn.execute(
            f"""
            SELECT countries_json, unit_of_analysis_json, context_note, COUNT(*) AS c
            FROM node_instances
            WHERE normalized_label IN ({member_placeholders})
            GROUP BY countries_json, unit_of_analysis_json, context_note
            ORDER BY c DESC
            LIMIT 5
            """,
            members,
        ).fetchall()
        representative_contexts = [
            {
                "countries": json_loads(countries_json),
                "unit_of_analysis": json_loads(unit_json),
                "context_note": context_note,
                "count": count,
            }
            for countries_json, unit_json, context_note, count in rep_contexts
        ]
        concept_insert_rows.append(
            (
                concept_id,
                row["preferred_label"],
                json.dumps(sorted({pool_meta[label][1] for label in members}), ensure_ascii=False),
                len(members),
                row["cluster_size"],
                row["instance_support"],
                row["distinct_paper_support"],
                "accepted_head",
                "not_reviewed",
                json.dumps(members, ensure_ascii=False),
                json.dumps(representative_contexts, ensure_ascii=False),
                "[]",
                rank,
                ontology_version,
            )
        )
    conn.executemany(
        """
        INSERT INTO head_concepts (
            concept_id, preferred_label, aliases_json, aliases_count, cluster_size, instance_support,
            distinct_paper_support, head_status, review_status, cluster_member_labels_json,
            representative_contexts_json, exemplar_papers_json, selection_rank, ontology_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        concept_insert_rows,
    )
    conn.commit()

    mapping_rows: list[tuple[Any, ...]] = []
    cursor = conn.execute(
        """
        SELECT custom_id, node_id, normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym, initialism_signature
        FROM node_instances
        ORDER BY custom_id, node_id
        """
    )
    for custom_id, node_id, normalized_label, no_paren_signature, punctuation_signature_value, singular_signature_value, paren_acronym, initialism_signature_value in cursor:
        concept_id = None
        mapping_source = "unresolved"
        confidence = 0.0
        if normalized_label in accepted_label_to_concept:
            concept_id, mapping_source, confidence = accepted_label_to_concept[normalized_label]
        else:
            candidate_concepts: set[tuple[str, str, float]] = set()
            for signature_type, signature_value, score in (
                ("no_paren_signature", no_paren_signature, 0.90),
                ("paren_acronym", paren_acronym, 0.90),
                ("punctuation_signature", punctuation_signature_value, 0.86),
                ("singular_signature", singular_signature_value, 0.84),
            ):
                if not signature_value:
                    continue
                concept_ids = signature_maps[signature_type].get(signature_value, set())
                if len(concept_ids) == 1:
                    candidate_concepts.add((next(iter(concept_ids)), "lexical", score))
            if len(candidate_concepts) == 1:
                concept_id, mapping_source, confidence = next(iter(candidate_concepts))
        mapping_rows.append((custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version))
    conn.executemany(
        """
        INSERT INTO instance_mappings (
            custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        mapping_rows,
    )
    conn.commit()

    exemplar_rows = conn.execute(
        """
        WITH ranked AS (
            SELECT
                m.concept_id,
                n.custom_id,
                COUNT(*) AS c,
                ROW_NUMBER() OVER (PARTITION BY m.concept_id ORDER BY COUNT(*) DESC, n.custom_id) AS rn
            FROM instance_mappings m
            JOIN node_instances n ON n.custom_id = m.custom_id AND n.node_id = m.node_id
            WHERE m.concept_id IS NOT NULL
            GROUP BY m.concept_id, n.custom_id
        )
        SELECT concept_id, custom_id, c
        FROM ranked
        WHERE rn <= 3
        ORDER BY concept_id, c DESC, custom_id
        """
    ).fetchall()
    by_concept_exemplars: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for concept_id, custom_id, count in exemplar_rows:
        by_concept_exemplars[concept_id].append({"custom_id": custom_id, "count": count})
    conn.executemany(
        "UPDATE head_concepts SET exemplar_papers_json = ? WHERE concept_id = ?",
        [(json.dumps(by_concept_exemplars.get(concept_id, []), ensure_ascii=False), concept_id) for concept_id, in conn.execute("SELECT concept_id FROM head_concepts")],
    )
    conn.commit()

    return {
        "accepted_heads": len(accepted_clusters),
        "mapped_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings WHERE concept_id IS NOT NULL").fetchone()[0]),
        "unresolved_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings WHERE concept_id IS NULL").fetchone()[0]),
    }


def populate_context_fingerprints(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT
            m.concept_id,
            n.context_fingerprint,
            COUNT(*) AS count_support,
            n.countries_json,
            n.unit_of_analysis_json,
            n.start_year_json,
            n.end_year_json,
            n.context_note
        FROM instance_mappings m
        JOIN node_instances n ON n.custom_id = m.custom_id AND n.node_id = m.node_id
        WHERE m.concept_id IS NOT NULL
        GROUP BY
            m.concept_id,
            n.context_fingerprint,
            n.countries_json,
            n.unit_of_analysis_json,
            n.start_year_json,
            n.end_year_json,
            n.context_note
        """
    ).fetchall()
    conn.executemany(
        """
        INSERT INTO context_fingerprints (
            concept_id, context_fingerprint, count_support, countries_json, unit_of_analysis_json,
            year_range_json, context_notes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                concept_id,
                fingerprint,
                count_support,
                countries_json,
                unit_json,
                json.dumps({"start_year": json_loads(start_year_json), "end_year": json_loads(end_year_json)}, ensure_ascii=False),
                json.dumps([context_note] if context_note and context_note != "NA" else [], ensure_ascii=False),
            )
            for concept_id, fingerprint, count_support, countries_json, unit_json, start_year_json, end_year_json, context_note in rows
        ],
    )
    conn.commit()


def export_review_files(conn: sqlite3.Connection, output_root: Path, export_top_heads: int, export_top_edges: int) -> dict[str, int]:
    exports_dir = output_root / "exports"
    review_dir = output_root / "review"

    head_rows = [
        {
            "concept_id": concept_id,
            "preferred_label": preferred_label_value,
            "instance_support": instance_support,
            "distinct_paper_support": distinct_paper_support,
            "cluster_size": cluster_size,
            "selection_rank": selection_rank,
            "aliases_json": aliases_json,
            "representative_contexts_json": representative_contexts_json,
            "exemplar_papers_json": exemplar_papers_json,
        }
        for concept_id, preferred_label_value, instance_support, distinct_paper_support, cluster_size, selection_rank, aliases_json, representative_contexts_json, exemplar_papers_json in conn.execute(
            """
            SELECT concept_id, preferred_label, instance_support, distinct_paper_support, cluster_size,
                   selection_rank, aliases_json, representative_contexts_json, exemplar_papers_json
            FROM head_concepts
            ORDER BY selection_rank
            LIMIT ?
            """,
            (export_top_heads,),
        )
    ]
    write_csv(
        exports_dir / "top_head_concepts.csv",
        head_rows,
        [
            "concept_id",
            "preferred_label",
            "instance_support",
            "distinct_paper_support",
            "cluster_size",
            "selection_rank",
            "aliases_json",
            "representative_contexts_json",
            "exemplar_papers_json",
        ],
    )

    edge_rows = [
        {
            "source_concept_id": source_concept_id,
            "target_concept_id": target_concept_id,
            "edge_count": edge_count,
            "papers": papers,
        }
        for source_concept_id, target_concept_id, edge_count, papers in conn.execute(
            """
            SELECT
                sm.concept_id AS source_concept_id,
                tm.concept_id AS target_concept_id,
                COUNT(*) AS edge_count,
                COUNT(DISTINCT e.custom_id) AS papers
            FROM edge_instances e
            JOIN instance_mappings sm ON sm.custom_id = e.custom_id AND sm.node_id = e.source_node_id
            JOIN instance_mappings tm ON tm.custom_id = e.custom_id AND tm.node_id = e.target_node_id
            WHERE sm.concept_id IS NOT NULL
              AND tm.concept_id IS NOT NULL
              AND sm.concept_id != tm.concept_id
            GROUP BY sm.concept_id, tm.concept_id
            ORDER BY edge_count DESC, papers DESC, sm.concept_id, tm.concept_id
            LIMIT ?
            """,
            (export_top_edges,),
        )
    ]
    write_csv(
        exports_dir / "top_concept_edges.csv",
        edge_rows,
        ["source_concept_id", "target_concept_id", "edge_count", "papers"],
    )

    candidate_review_rows = [
        {
            "left_normalized_label": left,
            "right_normalized_label": right,
            "lexical_score": lexical_score,
            "signature_overlap_json": signature_overlap_json,
            "neighbor_jaccard": neighbor_jaccard,
            "relationship_profile_similarity": relationship_profile_similarity,
            "edge_role_profile_similarity": edge_role_profile_similarity,
            "country_overlap": country_overlap,
            "unit_overlap": unit_overlap,
            "bucket_profile_similarity": bucket_profile_similarity,
            "combined_score": combined_score,
            "decision_status": decision_status,
            "decision_source": decision_source,
            "notes": notes,
            "manual_decision": "",
            "preferred_label_override": "",
            "review_notes": "",
        }
        for (
            left,
            right,
            lexical_score,
            signature_overlap_json,
            neighbor_jaccard,
            relationship_profile_similarity,
            edge_role_profile_similarity,
            country_overlap,
            unit_overlap,
            bucket_profile_similarity,
            combined_score,
            decision_status,
            decision_source,
            notes,
        ) in conn.execute(
            """
            SELECT
                left_normalized_label,
                right_normalized_label,
                lexical_score,
                signature_overlap_json,
                neighbor_jaccard,
                relationship_profile_similarity,
                edge_role_profile_similarity,
                country_overlap,
                unit_overlap,
                bucket_profile_similarity,
                combined_score,
                decision_status,
                decision_source,
                notes
            FROM candidate_pairs
            WHERE decision_status = 'needs_llm_review'
            ORDER BY combined_score DESC, left_normalized_label, right_normalized_label
            """
        )
    ]
    write_csv(
        review_dir / "candidate_pairs_review.csv",
        candidate_review_rows,
        [
            "left_normalized_label",
            "right_normalized_label",
            "lexical_score",
            "signature_overlap_json",
            "neighbor_jaccard",
            "relationship_profile_similarity",
            "edge_role_profile_similarity",
            "country_overlap",
            "unit_overlap",
            "bucket_profile_similarity",
            "combined_score",
            "decision_status",
            "decision_source",
            "notes",
            "manual_decision",
            "preferred_label_override",
            "review_notes",
        ],
    )

    write_csv(
        review_dir / "manual_overrides_template.csv",
        [],
        ["left_normalized_label", "right_normalized_label", "final_decision", "preferred_label_override", "notes"],
    )
    write_csv(
        review_dir / "reject_labels_template.csv",
        [],
        ["normalized_label", "reject_reason", "decision_source", "notes"],
    )
    return {
        "top_head_export_rows": len(head_rows),
        "top_edge_export_rows": len(edge_rows),
        "candidate_review_rows": len(candidate_review_rows),
    }


def build_manifest(conn: sqlite3.Connection, output_root: Path, args: argparse.Namespace, stage_counts: dict[str, Any]) -> dict[str, Any]:
    mapped_instances = int(conn.execute("SELECT COUNT(*) FROM instance_mappings WHERE concept_id IS NOT NULL").fetchone()[0])
    total_instances = int(conn.execute("SELECT COUNT(*) FROM instance_mappings").fetchone()[0])
    summary = {
        "ontology_version": args.ontology_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_sqlite": str(Path(args.input_sqlite)),
        "output_root": str(output_root),
        "counts": {
            "node_instances": int(conn.execute("SELECT COUNT(*) FROM node_instances").fetchone()[0]),
            "edge_instances": int(conn.execute("SELECT COUNT(*) FROM edge_instances").fetchone()[0]),
            "node_strings": int(conn.execute("SELECT COUNT(*) FROM node_strings").fetchone()[0]),
            "head_pool_labels": int(conn.execute("SELECT COUNT(*) FROM node_strings WHERE in_head_pool = 1").fetchone()[0]),
            "candidate_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs").fetchone()[0]),
            "accepted_auto_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs WHERE decision_status = 'accepted_auto'").fetchone()[0]),
            "needs_llm_review_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs WHERE decision_status = 'needs_llm_review'").fetchone()[0]),
            "head_concepts": int(conn.execute("SELECT COUNT(*) FROM head_concepts").fetchone()[0]),
            "mapped_instances": mapped_instances,
            "unresolved_instances": total_instances - mapped_instances,
            "mapped_instance_share": (mapped_instances / total_instances) if total_instances else 0.0,
            "context_fingerprints": int(conn.execute("SELECT COUNT(*) FROM context_fingerprints").fetchone()[0]),
        },
        "parameters": {
            "target_heads": args.target_heads,
            "min_distinct_papers": args.min_distinct_papers,
            "coverage_target": args.coverage_target,
            "max_head_pool_labels": args.max_head_pool_labels,
            "neighbor_topk": args.neighbor_topk,
        },
        "stages": stage_counts,
    }
    write_json(output_root / "manifest.json", summary)
    return summary


def main() -> None:
    args = parse_args()
    input_sqlite = Path(args.input_sqlite)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    db_path = output_root / "ontology_v1.sqlite"
    conn = init_db(db_path)

    stage_counts: dict[str, Any] = {}
    stage_counts["copy"] = copy_node_instances(conn, input_sqlite, args.progress_every)
    print(json.dumps({"stage": "copy_complete", **stage_counts["copy"]}, ensure_ascii=False))
    stage_counts["base"] = build_node_strings_base(conn)
    print(json.dumps({"stage": "node_strings_base_complete", **stage_counts["base"]}, ensure_ascii=False))
    stage_counts["pool"] = mark_head_pool(
        conn,
        args.min_distinct_papers,
        args.coverage_target,
        args.max_head_pool_labels,
    )
    print(json.dumps({"stage": "head_pool_complete", **stage_counts["pool"]}, ensure_ascii=False))
    pool_labels = load_pool_labels(conn)
    enrich_pool_summaries(conn, pool_labels)
    print(json.dumps({"stage": "pool_summaries_complete", "pool_labels": len(pool_labels)}, ensure_ascii=False))
    stage_counts["candidates"] = build_candidate_pairs(conn)
    print(json.dumps({"stage": "candidate_pairs_complete", **stage_counts["candidates"]}, ensure_ascii=False))
    stage_counts["heads"] = build_heads_and_mappings(conn, args.target_heads, args.ontology_version)
    print(json.dumps({"stage": "head_concepts_complete", **stage_counts["heads"]}, ensure_ascii=False))
    populate_context_fingerprints(conn)
    print(json.dumps({"stage": "context_fingerprints_complete"}, ensure_ascii=False))
    stage_counts["exports"] = export_review_files(conn, output_root, args.export_top_heads, args.export_top_edges)
    print(json.dumps({"stage": "exports_complete", **stage_counts["exports"]}, ensure_ascii=False))
    manifest = build_manifest(conn, output_root, args, stage_counts)
    conn.close()
    print(json.dumps(manifest["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
