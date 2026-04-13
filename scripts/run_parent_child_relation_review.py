"""Run staged parent-child relation review over the v2.2 candidate queue."""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

QUEUE_PATH = Path(
    os.environ.get(
        "PARENT_CHILD_REVIEW_QUEUE_PATH",
        str(DATA_DIR / "parent_child_nano_review_queue_v2_2.parquet"),
    )
)
KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt"
)

RUN_SUFFIX = os.environ.get("PARENT_CHILD_REVIEW_RUN_SUFFIX", "").strip()
MODEL = os.environ.get("PARENT_CHILD_REVIEW_MODEL", "gpt-5.4-nano")
REASONING_EFFORT = os.environ.get("PARENT_CHILD_REVIEW_REASONING_EFFORT", "").strip()
CONCURRENCY = int(os.environ.get("PARENT_CHILD_REVIEW_CONCURRENCY", "80"))
MAX_ITEMS = int(os.environ.get("PARENT_CHILD_REVIEW_MAX_ITEMS", "0"))
BATCH_SIZE = int(os.environ.get("PARENT_CHILD_REVIEW_BATCH_SIZE", "25"))
TIER_FILTER = os.environ.get("PARENT_CHILD_REVIEW_TIERS", "").strip()


DECISION_SET = {
    "valid_parent",
    "plausible_but_too_broad",
    "alias_or_duplicate",
    "sibling_or_related",
    "context_not_parent",
    "invalid",
}


PAIR_SYSTEM_PROMPT = """You are reviewing possible parent-child relations in an ontology of economics-facing research concepts.

A valid ontology concept may be:
- an economics concept or variable
- an institution or policy
- an outcome or behavior
- a method or model
- a demographic, geographic, environmental, health, or social-science concept used in economics-facing research

Your task is to judge whether the candidate parent is the right direct broader concept for the child.

Decision rules:
- `valid_parent`: the candidate parent is a good direct broader concept for the child
- `plausible_but_too_broad`: the candidate is broader and related, but too generic to be the right immediate parent
- `alias_or_duplicate`: the pair is really the same concept or a surface-form duplicate rather than parent-child
- `sibling_or_related`: the pair is related, but neither is the parent of the other
- `context_not_parent`: the candidate is a context, place, measurement frame, or other association rather than a semantic parent
- `invalid`: the candidate is simply the wrong ontology neighborhood

Important rules:
- Do not force a parent-child relation just because the labels are similar.
- A parent should usually be conceptually broader than the child, not just co-occurring or associated.
- If the child is a specific type, application, subtype, or named instance of the parent, prefer `valid_parent`, not `alias_or_duplicate`.
- Use `alias_or_duplicate` only when the child and parent are essentially the same concept under different wording, formatting, or source duplication.
- If the candidate parent is a real broader domain but skips an intermediate level, prefer `plausible_but_too_broad`.
- Geographic scope alone does not make a parent-child relation.
- Measure names, contexts, and applications are often not parents.
- Existing source hierarchies and current parent labels are hints, not truth.
- Be conservative.

Examples:
- `Willingness to pay` -> `Willingness to Pay.` = `alias_or_duplicate`
- `basic unemployment allowance` -> `unemployment benefit` = `valid_parent`
- `future of work` -> `economics` = `plausible_but_too_broad` or `sibling_or_related`, not `alias_or_duplicate`

Return JSON only in this form:
{
  "results": [
    {
      "review_id": "...",
      "decision": "...",
      "confidence": "high" | "medium" | "low",
      "reason": "one short sentence, max 25 words"
    }
  ]
}"""


@dataclass
class RunStats:
    batches: int = 0
    items: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def suffix_name(stem: str, ext: str) -> Path:
    suffix = f"_{RUN_SUFFIX}" if RUN_SUFFIX else ""
    return DATA_DIR / f"{stem}{suffix}{ext}"


RESULTS_PATH = suffix_name("parent_child_relation_review_results_v2_2", ".parquet")
SUMMARY_PATH = suffix_name("parent_child_relation_review_results_v2_2", ".md")


def load_openai_client():
    os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()
    import openai

    return openai.AsyncOpenAI(timeout=60.0)


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[first : last + 1])


def extract_response_text(resp: Any) -> str:
    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    output = getattr(resp, "output", None) or []
    fragments: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for block in content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                fragments.append(block_text)
    return "\n".join(x for x in fragments if x).strip()


