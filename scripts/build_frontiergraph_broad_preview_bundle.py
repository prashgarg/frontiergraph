from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_frontiergraph_broad_preview_site import GENERATED_SITE_DATA_PATH, main as build_site_preview
from scripts.frontiergraph_regime_preview_utils import ROOT, build_broad_preview_dataset, write_json


SITE_ROOT = ROOT / "site"
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public" / "downloads"
OUTPUT_DB_PATH = Path(os.environ.get("FRONTIERGRAPH_PUBLIC_RELEASE_DB_BROAD", "/tmp/frontiergraph-economics-broad-preview.db"))
PUBLIC_DB_FILENAME = os.environ.get("FRONTIERGRAPH_PUBLIC_DB_FILENAME_BROAD", OUTPUT_DB_PATH.name)
DEFAULT_PUBLIC_URL = os.environ.get("FRONTIERGRAPH_PUBLIC_BROAD_DB_URL", "").strip()
MANIFEST_PATH = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-broad-preview.manifest.json"
CHECKSUM_PATH = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-broad-preview.sha256.txt"


QUESTION_COLUMNS = [
    "pair_key",
    "source_id",
    "target_id",
    "source_label",
    "target_label",
    "source_display_label",
    "target_display_label",
    "source_display_concept_id",
    "target_display_concept_id",
    "source_display_refined",
    "target_display_refined",
    "display_refinement_confidence",
    "source_bucket",
    "target_bucket",
    "cross_field",
    "score",
    "base_score",
    "duplicate_penalty",
    "path_support_norm",
    "gap_bonus",
    "mediator_count",
    "motif_count",
    "cooc_count",
    "direct_link_status",
    "supporting_path_count",
    "why_now",
    "recommended_move",
    "slice_label",
    "public_pair_label",
    "question_family",
    "suppress_from_public_ranked_window",
    "top_mediator_labels_json",
    "top_mediator_baseline_labels_json",
    "representative_papers_json",
    "top_countries_source_json",
    "top_countries_target_json",
    "source_context_summary",
    "target_context_summary",
    "common_contexts",
    "public_specificity_score",
    "app_link",
]

