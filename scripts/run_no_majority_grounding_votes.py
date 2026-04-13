"""Run additional grounding-review votes on the current no-majority hard cases.

This script targets either:
1. the rows currently labeled `split_type == "no_majority"` in
   `main_grounding_review_v2_vote_matrix.parquet`, or
2. the rows currently labeled `modal_type == "tied_modal"` in
   `no_majority_modal_vote_10run.parquet`.

It uses GPT-5.4-mini with low reasoning through the shared review runner, with
tiny batches and built-in micro-retries so each extra vote is as complete as
possible.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

RUN_LABEL = (Path.cwd().name and "") or ""
RUN_LABEL = __import__("os").environ.get("NO_MAJORITY_RUN_LABEL", "").strip()
if not RUN_LABEL:
    raise SystemExit("Set NO_MAJORITY_RUN_LABEL, e.g. run4")

CONCURRENCY = int(__import__("os").environ.get("NO_MAJORITY_CONCURRENCY", "24"))
ROW_BATCH = int(__import__("os").environ.get("NO_MAJORITY_ROW_BATCH", "1"))
CLUSTER_BATCH = int(__import__("os").environ.get("NO_MAJORITY_CLUSTER_BATCH", "1"))
UNRESOLVED_BATCH = int(__import__("os").environ.get("NO_MAJORITY_UNRESOLVED_BATCH", "1"))
MAX_RETRY_ROUNDS = int(__import__("os").environ.get("NO_MAJORITY_MAX_RETRY_ROUNDS", "3"))
TARGET_SET = __import__("os").environ.get("NO_MAJORITY_TARGET_SET", "original_no_majority").strip()

VOTE_MATRIX_PATH = DATA_DIR / "main_grounding_review_v2_vote_matrix.parquet"
MODAL_10RUN_PATH = DATA_DIR / "no_majority_modal_vote_10run.parquet"
BASE_SOURCE_PATH = DATA_DIR / "main_grounding_review_v2_results_final.parquet"

QUEUE_PATH = DATA_DIR / f"no_majority_grounding_review_queue_{RUN_LABEL}.parquet"
RESULTS_PATH = DATA_DIR / f"no_majority_grounding_review_results_{RUN_LABEL}.parquet"
SUMMARY_PATH = DATA_DIR / f"no_majority_grounding_review_results_{RUN_LABEL}.md"


def load_review_module():
    path = ROOT / "scripts" / "run_ontology_v2_grounding_review.py"
    spec = importlib.util.spec_from_file_location(f"grounding_review_{RUN_LABEL}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def stale_review_cols(df: pd.DataFrame) -> list[str]:
    cols = [
        "decision",
        "decision_raw",
        "canonical_target_label",
        "new_concept_family_label",
        "confidence",
        "reason",
        "raw_response_ok",
    ]
    return [c for c in cols if c in df.columns]


def missing_mask(df: pd.DataFrame) -> pd.Series:
    return df["decision"].isna() | (~df["raw_response_ok"].fillna(False))


async def main() -> None:
    review = load_review_module()
    review.ROW_BATCH_SIZE = ROW_BATCH
    review.CLUSTER_BATCH_SIZE = CLUSTER_BATCH
    review.UNRESOLVED_BATCH_SIZE = UNRESOLVED_BATCH

    if TARGET_SET == "tied_modal_10run":
        vote = pd.read_parquet(MODAL_10RUN_PATH)
        target_ids = vote.loc[vote["modal_type"] == "tied_modal", "review_id"].tolist()
    else:
        vote = pd.read_parquet(VOTE_MATRIX_PATH)
        target_ids = vote.loc[vote["split_type"] == "no_majority", "review_id"].tolist()
    source = pd.read_parquet(BASE_SOURCE_PATH)
    queue = source[source["review_id"].isin(target_ids)].copy()
    queue = queue.drop(columns=stale_review_cols(queue))
    queue = queue.sort_values("review_id").reset_index(drop=True)
    queue.to_parquet(QUEUE_PATH, index=False)

    print(f"{RUN_LABEL}: target set = {TARGET_SET}", flush=True)
    print(f"{RUN_LABEL}: target rows = {len(queue):,}", flush=True)

    client = review.load_openai_client()
    pending = queue.copy()
    final = queue.copy()
    final["decision"] = None
    final["decision_raw"] = None
    final["canonical_target_label"] = None
    final["new_concept_family_label"] = None
    final["confidence"] = None
    final["reason"] = None
    final["raw_response_ok"] = False

    total_stats = review.RunStats()

    for round_idx in range(1, MAX_RETRY_ROUNDS + 1):
        if pending.empty:
            break
        print(f"{RUN_LABEL}: review round {round_idx}, pending {len(pending):,}", flush=True)
        results, stats = await review.run_batches(
            client=client,
            model=review.MAIN_MODEL,
            reasoning_effort=review.MAIN_REASONING_EFFORT,
            df=pending,
            concurrency=CONCURRENCY,
        )
        total_stats.batches += stats.batches
        total_stats.items += stats.items
        total_stats.prompt_tokens += stats.prompt_tokens
        total_stats.completion_tokens += stats.completion_tokens

        merged = review.merge_and_write(pending, results, RESULTS_PATH)
        idx = final.set_index("review_id")
        upd = merged.set_index("review_id")
        for col in [
            "decision",
            "decision_raw",
            "canonical_target_label",
            "new_concept_family_label",
            "confidence",
            "reason",
            "raw_response_ok",
        ]:
            idx[col] = upd[col].combine_first(idx[col])
        final = idx.reset_index()

        pending = final.loc[missing_mask(final)].copy()
        pending = pending.drop(columns=stale_review_cols(pending))

    final.to_parquet(RESULTS_PATH, index=False)
    review.write_summary(
        path=SUMMARY_PATH,
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=final,
        stats=total_stats,
        title=f"No-Majority Grounding Review Results {RUN_LABEL}",
    )

    remaining = int(missing_mask(final).sum())
    with SUMMARY_PATH.open("a") as f:
        f.write("\n## Run details\n")
        f.write(f"\n- run label: `{RUN_LABEL}`\n")
        f.write(f"- target set: `{TARGET_SET}`\n")
        f.write(f"- target rows: `{len(queue):,}`\n")
        f.write(f"- remaining missing after retries: `{remaining:,}`\n")
        f.write(f"- retry rounds: `{MAX_RETRY_ROUNDS}`\n")
        f.write(
            f"- batch sizes: row=`{ROW_BATCH}`, cluster=`{CLUSTER_BATCH}`, "
            f"unresolved=`{UNRESOLVED_BATCH}`\n"
        )
        f.write(f"- concurrency: `{CONCURRENCY}`\n")

    print(f"{RUN_LABEL}: complete, remaining missing = {remaining}", flush=True)
    print(f"{RUN_LABEL}: results = {RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
