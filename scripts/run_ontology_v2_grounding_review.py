"""Run ontology-v2 grounding review with GPT-5.4-mini as the main reviewer.

This script consumes the queued review items built by
`build_ontology_v2_open_world_grounding.py`, enriches them with extra audit
context, then runs a full async review over the queued items using
`gpt-5.4-mini` with low reasoning.

The raw queue is never mutated. Results are written to separate artifacts.
"""
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

QUEUE_PATH = DATA_DIR / "nano_grounding_review_v2.parquet"
AUDIT_PATH = DATA_DIR / "grounding_rescue_audit_v2.parquet"
CLUSTERS_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2.parquet"

RUN_SUFFIX = os.environ.get("ONTOLOGY_REVIEW_RUN_SUFFIX", "").strip()


def suffix_name(stem: str, ext: str) -> Path:
    suffix = f"_{RUN_SUFFIX}" if RUN_SUFFIX else ""
    return DATA_DIR / f"{stem}{suffix}{ext}"


ENRICHED_QUEUE_PATH = suffix_name("nano_grounding_review_v2_enriched", ".parquet")
MAIN_RESULTS_PATH = suffix_name("main_grounding_review_v2_results", ".parquet")
MAIN_SUMMARY_PATH = suffix_name("main_grounding_review_v2_results", ".md")

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt"
)

MAIN_MODEL = os.environ.get("ONTOLOGY_REVIEW_MAIN_MODEL", "gpt-5.4-mini")
MAIN_REASONING_EFFORT = os.environ.get("ONTOLOGY_REVIEW_MAIN_REASONING_EFFORT", "low")

MAIN_CONCURRENCY = int(os.environ.get("ONTOLOGY_REVIEW_MAIN_CONCURRENCY", "120"))
MAX_ITEMS = int(os.environ.get("ONTOLOGY_REVIEW_MAX_ITEMS", "0"))

ROW_BATCH_SIZE = int(os.environ.get("ONTOLOGY_REVIEW_ROW_BATCH", "20"))
CLUSTER_BATCH_SIZE = int(os.environ.get("ONTOLOGY_REVIEW_CLUSTER_BATCH", "8"))
UNRESOLVED_BATCH_SIZE = int(os.environ.get("ONTOLOGY_REVIEW_UNRESOLVED_BATCH", "10"))

DECISION_NORMALIZATION = {
    "accept_existing_broad": "accept_existing_broad",
    "attach_existing_broad": "accept_existing_broad",
    "broader_concept_available": "accept_existing_broad",
    "accept_existing_alias": "accept_existing_alias",
    "add_alias_to_existing": "accept_existing_alias",
    "missing_alias": "accept_existing_alias",
    "promote_new_concept_family": "promote_new_concept_family",
    "propose_new_concept_family": "promote_new_concept_family",
    "missing_concept_family": "promote_new_concept_family",
    "accept_existing_concept_family": "promote_new_concept_family",
    "reject_match_keep_raw": "reject_match_keep_raw",
    "bad_match_or_noise": "reject_match_keep_raw",
    "keep_unresolved": "keep_unresolved",
    "unclear": "unclear",
}


ROW_SYSTEM_PROMPT = """You are reviewing ontology grounding for labels extracted from economics-facing research papers.

A valid label is not limited to narrow textbook economics vocabulary. Valid labels may include:
- economics concepts and variables
- policies and institutions
- outcomes and behaviors
- methods
- demographic or geographic contexts
- environmental or climate variables
- health, education, or social-science concepts that commonly appear in economics research

Important rules:
- Raw labels are always preserved. Never recommend deleting a raw label.
- Broader grounding is allowed when the ontology target is economically meaningful but more general than the extracted label.
- If the nearest ontology candidates are wrong but the extracted label is still a valid research label, prefer `promote_new_concept_family` or `keep_unresolved`.
- Use `accept_existing_alias` only when the ontology already has the right concept and this looks like a wording or surface-form variant.
- Use `reject_match_keep_raw` only when the proposed ontology attachment is wrong and there is no usable ontology action yet.
- Be conservative about forcing a match.

Allowed decisions:
- accept_existing_broad
- accept_existing_alias
- promote_new_concept_family
- reject_match_keep_raw
- keep_unresolved
- unclear

Return JSON only in this form:
{
  "results": [
    {
      "review_id": "...",
      "decision": "...",
      "canonical_target_label": string or null,
      "new_concept_family_label": string or null,
      "confidence": "high" | "medium" | "low",
      "reason": "one short sentence, max 25 words"
    }
  ]
}"""


