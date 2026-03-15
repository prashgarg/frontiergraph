from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
PUBLIC_DATA_DIR = SITE_ROOT / "public" / "data" / "v2"
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public" / "downloads"
GENERATED_SITE_DATA_PATH = SITE_ROOT / "src" / "generated" / "site-data.json"
OUTPUT_DB_PATH = ROOT / "data" / "production" / "frontiergraph_public_release" / "frontiergraph-economics-public.db"
SOURCE_DB_PATH = Path(
    os.environ.get(
        "FRONTIERGRAPH_PUBLIC_SOURCE_DB",
        ROOT
        / "data"
        / "production"
        / "frontiergraph_concept_compare_v1"
        / "baseline"
        / "suppression"
        / "concept_exploratory_suppressed_top100k_app.sqlite",
    )
)
MANIFEST_PATH = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.manifest.json"
CHECKSUM_PATH = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.sha256.txt"
DEFAULT_PUBLIC_URL = "https://storage.googleapis.com/frontiergraph-public-downloads-1058669339361/frontiergraph-economics-public.db"


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def shard_path_from_public_url(path: str) -> Path:
    cleaned = path.lstrip("/")
    return SITE_ROOT / "public" / cleaned


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


def parse_json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except Exception:
        return []
    return loaded if isinstance(loaded, list) else []


