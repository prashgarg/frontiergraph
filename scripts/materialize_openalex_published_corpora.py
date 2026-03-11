from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_IN_DIR = "data/raw/openalex/journal_field20_metadata"
DEFAULT_REGISTRY_CSV = "data/raw/openalex/journal_field20_metadata/source_registry.csv"
DEFAULT_OUT_DIR = "data/processed/openalex/published_journal_corpora"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize reviewed OpenAlex journal work corpora into core, adjacent, exclude, and review buckets."
    )
    parser.add_argument("--in-dir", default=DEFAULT_IN_DIR)
    parser.add_argument("--registry-csv", default=DEFAULT_REGISTRY_CSV)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def load_registry(path: Path) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mapping[row["source_id"]] = row
    return mapping


def output_name_for_bucket(bucket: str) -> str:
    names = {
        "core": "published_core_econ.jsonl.gz",
        "adjacent": "published_adjacent_econ_relevant.jsonl.gz",
        "exclude": "published_excluded.jsonl.gz",
        "review": "published_review_pending.jsonl.gz",
    }
    if bucket not in names:
        raise ValueError(f"Unexpected bucket: {bucket}")
    return names[bucket]


def record_source_id(row: dict) -> str | None:
    primary_location = row.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("id")


def build_materialized_row(raw: dict, registry_row: dict[str, str]) -> dict:
    payload = dict(raw)
    payload["frontiergraph_bucket"] = registry_row["final_bucket"]
    payload["frontiergraph_decision_source"] = registry_row["decision_source"]
    payload["frontiergraph_decision_reason"] = registry_row["decision_reason"]
    payload["frontiergraph_manual_notes"] = registry_row["manual_notes"]
    payload["frontiergraph_source_name"] = registry_row["source_name"]
    payload["frontiergraph_source_type"] = registry_row["source_type"]
    payload["frontiergraph_source_id"] = registry_row["source_id"]
    return payload


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    registry_csv = Path(args.registry_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry(registry_csv)

    handles: dict[str, gzip.GzipFile] = {}
    bucket_counts: Counter[str] = Counter()
    bucket_year_counts: dict[str, Counter[int]] = defaultdict(Counter)
    missing_source_ids: Counter[str] = Counter()

    try:
        for bucket in ("core", "adjacent", "exclude", "review"):
            handles[bucket] = gzip.open(out_dir / output_name_for_bucket(bucket), "wt", encoding="utf-8")

        for shard in sorted(in_dir.glob("openalex_field*_journal_articles_en_*.jsonl.gz")):
            with gzip.open(shard, "rt", encoding="utf-8") as handle:
                for line in handle:
                    raw = json.loads(line)
                    source_id = record_source_id(raw)
                    if not source_id or source_id not in registry:
                        missing_source_ids[source_id or "<missing>"] += 1
                        continue
                    registry_row = registry[source_id]
                    bucket = registry_row["final_bucket"]
                    payload = build_materialized_row(raw, registry_row)
                    handles[bucket].write(json.dumps(payload, ensure_ascii=False) + "\n")
                    bucket_counts[bucket] += 1
                    year = int(raw.get("publication_year") or 0)
                    if year:
                        bucket_year_counts[bucket][year] += 1
    finally:
        for handle in handles.values():
            handle.close()

    manifest = {
        "input_dir": str(in_dir),
        "registry_csv": str(registry_csv),
        "output_dir": str(out_dir),
        "bucket_counts": dict(bucket_counts),
        "bucket_year_counts": {bucket: dict(sorted(counter.items())) for bucket, counter in bucket_year_counts.items()},
        "missing_source_id_rows": dict(missing_source_ids),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary_rows = [
        {"bucket": bucket, "works_count": bucket_counts.get(bucket, 0), "output_file": output_name_for_bucket(bucket)}
        for bucket in ("core", "adjacent", "exclude", "review")
    ]
    with (out_dir / "bucket_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bucket", "works_count", "output_file"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote materialized corpora to {out_dir}")
    for row in summary_rows:
        print(f"{row['bucket']}: {row['works_count']}")
    if missing_source_ids:
        print(f"Missing source-id rows: {sum(missing_source_ids.values())}")


if __name__ == "__main__":
    main()
