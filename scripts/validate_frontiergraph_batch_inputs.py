from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_BATCH_DIR = "data/pilots/frontiergraph_extraction_v2/batch_inputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FrontierGraph batch JSONL inputs before upload.")
    parser.add_argument("--batch-dir", required=True)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if line:
                yield line_no, json.loads(line)


def validate_line(payload: dict[str, Any], path: Path, line_no: int) -> list[str]:
    errors: list[str] = []
    if payload.get("method") != "POST":
        errors.append(f"{path.name}:{line_no} method must be POST")
    if payload.get("url") != "/v1/responses":
        errors.append(f"{path.name}:{line_no} url must be /v1/responses")
    if not isinstance(payload.get("custom_id"), str) or not payload["custom_id"]:
        errors.append(f"{path.name}:{line_no} missing custom_id")
    body = payload.get("body")
    if not isinstance(body, dict):
        errors.append(f"{path.name}:{line_no} missing body object")
        return errors
    if not body.get("model"):
        errors.append(f"{path.name}:{line_no} missing model")
    if not isinstance(body.get("input"), list):
        errors.append(f"{path.name}:{line_no} body.input must be a list")
    text = body.get("text")
    if not isinstance(text, dict) or not isinstance(text.get("format"), dict):
        errors.append(f"{path.name}:{line_no} missing text.format")
    else:
        fmt = text["format"]
        if fmt.get("type") != "json_schema":
            errors.append(f"{path.name}:{line_no} text.format.type must be json_schema")
        if fmt.get("strict") is not True:
            errors.append(f"{path.name}:{line_no} text.format.strict should be true")
        if not isinstance(fmt.get("schema"), dict):
            errors.append(f"{path.name}:{line_no} schema must be an object")
    return errors


def main() -> None:
    args = parse_args()
    batch_dir = Path(args.batch_dir)
    if not batch_dir.exists():
        raise SystemExit(f"Batch directory not found: {batch_dir}")

    jsonl_files = sorted(batch_dir.glob("*.jsonl"))
    if not jsonl_files:
        raise SystemExit(f"No JSONL files found in {batch_dir}")

    all_errors: list[str] = []
    for path in jsonl_files:
        seen_ids: set[str] = set()
        line_count = 0
        for line_no, payload in iter_jsonl(path):
            line_count += 1
            errors = validate_line(payload, path, line_no)
            custom_id = payload.get("custom_id")
            if isinstance(custom_id, str):
                if custom_id in seen_ids:
                    errors.append(f"{path.name}:{line_no} duplicate custom_id {custom_id}")
                seen_ids.add(custom_id)
            all_errors.extend(errors)
        print(f"{path.name}: {line_count} requests, {len(seen_ids)} unique custom_ids")

    if all_errors:
        print("\nValidation errors:")
        for err in all_errors:
            print(err)
        raise SystemExit(1)

    print("\nBatch inputs validated successfully.")


if __name__ == "__main__":
    main()
