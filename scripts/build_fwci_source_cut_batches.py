from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_JSONL = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/sample/fwci_core150_adj150_remaining.jsonl"
DEFAULT_SYSTEM_PROMPT = "prompts/frontiergraph_extraction_v2/system_prompt.md"
DEFAULT_USER_PROMPT = "prompts/frontiergraph_extraction_v2/user_prompt_template.md"
DEFAULT_SCHEMA_JSON = "prompts/frontiergraph_extraction_v2/schema.json"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/batch_inputs"
DEFAULT_MAX_OUTPUT_TOKENS = 25000
DEFAULT_MAX_REQUESTS = 10000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build year/part batch JSONL files for the FWCI source-cut sample.")
    parser.add_argument("--sample-jsonl", default=DEFAULT_SAMPLE_JSONL)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--user-prompt", default=DEFAULT_USER_PROMPT)
    parser.add_argument("--schema-json", default=DEFAULT_SCHEMA_JSON)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--batch-prefix", default="fwci150x150")
    parser.add_argument("--condition-id", default="gpt5mini_low")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    parser.add_argument("--from-year", type=int, default=None, help="Highest year to include.")
    parser.add_argument("--to-year", type=int, default=None, help="Lowest year to include.")
    parser.add_argument("--exclude-year", type=int, action="append", default=[])
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


def render_user_prompt(template: str, row: dict[str, Any]) -> str:
    replacements = {
        "{{paper_title}}": str(row.get("title", "")),
        "{{paper_abstract}}": str(row.get("abstract", "")),
        "{{title}}": str(row.get("title", "")),
        "{{abstract}}": str(row.get("abstract", "")),
        "{{openalex_work_id}}": str(row.get("openalex_work_id", "")),
    }
    rendered = template
    for needle, value in replacements.items():
        rendered = rendered.replace(needle, value)
    return rendered


def short_work_id(openalex_work_id: str) -> str:
    return openalex_work_id.rstrip("/").split("/")[-1]


def request_jsonl_name(batch_name: str, condition_id: str) -> str:
    if condition_id in batch_name:
        return f"{batch_name}.jsonl"
    return f"{batch_name}__{condition_id}.jsonl"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.sample_jsonl)))
    exclude_years = set(args.exclude_year)
    if args.from_year is not None:
        rows = [row for row in rows if int(row["publication_year"]) <= args.from_year]
    if args.to_year is not None:
        rows = [row for row in rows if int(row["publication_year"]) >= args.to_year]
    if exclude_years:
        rows = [row for row in rows if int(row["publication_year"]) not in exclude_years]

    system_prompt = load_text(Path(args.system_prompt))
    user_prompt_template = load_text(Path(args.user_prompt))
    schema = load_json(Path(args.schema_json))

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["publication_year"])].append(row)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_jsonl": str(Path(args.sample_jsonl)),
        "batch_prefix": args.batch_prefix,
        "condition_id": args.condition_id,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": args.max_output_tokens,
        "max_requests": args.max_requests,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "exclude_years": sorted(exclude_years),
        "batches": [],
    }

    for year in sorted(grouped, reverse=True):
        year_rows = grouped[year]
        total_parts = math.ceil(len(year_rows) / args.max_requests)
        for idx in range(total_parts):
            part = idx + 1
            start = idx * args.max_requests
            end = start + args.max_requests
            chunk = year_rows[start:end]
            batch_name = f"{args.batch_prefix}_y{year}_part{part:02d}_{args.condition_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            batch_dir = output_root / batch_name
            batch_dir.mkdir(parents=True, exist_ok=True)

            sample_jsonl = batch_dir / f"{batch_name}.sample.jsonl"
            with sample_jsonl.open("w", encoding="utf-8") as sample_handle:
                for row in chunk:
                    sample_handle.write(json.dumps(row, ensure_ascii=False) + "\n")

            request_jsonl = batch_dir / request_jsonl_name(batch_name, args.condition_id)
            with request_jsonl.open("w", encoding="utf-8") as handle:
                for row in chunk:
                    custom_id = f"{short_work_id(str(row['openalex_work_id']))}__{args.condition_id}"
                    body = {
                        "model": args.model,
                        "reasoning": {"effort": args.reasoning_effort},
                        "instructions": system_prompt,
                        "input": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": render_user_prompt(user_prompt_template, row),
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
                    payload = {
                        "custom_id": custom_id,
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": body,
                    }
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

            batch_manifest = {
                "batch_name": batch_name,
                "year": year,
                "part": part,
                "total_parts_for_year": total_parts,
                "request_count": len(chunk),
                "sample_jsonl": str(sample_jsonl),
                "jsonl_path": str(request_jsonl),
                "condition_id": args.condition_id,
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "max_output_tokens": args.max_output_tokens,
            }
            write_json(batch_dir / "manifest.json", batch_manifest)
            manifest["batches"].append(batch_manifest)

    write_json(output_root / f"{args.batch_prefix}_manifest.json", manifest)
    print(json.dumps({"batch_count": len(manifest["batches"]), "total_requests": sum(b["request_count"] for b in manifest["batches"])}, indent=2))


if __name__ == "__main__":
    main()
