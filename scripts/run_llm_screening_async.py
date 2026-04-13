from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openai


DEFAULT_INPUTS = [
    "outputs/paper/99_llm_screening_prompt_pack_endpoint_first/prompt_a_batch_2000.jsonl",
    "outputs/paper/99_llm_screening_prompt_pack_endpoint_first/prompt_b_batch_2000.jsonl",
    "outputs/paper/99_llm_screening_prompt_pack_endpoint_first/prompt_c_batch_2000.jsonl",
]


@dataclass
class WorkItem:
    source_name: str
    source_path: Path
    custom_id: str
    body: dict[str, Any]


def _load_api_key(args: argparse.Namespace) -> None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return
    if args.api_key_file:
        key_path = Path(args.api_key_file)
        if not key_path.exists():
            raise SystemExit(f"API key file not found: {key_path}")
        os.environ["OPENAI_API_KEY"] = key_path.read_text(encoding="utf-8").strip()
        return
    raise SystemExit(
        "OPENAI_API_KEY is not set. Provide --api-key-file or export OPENAI_API_KEY."
    )


def _iter_requests(path: Path, max_requests: int | None = None) -> list[WorkItem]:
    rows: list[WorkItem] = []
    with path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if max_requests is not None and idx >= max_requests:
                break
            payload = json.loads(line)
            rows.append(
                WorkItem(
                    source_name=path.stem,
                    source_path=path,
                    custom_id=str(payload["custom_id"]),
                    body=dict(payload["body"]),
                )
            )
    return rows


def _completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            custom_id = payload.get("custom_id")
            if custom_id:
                done.add(str(custom_id))
    return done


def _apply_overrides(body: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    out = json.loads(json.dumps(body))
    if args.model:
        out["model"] = args.model
    if args.reasoning_effort:
        out["reasoning"] = {"effort": args.reasoning_effort}
    if args.max_output_tokens is not None:
        out["max_output_tokens"] = int(args.max_output_tokens)
    return out


def _is_retryable(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.InternalServerError,
        ),
    ):
        return True
    if isinstance(exc, openai.APIStatusError):
        return int(getattr(exc, "status_code", 0) or 0) >= 500
    return False


def _error_payload(exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        payload["status_code"] = status_code
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload["response"] = response.json()
        except Exception:
            payload["response_text"] = getattr(response, "text", None)
    return payload


async def _append_jsonl(path: Path, row: dict[str, Any], lock: asyncio.Lock) -> None:
    async with lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


async def _run_requests(args: argparse.Namespace, work_items: list[WorkItem], out_dir: Path) -> None:
    client = openai.AsyncOpenAI(timeout=float(args.timeout), max_retries=0)
    sem = asyncio.Semaphore(int(args.concurrency))
    file_locks: dict[str, asyncio.Lock] = {}
    results_path = out_dir / "responses.jsonl"
    errors_path = out_dir / "errors.jsonl"
    existing_done = _completed_ids(results_path) if args.resume else set()
    todo = [item for item in work_items if item.custom_id not in existing_done]

    stats = {
        "requested": len(work_items),
        "skipped_completed": len(work_items) - len(todo),
        "completed": 0,
        "failed": 0,
        "started_at": time.time(),
    }

    progress_every = max(1, int(args.progress_every))

    async def handle(item: WorkItem) -> None:
        nonlocal stats
        async with sem:
            body = _apply_overrides(item.body, args)
            last_exc: Exception | None = None
            for attempt in range(int(args.max_retries) + 1):
                try:
                    response = await client.responses.create(**body)
                    row = {
                        "custom_id": item.custom_id,
                        "source_name": item.source_name,
                        "source_path": str(item.source_path),
                        "response": response.model_dump(mode="json"),
                    }
                    await _append_jsonl(results_path, row, file_locks.setdefault("results", asyncio.Lock()))
                    stats["completed"] += 1
                    total_done = stats["completed"] + stats["failed"]
                    if total_done % progress_every == 0 or total_done == len(todo):
                        elapsed = time.time() - stats["started_at"]
                        rate = total_done / elapsed if elapsed > 0 else 0.0
                        print(
                            f"[progress] {total_done}/{len(todo)} done, "
                            f"completed={stats['completed']}, failed={stats['failed']}, rate={rate:.2f}/s",
                            flush=True,
                        )
                    return
                except Exception as exc:
                    last_exc = exc
                    if attempt < int(args.max_retries) and _is_retryable(exc):
                        await asyncio.sleep(float(args.initial_backoff) * (2**attempt))
                        continue
                    error_row = {
                        "custom_id": item.custom_id,
                        "source_name": item.source_name,
                        "source_path": str(item.source_path),
                        "attempts": attempt + 1,
                        **_error_payload(exc),
                    }
                    await _append_jsonl(errors_path, error_row, file_locks.setdefault("errors", asyncio.Lock()))
                    stats["failed"] += 1
                    total_done = stats["completed"] + stats["failed"]
                    if total_done % progress_every == 0 or total_done == len(todo):
                        elapsed = time.time() - stats["started_at"]
                        rate = total_done / elapsed if elapsed > 0 else 0.0
                        print(
                            f"[progress] {total_done}/{len(todo)} done, "
                            f"completed={stats['completed']}, failed={stats['failed']}, rate={rate:.2f}/s",
                            flush=True,
                        )
                    return
            if last_exc is not None:
                raise last_exc

    print(
        f"Launching {len(todo)} requests "
        f"(skipping {stats['skipped_completed']} already completed) "
        f"with concurrency={args.concurrency}",
        flush=True,
    )
    await asyncio.gather(*(handle(item) for item in todo))
    stats["finished_at"] = time.time()
    stats["elapsed_seconds"] = stats["finished_at"] - stats["started_at"]
    summary = {
        **stats,
        "out_dir": str(out_dir),
        "inputs": sorted({str(item.source_path) for item in work_items}),
        "model_override": args.model,
        "reasoning_effort_override": args.reasoning_effort,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run prepared LLM screening JSONL files asynchronously.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=DEFAULT_INPUTS,
        help="Prepared request JSONL files. Defaults to the endpoint-first 99 pack A/B/C files.",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/100_llm_screening_async_runs",
        help="Output directory for responses, errors, and summary.",
    )
    parser.add_argument(
        "--api-key-file",
        default="/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt",
        help="Optional path to a file containing the OpenAI API key.",
    )
    parser.add_argument("--concurrency", type=int, default=96)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--initial-backoff", type=float, default=1.5)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--model", default=None, help="Optional model override.")
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        choices=["minimal", "low", "medium", "high", "xhigh", "none"],
        help="Optional reasoning effort override applied to all requests.",
    )
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--max-requests", type=int, default=None, help="Limit requests per input file for smoke testing.")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    args = parser.parse_args()

    _load_api_key(args)

    input_paths = [Path(p) for p in args.inputs]
    missing = [str(p) for p in input_paths if not p.exists()]
    if missing:
        raise SystemExit(f"Missing input files: {missing}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    work_items: list[WorkItem] = []
    for path in input_paths:
        work_items.extend(_iter_requests(path, max_requests=args.max_requests))

    if not work_items:
        raise SystemExit("No work items loaded.")

    asyncio.run(_run_requests(args, work_items, out_dir))


if __name__ == "__main__":
    main()
