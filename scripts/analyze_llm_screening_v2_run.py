from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


FLAG_ENUM = [
    "broad_endpoint",
    "generic_mediator",
    "method_not_mechanism",
    "canonical_pairing",
    "placeholder_like",
    "unclear_question_object",
    "insufficient_information",
]


def _extract_text_payload(response: dict[str, Any]) -> str | None:
    for output in response.get("output", []):
        if output.get("type") != "message":
            continue
        for item in output.get("content", []):
            if item.get("type") == "output_text":
                return item.get("text")
            if item.get("type") == "refusal":
                return None
    return None


def _request_key_from_custom_id(custom_id: str | None) -> str | None:
    if not custom_id or "-" not in custom_id:
        return None
    return custom_id.split("-", 2)[-1]


def _repair_truncated_json(text_payload: str) -> tuple[dict[str, Any] | None, str | None]:
    reason_marker = ',"reason":"'
    if reason_marker not in text_payload:
        return None, None
    prefix, reason_tail = text_payload.split(reason_marker, 1)
    sanitized_reason = reason_tail.replace("\\", "\\\\").replace('"', '\\"')
    if sanitized_reason.endswith("}"):
        sanitized_reason = sanitized_reason[:-1]
    repaired = f'{prefix},"reason":"{sanitized_reason}"}}'
    try:
        return json.loads(repaired), "repaired_truncated_reason"
    except json.JSONDecodeError:
        return None, None


