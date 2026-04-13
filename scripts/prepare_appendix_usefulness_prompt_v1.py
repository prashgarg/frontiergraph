from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "outputs/paper/79_method_v2_human_validation_pack/human_validation_pack.csv"
DEFAULT_OUT_DIR = ROOT / "outputs/paper/117_appendix_usefulness_prompt_v1"


BASE_SYSTEM_PROMPT = """You are rating candidate research-question objects for current reader usefulness.

Judge only what is visible in the supplied record. Do not use outside knowledge, web search, topic prestige, publication prospects, or whether the question was later pursued in the literature.

You are not judging novelty, importance, truth, or likely future success.
You are judging only whether the item reads as a useful, intelligible research-question object to a current human reader.

Rate:
- readability: is the wording easy to read and parse?
- interpretability: can a reader tell what relationship or mechanism is being proposed?
- usefulness: is this a usable research-question object, even if it may still need revision?
- artifact_risk: does it read like a graph artifact rather than a real research question?

Score anchors:
- 5 = clear and strong
- 3 = understandable but mixed
- 1 = weak or unclear

artifact_risk anchors:
- low = reads like a normal research question
- medium = partly usable but somewhat artificial, generic, or awkward
- high = mostly reads like a graph artifact or malformed question object

Return JSON only.
Be concise and evidence-based."""


USER_TEMPLATE = """Evaluate this candidate for current reader usefulness only.

JSON record:
{record_json}"""


BASE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "item_id": {"type": "string"},
        "readability": {"type": "integer", "minimum": 1, "maximum": 5},
        "interpretability": {"type": "integer", "minimum": 1, "maximum": 5},
        "usefulness": {"type": "integer", "minimum": 1, "maximum": 5},
        "artifact_risk": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
    },
    "required": [
        "item_id",
        "readability",
        "interpretability",
        "usefulness",
        "artifact_risk",
    ],
}


def _pilot_selection(df: pd.DataFrame) -> pd.DataFrame:
    ordered = df.copy()
    ordered["row_in_stratum"] = (
        ordered.groupby(["comparison_group", "selection_horizon"]).cumcount()
    )

    keep_parts: list[pd.DataFrame] = []

    # One from each comparison-group x horizon stratum = 6.
    keep_parts.append(ordered[ordered["row_in_stratum"] == 0])

    # Add a second item for 5- and 10-year horizons in each group = 4 more.
    extra = ordered[
        (ordered["row_in_stratum"] == 1)
        & (ordered["selection_horizon"].isin([5, 10]))
    ]
    keep_parts.append(extra)

    pilot = pd.concat(keep_parts, ignore_index=True)
    pilot = pilot.sort_values(
        ["comparison_group", "selection_horizon", "row_in_stratum", "pair_key"],
        kind="mergesort",
    ).reset_index(drop=True)
    pilot["item_id"] = [f"appendix_uv1_{i:02d}" for i in range(1, len(pilot) + 1)]
    return pilot


def _build_system_prompt(include_reason: bool) -> str:
    if include_reason:
        return BASE_SYSTEM_PROMPT.replace(
            "Return JSON only.\nBe concise and evidence-based.",
            "Return JSON only.\nKeep the reason under 18 words.\nBe concise and evidence-based.",
        )
    return BASE_SYSTEM_PROMPT


def _build_schema(include_reason: bool) -> dict:
    schema = json.loads(json.dumps(BASE_SCHEMA))
    if include_reason:
        schema["properties"]["reason"] = {"type": "string", "maxLength": 100}
        schema["required"].append("reason")
    return schema


def _request_body(row: pd.Series, *, include_reason: bool) -> dict:
    system_prompt = _build_system_prompt(include_reason)
    schema = _build_schema(include_reason)
    record = {
        "item_id": row["item_id"],
        "question_text": row["prompt_text"],
        "source_label": row["source_label"],
        "focal_mediator_label": row["focal_mediator_label"],
        "target_label": row["target_label"],
    }
    user_prompt = USER_TEMPLATE.format(
        record_json=json.dumps(record, ensure_ascii=True, sort_keys=True)
    )
    return {
        "model": "gpt-5.4-mini",
        "reasoning": {"effort": "none"},
        "max_output_tokens": 120,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": (
                    "appendix_usefulness_rating_v1"
                    if include_reason
                    else "appendix_usefulness_rating_v1_noreason"
                ),
                "strict": True,
                "schema": schema,
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--no-reason", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    include_reason = not args.no_reason
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)
    pilot = _pilot_selection(df)

    pilot_csv = out_dir / "pilot10_items.csv"
    request_jsonl = out_dir / "pilot10_requests.jsonl"
    system_md = out_dir / "system_prompt.md"
    user_md = out_dir / "user_prompt_template.md"
    schema_json = out_dir / "schema_appendix_usefulness_v1.json"
    manifest_json = out_dir / "manifest.json"
    system_prompt = _build_system_prompt(include_reason)
    schema = _build_schema(include_reason)

    pilot.to_csv(pilot_csv, index=False)
    system_md.write_text(system_prompt + "\n", encoding="utf-8")
    user_md.write_text(USER_TEMPLATE + "\n", encoding="utf-8")
    schema_json.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    with request_jsonl.open("w", encoding="utf-8") as fh:
        for row in pilot.to_dict(orient="records"):
            payload = {
                "custom_id": row["item_id"],
                "method": "POST",
                "url": "/v1/responses",
                "body": _request_body(pd.Series(row), include_reason=include_reason),
            }
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    manifest = {
        "input_csv": str(INPUT_CSV),
        "pilot_csv": str(pilot_csv),
        "request_jsonl": str(request_jsonl),
        "n_requests": int(len(pilot)),
        "model": "gpt-5.4-mini",
        "reasoning_effort": "none",
        "max_output_tokens": 120,
        "schema_file": str(schema_json),
        "include_reason": include_reason,
    }
    manifest_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
