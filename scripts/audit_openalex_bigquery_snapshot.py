from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account


DEFAULT_KEY = "../key/bigquery/patbis-2d3dff5b922f.json"
DEFAULT_PROJECT = "patbis"
DEFAULT_TABLE = "patbis.fromOpenAlex.works"
DEFAULT_REGISTRY = "data/raw/openalex/journal_field20_metadata/source_registry.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit OpenAlex BigQuery snapshot freshness and dry-run extract cost.")
    parser.add_argument("--key-path", default=DEFAULT_KEY)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--registry-csv", default=DEFAULT_REGISTRY)
    return parser.parse_args()


def load_client(project: str, key_path: Path) -> bigquery.Client:
    credentials = service_account.Credentials.from_service_account_file(str(key_path))
    return bigquery.Client(project=project, credentials=credentials)


def load_retained_source_ids(path: Path) -> list[str]:
    source_ids: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["final_bucket"] in {"core", "adjacent"}:
                source_ids.append(row["source_id"])
    return sorted(set(source_ids))


def dry_run_bytes(client: bigquery.Client, sql: str, source_ids: list[str]) -> int:
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        query_parameters=[bigquery.ArrayQueryParameter("source_ids", "STRING", source_ids)],
    )
    job = client.query(sql, job_config=job_config)
    return int(job.total_bytes_processed or 0)


def bytes_summary(n_bytes: int) -> dict[str, float]:
    return {
        "bytes": n_bytes,
        "gib": round(n_bytes / (1024**3), 3),
        "tib": round(n_bytes / (1024**4), 3),
        "on_demand_usd_at_6_25_per_tib": round((n_bytes / (1024**4)) * 6.25, 2),
    }


def main() -> None:
    args = parse_args()
    key_path = Path(args.key_path).resolve()
    registry_csv = Path(args.registry_csv)
    client = load_client(args.project, key_path)

    table = client.get_table(args.table)
    retained_source_ids = load_retained_source_ids(registry_csv)

    freshness_sql = f"""
    SELECT
      MAX(publication_date) AS max_publication_date,
      MAX(updated_date) AS max_updated_date,
      MAX(created_date) AS max_created_date,
      MAX(publication_year) AS max_publication_year,
      COUNTIF(publication_year = 2024) AS n_2024,
      COUNTIF(publication_year = 2025) AS n_2025,
      COUNTIF(publication_year = 2026) AS n_2026
    FROM `{args.table}`
    """
    freshness_row = list(client.query(freshness_sql).result())[0]

    full_sql = f"""
    SELECT
      id, doi, display_name, title, publication_year, publication_date, language,
      ids, primary_location, best_oa_location, type, type_crossref,
      topics, primary_topic, open_access, authorships,
      corresponding_author_ids, corresponding_institution_ids,
      cited_by_count, summary_stats, biblio,
      is_retracted, is_paratext, fulltext_origin, has_fulltext, fwci,
      mesh, locations_count, locations,
      referenced_works_count, indexed_in, sustainable_development_goals,
      grants, apc_list, apc_paid,
      abstract_inverted_index, counts_by_year, cited_by_api_url,
      keywords, updated_date, created_date,
      authors_count, topics_count, institutions_distinct_count, countries_distinct_count
    FROM `{args.table}`
    WHERE primary_location.source.id IN UNNEST(@source_ids)
    """
    recent_sql = full_sql + "\nAND publication_date >= DATE(2024, 1, 1)"
    light_sql = f"""
    SELECT
      id, doi, display_name, title, publication_year, publication_date, language,
      primary_location.source.id, primary_location.source.display_name,
      type, open_access, cited_by_count, fwci,
      primary_topic, topics, keywords, updated_date, created_date
    FROM `{args.table}`
    WHERE primary_location.source.id IN UNNEST(@source_ids)
    """

    payload = {
        "table_metadata": {
            "table_id": table.full_table_id,
            "created": table.created.isoformat() if table.created else None,
            "modified": table.modified.isoformat() if table.modified else None,
            "num_rows": table.num_rows,
            "num_bytes": table.num_bytes,
            "clustering_fields": table.clustering_fields,
            "time_partitioning": str(table.time_partitioning) if table.time_partitioning else None,
            "range_partitioning": str(table.range_partitioning) if table.range_partitioning else None,
        },
        "freshness": {k: (str(freshness_row[k]) if freshness_row[k] is not None else None) for k in freshness_row.keys()},
        "retained_source_ids": len(retained_source_ids),
        "dry_run_retained_full": bytes_summary(dry_run_bytes(client, full_sql, retained_source_ids)),
        "dry_run_retained_recent_2024_onward": bytes_summary(dry_run_bytes(client, recent_sql, retained_source_ids)),
        "dry_run_retained_light": bytes_summary(dry_run_bytes(client, light_sql, retained_source_ids)),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