CONCEPT_COLUMNS = [
    "concept_id",
    "label",
    "plain_label",
    "subtitle",
    "display_concept_id",
    "display_refined",
    "display_refinement_confidence",
    "alternate_display_labels_json",
    "bucket_hint",
    "instance_support",
    "distinct_paper_support",
    "weighted_degree",
    "pagerank",
    "in_degree",
    "out_degree",
    "neighbor_count",
    "top_countries_json",
    "top_units_json",
    "app_link",
]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sqlite_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle_db(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"Integrity check failed for {path}")
        tables = [
            "top_questions",
            "questions",
            "concepts",
            "question_mediators",
            "question_paths",
            "question_papers",
            "concept_neighbors",
            "concept_opportunities",
        ]
        counts = {table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables}
    finally:
        conn.close()
    return counts


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE release_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE release_metrics (key TEXT PRIMARY KEY, value TEXT);

        CREATE TABLE top_questions (
          pair_key TEXT PRIMARY KEY,
          source_id TEXT,
          target_id TEXT,
          source_label TEXT,
          target_label TEXT,
          source_display_label TEXT,
          target_display_label TEXT,
          source_display_concept_id TEXT,
          target_display_concept_id TEXT,
          source_display_refined INTEGER,
          target_display_refined INTEGER,
          display_refinement_confidence REAL,
          source_bucket TEXT,
          target_bucket TEXT,
          cross_field INTEGER,
          score REAL,
          base_score REAL,
          duplicate_penalty REAL,
          path_support_norm REAL,
          gap_bonus REAL,
          mediator_count INTEGER,
          motif_count INTEGER,
          cooc_count INTEGER,
          direct_link_status TEXT,
          supporting_path_count INTEGER,
          why_now TEXT,
          recommended_move TEXT,
          slice_label TEXT,
          public_pair_label TEXT,
          question_family TEXT,
          suppress_from_public_ranked_window INTEGER,
          top_mediator_labels_json TEXT,
          top_mediator_baseline_labels_json TEXT,
          representative_papers_json TEXT,
          top_countries_source_json TEXT,
          top_countries_target_json TEXT,
          source_context_summary TEXT,
          target_context_summary TEXT,
          common_contexts TEXT,
          public_specificity_score REAL,
          app_link TEXT
        );

        CREATE TABLE questions AS SELECT * FROM top_questions WHERE 0;

        CREATE TABLE concepts (
          concept_id TEXT PRIMARY KEY,
          label TEXT,
          plain_label TEXT,
          subtitle TEXT,
          display_concept_id TEXT,
          display_refined INTEGER,
          display_refinement_confidence REAL,
          alternate_display_labels_json TEXT,
          bucket_hint TEXT,
          instance_support INTEGER,
          distinct_paper_support INTEGER,
          weighted_degree REAL,
          pagerank REAL,
          in_degree INTEGER,
          out_degree INTEGER,
          neighbor_count INTEGER,
          top_countries_json TEXT,
          top_units_json TEXT,
          app_link TEXT
        );

        CREATE TABLE central_concepts (
          concept_id TEXT PRIMARY KEY,
          label TEXT,
          plain_label TEXT,
          subtitle TEXT,
          display_concept_id TEXT,
          display_refined INTEGER,
          display_refinement_confidence REAL,
          alternate_display_labels_json TEXT,
          bucket_hint TEXT,
          instance_support INTEGER,
          distinct_paper_support INTEGER,
          weighted_degree REAL,
          pagerank REAL,
          in_degree INTEGER,
          out_degree INTEGER,
          neighbor_count INTEGER,
          top_countries_json TEXT,
          top_units_json TEXT,
          app_link TEXT
        );

        CREATE TABLE concept_index (
          concept_id TEXT PRIMARY KEY,
          label TEXT,
          plain_label TEXT,
          subtitle TEXT,
          display_concept_id TEXT,
          display_refined INTEGER,
          display_refinement_confidence REAL,
          alternate_display_labels_json TEXT,
          aliases_json TEXT,
          bucket_hint TEXT,
          instance_support INTEGER,
          distinct_paper_support INTEGER,
          weighted_degree REAL,
          pagerank REAL,
          in_degree INTEGER,
          out_degree INTEGER,
          neighbor_count INTEGER,
          top_countries_json TEXT,
          top_units_json TEXT,
          search_terms_json TEXT,
          app_link TEXT
        );

        CREATE TABLE graph_nodes (
          concept_id TEXT PRIMARY KEY,
          label TEXT,
          plain_label TEXT,
          x REAL,
          y REAL,
          bucket_hint TEXT,
          weighted_degree REAL,
          pagerank REAL
        );

        CREATE TABLE graph_edges (
          id TEXT PRIMARY KEY,
          source TEXT,
          target TEXT,
          support_count INTEGER,
          distinct_papers INTEGER,
          avg_stability REAL,
          strength REAL
        );

        CREATE TABLE question_mediators (
          pair_key TEXT,
          rank INTEGER,
          mediator_concept_id TEXT,
          mediator_label TEXT,
          mediator_baseline_label TEXT,
          score REAL
        );

        CREATE TABLE question_paths (
          pair_key TEXT,
          rank INTEGER,
          path_len INTEGER,
          path_score REAL,
          path_text TEXT,
          path_nodes_json TEXT,
          path_labels_json TEXT,
          path_baseline_labels_json TEXT
        );

        CREATE TABLE question_papers (
          pair_key TEXT,
          path_rank INTEGER,
          paper_rank INTEGER,
          paper_id TEXT,
          title TEXT,
          year INTEGER,
          edge_src TEXT,
          edge_src_label TEXT,
          edge_src_baseline_label TEXT,
          edge_dst TEXT,
          edge_dst_label TEXT,
          edge_dst_baseline_label TEXT
        );

        CREATE TABLE question_neighborhoods (
          pair_key TEXT PRIMARY KEY,
          source_out_neighbors_json TEXT,
          target_in_neighbors_json TEXT
        );

        CREATE TABLE concept_neighbors (
          concept_id TEXT,
          direction TEXT,
          rank_for_concept INTEGER,
          neighbor_concept_id TEXT,
          label TEXT,
          support_count INTEGER,
          distinct_papers INTEGER,
          avg_stability REAL,
          row_json TEXT
        );

        CREATE TABLE concept_opportunities (
          concept_id TEXT,
          rank_for_concept INTEGER,
          pair_key TEXT,
          score REAL,
          source_label TEXT,
          target_label TEXT,
          row_json TEXT
        );
        """
    )


def insert_questions(conn: sqlite3.Connection, table_name: str, questions: list[dict[str, Any]]) -> None:
    placeholders = ", ".join("?" for _ in QUESTION_COLUMNS)
    sql = f"INSERT INTO {table_name} ({', '.join(QUESTION_COLUMNS)}) VALUES ({placeholders})"
    rows = []
    for question in questions:
        rows.append(
            [
                question["pair_key"],
                question["source_id"],
                question["target_id"],
                question["source_label"],
                question["target_label"],
                question["source_display_label"],
                question["target_display_label"],
                question["source_display_concept_id"],
                question["target_display_concept_id"],
                int(bool(question.get("source_display_refined"))),
                int(bool(question.get("target_display_refined"))),
                float(question.get("display_refinement_confidence") or 0.0),
                question["source_bucket"],
                question["target_bucket"],
                int(bool(question.get("cross_field"))),
                float(question.get("score") or 0.0),
                float(question.get("base_score") or 0.0),
                float(question.get("duplicate_penalty") or 0.0),
                float(question.get("path_support_norm") or 0.0),
                float(question.get("gap_bonus") or 0.0),
                int(question.get("mediator_count") or 0),
                int(question.get("motif_count") or 0),
                int(question.get("cooc_count") or 0),
                question["direct_link_status"],
                int(question.get("supporting_path_count") or 0),
                question["why_now"],
                question["recommended_move"],
                question["slice_label"],
                question["public_pair_label"],
                question["question_family"],
                int(bool(question.get("suppress_from_public_ranked_window"))),
                sqlite_json(question.get("top_mediator_labels", [])),
                sqlite_json(question.get("top_mediator_baseline_labels", [])),
                sqlite_json(question.get("representative_papers", [])),
                sqlite_json(question.get("top_countries_source", [])),
                sqlite_json(question.get("top_countries_target", [])),
                question.get("source_context_summary", ""),
                question.get("target_context_summary", ""),
                question.get("common_contexts", ""),
                float(question.get("public_specificity_score") or 0.0),
                question["app_link"],
            ]
        )
    conn.executemany(sql, rows)


def insert_concepts(conn: sqlite3.Connection, table_name: str, concepts: list[dict[str, Any]]) -> None:
    placeholders = ", ".join("?" for _ in CONCEPT_COLUMNS)
    sql = f"INSERT INTO {table_name} ({', '.join(CONCEPT_COLUMNS)}) VALUES ({placeholders})"
    rows = []
    for concept in concepts:
        rows.append(
            [
                concept["concept_id"],
                concept["label"],
                concept["plain_label"],
                concept.get("subtitle", ""),
                concept.get("display_concept_id", concept["concept_id"]),
                int(bool(concept.get("display_refined"))),
                float(concept.get("display_refinement_confidence") or 0.0),
                sqlite_json(concept.get("alternate_display_labels", [])),
                concept.get("bucket_hint", "mixed"),
                int(concept.get("instance_support") or 0),
                int(concept.get("distinct_paper_support") or 0),
                float(concept.get("weighted_degree") or 0.0),
                float(concept.get("pagerank") or 0.0),
                int(concept.get("in_degree") or 0),
                int(concept.get("out_degree") or 0),
                int(concept.get("neighbor_count") or 0),
                sqlite_json(concept.get("top_countries", [])),
                sqlite_json(concept.get("top_units", [])),
                concept.get("app_link", ""),
            ]
        )
    conn.executemany(sql, rows)


def write_bundle(dataset: dict[str, Any], output_path: Path) -> dict[str, int]:
    ensure_parent(output_path)
    if output_path.exists():
        output_path.unlink()
    conn = sqlite3.connect(output_path)
    try:
        create_tables(conn)
        conn.executemany(
            "INSERT INTO app_meta(key, value) VALUES (?, ?)",
            [
                ("app_mode", "concept_broad_preview"),
                ("release_variant", "broad"),
                ("preview_note", str(dataset.get("preview_note") or "")),
            ],
        )
        conn.executemany(
            "INSERT INTO release_meta(key, value) VALUES (?, ?)",
            [
                ("variant", "broad"),
                ("variant_label", "Broad preview"),
                ("generated_at", str(dataset["generated_at"])),
                ("preview_note", str(dataset.get("preview_note") or "")),
                ("app_url", str(dataset["app_url"])),
            ],
        )
        conn.executemany(
            "INSERT INTO release_metrics(key, value) VALUES (?, ?)",
            [(key, int(value)) for key, value in dataset["metrics"].items()],
        )

        insert_questions(conn, "top_questions", dataset["top_questions"])
        insert_questions(conn, "questions", dataset["questions"])
        insert_concepts(conn, "concepts", dataset["concepts"])
        insert_concepts(conn, "central_concepts", dataset["central_concepts"])

        conn.executemany(
            """
            INSERT INTO concept_index(
              concept_id, label, plain_label, subtitle, display_concept_id, display_refined, display_refinement_confidence,
              alternate_display_labels_json, aliases_json, bucket_hint, instance_support, distinct_paper_support, weighted_degree,
              pagerank, in_degree, out_degree, neighbor_count, top_countries_json, top_units_json, search_terms_json, app_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    concept["concept_id"],
                    concept["label"],
                    concept["plain_label"],
                    concept.get("subtitle", ""),
                    concept.get("display_concept_id", concept["concept_id"]),
                    int(bool(concept.get("display_refined"))),
                    float(concept.get("display_refinement_confidence") or 0.0),
                    sqlite_json(concept.get("alternate_display_labels", [])),
                    sqlite_json(concept.get("aliases", [])),
                    concept.get("bucket_hint", "mixed"),
                    int(concept.get("instance_support") or 0),
                    int(concept.get("distinct_paper_support") or 0),
                    float(concept.get("weighted_degree") or 0.0),
                    float(concept.get("pagerank") or 0.0),
                    int(concept.get("in_degree") or 0),
                    int(concept.get("out_degree") or 0),
                    int(concept.get("neighbor_count") or 0),
                    sqlite_json(concept.get("top_countries", [])),
                    sqlite_json(concept.get("top_units", [])),
                    sqlite_json(concept.get("search_terms", [])),
                    concept.get("app_link", ""),
                )
                for concept in dataset["concepts"]
            ],
        )
        conn.executemany(
            "INSERT INTO graph_nodes(concept_id, label, plain_label, x, y, bucket_hint, weighted_degree, pagerank) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    node["id"],
                    node["label"],
                    node["plain_label"],
                    float(node["x"]),
                    float(node["y"]),
                    node.get("bucket_hint", "mixed"),
                    float(node.get("weighted_degree") or 0.0),
                    float(node.get("pagerank") or 0.0),
                )
                for node in dataset["graph"]["nodes"]
            ],
        )
        conn.executemany(
            "INSERT INTO graph_edges(id, source, target, support_count, distinct_papers, avg_stability, strength) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    edge["id"],
                    edge["source"],
                    edge["target"],
                    int(edge.get("support_count") or 0),
                    int(edge.get("distinct_papers") or 0),
                    float(edge.get("avg_stability") or 0.0),
                    float(edge.get("strength") or 0.0),
                )
                for edge in dataset["graph"]["edges"]
            ],
        )
        conn.executemany(
            "INSERT INTO question_mediators(pair_key, rank, mediator_concept_id, mediator_label, mediator_baseline_label, score) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    row["pair_key"],
                    int(row["rank"]),
                    row["mediator_concept_id"],
                    row["mediator_label"],
                    row["mediator_baseline_label"],
                    float(row["score"]),
                )
                for row in dataset["question_mediators"]
            ],
        )
        conn.executemany(
            "INSERT INTO question_paths(pair_key, rank, path_len, path_score, path_text, path_nodes_json, path_labels_json, path_baseline_labels_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["pair_key"],
                    int(row["rank"]),
                    int(row["path_len"]),
                    float(row["path_score"]),
                    row["path_text"],
                    row["path_nodes_json"],
                    row["path_labels_json"],
                    row["path_baseline_labels_json"],
                )
                for row in dataset["question_paths"]
            ],
        )
        conn.executemany(
            "INSERT INTO question_papers(pair_key, path_rank, paper_rank, paper_id, title, year, edge_src, edge_src_label, edge_src_baseline_label, edge_dst, edge_dst_label, edge_dst_baseline_label) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["pair_key"],
                    int(row["path_rank"]),
                    int(row["paper_rank"]),
                    row["paper_id"],
                    row["title"],
                    int(row["year"] or 0),
                    row["edge_src"],
                    row["edge_src_label"],
                    row["edge_src_baseline_label"],
                    row["edge_dst"],
                    row["edge_dst_label"],
                    row["edge_dst_baseline_label"],
                )
                for row in dataset["question_papers"]
            ],
        )
        conn.executemany(
            "INSERT INTO question_neighborhoods(pair_key, source_out_neighbors_json, target_in_neighbors_json) VALUES (?, ?, ?)",
            [
                (row["pair_key"], row["source_out_neighbors_json"], row["target_in_neighbors_json"])
                for row in dataset["question_neighborhoods"]
            ],
        )
        conn.executemany(
            "INSERT INTO concept_neighbors(concept_id, direction, rank_for_concept, neighbor_concept_id, label, support_count, distinct_papers, avg_stability, row_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["concept_id"],
                    row["direction"],
                    int(row["rank_for_concept"]),
                    row["neighbor_concept_id"],
                    row["label"],
                    int(row["support_count"]),
                    int(row["distinct_papers"]),
                    float(row["avg_stability"]),
                    row["row_json"],
                )
                for row in dataset["concept_neighbors_rows"]
            ],
        )
        conn.executemany(
            "INSERT INTO concept_opportunities(concept_id, rank_for_concept, pair_key, score, source_label, target_label, row_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["concept_id"],
                    int(row["rank_for_concept"]),
                    row["pair_key"],
                    float(row["score"]),
                    row["source_label"],
                    row["target_label"],
                    row["row_json"],
                )
                for row in dataset["concept_opportunities_rows"]
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return verify_bundle_db(output_path)


