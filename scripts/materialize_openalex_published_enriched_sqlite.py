from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REGISTRY = "data/raw/openalex/journal_field20_metadata/source_registry.csv"
DEFAULT_BIGQUERY_RAW = "data/raw/openalex_enriched/bigquery_snapshot_retained_full.jsonl.gz"
DEFAULT_API_RECENT_DIR = "data/raw/openalex/journal_field20_full_recent"
DEFAULT_API_OVERLAY = "data/raw/openalex_enriched/openalex_api_recent_retained_overlay.jsonl.gz"
DEFAULT_API_OVERLAY_MANIFEST = "data/raw/openalex_enriched/openalex_api_recent_retained_overlay_manifest.json"
DEFAULT_OUTPUT_DB = "data/processed/openalex/published_enriched/openalex_published_enriched.sqlite"
DEFAULT_OUTPUT_MANIFEST = "data/processed/openalex/published_enriched/openalex_published_enriched_manifest.json"

SIDECAR_TABLES = [
    "works_abstracts",
    "works_topics",
    "works_keywords",
    "works_authorships",
    "works_authorship_institutions",
    "works_locations",
    "works_mesh",
    "works_counts_by_year",
    "works_sdgs",
    "works_grants",
    "works_apc_list",
    "works_apc_paid",
]

PLACEHOLDER_SUBSTRINGS = (
    "an abstract is not available",
    "abstract is not available",
    "no abstract available",
    "please use the get access link",
    "for information on how to access this content",
    "preview has been provided",
)

METADATA_SUBSTRINGS = (
    "clinicaltrials.gov identifier",
    "trial registration",
    "registration number",
    "funded by",
    "supported by",
)