def label_lookup_from_assets(
    concept_index: list[dict[str, Any]],
    graph_backbone: dict[str, Any],
    central_concepts: list[dict[str, str]],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in concept_index:
        concept_id = str(row.get("concept_id", "")).strip()
        label = str(row.get("plain_label") or row.get("label") or "").strip()
        if concept_id and label:
            lookup[concept_id] = label
    for row in central_concepts:
        concept_id = str(row.get("concept_id", "")).strip()
        label = str(row.get("plain_label") or row.get("label") or "").strip()
        if concept_id and label:
            lookup.setdefault(concept_id, label)
    for row in graph_backbone.get("nodes", []):
        concept_id = str(row.get("id", "")).strip()
        label = str(row.get("plain_label") or row.get("label") or "").strip()
        if concept_id and label:
            lookup.setdefault(concept_id, label)
    return lookup


def top_values_from_json(value: str | None, *, limit: int = 3) -> list[str]:
    items = parse_json_list(value)
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = str(item.get("value", "")).strip()
        else:
            text = str(item).strip()
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def direct_literature_status(cooc_count: int) -> str:
    if cooc_count <= 0:
        return "No direct papers yet in the current public sample"
    if cooc_count <= 3:
        return "A few direct papers already exist in the current public sample"
    return "Direct literature already exists in the current public sample"


def recommendation_play(row: sqlite3.Row) -> str:
    cooc_count = int(row["cooc_count"] or 0)
    cross_field = str(row["u_bucket_hint"] or "") != str(row["v_bucket_hint"] or "")
    path_support = float(row["path_support_norm"] or 0.0)
    gap_bonus = float(row["gap_bonus"] or 0.0)
    mediator_count = int(row["mediator_count"] or 0)
    motif_count = int(row["motif_count"] or 0)

    if cross_field and cooc_count <= 0 and path_support >= 0.7:
        return "Bridge paper across literatures"
    if cross_field and cooc_count <= 0:
        return "Scoping review before a bridge paper"
    if gap_bonus >= 0.4 and mediator_count >= 25:
        return "Direct empirical test"
    if gap_bonus >= 0.4:
        return "Synthesis plus pilot design"
    if path_support >= 0.8 and motif_count >= 100:
        return "Flagship empirical paper"
    if path_support >= 0.7:
        return "Focused empirical test"
    return "Seminar seed or targeted replication map"


def slice_label(row: sqlite3.Row) -> str:
    cooc_count = int(row["cooc_count"] or 0)
    cross_field = str(row["u_bucket_hint"] or "") != str(row["v_bucket_hint"] or "")
    path_support = float(row["path_support_norm"] or 0.0)
    if cooc_count <= 0 and cross_field:
        return "Cross-bucket frontier"
    if cooc_count <= 0:
        return "Within-bucket frontier"
    if path_support >= 0.8:
        return "Fast follow"
    return "Broader released list"


def plain_context(values: list[str], fallback: str) -> str:
    if not values:
        return fallback
    return ", ".join(values)


def why_now(row: sqlite3.Row, source_plain: str, target_plain: str) -> str:
    return (
        f"{source_plain} and {target_plain} already sit near "
        f"{int(row['mediator_count'] or 0)} related ideas and {int(row['motif_count'] or 0)} supporting motifs, "
        f"while the direct literature remains at {int(row['cooc_count'] or 0)} papers in the current public sample."
    )


def build_release_bundle(output_path: Path, source_db_path: Path) -> tuple[int, str]:
    site_data = read_json(GENERATED_SITE_DATA_PATH)
    top_questions = load_csv_rows(PUBLIC_DATA_DIR / "top_questions.csv")
    central_concepts = load_csv_rows(PUBLIC_DATA_DIR / "central_concepts.csv")
    concept_index = read_json(PUBLIC_DATA_DIR / "concept_index.json")
    graph_backbone = read_json(PUBLIC_DATA_DIR / "graph_backbone.json")
    opportunity_slices = read_json(PUBLIC_DATA_DIR / "opportunity_slices.json")
    neighborhoods_index = read_json(PUBLIC_DATA_DIR / "concept_neighborhoods_index.json")
    concept_opportunities_index = read_json(PUBLIC_DATA_DIR / "concept_opportunities_index.json")
    hybrid_manifest = read_json(PUBLIC_DATA_DIR / "hybrid_corpus_manifest.json")

    if not source_db_path.exists():
        raise FileNotFoundError(f"Source public app database is missing: {source_db_path}")

    if output_path.exists() or output_path.is_symlink():
        output_path.unlink()
    ensure_parent(output_path)

    conn = sqlite3.connect(output_path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")

    conn.executescript(
        """
        CREATE TABLE app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE release_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE release_metrics (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        );
        CREATE TABLE top_questions (
            pair_key TEXT PRIMARY KEY,
            source_id TEXT,
            target_id TEXT,
            source_label TEXT,
            target_label TEXT,
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
            representative_papers_json TEXT,
            top_countries_source_json TEXT,
            top_countries_target_json TEXT,
            source_context_summary TEXT,
            target_context_summary TEXT,
            common_contexts TEXT,
            app_link TEXT
        );
        CREATE TABLE questions (
            pair_key TEXT PRIMARY KEY,
            source_id TEXT,
            target_id TEXT,
            source_label TEXT,
            target_label TEXT,
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
            representative_papers_json TEXT,
            top_countries_source_json TEXT,
            top_countries_target_json TEXT,
            source_context_summary TEXT,
            target_context_summary TEXT,
            common_contexts TEXT,
            app_link TEXT
        );
        CREATE TABLE central_concepts (
            concept_id TEXT PRIMARY KEY,
            label TEXT,
            plain_label TEXT,
            subtitle TEXT,
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
            subtitle TEXT,
            aliases_json TEXT,
            alias_count INTEGER,
            bucket_hint TEXT,
            instance_support INTEGER,
            distinct_paper_support INTEGER,
            x REAL,
            y REAL,
            weighted_degree REAL,
            pagerank REAL,
            in_degree INTEGER,
            out_degree INTEGER,
            neighbor_count INTEGER,
            bucket_group TEXT,
            show_label INTEGER
        );
        CREATE TABLE graph_edges (
            edge_id TEXT PRIMARY KEY,
            source TEXT,
            target TEXT,
            support_count INTEGER,
            distinct_papers INTEGER,
            avg_stability REAL,
            strength REAL,
            directionality_mix_json TEXT,
            relationship_type_mix_json TEXT,
            edge_role_mix_json TEXT,
            dominant_countries_json TEXT,
            dominant_units_json TEXT,
            dominant_years_json TEXT,
            examples_json TEXT
        );
        CREATE TABLE opportunity_slices (
            slice_name TEXT,
            rank_in_slice INTEGER,
            pair_key TEXT,
            score REAL,
            source_label TEXT,
            target_label TEXT,
            row_json TEXT,
            PRIMARY KEY (slice_name, rank_in_slice, pair_key)
        );
        CREATE TABLE concept_opportunities (
            concept_id TEXT,
            rank_for_concept INTEGER,
            pair_key TEXT,
            score REAL,
            source_label TEXT,
            target_label TEXT,
            row_json TEXT,
            PRIMARY KEY (concept_id, rank_for_concept, pair_key)
        );
        CREATE TABLE concept_neighborhoods (
            concept_id TEXT,
            direction TEXT,
            rank_for_concept INTEGER,
            neighbor_concept_id TEXT,
            label TEXT,
            support_count INTEGER,
            distinct_papers INTEGER,
            avg_stability REAL,
            row_json TEXT,
            PRIMARY KEY (concept_id, direction, rank_for_concept, neighbor_concept_id)
        );
        CREATE TABLE question_mediators (
            pair_key TEXT,
            rank INTEGER,
            mediator_concept_id TEXT,
            mediator_label TEXT,
            score REAL,
            PRIMARY KEY (pair_key, rank, mediator_concept_id)
        );
        CREATE TABLE question_paths (
            pair_key TEXT,
            rank INTEGER,
            path_len INTEGER,
            path_score REAL,
            path_text TEXT,
            path_nodes_json TEXT,
            path_labels_json TEXT,
            PRIMARY KEY (pair_key, rank)
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
            edge_dst TEXT,
            edge_dst_label TEXT,
            PRIMARY KEY (pair_key, path_rank, paper_rank, paper_id)
        );
        CREATE TABLE question_neighborhoods (
            pair_key TEXT PRIMARY KEY,
            source_out_neighbors_json TEXT,
            target_in_neighbors_json TEXT
        );
        CREATE VIEW concepts AS
        SELECT
            concept_id,
            label,
            plain_label,
            subtitle,
            bucket_hint,
            instance_support,
            distinct_paper_support,
            weighted_degree,
            pagerank,
            in_degree,
            out_degree,
            neighbor_count,
            top_countries_json,
            top_units_json,
            app_link
        FROM concept_index;
        CREATE VIEW concept_neighbors AS
        SELECT
            concept_id,
            direction,
            rank_for_concept,
            neighbor_concept_id,
            label,
            support_count,
            distinct_papers,
            avg_stability,
            row_json
        FROM concept_neighborhoods;
        CREATE INDEX idx_top_questions_score ON top_questions(score DESC);
        CREATE INDEX idx_questions_score ON questions(score DESC);
        CREATE INDEX idx_questions_public_pair ON questions(public_pair_label);
        CREATE INDEX idx_opportunity_slices_pair_key ON opportunity_slices(pair_key);
        CREATE INDEX idx_concept_opportunities_pair_key ON concept_opportunities(pair_key);
        CREATE INDEX idx_concept_neighborhoods_neighbor ON concept_neighborhoods(neighbor_concept_id);
        CREATE INDEX idx_question_mediators_pair_key ON question_mediators(pair_key, rank);
        CREATE INDEX idx_question_paths_pair_key ON question_paths(pair_key, rank);
        CREATE INDEX idx_question_papers_pair_key ON question_papers(pair_key, path_rank, paper_rank);
        """
    )

    release_meta = {
        "generated_at": site_data["generated_at"],
        "repo_url": site_data["repo_url"],
        "app_url": site_data["app_url"],
        "working_paper_pdf": site_data["downloads"]["artifacts"]["working_paper_pdf"],
        "extended_abstract_pdf": site_data["downloads"]["artifacts"]["extended_abstract_pdf"],
        "benchmark_manifest_json": site_data["downloads"]["artifacts"]["benchmark_manifest_json"],
        "graph_backbone_json": site_data["downloads"]["artifacts"]["graph_backbone_json"],
        "top_questions_csv": site_data["downloads"]["artifacts"]["top_questions_csv"],
        "central_concepts_csv": site_data["downloads"]["artifacts"]["central_concepts_csv"],
        "curated_questions_json": site_data["downloads"]["artifacts"].get("curated_questions_json", ""),
        "concept_index_json": site_data["downloads"]["artifacts"].get("concept_index_json", ""),
        "concept_neighborhoods_index_json": site_data["downloads"]["artifacts"].get("concept_neighborhoods_index_json", ""),
        "concept_opportunities_index_json": site_data["downloads"]["artifacts"].get("concept_opportunities_index_json", ""),
        "opportunity_slices_json": site_data["downloads"]["artifacts"].get("opportunity_slices_json", ""),
        "hybrid_corpus_manifest_json": "/data/v2/hybrid_corpus_manifest.json",
        "source_db_path": str(source_db_path),
    }
    conn.executemany(
        "INSERT INTO release_meta(key, value) VALUES (?, ?)",
        release_meta.items(),
    )
    conn.executemany(
        "INSERT INTO release_metrics(key, value) VALUES (?, ?)",
        [(key, int(value)) for key, value in site_data["metrics"].items()],
    )
    conn.executemany(
        "INSERT INTO app_meta(key, value) VALUES (?, ?)",
        [
            ("app_mode", "public_release_v2"),
            ("schema_version", "frontiergraph_public_bundle_v2"),
            ("app_host", site_data["app_url"]),
            ("source_db", str(source_db_path)),
        ],
    )

    deduped_top_questions: dict[str, dict[str, Any]] = {}
    for row in top_questions:
        prepared = {
            **row,
            "cross_field": int(str(row["cross_field"]).lower() == "true"),
            "score": float(row["score"]),
            "base_score": float(row["base_score"]),
            "duplicate_penalty": float(row["duplicate_penalty"]),
            "path_support_norm": float(row["path_support_norm"]),
            "gap_bonus": float(row["gap_bonus"]),
            "mediator_count": int(row["mediator_count"]),
            "motif_count": int(row["motif_count"]),
            "cooc_count": int(row["cooc_count"]),
            "supporting_path_count": int(row["supporting_path_count"]),
            "suppress_from_public_ranked_window": int(str(row["suppress_from_public_ranked_window"]).lower() == "true"),
            "top_mediator_labels_json": row["top_mediator_labels"],
            "representative_papers_json": row["representative_papers"],
            "top_countries_source_json": row["top_countries_source"],
            "top_countries_target_json": row["top_countries_target"],
        }
        existing = deduped_top_questions.get(prepared["pair_key"])
        if existing is None or prepared["score"] > existing["score"]:
            deduped_top_questions[prepared["pair_key"]] = prepared

    conn.executemany(
        """
        INSERT INTO top_questions VALUES (
            :pair_key, :source_id, :target_id, :source_label, :target_label,
            :source_bucket, :target_bucket, :cross_field, :score, :base_score,
            :duplicate_penalty, :path_support_norm, :gap_bonus, :mediator_count,
            :motif_count, :cooc_count, :direct_link_status, :supporting_path_count,
            :why_now, :recommended_move, :slice_label, :public_pair_label,
            :question_family, :suppress_from_public_ranked_window, :top_mediator_labels_json,
            :representative_papers_json, :top_countries_source_json, :top_countries_target_json,
            :source_context_summary, :target_context_summary, :common_contexts, :app_link
        )
        """,
        deduped_top_questions.values(),
    )

    conn.executemany(
        """
        INSERT INTO central_concepts VALUES (
            :concept_id, :label, :plain_label, :subtitle, :bucket_hint,
            :instance_support, :distinct_paper_support, :weighted_degree,
            :pagerank, :in_degree, :out_degree, :neighbor_count,
            :top_countries_json, :top_units_json, :app_link
        )
        """,
        [
            {
                **row,
                "instance_support": int(row["instance_support"]),
                "distinct_paper_support": int(row["distinct_paper_support"]),
                "weighted_degree": float(row["weighted_degree"]),
                "pagerank": float(row["pagerank"]),
                "in_degree": int(row["in_degree"]),
                "out_degree": int(row["out_degree"]),
                "neighbor_count": int(row["neighbor_count"]),
                "top_countries_json": row["top_countries"],
                "top_units_json": row["top_units"],
            }
            for row in central_concepts
        ],
    )

    conn.executemany(
        """
        INSERT INTO concept_index VALUES (
            :concept_id, :label, :plain_label, :subtitle, :aliases_json,
            :bucket_hint, :instance_support, :distinct_paper_support,
            :weighted_degree, :pagerank, :in_degree, :out_degree,
            :neighbor_count, :top_countries_json, :top_units_json,
            :search_terms_json, :app_link
        )
        """,
        [
            {
                "concept_id": row["concept_id"],
                "label": row["label"],
                "plain_label": row.get("plain_label", ""),
                "subtitle": row.get("subtitle", ""),
                "aliases_json": sqlite_json(row.get("aliases", [])),
                "bucket_hint": row.get("bucket_hint", ""),
                "instance_support": int(row.get("instance_support", 0)),
                "distinct_paper_support": int(row.get("distinct_paper_support", 0)),
                "weighted_degree": float(row.get("weighted_degree", 0.0)),
                "pagerank": float(row.get("pagerank", 0.0)),
                "in_degree": int(row.get("in_degree", 0)),
                "out_degree": int(row.get("out_degree", 0)),
                "neighbor_count": int(row.get("neighbor_count", 0)),
                "top_countries_json": sqlite_json(row.get("top_countries", [])),
                "top_units_json": sqlite_json(row.get("top_units", [])),
                "search_terms_json": sqlite_json(row.get("search_terms", [])),
                "app_link": row.get("app_link", ""),
            }
            for row in concept_index
        ],
    )

    conn.executemany(
        """
        INSERT INTO graph_nodes VALUES (
            :id, :label, :plain_label, :subtitle, :aliases_json, :alias_count,
            :bucket_hint, :instance_support, :distinct_paper_support, :x, :y,
            :weighted_degree, :pagerank, :in_degree, :out_degree, :neighbor_count,
            :bucket_group, :show_label
        )
        """,
        [
            {
                **row,
                "aliases_json": sqlite_json(row.get("aliases", [])),
                "show_label": int(bool(row.get("show_label", False))),
            }
            for row in graph_backbone.get("nodes", [])
        ],
    )
    conn.executemany(
        """
        INSERT INTO graph_edges VALUES (
            :id, :source, :target, :support_count, :distinct_papers,
            :avg_stability, :strength, :directionality_mix_json,
            :relationship_type_mix_json, :edge_role_mix_json,
            :dominant_countries_json, :dominant_units_json, :dominant_years_json,
            :examples_json
        )
        """,
        [
            {
                **row,
                "directionality_mix_json": sqlite_json(row.get("directionality_mix", [])),
                "relationship_type_mix_json": sqlite_json(row.get("relationship_type_mix", [])),
                "edge_role_mix_json": sqlite_json(row.get("edge_role_mix", [])),
                "dominant_countries_json": sqlite_json(row.get("dominant_countries", [])),
                "dominant_units_json": sqlite_json(row.get("dominant_units", [])),
                "dominant_years_json": sqlite_json(row.get("dominant_years", [])),
                "examples_json": sqlite_json(row.get("examples", [])),
            }
            for row in graph_backbone.get("edges", [])
        ],
    )

    for slice_name, rows in opportunity_slices.items():
        conn.executemany(
            "INSERT INTO opportunity_slices VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    slice_name,
                    rank,
                    row.get("pair_key", ""),
                    float(row.get("score", 0.0)),
                    row.get("source_label", ""),
                    row.get("target_label", ""),
                    sqlite_json(row),
                )
                for rank, row in enumerate(rows, start=1)
            ],
        )

    concept_shard_cache: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for concept_id, public_path in concept_opportunities_index.items():
        shard_key = str(public_path)
        if shard_key not in concept_shard_cache:
            concept_shard_cache[shard_key] = read_json(shard_path_from_public_url(shard_key))
        concept_rows = concept_shard_cache[shard_key].get(concept_id, [])
        conn.executemany(
            "INSERT INTO concept_opportunities VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    concept_id,
                    rank,
                    row.get("pair_key", ""),
                    float(row.get("score", 0.0)),
                    row.get("source_label", ""),
                    row.get("target_label", ""),
                    sqlite_json(row),
                )
                for rank, row in enumerate(concept_rows, start=1)
            ],
        )

    neighborhood_shard_cache: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
    for concept_id, public_path in neighborhoods_index.items():
        shard_key = str(public_path)
        if shard_key not in neighborhood_shard_cache:
            neighborhood_shard_cache[shard_key] = read_json(shard_path_from_public_url(shard_key))
        neighborhood = neighborhood_shard_cache[shard_key].get(concept_id, {})
        for direction in ("incoming", "outgoing", "top_neighbors"):
            rows = neighborhood.get(direction, [])
            conn.executemany(
                "INSERT INTO concept_neighborhoods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        concept_id,
                        direction,
                        rank,
                        row.get("concept_id", ""),
                        row.get("label", ""),
                        int(row.get("support_count", 0)),
                        int(row.get("distinct_papers", 0)),
                        float(row.get("avg_stability", 0.0)),
                        sqlite_json(row),
                    )
                    for rank, row in enumerate(rows, start=1)
                ],
            )

    conn.executemany(
        "INSERT OR REPLACE INTO release_meta(key, value) VALUES (?, ?)",
        [
            ("hybrid_manifest", sqlite_json(hybrid_manifest)),
            ("graph_counts", sqlite_json(graph_backbone.get("counts", {}))),
        ],
    )

    label_lookup = label_lookup_from_assets(concept_index, graph_backbone, central_concepts)

    source_conn = sqlite3.connect(source_db_path)
    source_conn.row_factory = sqlite3.Row

    full_question_rows: dict[str, dict[str, Any]] = {}
    for row in source_conn.execute("SELECT * FROM candidates ORDER BY rank"):
        source_id = str(row["u"])
        target_id = str(row["v"])
        source_plain = label_lookup.get(source_id, str(row["u_preferred_label"] or source_id))
        target_plain = label_lookup.get(target_id, str(row["v_preferred_label"] or target_id))
        top_source = top_values_from_json(row["u_top_countries"])
        top_target = top_values_from_json(row["v_top_countries"])
        top_mediator_labels = [
            label_lookup.get(str(item.get("mediator", "")), str(item.get("mediator", "")))
            for item in parse_json_list(row["top_mediators_json"])[:3]
            if isinstance(item, dict) and str(item.get("mediator", "")).strip()
        ]
        source_context_summary = plain_context(top_source, "No dominant source setting in the current public sample")
        target_context_summary = plain_context(top_target, "No dominant target setting in the current public sample")
        prepared = {
            "pair_key": str(row["pair_key"]),
            "source_id": source_id,
            "target_id": target_id,
            "source_label": str(row["u_preferred_label"] or source_plain),
            "target_label": str(row["v_preferred_label"] or target_plain),
            "source_bucket": str(row["u_bucket_hint"] or ""),
            "target_bucket": str(row["v_bucket_hint"] or ""),
            "cross_field": int(str(row["u_bucket_hint"] or "") != str(row["v_bucket_hint"] or "")),
            "score": float(row["score"] if row["score"] is not None else row["final_score"] or row["base_score"] or 0.0),
            "base_score": float(row["base_score"] or row["score"] or 0.0),
            "duplicate_penalty": float(row["duplicate_penalty"] or 0.0),
            "path_support_norm": float(row["path_support_norm"] or 0.0),
            "gap_bonus": float(row["gap_bonus"] or 0.0),
            "mediator_count": int(row["mediator_count"] or 0),
            "motif_count": int(row["motif_count"] or 0),
            "cooc_count": int(row["cooc_count"] or 0),
            "direct_link_status": direct_literature_status(int(row["cooc_count"] or 0)),
            "supporting_path_count": int(row["mediator_count"] or 0),
            "why_now": why_now(row, source_plain, target_plain),
            "recommended_move": recommendation_play(row),
            "slice_label": slice_label(row),
            "public_pair_label": f"{source_plain} and {target_plain}",
            "question_family": "",
            "suppress_from_public_ranked_window": 0,
            "top_mediator_labels_json": sqlite_json(top_mediator_labels),
            "representative_papers_json": "[]",
            "top_countries_source_json": sqlite_json(top_source),
            "top_countries_target_json": sqlite_json(top_target),
            "source_context_summary": source_context_summary,
            "target_context_summary": target_context_summary,
            "common_contexts": f"Source-side settings most often mention {source_context_summary}. Target-side settings most often mention {target_context_summary}.",
            "app_link": f"{site_data['app_url']}?view=question&pair={row['pair_key']}",
        }
        existing = full_question_rows.get(prepared["pair_key"])
        if existing is None or prepared["score"] > existing["score"]:
            full_question_rows[prepared["pair_key"]] = prepared

    conn.executemany(
        """
        INSERT INTO questions VALUES (
            :pair_key, :source_id, :target_id, :source_label, :target_label,
            :source_bucket, :target_bucket, :cross_field, :score, :base_score,
            :duplicate_penalty, :path_support_norm, :gap_bonus, :mediator_count,
            :motif_count, :cooc_count, :direct_link_status, :supporting_path_count,
            :why_now, :recommended_move, :slice_label, :public_pair_label,
            :question_family, :suppress_from_public_ranked_window, :top_mediator_labels_json,
            :representative_papers_json, :top_countries_source_json, :top_countries_target_json,
            :source_context_summary, :target_context_summary, :common_contexts, :app_link
        )
        """,
        full_question_rows.values(),
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO question_mediators VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                str(row["pair_key"]),
                int(row["rank"]),
                str(row["mediator_concept_id"]),
                str(row["mediator_label"]),
                float(row["score"]),
            )
            for row in source_conn.execute(
                """
                SELECT
                    c.pair_key AS pair_key,
                    cm.rank AS rank,
                    cm.mediator AS mediator_concept_id,
                    COALESCE(nd.preferred_label, n.label, cm.mediator) AS mediator_label,
                    cm.score AS score
                FROM candidate_mediators cm
                INNER JOIN candidates c
                    ON cm.candidate_u = c.u AND cm.candidate_v = c.v
                LEFT JOIN node_details nd
                    ON cm.mediator = nd.concept_id
                LEFT JOIN nodes n
                    ON cm.mediator = n.code
                ORDER BY c.rank, cm.rank
                """
            )
        ],
    )

    question_paths_payload: list[tuple[str, int, int, float, str, str, str]] = []
    for row in source_conn.execute(
        """
        SELECT
            c.pair_key AS pair_key,
            cp.rank AS rank,
            cp.path_len AS path_len,
            cp.path_score AS path_score,
            cp.path_text AS path_text,
            cp.path_nodes_json AS path_nodes_json
        FROM candidate_paths cp
        INNER JOIN candidates c
            ON cp.candidate_u = c.u AND cp.candidate_v = c.v
        ORDER BY c.rank, cp.rank
        """
    ):
        path_nodes = [str(value) for value in parse_json_list(row["path_nodes_json"])]
        path_labels = [label_lookup.get(node_id, node_id) for node_id in path_nodes]
        question_paths_payload.append(
            (
                str(row["pair_key"]),
                int(row["rank"]),
                int(row["path_len"]),
                float(row["path_score"]),
                str(row["path_text"]),
                sqlite_json(path_nodes),
                sqlite_json(path_labels),
            )
        )
    conn.executemany("INSERT OR REPLACE INTO question_paths VALUES (?, ?, ?, ?, ?, ?, ?)", question_paths_payload)

    conn.executemany(
        """
        INSERT OR REPLACE INTO question_papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(row["pair_key"]),
                int(row["path_rank"]),
                int(row["paper_rank"]),
                str(row["paper_id"]),
                str(row["title"]),
                int(row["year"]) if row["year"] is not None else 0,
                str(row["edge_src"]),
                label_lookup.get(str(row["edge_src"]), str(row["edge_src"])),
                str(row["edge_dst"]),
                label_lookup.get(str(row["edge_dst"]), str(row["edge_dst"])),
            )
            for row in source_conn.execute(
                """
                SELECT
                    c.pair_key AS pair_key,
                    cp.path_rank AS path_rank,
                    cp.paper_rank AS paper_rank,
                    cp.paper_id AS paper_id,
                    cp.title AS title,
                    cp.year AS year,
                    cp.edge_src AS edge_src,
                    cp.edge_dst AS edge_dst
                FROM candidate_papers cp
                INNER JOIN candidates c
                    ON cp.candidate_u = c.u AND cp.candidate_v = c.v
                ORDER BY c.rank, cp.path_rank, cp.paper_rank
                """
            )
        ],
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO question_neighborhoods VALUES (?, ?, ?)
        """,
        [
            (
                str(row["pair_key"]),
                str(row["top_out_neighbors_u_json"]),
                str(row["top_in_neighbors_v_json"]),
            )
            for row in source_conn.execute(
                """
                SELECT
                    c.pair_key AS pair_key,
                    cn.top_out_neighbors_u_json AS top_out_neighbors_u_json,
                    cn.top_in_neighbors_v_json AS top_in_neighbors_v_json
                FROM candidate_neighborhoods cn
                INNER JOIN candidates c
                    ON cn.candidate_u = c.u AND cn.candidate_v = c.v
                ORDER BY c.rank
                """
            )
        ],
    )
    source_conn.close()

    conn.commit()
    conn.close()

    sha256 = sha256_file(output_path)
    return output_path.stat().st_size, sha256


