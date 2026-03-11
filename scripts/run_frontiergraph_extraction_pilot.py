from __future__ import annotations

import asyncio
import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_JSONL = "data/pilots/frontiergraph_extraction_v2/pilot_sample.jsonl"
DEFAULT_CONDITIONS_JSON = "prompts/frontiergraph_extraction_v2/pilot_conditions.json"
DEFAULT_SYSTEM_PROMPT = "prompts/frontiergraph_extraction_v2/system_prompt.md"
DEFAULT_USER_PROMPT = "prompts/frontiergraph_extraction_v2/user_prompt_template.md"
DEFAULT_SCHEMA_JSON = "prompts/frontiergraph_extraction_v2/schema.json"
DEFAULT_OUTPUT_ROOT = "data/pilots/frontiergraph_extraction_v2/runs"
DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"
DEFAULT_MAX_OUTPUT_TOKENS = 25000
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_SLEEP_SECONDS = 0.0
DEFAULT_MAX_CONCURRENCY = 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the 4-condition FrontierGraph extraction pilot via the OpenAI Responses API.")
    parser.add_argument("--sample-jsonl", default=DEFAULT_SAMPLE_JSONL)
    parser.add_argument("--conditions-json", default=DEFAULT_CONDITIONS_JSON)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--user-prompt", default=DEFAULT_USER_PROMPT)
    parser.add_argument("--schema-json", default=DEFAULT_SCHEMA_JSON)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--condition-id", action="append", default=[])
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY)
    parser.add_argument("--api-base", default="https://api.openai.com/v1")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_api_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"API key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"API key file is empty: {path}")
    return key


def short_work_id(openalex_work_id: str) -> str:
    return openalex_work_id.rstrip("/").split("/")[-1]


def render_user_prompt(template: str, row: dict[str, Any]) -> str:
    return (
        template.replace("{{paper_title}}", str(row["title"]))
        .replace("{{paper_abstract}}", str(row["abstract"]))
    )


def extract_output_json(response_json: dict[str, Any]) -> Any:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return json.loads(output_text)

    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return json.loads(text)

    raise ValueError("Could not locate structured JSON output in the Responses API payload.")


