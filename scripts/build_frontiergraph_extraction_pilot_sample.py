from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY_CSV = "data/raw/openalex/journal_field20_metadata/source_registry.csv"
DEFAULT_RECENT_DIR = "data/raw/openalex/journal_field20_full_recent"
DEFAULT_OUTPUT_JSONL = "data/pilots/frontiergraph_extraction_v2/pilot_sample.jsonl"
DEFAULT_OUTPUT_MANIFEST = "data/pilots/frontiergraph_extraction_v2/pilot_sample_manifest.json"
DEFAULT_TARGET_SIZE = 96
DEFAULT_SEED = 20260308
DEFAULT_YEARS = (2024, 2025, 2026)
RETAINED_BUCKETS = {"core", "adjacent"}

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
    parser = argparse.ArgumentParser(description="Build a balanced recent-paper pilot sample for FrontierGraph extraction.")
    parser.add_argument("--registry-csv", default=DEFAULT_REGISTRY_CSV)
    parser.add_argument("--recent-dir", default=DEFAULT_RECENT_DIR)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--manifest-path", default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--target-size", type=int, default=DEFAULT_TARGET_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--all-candidates", action="store_true", help="Write all extraction-ready retained candidates for the requested years instead of sampling.")
    return parser.parse_args()


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def load_registry(path: Path) -> dict[str, dict[str, str]]:
    retained: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["final_bucket"] in RETAINED_BUCKETS:
                retained[row["source_id"]] = row
    return retained


def reconstruct_abstract(abstract_inverted_index: Any) -> tuple[str | None, int]:
    inverted = ensure_dict(abstract_inverted_index)
    if not inverted:
        return None, 0
    max_pos = -1
    for positions in inverted.values():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int) and pos > max_pos:
                    max_pos = pos
    if max_pos < 0:
        return None, 0
    tokens = [""] * (max_pos + 1)
    for token, positions in inverted.items():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int) and 0 <= pos <= max_pos:
                    tokens[pos] = token
    filtered = [token for token in tokens if token]
    if not filtered:
        return None, 0
    return " ".join(filtered), len(filtered)


def classify_abstract_quality(abstract_text: str | None, abstract_word_count: int) -> tuple[str, bool]:
    if not abstract_text or abstract_word_count == 0:
        return "missing", False

    normalized = " ".join(abstract_text.split()).strip()
    lowered = normalized.casefold()
    semicolons = normalized.count(";")
    token_count = len(TOKENISH_RE.findall(normalized))

    if lowered in {"none", "none.", "not available", "n/a"}:
        return "placeholder", False
    if any(needle in lowered for needle in PLACEHOLDER_SUBSTRINGS):
        return "placeholder", False
    if abstract_word_count < 20 and any(needle in lowered for needle in METADATA_SUBSTRINGS):
        return "metadata_only", False
    if abstract_word_count < 20 and token_count <= 8 and "." not in normalized and ":" not in normalized:
        return "metadata_only", False
    if abstract_word_count < 25 and semicolons >= 2:
        return "keyword_list", False
    if abstract_word_count < 20:
        return "too_short", False
    if abstract_word_count < 30:
        return "borderline_short", False
    if abstract_word_count < 50:
        return "usable_short", True
    return "usable", True


def iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def short_work_id(openalex_id: str) -> str:
    return openalex_id.rstrip("/").split("/")[-1]


def extract_source(work: dict[str, Any]) -> dict[str, Any]:
    return ensure_dict(ensure_dict(work.get("primary_location")).get("source"))


