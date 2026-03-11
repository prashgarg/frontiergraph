from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path


DEFAULT_DB = "data/processed/openalex/published_enriched/openalex_published_enriched.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-year FrontierGraph extraction-ready JSONL files from the materialized enriched SQLite corpus.")
    parser.add_argument("--db-path", default=DEFAULT_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--from-year", type=int, default=None)
    parser.add_argument("--to-year", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db_path)
    conn.row_factory = sqlite3.Row

    year_sql = """
        SELECT DISTINCT wb.publication_year
        FROM works_base wb
        JOIN works_abstracts wa ON wa.work_id = wb.work_id
        WHERE wb.frontiergraph_bucket IN ('core', 'adjacent')
          AND wa.abstract_ready_for_extraction = 1
          AND wb.publication_year IS NOT NULL
    """
    params: list[int] = []
    if args.from_year is not None:
        year_sql += " AND wb.publication_year >= ?"
        params.append(args.from_year)
    if args.to_year is not None:
        year_sql += " AND wb.publication_year <= ?"
        params.append(args.to_year)
    year_sql += " ORDER BY wb.publication_year DESC"
    years = [int(row[0]) for row in conn.execute(year_sql, params)]

    for year in years:
        rows = conn.execute(
            """
            SELECT
                wb.work_id,
                wb.publication_year,
                wb.title,
                COALESCE(wb.display_name, wb.title) AS display_name,
                wb.cited_by_count,
                wb.frontiergraph_bucket,
                wb.frontiergraph_source_name,
                wb.source_id,
                wa.abstract_text,
                wa.abstract_word_count,
                wa.abstract_quality
            FROM works_base wb
            JOIN works_abstracts wa ON wa.work_id = wb.work_id
            WHERE wb.publication_year = ?
              AND wb.frontiergraph_bucket IN ('core', 'adjacent')
              AND wa.abstract_ready_for_extraction = 1
            ORDER BY wb.frontiergraph_bucket, wb.cited_by_count DESC, wb.work_id
            """,
            (year,),
        ).fetchall()

        out_jsonl = output_root / f"published_{year}_ready.jsonl"
        manifest_path = output_root / f"published_{year}_ready_manifest.json"

        bucket_counts = Counter()
        quality_counts = Counter()

        with out_jsonl.open("w", encoding="utf-8") as handle:
            for row in rows:
                bucket_counts[row["frontiergraph_bucket"]] += 1
                quality_counts[row["abstract_quality"]] += 1
                payload = {
                    "openalex_work_id": row["work_id"],
                    "work_id_short": row["work_id"].rstrip("/").split("/")[-1],
                    "publication_year": row["publication_year"],
                    "bucket": row["frontiergraph_bucket"],
                    "title": row["title"] or row["display_name"] or "",
                    "abstract": row["abstract_text"] or "",
                    "abstract_word_count": row["abstract_word_count"],
                    "abstract_quality": row["abstract_quality"],
                    "cited_by_count": row["cited_by_count"],
                    "source_name": row["frontiergraph_source_name"],
                    "source_id": row["source_id"],
                }
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

        manifest = {
            "publication_year": year,
            "db_path": args.db_path,
            "output_jsonl": str(out_jsonl),
            "row_count": len(rows),
            "bucket_counts": dict(sorted(bucket_counts.items())),
            "sample_abstract_quality": dict(sorted(quality_counts.items())),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{year}: wrote {len(rows)} rows -> {out_jsonl}")

    conn.close()


if __name__ == "__main__":
    main()
