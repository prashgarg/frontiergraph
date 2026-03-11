from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit FWCI source-cut batch extraction coverage and usage.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--out-json", default=None)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def short_work_id(work_id: str) -> str:
    return work_id.rstrip("/").split("/")[-1]


def collect_expected_ids(sample_jsonl: Path) -> set[str]:
    return {str(row["custom_id"]) if "custom_id" in row else f"{short_work_id(str(row['openalex_work_id']))}__gpt5mini_low" for row in iter_jsonl(sample_jsonl)}


def collect_preexisting_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for row in iter_jsonl(path):
        custom_id = row.get("custom_id")
        if isinstance(custom_id, str) and custom_id:
            ids.add(custom_id)
    return ids


def collect_output_ids(path: Path) -> tuple[set[str], int]:
    ids: set[str] = set()
    lines = 0
    for row in iter_jsonl(path):
        lines += 1
        custom_id = row.get("custom_id")
        if isinstance(custom_id, str) and custom_id:
            ids.add(custom_id)
    return ids, lines


def collect_error_ids(path: Path) -> tuple[set[str], int]:
    ids: set[str] = set()
    lines = 0
    for row in iter_jsonl(path):
        lines += 1
        custom_id = row.get("custom_id")
        if isinstance(custom_id, str) and custom_id:
            ids.add(custom_id)
    return ids, lines


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    batch_inputs_dir = output_root / "batch_inputs"
    batch_outputs_dir = output_root / "batch_outputs"
    sample_jsonl = output_root / "sample" / "fwci_core150_adj150_all.jsonl"
    completed_jsonl = output_root / "completed" / "completed_successes.jsonl"

    batch_dirs = sorted([p for p in batch_inputs_dir.iterdir() if p.is_dir() and (p / "manifest.json").exists()])

    status_counts: Counter[str] = Counter()
    total_request_counts = Counter()
    usage_totals = Counter()
    missing_submission_dirs: list[str] = []
    missing_poll_dirs: list[str] = []
    completed_without_output_download: list[str] = []
    completed_with_error_file: list[str] = []
    batch_dir_summaries: list[dict[str, Any]] = []

    for batch_dir in batch_dirs:
        manifest_path = batch_dir / "manifest.json"
        submission_path = batch_dir / "submission.json"
        poll_path = batch_dir / "poll.json"
        manifest = read_json(manifest_path)
        batch_name = str(manifest.get("batch_name") or batch_dir.name)

        summary: dict[str, Any] = {
            "batch_dir": str(batch_dir),
            "batch_name": batch_name,
            "request_count_manifest": int(manifest.get("request_count") or 0),
            "has_submission": submission_path.exists(),
            "has_poll": poll_path.exists(),
        }

        if not submission_path.exists():
            missing_submission_dirs.append(str(batch_dir))
        else:
            submission = read_json(submission_path)
            summary["batch_id"] = (submission.get("batch") or {}).get("id") or submission.get("batch_id")

        if not poll_path.exists():
            missing_poll_dirs.append(str(batch_dir))
            batch_dir_summaries.append(summary)
            continue

        poll = read_json(poll_path)
        batch = poll.get("batch") or {}
        status = str(batch.get("status") or "unknown")
        status_counts[status] += 1
        summary["status"] = status
        request_counts = batch.get("request_counts") or {}
        for key in ("total", "completed", "failed"):
            total_request_counts[key] += int(request_counts.get(key) or 0)
            summary[f"request_{key}"] = int(request_counts.get(key) or 0)
        usage = batch.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or 0)
        cached_input_tokens = int(((usage.get("input_tokens_details") or {}).get("cached_tokens")) or 0)
        reasoning_tokens = int(((usage.get("output_tokens_details") or {}).get("reasoning_tokens")) or 0)
        usage_totals["input_tokens"] += input_tokens
        usage_totals["output_tokens"] += output_tokens
        usage_totals["total_tokens"] += total_tokens
        usage_totals["cached_input_tokens"] += cached_input_tokens
        usage_totals["reasoning_tokens"] += reasoning_tokens
        summary["input_tokens"] = input_tokens
        summary["output_tokens"] = output_tokens
        summary["total_tokens"] = total_tokens
        summary["cached_input_tokens"] = cached_input_tokens
        summary["reasoning_tokens"] = reasoning_tokens

        downloaded_output_path = poll.get("downloaded_output_path")
        downloaded_error_path = poll.get("downloaded_error_path")
        summary["downloaded_output_path"] = downloaded_output_path
        summary["downloaded_error_path"] = downloaded_error_path
        if status == "completed" and not downloaded_output_path:
            completed_without_output_download.append(str(batch_dir))
        if downloaded_error_path:
            completed_with_error_file.append(str(batch_dir))
        batch_dir_summaries.append(summary)

    output_files = sorted(batch_outputs_dir.glob("batch_*.output.jsonl"))
    error_files = sorted(batch_outputs_dir.glob("batch_*.error.jsonl"))

    output_ids: set[str] = set()
    error_ids: set[str] = set()
    downloaded_output_lines = 0
    downloaded_error_lines = 0

    for path in output_files:
        ids, lines = collect_output_ids(path)
        output_ids |= ids
        downloaded_output_lines += lines

    for path in error_files:
        ids, lines = collect_error_ids(path)
        error_ids |= ids
        downloaded_error_lines += lines

    expected_ids = collect_expected_ids(sample_jsonl)
    preexisting_ids = collect_preexisting_ids(completed_jsonl)
    success_ids = output_ids | preexisting_ids
    missing_expected_ids = sorted(expected_ids - success_ids)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "output_root": str(output_root),
            "sample_jsonl": str(sample_jsonl),
            "completed_successes_jsonl": str(completed_jsonl),
            "batch_inputs_dir": str(batch_inputs_dir),
            "batch_outputs_dir": str(batch_outputs_dir),
        },
        "batch_counts": {
            "batch_dirs": len(batch_dirs),
            "with_submission": len(batch_dirs) - len(missing_submission_dirs),
            "with_poll": len(batch_dirs) - len(missing_poll_dirs),
            "status_counts": dict(status_counts),
        },
        "request_totals": dict(total_request_counts),
        "usage_totals": {
            "input_tokens": usage_totals["input_tokens"],
            "output_tokens": usage_totals["output_tokens"],
            "total_tokens": usage_totals["total_tokens"],
            "cached_input_tokens": usage_totals["cached_input_tokens"],
            "uncached_input_tokens": usage_totals["input_tokens"] - usage_totals["cached_input_tokens"],
            "reasoning_tokens": usage_totals["reasoning_tokens"],
        },
        "downloads": {
            "output_file_count": len(output_files),
            "error_file_count": len(error_files),
            "downloaded_output_lines": downloaded_output_lines,
            "downloaded_error_lines": downloaded_error_lines,
        },
        "coverage": {
            "expected_custom_ids": len(expected_ids),
            "preexisting_completed_successes": len(preexisting_ids),
            "batch_output_successes": len(output_ids),
            "batch_error_ids": len(error_ids),
            "have_success_result_or_preexisting": len(success_ids),
            "missing_expected_count": len(missing_expected_ids),
            "missing_expected_sample": missing_expected_ids[:50],
        },
        "integrity": {
            "missing_submission_dirs": missing_submission_dirs,
            "missing_poll_dirs": missing_poll_dirs,
            "completed_without_output_download": completed_without_output_download,
            "completed_with_error_file": completed_with_error_file,
        },
        "batch_dir_summaries": batch_dir_summaries,
    }

    out_json = Path(args.out_json) if args.out_json else None
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
