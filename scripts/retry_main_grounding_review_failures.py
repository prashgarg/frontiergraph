"""Retry failed GPT-5.4-mini grounding review items with smaller batches.

This script reloads the full main review output, extracts only rows that
failed to return a parsed decision, reruns them with the same model but
smaller batch sizes, and writes both retry-only and merged post-retry
artifacts.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

RUN_SUFFIX = os.environ.get("ONTOLOGY_REVIEW_RUN_SUFFIX", "").strip()


def suffix_name(stem: str, ext: str) -> Path:
    suffix = f"_{RUN_SUFFIX}" if RUN_SUFFIX else ""
    return DATA_DIR / f"{stem}{suffix}{ext}"

BASE_RESULTS_PATH = suffix_name("main_grounding_review_v2_results", ".parquet")
BASE_SUMMARY_PATH = suffix_name("main_grounding_review_v2_results", ".md")

RETRY_QUEUE_PATH = suffix_name("main_grounding_review_v2_retry_queue", ".parquet")
RETRY_RESULTS_PATH = suffix_name("main_grounding_review_v2_retry_results", ".parquet")
RETRY_SUMMARY_PATH = suffix_name("main_grounding_review_v2_retry_results", ".md")

MERGED_RESULTS_PATH = suffix_name("main_grounding_review_v2_results_merged", ".parquet")
MERGED_SUMMARY_PATH = suffix_name("main_grounding_review_v2_results_merged", ".md")

RETRY_CONCURRENCY = int(os.environ.get("ONTOLOGY_REVIEW_RETRY_CONCURRENCY", "64"))
RETRY_ROW_BATCH = int(os.environ.get("ONTOLOGY_REVIEW_RETRY_ROW_BATCH", "8"))
RETRY_CLUSTER_BATCH = int(os.environ.get("ONTOLOGY_REVIEW_RETRY_CLUSTER_BATCH", "4"))
RETRY_UNRESOLVED_BATCH = int(os.environ.get("ONTOLOGY_REVIEW_RETRY_UNRESOLVED_BATCH", "4"))


def load_review_module():
    path = ROOT / "scripts" / "run_ontology_v2_grounding_review.py"
    spec = importlib.util.spec_from_file_location("grounding_review_main", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_stats_from_summary(path: Path) -> tuple[int, int, int]:
    text = path.read_text() if path.exists() else ""
    def extract(label: str) -> int:
        match = re.search(rf"- {label}: `([0-9,]+)`", text)
        return int(match.group(1).replace(",", "")) if match else 0
    return (
        extract("batches"),
        extract("prompt tokens"),
        extract("completion tokens"),
    )


def missing_mask(df: pd.DataFrame) -> pd.Series:
    return df["decision"].isna() | (~df["raw_response_ok"].fillna(False))


async def main() -> None:
    review = load_review_module()

    base = pd.read_parquet(BASE_RESULTS_PATH)
    failed = base.loc[missing_mask(base)].copy()
    stale_review_cols = [
        "decision",
        "decision_raw",
        "canonical_target_label",
        "new_concept_family_label",
        "confidence",
        "reason",
        "raw_response_ok",
    ]
    failed = failed.drop(columns=[c for c in stale_review_cols if c in failed.columns])
    failed.to_parquet(RETRY_QUEUE_PATH, index=False)

    print(f"Retry queue rows: {len(failed):,}", flush=True)
    if failed.empty:
        print("No failed rows to retry.", flush=True)
        base.to_parquet(MERGED_RESULTS_PATH, index=False)
        return

    review.ROW_BATCH_SIZE = RETRY_ROW_BATCH
    review.CLUSTER_BATCH_SIZE = RETRY_CLUSTER_BATCH
    review.UNRESOLVED_BATCH_SIZE = RETRY_UNRESOLVED_BATCH

    client = review.load_openai_client()
    retry_results, retry_stats = await review.run_batches(
        client=client,
        model=review.MAIN_MODEL,
        reasoning_effort=review.MAIN_REASONING_EFFORT,
        df=failed,
        concurrency=RETRY_CONCURRENCY,
    )
    retry_merged = review.merge_and_write(failed, retry_results, RETRY_RESULTS_PATH)
    review.write_summary(
        path=RETRY_SUMMARY_PATH,
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=retry_merged,
        stats=retry_stats,
        title="Retry Grounding Review Results v2",
    )

    merged = base.set_index("review_id").copy()
    retry_indexed = retry_merged.set_index("review_id")
    for col in [
        "decision",
        "decision_raw",
        "canonical_target_label",
        "new_concept_family_label",
        "confidence",
        "reason",
        "raw_response_ok",
    ]:
        if col in retry_indexed.columns:
            merged[col] = retry_indexed[col].combine_first(merged[col])

    merged = merged.reset_index()
    merged.to_parquet(MERGED_RESULTS_PATH, index=False)

    base_batches, base_prompt, base_completion = parse_stats_from_summary(BASE_SUMMARY_PATH)
    total_stats = review.RunStats(
        batches=base_batches + retry_stats.batches,
        items=len(merged),
        prompt_tokens=base_prompt + retry_stats.prompt_tokens,
        completion_tokens=base_completion + retry_stats.completion_tokens,
    )
    review.write_summary(
        path=MERGED_SUMMARY_PATH,
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=merged,
        stats=total_stats,
        title="Main Grounding Review Results v2 (Merged After Retry)",
    )

    recovered = int((~missing_mask(merged)).sum() - (~missing_mask(base)).sum())
    remaining = int(missing_mask(merged).sum())
    with MERGED_SUMMARY_PATH.open("a") as f:
        f.write("\n## Retry details\n")
        f.write(f"\n- retry queue rows: `{len(failed):,}`\n")
        f.write(f"- recovered decisions on retry: `{recovered:,}`\n")
        f.write(f"- remaining missing after retry: `{remaining:,}`\n")
        f.write(
            f"- retry batch sizes: row=`{RETRY_ROW_BATCH}`, "
            f"cluster=`{RETRY_CLUSTER_BATCH}`, unresolved=`{RETRY_UNRESOLVED_BATCH}`\n"
        )
        f.write(f"- retry concurrency: `{RETRY_CONCURRENCY}`\n")

    print("Done.", flush=True)
    print(f"  retry results: {RETRY_RESULTS_PATH}", flush=True)
    print(f"  merged results: {MERGED_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
