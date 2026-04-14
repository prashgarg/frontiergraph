from __future__ import annotations

import csv
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
PUBLIC_DATA_DIR = SITE_ROOT / "public" / "data" / "v2"
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public" / "downloads"
GENERATED_SITE_DATA_PATH = SITE_ROOT / "src" / "generated" / "site-data.json"
MECHANISM_EDITORIAL_PATH = SITE_ROOT / "src" / "content" / "mechanism-editorial-opportunities.json"
QUESTIONS_CAROUSEL_ASSIGNMENTS_PATH = SITE_ROOT / "src" / "content" / "questions-carousel-assignments.json"

QUESTION_BASE_URL = "https://frontiergraph.com/questions/"
LITERATURE_BASE_URL = "https://frontiergraph.com/literature/"

SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_site_data_v2 import build_data_dictionary_markdown, build_release_readme_markdown  # noqa: E402


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def question_url(pair_key: object) -> str:
    cleaned = clean_text(pair_key)
    return f"{QUESTION_BASE_URL}#{cleaned}" if cleaned else QUESTION_BASE_URL


def concept_url(query: object) -> str:
    cleaned = clean_text(query)
    if not cleaned:
        return LITERATURE_BASE_URL
    return f"{LITERATURE_BASE_URL}?{urlencode({'q': cleaned})}"


def file_entry(public_path: str) -> dict[str, object]:
    local_path = SITE_ROOT / "public" / public_path.lstrip("/")
    return {
        "path": public_path,
        "filename": Path(public_path).name,
        "size_bytes": int(local_path.stat().st_size),
    }


def transform_app_links(value: object) -> object:
    if isinstance(value, list):
        return [transform_app_links(item) for item in value]
    if isinstance(value, dict):
        rewritten = {key: transform_app_links(item) for key, item in value.items()}
        if "app_link" in rewritten:
            if clean_text(rewritten.get("pair_key")):
                rewritten["app_link"] = question_url(rewritten["pair_key"])
            elif clean_text(rewritten.get("concept_id")):
                concept_label = (
                    clean_text(rewritten.get("plain_label"))
                    or clean_text(rewritten.get("label"))
                    or clean_text(rewritten.get("query"))
                )
                if concept_label:
                    rewritten["app_link"] = concept_url(concept_label)
        return rewritten
    return value


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rewrite_question_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
    for row in rows:
        row["app_link"] = question_url(row.get("pair_key"))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rewrite_concept_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
    for row in rows:
        row["app_link"] = concept_url(row.get("plain_label") or row.get("label"))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_mechanism_curated_questions() -> list[dict[str, object]]:
    payload = read_json(MECHANISM_EDITORIAL_PATH)
    if isinstance(payload, dict):
        items = list(payload.values())
    else:
        items = list(payload)
    curated = []
    for item in sorted(items, key=lambda row: (int(row.get("display_order", 9999)), str(row.get("pair_key", "")))):
        if not isinstance(item, dict):
            continue
        record = dict(item)
        record["app_link"] = question_url(record.get("pair_key"))
        curated.append(record)
    return curated


def rewrite_json_targets() -> None:
    question_json_files = [
        PUBLIC_DATA_DIR / "opportunity_slices.json",
        PUBLIC_DATA_DIR / "curated_questions.json",
    ]
    concept_json_files = [
        PUBLIC_DATA_DIR / "concept_index.json",
        PUBLIC_DATA_DIR / "central_concepts.json",
    ]

    for path in question_json_files + concept_json_files:
        write_json(path, transform_app_links(read_json(path)))

    for shard_path in sorted((PUBLIC_DATA_DIR / "concept_opportunities").glob("*.json")):
        write_json(shard_path, transform_app_links(read_json(shard_path)))

    # Replace the stale curated public-question file with the current mechanism curation.
    write_json(PUBLIC_DATA_DIR / "curated_questions.json", build_mechanism_curated_questions())


def rebuild_download_guides(site_data: dict[str, object]) -> None:
    metrics = site_data["metrics"]
    release_metrics = {
        "papers": int(metrics["papers"]),
        "normalized_links": int(metrics["normalized_links"]),
        "native_concepts": int(metrics["native_concepts"]),
        "visible_public_questions": int(metrics["visible_public_questions"]),
    }
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-release-readme.md").write_text(
        build_release_readme_markdown(release_metrics),
        encoding="utf-8",
    )
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-data-dictionary.md").write_text(
        build_data_dictionary_markdown(),
        encoding="utf-8",
    )