TOKENISH_RE = re.compile(r"[A-Za-z0-9]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize retained OpenAlex published works into a normalized SQLite corpus.")
    parser.add_argument("--registry-csv", default=DEFAULT_REGISTRY)
    parser.add_argument("--bigquery-raw", default=DEFAULT_BIGQUERY_RAW)
    parser.add_argument("--api-recent-dir", default=DEFAULT_API_RECENT_DIR)
    parser.add_argument("--api-overlay-out", default=DEFAULT_API_OVERLAY)
    parser.add_argument("--api-overlay-manifest", default=DEFAULT_API_OVERLAY_MANIFEST)
    parser.add_argument("--output-db", default=DEFAULT_OUTPUT_DB)
    parser.add_argument("--manifest-path", default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--progress-every", type=int, default=10000)
    return parser.parse_args()


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def bool_to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(bool(value))


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def ensure_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return {}


def reconstruct_abstract(abstract_inverted_index: Any) -> tuple[str | None, int]:
    inverted = ensure_dict(abstract_inverted_index)
    if not inverted:
        return None, 0
    max_pos = -1
    for positions in inverted.values():
        for pos in positions:
            if pos > max_pos:
                max_pos = pos
    if max_pos < 0:
        return None, 0
    tokens = [""] * (max_pos + 1)
    for token, positions in inverted.items():
        for pos in positions:
            tokens[pos] = token
    filtered = [token for token in tokens if token]
    if not filtered:
        return None, 0
    return " ".join(filtered), len(filtered)


def classify_abstract_quality(abstract_text: str | None, abstract_word_count: int) -> tuple[str, int, int]:
    if not abstract_text or abstract_word_count == 0:
        return "missing", 0, 0

    normalized = " ".join(abstract_text.split()).strip()
    lowered = normalized.casefold()
    semicolons = normalized.count(";")
    token_count = len(TOKENISH_RE.findall(normalized))

    if lowered in {"none", "none.", "not available", "n/a"}:
        return "placeholder", 0, 0
    if any(needle in lowered for needle in PLACEHOLDER_SUBSTRINGS):
        return "placeholder", 0, 0
    if abstract_word_count < 20 and any(needle in lowered for needle in METADATA_SUBSTRINGS):
        return "metadata_only", 0, 0
    if abstract_word_count < 20 and token_count <= 8 and "." not in normalized and ":" not in normalized:
        return "metadata_only", 0, 0
    if abstract_word_count < 25 and semicolons >= 2:
        return "keyword_list", 0, 0
    if abstract_word_count < 20:
        return "too_short", 0, 0
    if abstract_word_count < 30:
        return "borderline_short", 0, 0
    if abstract_word_count < 50:
        return "usable_short", 1, 1
    return "usable", 1, 1


def normalize_primary_topic(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        return first if isinstance(first, dict) else {}
    return {}


def primary_source(work: dict[str, Any]) -> dict[str, Any]:
    primary_location = ensure_dict(work.get("primary_location"))
    return ensure_dict(primary_location.get("source"))


def load_registry_rows(path: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    rows: list[dict[str, str]] = []
    retained: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
            if row["final_bucket"] in {"core", "adjacent"}:
                retained[row["source_id"]] = row
    return rows, retained


def iter_jsonl_gz(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def build_recent_api_overlay(
    *,
    api_recent_dir: Path,
    registry: dict[str, dict[str, str]],
    overlay_out: Path,
    overlay_manifest_path: Path,
) -> set[str]:
    overlay_out.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "query_type": "retained_openalex_api_overlay",
        "source_files": [],
        "bucket_counts": Counter(),
        "year_counts": Counter(),
        "retained_rows": 0,
        "duplicate_ids_skipped": 0,
        "non_retained_rows_skipped": 0,
    }
    seen_ids: set[str] = set()

    raw_files = sorted(api_recent_dir.glob("openalex_field20_journal_articles_en_full_*.jsonl.gz"))
    with gzip.open(overlay_out, "wt", encoding="utf-8") as out_handle:
        for raw_file in raw_files:
            state["source_files"].append(raw_file.name)
            for work in iter_jsonl_gz(raw_file):
                source_id = ensure_dict(ensure_dict(work.get("primary_location")).get("source")).get("id")
                if source_id not in registry:
                    state["non_retained_rows_skipped"] += 1
                    continue
                work_id = work.get("id")
                if not work_id or work_id in seen_ids:
                    state["duplicate_ids_skipped"] += 1
                    continue
                seen_ids.add(work_id)
                registry_row = registry[source_id]
                work["frontiergraph_bucket"] = registry_row["final_bucket"]
                work["frontiergraph_source_id"] = source_id
                work["frontiergraph_source_name"] = registry_row["source_name"]
                work["frontiergraph_source_type"] = registry_row["source_type"]
                work["frontiergraph_decision_source"] = registry_row["decision_source"]
                work["frontiergraph_decision_reason"] = registry_row["decision_reason"]
                work["frontiergraph_manual_notes"] = registry_row["manual_notes"]
                work["frontiergraph_snapshot_origin"] = "openalex_api_recent"
                out_handle.write(json.dumps(work, ensure_ascii=False) + "\n")
                state["retained_rows"] += 1
                state["bucket_counts"][registry_row["final_bucket"]] += 1
                if work.get("publication_year"):
                    state["year_counts"][int(work["publication_year"])] += 1

    overlay_manifest = {
        **state,
        "bucket_counts": dict(state["bucket_counts"]),
        "year_counts": dict(sorted(state["year_counts"].items())),
        "overlay_output_path": str(overlay_out),
    }
    overlay_manifest_path.write_text(json.dumps(overlay_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return seen_ids


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")
    conn.executescript(
        """
        DROP TABLE IF EXISTS source_registry;
        DROP TABLE IF EXISTS works_base;
        DROP TABLE IF EXISTS works_abstracts;
        DROP TABLE IF EXISTS works_topics;
        DROP TABLE IF EXISTS works_keywords;
        DROP TABLE IF EXISTS works_authorships;
        DROP TABLE IF EXISTS works_authorship_institutions;
        DROP TABLE IF EXISTS works_locations;
        DROP TABLE IF EXISTS works_mesh;
        DROP TABLE IF EXISTS works_counts_by_year;
        DROP TABLE IF EXISTS works_sdgs;
        DROP TABLE IF EXISTS works_grants;
        DROP TABLE IF EXISTS works_apc_list;
        DROP TABLE IF EXISTS works_apc_paid;

        CREATE TABLE source_registry (
            source_id TEXT PRIMARY KEY,
            source_name TEXT,
            source_type TEXT,
            works_count INTEGER,
            first_year INTEGER,
            last_year INTEGER,
            total_citations INTEGER,
            top_subfields TEXT,
            normalized_name TEXT,
            final_bucket TEXT,
            decision_source TEXT,
            decision_reason TEXT,
            manual_notes TEXT
        );

        CREATE TABLE works_base (
            work_id TEXT PRIMARY KEY,
            doi TEXT,
            display_name TEXT,
            title TEXT,
            publication_year INTEGER,
            publication_date TEXT,
            language TEXT,
            type TEXT,
            type_crossref TEXT,
            source_id TEXT,
            source_display_name TEXT,
            source_type TEXT,
            source_issn_l TEXT,
            source_issn_json TEXT,
            source_host_organization TEXT,
            source_host_organization_name TEXT,
            source_host_organization_lineage_json TEXT,
            source_is_oa INTEGER,
            source_is_in_doaj INTEGER,
            source_is_core INTEGER,
            primary_topic_id TEXT,
            primary_topic_display_name TEXT,
            primary_topic_score REAL,
            primary_subfield_id TEXT,
            primary_subfield_display_name TEXT,
            primary_field_id TEXT,
            primary_field_display_name TEXT,
            primary_domain_id TEXT,
            primary_domain_display_name TEXT,
            frontiergraph_bucket TEXT,
            frontiergraph_source_name TEXT,
            frontiergraph_source_type TEXT,
            frontiergraph_decision_source TEXT,
            frontiergraph_decision_reason TEXT,
            frontiergraph_manual_notes TEXT,
            frontiergraph_snapshot_origin TEXT,
            open_access_is_oa INTEGER,
            open_access_status TEXT,
            open_access_url TEXT,
            any_repository_has_fulltext INTEGER,
            primary_location_is_oa INTEGER,
            primary_pdf_url TEXT,
            primary_landing_page_url TEXT,
            primary_version TEXT,
            primary_license TEXT,
            best_oa_is_oa INTEGER,
            best_oa_pdf_url TEXT,
            best_oa_landing_page_url TEXT,
            best_oa_version TEXT,
            best_oa_license TEXT,
            cited_by_count INTEGER,
            summary_2yr_cited_by_count INTEGER,
            fwci REAL,
            referenced_works_count INTEGER,
            locations_count INTEGER,
            authors_count INTEGER,
            topics_count INTEGER,
            institutions_distinct_count INTEGER,
            countries_distinct_count INTEGER,
            corresponding_author_ids_json TEXT,
            corresponding_institution_ids_json TEXT,
            indexed_in_json TEXT,
            ids_json TEXT,
            biblio_json TEXT,
            summary_stats_json TEXT,
            primary_location_json TEXT,
            best_oa_location_json TEXT,
            open_access_json TEXT,
            citation_normalized_percentile_json TEXT,
            cited_by_percentile_year_json TEXT,
            awards_json TEXT,
            content_urls_json TEXT,
            is_retracted INTEGER,
            is_paratext INTEGER,
            fulltext_origin TEXT,
            has_fulltext INTEGER,
            cited_by_api_url TEXT,
            updated_date TEXT,
            created_date TEXT
        );

        CREATE TABLE works_abstracts (
            work_id TEXT PRIMARY KEY,
            has_abstract INTEGER,
            abstract_word_count INTEGER,
            abstract_quality TEXT,
            abstract_is_placeholder INTEGER,
            abstract_ready_for_extraction INTEGER,
            abstract_text TEXT,
            abstract_inverted_index_json TEXT
        );

        CREATE TABLE works_topics (
            work_id TEXT,
            topic_seq INTEGER,
            topic_id TEXT,
            display_name TEXT,
            score REAL,
            subfield_id TEXT,
            subfield_display_name TEXT,
            field_id TEXT,
            field_display_name TEXT,
            domain_id TEXT,
            domain_display_name TEXT,
            PRIMARY KEY (work_id, topic_seq)
        );

        CREATE TABLE works_keywords (
            work_id TEXT,
            keyword_seq INTEGER,
            keyword_id TEXT,
            display_name TEXT,
            score REAL,
            PRIMARY KEY (work_id, keyword_seq)
        );

        CREATE TABLE works_authorships (
            work_id TEXT,
            author_seq INTEGER,
            author_position TEXT,
            author_id TEXT,
            author_display_name TEXT,
            is_corresponding INTEGER,
            raw_author_string TEXT,
            countries_json TEXT,
            raw_affiliation_strings_json TEXT,
            PRIMARY KEY (work_id, author_seq)
        );

        CREATE TABLE works_authorship_institutions (
            work_id TEXT,
            author_seq INTEGER,
            institution_seq INTEGER,
            institution_id TEXT,
            ror TEXT,
            display_name TEXT,
            country_code TEXT,
            type TEXT,
            lineage_json TEXT,
            PRIMARY KEY (work_id, author_seq, institution_seq)
        );

        CREATE TABLE works_locations (
            work_id TEXT,
            location_seq INTEGER,
            source_id TEXT,
            source_display_name TEXT,
            source_type TEXT,
            source_issn_l TEXT,
            source_issn_json TEXT,
            source_host_organization TEXT,
            source_host_organization_name TEXT,
            source_is_oa INTEGER,
            source_is_in_doaj INTEGER,
            source_is_core INTEGER,
            pdf_url TEXT,
            landing_page_url TEXT,
            is_oa INTEGER,
            version TEXT,
            license TEXT,
            PRIMARY KEY (work_id, location_seq)
        );

        CREATE TABLE works_mesh (
            work_id TEXT,
            mesh_seq INTEGER,
            is_major_topic INTEGER,
            descriptor_ui TEXT,
            descriptor_name TEXT,
            qualifier_ui TEXT,
            qualifier_name TEXT,
            PRIMARY KEY (work_id, mesh_seq)
        );

        CREATE TABLE works_counts_by_year (
            work_id TEXT,
            citation_year INTEGER,
            cited_by_count INTEGER,
            PRIMARY KEY (work_id, citation_year)
        );

        CREATE TABLE works_sdgs (
            work_id TEXT,
            sdg_seq INTEGER,
            sdg_id TEXT,
            description TEXT,
            score REAL,
            PRIMARY KEY (work_id, sdg_seq)
        );

        CREATE TABLE works_grants (
            work_id TEXT,
            grant_seq INTEGER,
            funder TEXT,
            funder_display_name TEXT,
            award_id TEXT,
            PRIMARY KEY (work_id, grant_seq)
        );

        CREATE TABLE works_apc_list (
            work_id TEXT,
            apc_seq INTEGER,
            value REAL,
            currency TEXT,
            value_usd REAL,
            provenance TEXT,
            PRIMARY KEY (work_id, apc_seq)
        );

        CREATE TABLE works_apc_paid (
            work_id TEXT,
            apc_seq INTEGER,
            value REAL,
            currency TEXT,
            value_usd REAL,
            provenance TEXT,
            PRIMARY KEY (work_id, apc_seq)
        );
        """
    )
    return conn


def insert_registry_rows(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    conn.executemany(
        """
        INSERT INTO source_registry (
            source_id, source_name, source_type, works_count, first_year, last_year, total_citations,
            top_subfields, normalized_name, final_bucket, decision_source, decision_reason, manual_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["source_id"],
                row["source_name"],
                row["source_type"],
                int(row["works_count"]),
                int(row["first_year"]),
                int(row["last_year"]),
                int(row["total_citations"]),
                row["top_subfields"],
                row["normalized_name"],
                row["final_bucket"],
                row["decision_source"],
                row["decision_reason"],
                row["manual_notes"],
            )
            for row in rows
        ],
    )


def insert_work(conn: sqlite3.Connection, work: dict[str, Any], stats: Counter) -> None:
    work_id = work["id"]
    source = primary_source(work)
    primary_location = ensure_dict(work.get("primary_location"))
    best_oa_location = ensure_dict(work.get("best_oa_location"))
    open_access = ensure_dict(work.get("open_access"))
    summary_stats = ensure_dict(work.get("summary_stats"))
    biblio = ensure_dict(work.get("biblio"))
    primary_topic = normalize_primary_topic(work.get("primary_topic"))
    primary_subfield = ensure_dict(primary_topic.get("subfield"))
    primary_field = ensure_dict(primary_topic.get("field"))
    primary_domain = ensure_dict(primary_topic.get("domain"))
    abstract_text, abstract_word_count = reconstruct_abstract(work.get("abstract_inverted_index"))
    abstract_quality, abstract_is_placeholder, abstract_ready_for_extraction = classify_abstract_quality(abstract_text, abstract_word_count)

    base_row = {
        "work_id": work_id,
        "doi": work.get("doi"),
        "display_name": work.get("display_name"),
        "title": work.get("title"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "language": work.get("language"),
        "type": work.get("type"),
        "type_crossref": work.get("type_crossref"),
        "source_id": source.get("id") or work.get("frontiergraph_source_id"),
        "source_display_name": source.get("display_name") or work.get("frontiergraph_source_name"),
        "source_type": source.get("type") or work.get("frontiergraph_source_type"),
        "source_issn_l": source.get("issn_l"),
        "source_issn_json": json_dumps(source.get("issn")),
        "source_host_organization": source.get("host_organization"),
        "source_host_organization_name": source.get("host_organization_name"),
        "source_host_organization_lineage_json": json_dumps(source.get("host_organization_lineage")),
        "source_is_oa": bool_to_int(source.get("is_oa")),
        "source_is_in_doaj": bool_to_int(source.get("is_in_doaj")),
        "source_is_core": bool_to_int(source.get("is_core")),
        "primary_topic_id": primary_topic.get("id"),
        "primary_topic_display_name": primary_topic.get("display_name"),
        "primary_topic_score": primary_topic.get("score"),
        "primary_subfield_id": primary_subfield.get("id"),
        "primary_subfield_display_name": primary_subfield.get("display_name"),
        "primary_field_id": primary_field.get("id"),
        "primary_field_display_name": primary_field.get("display_name"),
        "primary_domain_id": primary_domain.get("id"),
        "primary_domain_display_name": primary_domain.get("display_name"),
        "frontiergraph_bucket": work.get("frontiergraph_bucket"),
        "frontiergraph_source_name": work.get("frontiergraph_source_name"),
        "frontiergraph_source_type": work.get("frontiergraph_source_type"),
        "frontiergraph_decision_source": work.get("frontiergraph_decision_source"),
        "frontiergraph_decision_reason": work.get("frontiergraph_decision_reason"),
        "frontiergraph_manual_notes": work.get("frontiergraph_manual_notes"),
        "frontiergraph_snapshot_origin": work.get("frontiergraph_snapshot_origin"),
        "open_access_is_oa": bool_to_int(open_access.get("is_oa")),
        "open_access_status": open_access.get("oa_status"),
        "open_access_url": open_access.get("oa_url"),
        "any_repository_has_fulltext": bool_to_int(open_access.get("any_repository_has_fulltext")),
        "primary_location_is_oa": bool_to_int(primary_location.get("is_oa")),
        "primary_pdf_url": primary_location.get("pdf_url"),
        "primary_landing_page_url": primary_location.get("landing_page_url"),
        "primary_version": primary_location.get("version"),
        "primary_license": primary_location.get("license"),
        "best_oa_is_oa": bool_to_int(best_oa_location.get("is_oa")),
        "best_oa_pdf_url": best_oa_location.get("pdf_url"),
        "best_oa_landing_page_url": best_oa_location.get("landing_page_url"),
        "best_oa_version": best_oa_location.get("version"),
        "best_oa_license": best_oa_location.get("license"),
        "cited_by_count": work.get("cited_by_count"),
        "summary_2yr_cited_by_count": summary_stats.get("2yr_cited_by_count"),
        "fwci": work.get("fwci"),
        "referenced_works_count": work.get("referenced_works_count"),
        "locations_count": work.get("locations_count"),
        "authors_count": work.get("authors_count"),
        "topics_count": work.get("topics_count"),
        "institutions_distinct_count": work.get("institutions_distinct_count"),
        "countries_distinct_count": work.get("countries_distinct_count"),
        "corresponding_author_ids_json": json_dumps(work.get("corresponding_author_ids")),
        "corresponding_institution_ids_json": json_dumps(work.get("corresponding_institution_ids")),
        "indexed_in_json": json_dumps(work.get("indexed_in")),
        "ids_json": json_dumps(work.get("ids")),
        "biblio_json": json_dumps(biblio),
        "summary_stats_json": json_dumps(summary_stats),
        "primary_location_json": json_dumps(primary_location),
        "best_oa_location_json": json_dumps(best_oa_location),
        "open_access_json": json_dumps(open_access),
        "citation_normalized_percentile_json": json_dumps(work.get("citation_normalized_percentile")),
        "cited_by_percentile_year_json": json_dumps(work.get("cited_by_percentile_year")),
        "awards_json": json_dumps(work.get("awards")),
        "content_urls_json": json_dumps(work.get("content_urls")),
        "is_retracted": bool_to_int(work.get("is_retracted")),
        "is_paratext": bool_to_int(work.get("is_paratext")),
        "fulltext_origin": work.get("fulltext_origin"),
        "has_fulltext": bool_to_int(work.get("has_fulltext")),
        "cited_by_api_url": work.get("cited_by_api_url"),
        "updated_date": work.get("updated_date"),
        "created_date": work.get("created_date"),
    }
    base_columns = list(base_row.keys())
    base_placeholders = ", ".join("?" for _ in base_columns)
    conn.execute(
        f"INSERT OR REPLACE INTO works_base ({', '.join(base_columns)}) VALUES ({base_placeholders})",
        tuple(base_row[column] for column in base_columns),
    )

    conn.execute(
        """
        INSERT OR REPLACE INTO works_abstracts (
            work_id, has_abstract, abstract_word_count, abstract_quality,
            abstract_is_placeholder, abstract_ready_for_extraction, abstract_text, abstract_inverted_index_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            work_id,
            int(abstract_text is not None),
            abstract_word_count,
            abstract_quality,
            abstract_is_placeholder,
            abstract_ready_for_extraction,
            abstract_text,
            json_dumps(work.get("abstract_inverted_index")),
        ),
    )

    for idx, topic in enumerate(ensure_list(work.get("topics"))):
        topic = ensure_dict(topic)
        subfield = ensure_dict(topic.get("subfield"))
        field = ensure_dict(topic.get("field"))
        domain = ensure_dict(topic.get("domain"))
        conn.execute(
            """
            INSERT OR REPLACE INTO works_topics (
                work_id, topic_seq, topic_id, display_name, score, subfield_id, subfield_display_name,
                field_id, field_display_name, domain_id, domain_display_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                idx,
                topic.get("id"),
                topic.get("display_name"),
                topic.get("score"),
                subfield.get("id"),
                subfield.get("display_name"),
                field.get("id"),
                field.get("display_name"),
                domain.get("id"),
                domain.get("display_name"),
            ),
        )

    for idx, keyword in enumerate(ensure_list(work.get("keywords"))):
        keyword = ensure_dict(keyword)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_keywords (work_id, keyword_seq, keyword_id, display_name, score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (work_id, idx, keyword.get("id"), keyword.get("display_name"), keyword.get("score")),
        )

    for idx, authorship in enumerate(ensure_list(work.get("authorships"))):
        authorship = ensure_dict(authorship)
        author = ensure_dict(authorship.get("author"))
        institutions = ensure_list(authorship.get("institutions"))
        conn.execute(
            """
            INSERT OR REPLACE INTO works_authorships (
                work_id, author_seq, author_position, author_id, author_display_name, is_corresponding,
                raw_author_string, countries_json, raw_affiliation_strings_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                idx,
                authorship.get("author_position"),
                author.get("id"),
                author.get("display_name"),
                bool_to_int(authorship.get("is_corresponding")),
                authorship.get("raw_author_string"),
                json_dumps(authorship.get("countries")),
                json_dumps(authorship.get("raw_affiliation_strings")),
            ),
        )
        for inst_idx, institution in enumerate(institutions):
            institution = ensure_dict(institution)
            conn.execute(
                """
                INSERT OR REPLACE INTO works_authorship_institutions (
                    work_id, author_seq, institution_seq, institution_id, ror, display_name, country_code, type, lineage_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    work_id,
                    idx,
                    inst_idx,
                    institution.get("id"),
                    institution.get("ror"),
                    institution.get("display_name"),
                    institution.get("country_code"),
                    institution.get("type"),
                    json_dumps(institution.get("lineage")),
                ),
            )

    for idx, location in enumerate(ensure_list(work.get("locations"))):
        location = ensure_dict(location)
        location_source = ensure_dict(location.get("source"))
        conn.execute(
            """
            INSERT OR REPLACE INTO works_locations (
                work_id, location_seq, source_id, source_display_name, source_type, source_issn_l, source_issn_json,
                source_host_organization, source_host_organization_name, source_is_oa, source_is_in_doaj, source_is_core,
                pdf_url, landing_page_url, is_oa, version, license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                idx,
                location_source.get("id"),
                location_source.get("display_name"),
                location_source.get("type"),
                location_source.get("issn_l"),
                json_dumps(location_source.get("issn")),
                location_source.get("host_organization"),
                location_source.get("host_organization_name"),
                bool_to_int(location_source.get("is_oa")),
                bool_to_int(location_source.get("is_in_doaj")),
                bool_to_int(location_source.get("is_core")),
                location.get("pdf_url"),
                location.get("landing_page_url"),
                bool_to_int(location.get("is_oa")),
                location.get("version"),
                location.get("license"),
            ),
        )

    for idx, mesh in enumerate(ensure_list(work.get("mesh"))):
        mesh = ensure_dict(mesh)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_mesh (
                work_id, mesh_seq, is_major_topic, descriptor_ui, descriptor_name, qualifier_ui, qualifier_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                idx,
                bool_to_int(mesh.get("is_major_topic")),
                mesh.get("descriptor_ui"),
                mesh.get("descriptor_name"),
                mesh.get("qualifier_ui"),
                mesh.get("qualifier_name"),
            ),
        )

    for entry in ensure_list(work.get("counts_by_year")):
        entry = ensure_dict(entry)
        if entry.get("year") is None:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO works_counts_by_year (work_id, citation_year, cited_by_count)
            VALUES (?, ?, ?)
            """,
            (work_id, entry.get("year"), entry.get("cited_by_count")),
        )

    for idx, sdg in enumerate(ensure_list(work.get("sustainable_development_goals"))):
        sdg = ensure_dict(sdg)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_sdgs (work_id, sdg_seq, sdg_id, description, score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (work_id, idx, sdg.get("id"), sdg.get("description"), sdg.get("score")),
        )

    for idx, grant in enumerate(ensure_list(work.get("grants"))):
        grant = ensure_dict(grant)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_grants (work_id, grant_seq, funder, funder_display_name, award_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (work_id, idx, grant.get("funder"), grant.get("funder_display_name"), grant.get("award_id")),
        )

    for idx, apc in enumerate(ensure_list(work.get("apc_list"))):
        apc = ensure_dict(apc)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_apc_list (work_id, apc_seq, value, currency, value_usd, provenance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (work_id, idx, apc.get("value"), apc.get("currency"), apc.get("value_usd"), apc.get("provenance")),
        )

    for idx, apc in enumerate(ensure_list(work.get("apc_paid"))):
        apc = ensure_dict(apc)
        conn.execute(
            """
            INSERT OR REPLACE INTO works_apc_paid (work_id, apc_seq, value, currency, value_usd, provenance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (work_id, idx, apc.get("value"), apc.get("currency"), apc.get("value_usd"), apc.get("provenance")),
        )

    stats["works_base"] += 1
    stats[f"bucket__{work.get('frontiergraph_bucket')}"] += 1
    stats[f"origin__{work.get('frontiergraph_snapshot_origin')}"] += 1
    stats["works_with_abstract"] += int(abstract_text is not None)
    stats["works_without_abstract"] += int(abstract_text is None)
    stats["works_abstract_lt_50"] += int(abstract_text is not None and abstract_word_count < 50)
    stats[f"abstract_quality__{abstract_quality}"] += 1
    stats["works_ready_for_extraction"] += abstract_ready_for_extraction


def ingest_stream(
    *,
    conn: sqlite3.Connection,
    path: Path,
    stats: Counter,
    skip_ids: set[str] | None,
    label: str,
    progress_every: int,
) -> int:
    written = 0
    with conn:
        for idx, work in enumerate(iter_jsonl_gz(path), start=1):
            work_id = work.get("id")
            if not work_id:
                continue
            if skip_ids and work_id in skip_ids:
                stats[f"{label}_skipped"] += 1
                continue
            insert_work(conn, work, stats)
            written += 1
            if idx % progress_every == 0:
                conn.commit()
                print(f"{label}: processed {idx} rows | wrote {written}", flush=True)
    return written


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_source_registry_bucket ON source_registry(final_bucket);
        CREATE INDEX idx_works_base_pub_year ON works_base(publication_year);
        CREATE INDEX idx_works_base_bucket ON works_base(frontiergraph_bucket);
        CREATE INDEX idx_works_base_source ON works_base(source_id);
        CREATE INDEX idx_works_abstracts_word_count ON works_abstracts(abstract_word_count);
        CREATE INDEX idx_works_abstracts_quality ON works_abstracts(abstract_quality);
        CREATE INDEX idx_works_abstracts_ready ON works_abstracts(abstract_ready_for_extraction);
        CREATE INDEX idx_works_topics_topic_id ON works_topics(topic_id);
        CREATE INDEX idx_works_topics_subfield_id ON works_topics(subfield_id);
        CREATE INDEX idx_works_keywords_keyword_id ON works_keywords(keyword_id);
        CREATE INDEX idx_works_authorships_author_id ON works_authorships(author_id);
        CREATE INDEX idx_works_locations_source_id ON works_locations(source_id);
        CREATE INDEX idx_works_counts_by_year_year ON works_counts_by_year(citation_year);
        CREATE INDEX idx_works_grants_funder ON works_grants(funder);
        """
    )


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def main() -> None:
    args = parse_args()
    registry_rows, retained_registry = load_registry_rows(Path(args.registry_csv))
    overlay_ids = build_recent_api_overlay(
        api_recent_dir=Path(args.api_recent_dir),
        registry=retained_registry,
        overlay_out=Path(args.api_overlay_out),
        overlay_manifest_path=Path(args.api_overlay_manifest),
    )

    conn = init_db(Path(args.output_db))
    insert_registry_rows(conn, registry_rows)
    conn.commit()

    stats = Counter()
    stats["registry_rows"] = len(registry_rows)
    stats["retained_registry_rows"] = len(retained_registry)
    stats["api_overlay_ids"] = len(overlay_ids)

    stats["bigquery_written"] = ingest_stream(
        conn=conn,
        path=Path(args.bigquery_raw),
        stats=stats,
        skip_ids=overlay_ids,
        label="bigquery",
        progress_every=args.progress_every,
    )
    conn.commit()

    stats["api_written"] = ingest_stream(
        conn=conn,
        path=Path(args.api_overlay_out),
        stats=stats,
        skip_ids=None,
        label="api_overlay",
        progress_every=args.progress_every,
    )
    conn.commit()

    create_indexes(conn)
    conn.commit()

    manifest = {
        "registry_rows": stats["registry_rows"],
        "retained_registry_rows": stats["retained_registry_rows"],
        "api_overlay_ids": stats["api_overlay_ids"],
        "bigquery_written": stats["bigquery_written"],
        "bigquery_skipped": stats["bigquery_skipped"],
        "api_written": stats["api_written"],
        "bucket_counts": {key.removeprefix("bucket__"): value for key, value in stats.items() if key.startswith("bucket__")},
        "origin_counts": {key.removeprefix("origin__"): value for key, value in stats.items() if key.startswith("origin__")},
        "abstract_counts": {
            "with_abstract": stats["works_with_abstract"],
            "without_abstract": stats["works_without_abstract"],
            "abstract_lt_50_words": stats["works_abstract_lt_50"],
            "ready_for_extraction": stats["works_ready_for_extraction"],
        },
        "abstract_quality_counts": {
            key.removeprefix("abstract_quality__"): value
            for key, value in stats.items()
            if key.startswith("abstract_quality__")
        },
        "table_counts": {
            table: table_count(conn, table)
            for table in [
                "source_registry",
                "works_base",
                "works_abstracts",
                "works_topics",
                "works_keywords",
                "works_authorships",
                "works_authorship_institutions",
                "works_locations",
                "works_mesh",
                "works_counts_by_year",
                "works_sdgs",
                "works_grants",
                "works_apc_list",
                "works_apc_paid",
            ]
        },
        "output_db": args.output_db,
    }
    Path(args.manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    conn.close()


if __name__ == "__main__":
    main()