CLUSTER_SYSTEM_PROMPT = """You are reviewing cluster-level ontology enrichment proposals for labels extracted from economics-facing research papers.

A valid cluster may represent economics concepts, methods, institutions, policies, outcomes, demographic or geographic contexts, environmental variables, or social-science concepts commonly used in economics.

Important rules:
- Do not assume the dominant ontology target is correct just because it is frequent.
- Broader grounding is allowed when one existing ontology concept is clearly the right general home.
- Use `accept_existing_alias` only when the cluster mostly reflects wording variants of an existing concept.
- Use `promote_new_concept_family` when the cluster represents a recurring research concept family not adequately captured by the current ontology.
- Use `keep_unresolved` when the cluster is real but too mixed for a clean decision.
- Use `reject_match_keep_raw` when the current ontology neighborhood is misleading and should not be trusted.

Allowed decisions:
- accept_existing_broad
- accept_existing_alias
- promote_new_concept_family
- reject_match_keep_raw
- keep_unresolved
- unclear

Return JSON only in this form:
{
  "results": [
    {
      "review_id": "...",
      "decision": "...",
      "canonical_target_label": string or null,
      "new_concept_family_label": string or null,
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
    payload = text[first : last + 1]
    return json.loads(payload)


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
    return DECISION_NORMALIZATION.get(key, key)


def safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except Exception:
        return None


def sample_member_labels(member_labels_json: str | None, limit: int = 12) -> list[str]:
    if not member_labels_json:
        return []
    try:
        labels = json.loads(member_labels_json)
    except Exception:
        return []
    return [str(x) for x in labels[:limit]]


def enrich_queue() -> pd.DataFrame:
    queue = pd.read_parquet(QUEUE_PATH)
    audit = pd.read_parquet(AUDIT_PATH)
    clusters = pd.read_parquet(CLUSTERS_PATH)

    audit_cols = [
        "label",
        "score_band",
        "freq",
        "impact_score",
        "unique_papers",
        "unique_edge_instances",
        "directed_edge_instances",
        "onto_label",
        "onto_source",
        "onto_domain",
        "rank1_score",
        "rank2_label",
        "rank2_score",
        "rank3_label",
        "rank3_score",
        "rank_gap",
        "issue_type",
        "proposed_onto_label",
        "cluster_id",
        "cluster_proposal",
    ]
    audit = audit[audit_cols].drop_duplicates("label")

    cluster_cols = [
        "cluster_id",
        "cluster_size",
        "cluster_weighted_freq",
        "cluster_weighted_unique_papers",
        "cluster_representative_label",
        "cluster_mean_similarity",
        "dominant_onto_label",
        "dominant_share",
        "cluster_proposal",
        "member_labels_json",
    ]
    clusters = clusters[cluster_cols]

    enriched = queue.merge(
        audit.add_prefix("audit_"),
        left_on="label",
        right_on="audit_label",
        how="left",
    )
    enriched = enriched.merge(
        clusters.add_prefix("cluster_"),
        left_on="cluster_id",
        right_on="cluster_cluster_id",
        how="left",
    )

    enriched["review_id"] = [
        f"gr_{i:05d}_{kind}"
        for i, kind in enumerate(enriched["review_item_type"].astype(str), start=1)
    ]
    enriched["member_labels_sample_json"] = enriched["cluster_member_labels_json"].map(
        lambda x: json_dumps(sample_member_labels(x))
    )
    enriched["effective_rank1_label"] = enriched["rank1_label"].fillna(enriched["audit_onto_label"])
    enriched["effective_rank1_score"] = enriched["rank1_score"].fillna(enriched["audit_rank1_score"])
    enriched["effective_rank2_label"] = enriched["rank2_label"].fillna(enriched["audit_rank2_label"])
    enriched["effective_rank2_score"] = enriched["rank2_score"].fillna(enriched["audit_rank2_score"])
    enriched["effective_rank3_label"] = enriched["audit_rank3_label"]
    enriched["effective_rank3_score"] = enriched["audit_rank3_score"]
    enriched["effective_issue_type"] = enriched["issue_type"].fillna(enriched["audit_issue_type"])
    enriched["effective_proposed_action"] = enriched["proposed_action"].fillna(enriched["cluster_cluster_proposal"])
    enriched["effective_score_band"] = enriched["score_band"].fillna(enriched["audit_score_band"])
    enriched["effective_freq"] = enriched["freq"].fillna(enriched["audit_freq"])
    enriched["effective_impact_score"] = enriched["impact_score"].fillna(enriched["audit_impact_score"])

    enriched.to_parquet(ENRICHED_QUEUE_PATH, index=False)
    return enriched


def row_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "review_id": row["review_id"],
        "label": row["label"],
        "score_band": row["effective_score_band"],
        "freq": int(row["effective_freq"]) if pd.notna(row["effective_freq"]) else None,
        "impact_score": round(float(row["effective_impact_score"]), 6)
        if pd.notna(row["effective_impact_score"])
        else None,
        "unique_papers": int(row["audit_unique_papers"]) if pd.notna(row.get("audit_unique_papers")) else None,
        "unique_edge_instances": int(row["audit_unique_edge_instances"])
        if pd.notna(row.get("audit_unique_edge_instances"))
        else None,
        "directed_edge_instances": int(row["audit_directed_edge_instances"])
        if pd.notna(row.get("audit_directed_edge_instances"))
        else None,
        "rank1_label": row["effective_rank1_label"],
        "rank1_score": safe_float(row["effective_rank1_score"]),
        "rank2_label": row["effective_rank2_label"],
        "rank2_score": safe_float(row["effective_rank2_score"]),
        "rank3_label": row["effective_rank3_label"],
        "rank3_score": safe_float(row["effective_rank3_score"]),
        "rank_gap": safe_float(row["rank_gap"]),
        "onto_source": row.get("audit_onto_source"),
        "onto_domain": row.get("audit_onto_domain"),
        "proposed_action": row["effective_proposed_action"],
        "issue_type": row["effective_issue_type"],
    }


def cluster_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "review_id": row["review_id"],
        "cluster_id": row["cluster_id"],
        "cluster_representative_label": row["label"],
        "cluster_size": int(row["cluster_cluster_size"]) if pd.notna(row.get("cluster_cluster_size")) else None,
        "cluster_weighted_freq": int(row["cluster_cluster_weighted_freq"])
        if pd.notna(row.get("cluster_cluster_weighted_freq"))
        else int(row["freq"]) if pd.notna(row.get("freq")) else None,
        "cluster_weighted_unique_papers": int(row["cluster_cluster_weighted_unique_papers"])
        if pd.notna(row.get("cluster_cluster_weighted_unique_papers"))
        else None,
        "cluster_mean_similarity": safe_float(row["cluster_cluster_mean_similarity"]),
        "dominant_onto_label": row.get("cluster_dominant_onto_label"),
        "dominant_share": safe_float(row.get("cluster_dominant_share")),
        "cluster_proposal": row["effective_proposed_action"],
        "member_labels_sample": sample_member_labels(row.get("cluster_member_labels_json"), limit=12),
    }


def build_batch_prompt(item_type: str, items: list[dict[str, Any]]) -> tuple[str, str, int]:
    if item_type == "cluster_medoid":
        system_prompt = CLUSTER_SYSTEM_PROMPT
        user_prompt = (
            "Review the following cluster-level items. Return JSON only.\n\n"
            + json_dumps({"items": items})
        )
        max_tokens = max(800, len(items) * 120)
    else:
        system_prompt = ROW_SYSTEM_PROMPT
        user_prompt = (
            "Review the following row-level items. Return JSON only.\n\n"
            + json_dumps({"items": items})
        )
        max_tokens = max(1200, len(items) * 110)
    return system_prompt, user_prompt, max_tokens


def batch_size_for(item_type: str) -> int:
    if item_type == "cluster_medoid":
        return CLUSTER_BATCH_SIZE
    if item_type == "unresolved_row":
        return UNRESOLVED_BATCH_SIZE
    return ROW_BATCH_SIZE


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

    tasks = []
    for item_type, sub in df.groupby("review_item_type", sort=False):
        batch_size = batch_size_for(item_type)
        payloads = [
            cluster_payload(row) if item_type == "cluster_medoid" else row_payload(row)
            for _, row in sub.iterrows()
        ]
        for i in range(0, len(payloads), batch_size):
            tasks.append((item_type, payloads[i : i + batch_size]))

    async def handle_batch(item_type: str, batch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal completed
        system_prompt, user_prompt, max_tokens = build_batch_prompt(item_type, batch_items)
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
                        "canonical_target_label": item.get("canonical_target_label"),
                        "new_concept_family_label": item.get("new_concept_family_label"),
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

    gathered = await asyncio.gather(*[handle_batch(item_type, items) for item_type, items in tasks])
    for batch in gathered:
        result_rows.extend(batch)

    results = pd.DataFrame(result_rows)
    return results, stats


def merge_and_write(
    source_df: pd.DataFrame,
    results_df: pd.DataFrame,
    out_path: Path,
) -> pd.DataFrame:
    merged = source_df.merge(results_df, on="review_id", how="left")
    if "decision" in merged.columns:
        merged["decision_raw"] = merged["decision"]
        merged["decision"] = merged["decision"].map(normalize_decision)
    merged.to_parquet(out_path, index=False)
    return merged


def write_summary(
    *,
    path: Path,
    model: str,
    merged: pd.DataFrame,
    stats: RunStats,
    title: str,
) -> None:
    decision_counts = (
        merged["decision"].fillna("missing").value_counts().to_dict()
        if "decision" in merged.columns
        else {}
    )
    confidence_counts = (
        merged["confidence"].fillna("missing").value_counts().to_dict()
        if "confidence" in merged.columns
        else {}
    )
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
    lines.extend(["", "## Sample rows"])
    sample_cols = [
        c
        for c in [
            "review_item_type",
            "label",
            "effective_score_band",
            "effective_proposed_action",
            "decision",
            "canonical_target_label",
            "new_concept_family_label",
            "confidence",
            "reason",
        ]
        if c in merged.columns
    ]
    sample = merged[sample_cols].head(12)
    lines.append("")
    lines.append(sample.to_markdown(index=False))
    path.write_text("\n".join(lines) + "\n")


async def main() -> None:
    print("=== Enriching review queue ===", flush=True)
    enriched = enrich_queue()
    if MAX_ITEMS > 0:
        enriched = enriched.head(MAX_ITEMS).copy()
        print(f"  limiting review to first {MAX_ITEMS:,} rows via ONTOLOGY_REVIEW_MAX_ITEMS", flush=True)
    print(f"  enriched queue rows: {len(enriched):,}", flush=True)

    client = load_openai_client()

    print(
        f"\n=== Running full main review with {MAIN_MODEL} "
        f"(reasoning={MAIN_REASONING_EFFORT}) ===",
        flush=True,
    )
    main_results, main_stats = await run_batches(
        client=client,
        model=MAIN_MODEL,
        reasoning_effort=MAIN_REASONING_EFFORT,
        df=enriched,
        concurrency=MAIN_CONCURRENCY,
    )
    main_merged = merge_and_write(enriched, main_results, MAIN_RESULTS_PATH)
    write_summary(
        path=MAIN_SUMMARY_PATH,
        model=f"{MAIN_MODEL} (reasoning={MAIN_REASONING_EFFORT})",
        merged=main_merged,
        stats=main_stats,
        title="Main Grounding Review Results v2",
    )

    print("\nDone.", flush=True)
    print(f"  main results: {MAIN_RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