def extract_usage_tokens(resp: Any) -> tuple[int, int]:
    usage = getattr(resp, "usage", None)
    if usage is None:
        return 0, 0
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    if not input_tokens:
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    if not output_tokens:
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return input_tokens, output_tokens


def normalize_decision(value: Any) -> str | None:
    if value is None:
        return None
    key = str(value).strip()
    if not key:
        return None
    return key if key in DECISION_SET else None


def safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except Exception:
        return None


def load_queue() -> pd.DataFrame:
    df = pd.read_parquet(QUEUE_PATH).copy()
    if TIER_FILTER:
        wanted = {x.strip() for x in TIER_FILTER.split(",") if x.strip()}
        df = df[df["review_tier"].isin(wanted)].copy()
    if MAX_ITEMS > 0:
        df = df.head(MAX_ITEMS).copy()
    df["review_id"] = [f"pc_{i:06d}" for i in range(1, len(df) + 1)]
    return df


def row_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "review_id": row["review_id"],
        "review_tier": row["review_tier"],
        "candidate_channel": row["candidate_channel"],
        "child_label": row["child_label"],
        "child_source": row["child_source"],
        "child_domain": row.get("child_domain"),
        "child_current_parent_label": row.get("child_current_parent_label"),
        "candidate_parent_label": row["candidate_parent_label"],
        "candidate_parent_source": row["candidate_parent_source"],
        "candidate_parent_domain": row.get("candidate_parent_domain"),
        "existing_parent_label": row.get("external_parent_label"),
        "structured_edge_type": row.get("structured_edge_type"),
        "semantic_cosine": safe_float(row.get("semantic_cosine")),
        "lexical_parent_score": safe_float(row.get("lexical_parent_score")),
        "support_ratio": safe_float(row.get("support_ratio")),
        "token_drop": int(row["token_drop"]) if pd.notna(row.get("token_drop")) else None,
        "same_source_pair": bool(row.get("same_source_pair")),
        "same_domain_pair": bool(row.get("same_domain_pair")),
        "needs_cleanup_attention": bool(row.get("needs_cleanup_attention")),
        "child_mapped_total_freq": int(row["child_mapped_total_freq"]) if pd.notna(row.get("child_mapped_total_freq")) else 0,
        "parent_mapped_total_freq": int(row["parent_mapped_total_freq"]) if pd.notna(row.get("parent_mapped_total_freq")) else 0,
    }


def build_batch_prompt(items: list[dict[str, Any]]) -> tuple[str, str, int]:
    user_prompt = (
        "Review the following possible parent-child ontology pairs. Return JSON only.\n\n"
        + json_dumps({"items": items})
    )
    max_tokens = max(1200, len(items) * 90)
    return PAIR_SYSTEM_PROMPT, user_prompt, max_tokens


