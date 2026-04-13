from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path

from src.research_allocation_v2 import build_hybrid_corpus, build_hybrid_manifest, load_large_corpus_frames


DEFAULT_EXTRACTION_DB = (
    "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"
)
DEFAULT_ONTOLOGY_DB = "data/production/frontiergraph_ontology_compare_v1/baseline/ontology_v3.sqlite"
DEFAULT_MAPPING_TABLE = "instance_mappings_soft"
DEFAULT_OUT_DIR = "data/processed/research_allocation_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the large-corpus hybrid benchmark for research-allocation v2.")
    parser.add_argument("--extraction-db", default=DEFAULT_EXTRACTION_DB)
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--mapping-table", default=DEFAULT_MAPPING_TABLE)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def fetch_source_counts(extraction_db: Path) -> tuple[int, int, int, int, int]:
    conn = sqlite3.connect(f"file:{extraction_db}?mode=ro", uri=True)
    try:
        source_min_year, source_max_year, source_selected_papers = conn.execute(
            "SELECT MIN(publication_year), MAX(publication_year), COUNT(*) FROM works"
        ).fetchone()
        extracted_min_year, extracted_max_year, extracted_papers, extracted_edges = conn.execute(
            """
            SELECT MIN(w.publication_year), MAX(w.publication_year),
                   COUNT(DISTINCT e.custom_id), COUNT(*)
            FROM edges e
            JOIN works w ON w.custom_id = e.custom_id
            """
        ).fetchone()
    finally:
        conn.close()
    if int(source_min_year) != int(extracted_min_year) or int(source_max_year) != int(extracted_max_year):
        pass
    return (
        int(source_selected_papers),
        int(source_min_year),
        int(source_max_year),
        int(extracted_papers),
        int(extracted_edges),
    )


def main() -> None:
    args = parse_args()
    extraction_db = Path(args.extraction_db)
    ontology_db = Path(args.ontology_db)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    source_selected_papers, source_min_year, source_max_year, extracted_papers, extracted_edges = fetch_source_counts(
        extraction_db
    )
    print(f"[corpus] source counts loaded in {time.perf_counter() - t0:.1f}s", flush=True)
    t1 = time.perf_counter()
    edge_instances = load_large_corpus_frames(
        extraction_db=extraction_db,
        ontology_db=ontology_db,
        mapping_table=args.mapping_table,
    )
    print(f"[corpus] edge instances loaded in {time.perf_counter() - t1:.1f}s ({len(edge_instances)} rows)", flush=True)
    t2 = time.perf_counter()
    hybrid_corpus = build_hybrid_corpus(edge_instances)
    print(f"[corpus] hybrid corpus built in {time.perf_counter() - t2:.1f}s ({len(hybrid_corpus)} rows)", flush=True)
    t3 = time.perf_counter()
    manifest = build_hybrid_manifest(
        hybrid_corpus=hybrid_corpus,
        source_selected_papers=source_selected_papers,
        source_min_year=source_min_year,
        source_max_year=source_max_year,
        extracted_papers=extracted_papers,
        extracted_edges=extracted_edges,
    )
    print(f"[corpus] manifest built in {time.perf_counter() - t3:.1f}s", flush=True)

    corpus_path = out_dir / "hybrid_corpus.parquet"
    manifest_path = out_dir / "hybrid_corpus_manifest.json"
    papers_path = out_dir / "hybrid_papers.parquet"

    t4 = time.perf_counter()
    hybrid_corpus.to_parquet(corpus_path, index=False)
    hybrid_corpus[
        ["paper_id", "year", "title", "authors", "venue", "source"]
    ].drop_duplicates(subset=["paper_id"]).to_parquet(papers_path, index=False)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[corpus] artifacts written in {time.perf_counter() - t4:.1f}s", flush=True)

    print(f"Wrote hybrid corpus: {corpus_path} ({len(hybrid_corpus)} rows)")
    print(f"Wrote hybrid papers: {papers_path}")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