def post_response(*, api_base: str, api_key: str, body: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url=f"{api_base.rstrip('/')}/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


async def async_main() -> None:
    args = parse_args()
    system_prompt = load_text(Path(args.system_prompt))
    user_prompt_template = load_text(Path(args.user_prompt))
    schema = load_json(Path(args.schema_json))
    conditions = load_json(Path(args.conditions_json))
    sample_rows = list(iter_jsonl(Path(args.sample_jsonl)))
    if args.limit is not None:
        sample_rows = sample_rows[: args.limit]
    if args.condition_id:
        wanted = set(args.condition_id)
        conditions = [row for row in conditions if row["condition_id"] in wanted]

    if not sample_rows:
        raise SystemExit("No sample rows available to run.")
    if not conditions:
        raise SystemExit("No pilot conditions selected.")

    run_name = args.run_name or datetime.now(timezone.utc).strftime("pilot_%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output_root) / run_name
    responses_dir = run_dir / "responses"
    parsed_path = run_dir / "parsed_results.jsonl"
    errors_path = run_dir / "errors.jsonl"
    requests_path = run_dir / "request_manifest.json"
    manifest_path = run_dir / "run_manifest.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    api_key = None if args.dry_run else load_api_key(Path(args.api_key_path))

    request_manifest = {
        "run_name": run_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_jsonl": str(Path(args.sample_jsonl)),
        "conditions_json": str(Path(args.conditions_json)),
        "system_prompt": str(Path(args.system_prompt)),
        "user_prompt": str(Path(args.user_prompt)),
        "schema_json": str(Path(args.schema_json)),
        "api_base": args.api_base,
        "api_key_path": str(Path(args.api_key_path)),
        "dry_run": args.dry_run,
        "sample_size": len(sample_rows),
        "conditions": conditions,
        "max_output_tokens": args.max_output_tokens,
        "max_concurrency": args.max_concurrency,
    }
    write_json(requests_path, request_manifest)

    total_requests = len(sample_rows) * len(conditions)
    existing_success = count_jsonl_rows(parsed_path)
    existing_fail = count_jsonl_rows(errors_path)
    completed = existing_success + existing_fail
    succeeded = existing_success
    failed = existing_fail
    started_at = time.time()

    pending: list[tuple[dict[str, Any], dict[str, Any], str, Path, dict[str, Any]]] = []
    for row in sample_rows:
        work_id_short = short_work_id(str(row["openalex_work_id"]))
        for condition in conditions:
            condition_id = str(condition["condition_id"])
            custom_id = f"{work_id_short}__{condition_id}"
            raw_path = responses_dir / f"{custom_id}.json"
            if raw_path.exists():
                continue
            user_text = render_user_prompt(user_prompt_template, row)
            body = {
                "model": condition["model"],
                "reasoning": {"effort": condition["reasoning_effort"]},
                "instructions": system_prompt,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_text,
                            }
                        ],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "frontiergraph_paper_graph_v2",
                        "strict": True,
                        "schema": schema,
                    }
                },
                "max_output_tokens": args.max_output_tokens,
            }
            pending.append((row, condition, custom_id, raw_path, body))

    progress_lock = asyncio.Lock()
    file_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(max(1, args.max_concurrency))

    async def worker(item: tuple[dict[str, Any], dict[str, Any], str, Path, dict[str, Any]]) -> None:
        nonlocal completed, succeeded, failed
        row, condition, custom_id, raw_path, body = item
        work_id_short = short_work_id(str(row["openalex_work_id"]))
        status = "fail"
        response_json = None

        async with semaphore:
            try:
                if args.dry_run:
                    async with file_lock:
                        write_json(raw_path, {"custom_id": custom_id, "request_body": body})
                    status = "ok"
                    error_payload = None
                    response_json = None
                else:
                    response_json = await asyncio.to_thread(
                        post_response,
                        api_base=args.api_base,
                        api_key=api_key,
                        body=body,
                        timeout_seconds=args.timeout_seconds,
                    )
                    async with file_lock:
                        write_json(raw_path, response_json)
                    parsed_output = extract_output_json(response_json)
                    async with file_lock:
                        append_jsonl(
                            parsed_path,
                            {
                                "custom_id": custom_id,
                                "openalex_work_id": row["openalex_work_id"],
                                "work_id_short": work_id_short,
                                "condition_id": condition["condition_id"],
                                "model": condition["model"],
                                "reasoning_effort": condition["reasoning_effort"],
                                "publication_year": row["publication_year"],
                                "bucket": row["bucket"],
                                "source_name": row.get("source_name") or row.get("source_display_name", ""),
                                "abstract_quality": row.get("abstract_quality", "NA"),
                                "response_id": response_json.get("id"),
                                "output": parsed_output,
                            },
                        )
                    status = "ok"
                    error_payload = None
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                socket.timeout,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                status = "fail"
                error_payload = {
                    "custom_id": custom_id,
                    "openalex_work_id": row["openalex_work_id"],
                    "condition_id": condition["condition_id"],
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                }
                if isinstance(exc, urllib.error.HTTPError):
                    try:
                        body_text = exc.read().decode("utf-8", errors="replace")
                    except Exception:
                        body_text = ""
                    if body_text:
                        error_payload["error_body"] = body_text
                async with file_lock:
                    append_jsonl(errors_path, error_payload)
            finally:
                async with progress_lock:
                    completed += 1
                    if status == "ok":
                        succeeded += 1
                    else:
                        failed += 1
                    elapsed = time.time() - started_at
                    print(
                        f"[{completed}/{total_requests}] {custom_id} | ok={succeeded} fail={failed} elapsed={elapsed:.1f}s",
                        file=sys.stderr,
                    )
                if args.sleep_seconds > 0:
                    await asyncio.sleep(args.sleep_seconds)

    await asyncio.gather(*(worker(item) for item in pending))

    manifest = {
        **request_manifest,
        "completed_requests": completed,
        "succeeded_requests": succeeded,
        "failed_requests": failed,
        "run_dir": str(run_dir),
        "responses_dir": str(responses_dir),
        "parsed_results_path": str(parsed_path),
        "errors_path": str(errors_path),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - started_at, 3),
    }
    write_json(manifest_path, manifest)
    print(f"Wrote run manifest: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(async_main())
