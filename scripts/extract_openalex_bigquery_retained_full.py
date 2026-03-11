from __future__ import annotations

import argparse
import csv
import gzip
import json
import time
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from google.cloud import bigquery
from google.oauth2 import service_account


DEFAULT_KEY = "../key/bigquery/patbis-2d3dff5b922f.json"
DEFAULT_PROJECT = "patbis"
DEFAULT_TABLE = "patbis.fromOpenAlex.works"
DEFAULT_DESTINATION_DATASET = "temp"
DEFAULT_CORE = "data/processed/openalex/published_journal_corpora/published_core_econ.jsonl.gz"
DEFAULT_ADJACENT = "data/processed/openalex/published_journal_corpora/published_adjacent_econ_relevant.jsonl.gz"
DEFAULT_EXISTING_SHARD = "data/raw/openalex_enriched/bigquery_snapshot_retained_full.jsonl.gz"
DEFAULT_VALID_EXISTING_OUT = "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_valid_existing.jsonl.gz"
DEFAULT_RECOVERY_OUT = "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_missing.jsonl.gz"
DEFAULT_MANIFEST = "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_missing_manifest.json"

WORK_JSON_SQL = """
TO_JSON_STRING(STRUCT(
  w.id, w.doi, w.display_name, w.title, w.publication_year, w.publication_date, w.language,
  w.ids, w.primary_location, w.best_oa_location, w.type, w.type_crossref,
  w.topics, w.primary_topic, w.open_access, w.authorships,
  w.corresponding_author_ids, w.corresponding_institution_ids,
  w.cited_by_count, w.summary_stats, w.biblio,
  w.is_retracted, w.is_paratext, w.fulltext_origin, w.has_fulltext, w.fwci,
  w.mesh, w.locations_count, w.locations, w.referenced_works_count, w.indexed_in,
  w.sustainable_development_goals, w.grants, w.apc_list, w.apc_paid,
  w.abstract_inverted_index, w.counts_by_year, w.cited_by_api_url, w.keywords,
  w.updated_date, w.created_date, w.authors_count, w.topics_count,
  w.institutions_distinct_count, w.countries_distinct_count
)) AS work_json
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover retained OpenAlex works from BigQuery by exact work ID.")
    parser.add_argument("--key-path", default=DEFAULT_KEY)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--destination-dataset", default=DEFAULT_DESTINATION_DATASET)
    parser.add_argument("--destination-table-prefix", default="frontiergraph_openalex_retained_missing")
    parser.add_argument("--core-path", default=DEFAULT_CORE)
    parser.add_argument("--adjacent-path", default=DEFAULT_ADJACENT)
    parser.add_argument("--max-publication-year", type=int, default=2023)
    parser.add_argument("--existing-shard", default=DEFAULT_EXISTING_SHARD)
    parser.add_argument("--valid-existing-out", default=DEFAULT_VALID_EXISTING_OUT)
    parser.add_argument("--out-path", default=DEFAULT_RECOVERY_OUT)
    parser.add_argument("--manifest-path", default=DEFAULT_MANIFEST)
    parser.add_argument("--progress-every", type=int, default=10000)
    parser.add_argument("--page-size", type=int, default=10000)
    parser.add_argument("--gzip-compresslevel", type=int, default=1)
    parser.add_argument("--keep-temp-tables", action="store_true")
    return parser.parse_args()


def iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_retained_works(core_path: Path, adjacent_path: Path, max_publication_year: int | None) -> dict[str, dict[str, str]]:
    retained: dict[str, dict[str, str]] = {}
    for path in (core_path, adjacent_path):
        for row in iter_jsonl_gz(path):
            publication_year = int(row.get("publication_year") or 0)
            if max_publication_year is not None and publication_year > max_publication_year:
                continue
            retained[row["id"]] = {
                "frontiergraph_bucket": str(row.get("frontiergraph_bucket") or ""),
                "frontiergraph_source_id": str(row.get("frontiergraph_source_id") or ""),
                "frontiergraph_source_name": str(row.get("frontiergraph_source_name") or ""),
                "frontiergraph_source_type": str(row.get("frontiergraph_source_type") or ""),
                "frontiergraph_decision_source": str(row.get("frontiergraph_decision_source") or ""),
                "frontiergraph_decision_reason": str(row.get("frontiergraph_decision_reason") or ""),
                "frontiergraph_manual_notes": str(row.get("frontiergraph_manual_notes") or ""),
                "publication_year": str(publication_year),
            }
    return retained


def salvage_existing_valid_rows(
    *,
    existing_shard: Path,
    valid_existing_out: Path,
    retained: dict[str, dict[str, str]],
    compresslevel: int,
) -> tuple[set[str], dict[str, int]]:
    valid_ids: set[str] = set()
    stats = {
        "existing_rows_total": 0,
        "existing_rows_valid": 0,
        "existing_rows_duplicate_valid": 0,
        "existing_rows_invalid": 0,
    }
    if not existing_shard.exists():
        return valid_ids, stats

    valid_existing_out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(existing_shard, "rt", encoding="utf-8") as src, gzip.open(
        valid_existing_out, "wt", encoding="utf-8", compresslevel=compresslevel
    ) as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            stats["existing_rows_total"] += 1
            row = json.loads(line)
            work_id = row.get("id")
            if work_id not in retained:
                stats["existing_rows_invalid"] += 1
                continue
            if work_id in valid_ids:
                stats["existing_rows_duplicate_valid"] += 1
                continue
            valid_ids.add(work_id)
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
            stats["existing_rows_valid"] += 1
    return valid_ids, stats


def write_missing_ids_csv(path: Path, retained: dict[str, dict[str, str]], valid_ids: set[str]) -> int:
    fieldnames = [
        "work_id",
        "frontiergraph_bucket",
        "frontiergraph_source_id",
        "frontiergraph_source_name",
        "frontiergraph_source_type",
        "frontiergraph_decision_source",
        "frontiergraph_decision_reason",
        "frontiergraph_manual_notes",
    ]
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for work_id in sorted(retained):
            if work_id in valid_ids:
                continue
            meta = retained[work_id]
            writer.writerow(
                {
                    "work_id": work_id,
                    "frontiergraph_bucket": meta["frontiergraph_bucket"],
                    "frontiergraph_source_id": meta["frontiergraph_source_id"],
                    "frontiergraph_source_name": meta["frontiergraph_source_name"],
                    "frontiergraph_source_type": meta["frontiergraph_source_type"],
                    "frontiergraph_decision_source": meta["frontiergraph_decision_source"],
                    "frontiergraph_decision_reason": meta["frontiergraph_decision_reason"],
                    "frontiergraph_manual_notes": meta["frontiergraph_manual_notes"],
                }
            )
            count += 1
    return count


def main() -> None:
    args = parse_args()
    key_path = Path(args.key_path).resolve()
    out_path = Path(args.out_path)
    valid_existing_out = Path(args.valid_existing_out)
    manifest_path = Path(args.manifest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    retained = load_retained_works(
        Path(args.core_path),
        Path(args.adjacent_path),
        args.max_publication_year,
    )
    if not retained:
        raise SystemExit("No retained works loaded for the requested publication-year window.")

    valid_ids, salvage_stats = salvage_existing_valid_rows(
        existing_shard=Path(args.existing_shard),
        valid_existing_out=valid_existing_out,
        retained=retained,
        compresslevel=args.gzip_compresslevel,
    )

    with NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False) as temp_csv_handle:
        temp_csv_path = Path(temp_csv_handle.name)
    missing_count = write_missing_ids_csv(temp_csv_path, retained, valid_ids)

    credentials = service_account.Credentials.from_service_account_file(str(key_path))
    client = bigquery.Client(project=args.project, credentials=credentials)

    ids_table = f"{args.project}.{args.destination_dataset}.frontiergraph_retained_ids_{uuid4().hex[:12]}"
    result_table = f"{args.project}.{args.destination_dataset}.{args.destination_table_prefix}_{uuid4().hex[:12]}"

    load_job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("work_id", "STRING"),
            bigquery.SchemaField("frontiergraph_bucket", "STRING"),
            bigquery.SchemaField("frontiergraph_source_id", "STRING"),
            bigquery.SchemaField("frontiergraph_source_name", "STRING"),
            bigquery.SchemaField("frontiergraph_source_type", "STRING"),
            bigquery.SchemaField("frontiergraph_decision_source", "STRING"),
            bigquery.SchemaField("frontiergraph_decision_reason", "STRING"),
            bigquery.SchemaField("frontiergraph_manual_notes", "STRING"),
        ],
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with temp_csv_path.open("rb") as handle:
        load_job = client.load_table_from_file(handle, ids_table, job_config=load_job_config)
    print(f"started ID-table load job {load_job.job_id}", flush=True)
    load_job.result()

    sql = f"""
    SELECT
      ids.work_id,
      ids.frontiergraph_bucket,
      ids.frontiergraph_source_id,
      ids.frontiergraph_source_name,
      ids.frontiergraph_source_type,
      ids.frontiergraph_decision_source,
      ids.frontiergraph_decision_reason,
      ids.frontiergraph_manual_notes,
      {WORK_JSON_SQL}
    FROM `{args.table}` AS w
    JOIN `{ids_table}` AS ids
      ON w.id = ids.work_id
    WHERE w.type = 'article'
      AND w.language = 'en'
      AND w.primary_location.source.type = 'journal'
    """

    query_config = bigquery.QueryJobConfig(
        use_query_cache=False,
        destination=result_table,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    query_job = client.query(sql, job_config=query_config)
    print(f"started BigQuery recovery job {query_job.job_id}", flush=True)

    while True:
        query_job.reload()
        if query_job.state == "DONE":
            break
        time.sleep(5)

    if query_job.error_result:
        raise RuntimeError(f"BigQuery recovery job failed: {query_job.error_result}")
    if not query_job.destination:
        raise RuntimeError("BigQuery recovery job completed without a destination table.")

    row_iter = client.list_rows(query_job.destination, page_size=args.page_size)
    recovered_ids: set[str] = set()
    bucket_counts: Counter[str] = Counter()
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=args.gzip_compresslevel) as handle:
        for idx, row in enumerate(row_iter, start=1):
            payload = json.loads(row["work_json"])
            payload["frontiergraph_bucket"] = row["frontiergraph_bucket"]
            payload["frontiergraph_source_id"] = row["frontiergraph_source_id"]
            payload["frontiergraph_source_name"] = row["frontiergraph_source_name"]
            payload["frontiergraph_source_type"] = row["frontiergraph_source_type"]
            payload["frontiergraph_decision_source"] = row["frontiergraph_decision_source"]
            payload["frontiergraph_decision_reason"] = row["frontiergraph_decision_reason"]
            payload["frontiergraph_manual_notes"] = row["frontiergraph_manual_notes"]
            payload["frontiergraph_snapshot_origin"] = "bigquery_2024_snapshot_recovered_by_id"
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            recovered_ids.add(payload["id"])
            bucket_counts[payload["frontiergraph_bucket"]] += 1
            if idx % args.progress_every == 0:
                print(f"wrote {idx} recovered rows", flush=True)

    temp_csv_path.unlink(missing_ok=True)

    manifest = {
        "max_publication_year": args.max_publication_year,
        "expected_retained_rows": len(retained),
        "existing_valid_rows": len(valid_ids),
        "missing_rows_requested": missing_count,
        "recovered_rows_written": len(recovered_ids),
        "bucket_counts_recovered": dict(bucket_counts),
        "existing_valid_out": str(valid_existing_out),
        "recovery_output_path": str(out_path),
        "ids_table": ids_table,
        "result_table": result_table,
        **salvage_stats,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

    if not args.keep_temp_tables:
        client.delete_table(ids_table, not_found_ok=True)
        client.delete_table(result_table, not_found_ok=True)


if __name__ == "__main__":
    main()