def update_site_payload(output_path: Path, sha256: str) -> None:
    payload = json.loads(GENERATED_SITE_DATA_PATH.read_text(encoding="utf-8"))
    public_db = payload.setdefault("downloads", {}).setdefault("public_db", {})
    public_db["filename"] = PUBLIC_DB_FILENAME
    public_db["public_url"] = DEFAULT_PUBLIC_URL
    public_db["sha256"] = sha256
    public_db["db_size_bytes"] = output_path.stat().st_size
    public_db["db_size_gb"] = round(output_path.stat().st_size / (1024 ** 3), 3)
    GENERATED_SITE_DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_download_manifests(output_path: Path, sha256: str, counts: dict[str, int], dataset: dict[str, Any]) -> None:
    ensure_parent(MANIFEST_PATH)
    ensure_parent(CHECKSUM_PATH)
    CHECKSUM_PATH.write_text(f"{sha256}  {PUBLIC_DB_FILENAME}\n", encoding="utf-8")
    manifest = {
        "generated_at": dataset["generated_at"],
        "variant": "broad",
        "variant_label": "Broad preview",
        "db_filename": PUBLIC_DB_FILENAME,
        "db_size_bytes": output_path.stat().st_size,
        "sha256": sha256,
        "public_url": DEFAULT_PUBLIC_URL,
        "counts": counts,
        "preview_note": dataset.get("preview_note", ""),
    }
    write_json(MANIFEST_PATH, manifest)


def main() -> None:
    build_site_preview()
    dataset = build_broad_preview_dataset(limit=100)
    counts = write_bundle(dataset, OUTPUT_DB_PATH)
    sha256 = sha256_file(OUTPUT_DB_PATH)
    update_site_payload(OUTPUT_DB_PATH, sha256)
    write_download_manifests(OUTPUT_DB_PATH, sha256, counts, dataset)


if __name__ == "__main__":
    main()