def update_release_artifacts(size_bytes: int, sha256: str, public_url: str) -> None:
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "filename": "frontiergraph-economics-public.db",
        "db_size_bytes": size_bytes,
        "db_size_gb": round(size_bytes / (1024**3), 2),
        "sha256": sha256,
        "public_url": public_url,
        "published_at": read_json(GENERATED_SITE_DATA_PATH)["generated_at"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    CHECKSUM_PATH.write_text(f"{sha256}  frontiergraph-economics-public.db\n", encoding="utf-8")

    site_data = read_json(GENERATED_SITE_DATA_PATH)
    site_data["downloads"]["public_db"] = {
        "filename": "frontiergraph-economics-public.db",
        "public_url": public_url,
        "sha256": sha256,
        "db_size_gb": round(size_bytes / (1024**3), 2),
    }
    GENERATED_SITE_DATA_PATH.write_text(json.dumps(site_data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    public_url = os.environ.get("FRONTIERGRAPH_PUBLIC_DB_URL", DEFAULT_PUBLIC_URL)
    size_bytes, sha256 = build_release_bundle(OUTPUT_DB_PATH, SOURCE_DB_PATH)
    update_release_artifacts(size_bytes, sha256, public_url)
    print(
        json.dumps(
            {
                "output_db": str(OUTPUT_DB_PATH),
                "source_db": str(SOURCE_DB_PATH),
                "public_url": public_url,
                "db_size_bytes": size_bytes,
                "db_size_gb": round(size_bytes / (1024**3), 2),
                "sha256": sha256,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
