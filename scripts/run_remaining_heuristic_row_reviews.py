"""Run full row-level reviews over the remaining heuristic overlay rows.

This pass targets the rows in `ontology_enrichment_overlay_v2_reviewed.parquet`
whose current `decision_source` is still `heuristic`. It keeps cluster review as
separate context and asks GPT-5.4-mini to adjudicate the rows themselves.

Each run:
1. builds a row-only review queue from the remaining heuristic overlay rows
2. runs a main async review
3. performs a micro-retry on any missing rows
4. writes a final per-run artifact
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

OVERLAY_REVIEWED_PATH = DATA_DIR / "ontology_enrichment_overlay_v2_reviewed.parquet"
AUDIT_PATH = DATA_DIR / "grounding_rescue_audit_v2.parquet"
CLUSTERS_REVIEWED_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2_reviewed.parquet"


def load_review_module():
    path = ROOT / "scripts" / "run_ontology_v2_grounding_review.py"
    spec = importlib.util.spec_from_file_location("remaining_heuristic_row_review_main", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_queue() -> pd.DataFrame:
    overlay = pd.read_parquet(OVERLAY_REVIEWED_PATH)
    audit = pd.read_parquet(AUDIT_PATH)
    clusters = pd.read_parquet(CLUSTERS_REVIEWED_PATH)

    heuristic = overlay[overlay["decision_source"] == "heuristic"].copy()
    heuristic = heuristic.rename(
        columns={
            "final_decision": "heuristic_final_decision",
            "overlay_action": "heuristic_overlay_action",
            "decision_source": "heuristic_decision_source",
        }
    )

    queue = heuristic.merge(
        audit[
            [
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
                "cluster_id",
            ]
        ],
        on=["label", "cluster_id"],
        how="left",
        suffixes=("", "_audit"),
    )
    queue = queue.merge(
        clusters[
            [
                "cluster_id",
                "final_decision",
                "final_cluster_proposal",
                "cluster_representative_label",
                "cluster_size",
                "cluster_weighted_freq",
                "cluster_weighted_unique_papers",
                "cluster_mean_similarity",
                "dominant_onto_label",
                "dominant_share",
                "member_labels_json",
            ]
        ].rename(
            columns={
                "final_decision": "cluster_final_decision",
                "final_cluster_proposal": "cluster_final_proposal",
            }
        ),
        on="cluster_id",
        how="left",
    )

    queue = queue.sort_values(["impact_score", "freq", "label"], ascending=[False, False, True]).reset_index(drop=True)
    queue["review_item_type"] = "row"
    queue["review_id"] = [f"rhr_{i:05d}_row" for i in range(1, len(queue) + 1)]
    queue["effective_score_band"] = queue["score_band"]
    queue["effective_proposed_action"] = queue["issue_type"]
    queue["effective_rank1_label"] = queue["onto_label"]
    queue["effective_rank1_score"] = queue["rank1_score"]
    queue["effective_rank2_label"] = queue["rank2_label"]
    queue["effective_rank2_score"] = queue["rank2_score"]
    queue["effective_rank3_label"] = queue["rank3_label"]
    queue["effective_rank3_score"] = queue["rank3_score"]
    queue["effective_issue_type"] = queue["issue_type"]
    queue["effective_freq"] = queue["freq"]
    queue["effective_impact_score"] = queue["impact_score"]
    queue["audit_unique_papers"] = queue["unique_papers"]
    queue["audit_unique_edge_instances"] = queue["unique_edge_instances"]
    queue["audit_directed_edge_instances"] = queue["directed_edge_instances"]
    queue["audit_onto_source"] = queue["onto_source"]
    queue["audit_onto_domain"] = queue["onto_domain"]
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


def write_comparison_summary(path: Path, merged: pd.DataFrame, stats) -> None:
    lines = [
        "# Remaining Heuristic Row Review",
        "",
        f"- model: `{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})`",
        f"- reviewed rows: `{len(merged):,}`",
        f"- batches: `{stats.batches:,}`",
        f"- prompt tokens: `{stats.prompt_tokens:,}`",
        f"- completion tokens: `{stats.completion_tokens:,}`",
        "",
        "## Final decisions",
    ]
    for key, value in merged["decision"].fillna("missing").value_counts().items():
        lines.append(f"- `{key}`: `{int(value):,}`")
    lines.extend(["", "## Heuristic comparison"])
    agreement = int((merged["decision"] == merged["heuristic_final_decision"]).sum())
    lines.append(f"- agreement with current heuristic decision: `{agreement:,}` / `{len(merged):,}`")
    lines.extend(["", "## Cluster comparison"])
    cluster_rows = merged["cluster_final_decision"].notna()
    cluster_agree = int((merged.loc[cluster_rows, "decision"] == merged.loc[cluster_rows, "cluster_final_decision"]).sum())
    lines.append(f"- rows with cluster decision context: `{int(cluster_rows.sum()):,}`")
    lines.append(f"- agreement with cluster decision where available: `{cluster_agree:,}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> None:
    queue = build_queue()
    queue_path = review.suffix_name("remaining_heuristic_row_review_queue", ".parquet")
    main_path = review.suffix_name("remaining_heuristic_row_review_results", ".parquet")
    summary_path = review.suffix_name("remaining_heuristic_row_review_results", ".md")
    retry_queue_path = review.suffix_name("remaining_heuristic_row_review_retry_queue", ".parquet")
    retry_path = review.suffix_name("remaining_heuristic_row_review_retry_results", ".parquet")
    final_path = review.suffix_name("remaining_heuristic_row_review_results_final", ".parquet")
    final_summary_path = review.suffix_name("remaining_heuristic_row_review_results_final", ".md")

    queue.to_parquet(queue_path, index=False)
    print(f"Built remaining-heuristic queue: {len(queue):,} rows", flush=True)

    client = review.load_openai_client()

    results, stats = await review.run_batches(
        client=client,
        model=review.MAIN_MODEL,
        reasoning_effort=review.MAIN_REASONING_EFFORT,
        df=queue,
        concurrency=review.MAIN_CONCURRENCY,
    )
    merged = review.merge_and_write(queue, results, main_path)
    review.write_summary(
        path=summary_path,
        model=f"{review.MAIN_MODEL} (reasoning={review.MAIN_REASONING_EFFORT})",
        merged=merged,
        stats=stats,
        title="Remaining Heuristic Row Review Results",
    )

    pending = merged.loc[missing_mask(merged)].copy()
    pending = pending.drop(columns=stale_review_cols(pending))
    pending.to_parquet(retry_queue_path, index=False)

    if not pending.empty:
        original_row_batch = review.ROW_BATCH_SIZE
        original_concurrency = review.MAIN_CONCURRENCY
        review.ROW_BATCH_SIZE = 1
        review.MAIN_CONCURRENCY = min(16, original_concurrency)
        retry_results, retry_stats = await review.run_batches(
            client=client,
            model=review.MAIN_MODEL,
            reasoning_effort=review.MAIN_REASONING_EFFORT,
            df=pending,
            concurrency=review.MAIN_CONCURRENCY,
        )
        review.ROW_BATCH_SIZE = original_row_batch
        review.MAIN_CONCURRENCY = original_concurrency
        retry_merged = review.merge_and_write(pending, retry_results, retry_path)

        final = merged.set_index("review_id").copy()
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
        stats.batches += retry_stats.batches
        stats.prompt_tokens += retry_stats.prompt_tokens
        stats.completion_tokens += retry_stats.completion_tokens
    else:
        final = merged.copy()
        pending.to_parquet(retry_path, index=False)

    final.to_parquet(final_path, index=False)
    write_comparison_summary(final_summary_path, final, stats)
    print(f"Final remaining-heuristic review written: {final_path}", flush=True)


if __name__ == "__main__":
    review = load_review_module()
    asyncio.run(main())
