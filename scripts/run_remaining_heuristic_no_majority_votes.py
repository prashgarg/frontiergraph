"""Run extra GPT votes on the remaining no-majority heuristic-row cases.

Targets the rows in `remaining_heuristic_row_review_majority.parquet` where
`majority_decision` is missing, preserving the original three run decisions and
adding one extra vote per run label.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

CONCURRENCY = int(os.environ.get("RHR_NO_MAJORITY_CONCURRENCY", "48"))
ROW_BATCH = int(os.environ.get("RHR_NO_MAJORITY_ROW_BATCH", "1"))
MAX_RETRY_ROUNDS = int(os.environ.get("RHR_NO_MAJORITY_MAX_RETRY_ROUNDS", "3"))

SOURCE_PATH = DATA_DIR / "remaining_heuristic_row_review_majority.parquet"


def run_label() -> str:
    label = os.environ.get("RHR_NO_MAJORITY_RUN_LABEL", "").strip()
    if not label:
        raise SystemExit("Set RHR_NO_MAJORITY_RUN_LABEL, e.g. run4")
    return label


def queue_path() -> Path:
    return DATA_DIR / f"remaining_heuristic_no_majority_queue_{run_label()}.parquet"


def results_path() -> Path:
    return DATA_DIR / f"remaining_heuristic_no_majority_results_{run_label()}.parquet"


def summary_path() -> Path:
    return DATA_DIR / f"remaining_heuristic_no_majority_results_{run_label()}.md"


def load_review_module():
    path = ROOT / "scripts" / "run_ontology_v2_grounding_review.py"
    spec = importlib.util.spec_from_file_location(f"rhr_no_majority_{run_label()}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_queue() -> pd.DataFrame:
    df = pd.read_parquet(SOURCE_PATH)
    queue = df[df["majority_decision"].isna()].copy().reset_index(drop=True)
    queue["review_item_type"] = "row"
    queue["score_band"] = queue["effective_score_band"]
    queue["proposed_action"] = queue["effective_proposed_action"]
    queue["rank1_label"] = queue["onto_label"]
    queue["rank1_score"] = None
    queue["rank2_score"] = None
    queue["rank3_label"] = None
    queue["rank3_score"] = None
    queue["rank_gap"] = None
    queue["issue_type"] = queue["effective_proposed_action"]
    queue["effective_freq"] = queue["freq"]
    queue["effective_impact_score"] = queue["impact_score"]
    queue["effective_issue_type"] = queue["effective_proposed_action"]
    queue["effective_rank1_label"] = queue["onto_label"]
    queue["effective_rank1_score"] = None
    queue["effective_rank2_label"] = queue["rank2_label"]
    queue["effective_rank2_score"] = None
    queue["effective_rank3_label"] = None
    queue["effective_rank3_score"] = None
    queue["raw_response_ok"] = False
    return queue


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
    label = run_label()
    review = load_review_module()
    review.ROW_BATCH_SIZE = ROW_BATCH
    review.CLUSTER_BATCH_SIZE = 1
    review.UNRESOLVED_BATCH_SIZE = 1

    queue = build_queue()
    queue = queue.drop(columns=stale_review_cols(queue))
    queue.to_parquet(queue_path(), index=False)

    print(f"{label}: target rows = {len(queue):,}", flush=True)

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
        print(f"{label}: review round {round_idx}, pending {len(pending):,}", flush=True)
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

        merged = review.merge_and_write(pending, results, results_path())
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

    final.to_parquet(results_path(), index=False)
    review.write_summary(
        path=summary_path(),
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=final,
        stats=total_stats,
        title=f"Remaining-Heuristic No-Majority Results {label}",
    )

    remaining = int(missing_mask(final).sum())
    with summary_path().open("a") as f:
        f.write("\n## Run details\n")
        f.write(f"\n- run label: `{label}`\n")
        f.write(f"- target rows: `{len(queue):,}`\n")
        f.write(f"- remaining missing after retries: `{remaining:,}`\n")
        f.write(f"- retry rounds: `{MAX_RETRY_ROUNDS}`\n")
        f.write(f"- row batch size: `{ROW_BATCH}`\n")
        f.write(f"- concurrency: `{CONCURRENCY}`\n")

    print(f"{label}: complete, remaining missing = {remaining}", flush=True)
    print(f"{label}: results = {results_path()}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
