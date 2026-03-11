from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_BATCH_INPUT_ROOT = "data/production/frontiergraph_extraction_v2/batch_inputs"
DEFAULT_ERROR_GLOBS = [
    "/tmp/batch_*/*.errors.jsonl",
]
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2/failed_retries"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect failed FrontierGraph batch requests into retry-ready JSONL files.")
    parser.add_argument("--batch-input-root", default=DEFAULT_BATCH_INPUT_ROOT)
    parser.add_argument("--error-glob", action="append", default=[])
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def load_submission_map(batch_input_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sub_path in batch_input_root.glob("**/*.submission.json"):
        payload = json.loads(sub_path.read_text(encoding="utf-8"))
        batch = payload.get("batch", {})
        batch_id = batch.get("id")
        if batch_id:
            out[batch_id] = payload
    return out


def load_request_map(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    with jsonl_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            mapping[row["custom_id"]] = row
    return mapping


def main() -> None:
    args = parse_args()
    batch_input_root = Path(args.batch_input_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    error_globs = args.error_glob or DEFAULT_ERROR_GLOBS

    submission_map = load_submission_map(batch_input_root)
    error_paths: list[Path] = []
    for pattern in error_globs:
        error_paths.extend(Path("/").glob(pattern.lstrip("/")) if pattern.startswith("/") else batch_input_root.glob(pattern))
    error_paths = sorted(set(error_paths))

    manifest: dict[str, Any] = {
        "error_files": [str(path) for path in error_paths],
        "batches": [],
        "total_failed_requests": 0,
        "error_code_counts": {},
    }
    error_code_counts = Counter()

    for error_path in error_paths:
        batch_id = error_path.name.removesuffix(".errors.jsonl")
        submission = submission_map.get(batch_id)
        if not submission:
            manifest["batches"].append(
                {
                    "batch_id": batch_id,
                    "error_path": str(error_path),
                    "status": "missing_submission_metadata",
                }
            )
            continue

        request_jsonl = Path(submission["jsonl_path"])
        request_map = load_request_map(request_jsonl)
        batch_failures: list[dict[str, Any]] = []

        with error_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                custom_id = row.get("custom_id")
                error = row.get("response", {}).get("body", {}).get("error", {})
                batch_failures.append(
                    {
                        "custom_id": custom_id,
                        "status_code": row.get("response", {}).get("status_code"),
                        "error_code": error.get("code"),
                        "error_type": error.get("type"),
                        "error_message": error.get("message"),
                    }
                )
                error_code_counts[error.get("code") or "unknown"] += 1

        retry_stem = request_jsonl.parent.name
        retry_jsonl = output_root / f"{retry_stem}.failed_retry.jsonl"
        summary_json = output_root / f"{retry_stem}.failed_summary.json"
        missing_custom_ids: list[str] = []

        with retry_jsonl.open("w", encoding="utf-8") as out_handle:
            for failure in batch_failures:
                custom_id = failure["custom_id"]
                original = request_map.get(custom_id)
                if original is None:
                    missing_custom_ids.append(custom_id)
                    continue
                out_handle.write(json.dumps(original, ensure_ascii=False) + "\n")

        summary_payload = {
            "batch_id": batch_id,
            "batch_description": submission.get("batch", {}).get("metadata", {}).get("description"),
            "request_jsonl": str(request_jsonl),
            "error_path": str(error_path),
            "retry_jsonl": str(retry_jsonl),
            "failed_count": len(batch_failures),
            "missing_custom_ids_count": len(missing_custom_ids),
            "missing_custom_ids_sample": missing_custom_ids[:20],
            "error_code_counts": dict(Counter(f["error_code"] or "unknown" for f in batch_failures)),
            "failures_sample": batch_failures[:20],
        }
        summary_json.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        manifest["batches"].append(summary_payload)
        manifest["total_failed_requests"] += len(batch_failures)

    manifest["error_code_counts"] = dict(error_code_counts)
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
