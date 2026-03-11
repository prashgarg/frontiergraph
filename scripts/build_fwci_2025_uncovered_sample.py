from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the uncovered 2025 source-cut sample rows for FrontierGraph extraction.")
    parser.add_argument(
        "--sample-jsonl",
        default="data/production/frontiergraph_extraction_v2/fwci_core150_adj150/sample/fwci_core150_adj150_all.jsonl",
    )
    parser.add_argument(
        "--completed-jsonl",
        default="data/production/frontiergraph_extraction_v2/fwci_core150_adj150/completed/completed_successes.jsonl",
    )
    parser.add_argument(
        "--batch-output-dir",
        default="data/production/frontiergraph_extraction_v2/fwci_core150_adj150/batch_outputs",
    )
    parser.add_argument(
        "--output-jsonl",
        default="data/production/frontiergraph_extraction_v2/fwci_core150_adj150/sample/fwci_core150_adj150_2025_uncovered.jsonl",
    )
    parser.add_argument(
        "--output-manifest",
        default="data/production/frontiergraph_extraction_v2/fwci_core150_adj150/sample/fwci_core150_adj150_2025_uncovered_manifest.json",
    )
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def make_custom_id(openalex_work_id: str) -> str:
    short = openalex_work_id.rstrip("/").split("/")[-1]
    return f"{short}__gpt5mini_low"


def main() -> None:
    args = parse_args()
    sample_path = Path(args.sample_jsonl)
    completed_path = Path(args.completed_jsonl)
    batch_output_dir = Path(args.batch_output_dir)
    output_jsonl = Path(args.output_jsonl)
    output_manifest = Path(args.output_manifest)

    have_success: set[str] = set()
    for row in iter_jsonl(completed_path):
        have_success.add(row["custom_id"])

    for output_path in batch_output_dir.glob("*.output.jsonl"):
        for row in iter_jsonl(output_path):
            custom_id = row.get("custom_id")
            if custom_id:
                have_success.add(custom_id)

    kept_rows: list[dict] = []
    for row in iter_jsonl(sample_path):
        if int(row["publication_year"]) != 2025:
            continue
        custom_id = make_custom_id(str(row["openalex_work_id"]))
        if custom_id in have_success:
            continue
        kept_rows.append(row)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for row in kept_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "sample_jsonl": str(sample_path),
        "completed_jsonl": str(completed_path),
        "batch_output_dir": str(batch_output_dir),
        "output_jsonl": str(output_jsonl),
        "uncovered_2025_count": len(kept_rows),
    }
    output_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
