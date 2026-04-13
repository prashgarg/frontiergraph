"""Finalize grounding review votes across run1/run2/run3.

This script:
1. Performs tiny micro-retries on the remaining misses in each merged run.
2. Writes final per-run artifacts.
3. Builds a 3-run vote matrix and majority-vote outputs.
4. Surfaces disagreement patterns, especially 2-1 splits.
"""
from __future__ import annotations

import asyncio
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

RUNS = [("run1", ""), ("run2", "run2"), ("run3", "run3")]

MICRO_RETRY_CONCURRENCY = 8
MICRO_RETRY_ROW_BATCH = 1
MICRO_RETRY_CLUSTER_BATCH = 1
MICRO_RETRY_UNRESOLVED_BATCH = 1


def suffix_name(stem: str, suffix: str, ext: str) -> Path:
    infix = f"_{suffix}" if suffix else ""
    return DATA_DIR / f"{stem}{infix}{ext}"


def load_review_module():
    path = ROOT / "scripts" / "run_ontology_v2_grounding_review.py"
    spec = importlib.util.spec_from_file_location("grounding_review_main_finalize", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_summary_stat(path: Path, label: str) -> int:
    text = path.read_text() if path.exists() else ""
    pattern = r"- " + re.escape(label) + r": `([0-9,]+)`"
    match = re.search(pattern, text)
    return int(match.group(1).replace(",", "")) if match else 0


def missing_mask(df: pd.DataFrame) -> pd.Series:
    return df["decision"].isna() | (~df["raw_response_ok"].fillna(False))


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


async def finalize_one_run(review: object, run_name: str, suffix: str) -> dict[str, int]:
    merged_path = suffix_name("main_grounding_review_v2_results_merged", suffix, ".parquet")
    merged_summary_path = suffix_name("main_grounding_review_v2_results_merged", suffix, ".md")

    micro_retry_queue_path = suffix_name("main_grounding_review_v2_micro_retry_queue", suffix, ".parquet")
    micro_retry_results_path = suffix_name("main_grounding_review_v2_micro_retry_results", suffix, ".parquet")
    micro_retry_summary_path = suffix_name("main_grounding_review_v2_micro_retry_results", suffix, ".md")
    final_results_path = suffix_name("main_grounding_review_v2_results_final", suffix, ".parquet")
    final_summary_path = suffix_name("main_grounding_review_v2_results_final", suffix, ".md")

    base = pd.read_parquet(merged_path)
    pending = base.loc[missing_mask(base)].copy()
    pending = pending.drop(columns=stale_review_cols(pending))
    pending.to_parquet(micro_retry_queue_path, index=False)

    pre_missing = int(missing_mask(base).sum())

    if not pending.empty:
        review.ROW_BATCH_SIZE = MICRO_RETRY_ROW_BATCH
        review.CLUSTER_BATCH_SIZE = MICRO_RETRY_CLUSTER_BATCH
        review.UNRESOLVED_BATCH_SIZE = MICRO_RETRY_UNRESOLVED_BATCH

        client = review.load_openai_client()
        retry_results, retry_stats = await review.run_batches(
            client=client,
            model=review.MAIN_MODEL,
            reasoning_effort=review.MAIN_REASONING_EFFORT,
            df=pending,
            concurrency=MICRO_RETRY_CONCURRENCY,
        )
        retry_merged = review.merge_and_write(pending, retry_results, micro_retry_results_path)
        review.write_summary(
            path=micro_retry_summary_path,
            model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
            merged=retry_merged,
            stats=retry_stats,
            title=f"Micro Retry Grounding Review Results {run_name}",
        )

        final = base.set_index("review_id").copy()
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
                final[col] = retry_indexed[col].combine_first(final[col])
        final = final.reset_index()

        prior_batches = parse_summary_stat(merged_summary_path, "batches")
        prior_prompt = parse_summary_stat(merged_summary_path, "prompt tokens")
        prior_completion = parse_summary_stat(merged_summary_path, "completion tokens")
        total_stats = review.RunStats(
            batches=prior_batches + retry_stats.batches,
            items=len(final),
            prompt_tokens=prior_prompt + retry_stats.prompt_tokens,
            completion_tokens=prior_completion + retry_stats.completion_tokens,
        )
    else:
        final = base.copy()
        total_stats = review.RunStats(
            batches=parse_summary_stat(merged_summary_path, "batches"),
            items=len(final),
            prompt_tokens=parse_summary_stat(merged_summary_path, "prompt tokens"),
            completion_tokens=parse_summary_stat(merged_summary_path, "completion tokens"),
        )
        empty_retry = pending.copy()
        empty_retry.to_parquet(micro_retry_results_path, index=False)
        micro_retry_summary_path.write_text(
            f"# Micro Retry Grounding Review Results {run_name}\n\n- no pending misses\n"
        )

    final.to_parquet(final_results_path, index=False)
    review.write_summary(
        path=final_summary_path,
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=final,
        stats=total_stats,
        title=f"Final Grounding Review Results {run_name}",
    )

    post_missing = int(missing_mask(final).sum())
    recovered = pre_missing - post_missing
    with final_summary_path.open("a") as f:
        f.write("\n## Micro retry details\n")
        f.write(f"\n- pending before micro retry: `{pre_missing:,}`\n")
        f.write(f"- recovered on micro retry: `{recovered:,}`\n")
        f.write(f"- remaining missing after micro retry: `{post_missing:,}`\n")
        f.write(
            f"- micro retry batch sizes: row=`{MICRO_RETRY_ROW_BATCH}`, "
            f"cluster=`{MICRO_RETRY_CLUSTER_BATCH}`, unresolved=`{MICRO_RETRY_UNRESOLVED_BATCH}`\n"
        )
        f.write(f"- micro retry concurrency: `{MICRO_RETRY_CONCURRENCY}`\n")

    return {
        "pre_missing": pre_missing,
        "post_missing": post_missing,
        "recovered": recovered,
    }


def majority_vote(values: list[str | None]) -> tuple[str | None, int, str, str]:
    clean = [v for v in values if v and v != "missing"]
    pattern = " | ".join(v if v else "missing" for v in values)
    if not clean:
        return None, 0, "all_missing", pattern
    counts = Counter(clean)
    top = counts.most_common()
    if len(top) == 1:
        top_label, top_count = top[0]
        split_type = "unanimous" if top_count == 3 else "available_only"
        return top_label, top_count, split_type, pattern
    if top[0][1] >= 2:
        top_label, top_count = top[0]
        split_type = "two_to_one" if len(clean) == 3 else "two_with_missing"
        return top_label, top_count, split_type, pattern
    return None, top[0][1], "no_majority", pattern


def build_vote_outputs() -> None:
    vote_matrix_path = DATA_DIR / "main_grounding_review_v2_vote_matrix.parquet"
    vote_matrix_csv_path = DATA_DIR / "main_grounding_review_v2_vote_matrix.csv"
    majority_path = DATA_DIR / "main_grounding_review_v2_majority_vote.parquet"
    majority_csv_path = DATA_DIR / "main_grounding_review_v2_majority_vote.csv"
    split_path = DATA_DIR / "main_grounding_review_v2_two_to_one_splits.parquet"
    split_csv_path = DATA_DIR / "main_grounding_review_v2_two_to_one_splits.csv"
    split_md_path = DATA_DIR / "main_grounding_review_v2_two_to_one_splits.md"
    disagreement_md_path = DATA_DIR / "main_grounding_review_v2_disagreements.md"

    runs: dict[str, pd.DataFrame] = {}
    for run_name, suffix in RUNS:
        runs[run_name] = pd.read_parquet(
            suffix_name("main_grounding_review_v2_results_final", suffix, ".parquet")
        ).set_index("review_id")

    base = runs["run1"].reset_index()
    context_cols = [
        c
        for c in [
            "review_id",
            "review_item_type",
            "label",
            "cluster_id",
            "effective_score_band",
            "effective_proposed_action",
            "rank1_label",
            "rank2_label",
            "audit_onto_source",
            "audit_onto_domain",
            "impact_score",
            "effective_impact_score",
        ]
        if c in base.columns
    ]
    vote = base[context_cols].copy().set_index("review_id")
    for run_name, df in runs.items():
        for col in ["decision", "confidence", "canonical_target_label", "new_concept_family_label", "reason"]:
            if col in df.columns:
                vote[f"{run_name}_{col}"] = df[col]

    majority_rows = []
    for review_id, row in vote.iterrows():
        values = [
            row.get("run1_decision"),
            row.get("run2_decision"),
            row.get("run3_decision"),
        ]
        maj, votes_count, split_type, pattern = majority_vote(values)
        majority_rows.append(
            {
                "review_id": review_id,
                "majority_decision": maj,
                "majority_votes": votes_count,
                "split_type": split_type,
                "decision_pattern": pattern,
                "unique_nonmissing_decisions": len({v for v in values if v and v != "missing"}),
            }
        )
    majority_df = pd.DataFrame(majority_rows).set_index("review_id")
    vote = vote.join(majority_df)
    vote = vote.reset_index()

    vote.to_parquet(vote_matrix_path, index=False)
    vote.to_csv(vote_matrix_csv_path, index=False)

    majority_only = vote[
        [
            c
            for c in [
                "review_id",
                "review_item_type",
                "label",
                "effective_score_band",
                "effective_proposed_action",
                "run1_decision",
                "run2_decision",
                "run3_decision",
                "majority_decision",
                "majority_votes",
                "split_type",
                "decision_pattern",
            ]
            if c in vote.columns
        ]
    ].copy()
    majority_only.to_parquet(majority_path, index=False)
    majority_only.to_csv(majority_csv_path, index=False)

    splits = vote[vote["split_type"] == "two_to_one"].copy()
    splits.to_parquet(split_path, index=False)
    splits.to_csv(split_csv_path, index=False)

    split_summary = [
        "# Two-to-One Splits",
        "",
        f"- total 2-1 splits: `{len(splits):,}`",
        "",
        "## Top patterns",
    ]
    pattern_counts = splits["decision_pattern"].value_counts().head(20)
    for pattern, count in pattern_counts.items():
        split_summary.append(f"- `{pattern}`: `{count:,}`")
    split_summary.extend(["", "## Sample rows", ""])
    sample_cols = [
        c
        for c in [
            "review_item_type",
            "label",
            "effective_score_band",
            "effective_proposed_action",
            "run1_decision",
            "run2_decision",
            "run3_decision",
            "majority_decision",
            "decision_pattern",
        ]
        if c in splits.columns
    ]
    split_summary.append(splits[sample_cols].head(40).to_markdown(index=False))
    split_md_path.write_text("\n".join(split_summary) + "\n")

    disagreement_lines = [
        "# Grounding Vote Disagreements",
        "",
        f"- total reviewed items: `{len(vote):,}`",
        f"- unanimous: `{int((vote['split_type'] == 'unanimous').sum()):,}`",
        f"- two-to-one splits: `{int((vote['split_type'] == 'two_to_one').sum()):,}`",
        f"- two-with-missing: `{int((vote['split_type'] == 'two_with_missing').sum()):,}`",
        f"- no majority: `{int((vote['split_type'] == 'no_majority').sum()):,}`",
        f"- all missing: `{int((vote['split_type'] == 'all_missing').sum()):,}`",
        "",
        "## Majority decisions",
    ]
    for decision, count in vote["majority_decision"].fillna("missing").value_counts().items():
        disagreement_lines.append(f"- `{decision}`: `{count:,}`")
    disagreement_lines.extend(["", "## Split types by proposed action"])
    by_action = (
        vote.groupby("effective_proposed_action")["split_type"]
        .value_counts()
        .unstack(fill_value=0)
        .sort_values(by="two_to_one", ascending=False)
    )
    disagreement_lines.append("")
    disagreement_lines.append(by_action.head(20).to_markdown())
    disagreement_md_path.write_text("\n".join(disagreement_lines) + "\n")


async def main() -> None:
    review = load_review_module()
    for run_name, suffix in RUNS:
        stats = await finalize_one_run(review, run_name, suffix)
        print(
            f"{run_name}: pre_missing={stats['pre_missing']}, "
            f"recovered={stats['recovered']}, post_missing={stats['post_missing']}",
            flush=True,
        )
    build_vote_outputs()
    print("Built vote matrix, majority vote outputs, and disagreement reports.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
