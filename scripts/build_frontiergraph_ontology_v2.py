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

from src.ontology_v1 import canonical_pair, context_fingerprint, preferred_label, top_items
from src.ontology_v2 import (
    bool_to_int,
    cosine_similarity,
    graph_context_similarity,
    lexical_contradiction,
    manual_pair_decision,
    parse_vector,
    safe_margin,
    select_cluster_preferred_label,
    token_set,
)


DEFAULT_V1_DB = "data/production/frontiergraph_ontology_v1/ontology_v1.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_ontology_v2"
DEFAULT_MANUAL_REVIEW_CSV = "data/production/frontiergraph_ontology_v2/review/candidate_pairs_review_completed.csv"
DEFAULT_MANUAL_NEGATIVE_OVERRIDES = "data/production/frontiergraph_ontology_v2/review/manual_negative_overrides.csv"
DEFAULT_EMBEDDING_REVIEW_CSV = "data/production/frontiergraph_ontology_v2/review/embedding_review_completed.csv"
DEFAULT_ONTOLOGY_VERSION = "v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FrontierGraph ontology v2 from v1 plus manual review and embeddings.")
    parser.add_argument("--v1-db", default=DEFAULT_V1_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manual-review-csv", default=DEFAULT_MANUAL_REVIEW_CSV)
    parser.add_argument("--manual-negative-overrides", default=DEFAULT_MANUAL_NEGATIVE_OVERRIDES)
    parser.add_argument("--embedding-review-csv", default=DEFAULT_EMBEDDING_REVIEW_CSV)
    parser.add_argument("--ontology-version", default=DEFAULT_ONTOLOGY_VERSION)
    parser.add_argument("--target-heads", type=int, default=10000)
    parser.add_argument("--embedding-model", default="text-embedding-3-large")
    parser.add_argument("--auto-embedding-threshold", type=float, default=0.93)
    parser.add_argument("--review-embedding-threshold", type=float, default=0.88)
    parser.add_argument("--embedding-margin-threshold", type=float, default=0.03)
    parser.add_argument("--graph-consistency-threshold", type=float, default=0.45)
    parser.add_argument("--export-top-heads", type=int, default=500)
    parser.add_argument("--export-top-edges", type=int, default=500)
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
        if "shard_id" in cols:
            select_cols.append("shard_id")
        else:
            select_cols.append("'' AS shard_id")
        if "run_id" in cols:
            select_cols.append("run_id")
        else:
            select_cols.append("'' AS run_id")
        sql = f"SELECT {', '.join(select_cols)} FROM string_embeddings"
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def init_v2_db(v1_db: Path, v2_db: Path) -> sqlite3.Connection:
    existing_embeddings = load_existing_embeddings(v2_db)
    v2_db.parent.mkdir(parents=True, exist_ok=True)
    if v2_db.exists():
        v2_db.unlink()
    shm = v2_db.with_name(v2_db.name + "-shm")
    wal = v2_db.with_name(v2_db.name + "-wal")
    if shm.exists():
        shm.unlink()
    if wal.exists():
        wal.unlink()
    shutil.copy2(v1_db, v2_db)
    conn = sqlite3.connect(v2_db)
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE IF NOT EXISTS manual_overrides (
            override_id INTEGER PRIMARY KEY AUTOINCREMENT,
            override_kind TEXT NOT NULL,
            left_normalized_label TEXT NOT NULL DEFAULT '',
            right_normalized_label TEXT NOT NULL DEFAULT '',
            label TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tail_to_head_candidates (
            normalized_label TEXT NOT NULL,
            candidate_concept_id TEXT NOT NULL,
            candidate_preferred_label TEXT NOT NULL,
            cosine_similarity REAL NOT NULL,
            margin REAL NOT NULL,
            graph_context_similarity REAL NOT NULL,
            lexical_contradiction INTEGER NOT NULL,
            decision_status TEXT NOT NULL,
            decision_source TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (normalized_label, candidate_concept_id)
        );

        CREATE TABLE IF NOT EXISTS embedding_review_queue (
            normalized_label TEXT NOT NULL,
            candidate_concept_id TEXT NOT NULL,
            candidate_preferred_label TEXT NOT NULL,
            cosine_similarity REAL NOT NULL,
            margin REAL NOT NULL,
            graph_context_similarity REAL NOT NULL,
            lexical_contradiction INTEGER NOT NULL,
            review_status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (normalized_label, candidate_concept_id)
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
    embedding_cols = [row[1] for row in conn.execute("PRAGMA table_info(string_embeddings)").fetchall()]
    dim_col = "vector_dim" if "vector_dim" in embedding_cols else "dimensions"
    ts_col = "created_at" if "created_at" in embedding_cols else "embedded_at"
    conn.executescript(
        """
        DELETE FROM head_concepts;
        DELETE FROM instance_mappings;
        DELETE FROM context_fingerprints;
        DELETE FROM review_decisions;
        DELETE FROM manual_overrides;
        DELETE FROM tail_to_head_candidates;
        DELETE FROM embedding_review_queue;
        """
    )
    if existing_embeddings:
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


def load_manual_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_manual_overrides(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_optional_review_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ingest_manual_inputs(
    conn: sqlite3.Connection,
    manual_review_rows: list[dict[str, str]],
    manual_overrides: list[dict[str, str]],
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[str]]:
    same_pairs: set[tuple[str, str]] = set()
    different_pairs: set[tuple[str, str]] = set()
    review_decision_rows = []
    now = datetime.now(timezone.utc).isoformat()
    for row in manual_review_rows:
        pair = canonical_pair(row["left_normalized_label"], row["right_normalized_label"])
        decision = row["manual_decision"]
        if decision == "same_concept":
            same_pairs.add(pair)
        elif decision == "different_concept":
            different_pairs.add(pair)
        review_decision_rows.append(
            (
                row["left_normalized_label"],
                row["right_normalized_label"],
                row.get("decision_status", "needs_llm_review"),
                decision,
                "manual_codex_v1",
                json.dumps(
                    {
                        "combined_score": row.get("combined_score"),
                        "lexical_score": row.get("lexical_score"),
                        "neighbor_jaccard": row.get("neighbor_jaccard"),
                        "relationship_profile_similarity": row.get("relationship_profile_similarity"),
                        "edge_role_profile_similarity": row.get("edge_role_profile_similarity"),
                        "country_overlap": row.get("country_overlap"),
                        "unit_overlap": row.get("unit_overlap"),
                        "bucket_profile_similarity": row.get("bucket_profile_similarity"),
                    },
                    ensure_ascii=False,
                ),
                "manual_codex_v1",
                "codex_manual_review",
                row.get("review_notes", ""),
                now,
            )
        )
    conn.executemany(
        """
        INSERT INTO review_decisions (
            left_normalized_label, right_normalized_label, proposed_decision, final_decision,
            decision_source, evidence_json, prompt_version, model, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        review_decision_rows,
    )
    conn.executemany(
        """
        INSERT INTO manual_overrides (
            override_kind, left_normalized_label, right_normalized_label, label, reason
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                row["override_kind"],
                row.get("left_normalized_label", ""),
                row.get("right_normalized_label", ""),
                row.get("label", ""),
                row["reason"],
            )
            for row in manual_overrides
        ],
    )
    conn.commit()

    blocked_pairs = {canonical_pair(row["left_normalized_label"], row["right_normalized_label"]) for row in manual_overrides if row["override_kind"] == "block_pair"}
    blocked_pairs |= different_pairs
    isolate_labels = {row["label"] for row in manual_overrides if row["override_kind"] == "isolate_label" and row["label"]}
    return same_pairs, blocked_pairs, isolate_labels


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


def cluster_head_pool(
    conn: sqlite3.Connection,
    same_pairs: set[tuple[str, str]],
    blocked_pairs: set[tuple[str, str]],
    isolate_labels: set[str],
    target_heads: int,
    ontology_version: str,
) -> tuple[dict[str, tuple[str, str, float]], dict[str, Any]]:
    pool_rows = conn.execute(
        """
        SELECT normalized_label, preferred_label, instance_count, distinct_papers
        FROM node_strings
        WHERE in_head_pool = 1
        ORDER BY instance_count DESC, normalized_label
        """
    ).fetchall()
    pool_meta = {row[0]: row for row in pool_rows}
    uf = UnionFind()
    for normalized_label, *_ in pool_rows:
        uf.add(normalized_label)

    accepted_auto_pairs = conn.execute(
        "SELECT left_normalized_label, right_normalized_label FROM candidate_pairs WHERE decision_status = 'accepted_auto'"
    ).fetchall()

    for left_label, right_label in accepted_auto_pairs:
        pair = canonical_pair(left_label, right_label)
        if pair in blocked_pairs:
            continue
        if left_label in isolate_labels or right_label in isolate_labels:
            continue
        uf.union(left_label, right_label)

    for left_label, right_label in sorted(same_pairs):
        if left_label not in pool_meta or right_label not in pool_meta:
            continue
        if left_label in isolate_labels or right_label in isolate_labels:
            continue
        uf.union(left_label, right_label)

    clusters: dict[str, list[str]] = defaultdict(list)
    for normalized_label in pool_meta:
        clusters[uf.find(normalized_label)].append(normalized_label)

    cluster_rows: list[dict[str, Any]] = []
    for root, members in clusters.items():
        members_sorted = sorted(members, key=lambda label: (-int(pool_meta[label][2]), label))
        aliases = [pool_meta[label][1] for label in members_sorted]
        cluster_rows.append(
            {
                "root": root,
                "members": members_sorted,
                "preferred_label": select_cluster_preferred_label(Counter(aliases)),
                "cluster_size": len(members_sorted),
                "instance_support": sum(int(pool_meta[label][2]) for label in members_sorted),
                "distinct_paper_support": sum(int(pool_meta[label][3]) for label in members_sorted),
            }
        )
    cluster_rows.sort(key=lambda row: (-row["instance_support"], -row["distinct_paper_support"], row["preferred_label"]))
    accepted_clusters = cluster_rows[:target_heads]

    accepted_label_to_concept: dict[str, tuple[str, str, float]] = {}
    concept_insert_rows = []
    for rank, row in enumerate(accepted_clusters, start=1):
        concept_id = f"FGC{rank:06d}"
        members = row["members"]
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
                "manual_reviewed_v2" if any(canonical_pair(members[0], label) in same_pairs for label in members[1:]) else "deterministic_v2",
                json.dumps(members, ensure_ascii=False),
                "[]",
                "[]",
                rank,
                ontology_version,
            )
        )
        preferred_norm = members[0]
        for label in members:
            accepted_label_to_concept[label] = (
                concept_id,
                "exact" if label == preferred_norm else "lexical",
                1.0 if label == preferred_norm else 0.98,
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
    return accepted_label_to_concept, {
        "accepted_heads": len(accepted_clusters),
        "accepted_auto_pairs_kept": len(accepted_auto_pairs) - len([pair for pair in accepted_auto_pairs if canonical_pair(pair[0], pair[1]) in blocked_pairs]),
        "manual_same_pairs": len(same_pairs),
        "blocked_pairs": len(blocked_pairs),
        "isolated_labels": len(isolate_labels),
    }


def build_signature_maps(conn: sqlite3.Connection, accepted_label_to_concept: dict[str, tuple[str, str, float]]) -> dict[str, dict[str, set[str]]]:
    signature_maps: dict[str, dict[str, set[str]]] = {
        "no_paren_signature": defaultdict(set),
        "punctuation_signature": defaultdict(set),
        "singular_signature": defaultdict(set),
        "paren_acronym": defaultdict(set),
    }
    rows = conn.execute(
        """
        SELECT normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym
        FROM node_strings
        WHERE normalized_label IN ({})
        """.format(",".join("?" for _ in accepted_label_to_concept)),
        list(accepted_label_to_concept),
    ).fetchall()
    for normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym in rows:
        concept_id, _, _ = accepted_label_to_concept[normalized_label]
        signature_maps["no_paren_signature"][no_paren_signature].add(concept_id)
        signature_maps["punctuation_signature"][punctuation_signature].add(concept_id)
        signature_maps["singular_signature"][singular_signature].add(concept_id)
        if paren_acronym:
            signature_maps["paren_acronym"][paren_acronym].add(concept_id)
    return signature_maps


def load_node_string_rows(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM node_strings").fetchall()
    return {row["normalized_label"]: row for row in rows}


def apply_embedding_tail_mapping(
    conn: sqlite3.Connection,
    node_string_rows: dict[str, sqlite3.Row],
    accepted_label_to_concept: dict[str, tuple[str, str, float]],
    ontology_version: str,
    embedding_model: str,
    auto_threshold: float,
    review_threshold: float,
    margin_threshold: float,
    graph_consistency_threshold: float,
) -> dict[str, int]:
    head_label_to_concept = {
        label: concept_id for label, (concept_id, _source, _confidence) in accepted_label_to_concept.items()
    }
    embedded_labels = {
        row[0]
        for row in conn.execute(
            """
            SELECT normalized_label
            FROM string_embeddings
            WHERE embedding_model = ?
            """,
            (embedding_model,),
        ).fetchall()
    }
    head_embedding_rows = conn.execute(
        """
        SELECT normalized_label, vector_json
        FROM string_embeddings
        WHERE embedding_model = ?
          AND normalized_label IN ({})
        """.format(",".join("?" for _ in head_label_to_concept)),
        [embedding_model, *head_label_to_concept.keys()],
    ).fetchall()
    if not head_embedding_rows:
        return {"tail_to_head_candidates": 0, "embedding_review_queue": 0, "auto_embedding_mapped_labels": 0}

    head_labels = [row[0] for row in head_embedding_rows]
    head_vectors = np.vstack([parse_vector(row[1]) for row in head_embedding_rows]).astype(np.float32)
    head_norms = np.linalg.norm(head_vectors, axis=1)
    head_norms[head_norms == 0.0] = 1.0
    head_label_to_index = {label: idx for idx, label in enumerate(head_labels)}
    concept_id_to_preferred_label = {
        concept_id: preferred_label
        for concept_id, preferred_label in conn.execute("SELECT concept_id, preferred_label FROM head_concepts").fetchall()
    }

    head_signature_indexes: dict[str, dict[str, set[str]]] = {
        "no_paren_signature": defaultdict(set),
        "punctuation_signature": defaultdict(set),
        "singular_signature": defaultdict(set),
        "paren_acronym": defaultdict(set),
        "initialism_signature": defaultdict(set),
    }
    raw_token_to_heads: dict[str, set[str]] = defaultdict(set)
    for label in head_labels:
        row = node_string_rows.get(label)
        if row is None:
            continue
        for signature_name in head_signature_indexes:
            signature_value = row[signature_name]
            if signature_value:
                head_signature_indexes[signature_name][signature_value].add(label)
        for token in token_set(row["preferred_label"]):
            raw_token_to_heads[token].add(label)

    token_to_heads = {
        token: labels
        for token, labels in raw_token_to_heads.items()
        if len(labels) <= 500
    }

    unresolved_rows = sorted(
        (
            row
            for normalized_label, row in node_string_rows.items()
            if normalized_label not in accepted_label_to_concept and normalized_label in embedded_labels
        ),
        key=lambda row: (-int(row["instance_count"]), row["normalized_label"]),
    )

    candidate_rows = []
    review_rows = []
    auto_map_labels: dict[str, tuple[str, float]] = {}
    for unresolved in unresolved_rows:
        vector_row = conn.execute(
            """
            SELECT vector_json
            FROM string_embeddings
            WHERE normalized_label = ? AND embedding_model = ?
            """,
            (unresolved["normalized_label"], embedding_model),
        ).fetchone()
        if vector_row is None:
            continue
        vector = parse_vector(vector_row[0]).astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm == 0.0:
            continue

        candidate_label_set: set[str] = set()
        for signature_name, index_map in head_signature_indexes.items():
            signature_value = unresolved[signature_name]
            if signature_value:
                candidate_label_set.update(index_map.get(signature_value, set()))
        for token in token_set(unresolved["preferred_label"]):
            candidate_label_set.update(token_to_heads.get(token, set()))
        if not candidate_label_set:
            continue

        if len(candidate_label_set) > 256:
            unresolved_tokens = token_set(unresolved["preferred_label"])
            ranked_candidates = []
            for label in candidate_label_set:
                head_row = node_string_rows[label]
                score = 0.0
                if unresolved["no_paren_signature"] and unresolved["no_paren_signature"] == head_row["no_paren_signature"]:
                    score += 2.0
                if unresolved["paren_acronym"] and unresolved["paren_acronym"] == head_row["paren_acronym"]:
                    score += 2.0
                if unresolved["initialism_signature"] and unresolved["initialism_signature"] == head_row["initialism_signature"]:
                    score += 1.5
                overlap = len(unresolved_tokens & token_set(head_row["preferred_label"]))
                score += float(overlap)
                ranked_candidates.append((score, head_label_to_index[label], label))
            ranked_candidates.sort(key=lambda item: (-item[0], item[2]))
            candidate_indices = np.asarray([idx for _score, idx, _label in ranked_candidates[:256]], dtype=np.int32)
        else:
            candidate_indices = np.asarray(
                sorted(head_label_to_index[label] for label in candidate_label_set if label in head_label_to_index),
                dtype=np.int32,
            )
        if candidate_indices.size == 0:
            continue

        candidate_vectors = head_vectors[candidate_indices]
        candidate_norms = head_norms[candidate_indices]
        cosine_scores = (candidate_vectors @ vector) / (candidate_norms * norm)
        cosine_scores = np.nan_to_num(cosine_scores, nan=-1.0, posinf=-1.0, neginf=-1.0)
        top_local = np.argsort(cosine_scores)[-2:][::-1]
        top_indices = candidate_indices[top_local]
        top1_idx = int(top_indices[0])
        top1_score = float(cosine_scores[top_local[0]])
        top2_score = float(cosine_scores[top_local[1]]) if len(top_local) > 1 else None
        margin = safe_margin(top1_score, top2_score)
        candidate_label = head_labels[top1_idx]
        candidate_concept_id = head_label_to_concept[candidate_label]
        candidate_head = concept_id_to_preferred_label[candidate_concept_id]
        head_row = node_string_rows[candidate_label]
        lexical_issue = lexical_contradiction(unresolved["preferred_label"], head_row["preferred_label"])
        graph_score = graph_context_similarity(dict(unresolved), dict(head_row))

        manual_embedding_decision = manual_pair_decision(unresolved["preferred_label"], candidate_head)

        if top1_score >= auto_threshold and margin >= margin_threshold and not lexical_issue and graph_score >= graph_consistency_threshold:
            decision_status = "accepted_auto_embedding"
            auto_map_labels[unresolved["normalized_label"]] = (candidate_concept_id, top1_score)
        elif (
            manual_embedding_decision.decision == "same_concept"
            and not lexical_issue
            and graph_score >= 0.75
            and top1_score >= review_threshold
        ):
            decision_status = "accepted_auto_embedding"
            auto_map_labels[unresolved["normalized_label"]] = (candidate_concept_id, top1_score)
        elif (top1_score >= review_threshold or margin < margin_threshold) and int(unresolved["instance_count"]) >= 7:
            decision_status = "needs_manual_review"
            review_rows.append(
                (
                    unresolved["normalized_label"],
                    candidate_concept_id,
                    candidate_head,
                    top1_score,
                    margin,
                    graph_score,
                    bool_to_int(lexical_issue),
                    "needs_manual_review",
                    "Embedding similarity ambiguous or contradicted by lexical/graph evidence.",
                )
            )
        else:
            decision_status = "rejected_embedding"

        candidate_rows.append(
            (
                unresolved["normalized_label"],
                candidate_concept_id,
                candidate_head,
                top1_score,
                margin,
                graph_score,
                bool_to_int(lexical_issue),
                decision_status,
                "embedding_v2",
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
        "tail_to_head_candidates": len(candidate_rows),
        "embedding_review_queue": len(review_rows),
        "auto_embedding_mapped_labels": len(auto_map_labels),
    }, auto_map_labels


def ingest_embedding_review_rows(
    conn: sqlite3.Connection,
    embedding_review_rows: list[dict[str, str]],
) -> dict[str, tuple[str, float]]:
    if not embedding_review_rows:
        return {}
    now = datetime.now(timezone.utc).isoformat()
    manual_maps: dict[str, tuple[str, float]] = {}
    queue_rows = []
    for row in embedding_review_rows:
        normalized_label = row["normalized_label"]
        candidate_concept_id = row["candidate_concept_id"]
        decision = row["manual_decision"]
        if decision == "same_concept":
            manual_maps[normalized_label] = (candidate_concept_id, 0.96)
        queue_rows.append(
            (
                normalized_label,
                candidate_concept_id,
                row.get("candidate_preferred_label", ""),
                float(row.get("cosine_similarity") or 0.0),
                float(row.get("margin") or 0.0),
                float(row.get("graph_context_similarity") or 0.0),
                bool_to_int(str(row.get("lexical_contradiction", "0")).strip() in {"1", "true", "True"}),
                "manual_reviewed",
                row.get("review_notes", ""),
            )
        )
        conn.execute(
            """
            INSERT INTO review_decisions (
                left_normalized_label, right_normalized_label, proposed_decision, final_decision,
                decision_source, evidence_json, prompt_version, model, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_label,
                candidate_concept_id,
                "needs_manual_review",
                decision,
                "manual_codex_v2_embedding",
                json.dumps(
                    {
                        "candidate_preferred_label": row.get("candidate_preferred_label", ""),
                        "cosine_similarity": row.get("cosine_similarity", ""),
                        "margin": row.get("margin", ""),
                        "graph_context_similarity": row.get("graph_context_similarity", ""),
                        "lexical_contradiction": row.get("lexical_contradiction", ""),
                    },
                    ensure_ascii=False,
                ),
                "manual_codex_v2_embedding",
                "codex_manual_review",
                row.get("review_notes", ""),
                now,
            ),
        )
    conn.executemany(
        """
        INSERT OR REPLACE INTO embedding_review_queue (
            normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity, margin,
            graph_context_similarity, lexical_contradiction, review_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        queue_rows,
    )
    conn.commit()
    return manual_maps


def rebuild_instance_mappings(
    conn: sqlite3.Connection,
    accepted_label_to_concept: dict[str, tuple[str, str, float]],
    signature_maps: dict[str, dict[str, set[str]]],
    ontology_version: str,
    embedding_auto_maps: dict[str, tuple[str, float]],
    manual_embedding_maps: dict[str, tuple[str, float]],
) -> dict[str, int]:
    mapping_rows = []
    cursor = conn.execute(
        """
        SELECT custom_id, node_id, normalized_label, no_paren_signature, punctuation_signature,
               singular_signature, paren_acronym
        FROM node_instances
        ORDER BY custom_id, node_id
        """
    )
    for custom_id, node_id, normalized_label, no_paren_signature, punctuation_signature, singular_signature, paren_acronym in cursor:
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
                mapping_source = "manual"
            elif normalized_label in embedding_auto_maps:
                concept_id, confidence = embedding_auto_maps[normalized_label]
                mapping_source = "embedding"
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
    return {
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
                json.dumps({"start_year": json.loads(start_year_json), "end_year": json.loads(end_year_json)}, ensure_ascii=False),
                json.dumps([context_note] if context_note and context_note != "NA" else [], ensure_ascii=False),
            )
            for concept_id, fingerprint, count_support, countries_json, unit_json, start_year_json, end_year_json, context_note in rows
        ],
    )
    conn.commit()


def export_v2_artifacts(conn: sqlite3.Connection, output_root: Path, export_top_heads: int, export_top_edges: int) -> None:
    exports_dir = output_root / "exports"
    analysis_dir = output_root / "analysis"
    exports_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    head_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT concept_id, preferred_label, instance_support, distinct_paper_support, aliases_count,
                   review_status, cluster_member_labels_json
            FROM head_concepts
            ORDER BY instance_support DESC, concept_id
            LIMIT ?
            """,
            (export_top_heads,),
        ).fetchall()
    ]
    write_csv(exports_dir / "top_head_concepts.csv", head_rows, list(head_rows[0].keys()) if head_rows else ["concept_id"])

    edge_rows = [
        dict(row)
        for row in conn.execute(
            """
            WITH concept_edges AS (
                SELECT sm.concept_id AS source_concept_id,
                       tm.concept_id AS target_concept_id,
                       COUNT(*) AS support_count
                FROM edge_instances e
                JOIN instance_mappings sm ON sm.custom_id = e.custom_id AND sm.node_id = e.source_node_id
                JOIN instance_mappings tm ON tm.custom_id = e.custom_id AND tm.node_id = e.target_node_id
                WHERE sm.concept_id IS NOT NULL
                  AND tm.concept_id IS NOT NULL
                  AND sm.concept_id != tm.concept_id
                GROUP BY sm.concept_id, tm.concept_id
            )
            SELECT ce.source_concept_id, hs.preferred_label AS source_label,
                   ce.target_concept_id, ht.preferred_label AS target_label,
                   ce.support_count
            FROM concept_edges ce
            JOIN head_concepts hs ON hs.concept_id = ce.source_concept_id
            JOIN head_concepts ht ON ht.concept_id = ce.target_concept_id
            ORDER BY ce.support_count DESC, ce.source_concept_id, ce.target_concept_id
            LIMIT ?
            """,
            (export_top_edges,),
        ).fetchall()
    ]
    write_csv(exports_dir / "top_concept_edges.csv", edge_rows, list(edge_rows[0].keys()) if edge_rows else ["source_concept_id"])
    review_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity,
                   margin, graph_context_similarity, lexical_contradiction, review_status, notes
            FROM embedding_review_queue
            ORDER BY cosine_similarity DESC, margin ASC, normalized_label
            """
        ).fetchall()
    ]
    if review_rows:
        write_csv(output_root / "review" / "embedding_review_queue.csv", review_rows, list(review_rows[0].keys()))


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    v2_db = output_root / "ontology_v2.sqlite"
    conn = init_v2_db(Path(args.v1_db), v2_db)

    manual_review_rows = load_manual_review_rows(Path(args.manual_review_csv))
    manual_overrides = load_manual_overrides(Path(args.manual_negative_overrides))
    embedding_review_rows = load_optional_review_rows(Path(args.embedding_review_csv))
    same_pairs, blocked_pairs, isolate_labels = ingest_manual_inputs(conn, manual_review_rows, manual_overrides)
    manual_embedding_maps = ingest_embedding_review_rows(conn, embedding_review_rows)
    accepted_label_to_concept, cluster_stats = cluster_head_pool(
        conn=conn,
        same_pairs=same_pairs,
        blocked_pairs=blocked_pairs,
        isolate_labels=isolate_labels,
        target_heads=args.target_heads,
        ontology_version=args.ontology_version,
    )
    signature_maps = build_signature_maps(conn, accepted_label_to_concept)
    node_string_rows = load_node_string_rows(conn)

    embedding_stats: dict[str, int] = {"tail_to_head_candidates": 0, "embedding_review_queue": 0, "auto_embedding_mapped_labels": 0}
    embedding_auto_maps: dict[str, tuple[str, float]] = {}
    if conn.execute("SELECT COUNT(*) FROM string_embeddings WHERE embedding_model = ?", (args.embedding_model,)).fetchone()[0] > 0:
        embedding_stats, embedding_auto_maps = apply_embedding_tail_mapping(
            conn=conn,
            node_string_rows=node_string_rows,
            accepted_label_to_concept=accepted_label_to_concept,
            ontology_version=args.ontology_version,
            embedding_model=args.embedding_model,
            auto_threshold=args.auto_embedding_threshold,
            review_threshold=args.review_embedding_threshold,
            margin_threshold=args.embedding_margin_threshold,
            graph_consistency_threshold=args.graph_consistency_threshold,
        )

    mapping_stats = rebuild_instance_mappings(
        conn=conn,
        accepted_label_to_concept=accepted_label_to_concept,
        signature_maps=signature_maps,
        ontology_version=args.ontology_version,
        embedding_auto_maps=embedding_auto_maps,
        manual_embedding_maps=manual_embedding_maps,
    )
    populate_context_fingerprints(conn)
    export_v2_artifacts(conn, output_root, export_top_heads=args.export_top_heads, export_top_edges=args.export_top_edges)

    manifest = {
        "ontology_version": args.ontology_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_v1_db": str(args.v1_db),
        "manual_review_csv": str(args.manual_review_csv),
        "manual_negative_overrides": str(args.manual_negative_overrides),
        "embedding_review_csv": str(args.embedding_review_csv),
        "counts": {
            "node_instances": int(conn.execute("SELECT COUNT(*) FROM node_instances").fetchone()[0]),
            "node_strings": int(conn.execute("SELECT COUNT(*) FROM node_strings").fetchone()[0]),
            "candidate_pairs": int(conn.execute("SELECT COUNT(*) FROM candidate_pairs").fetchone()[0]),
            "review_decisions": int(conn.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0]),
            "manual_overrides": int(conn.execute("SELECT COUNT(*) FROM manual_overrides").fetchone()[0]),
            "head_concepts": int(conn.execute("SELECT COUNT(*) FROM head_concepts").fetchone()[0]),
            "context_fingerprints": int(conn.execute("SELECT COUNT(*) FROM context_fingerprints").fetchone()[0]),
            "embedding_rows": int(conn.execute("SELECT COUNT(*) FROM string_embeddings WHERE embedding_model = ?", (args.embedding_model,)).fetchone()[0]),
            **cluster_stats,
            **embedding_stats,
            "manual_embedding_maps": len(manual_embedding_maps),
            **mapping_stats,
        },
        "parameters": {
            "target_heads": args.target_heads,
            "embedding_model": args.embedding_model,
            "auto_embedding_threshold": args.auto_embedding_threshold,
            "review_embedding_threshold": args.review_embedding_threshold,
            "embedding_margin_threshold": args.embedding_margin_threshold,
            "graph_consistency_threshold": args.graph_consistency_threshold,
        },
    }
    write_json(output_root / "manifest.json", manifest)
    conn.close()


if __name__ == "__main__":
    main()