async def run_batches(
    *,
    client: Any,
    model: str,
    reasoning_effort: str | None,
    df: pd.DataFrame,
    concurrency: int,
) -> tuple[pd.DataFrame, RunStats]:
    sem = asyncio.Semaphore(concurrency)
    stats = RunStats()
    completed = 0
    t0 = time.time()
    result_rows: list[dict[str, Any]] = []

    payloads = [row_payload(row) for _, row in df.iterrows()]
    tasks = [payloads[i : i + BATCH_SIZE] for i in range(0, len(payloads), BATCH_SIZE)]

    async def handle_batch(batch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal completed
        system_prompt, user_prompt, max_tokens = build_batch_prompt(batch_items)
        async with sem:
            text = ""
            usage = None
            for attempt in range(4):
                try:
                    request_kwargs: dict[str, Any] = {
                        "model": model,
                        "instructions": system_prompt,
                        "input": [
                            {
                                "role": "user",
                                "content": [{"type": "input_text", "text": user_prompt}],
                            }
                        ],
                        "max_output_tokens": max_tokens,
                    }
                    if reasoning_effort:
                        request_kwargs["reasoning"] = {"effort": reasoning_effort}
                    resp = await client.responses.create(**request_kwargs)
                    text = extract_response_text(resp)
                    usage = resp
                    break
                except Exception:
                    if attempt < 3:
                        await asyncio.sleep(1.5 * (attempt + 1))
                    else:
                        text = ""
            parsed_rows: list[dict[str, Any]] = []
            try:
                payload = extract_json(text)
                parsed_rows = payload.get("results", [])
                if not isinstance(parsed_rows, list):
                    parsed_rows = []
            except Exception:
                parsed_rows = []

            by_id = {str(item.get("review_id")): item for item in parsed_rows if isinstance(item, dict)}
            batch_results = []
            for source in batch_items:
                rid = str(source["review_id"])
                item = by_id.get(rid, {})
                batch_results.append(
                    {
                        "review_id": rid,
                        "decision": item.get("decision"),
                        "confidence": item.get("confidence"),
                        "reason": item.get("reason"),
                        "raw_response_ok": rid in by_id,
                    }
                )

            completed += 1
            stats.batches += 1
            stats.items += len(batch_items)
            if usage is not None:
                input_tokens, output_tokens = extract_usage_tokens(usage)
                stats.prompt_tokens += input_tokens
                stats.completion_tokens += output_tokens
            if completed % 50 == 0 or completed == len(tasks):
                elapsed = time.time() - t0
                rate = completed / elapsed if elapsed > 0 else 0.0
                eta = (len(tasks) - completed) / rate if rate > 0 else 0.0
                print(
                    f"  {model}: {completed}/{len(tasks)} batches "
                    f"({rate:.2f}/s, ETA {eta:.0f}s)",
                    flush=True,
                )
            return batch_results

    gathered = await asyncio.gather(*[handle_batch(items) for items in tasks])
    for batch in gathered:
        result_rows.extend(batch)
    return pd.DataFrame(result_rows), stats


def merge_and_write(source_df: pd.DataFrame, results_df: pd.DataFrame) -> pd.DataFrame:
    merged = source_df.merge(results_df, on="review_id", how="left")
    merged["decision_raw"] = merged["decision"]
    merged["decision"] = merged["decision"].map(normalize_decision)
    merged.to_parquet(RESULTS_PATH, index=False)
    return merged


def write_summary(path: Path, model: str, merged: pd.DataFrame, stats: RunStats, title: str) -> None:
    decision_counts = merged["decision"].fillna("missing").value_counts().to_dict()
    confidence_counts = merged["confidence"].fillna("missing").value_counts().to_dict()
    lines = [
        f"# {title}",
        "",
        f"- model: `{model}`",
        f"- reviewed items: `{len(merged):,}`",
        f"- batches: `{stats.batches:,}`",
        f"- prompt tokens: `{stats.prompt_tokens:,}`",
        f"- completion tokens: `{stats.completion_tokens:,}`",
        "",
        "## Decisions",
    ]
    for key, value in decision_counts.items():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.extend(["", "## Confidence"])
    for key, value in confidence_counts.items():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.extend(["", "## Sample rows", ""])
    sample_cols = [
        c
        for c in [
            "review_tier",
            "candidate_channel",
            "child_label",
            "candidate_parent_label",
            "decision",
            "confidence",
            "reason",
        ]
        if c in merged.columns
    ]
    lines.append(merged[sample_cols].head(12).to_markdown(index=False))
    path.write_text("\n".join(lines) + "\n")


async def main() -> None:
    queue = load_queue()
    print(f"=== Parent-child review queue: {len(queue):,} rows ===", flush=True)
    if TIER_FILTER:
        print(f"  tiers: {TIER_FILTER}", flush=True)

    client = load_openai_client()
    print(
        f"\n=== Running parent-child review with {MODEL}"
        + (f" (reasoning={REASONING_EFFORT})" if REASONING_EFFORT else "")
        + " ===",
        flush=True,
    )
    results, stats = await run_batches(
        client=client,
        model=MODEL,
        reasoning_effort=REASONING_EFFORT or None,
        df=queue,
        concurrency=CONCURRENCY,
    )
    merged = merge_and_write(queue, results)
    write_summary(
        SUMMARY_PATH,
        f"{MODEL}" + (f" (reasoning={REASONING_EFFORT})" if REASONING_EFFORT else ""),
        merged,
        stats,
        "Parent-Child Relation Review Results v2.2",
    )
    print("\nDone.", flush=True)
    print(f"  results: {RESULTS_PATH}", flush=True)
    print(f"  summary: {SUMMARY_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
