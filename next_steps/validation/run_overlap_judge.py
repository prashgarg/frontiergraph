from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_frontiergraph_extraction_pilot import (
    append_jsonl,
    count_jsonl_rows,
    extract_output_json,
    load_api_key,
    load_json,
    load_text,
    post_response,
    write_json,
)


DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"
DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_MAX_OUTPUT_TOKENS = 12000
DEFAULT_MAX_CONCURRENCY = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM-based graph overlap judging on prepared judge inputs.")
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--system-prompt", required=True)
    parser.add_argument("--user-prompt", required=True)
    parser.add_argument("--schema-json", required=True)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--output-root", default="data/pilots/frontiergraph_extraction_v2/judge_runs")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--schema-name", default="graph_overlap_judge")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def prompt_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def render_user_prompt(template: str, row: dict[str, Any]) -> str:
    rendered = template
    for key, value in row.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", prompt_value(value))
    return rendered


async def async_main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.input_jsonl)))
    if not rows:
        raise SystemExit("No judge rows found.")

    system_prompt = load_text(Path(args.system_prompt))
    user_template = load_text(Path(args.user_prompt))
    schema = load_json(Path(args.schema_json))
    api_key = load_api_key(Path(args.api_key_path))

    run_dir = Path(args.output_root) / args.run_name
    responses_dir = run_dir / "responses"
    parsed_path = run_dir / "parsed_results.jsonl"
    errors_path = run_dir / "errors.jsonl"
    manifest_path = run_dir / "run_manifest.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        manifest_path,
        {
            "input_jsonl": str(Path(args.input_jsonl)),
            "system_prompt": str(Path(args.system_prompt)),
            "user_prompt": str(Path(args.user_prompt)),
            "schema_json": str(Path(args.schema_json)),
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "timeout_seconds": args.timeout_seconds,
            "max_output_tokens": args.max_output_tokens,
            "row_count": len(rows),
        },
    )

    semaphore = asyncio.Semaphore(max(1, args.max_concurrency))
    file_lock = asyncio.Lock()

    async def worker(row: dict[str, Any]) -> None:
        benchmark_id = str(row["benchmark_id"])
        prompt_family = str(row["prompt_family"])
        custom_id = f"{benchmark_id}__{prompt_family}__judge"
        raw_path = responses_dir / f"{custom_id}.json"
        if raw_path.exists():
            return
        user_text = render_user_prompt(user_template, row)
        body = {
            "model": args.model,
            "reasoning": {"effort": args.reasoning_effort},
            "instructions": system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": args.schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": args.max_output_tokens,
        }

        async with semaphore:
            try:
                response_json = await asyncio.to_thread(
                    post_response,
                    api_base=args.api_base,
                    api_key=api_key,
                    body=body,
                    timeout_seconds=args.timeout_seconds,
                )
                parsed_output = extract_output_json(response_json)
                async with file_lock:
                    write_json(raw_path, response_json)
                    append_jsonl(
                        parsed_path,
                        {
                            "custom_id": custom_id,
                            "benchmark_id": benchmark_id,
                            "benchmark_dataset": row["benchmark_dataset"],
                            "prompt_family": prompt_family,
                            "condition_id": row["condition_id"],
                            "source_model": row["model"],
                            "source_reasoning_effort": row["reasoning_effort"],
                            "judge_model": args.model,
                            "judge_reasoning_effort": args.reasoning_effort,
                            "output": parsed_output,
                        },
                    )
            except Exception as exc:  # noqa: BLE001
                async with file_lock:
                    append_jsonl(
                        errors_path,
                        {
                            "custom_id": custom_id,
                            "benchmark_id": benchmark_id,
                            "prompt_family": prompt_family,
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )

    await asyncio.gather(*(worker(row) for row in rows))

    write_json(
        run_dir / "run_status.json",
        {
            "completed": count_jsonl_rows(parsed_path),
            "failed": count_jsonl_rows(errors_path),
        },
    )


if __name__ == "__main__":
    asyncio.run(async_main())
