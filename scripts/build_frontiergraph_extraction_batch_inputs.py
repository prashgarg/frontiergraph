from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_JSONL = "data/pilots/frontiergraph_extraction_v2/pilot_sample.jsonl"
DEFAULT_CONDITIONS_JSON = "prompts/frontiergraph_extraction_v2/pilot_conditions.json"
DEFAULT_SYSTEM_PROMPT = "prompts/frontiergraph_extraction_v2/system_prompt.md"
DEFAULT_USER_PROMPT = "prompts/frontiergraph_extraction_v2/user_prompt_template.md"
DEFAULT_SCHEMA_JSON = "prompts/frontiergraph_extraction_v2/schema.json"
DEFAULT_OUTPUT_ROOT = "data/pilots/frontiergraph_extraction_v2/batch_inputs"
DEFAULT_MAX_OUTPUT_TOKENS = 25000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FrontierGraph extraction batch JSONL files, one per model/reasoning condition.")
    parser.add_argument("--sample-jsonl", default=DEFAULT_SAMPLE_JSONL)
    parser.add_argument("--conditions-json", default=DEFAULT_CONDITIONS_JSON)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--user-prompt", default=DEFAULT_USER_PROMPT)
    parser.add_argument("--schema-json", default=DEFAULT_SCHEMA_JSON)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--batch-name", default=None)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--condition-id", action="append", default=[])
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
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


def short_work_id(openalex_work_id: str) -> str:
    return openalex_work_id.rstrip("/").split("/")[-1]


def request_jsonl_name(batch_name: str, condition_id: str) -> str:
    if condition_id in batch_name:
        return f"{batch_name}.jsonl"
    return f"{batch_name}__{condition_id}.jsonl"


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    sample_rows = list(iter_jsonl(Path(args.sample_jsonl)))
    if args.start < 0:
        raise SystemExit("--start must be non-negative.")
    if args.start:
        sample_rows = sample_rows[args.start :]
    if args.limit is not None:
        sample_rows = sample_rows[: args.limit]
    conditions = load_json(Path(args.conditions_json))
    if args.condition_id:
        wanted = set(args.condition_id)
        conditions = [row for row in conditions if row["condition_id"] in wanted]
    if not sample_rows:
        raise SystemExit("No sample rows available.")
    if not conditions:
        raise SystemExit("No conditions selected.")

    system_prompt = load_text(Path(args.system_prompt))
    user_prompt_template = load_text(Path(args.user_prompt))
    schema = load_json(Path(args.schema_json))

    batch_name = args.batch_name or datetime.now(timezone.utc).strftime("batch_pack_%Y%m%dT%H%M%SZ")
    batch_dir = Path(args.output_root) / batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "batch_name": batch_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_jsonl": str(Path(args.sample_jsonl)),
        "start": args.start,
        "sample_size": len(sample_rows),
        "conditions_json": str(Path(args.conditions_json)),
        "system_prompt": str(Path(args.system_prompt)),
        "user_prompt": str(Path(args.user_prompt)),
        "schema_json": str(Path(args.schema_json)),
        "max_output_tokens": args.max_output_tokens,
        "files": [],
    }

    sample_by_stratum = Counter((row["bucket"], int(row["publication_year"])) for row in sample_rows)

    for condition in conditions:
        condition_id = str(condition["condition_id"])
        model = str(condition["model"])
        reasoning_effort = str(condition["reasoning_effort"])
        out_path = batch_dir / request_jsonl_name(batch_name, condition_id)
        count = 0
        custom_ids: list[str] = []
        with out_path.open("w", encoding="utf-8") as handle:
            for row in sample_rows:
                work_id_short = short_work_id(str(row["openalex_work_id"]))
                custom_id = f"{work_id_short}__{condition_id}"
                custom_ids.append(custom_id)
                body = {
                    "model": model,
                    "reasoning": {"effort": reasoning_effort},
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
                count += 1

        manifest["files"].append(
            {
                "condition_id": condition_id,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "request_count": count,
                "jsonl_path": str(out_path),
                "custom_id_unique": len(custom_ids) == len(set(custom_ids)),
            }
        )

    manifest["sample_by_stratum"] = {f"{bucket}:{year}": n for (bucket, year), n in sorted(sample_by_stratum.items())}
    write_json(batch_dir / "manifest.json", manifest)
    print(f"Wrote batch pack: {batch_dir}")
    print(f"Wrote manifest: {batch_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
