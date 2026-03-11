from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


DEFAULT_CORE = "data/processed/openalex/published_journal_corpora/published_core_econ.jsonl.gz"
DEFAULT_ADJACENT = "data/processed/openalex/published_journal_corpora/published_adjacent_econ_relevant.jsonl.gz"
DEFAULT_VALID_EXISTING = "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_valid_existing.jsonl.gz"
DEFAULT_RECOVERED = "data/raw/openalex_enriched/bigquery_snapshot_retained_pre2024_missing.jsonl.gz"
DEFAULT_OUT_DIR = "data/raw/openalex_enriched/api_recovery_pre2024"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the remaining pre-2024 retained OpenAlex ID lists for API recovery.")
    parser.add_argument("--core-path", default=DEFAULT_CORE)
    parser.add_argument("--adjacent-path", default=DEFAULT_ADJACENT)
    parser.add_argument("--valid-existing-path", default=DEFAULT_VALID_EXISTING)
    parser.add_argument("--recovered-path", default=DEFAULT_RECOVERED)
    parser.add_argument("--max-publication-year", type=int, default=2023)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_retained(core_path: Path, adjacent_path: Path, max_publication_year: int) -> dict[str, dict]:
    retained: dict[str, dict] = {}
    for path in (core_path, adjacent_path):
        for row in iter_jsonl_gz(path):
            if int(row.get("publication_year") or 0) > max_publication_year:
                continue
            retained[row["id"]] = {
                "id": row["id"],
                "publication_year": int(row.get("publication_year") or 0),
                "frontiergraph_bucket": row.get("frontiergraph_bucket"),
                "frontiergraph_source_id": row.get("frontiergraph_source_id"),
                "frontiergraph_source_name": row.get("frontiergraph_source_name"),
                "frontiergraph_source_type": row.get("frontiergraph_source_type"),
                "frontiergraph_decision_source": row.get("frontiergraph_decision_source"),
                "frontiergraph_decision_reason": row.get("frontiergraph_decision_reason"),
                "frontiergraph_manual_notes": row.get("frontiergraph_manual_notes"),
            }
    return retained


def load_covered_ids(*paths: Path) -> set[str]:
    covered: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for row in iter_jsonl_gz(path):
            covered.add(row["id"])
    return covered


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    retained = load_retained(Path(args.core_path), Path(args.adjacent_path), args.max_publication_year)
    covered = load_covered_ids(Path(args.valid_existing_path), Path(args.recovered_path))

    missing = [retained[work_id] for work_id in sorted(retained) if work_id not in covered]
    midpoint = len(missing) // 2
    shards = {
        "part1": missing[:midpoint],
        "part2": missing[midpoint:],
    }

    manifest = {
        "max_publication_year": args.max_publication_year,
        "expected_retained_rows": len(retained),
        "covered_rows": len(covered & set(retained)),
        "missing_rows": len(missing),
        "shards": {},
    }

    for name, rows in shards.items():
        out_path = out_dir / f"{name}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["shards"][name] = {
            "path": str(out_path),
            "rows": len(rows),
        }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
