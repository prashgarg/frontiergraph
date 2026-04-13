from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from analyze_llm_screening_v2_run import _parse_responses


BAD_FAILURE_MODES = {
    "broad_endpoint",
    "generic_mediator",
    "method_not_mechanism",
    "canonical_pairing",
    "placeholder_like",
    "unclear_question_object",
}


def _expand_g(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_g_batch":
            continue
        p = dict(row.parsed)
        rows.append(
            {
                "request_key": row.request_key,
                "candidate_id": p.get("candidate_id"),
                "variant": p.get("variant"),
                "overall_screening_value": p.get("overall_screening_value"),
                "endpoint_specificity": p.get("endpoint_specificity"),
                "mediator_specificity": p.get("mediator_specificity"),
                "question_object_clarity": p.get("question_object_clarity"),
                "mechanism_clarity": p.get("mechanism_clarity"),
                "canonicality_risk": p.get("canonicality_risk"),
                "local_crowding_risk": p.get("local_crowding_risk"),
                "confidence": p.get("confidence"),
                "flags": p.get("flags", []),
                "evidence_fields": p.get("evidence_fields", []),
                "reason": p.get("reason"),
                "parse_mode": row.parse_mode,
                "response_id": row.response_id,
            }
        )
    return pd.DataFrame(rows)


def _expand_e(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_e_batch":
            continue
        p = dict(row.parsed)
        rows.append(
            {
                "request_key": row.request_key,
                "candidate_id": p.get("candidate_id"),
                "screen_decision": p.get("screen_decision"),
                "primary_failure_mode": p.get("primary_failure_mode"),
                "confidence": p.get("confidence"),
                "flags": p.get("flags", []),
                "evidence_fields": p.get("evidence_fields", []),
                "reason": p.get("reason"),
                "parse_mode": row.parse_mode,
            }
        )
    return pd.DataFrame(rows)


def _expand_h(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_h_batch":
            continue
        p = dict(row.parsed)
        rows.append(
            {
                "request_key": row.request_key,
                "pair_id": p.get("pair_id"),
                "preferred_candidate": p.get("preferred_candidate"),
                "endpoint_specificity_preference": p.get("endpoint_specificity_preference"),
                "mechanism_clarity_preference": p.get("mechanism_clarity_preference"),
                "question_object_clarity_preference": p.get("question_object_clarity_preference"),
                "confidence": p.get("confidence"),
                "flags_a": p.get("flags_a", []),
                "flags_b": p.get("flags_b", []),
                "evidence_fields": p.get("evidence_fields", []),
                "reason": p.get("reason"),
                "parse_mode": row.parse_mode,
            }
        )
    return pd.DataFrame(rows)


def _load_run(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    parsed_df, _ = _parse_responses(run_dir / "responses.jsonl")
    return parsed_df, _expand_g(parsed_df), _expand_e(parsed_df), _expand_h(parsed_df)


def _majority_vote(values: list[str]) -> tuple[str, int]:
    clean = [v for v in values if isinstance(v, str)]
    if not clean:
        return "tie", 0
    counts = pd.Series(clean).value_counts()
    top_value = str(counts.index[0])
    top_count = int(counts.iloc[0])
    if top_count >= 2:
        return top_value, top_count
    return "tie", top_count


def _build_pairwise_consensus(pair_meta: pd.DataFrame, runs: list[pd.DataFrame]) -> pd.DataFrame:
    merged = pair_meta[["pair_id", "field_slug", "horizon", "pair_type", "a_candidate_id", "b_candidate_id"]].copy()
    for idx, run in enumerate(runs, start=1):
        merged = merged.merge(
            run[["pair_id", "preferred_candidate", "confidence"]].rename(
                columns={
                    "preferred_candidate": f"preferred_{idx}",
                    "confidence": f"confidence_{idx}",
                }
            ),
            on="pair_id",
            how="left",
        )
    prefs = [f"preferred_{i}" for i in range(1, len(runs) + 1)]
    confs = [f"confidence_{i}" for i in range(1, len(runs) + 1)]
    majority_choice: list[str] = []
    majority_count: list[int] = []
    mean_conf: list[float] = []
    for row in merged.itertuples(index=False):
        vals = [getattr(row, col) for col in prefs]
        choice, count = _majority_vote(vals)
        majority_choice.append(choice)
        majority_count.append(count)
        conf_values = [getattr(row, col) for col in confs if pd.notna(getattr(row, col))]
        mean_conf.append(float(pd.Series(conf_values).mean()) if conf_values else float("nan"))
    merged["majority_preference"] = majority_choice
    merged["majority_count"] = majority_count
    merged["mean_confidence"] = mean_conf
    merged["stable_preference"] = merged.apply(
        lambda r: r["majority_preference"]
        if (r["majority_count"] >= 2 and float(r["mean_confidence"] or 0) >= 3.0)
        else "tie",
        axis=1,
    )
    return merged


def _weak_veto(screen_df: pd.DataFrame) -> pd.DataFrame:
    out = screen_df.copy()
    out["weak_veto_drop"] = (
        out["screen_decision"].eq("fail")
        & out["primary_failure_mode"].isin(BAD_FAILURE_MODES)
        & (out["veto_confidence"] >= 4)
        & (out["overall_screening_value"] <= 2)
    )
    return out


def _coalesce_candidate_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "candidate_id" in out.columns:
        return out
    left = "candidate_id_x" if "candidate_id_x" in out.columns else None
    right = "candidate_id_y" if "candidate_id_y" in out.columns else None
    if left and right:
        out["candidate_id"] = out[left].combine_first(out[right])
        out = out.drop(columns=[left, right])
    elif left:
        out = out.rename(columns={left: "candidate_id"})
    elif right:
        out = out.rename(columns={right: "candidate_id"})
    return out


def _rerank_within_bucket(candidates: pd.DataFrame, pairwise_consensus: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    edge_df = pairwise_consensus[pairwise_consensus["stable_preference"].isin(["A", "B"])].copy()
    for (horizon, field_slug), sub in candidates.groupby(["horizon", "field_slug"], sort=True):
        bucket = sub[~sub["weak_veto_drop"]].copy()
        if bucket.empty:
            continue
        score_map = {cid: 0.0 for cid in bucket["candidate_id"]}
        local_edges = edge_df[(edge_df["horizon"] == horizon) & (edge_df["field_slug"] == field_slug)]
        for edge in local_edges.itertuples(index=False):
            a_id = edge.a_candidate_id
            b_id = edge.b_candidate_id
            if a_id not in score_map or b_id not in score_map:
                continue
            if edge.stable_preference == "A":
                score_map[a_id] += 1.0
                score_map[b_id] -= 1.0
            elif edge.stable_preference == "B":
                score_map[b_id] += 1.0
                score_map[a_id] -= 1.0
        bucket["pairwise_copeland_score"] = bucket["candidate_id"].map(score_map).astype(float)
        bucket = bucket.sort_values(
            ["pairwise_copeland_score", "overall_screening_value", "surface_rank"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
        bucket["llm_bucket_rank"] = range(1, len(bucket) + 1)
        rows.append(bucket)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _bucket_summary(df: pd.DataFrame, rank_col: str, *, top_k: int | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (horizon, field_slug), sub in df.groupby(["horizon", "field_slug"], sort=True):
        ranked = sub.sort_values(rank_col).copy()
        if top_k is not None:
            ranked = ranked.head(top_k).copy()
        rows.append(
            {
                "horizon": int(horizon),
                "field_slug": str(field_slug),
                "top_k": int(top_k or len(ranked)),
                "candidate_count": int(len(ranked)),
                "unique_targets": int(ranked["v_label"].nunique(dropna=False)),
                "top_target_share": float(ranked["v_label"].value_counts(normalize=True, dropna=False).iloc[0]),
                "broad_share": float((ranked["endpoint_broadness_pct"] >= 0.85).mean()),
                "low_compression_share": float((ranked["compression_confidence"] < 0.35).mean()),
                "mean_overall_screening_value": float(ranked["overall_screening_value"].mean()),
                "mean_pairwise_copeland_score": float(ranked.get("pairwise_copeland_score", pd.Series([0] * len(ranked))).mean()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-run", type=Path, default=Path("outputs/paper/113_llm_screening_global_top250_none"))
    parser.add_argument("--repeat2-run", type=Path, default=Path("outputs/paper/114_llm_screening_global_top250_repeat2"))
    parser.add_argument("--repeat3-run", type=Path, default=Path("outputs/paper/115_llm_screening_global_top250_repeat3"))
    parser.add_argument("--pack-dir", type=Path, default=Path("outputs/paper/112_llm_screening_global_top250_prompt_pack"))
    parser.add_argument("--out", type=Path, default=Path("outputs/paper/116_llm_screening_global_top250_analysis"))
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_meta = pd.read_csv(args.pack_dir / "global_top250_candidate_rows.csv", low_memory=False)
    candidate_meta["global_rank"] = (
        candidate_meta.groupby("horizon")["surface_rank"].rank(method="first", ascending=True).astype(int)
    )
    candidate_meta["bucket_rank"] = (
        candidate_meta.groupby(["horizon", "field_slug"])["surface_rank"].rank(method="first", ascending=True).astype(int)
    )
    pair_meta = pd.read_csv(args.pack_dir / "global_top250_pairwise_rows.csv", low_memory=False)

    run_map = {
        "baseline": _load_run(args.baseline_run),
        "repeat2": _load_run(args.repeat2_run),
        "repeat3": _load_run(args.repeat3_run),
    }

    parse_rows: list[dict[str, Any]] = []
    for run_name, (parsed_df, _, _, _) in run_map.items():
        counts = parsed_df.groupby(["source_name", "parse_mode"]).size().reset_index(name="n")
        for row in counts.itertuples(index=False):
            parse_rows.append(
                {
                    "run_name": run_name,
                    "source_name": row.source_name,
                    "parse_mode": row.parse_mode,
                    "n": int(row.n),
                }
            )
    parse_summary = pd.DataFrame(parse_rows)
    parse_summary.to_csv(out_dir / "parse_summary.csv", index=False)

    g_base = _coalesce_candidate_id(
        run_map["baseline"][1].merge(candidate_meta, left_on="request_key", right_on="candidate_row_id", how="left")
    )
    e_base = _coalesce_candidate_id(
        run_map["baseline"][2].merge(candidate_meta, left_on="request_key", right_on="candidate_row_id", how="left")
    )
    h_base = run_map["baseline"][3].merge(pair_meta, on="pair_id", how="left")
    h_rep2 = run_map["repeat2"][3]
    h_rep3 = run_map["repeat3"][3]

    g_base.to_csv(out_dir / "prompt_g_baseline_scores.csv", index=False)
    e_base.to_csv(out_dir / "prompt_e_baseline_scores.csv", index=False)
    h_base.to_csv(out_dir / "prompt_h_baseline_scores.csv", index=False)

    h_consensus = _build_pairwise_consensus(pair_meta, [h_base, h_rep2, h_rep3])
    h_repeat = (
        h_base[["pair_id", "preferred_candidate", "confidence"]]
        .rename(columns={"preferred_candidate": "preferred_r1", "confidence": "confidence_r1"})
        .merge(
            h_rep2[["pair_id", "preferred_candidate", "confidence"]].rename(
                columns={"preferred_candidate": "preferred_r2", "confidence": "confidence_r2"}
            ),
            on="pair_id",
            how="inner",
        )
        .merge(
            h_rep3[["pair_id", "preferred_candidate", "confidence"]].rename(
                columns={"preferred_candidate": "preferred_r3", "confidence": "confidence_r3"}
            ),
            on="pair_id",
            how="inner",
        )
    )
    h_repeat["exact_three_run_agreement"] = (
        (h_repeat["preferred_r1"] == h_repeat["preferred_r2"])
        & (h_repeat["preferred_r1"] == h_repeat["preferred_r3"])
    )
    h_repeat.to_csv(out_dir / "prompt_h_repeatability.csv", index=False)

    h_summary = pd.DataFrame(
        [
            {
                "n_pairs": int(len(h_repeat)),
                "exact_three_run_agreement": float(h_repeat["exact_three_run_agreement"].mean()),
                "stable_preference_share": float(h_consensus["stable_preference"].isin(["A", "B"]).mean()),
                "stable_tie_share": float(h_consensus["stable_preference"].eq("tie").mean()),
            }
        ]
    )
    h_summary.to_csv(out_dir / "prompt_h_repeatability_summary.csv", index=False)

    screened = (
        g_base[
            [
                "candidate_row_id",
                "candidate_id",
                "field_slug",
                "horizon",
                "surface_rank",
                "global_rank",
                "bucket_rank",
                "u_label",
                "focal_mediator_label",
                "v_label",
                "endpoint_broadness_pct",
                "endpoint_resolution_score",
                "focal_mediator_specificity_score",
                "compression_confidence",
                "overall_screening_value",
                "confidence",
                "reason",
            ]
        ]
        .rename(columns={"confidence": "scalar_confidence", "reason": "scalar_reason"})
        .merge(
            e_base[
                [
                    "candidate_row_id",
                    "screen_decision",
                    "primary_failure_mode",
                    "confidence",
                    "reason",
                ]
            ].rename(columns={"confidence": "veto_confidence", "reason": "veto_reason"}),
            on="candidate_row_id",
            how="left",
        )
    )
    screened = _weak_veto(screened)
    screened.to_csv(out_dir / "candidate_screening_merged.csv", index=False)

    reranked = _rerank_within_bucket(screened, h_consensus)
    reranked["bucket_rank_change"] = reranked["bucket_rank"] - reranked["llm_bucket_rank"]
    reranked.to_csv(out_dir / "global_top250_bucketed_llm_reranked_package.csv", index=False)

    baseline_bucket_top10 = _bucket_summary(screened[~screened["weak_veto_drop"]].copy(), "surface_rank", top_k=10)
    reranked_bucket_top10 = _bucket_summary(reranked, "llm_bucket_rank", top_k=10)
    baseline_bucket_top10.to_csv(out_dir / "baseline_bucket_top10_summary.csv", index=False)
    reranked_bucket_top10.to_csv(out_dir / "reranked_bucket_top10_summary.csv", index=False)

    veto_examples = screened[screened["weak_veto_drop"]].sort_values(["horizon", "surface_rank"]).head(40)
    veto_examples.to_csv(out_dir / "examples_weak_veto_drops.csv", index=False)

    promo_examples = reranked.sort_values(["bucket_rank_change", "horizon", "field_slug"], ascending=[False, True, True]).head(40)
    promo_examples.to_csv(out_dir / "examples_pairwise_promotions.csv", index=False)

    stable_pairs = h_consensus[h_consensus["stable_preference"].isin(["A", "B"])].copy()
    stable_pairs.to_csv(out_dir / "pairwise_consensus.csv", index=False)

    lines = [
        "# Global Top-250 LLM Screening Analysis",
        "",
        "## Parse and stability",
        f"- Pairwise exact three-run agreement: {h_summary.iloc[0]['exact_three_run_agreement']:.3f}",
        f"- Stable preference share: {h_summary.iloc[0]['stable_preference_share']:.3f}",
        f"- Stable tie share: {h_summary.iloc[0]['stable_tie_share']:.3f}",
        "",
        "## Weak veto",
        f"- Weak-veto drop share: {screened['weak_veto_drop'].mean():.3f}",
        f"- Mean scalar score among weak-veto drops: {screened.loc[screened['weak_veto_drop'], 'overall_screening_value'].mean():.3f}",
        "",
        "## Bucket-level effect",
        f"- Mean baseline bucket top10 top-target share: {baseline_bucket_top10['top_target_share'].mean():.3f}",
        f"- Mean reranked bucket top10 top-target share: {reranked_bucket_top10['top_target_share'].mean():.3f}",
        f"- Mean baseline bucket top10 broad share: {baseline_bucket_top10['broad_share'].mean():.3f}",
        f"- Mean reranked bucket top10 broad share: {reranked_bucket_top10['broad_share'].mean():.3f}",
        f"- Mean baseline bucket top10 low-compression share: {baseline_bucket_top10['low_compression_share'].mean():.3f}",
        f"- Mean reranked bucket top10 low-compression share: {reranked_bucket_top10['low_compression_share']:.3f}" if False else "",
    ]
    # Repair last line with scalar access.
    lines[-1] = f"- Mean reranked bucket top10 low-compression share: {reranked_bucket_top10['low_compression_share'].mean():.3f}"
    (out_dir / "summary.md").write_text("\n".join([x for x in lines if x != ""]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
