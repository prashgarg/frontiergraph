from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.frontiergraph_regime_preview_utils import SITE_ROOT, build_broad_preview_dataset, write_csv_rows, write_json


PUBLIC_DATA_DIR = SITE_ROOT / "public" / "data" / "broad-v1"
GENERATED_SITE_DATA_PATH = SITE_ROOT / "src" / "generated" / "site-data-broad.json"
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public" / "downloads"
OUTPUT_DB_PATH = Path(os.environ.get("FRONTIERGRAPH_PUBLIC_RELEASE_DB_BROAD", "/tmp/frontiergraph-economics-broad-preview.db"))
PUBLIC_DB_FILENAME = os.environ.get("FRONTIERGRAPH_PUBLIC_DB_FILENAME_BROAD", OUTPUT_DB_PATH.name)
PUBLIC_DB_URL = os.environ.get("FRONTIERGRAPH_PUBLIC_BROAD_DB_URL", "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_public_files(dataset: dict[str, object]) -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    neighborhoods_dir = PUBLIC_DATA_DIR / "concept_neighborhoods"
    opportunities_dir = PUBLIC_DATA_DIR / "concept_opportunities"
    neighborhoods_dir.mkdir(parents=True, exist_ok=True)
    opportunities_dir.mkdir(parents=True, exist_ok=True)

    questions = dataset["questions"]
    concepts = dataset["concepts"]
    central_concepts = dataset["central_concepts"]

    write_json(PUBLIC_DATA_DIR / "graph_backbone.json", dataset["graph"])
    write_json(PUBLIC_DATA_DIR / "concept_index.json", concepts)
    write_json(PUBLIC_DATA_DIR / "central_concepts.json", central_concepts)
    write_json(PUBLIC_DATA_DIR / "opportunity_slices.json", dataset["top_slices"])

    neighborhoods_path = neighborhoods_dir / "neighborhoods-000.json"
    opportunities_path = opportunities_dir / "opportunities-000.json"
    write_json(neighborhoods_path, dataset["concept_neighborhoods"])
    write_json(opportunities_path, dataset["concept_opportunities"])

    concept_ids = [str(concept["concept_id"]) for concept in concepts]
    write_json(
        PUBLIC_DATA_DIR / "concept_neighborhoods_index.json",
        {concept_id: "/data/broad-v1/concept_neighborhoods/neighborhoods-000.json" for concept_id in concept_ids},
    )
    write_json(
        PUBLIC_DATA_DIR / "concept_opportunities_index.json",
        {concept_id: "/data/broad-v1/concept_opportunities/opportunities-000.json" for concept_id in concept_ids},
    )

    top_question_columns = [
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
        "top_mediator_labels",
        "top_mediator_baseline_labels",
        "representative_papers",
        "top_countries_source",
        "top_countries_target",
        "source_context_summary",
        "target_context_summary",
        "common_contexts",
        "public_specificity_score",
        "app_link",
    ]
    csv_rows: list[dict[str, object]] = []
    for question in questions:
        row = dict(question)
        row["top_mediator_labels"] = json.dumps(question.get("top_mediator_labels", []), ensure_ascii=False)
        row["top_mediator_baseline_labels"] = json.dumps(question.get("top_mediator_baseline_labels", []), ensure_ascii=False)
        row["representative_papers"] = json.dumps(question.get("representative_papers", []), ensure_ascii=False)
        row["top_countries_source"] = json.dumps(question.get("top_countries_source", []), ensure_ascii=False)
        row["top_countries_target"] = json.dumps(question.get("top_countries_target", []), ensure_ascii=False)
        csv_rows.append({column: row.get(column, "") for column in top_question_columns})
    write_csv_rows(PUBLIC_DATA_DIR / "top_questions.csv", csv_rows, top_question_columns)

    central_columns = [
        "concept_id",
        "label",
        "plain_label",
        "subtitle",
        "display_concept_id",
        "display_refined",
        "display_refinement_confidence",
        "alternate_display_labels",
        "bucket_hint",
        "instance_support",
        "distinct_paper_support",
        "weighted_degree",
        "pagerank",
        "in_degree",
        "out_degree",
        "neighbor_count",
        "top_countries",
        "top_units",
        "app_link",
    ]
    central_rows = []
    for concept in central_concepts:
        row = dict(concept)
        row["alternate_display_labels"] = json.dumps(concept.get("alternate_display_labels", []), ensure_ascii=False)
        row["top_countries"] = json.dumps(concept.get("top_countries", []), ensure_ascii=False)
        row["top_units"] = json.dumps(concept.get("top_units", []), ensure_ascii=False)
        central_rows.append({column: row.get(column, "") for column in central_columns})
    write_csv_rows(PUBLIC_DATA_DIR / "central_concepts.csv", central_rows, central_columns)


def build_site_payload(dataset: dict[str, object]) -> dict[str, object]:
    public_db = {
        "filename": PUBLIC_DB_FILENAME,
        "public_url": PUBLIC_DB_URL,
        "sha256": "",
        "db_size_bytes": 0,
        "db_size_gb": 0.0,
    }
    if OUTPUT_DB_PATH.exists():
        public_db["db_size_bytes"] = OUTPUT_DB_PATH.stat().st_size
        public_db["db_size_gb"] = round(OUTPUT_DB_PATH.stat().st_size / (1024 ** 3), 3)
        public_db["sha256"] = sha256_file(OUTPUT_DB_PATH)

    return {
        "generated_at": dataset["generated_at"],
        "app_url": dataset["app_url"],
        "repo_url": dataset["repo_url"],
        "public_label_glossary": {},
        "metrics": dataset["metrics"],
        "home": {
            "featured_questions": dataset["questions"][:6],
            "curated_questions": [],
            "featured_central_concepts": dataset["central_concepts"][:8],
            "graph_snapshot": {
                "nodes": len(dataset["graph"]["nodes"]),
                "edges": len(dataset["graph"]["edges"]),
                "path": "/data/broad-v1/graph_backbone.json",
            },
        },
        "graph": {
            "backbone_path": "/data/broad-v1/graph_backbone.json",
            "concept_index_path": "/data/broad-v1/concept_index.json",
            "concept_neighborhoods_index_path": "/data/broad-v1/concept_neighborhoods_index.json",
            "concept_opportunities_index_path": "/data/broad-v1/concept_opportunities_index.json",
            "central_concepts_path": "/data/broad-v1/central_concepts.json",
        },
        "questions": {
            "slices_path": "/data/broad-v1/opportunity_slices.json",
            "concept_opportunities_index_path": "/data/broad-v1/concept_opportunities_index.json",
            "curated_front_set": [],
            "field_shelves": [],
            "collections": [],
            "field_carousels": dataset["field_carousels"],
            "use_case_carousels": dataset["use_case_carousels"],
            "ranked_questions": dataset["questions"],
            "top_slices": dataset["top_slices"],
        },
        "downloads": {
            "public_db": public_db,
            "checksum_path": "/downloads/frontiergraph-economics-broad-preview.sha256.txt",
            "manifest_path": "/downloads/frontiergraph-economics-broad-preview.manifest.json",
            "guides": {},
            "tier_bundles": {},
            "artifacts": {},
            "artifact_details": {},
        },
    }


def main() -> None:
    dataset = build_broad_preview_dataset(limit=100)
    write_public_files(dataset)
    site_payload = build_site_payload(dataset)
    write_json(GENERATED_SITE_DATA_PATH, site_payload)


if __name__ == "__main__":
    main()
