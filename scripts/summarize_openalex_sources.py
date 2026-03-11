from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize OpenAlex source counts from downloaded JSONL.gz metadata.")
    parser.add_argument(
        "--in-dir",
        default="data/raw/openalex/journal_field20_metadata",
        help="Directory containing yearly JSONL.gz files",
    )
    parser.add_argument(
        "--out-csv",
        default="data/raw/openalex/journal_field20_metadata/source_summary.csv",
        help="Output CSV path",
    )
    return parser.parse_args()


def iter_rows(in_dir: Path):
    for path in sorted(in_dir.glob("openalex_field*_journal_articles_en_*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, dict[str, Any]] = {}
    subfield_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for row in iter_rows(in_dir):
        primary_location = row.get("primary_location") or {}
        source = primary_location.get("source") or {}
        source_id = str(source.get("id") or "UNKNOWN")
        source_name = str(source.get("display_name") or "Unknown source")
        source_type = str(source.get("type") or "")
        year = row.get("publication_year")
        cited_by_count = int(row.get("cited_by_count") or 0)

        primary_topic = row.get("primary_topic") or {}
        subfield = primary_topic.get("subfield") or {}
        subfield_name = str(subfield.get("display_name") or "Unknown")

        if source_id not in counts:
            counts[source_id] = {
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type,
                "works_count": 0,
                "first_year": year,
                "last_year": year,
                "total_citations": 0,
            }

        item = counts[source_id]
        item["works_count"] += 1
        item["total_citations"] += cited_by_count
        if year is not None:
            item["first_year"] = min(item["first_year"], year) if item["first_year"] is not None else year
            item["last_year"] = max(item["last_year"], year) if item["last_year"] is not None else year
        subfield_counts[source_id][subfield_name] += 1

    rows = []
    for source_id, item in counts.items():
        top_subfields = subfield_counts[source_id].most_common(3)
        item["top_subfields"] = " | ".join(f"{name}:{count}" for name, count in top_subfields)
        rows.append(item)

    rows.sort(key=lambda row: (-row["works_count"], row["source_name"]))

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source_id",
                "source_name",
                "source_type",
                "works_count",
                "first_year",
                "last_year",
                "total_citations",
                "top_subfields",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote source summary: {out_path}")


if __name__ == "__main__":
    main()
