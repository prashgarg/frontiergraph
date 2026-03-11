from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INPUTS = [
    "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_valid_existing.jsonl.gz",
    "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_missing.jsonl.gz",
    "data/raw/openalex_enriched/api_recovery_pre2024/part1.output.jsonl.gz",
    "data/raw/openalex_enriched/api_recovery_pre2024/part2.output.jsonl.gz",
]
DEFAULT_OUTPUT = "data/raw/openalex_enriched/openalex_retained_pre2024_combined_exact.jsonl.gz"
DEFAULT_MANIFEST = "data/raw/openalex_enriched/openalex_retained_pre2024_combined_exact_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine corrected retained pre-2024 OpenAlex enriched shards into one deduplicated JSONL.GZ stream.")
    parser.add_argument("--input", action="append", default=[], help="Input JSONL.GZ shard. May be passed multiple times.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest-path", default=DEFAULT_MANIFEST)
    return parser.parse_args()


def iter_jsonl_gz(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    args = parse_args()
    inputs = [Path(path) for path in (args.input or DEFAULT_INPUTS)]
    output_path = Path(args.output)
    manifest_path = Path(args.manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen_ids: set[str] = set()
    stats = Counter()
    per_input: list[dict[str, Any]] = []

    with gzip.open(output_path, "wt", encoding="utf-8", compresslevel=1) as out_handle:
        for input_path in inputs:
            input_stats = Counter()
            for row in iter_jsonl_gz(input_path):
                work_id = row.get("id")
                if not work_id:
                    input_stats["missing_id"] += 1
                    continue
                input_stats["rows_seen"] += 1
                if work_id in seen_ids:
                    input_stats["duplicates_skipped"] += 1
                    continue
                seen_ids.add(work_id)
                out_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                input_stats["rows_written"] += 1
                stats["rows_written"] += 1
                stats[f"origin__{row.get('frontiergraph_snapshot_origin', 'unknown')}"] += 1
                stats[f"bucket__{row.get('frontiergraph_bucket', 'unknown')}"] += 1
                if row.get("publication_year") is not None:
                    stats[f"year__{row['publication_year']}"] += 1
            per_input.append(
                {
                    "path": str(input_path),
                    "rows_seen": input_stats["rows_seen"],
                    "rows_written": input_stats["rows_written"],
                    "duplicates_skipped": input_stats["duplicates_skipped"],
                    "missing_id": input_stats["missing_id"],
                }
            )

    manifest = {
        "inputs": per_input,
        "output_path": str(output_path),
        "rows_written": stats["rows_written"],
        "bucket_counts": {
            key.removeprefix("bucket__"): value
            for key, value in stats.items()
            if key.startswith("bucket__")
        },
        "origin_counts": {
            key.removeprefix("origin__"): value
            for key, value in stats.items()
            if key.startswith("origin__")
        },
        "year_counts": {
            int(key.removeprefix("year__")): value
            for key, value in stats.items()
            if key.startswith("year__")
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