def build_candidates(recent_dir: Path, registry: dict[str, dict[str, str]], years: set[int]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(recent_dir.glob("openalex_field20_journal_articles_en_full_*.jsonl.gz")):
        for work in iter_jsonl_gz(path):
            year = int(work.get("publication_year") or 0)
            if year not in years:
                continue
            source = extract_source(work)
            source_id = str(source.get("id") or "")
            if source_id not in registry:
                continue
            abstract_text, abstract_word_count = reconstruct_abstract(work.get("abstract_inverted_index"))
            abstract_quality, abstract_ready = classify_abstract_quality(abstract_text, abstract_word_count)
            if not abstract_ready:
                continue
            registry_row = registry[source_id]
            title = str(work.get("title") or work.get("display_name") or "").strip()
            if not title or not abstract_text:
                continue
            row = {
                "openalex_work_id": str(work["id"]),
                "work_id_short": short_work_id(str(work["id"])),
                "title": title,
                "abstract": abstract_text,
                "publication_year": year,
                "publication_date": work.get("publication_date"),
                "bucket": registry_row["final_bucket"],
                "source_id": source_id,
                "source_name": registry_row["source_name"],
                "doi": work.get("doi"),
                "cited_by_count": int(work.get("cited_by_count") or 0),
                "fwci": work.get("fwci"),
                "abstract_word_count": abstract_word_count,
                "abstract_quality": abstract_quality,
                "primary_topic": ensure_dict(work.get("primary_topic")).get("display_name")
                if isinstance(work.get("primary_topic"), dict)
                else (
                    ensure_dict((work.get("primary_topic") or [{}])[0]).get("display_name")
                    if isinstance(work.get("primary_topic"), list) and work.get("primary_topic")
                    else None
                ),
            }
            candidates.append(row)
    return candidates


def allocate_counts(target_size: int, strata: list[tuple[str, int]]) -> dict[tuple[str, int], int]:
    base = target_size // len(strata)
    remainder = target_size % len(strata)
    allocation = {stratum: base for stratum in strata}
    for stratum in strata[:remainder]:
        allocation[stratum] += 1
    return allocation


def choose_sample(candidates: list[dict[str, Any]], target_size: int, seed: int, years: list[int]) -> list[dict[str, Any]]:
    by_stratum: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    strata_order: list[tuple[str, int]] = []
    for bucket in ("core", "adjacent"):
        for year in years:
            strata_order.append((bucket, year))
    for row in candidates:
        by_stratum[(row["bucket"], int(row["publication_year"]))].append(row)

    rng = random.Random(seed)
    for rows in by_stratum.values():
        rows.sort(key=lambda row: (row["abstract_quality"], row["cited_by_count"], row["work_id_short"]))
        rng.shuffle(rows)

    allocation = allocate_counts(target_size, strata_order)
    selected: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []

    for stratum in strata_order:
        rows = by_stratum.get(stratum, [])
        take = min(allocation[stratum], len(rows))
        selected.extend(rows[:take])
        leftovers.extend(rows[take:])

    if len(selected) < target_size:
        rng.shuffle(leftovers)
        deficit = target_size - len(selected)
        selected.extend(leftovers[:deficit])

    selected.sort(key=lambda row: (row["bucket"], row["publication_year"], row["work_id_short"]))
    return selected[:target_size]


def main() -> None:
    args = parse_args()
    registry = load_registry(Path(args.registry_csv))
    years = set(args.years)
    candidates = build_candidates(Path(args.recent_dir), registry, years)
    if not candidates:
        raise SystemExit("No extraction-ready candidates found for the requested years.")

    if args.all_candidates:
        sample = sorted(candidates, key=lambda row: (row["bucket"], row["publication_year"], row["work_id_short"]))
    else:
        sample = choose_sample(candidates, args.target_size, args.seed, sorted(years))
    if not sample:
        raise SystemExit("Failed to select any pilot sample rows.")

    output_path = Path(args.output_jsonl)
    manifest_path = Path(args.manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for row in sample:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    candidates_by_stratum = Counter((row["bucket"], int(row["publication_year"])) for row in candidates)
    sample_by_stratum = Counter((row["bucket"], int(row["publication_year"])) for row in sample)
    sample_quality = Counter(row["abstract_quality"] for row in sample)

    manifest = {
        "target_size": None if args.all_candidates else args.target_size,
        "all_candidates": args.all_candidates,
        "selected_size": len(sample),
        "seed": args.seed,
        "years": sorted(years),
        "source_registry_path": str(Path(args.registry_csv)),
        "recent_dir": str(Path(args.recent_dir)),
        "output_jsonl": str(output_path),
        "candidates_total": len(candidates),
        "candidates_by_stratum": {f"{bucket}:{year}": count for (bucket, year), count in sorted(candidates_by_stratum.items())},
        "sample_by_stratum": {f"{bucket}:{year}": count for (bucket, year), count in sorted(sample_by_stratum.items())},
        "sample_abstract_quality": dict(sorted(sample_quality.items())),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote pilot sample: {output_path} ({len(sample)} rows)")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
