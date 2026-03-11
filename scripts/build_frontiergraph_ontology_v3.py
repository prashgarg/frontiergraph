from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.ontology_v1 import canonical_pair, preferred_label
from src.ontology_v2 import (
    bool_to_int,
    graph_context_similarity,
    lexical_contradiction,
    manual_pair_decision,
    parse_vector,
    safe_margin,
    token_set,
)


DEFAULT_V2_DB = "data/production/frontiergraph_ontology_v2/ontology_v2.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_ontology_v3"
DEFAULT_MANUAL_EMBEDDING_REVIEW_CSV = (
    "data/production/frontiergraph_ontology_v2/review/embedding_review_completed.csv"
)
DEFAULT_ONTOLOGY_VERSION = "v3"


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        parent = self.parent.get(item, item)
        if parent != item:
            parent = self.find(parent)
            self.parent[item] = parent
        return parent

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build FrontierGraph ontology v3 with coverage-based heads and hard/soft mappings."
    )
    parser.add_argument("--v2-db", default=DEFAULT_V2_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manual-embedding-review-csv", default=DEFAULT_MANUAL_EMBEDDING_REVIEW_CSV)
    parser.add_argument("--ontology-version", default=DEFAULT_ONTOLOGY_VERSION)
    parser.add_argument("--embedding-model", default="text-embedding-3-large")
    parser.add_argument("--min-distinct-papers", type=int, default=5)
    parser.add_argument("--min-distinct-journals", type=int, default=1)
    parser.add_argument("--coverage-target", type=float, default=0.90)
    parser.add_argument("--support-only-heads", action="store_true")
    parser.add_argument("--hard-auto-threshold", type=float, default=0.93)
    parser.add_argument("--hard-review-threshold", type=float, default=0.88)
    parser.add_argument("--hard-margin-threshold", type=float, default=0.03)
    parser.add_argument("--hard-graph-threshold", type=float, default=0.45)
    parser.add_argument("--soft-global-batch-size", type=int, default=256)
    parser.add_argument("--export-top-heads", type=int, default=500)
    parser.add_argument("--export-top-soft-audit", type=int, default=200)
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


def load_existing_embeddings(existing_db: Path) -> list[tuple[Any, ...]]:
    if not existing_db.exists():
        return []
    conn = sqlite3.connect(existing_db)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(string_embeddings)").fetchall()]
        if not cols:
            return []
        dim_col = "vector_dim" if "vector_dim" in cols else "dimensions"
        ts_col = "created_at" if "created_at" in cols else "embedded_at"
        select_cols = [
            "normalized_label",
            "embedding_model",
            dim_col,
            "text_used",
            "vector_json",
            ts_col,
        ]
        select_cols.append("shard_id" if "shard_id" in cols else "'' AS shard_id")
        select_cols.append("run_id" if "run_id" in cols else "'' AS run_id")
        return conn.execute(f"SELECT {', '.join(select_cols)} FROM string_embeddings").fetchall()
    finally:
        conn.close()


def init_v3_db(v2_db: Path, v3_db: Path) -> sqlite3.Connection:
    existing_embeddings = load_existing_embeddings(v3_db)
    v3_db.parent.mkdir(parents=True, exist_ok=True)
    if v3_db.exists():
        v3_db.unlink()
    for suffix in ("-shm", "-wal"):
        sidecar = v3_db.with_name(v3_db.name + suffix)
        if sidecar.exists():
            sidecar.unlink()
    shutil.copy2(v2_db, v3_db)
    conn = sqlite3.connect(v3_db)
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE IF NOT EXISTS head_selection_metrics (
            normalized_label TEXT PRIMARY KEY,
            instance_count INTEGER NOT NULL,
            distinct_papers INTEGER NOT NULL,
            distinct_journals INTEGER NOT NULL,
            distinct_partners INTEGER NOT NULL,
            distinct_edge_papers INTEGER NOT NULL,
            head_rank_score REAL NOT NULL,
            cumulative_instance_share REAL NOT NULL,
            selected_head_candidate INTEGER NOT NULL,
            selection_reason TEXT NOT NULL,
            selection_rank INTEGER
        );

        CREATE TABLE IF NOT EXISTS instance_mappings_hard (
            custom_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            normalized_label TEXT NOT NULL,
            concept_id TEXT,
            mapping_source TEXT NOT NULL,
            confidence REAL NOT NULL,
            ontology_version TEXT NOT NULL,
            PRIMARY KEY (custom_id, node_id)
        );

        CREATE TABLE IF NOT EXISTS instance_mappings_soft (
            custom_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            normalized_label TEXT NOT NULL,
            concept_id TEXT,
            mapping_source TEXT NOT NULL,
            confidence REAL NOT NULL,
            ontology_version TEXT NOT NULL,
            PRIMARY KEY (custom_id, node_id)
        );

        CREATE TABLE IF NOT EXISTS tail_soft_candidates (
            normalized_label TEXT NOT NULL,
            candidate_rank INTEGER NOT NULL,
            candidate_concept_id TEXT NOT NULL,
            candidate_preferred_label TEXT NOT NULL,
            cosine_similarity REAL,
            margin REAL,
            graph_context_similarity REAL,
            lexical_contradiction INTEGER NOT NULL,
            candidate_source TEXT NOT NULL,
            decision_status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (normalized_label, candidate_rank)
        );

        CREATE TABLE IF NOT EXISTS soft_map_pending (
            normalized_label TEXT PRIMARY KEY,
            preferred_label TEXT NOT NULL,
            instance_count INTEGER NOT NULL,
            distinct_papers INTEGER NOT NULL,
            has_embedding INTEGER NOT NULL,
            shortlist_candidate_count INTEGER NOT NULL,
            pending_reason TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS context_fingerprints_hard (
            concept_id TEXT NOT NULL,
            context_fingerprint TEXT NOT NULL,
            count_support INTEGER NOT NULL,
            countries_json TEXT NOT NULL,
            unit_of_analysis_json TEXT NOT NULL,
            year_range_json TEXT NOT NULL,
            context_notes_json TEXT NOT NULL,
            PRIMARY KEY (concept_id, context_fingerprint)
        );

        CREATE TABLE IF NOT EXISTS context_fingerprints_soft (
            concept_id TEXT NOT NULL,
            context_fingerprint TEXT NOT NULL,
            count_support INTEGER NOT NULL,
            countries_json TEXT NOT NULL,
            unit_of_analysis_json TEXT NOT NULL,
            year_range_json TEXT NOT NULL,
            context_notes_json TEXT NOT NULL,
            PRIMARY KEY (concept_id, context_fingerprint)
        );
        """
    )
    try:
        conn.execute("ALTER TABLE string_embeddings ADD COLUMN shard_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE string_embeddings ADD COLUMN run_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.executescript(
        """
        DELETE FROM head_concepts;
        DELETE FROM instance_mappings;
        DELETE FROM context_fingerprints;
        DELETE FROM tail_to_head_candidates;
        DELETE FROM embedding_review_queue;
        DELETE FROM head_selection_metrics;
        DELETE FROM instance_mappings_hard;
        DELETE FROM instance_mappings_soft;
        DELETE FROM tail_soft_candidates;
        DELETE FROM soft_map_pending;
        DELETE FROM context_fingerprints_hard;
        DELETE FROM context_fingerprints_soft;
        """
    )
    if existing_embeddings:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(string_embeddings)").fetchall()]
        dim_col = "vector_dim" if "vector_dim" in cols else "dimensions"
        ts_col = "created_at" if "created_at" in cols else "embedded_at"
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO string_embeddings (
                normalized_label, embedding_model, {dim_col}, text_used, vector_json, {ts_col}, shard_id, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            existing_embeddings,
        )
    conn.commit()
    return conn


def load_manual_embedding_accepts(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    accepts: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("manual_decision") == "same_concept":
                accepts[str(row["normalized_label"])] = str(row["candidate_preferred_label"])
    return accepts


def _zscore_dict(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    arr = np.array(list(values.values()), dtype=float)
    mean = float(arr.mean())
    std = float(arr.std())
    if std <= 1e-12:
        return {key: 0.0 for key in values}
    return {key: (float(value) - mean) / std for key, value in values.items()}


def rebuild_head_pool(
    conn: sqlite3.Connection,
    min_distinct_papers: int,
    min_distinct_journals: int,
    coverage_target: float,
    support_only_heads: bool,
) -> tuple[set[str], dict[str, Any]]:
    rows = conn.execute(
        """
        WITH node_edge_stats AS (
            WITH directed AS (
                SELECT source_normalized_label AS label, target_normalized_label AS partner, custom_id
                FROM edge_instances
                UNION ALL
                SELECT target_normalized_label AS label, source_normalized_label AS partner, custom_id
                FROM edge_instances
            )
            SELECT
                label AS normalized_label,
                COUNT(DISTINCT partner) AS distinct_partners,
                COUNT(DISTINCT custom_id) AS distinct_edge_papers
            FROM directed
            GROUP BY label
        )
        SELECT
            ns.normalized_label,
            ns.instance_count,
            ns.distinct_papers,
            ns.distinct_journals,
            COALESCE(es.distinct_partners, 0) AS distinct_partners,
            COALESCE(es.distinct_edge_papers, 0) AS distinct_edge_papers
        FROM node_strings ns
        LEFT JOIN node_edge_stats es
          ON es.normalized_label = ns.normalized_label
        ORDER BY ns.instance_count DESC, ns.normalized_label
        """
    ).fetchall()
    total_instances = sum(int(row[1]) for row in rows)
    coverage_labels: set[str] = set()
    if not support_only_heads:
        cumulative = 0
        for normalized_label, instance_count, _distinct_papers, _distinct_journals, _distinct_partners, _distinct_edge_papers in rows:
            if total_instances and cumulative / total_instances >= coverage_target:
                break
            coverage_labels.add(str(normalized_label))
            cumulative += int(instance_count)
    threshold_labels = {
        str(row[0])
        for row in rows
        if int(row[2]) >= min_distinct_papers and int(row[3]) >= min_distinct_journals
    }
    selected_labels = set(threshold_labels) if support_only_heads else (threshold_labels | coverage_labels)

    candidate_rows = [row for row in rows if str(row[0]) in selected_labels]
    z_support_papers = _zscore_dict({str(row[0]): float(np.log1p(int(row[2]))) for row in candidate_rows})
    z_support_journals = _zscore_dict({str(row[0]): float(np.log1p(int(row[3]))) for row in candidate_rows})
    z_support_instances = _zscore_dict({str(row[0]): float(np.log1p(int(row[1]))) for row in candidate_rows})
    z_reuse_partners = _zscore_dict({str(row[0]): float(np.log1p(int(row[4]))) for row in candidate_rows})
    z_reuse_edge_papers = _zscore_dict({str(row[0]): float(np.log1p(int(row[5]))) for row in candidate_rows})
    head_rank_score = {
        str(row[0]): (
            z_support_papers.get(str(row[0]), 0.0)
            + z_support_journals.get(str(row[0]), 0.0)
            + z_support_instances.get(str(row[0]), 0.0)
            + z_reuse_partners.get(str(row[0]), 0.0)
            + z_reuse_edge_papers.get(str(row[0]), 0.0)
        )
        for row in candidate_rows
    }

    updates = []
    metric_rows = []
    cumulative = 0
    selected_instances = 0
    selection_rank_lookup = {
        label: rank
        for rank, label in enumerate(
            sorted(selected_labels, key=lambda label: (-head_rank_score.get(label, 0.0), label)),
            start=1,
        )
    }
    for normalized_label, instance_count, distinct_papers, distinct_journals, distinct_partners, distinct_edge_papers in rows:
        normalized_label = str(normalized_label)
        instance_count = int(instance_count)
        distinct_papers = int(distinct_papers)
        distinct_journals = int(distinct_journals)
        distinct_partners = int(distinct_partners)
        distinct_edge_papers = int(distinct_edge_papers)
        cumulative += instance_count
        cumulative_share = cumulative / total_instances if total_instances else 0.0
        selected = normalized_label in selected_labels
        if selected:
            selected_instances += instance_count
        if normalized_label in threshold_labels and normalized_label in coverage_labels and not support_only_heads:
            reason = "distinct_papers_and_coverage_mass"
        elif normalized_label in threshold_labels:
            reason = "support_threshold"
        elif normalized_label in coverage_labels and not support_only_heads:
            reason = "coverage_mass"
        else:
            reason = ""
        updates.append((1 if selected else 0, reason, cumulative_share, normalized_label))
        metric_rows.append(
            (
                normalized_label,
                instance_count,
                distinct_papers,
                distinct_journals,
                distinct_partners,
                distinct_edge_papers,
                float(head_rank_score.get(normalized_label, 0.0)),
                cumulative_share,
                1 if selected else 0,
                reason,
                selection_rank_lookup.get(normalized_label),
            )
        )
    conn.executemany(
        "UPDATE node_strings SET in_head_pool = ?, head_pool_reason = ?, cumulative_instance_share = ? WHERE normalized_label = ?",
        updates,
    )
    conn.executemany(
        """
        INSERT INTO head_selection_metrics (
            normalized_label, instance_count, distinct_papers, distinct_journals,
            distinct_partners, distinct_edge_papers, head_rank_score, cumulative_instance_share,
            selected_head_candidate, selection_reason, selection_rank
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        metric_rows,
    )
    conn.commit()
    return selected_labels, {
        "head_candidate_count": len(selected_labels),
        "head_candidate_instance_share": (selected_instances / total_instances) if total_instances else 0.0,
        "coverage_target": coverage_target,
        "threshold_label_count": len(threshold_labels),
        "coverage_label_count": len(coverage_labels),
        "total_node_instances": total_instances,
        "support_only_heads": support_only_heads,
    }


def build_review_constraints(conn: sqlite3.Connection) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[str]]:
    valid_labels = {
        row[0]
        for row in conn.execute("SELECT normalized_label FROM node_strings")
    }
    same_pairs: set[tuple[str, str]] = set()
    different_pairs: set[tuple[str, str]] = set()
    for left_label, right_label, decision in conn.execute(
        """
        SELECT left_normalized_label, right_normalized_label, final_decision
        FROM review_decisions
        WHERE final_decision IN ('same_concept', 'different_concept')
        """
    ).fetchall():
        if left_label not in valid_labels or right_label not in valid_labels:
            continue
        pair = canonical_pair(left_label, right_label)
        if decision == "same_concept":
            same_pairs.add(pair)
        elif decision == "different_concept":
            different_pairs.add(pair)
    isolate_labels = {
        row[0]
        for row in conn.execute(
            "SELECT label FROM manual_overrides WHERE override_kind = 'isolate_label'"
        ).fetchall()
        if row[0]
    }
    blocked_pairs = set(different_pairs)
    blocked_pairs.update(
        canonical_pair(left_label, right_label)
        for left_label, right_label in conn.execute(
            """
            SELECT left_normalized_label, right_normalized_label
            FROM manual_overrides
            WHERE override_kind = 'block_pair'
            """
        ).fetchall()
    )
    return same_pairs, blocked_pairs, isolate_labels


def chunked_label_rows(
    conn: sqlite3.Connection,
    labels: Iterable[str],
    select_columns_sql: str,
    order_by_sql: str | None = None,
    chunk_size: int = 800,
) -> list[tuple[Any, ...]]:
    label_list = sorted(set(labels))
    if not label_list:
        return []
    rows: list[tuple[Any, ...]] = []
    for start in range(0, len(label_list), chunk_size):
        chunk = label_list[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        if " FROM " in select_columns_sql.upper():
            query = f"SELECT {select_columns_sql} WHERE ns.normalized_label IN ({placeholders})"
        else:
            query = f"SELECT {select_columns_sql} FROM node_strings WHERE normalized_label IN ({placeholders})"
        if order_by_sql:
            query += f" ORDER BY {order_by_sql}"
        rows.extend(conn.execute(query, chunk).fetchall())
    return rows


def cluster_head_candidates(
    conn: sqlite3.Connection,
    selected_labels: set[str],
    same_pairs: set[tuple[str, str]],
    blocked_pairs: set[tuple[str, str]],
    isolate_labels: set[str],
    ontology_version: str,
) -> tuple[dict[str, tuple[str, str, float]], dict[str, str], dict[str, Any]]:
    pool_rows = chunked_label_rows(
        conn,
        selected_labels,
        """
        ns.normalized_label, ns.preferred_label, ns.instance_count, ns.distinct_papers,
        COALESCE(hm.head_rank_score, 0.0)
        FROM node_strings ns
        LEFT JOIN head_selection_metrics hm
          ON hm.normalized_label = ns.normalized_label
        """,
    )
    pool_rows.sort(key=lambda row: (-float(row[4]), -int(row[2]), str(row[0])))
    pool_meta = {row[0]: row for row in pool_rows}
    uf = UnionFind()
    for normalized_label, *_rest in pool_rows:
        uf.add(str(normalized_label))

    for left_label, right_label in conn.execute(
        """
        SELECT left_normalized_label, right_normalized_label
        FROM candidate_pairs
        WHERE decision_status = 'accepted_auto'
        """
    ).fetchall():
        if left_label not in selected_labels or right_label not in selected_labels:
            continue
        pair = canonical_pair(left_label, right_label)
        if pair in blocked_pairs or left_label in isolate_labels or right_label in isolate_labels:
            continue
        uf.union(left_label, right_label)

    for left_label, right_label in sorted(same_pairs):
        if left_label not in selected_labels or right_label not in selected_labels:
            continue
        pair = canonical_pair(left_label, right_label)
        if pair in blocked_pairs or left_label in isolate_labels or right_label in isolate_labels:
            continue
        uf.union(left_label, right_label)

    clusters: dict[str, list[str]] = defaultdict(list)
    for label in selected_labels:
        clusters[uf.find(label)].append(label)

    manual_same_pairs = set(same_pairs)
    concept_insert_rows = []
    accepted_label_to_concept: dict[str, tuple[str, str, float]] = {}
    concept_rep_label: dict[str, str] = {}

    cluster_rows: list[dict[str, Any]] = []
    for root, members in clusters.items():
        members_sorted = sorted(members, key=lambda label: (-float(pool_meta[label][4]), -int(pool_meta[label][2]), label))
        aliases = [str(pool_meta[label][1]) for label in members_sorted]
        cluster_rows.append(
            {
                "root": root,
                "members": members_sorted,
                "preferred_label": preferred_label(Counter(aliases)),
                "cluster_size": len(members_sorted),
                "instance_support": sum(int(pool_meta[label][2]) for label in members_sorted),
                "distinct_paper_support": sum(int(pool_meta[label][3]) for label in members_sorted),
                "head_rank_score": max(float(pool_meta[label][4]) for label in members_sorted),
            }
        )
    cluster_rows.sort(key=lambda row: (-float(row["head_rank_score"]), -row["instance_support"], -row["distinct_paper_support"], row["preferred_label"]))

    for rank, row in enumerate(cluster_rows, start=1):
        concept_id = f"FG3C{rank:06d}"
        members = row["members"]
        rep_label = members[0]
        concept_rep_label[concept_id] = rep_label
        review_status = "manual_reviewed_v3" if any(
            canonical_pair(members[0], other) in manual_same_pairs for other in members[1:]
        ) else "deterministic_v3"
        concept_insert_rows.append(
            (
                concept_id,
                row["preferred_label"],
                json.dumps(sorted({str(pool_meta[label][1]) for label in members}), ensure_ascii=False),
                len(members),
                row["cluster_size"],
                row["instance_support"],
                row["distinct_paper_support"],
                "accepted_head",
                review_status,
                json.dumps(members, ensure_ascii=False),
                "[]",
                "[]",
                rank,
                ontology_version,
            )
        )
        for label in members:
            accepted_label_to_concept[label] = (
                concept_id,
                "exact" if label == rep_label else "lexical",
                1.0 if label == rep_label else 0.98,
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
    return accepted_label_to_concept, concept_rep_label, {
        "final_head_count": len(cluster_rows),
        "manual_same_pairs_reused": len(same_pairs),
        "blocked_pairs": len(blocked_pairs),
        "isolated_labels": len(isolate_labels),
    }


def build_signature_maps(conn: sqlite3.Connection, accepted_label_to_concept: dict[str, tuple[str, str, float]]) -> dict[str, dict[str, set[str]]]:
    if not accepted_label_to_concept:
        return {name: defaultdict(set) for name in ("no_paren_signature", "punctuation_signature", "singular_signature", "paren_acronym")}
    rows = chunked_label_rows(
        conn,
        accepted_label_to_concept.keys(),
        "normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym",
    )
    signature_maps: dict[str, dict[str, set[str]]] = {
        "no_paren_signature": defaultdict(set),
        "punctuation_signature": defaultdict(set),
        "singular_signature": defaultdict(set),
        "paren_acronym": defaultdict(set),
    }
    for normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym in rows:
        concept_id, _source, _confidence = accepted_label_to_concept[normalized_label]
        if no_paren_signature:
            signature_maps["no_paren_signature"][no_paren_signature].add(concept_id)
        if punctuation_signature:
            signature_maps["punctuation_signature"][punctuation_signature].add(concept_id)
        if singular_signature:
            signature_maps["singular_signature"][singular_signature].add(concept_id)
        if paren_acronym:
            signature_maps["paren_acronym"][paren_acronym].add(concept_id)
    return signature_maps


def load_node_string_rows(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM node_strings").fetchall()
    return {row["normalized_label"]: row for row in rows}


def build_head_indexes(
    node_string_rows: dict[str, sqlite3.Row],
    labels: list[str],
) -> tuple[dict[str, dict[str, set[str]]], dict[str, set[str]]]:
    signature_indexes: dict[str, dict[str, set[str]]] = {
        "no_paren_signature": defaultdict(set),
        "punctuation_signature": defaultdict(set),
        "singular_signature": defaultdict(set),
        "paren_acronym": defaultdict(set),
        "initialism_signature": defaultdict(set),
    }
    raw_token_to_labels: dict[str, set[str]] = defaultdict(set)
    for label in labels:
        row = node_string_rows.get(label)
        if row is None:
            continue
        for signature_name in signature_indexes:
            value = row[signature_name]
            if value:
                signature_indexes[signature_name][value].add(label)
        for token in token_set(row["preferred_label"]):
            raw_token_to_labels[token].add(label)
    token_to_labels = {token: label_set for token, label_set in raw_token_to_labels.items() if len(label_set) <= 500}
    return signature_indexes, token_to_labels


def top_concepts_from_label_scores(
    candidate_labels: list[str],
    scores: list[float],
    head_label_to_concept_id: dict[str, str],
    concept_id_to_preferred: dict[str, str],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    concept_best: dict[str, dict[str, Any]] = {}
    for label, score in zip(candidate_labels, scores):
        concept_id = head_label_to_concept_id[label]
        current = concept_best.get(concept_id)
        if current is None or score > current["score"]:
            concept_best[concept_id] = {
                "concept_id": concept_id,
                "preferred_label": concept_id_to_preferred[concept_id],
                "best_label": label,
                "score": float(score),
            }
    ranked = sorted(concept_best.values(), key=lambda item: (-item["score"], item["preferred_label"]))
    return ranked[:top_k]


def candidate_shortlist_labels(
    row: sqlite3.Row,
    signature_indexes: dict[str, dict[str, set[str]]],
    token_to_labels: dict[str, set[str]],
) -> set[str]:
    candidates: set[str] = set()
    for signature_name in signature_indexes:
        value = row[signature_name]
        if value:
            candidates.update(signature_indexes[signature_name].get(value, set()))
    for token in token_set(row["preferred_label"]):
        candidates.update(token_to_labels.get(token, set()))
    return candidates


def apply_hard_embedding_tail_mapping(
    conn: sqlite3.Connection,
    node_string_rows: dict[str, sqlite3.Row],
    accepted_label_to_concept: dict[str, tuple[str, str, float]],
    concept_rep_label: dict[str, str],
    embedding_model: str,
    auto_threshold: float,
    review_threshold: float,
    margin_threshold: float,
    graph_threshold: float,
) -> tuple[dict[str, int], dict[str, tuple[str, float]]]:
    head_label_to_concept_id = {label: concept_id for label, (concept_id, _source, _confidence) in accepted_label_to_concept.items()}
    embedded_labels = {
        row[0]
        for row in conn.execute(
            "SELECT normalized_label FROM string_embeddings WHERE embedding_model = ?",
            (embedding_model,),
        ).fetchall()
    }
    embedded_head_labels = [label for label in head_label_to_concept_id if label in embedded_labels]
    if not embedded_head_labels:
        return {"hard_embedding_candidates": 0, "hard_embedding_review_queue": 0, "hard_auto_embedding_labels": 0}, {}

    concept_id_to_preferred = {
        concept_id: preferred_label_value
        for concept_id, preferred_label_value in conn.execute("SELECT concept_id, preferred_label FROM head_concepts").fetchall()
    }
    signature_indexes, token_to_labels = build_head_indexes(node_string_rows, embedded_head_labels)
    head_label_to_index = {label: idx for idx, label in enumerate(embedded_head_labels)}
    head_vectors = np.vstack(
        [
            parse_vector(
                conn.execute(
                    """
                    SELECT vector_json
                    FROM string_embeddings
                    WHERE normalized_label = ? AND embedding_model = ?
                    """,
                    (label, embedding_model),
                ).fetchone()[0]
            )
            for label in embedded_head_labels
        ]
    ).astype(np.float32)
    head_norms = np.linalg.norm(head_vectors, axis=1)
    head_norms[head_norms == 0.0] = 1.0

    candidate_rows = []
    review_rows = []
    auto_maps: dict[str, tuple[str, float]] = {}
    unresolved_rows = sorted(
        [
            row
            for normalized_label, row in node_string_rows.items()
            if normalized_label not in accepted_label_to_concept and normalized_label in embedded_labels
        ],
        key=lambda row: (-int(row["instance_count"]), row["normalized_label"]),
    )
    for unresolved in unresolved_rows:
        shortlist_labels = candidate_shortlist_labels(unresolved, signature_indexes, token_to_labels)
        if not shortlist_labels:
            continue
        candidate_indices = np.asarray(
            sorted(head_label_to_index[label] for label in shortlist_labels if label in head_label_to_index),
            dtype=np.int32,
        )
        if candidate_indices.size == 0:
            continue
        vector_json = conn.execute(
            """
            SELECT vector_json
            FROM string_embeddings
            WHERE normalized_label = ? AND embedding_model = ?
            """,
            (unresolved["normalized_label"], embedding_model),
        ).fetchone()
        if vector_json is None:
            continue
        query_vector = parse_vector(vector_json[0]).astype(np.float32)
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0.0:
            continue
        candidate_vectors = head_vectors[candidate_indices]
        candidate_norms = head_norms[candidate_indices]
        cosine_scores = (candidate_vectors @ query_vector) / (candidate_norms * query_norm)
        cosine_scores = np.nan_to_num(cosine_scores, nan=-1.0, posinf=-1.0, neginf=-1.0)
        ranked_local = np.argsort(cosine_scores)[::-1]
        ranked_labels = [embedded_head_labels[int(candidate_indices[idx])] for idx in ranked_local[:12]]
        ranked_scores = [float(cosine_scores[idx]) for idx in ranked_local[:12]]
        top_concepts = top_concepts_from_label_scores(
            candidate_labels=ranked_labels,
            scores=ranked_scores,
            head_label_to_concept_id=head_label_to_concept_id,
            concept_id_to_preferred=concept_id_to_preferred,
            top_k=3,
        )
        if not top_concepts:
            continue
        top1 = top_concepts[0]
        top2 = top_concepts[1] if len(top_concepts) > 1 else None
        margin = safe_margin(top1["score"], top2["score"] if top2 else None)
        rep_row = node_string_rows[concept_rep_label[top1["concept_id"]]]
        lexical_issue = lexical_contradiction(unresolved["preferred_label"], rep_row["preferred_label"])
        graph_score = graph_context_similarity(dict(unresolved), dict(rep_row))

        if top1["score"] >= auto_threshold and margin >= margin_threshold and not lexical_issue and graph_score >= graph_threshold:
            decision_status = "accepted_auto_embedding"
            auto_maps[unresolved["normalized_label"]] = (top1["concept_id"], top1["score"])
        elif (
            top1["score"] >= review_threshold
            or margin < margin_threshold
        ) and int(unresolved["instance_count"]) >= 7:
            decision_status = "needs_manual_review"
            review_rows.append(
                (
                    unresolved["normalized_label"],
                    top1["concept_id"],
                    top1["preferred_label"],
                    top1["score"],
                    margin,
                    graph_score,
                    bool_to_int(lexical_issue),
                    "needs_manual_review",
                    "v3 hard embedding ambiguity queue",
                )
            )
        else:
            decision_status = "rejected_embedding"

        candidate_rows.append(
            (
                unresolved["normalized_label"],
                top1["concept_id"],
                top1["preferred_label"],
                top1["score"],
                margin,
                graph_score,
                bool_to_int(lexical_issue),
                decision_status,
                "embedding_v3_hard",
                "",
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO tail_to_head_candidates (
            normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity, margin,
            graph_context_similarity, lexical_contradiction, decision_status, decision_source, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        candidate_rows,
    )
    conn.executemany(
        """
        INSERT OR REPLACE INTO embedding_review_queue (
            normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity, margin,
            graph_context_similarity, lexical_contradiction, review_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        review_rows,
    )
    conn.commit()
    return {
        "hard_embedding_candidates": len(candidate_rows),
        "hard_embedding_review_queue": len(review_rows),
        "hard_auto_embedding_labels": len(auto_maps),
    }, auto_maps


def resolve_manual_embedding_maps(
    conn: sqlite3.Connection,
    accepted_preferred_labels: dict[str, str],
) -> dict[str, tuple[str, float]]:
    alias_lookup: dict[str, set[str]] = defaultdict(set)
    for concept_id, preferred_label_value, aliases_json in conn.execute(
        "SELECT concept_id, preferred_label, aliases_json FROM head_concepts"
    ).fetchall():
        alias_lookup[str(preferred_label_value)].add(concept_id)
        for alias in json.loads(aliases_json):
            alias_lookup[str(alias)].add(concept_id)
    manual_maps: dict[str, tuple[str, float]] = {}
    for normalized_label, candidate_preferred in accepted_preferred_labels.items():
        concept_ids = alias_lookup.get(candidate_preferred, set())
        if len(concept_ids) == 1:
            manual_maps[normalized_label] = (next(iter(concept_ids)), 0.96)
    return manual_maps


def build_hard_label_map(
    conn: sqlite3.Connection,
    accepted_label_to_concept: dict[str, tuple[str, str, float]],
    signature_maps: dict[str, dict[str, set[str]]],
    embedding_auto_maps: dict[str, tuple[str, float]],
    manual_embedding_maps: dict[str, tuple[str, float]],
    ontology_version: str,
) -> tuple[dict[str, tuple[str | None, str, float]], dict[str, int]]:
    label_map: dict[str, tuple[str | None, str, float]] = {}
    for row in conn.execute(
        """
        SELECT normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym
        FROM node_strings
        ORDER BY instance_count DESC, normalized_label
        """
    ).fetchall():
        normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym = row
        concept_id: str | None = None
        mapping_source = "unresolved"
        confidence = 0.0
        if normalized_label in accepted_label_to_concept:
            concept_id, mapping_source, confidence = accepted_label_to_concept[normalized_label]
        else:
            candidate_concepts: set[tuple[str, str, float]] = set()
            for signature_type, signature_value, score in (
                ("no_paren_signature", no_paren_signature, 0.90),
                ("paren_acronym", paren_acronym, 0.90),
                ("punctuation_signature", punctuation_signature, 0.86),
                ("singular_signature", singular_signature, 0.84),
            ):
                if not signature_value:
                    continue
                concept_ids = signature_maps[signature_type].get(signature_value, set())
                if len(concept_ids) == 1:
                    candidate_concepts.add((next(iter(concept_ids)), "lexical", score))
            if len(candidate_concepts) == 1:
                concept_id, mapping_source, confidence = next(iter(candidate_concepts))
            elif normalized_label in manual_embedding_maps:
                concept_id, confidence = manual_embedding_maps[normalized_label]
                mapping_source = "manual_embedding"
            elif normalized_label in embedding_auto_maps:
                concept_id, confidence = embedding_auto_maps[normalized_label]
                mapping_source = "embedding"
        label_map[normalized_label] = (concept_id, mapping_source, float(confidence))

    mapping_rows = []
    for custom_id, node_id, normalized_label in conn.execute(
        "SELECT custom_id, node_id, normalized_label FROM node_instances ORDER BY custom_id, node_id"
    ).fetchall():
        concept_id, mapping_source, confidence = label_map[normalized_label]
        mapping_rows.append((custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version))
    conn.executemany(
        """
        INSERT INTO instance_mappings (
            custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        mapping_rows,
    )
    conn.executemany(
        """
        INSERT INTO instance_mappings_hard (
            custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        mapping_rows,
    )
    conn.commit()
    return label_map, {
        "hard_mapped_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings_hard WHERE concept_id IS NOT NULL").fetchone()[0]),
        "hard_unresolved_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings_hard WHERE concept_id IS NULL").fetchone()[0]),
    }


def _top3_global_concepts(
    query_matrix: np.ndarray,
    head_matrix: np.ndarray,
    head_labels: list[str],
    head_label_to_concept_id: dict[str, str],
    concept_id_to_preferred: dict[str, str],
) -> list[list[dict[str, Any]]]:
    scores = query_matrix @ head_matrix.T
    top_label_count = min(12, head_matrix.shape[0])
    if top_label_count <= 0:
        return [[] for _ in range(query_matrix.shape[0])]
    if head_matrix.shape[0] <= top_label_count:
        top_indices = np.argsort(scores, axis=1)[:, ::-1]
    else:
        top_indices = np.argpartition(scores, -top_label_count, axis=1)[:, -top_label_count:]
        row_scores = np.take_along_axis(scores, top_indices, axis=1)
        order = np.argsort(row_scores, axis=1)[:, ::-1]
        top_indices = np.take_along_axis(top_indices, order, axis=1)
    all_results: list[list[dict[str, Any]]] = []
    for row_idx in range(query_matrix.shape[0]):
        labels = [head_labels[int(idx)] for idx in top_indices[row_idx]]
        label_scores = [float(scores[row_idx, int(idx)]) for idx in top_indices[row_idx]]
        all_results.append(
            top_concepts_from_label_scores(
                candidate_labels=labels,
                scores=label_scores,
                head_label_to_concept_id=head_label_to_concept_id,
                concept_id_to_preferred=concept_id_to_preferred,
                top_k=3,
            )
        )
    return all_results


def build_soft_mappings(
    conn: sqlite3.Connection,
    node_string_rows: dict[str, sqlite3.Row],
    accepted_label_to_concept: dict[str, tuple[str, str, float]],
    concept_rep_label: dict[str, str],
    label_map_hard: dict[str, tuple[str | None, str, float]],
    embedding_model: str,
    ontology_version: str,
    global_batch_size: int,
) -> dict[str, int]:
    head_label_to_concept_id = {label: concept_id for label, (concept_id, _source, _confidence) in accepted_label_to_concept.items()}
    concept_id_to_preferred = {
        concept_id: preferred_label_value
        for concept_id, preferred_label_value in conn.execute("SELECT concept_id, preferred_label FROM head_concepts").fetchall()
    }
    embedded_labels = {
        row[0]
        for row in conn.execute(
            "SELECT normalized_label FROM string_embeddings WHERE embedding_model = ?",
            (embedding_model,),
        ).fetchall()
    }
    all_head_labels = sorted(head_label_to_concept_id)
    embedded_head_labels = [label for label in all_head_labels if label in embedded_labels]
    all_signature_indexes, all_token_to_labels = build_head_indexes(node_string_rows, all_head_labels)
    embedded_signature_indexes, embedded_token_to_labels = build_head_indexes(node_string_rows, embedded_head_labels)
    head_label_to_index = {label: idx for idx, label in enumerate(embedded_head_labels)}

    head_vectors = None
    head_norms = None
    if embedded_head_labels:
        head_vectors = np.vstack(
            [
                parse_vector(
                    conn.execute(
                        """
                        SELECT vector_json
                        FROM string_embeddings
                        WHERE normalized_label = ? AND embedding_model = ?
                        """,
                        (label, embedding_model),
                    ).fetchone()[0]
                )
                for label in embedded_head_labels
            ]
        ).astype(np.float32)
        head_norms = np.linalg.norm(head_vectors, axis=1)
        head_norms[head_norms == 0.0] = 1.0
        head_vectors = head_vectors / head_norms[:, None]

    soft_label_map: dict[str, tuple[str | None, str, float]] = {}
    candidate_rows: list[tuple[Any, ...]] = []
    pending_rows: list[tuple[Any, ...]] = []
    fallback_queries: list[tuple[sqlite3.Row, np.ndarray]] = []

    for normalized_label, row in node_string_rows.items():
        hard_concept_id, hard_source, hard_confidence = label_map_hard.get(normalized_label, (None, "unresolved", 0.0))
        if hard_concept_id is not None:
            soft_label_map[normalized_label] = (hard_concept_id, "hard_reuse", hard_confidence)
            continue

        shortlist_all = candidate_shortlist_labels(row, all_signature_indexes, all_token_to_labels)
        shortlist_concepts_all = {head_label_to_concept_id[label] for label in shortlist_all if label in head_label_to_concept_id}
        has_embedding = normalized_label in embedded_labels
        if has_embedding and embedded_head_labels:
            shortlist_embedded = candidate_shortlist_labels(row, embedded_signature_indexes, embedded_token_to_labels)
            if shortlist_embedded:
                vector_json = conn.execute(
                    """
                    SELECT vector_json
                    FROM string_embeddings
                    WHERE normalized_label = ? AND embedding_model = ?
                    """,
                    (normalized_label, embedding_model),
                ).fetchone()
                if vector_json is None:
                    has_embedding = False
                else:
                    query_vector = parse_vector(vector_json[0]).astype(np.float32)
                    query_norm = np.linalg.norm(query_vector)
                    if query_norm == 0.0:
                        has_embedding = False
                    else:
                        query_vector = query_vector / query_norm
                        candidate_indices = np.asarray(
                            sorted(head_label_to_index[label] for label in shortlist_embedded if label in head_label_to_index),
                            dtype=np.int32,
                        )
                        if candidate_indices.size > 0:
                            scores = head_vectors[candidate_indices] @ query_vector
                            ranked_local = np.argsort(scores)[::-1]
                            ranked_labels = [embedded_head_labels[int(candidate_indices[idx])] for idx in ranked_local[:12]]
                            ranked_scores = [float(scores[idx]) for idx in ranked_local[:12]]
                            top_concepts = top_concepts_from_label_scores(
                                candidate_labels=ranked_labels,
                                scores=ranked_scores,
                                head_label_to_concept_id=head_label_to_concept_id,
                                concept_id_to_preferred=concept_id_to_preferred,
                                top_k=3,
                            )
                            if top_concepts:
                                top1 = top_concepts[0]
                                top2 = top_concepts[1] if len(top_concepts) > 1 else None
                                margin = safe_margin(top1["score"], top2["score"] if top2 else None)
                                for rank, candidate in enumerate(top_concepts, start=1):
                                    rep_row = node_string_rows[concept_rep_label[candidate["concept_id"]]]
                                    candidate_rows.append(
                                        (
                                            normalized_label,
                                            rank,
                                            candidate["concept_id"],
                                            candidate["preferred_label"],
                                            candidate["score"],
                                            margin,
                                            graph_context_similarity(dict(row), dict(rep_row)),
                                            bool_to_int(lexical_contradiction(row["preferred_label"], rep_row["preferred_label"])),
                                            "shortlist_embedding",
                                            "selected" if rank == 1 else "alternative",
                                            "",
                                        )
                                    )
                                soft_label_map[normalized_label] = (top1["concept_id"], "soft_shortlist_embedding", top1["score"])
                                continue
            vector_json = conn.execute(
                """
                SELECT vector_json
                FROM string_embeddings
                WHERE normalized_label = ? AND embedding_model = ?
                """,
                (normalized_label, embedding_model),
            ).fetchone()
            if vector_json is not None:
                query_vector = parse_vector(vector_json[0]).astype(np.float32)
                query_norm = np.linalg.norm(query_vector)
                if query_norm > 0.0 and head_vectors is not None:
                    fallback_queries.append((row, query_vector / query_norm))
                    continue

        if shortlist_concepts_all and len(shortlist_concepts_all) == 1:
            concept_id = next(iter(shortlist_concepts_all))
            preferred_label_value = concept_id_to_preferred[concept_id]
            candidate_rows.append(
                (
                    normalized_label,
                    1,
                    concept_id,
                    preferred_label_value,
                    None,
                    None,
                    None,
                    0,
                    "lexical_unique",
                    "selected",
                    "",
                )
            )
            soft_label_map[normalized_label] = (concept_id, "soft_lexical_unique", 0.75)
        else:
            pending_rows.append(
                (
                    normalized_label,
                    row["preferred_label"],
                    int(row["instance_count"]),
                    int(row["distinct_papers"]),
                    bool_to_int(has_embedding),
                    len(shortlist_concepts_all),
                    "no_embedding_no_shortlist"
                    if not shortlist_concepts_all
                    else "no_embedding_ambiguous_shortlist",
                )
            )
            soft_label_map[normalized_label] = (None, "soft_pending", 0.0)

    if fallback_queries and head_vectors is not None:
        for start in range(0, len(fallback_queries), global_batch_size):
            chunk = fallback_queries[start : start + global_batch_size]
            labels = [row["normalized_label"] for row, _vector in chunk]
            query_matrix = np.vstack([vector for _row, vector in chunk]).astype(np.float32)
            top_results = _top3_global_concepts(
                query_matrix=query_matrix,
                head_matrix=head_vectors,
                head_labels=embedded_head_labels,
                head_label_to_concept_id=head_label_to_concept_id,
                concept_id_to_preferred=concept_id_to_preferred,
            )
            for (row, _vector), top_concepts in zip(chunk, top_results):
                if not top_concepts:
                    pending_rows.append(
                        (
                            row["normalized_label"],
                            row["preferred_label"],
                            int(row["instance_count"]),
                            int(row["distinct_papers"]),
                            1,
                            0,
                            "no_global_candidate",
                        )
                    )
                    soft_label_map[row["normalized_label"]] = (None, "soft_pending", 0.0)
                    continue
                top1 = top_concepts[0]
                top2 = top_concepts[1] if len(top_concepts) > 1 else None
                margin = safe_margin(top1["score"], top2["score"] if top2 else None)
                for rank, candidate in enumerate(top_concepts, start=1):
                    rep_row = node_string_rows[concept_rep_label[candidate["concept_id"]]]
                    candidate_rows.append(
                        (
                            row["normalized_label"],
                            rank,
                            candidate["concept_id"],
                            candidate["preferred_label"],
                            candidate["score"],
                            margin,
                            graph_context_similarity(dict(row), dict(rep_row)),
                            bool_to_int(lexical_contradiction(row["preferred_label"], rep_row["preferred_label"])),
                            "global_embedding",
                            "selected" if rank == 1 else "alternative",
                            "",
                        )
                    )
                soft_label_map[row["normalized_label"]] = (top1["concept_id"], "soft_global_embedding", top1["score"])

    conn.executemany(
        """
        INSERT INTO tail_soft_candidates (
            normalized_label, candidate_rank, candidate_concept_id, candidate_preferred_label, cosine_similarity,
            margin, graph_context_similarity, lexical_contradiction, candidate_source, decision_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        candidate_rows,
    )
    conn.executemany(
        """
        INSERT INTO soft_map_pending (
            normalized_label, preferred_label, instance_count, distinct_papers, has_embedding,
            shortlist_candidate_count, pending_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        pending_rows,
    )

    soft_rows = []
    for custom_id, node_id, normalized_label in conn.execute(
        "SELECT custom_id, node_id, normalized_label FROM node_instances ORDER BY custom_id, node_id"
    ).fetchall():
        concept_id, mapping_source, confidence = soft_label_map.get(normalized_label, (None, "soft_pending", 0.0))
        soft_rows.append((custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version))
    conn.executemany(
        """
        INSERT INTO instance_mappings_soft (
            custom_id, node_id, normalized_label, concept_id, mapping_source, confidence, ontology_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        soft_rows,
    )
    conn.commit()
    return {
        "soft_candidate_rows": len(candidate_rows),
        "soft_pending_labels": len(pending_rows),
        "soft_mapped_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings_soft WHERE concept_id IS NOT NULL").fetchone()[0]),
        "soft_unresolved_instances": int(conn.execute("SELECT COUNT(*) FROM instance_mappings_soft WHERE concept_id IS NULL").fetchone()[0]),
    }


def populate_context_fingerprints_for_mapping(
    conn: sqlite3.Connection,
    mapping_table: str,
    output_table: str,
) -> int:
    rows = conn.execute(
        f"""
        SELECT
            m.concept_id,
            n.context_fingerprint,
            COUNT(*) AS count_support,
            n.countries_json,
            n.unit_of_analysis_json,
            n.start_year_json,
            n.end_year_json,
            n.context_note
        FROM {mapping_table} m
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
        f"""
        INSERT INTO {output_table} (
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
                json.dumps({"start_year": json.loads(start_year_json), "end_year": json.loads(end_year_json)}, ensure_ascii=False),
                json.dumps([context_note] if context_note and context_note != "NA" else [], ensure_ascii=False),
            )
            for concept_id, fingerprint, count_support, countries_json, unit_json, start_year_json, end_year_json, context_note in rows
        ],
    )
    conn.commit()
    return len(rows)


def export_v3_artifacts(conn: sqlite3.Connection, output_root: Path, export_top_heads: int, export_top_soft_audit: int) -> None:
    exports_dir = output_root / "exports"
    review_dir = output_root / "review"
    exports_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    head_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT concept_id, preferred_label, instance_support, distinct_paper_support, aliases_count,
                   review_status, cluster_member_labels_json, selection_rank
            FROM head_concepts
            ORDER BY selection_rank ASC, concept_id
            LIMIT ?
            """,
            (export_top_heads,),
        ).fetchall()
    ]
    if head_rows:
        write_csv(exports_dir / "top_head_concepts.csv", head_rows, list(head_rows[0].keys()))

    soft_audit_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT
                sp.normalized_label,
                sp.preferred_label,
                sp.instance_count,
                sp.distinct_papers,
                sc.candidate_concept_id,
                sc.candidate_preferred_label,
                sc.cosine_similarity,
                sc.margin,
                sc.graph_context_similarity,
                sc.lexical_contradiction,
                sc.candidate_source
            FROM soft_map_pending sp
            LEFT JOIN tail_soft_candidates sc
              ON sc.normalized_label = sp.normalized_label
             AND sc.candidate_rank = 1
            ORDER BY sp.instance_count DESC, sp.normalized_label
            LIMIT ?
            """,
            (export_top_soft_audit,),
        ).fetchall()
    ]
    if soft_audit_rows:
        write_csv(review_dir / "manual_soft_audit_sample.csv", soft_audit_rows, list(soft_audit_rows[0].keys()))


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    v3_db = output_root / "ontology_v3.sqlite"
    conn = init_v3_db(Path(args.v2_db), v3_db)

    manual_embedding_accepts = load_manual_embedding_accepts(Path(args.manual_embedding_review_csv))
    selected_labels, head_stats = rebuild_head_pool(
        conn,
        min_distinct_papers=args.min_distinct_papers,
        min_distinct_journals=args.min_distinct_journals,
        coverage_target=args.coverage_target,
        support_only_heads=args.support_only_heads,
    )
    same_pairs, blocked_pairs, isolate_labels = build_review_constraints(conn)
    accepted_label_to_concept, concept_rep_label, cluster_stats = cluster_head_candidates(
        conn=conn,
        selected_labels=selected_labels,
        same_pairs=same_pairs,
        blocked_pairs=blocked_pairs,
        isolate_labels=isolate_labels,
        ontology_version=args.ontology_version,
    )
    signature_maps = build_signature_maps(conn, accepted_label_to_concept)
    node_string_rows = load_node_string_rows(conn)
    hard_embedding_stats, embedding_auto_maps = apply_hard_embedding_tail_mapping(
        conn=conn,
        node_string_rows=node_string_rows,
        accepted_label_to_concept=accepted_label_to_concept,
        concept_rep_label=concept_rep_label,
        embedding_model=args.embedding_model,
        auto_threshold=args.hard_auto_threshold,
        review_threshold=args.hard_review_threshold,
        margin_threshold=args.hard_margin_threshold,
        graph_threshold=args.hard_graph_threshold,
    )
    manual_embedding_maps = resolve_manual_embedding_maps(conn, manual_embedding_accepts)
    label_map_hard, hard_mapping_stats = build_hard_label_map(
        conn=conn,
        accepted_label_to_concept=accepted_label_to_concept,
        signature_maps=signature_maps,
        embedding_auto_maps=embedding_auto_maps,
        manual_embedding_maps=manual_embedding_maps,
        ontology_version=args.ontology_version,
    )
    context_hard_count = populate_context_fingerprints_for_mapping(conn, "instance_mappings_hard", "context_fingerprints")
    conn.execute(
        """
        INSERT INTO context_fingerprints_hard
        SELECT * FROM context_fingerprints
        """
    )
    conn.commit()
    soft_mapping_stats = build_soft_mappings(
        conn=conn,
        node_string_rows=node_string_rows,
        accepted_label_to_concept=accepted_label_to_concept,
        concept_rep_label=concept_rep_label,
        label_map_hard=label_map_hard,
        embedding_model=args.embedding_model,
        ontology_version=args.ontology_version,
        global_batch_size=args.soft_global_batch_size,
    )
    context_soft_count = populate_context_fingerprints_for_mapping(conn, "instance_mappings_soft", "context_fingerprints_soft")
    export_v3_artifacts(conn, output_root, args.export_top_heads, args.export_top_soft_audit)

    ge2_missing_embeddings = conn.execute(
        """
        SELECT COUNT(*)
        FROM node_strings ns
        LEFT JOIN string_embeddings se
          ON se.normalized_label = ns.normalized_label
         AND se.embedding_model = ?
        WHERE ns.distinct_papers >= 2
          AND se.normalized_label IS NULL
        """,
        (args.embedding_model,),
    ).fetchone()[0]
    selected_missing_embeddings = conn.execute(
        """
        SELECT COUNT(*)
        FROM head_selection_metrics hm
        LEFT JOIN string_embeddings se
          ON se.normalized_label = hm.normalized_label
         AND se.embedding_model = ?
        WHERE hm.selected_head_candidate = 1
          AND se.normalized_label IS NULL
        """,
        (args.embedding_model,),
    ).fetchone()[0]

    manifest = {
        "ontology_version": args.ontology_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_v2_db": args.v2_db,
        "manual_embedding_review_csv": args.manual_embedding_review_csv,
        "counts": {
            "node_instances": int(conn.execute("SELECT COUNT(*) FROM node_instances").fetchone()[0]),
            "node_strings": int(conn.execute("SELECT COUNT(*) FROM node_strings").fetchone()[0]),
            "review_decisions": int(conn.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0]),
            "manual_overrides": int(conn.execute("SELECT COUNT(*) FROM manual_overrides").fetchone()[0]),
            "embedding_rows": int(conn.execute("SELECT COUNT(*) FROM string_embeddings WHERE embedding_model = ?", (args.embedding_model,)).fetchone()[0]),
            **head_stats,
            **cluster_stats,
            **hard_embedding_stats,
            "hard_manual_embedding_labels": len(manual_embedding_maps),
            **hard_mapping_stats,
            **soft_mapping_stats,
            "context_fingerprints_hard": context_hard_count,
            "context_fingerprints_soft": context_soft_count,
            "ge2_missing_embeddings": int(ge2_missing_embeddings),
            "selected_head_missing_embeddings": int(selected_missing_embeddings),
        },
        "parameters": {
            "min_distinct_papers": args.min_distinct_papers,
            "min_distinct_journals": args.min_distinct_journals,
            "coverage_target": args.coverage_target,
            "support_only_heads": args.support_only_heads,
            "embedding_model": args.embedding_model,
            "hard_auto_threshold": args.hard_auto_threshold,
            "hard_review_threshold": args.hard_review_threshold,
            "hard_margin_threshold": args.hard_margin_threshold,
            "hard_graph_threshold": args.hard_graph_threshold,
        },
    }
    write_json(output_root / "manifest.json", manifest)
    conn.close()


if __name__ == "__main__":
    main()