def write_deferred_tier3_placeholders() -> None:
    manifest = {
        "filename": "frontiergraph-economics-public.db",
        "status": "deferred",
        "note": "The SQLite bundle is being rebuilt separately and is not part of this local release pass.",
        "published_at": None,
    }
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.sha256.txt").write_text(
        "DEFERRED  frontiergraph-economics-public.db\n",
        encoding="utf-8",
    )


def load_tier3_release_state() -> tuple[dict[str, object], bool]:
    manifest_path = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.manifest.json"
    checksum_path = PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.sha256.txt"
    if not manifest_path.exists() or not checksum_path.exists():
        write_deferred_tier3_placeholders()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    deferred = str(manifest.get("status", "")).lower() == "deferred"
    return manifest, deferred


def zip_bundle(output_path: Path, entries: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source_path, archive_name in entries:
            archive.write(source_path, archive_name)


def rebuild_tier_bundles() -> None:
    tier1_entries = [
        (PUBLIC_DATA_DIR / "top_questions.csv", "top_questions.csv"),
        (PUBLIC_DATA_DIR / "central_concepts.csv", "central_concepts.csv"),
        (PUBLIC_DATA_DIR / "curated_questions.json", "curated_questions.json"),
        (PUBLIC_DATA_DIR / "hybrid_corpus_manifest.json", "hybrid_corpus_manifest.json"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-release-readme.md", "README.md"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-data-dictionary.md", "DATA_DICTIONARY.md"),
    ]
    zip_bundle(PUBLIC_DOWNLOADS_DIR / "frontiergraph-tier1-lightweight-exports.zip", tier1_entries)

    tier2_core_entries = [
        (PUBLIC_DATA_DIR / "graph_backbone.json", "graph_backbone.json"),
        (PUBLIC_DATA_DIR / "concept_index.json", "concept_index.json"),
        (PUBLIC_DATA_DIR / "literature_search_index.json", "literature_search_index.json"),
        (PUBLIC_DATA_DIR / "concept_neighborhoods_index.json", "concept_neighborhoods_index.json"),
        (PUBLIC_DATA_DIR / "concept_opportunities_index.json", "concept_opportunities_index.json"),
        (PUBLIC_DATA_DIR / "opportunity_slices.json", "opportunity_slices.json"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-release-readme.md", "README.md"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-data-dictionary.md", "DATA_DICTIONARY.md"),
    ]
    zip_bundle(PUBLIC_DOWNLOADS_DIR / "frontiergraph-tier2-core-indexes.zip", tier2_core_entries)

    tier2_neighborhood_entries = [
        (PUBLIC_DATA_DIR / "concept_neighborhoods_index.json", "concept_neighborhoods_index.json"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-release-readme.md", "README.md"),
    ]
    directory = PUBLIC_DATA_DIR / "concept_neighborhoods"
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            tier2_neighborhood_entries.append((path, f"concept_neighborhoods/{path.relative_to(directory).as_posix()}"))
    zip_bundle(PUBLIC_DOWNLOADS_DIR / "frontiergraph-tier2-concept-neighborhoods.zip", tier2_neighborhood_entries)

    tier2_opportunity_entries = [
        (PUBLIC_DATA_DIR / "concept_opportunities_index.json", "concept_opportunities_index.json"),
        (PUBLIC_DATA_DIR / "opportunity_slices.json", "opportunity_slices.json"),
        (PUBLIC_DOWNLOADS_DIR / "frontiergraph-release-readme.md", "README.md"),
    ]
    directory = PUBLIC_DATA_DIR / "concept_opportunities"
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            tier2_opportunity_entries.append((path, f"concept_opportunities/{path.relative_to(directory).as_posix()}"))
    zip_bundle(PUBLIC_DOWNLOADS_DIR / "frontiergraph-tier2-concept-opportunities.zip", tier2_opportunity_entries)

    legacy_bundle = PUBLIC_DOWNLOADS_DIR / "frontiergraph-tier2-structured-assets.zip"
    if legacy_bundle.exists():
        legacy_bundle.unlink()


def sync_download_metadata() -> None:
    site_data = json.loads(GENERATED_SITE_DATA_PATH.read_text(encoding="utf-8"))
    carousel_assignments = json.loads(QUESTIONS_CAROUSEL_ASSIGNMENTS_PATH.read_text(encoding="utf-8"))
    rebuild_download_guides(site_data)
    rebuild_tier_bundles()
    manifest, tier3_deferred = load_tier3_release_state()

    downloads = site_data["downloads"]
    downloads["public_db"] = {
        "filename": str(manifest.get("filename") or "frontiergraph-economics-public.db"),
        "public_url": "" if tier3_deferred else str(manifest.get("public_url") or ""),
        "sha256": "deferred" if tier3_deferred else str(manifest.get("sha256") or ""),
        "db_size_bytes": 0 if tier3_deferred else int(manifest.get("db_size_bytes") or 0),
        "db_size_gb": 0.0 if tier3_deferred else float(manifest.get("db_size_gb") or 0.0),
    }
    downloads["checksum_path"] = "/downloads/frontiergraph-economics-public.sha256.txt"
    downloads["manifest_path"] = "/downloads/frontiergraph-economics-public.manifest.json"
    downloads["guides"] = {
        "readme": file_entry("/downloads/frontiergraph-release-readme.md"),
        "data_dictionary": file_entry("/downloads/frontiergraph-data-dictionary.md"),
    }
    downloads["tier_bundles"] = {
        "tier1": file_entry("/downloads/frontiergraph-tier1-lightweight-exports.zip"),
    }
    downloads["tier2_packages"] = {
        "core": file_entry("/downloads/frontiergraph-tier2-core-indexes.zip"),
        "neighborhoods": file_entry("/downloads/frontiergraph-tier2-concept-neighborhoods.zip"),
        "opportunities": file_entry("/downloads/frontiergraph-tier2-concept-opportunities.zip"),
    }
    downloads["artifact_details"]["top_questions_csv"] = file_entry("/data/v2/top_questions.csv")
    downloads["artifact_details"]["curated_questions_json"] = file_entry("/data/v2/curated_questions.json")
    downloads["artifact_details"]["central_concepts_csv"] = file_entry("/data/v2/central_concepts.csv")
    downloads["artifact_details"]["concept_index_json"] = file_entry("/data/v2/concept_index.json")
    downloads["artifact_details"]["concept_opportunities_index_json"] = file_entry("/data/v2/concept_opportunities_index.json")
    downloads["artifact_details"]["concept_neighborhoods_index_json"] = file_entry("/data/v2/concept_neighborhoods_index.json")
    downloads["artifact_details"]["opportunity_slices_json"] = file_entry("/data/v2/opportunity_slices.json")
    downloads["artifact_details"]["manifest_json"] = file_entry("/downloads/frontiergraph-economics-public.manifest.json")
    downloads["artifact_details"]["checksum_txt"] = file_entry("/downloads/frontiergraph-economics-public.sha256.txt")
    downloads["artifact_details"]["tier2_core_zip"] = file_entry("/downloads/frontiergraph-tier2-core-indexes.zip")
    downloads["artifact_details"]["tier2_neighborhoods_zip"] = file_entry("/downloads/frontiergraph-tier2-concept-neighborhoods.zip")
    downloads["artifact_details"]["tier2_opportunities_zip"] = file_entry("/downloads/frontiergraph-tier2-concept-opportunities.zip")
    downloads["artifact_details"]["manifest_json"]["deferred"] = tier3_deferred
    downloads["artifact_details"]["checksum_txt"]["deferred"] = tier3_deferred
    if not site_data["questions"].get("field_carousels"):
        site_data["questions"]["field_carousels"] = carousel_assignments.get("field_carousels", [])
    if not site_data["questions"].get("use_case_carousels"):
        site_data["questions"]["use_case_carousels"] = carousel_assignments.get("use_case_carousels", [])

    GENERATED_SITE_DATA_PATH.write_text(json.dumps(site_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    rewrite_question_csv(PUBLIC_DATA_DIR / "top_questions.csv")
    rewrite_concept_csv(PUBLIC_DATA_DIR / "central_concepts.csv")
    rewrite_json_targets()
    sync_download_metadata()


if __name__ == "__main__":
    main()
