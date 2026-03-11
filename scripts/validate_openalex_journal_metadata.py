from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate downloaded OpenAlex yearly journal metadata shards against gzip integrity, UTF-8 decoding, and saved state counts."
    )
    parser.add_argument(
        "--in-dir",
        default="data/raw/openalex/journal_field20_metadata",
        help="Directory containing yearly JSONL.gz files and _state metadata",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    state_dir = in_dir / "_state"

    issues: list[tuple[str, str, str]] = []
    checked = 0

    for path in sorted(in_dir.glob("openalex_field*_journal_articles_en_*.jsonl.gz")):
        year = path.stem.split("_")[-1]
        state_path = state_dir / f"{year}.json"
        expected = None
        complete = None
        if state_path.exists():
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            expected = payload.get("records_fetched")
            complete = payload.get("complete")

        count = 0
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                for count, _ in enumerate(fh, 1):
                    pass
        except Exception as exc:  # noqa: BLE001
            issues.append((year, type(exc).__name__, str(exc)))
            continue

        checked += 1
        if expected is not None and count != expected:
            issues.append((year, "count_mismatch", f"count={count} expected={expected}"))
        if complete is False:
            issues.append((year, "state_incomplete", "state marked incomplete"))

    if issues:
        print(f"Validation failed for {len(issues)} shard(s):")
        for year, kind, detail in issues:
            print(f"- {year}: {kind}: {detail}")
        sys.exit(1)

    print(f"Validated {checked} shard(s) successfully")


if __name__ == "__main__":
    main()