def _parse_responses(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            text_payload = _extract_text_payload(raw["response"])
            if not text_payload:
                failures.append({"custom_id": raw.get("custom_id"), "error": "missing_output_text"})
                continue
            try:
                parsed = json.loads(text_payload)
                parse_mode = "direct"
            except json.JSONDecodeError as exc:
                repaired, parse_mode = _repair_truncated_json(text_payload)
                if repaired is None:
                    failures.append(
                        {
                            "custom_id": raw.get("custom_id"),
                            "source_name": raw.get("source_name"),
                            "error": f"json_decode_error: {exc}",
                            "raw_text": text_payload[:1000],
                        }
                    )
                    continue
                parsed = repaired
            rows.append(
                {
                    "custom_id": raw.get("custom_id"),
                    "request_key": _request_key_from_custom_id(raw.get("custom_id")),
                    "source_name": raw.get("source_name"),
                    "model": raw["response"].get("model"),
                    "response_id": raw["response"].get("id"),
                    "parse_mode": parse_mode,
                    "parsed": parsed,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(failures)


def _expand_b(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_b_batch_2000":
            continue
        p = dict(row.parsed)
        out = {
            "custom_id": row.custom_id,
            "request_key": row.request_key,
            "variant": p.get("variant"),
            "candidate_id": p.get("candidate_id"),
            "source_name": row.source_name,
            "response_id": row.response_id,
            "model": row.model,
            "parse_mode": row.parse_mode,
            "flags": p.get("flags", []),
            "evidence_fields": p.get("evidence_fields", []),
            "reason": p.get("reason"),
            "overall_screening_value": p.get("overall_screening_value"),
            "endpoint_specificity": p.get("endpoint_specificity"),
            "mediator_specificity": p.get("mediator_specificity"),
            "question_object_clarity": p.get("question_object_clarity"),
            "mechanism_clarity": p.get("mechanism_clarity"),
            "canonicality_risk": p.get("canonicality_risk"),
            "local_crowding_risk": p.get("local_crowding_risk"),
            "confidence": p.get("confidence"),
        }
        rows.append(out)
    return pd.DataFrame(rows)


def _expand_e(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_e_batch_2000":
            continue
        p = dict(row.parsed)
        rows.append(
            {
                "custom_id": row.custom_id,
                "request_key": row.request_key,
                "variant": p.get("variant"),
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


def _expand_f(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_f_batch_2000":
            continue
        p = dict(row.parsed)
        rows.append(
            {
                "custom_id": row.custom_id,
                "request_key": row.request_key,
                "pair_id": p.get("pair_id"),
                "preferred_candidate_swapped": p.get("preferred_candidate"),
                "endpoint_specificity_preference_swapped": p.get("endpoint_specificity_preference"),
                "mechanism_clarity_preference_swapped": p.get("mechanism_clarity_preference"),
                "question_object_clarity_preference_swapped": p.get("question_object_clarity_preference"),
                "confidence_swapped": p.get("confidence"),
                "flags_a_swapped": p.get("flags_a", []),
                "flags_b_swapped": p.get("flags_b", []),
                "evidence_fields": p.get("evidence_fields", []),
                "reason_swapped": p.get("reason"),
                "parse_mode": row.parse_mode,
            }
        )
    out = pd.DataFrame(rows)
    for src, dst in [
        ("preferred_candidate_swapped", "preferred_candidate_originalized"),
        ("endpoint_specificity_preference_swapped", "endpoint_specificity_preference_originalized"),
        ("mechanism_clarity_preference_swapped", "mechanism_clarity_preference_originalized"),
        ("question_object_clarity_preference_swapped", "question_object_clarity_preference_originalized"),
    ]:
        out[dst] = out[src].map({"A": "B", "B": "A", "tie": "tie"})
    return out


def _triage_bucket(score: float) -> str:
    if pd.isna(score):
        return "missing"
    if score >= 4:
        return "high"
    if score <= 2:
        return "low"
    return "middle"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("outputs/paper/103_llm_screening_async_runs_v2_endpoint_first"))
    parser.add_argument("--old-analysis-dir", type=Path, default=Path("outputs/paper/101_llm_screening_analysis_99_endpoint_first"))
    parser.add_argument("--candidate-pilot", type=Path, default=Path("outputs/paper/102_llm_screening_prompt_pack_v2_endpoint_first/candidate_pilot2000.csv"))
    parser.add_argument("--pairwise-pilot", type=Path, default=Path("outputs/paper/102_llm_screening_prompt_pack_v2_endpoint_first/pairwise_pilot2000.csv"))
    parser.add_argument("--out", type=Path, default=Path("outputs/paper/104_llm_screening_analysis_v2_endpoint_first"))
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed_df, failures_df = _parse_responses(args.run_dir / "responses.jsonl")
    parsed_df.to_parquet(out_dir / "parsed_responses.parquet", index=False)
    if not failures_df.empty:
        failures_df.to_csv(out_dir / "parse_failures.csv", index=False)

    b_df = _expand_b(parsed_df)
    e_df = _expand_e(parsed_df)
    f_df = _expand_f(parsed_df)
    b_df.to_csv(out_dir / "prompt_b_v2_scores.csv", index=False)
    e_df.to_csv(out_dir / "prompt_e_veto_scores.csv", index=False)
    f_df.to_csv(out_dir / "prompt_f_swapped_pairwise_scores.csv", index=False)

    candidate_meta = pd.read_csv(args.candidate_pilot, low_memory=False)
    pair_meta = pd.read_csv(args.pairwise_pilot, low_memory=False)
    old_single = pd.read_csv(args.old_analysis_dir / "single_candidate_scores.csv", low_memory=False)
    old_pair = pd.read_csv(args.old_analysis_dir / "pairwise_scores.csv", low_memory=False)

    old_a = old_single[old_single["prompt_variant"] == "semantic_blind"].copy()
    old_b = old_single[old_single["prompt_variant"] == "record_aware"].copy()
    old_c = old_pair[old_pair["prompt_variant"] == "pairwise_within_field"].copy()

    # Bv2 vs old A and old B
    ab2 = (
        old_a[["request_key", "overall_screening_value", "flags", "reason"]]
        .rename(columns={"overall_screening_value": "score_a", "flags": "flags_a", "reason": "reason_a"})
        .merge(
            old_b[["request_key", "overall_screening_value", "flags", "reason"]].rename(
                columns={"overall_screening_value": "score_b_v1", "flags": "flags_b_v1", "reason": "reason_b_v1"}
            ),
            on="request_key",
            how="inner",
        )
        .merge(
            b_df[["request_key", "overall_screening_value", "flags", "reason", "parse_mode"]].rename(
                columns={"overall_screening_value": "score_b_v2", "flags": "flags_b_v2", "reason": "reason_b_v2"}
            ),
            on="request_key",
            how="inner",
        )
        .merge(
            candidate_meta[
                [
                    "pilot_row_id",
                    "candidate_id",
                    "horizon",
                    "rank_band",
                    "surface_rank",
                    "transparent_rank",
                    "u_label",
                    "focal_mediator_label",
                    "v_label",
                    "endpoint_broadness_pct",
                    "endpoint_resolution_score",
                    "focal_mediator_specificity_score",
                    "compression_confidence",
                ]
            ],
            left_on="request_key",
            right_on="pilot_row_id",
            how="left",
        )
    )
    ab2["diff_b2_minus_b1"] = ab2["score_b_v2"] - ab2["score_b_v1"]
    ab2["diff_b2_minus_a"] = ab2["score_b_v2"] - ab2["score_a"]
    ab2["triage_b_v2"] = ab2["score_b_v2"].apply(_triage_bucket)
    ab2.to_csv(out_dir / "prompt_b_v2_comparison.csv", index=False)

    b2_summary = pd.DataFrame(
        [
            {
                "n_rows": int(len(ab2)),
                "mean_score_a": float(ab2["score_a"].mean()),
                "mean_score_b_v1": float(ab2["score_b_v1"].mean()),
                "mean_score_b_v2": float(ab2["score_b_v2"].mean()),
                "mean_diff_b2_minus_b1": float(ab2["diff_b2_minus_b1"].mean()),
                "mean_diff_b2_minus_a": float(ab2["diff_b2_minus_a"].mean()),
                "drop_share_vs_b1": float((ab2["diff_b2_minus_b1"] < 0).mean()),
                "same_share_vs_b1": float((ab2["diff_b2_minus_b1"] == 0).mean()),
                "rise_share_vs_b1": float((ab2["diff_b2_minus_b1"] > 0).mean()),
            }
        ]
    )
    b2_summary.to_csv(out_dir / "prompt_b_v2_summary.csv", index=False)

    b2_by_rank = (
        ab2.groupby("rank_band")
        .agg(
            n=("request_key", "size"),
            mean_a=("score_a", "mean"),
            mean_b_v1=("score_b_v1", "mean"),
            mean_b_v2=("score_b_v2", "mean"),
            mean_diff_b2_minus_b1=("diff_b2_minus_b1", "mean"),
            drop_share_vs_b1=("diff_b2_minus_b1", lambda s: (s < 0).mean()),
        )
        .reset_index()
    )
    b2_by_rank.to_csv(out_dir / "prompt_b_v2_by_rank.csv", index=False)

    b2_by_horizon = (
        ab2.groupby("horizon")
        .agg(
            n=("request_key", "size"),
            mean_a=("score_a", "mean"),
            mean_b_v1=("score_b_v1", "mean"),
            mean_b_v2=("score_b_v2", "mean"),
            mean_diff_b2_minus_b1=("diff_b2_minus_b1", "mean"),
            drop_share_vs_b1=("diff_b2_minus_b1", lambda s: (s < 0).mean()),
        )
        .reset_index()
    )
    b2_by_horizon.to_csv(out_dir / "prompt_b_v2_by_horizon.csv", index=False)

    # E veto summaries
    e_merged = e_df.merge(candidate_meta, left_on="request_key", right_on="pilot_row_id", how="left")
    e_merged = e_merged.merge(
        ab2[["request_key", "score_a", "score_b_v1", "score_b_v2"]],
        on="request_key",
        how="left",
    )
    e_merged.to_csv(out_dir / "prompt_e_veto_merged.csv", index=False)

    e_summary = (
        e_merged.groupby("screen_decision")
        .agg(
            n=("request_key", "size"),
            mean_score_a=("score_a", "mean"),
            mean_score_b_v1=("score_b_v1", "mean"),
            mean_score_b_v2=("score_b_v2", "mean"),
            mean_confidence=("confidence", "mean"),
        )
        .reset_index()
    )
    e_summary.to_csv(out_dir / "prompt_e_veto_summary.csv", index=False)

    e_by_rank = (
        e_merged.groupby(["rank_band", "screen_decision"])
        .agg(n=("request_key", "size"))
        .reset_index()
    )
    e_by_rank.to_csv(out_dir / "prompt_e_veto_by_rank.csv", index=False)

    # F vs C
    fc = old_c.merge(
        f_df[
            [
                "pair_id",
                "preferred_candidate_originalized",
                "preferred_candidate_swapped",
                "confidence_swapped",
                "reason_swapped",
            ]
        ],
        on="pair_id",
        how="inner",
    ).merge(pair_meta[["pair_id", "horizon", "field_slug", "pair_type"]], on="pair_id", how="left")
    fc["agreement_originalized"] = fc["preferred_candidate"] == fc["preferred_candidate_originalized"]
    fc["tie_in_swapped"] = fc["preferred_candidate_originalized"].eq("tie")
    fc.to_csv(out_dir / "prompt_f_vs_prompt_c.csv", index=False)

    fc_summary = pd.DataFrame(
        [
            {
                "n_pairs": int(len(fc)),
                "agreement_originalized": float(fc["agreement_originalized"].mean()),
                "tie_share_in_f": float(fc["tie_in_swapped"].mean()),
                "mean_confidence_c": float(fc["confidence"].mean()),
                "mean_confidence_f": float(fc["confidence_swapped"].mean()),
            }
        ]
    )
    fc_summary.to_csv(out_dir / "prompt_f_vs_prompt_c_summary.csv", index=False)

    fc_by_field = (
        fc.groupby(["horizon", "field_slug"])
        .agg(
            n=("pair_id", "size"),
            agreement_originalized=("agreement_originalized", "mean"),
            tie_share_in_f=("tie_in_swapped", "mean"),
        )
        .reset_index()
    )
    fc_by_field.to_csv(out_dir / "prompt_f_vs_prompt_c_by_field.csv", index=False)

    # Examples
    b2_big_drops = ab2.sort_values(["diff_b2_minus_b1", "surface_rank"], ascending=[True, True]).head(20)
    b2_big_drops.to_csv(out_dir / "examples_b2_big_drops.csv", index=False)

    veto_fail_but_old_b_high = e_merged[(e_merged["screen_decision"] == "fail") & (e_merged["score_b_v1"] >= 4)].copy()
    veto_fail_but_old_b_high = veto_fail_but_old_b_high.sort_values(["surface_rank"]).head(20)
    veto_fail_but_old_b_high.to_csv(out_dir / "examples_veto_fail_old_b_high.csv", index=False)

    swapped_disagreements = fc[(~fc["agreement_originalized"]) | (fc["tie_in_swapped"])].copy()
    swapped_disagreements = swapped_disagreements.sort_values(["horizon", "field_slug"]).head(20)
    swapped_disagreements.to_csv(out_dir / "examples_swapped_disagreements.csv", index=False)

    parse_summary = (
        parsed_df.groupby(["source_name", "parse_mode"]).size().reset_index(name="n")
    )
    parse_summary.to_csv(out_dir / "parse_summary.csv", index=False)

    # Summary note
    lines: list[str] = []
    lines.append("# LLM Screening V2 Analysis")
    lines.append("")
    lines.append("## Parse Quality")
    for row in parse_summary.itertuples(index=False):
        lines.append(f"- `{row.source_name}` / `{row.parse_mode}`: `{row.n}`")
    lines.append("")
    b2 = b2_summary.iloc[0]
    lines.append("## Prompt B v2")
    lines.append(
        f"- mean score moved from old B `{b2['mean_score_b_v1']:.3f}` to new B v2 `{b2['mean_score_b_v2']:.3f}`; mean shift `{b2['mean_diff_b2_minus_b1']:.3f}`."
    )
    lines.append(
        f"- share of rows that dropped vs old B: `{b2['drop_share_vs_b1']:.3f}`; rose: `{b2['rise_share_vs_b1']:.3f}`."
    )
    lines.append("")
    lines.append("## Prompt E veto")
    for row in e_summary.itertuples(index=False):
        lines.append(
            f"- `{row.screen_decision}`: `n={int(row.n)}`, mean A `{row.mean_score_a:.3f}`, mean old B `{row.mean_score_b_v1:.3f}`, mean B v2 `{row.mean_score_b_v2:.3f}`."
        )
    lines.append("")
    fcs = fc_summary.iloc[0]
    lines.append("## Prompt F swapped pairwise")
    lines.append(
        f"- agreement with originalized Prompt C choices: `{fcs['agreement_originalized']:.3f}`; tie share in F: `{fcs['tie_share_in_f']:.3f}`."
    )
    lines.append("")
    lines.append("## Example highlights")
    for row in b2_big_drops.head(3).itertuples(index=False):
        lines.append(
            f"- Bv2 corrected downward: `{row.u_label} -> {row.focal_mediator_label} -> {row.v_label}` | old B `{row.score_b_v1}`, new B `{row.score_b_v2}`."
        )
    for row in veto_fail_but_old_b_high.head(3).itertuples(index=False):
        lines.append(
            f"- Veto fail despite old B high: `{row.u_label} -> {row.focal_mediator_label} -> {row.v_label}` | old B `{row.score_b_v1}`, new B `{row.score_b_v2}`."
        )
    for row in swapped_disagreements.head(3).itertuples(index=False):
        lines.append(
            f"- Swapped pairwise disagreement: [{row.field_slug}] pair `{row.pair_id}` | C `{row.preferred_candidate}`, F-swapped `{row.preferred_candidate_originalized}`."
        )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "run_dir": str(args.run_dir),
        "old_analysis_dir": str(args.old_analysis_dir),
        "candidate_pilot": str(args.candidate_pilot),
        "pairwise_pilot": str(args.pairwise_pilot),
        "n_parsed_rows": int(len(parsed_df)),
        "n_failures": int(len(failures_df)),
        "n_b_rows": int(len(b_df)),
        "n_e_rows": int(len(e_df)),
        "n_f_rows": int(len(f_df)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
