from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


SINGLE_SCORE_COLS = [
    "overall_screening_value",
    "endpoint_specificity",
    "mediator_specificity",
    "question_object_clarity",
    "mechanism_clarity",
    "canonicality_risk",
    "local_crowding_risk",
    "confidence",
]


PAIRWISE_PREF_COLS = [
    "preferred_candidate",
    "endpoint_specificity_preference",
    "mechanism_clarity_preference",
    "question_object_clarity_preference",
    "confidence",
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
        try:
            repaired_empty = f'{prefix},"reason":""}}'
            return json.loads(repaired_empty), "repaired_empty_reason"
        except json.JSONDecodeError:
            return None, None


def _parse_responses(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            text_payload = _extract_text_payload(raw["response"])
            if not text_payload:
                failures.append(
                    {
                        "custom_id": raw.get("custom_id"),
                        "source_name": raw.get("source_name"),
                        "error": "missing_output_text",
                    }
                )
                continue
            try:
                parsed = json.loads(text_payload)
                parse_mode = "direct"
            except json.JSONDecodeError as exc:
                repaired, parse_mode = _repair_truncated_json(text_payload)
                if repaired is not None:
                    parsed = repaired
                else:
                    failures.append(
                        {
                            "custom_id": raw.get("custom_id"),
                            "source_name": raw.get("source_name"),
                            "error": f"json_decode_error: {exc}",
                            "raw_text": text_payload[:1000],
                        }
                    )
                    continue
            rows.append(
                {
                    "custom_id": raw.get("custom_id"),
                    "request_key": _request_key_from_custom_id(raw.get("custom_id")),
                    "source_name": raw.get("source_name"),
                    "source_path": raw.get("source_path"),
                    "response_id": raw["response"].get("id"),
                    "model": raw["response"].get("model"),
                    "created_at": raw["response"].get("created_at"),
                    "parse_mode": parse_mode,
                    "parsed": parsed,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(failures)


def _expand_single(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name not in {"prompt_a_batch_2000", "prompt_b_batch_2000"}:
            continue
        parsed = dict(row.parsed)
        out = {
            "custom_id": row.custom_id,
            "request_key": row.request_key,
            "prompt_variant": parsed.get("variant"),
            "candidate_id": parsed.get("candidate_id"),
            "source_name": row.source_name,
            "response_id": row.response_id,
            "model": row.model,
            "parse_mode": row.parse_mode,
            "flags": parsed.get("flags", []),
            "evidence_fields": parsed.get("evidence_fields", []),
            "reason": parsed.get("reason"),
        }
        for col in SINGLE_SCORE_COLS:
            out[col] = parsed.get(col)
        rows.append(out)
    return pd.DataFrame(rows)


def _expand_pairwise(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "prompt_c_batch_2000":
            continue
        parsed = dict(row.parsed)
        out = {
            "custom_id": row.custom_id,
            "request_key": row.request_key,
            "prompt_variant": parsed.get("variant"),
            "pair_id": parsed.get("pair_id"),
            "preferred_candidate": parsed.get("preferred_candidate"),
            "endpoint_specificity_preference": parsed.get("endpoint_specificity_preference"),
            "mechanism_clarity_preference": parsed.get("mechanism_clarity_preference"),
            "question_object_clarity_preference": parsed.get("question_object_clarity_preference"),
            "confidence": parsed.get("confidence"),
            "flags_a": parsed.get("flags_a", []),
            "flags_b": parsed.get("flags_b", []),
            "evidence_fields": parsed.get("evidence_fields", []),
            "reason": parsed.get("reason"),
            "source_name": row.source_name,
            "response_id": row.response_id,
            "model": row.model,
        }
        rows.append(out)
    return pd.DataFrame(rows)


def _mean_flag_jaccard(a_flags: list[str], b_flags: list[str]) -> float:
    a = set(a_flags or [])
    b = set(b_flags or [])
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _triage_bucket(score: float) -> str:
    if pd.isna(score):
        return "missing"
    if score >= 4:
        return "high"
    if score <= 2:
        return "low"
    return "middle"


def _single_variant_summary(single_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant, sub in single_df.groupby("prompt_variant"):
        row = {
            "prompt_variant": variant,
            "n_rows": int(len(sub)),
            "mean_overall_screening_value": float(sub["overall_screening_value"].mean()),
            "mean_confidence": float(sub["confidence"].mean()),
            "high_share": float((sub["overall_screening_value"] >= 4).mean()),
            "low_share": float((sub["overall_screening_value"] <= 2).mean()),
        }
        for flag in [
            "broad_endpoint",
            "generic_mediator",
            "method_not_mechanism",
            "canonical_pairing",
            "placeholder_like",
            "unclear_question_object",
            "insufficient_information",
        ]:
            row[f"flag_share__{flag}"] = float(sub["flags"].apply(lambda xs, flag=flag: flag in (xs or [])).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _agreement_summary(single_df: pd.DataFrame) -> pd.DataFrame:
    a = single_df[single_df["prompt_variant"] == "semantic_blind"].copy()
    b = single_df[single_df["prompt_variant"] == "record_aware"].copy()
    merge_cols = ["request_key"]
    merged = a.merge(
        b,
        on=merge_cols,
        suffixes=("_a", "_b"),
        how="inner",
    )
    merged["score_diff_b_minus_a"] = merged["overall_screening_value_b"] - merged["overall_screening_value_a"]
    merged["exact_score_agreement"] = merged["overall_screening_value_a"] == merged["overall_screening_value_b"]
    merged["within_one_agreement"] = (merged["score_diff_b_minus_a"].abs() <= 1)
    merged["triage_a"] = merged["overall_screening_value_a"].apply(_triage_bucket)
    merged["triage_b"] = merged["overall_screening_value_b"].apply(_triage_bucket)
    merged["exact_triage_agreement"] = merged["triage_a"] == merged["triage_b"]
    merged["flag_jaccard"] = merged.apply(lambda row: _mean_flag_jaccard(row["flags_a"], row["flags_b"]), axis=1)
    merged["flag_count_a"] = merged["flags_a"].apply(lambda xs: len(xs or []))
    merged["flag_count_b"] = merged["flags_b"].apply(lambda xs: len(xs or []))
    summary = pd.DataFrame(
        [
            {
                "n_overlap": int(len(merged)),
                "mean_score_a": float(merged["overall_screening_value_a"].mean()),
                "mean_score_b": float(merged["overall_screening_value_b"].mean()),
                "mean_diff_b_minus_a": float(merged["score_diff_b_minus_a"].mean()),
                "exact_score_agreement": float(merged["exact_score_agreement"].mean()),
                "within_one_agreement": float(merged["within_one_agreement"].mean()),
                "exact_triage_agreement": float(merged["exact_triage_agreement"].mean()),
                "mean_flag_jaccard": float(merged["flag_jaccard"].mean()),
                "mean_flag_count_a": float(merged["flag_count_a"].mean()),
                "mean_flag_count_b": float(merged["flag_count_b"].mean()),
                "spearman_overall": float(
                    merged["overall_screening_value_a"].corr(
                        merged["overall_screening_value_b"], method="spearman"
                    )
                ),
            }
        ]
    )
    return summary, merged


def _pairwise_summary(pair_df: pd.DataFrame, pair_meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = pair_df.merge(pair_meta, on="pair_id", how="left")
    merged["prefers_higher_ranked_a"] = merged["preferred_candidate"].eq("A")
    merged["prefers_lower_ranked_b"] = merged["preferred_candidate"].eq("B")
    merged["tie_share"] = merged["preferred_candidate"].eq("tie")
    overall = pd.DataFrame(
        [
            {
                "n_pairs": int(len(merged)),
                "prefer_a_share": float((merged["preferred_candidate"] == "A").mean()),
                "prefer_b_share": float((merged["preferred_candidate"] == "B").mean()),
                "tie_share": float((merged["preferred_candidate"] == "tie").mean()),
                "mean_confidence": float(merged["confidence"].mean()),
            }
        ]
    )
    by_field = (
        merged.groupby(["horizon", "field_slug"], dropna=False)
        .agg(
            n_pairs=("pair_id", "size"),
            prefer_a_share=("preferred_candidate", lambda s: (s == "A").mean()),
            prefer_b_share=("preferred_candidate", lambda s: (s == "B").mean()),
            tie_share=("preferred_candidate", lambda s: (s == "tie").mean()),
            mean_confidence=("confidence", "mean"),
        )
        .reset_index()
    )
    return overall, by_field, merged


def _collect_examples(
    ab_merged: pd.DataFrame,
    candidate_meta: pd.DataFrame,
    pairwise_merged: pd.DataFrame,
    out_dir: Path,
) -> None:
    meta_cols = [
        "pilot_row_id",
        "candidate_id",
        "horizon",
        "rank_band",
        "surface_rank",
        "transparent_rank",
        "u_label",
        "focal_mediator_label",
        "v_label",
        "candidate_scope_bucket",
        "candidate_subfamily",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "compression_confidence",
        "compression_failure_reason",
    ]
    meta = candidate_meta[meta_cols].drop_duplicates("pilot_row_id")
    ab = ab_merged.merge(meta, left_on="request_key", right_on="pilot_row_id", how="left")

    weak = ab[
        (ab["overall_screening_value_a"] <= 2)
        & (ab["overall_screening_value_b"] <= 2)
    ].copy()
    weak["mean_score"] = (weak["overall_screening_value_a"] + weak["overall_screening_value_b"]) / 2
    weak = weak.sort_values(
        ["mean_score", "flag_jaccard", "compression_confidence", "surface_rank"],
        ascending=[True, False, True, True],
    ).head(12)

    strong = ab[
        (ab["overall_screening_value_a"] >= 4)
        & (ab["overall_screening_value_b"] >= 4)
    ].copy()
    strong["mean_score"] = (strong["overall_screening_value_a"] + strong["overall_screening_value_b"]) / 2
    strong = strong.sort_values(
        ["mean_score", "compression_confidence", "surface_rank"],
        ascending=[False, False, True],
    ).head(12)

    disagreement = ab.copy()
    disagreement["abs_diff"] = disagreement["score_diff_b_minus_a"].abs()
    disagreement = disagreement.sort_values(
        ["abs_diff", "surface_rank"],
        ascending=[False, True],
    ).head(12)

    weak.to_csv(out_dir / "examples_consistently_weak.csv", index=False)
    strong.to_csv(out_dir / "examples_consistently_strong.csv", index=False)
    disagreement.to_csv(out_dir / "examples_prompt_ab_disagreement.csv", index=False)

    pw = pairwise_merged.copy()
    reversals = pw[pw["preferred_candidate"] == "B"].copy()
    reversals = reversals.sort_values(["confidence", "horizon"], ascending=[False, True]).head(15)
    ties = pw[pw["preferred_candidate"] == "tie"].copy().sort_values(["confidence"], ascending=[False]).head(15)
    reversals.to_csv(out_dir / "examples_pairwise_reversals.csv", index=False)
    ties.to_csv(out_dir / "examples_pairwise_ties.csv", index=False)


def _render_note(
    out_dir: Path,
    single_summary: pd.DataFrame,
    agreement_summary: pd.DataFrame,
    pairwise_overall: pd.DataFrame,
    pairwise_by_field: pd.DataFrame,
    weak_examples: pd.DataFrame,
    strong_examples: pd.DataFrame,
    disagreement_examples: pd.DataFrame,
    reversal_examples: pd.DataFrame,
) -> None:
    ss = single_summary.set_index("prompt_variant")
    ag = agreement_summary.iloc[0]
    pw = pairwise_overall.iloc[0]
    lines: list[str] = []
    lines.append("# LLM Screening Analysis")
    lines.append("")
    parse_counts = single_summary.attrs.get("parse_counts", {})
    if parse_counts:
        direct = parse_counts.get("direct", 0)
        repaired = parse_counts.get("repaired", 0)
        lines.append("## Parse Quality")
        lines.append(f"- direct parses `{direct}`, repaired parses `{repaired}`.")
        lines.append("")
    lines.append("## Single-Candidate Prompts")
    for variant in ["semantic_blind", "record_aware"]:
        row = ss.loc[variant]
        lines.append(
            f"- `{variant}`: mean overall score `{row['mean_overall_screening_value']:.3f}`, "
            f"high-share `{row['high_share']:.3f}`, low-share `{row['low_share']:.3f}`, "
            f"mean confidence `{row['mean_confidence']:.3f}`."
        )
    lines.append("")
    lines.append("## Prompt A vs B Agreement")
    lines.append(
        f"- exact score agreement `{ag['exact_score_agreement']:.3f}`, within-one agreement `{ag['within_one_agreement']:.3f}`, "
        f"exact triage agreement `{ag['exact_triage_agreement']:.3f}`, Spearman `{ag['spearman_overall']:.3f}`."
    )
    lines.append(
        f"- mean score shift `B - A = {ag['mean_diff_b_minus_a']:.3f}`, mean flag Jaccard `{ag['mean_flag_jaccard']:.3f}`."
    )
    lines.append("")
    lines.append("## Prompt C Pairwise")
    lines.append(
        f"- prefer higher-ranked shelf item `A` share `{pw['prefer_a_share']:.3f}`, "
        f"prefer lower-ranked `B` share `{pw['prefer_b_share']:.3f}`, tie share `{pw['tie_share']:.3f}`, "
        f"mean confidence `{pw['mean_confidence']:.3f}`."
    )
    lines.append("")
    lines.append("## Pairwise By Field")
    for horizon in sorted(pairwise_by_field["horizon"].dropna().unique()):
        sub = pairwise_by_field[pairwise_by_field["horizon"] == horizon].sort_values("prefer_b_share", ascending=False)
        top = sub.head(3)
        parts = ", ".join(
            f"{row.field_slug}: prefer_B={row.prefer_b_share:.3f}, tie={row.tie_share:.3f}"
            for row in top.itertuples(index=False)
        )
        lines.append(f"- `h={int(horizon)}` highest reversal fields: {parts}.")
    lines.append("")
    lines.append("## Example Highlights")
    if not weak_examples.empty:
        lines.append("- Consistently weak:")
        for row in weak_examples.head(3).itertuples(index=False):
            lines.append(
                f"  - `{row.u_label} -> {row.focal_mediator_label} -> {row.v_label}` | A={row.overall_screening_value_a}, B={row.overall_screening_value_b}"
            )
    if not strong_examples.empty:
        lines.append("- Consistently strong:")
        for row in strong_examples.head(3).itertuples(index=False):
            lines.append(
                f"  - `{row.u_label} -> {row.focal_mediator_label} -> {row.v_label}` | A={row.overall_screening_value_a}, B={row.overall_screening_value_b}"
            )
    if not disagreement_examples.empty:
        lines.append("- Largest A/B disagreements:")
        for row in disagreement_examples.head(3).itertuples(index=False):
            lines.append(
                f"  - `{row.u_label} -> {row.focal_mediator_label} -> {row.v_label}` | A={row.overall_screening_value_a}, B={row.overall_screening_value_b}"
            )
    if not reversal_examples.empty:
        lines.append("- Pairwise reversals:")
        for row in reversal_examples.head(3).itertuples(index=False):
            lines.append(
                f"  - [{row.field_slug}] `{row.a_u_label} -> {row.a_focal_mediator_label} -> {row.a_v_label}` vs "
                f"`{row.b_u_label} -> {row.b_focal_mediator_label} -> {row.b_v_label}` | preferred `{row.preferred_candidate}`"
            )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze completed async LLM screening runs.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("outputs/paper/100_llm_screening_async_runs_99_endpoint_first"),
    )
    parser.add_argument(
        "--candidate-pilot",
        type=Path,
        default=Path("outputs/paper/99_llm_screening_prompt_pack_endpoint_first/candidate_pilot2000.csv"),
    )
    parser.add_argument(
        "--pairwise-pilot",
        type=Path,
        default=Path("outputs/paper/99_llm_screening_prompt_pack_endpoint_first/pairwise_pilot2000.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper/101_llm_screening_analysis_99_endpoint_first"),
    )
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed_df, failures_df = _parse_responses(args.run_dir / "responses.jsonl")
    parsed_df.to_parquet(out_dir / "parsed_responses.parquet", index=False)
    if not failures_df.empty:
        failures_df.to_csv(out_dir / "parse_failures.csv", index=False)

    single_df = _expand_single(parsed_df)
    pair_df = _expand_pairwise(parsed_df)
    single_df.to_csv(out_dir / "single_candidate_scores.csv", index=False)
    pair_df.to_csv(out_dir / "pairwise_scores.csv", index=False)

    single_summary = _single_variant_summary(single_df)
    parse_counts = {
        "direct": int((single_df["parse_mode"] == "direct").sum()),
        "repaired": int((single_df["parse_mode"] != "direct").sum()),
    }
    single_summary.attrs["parse_counts"] = parse_counts
    single_summary.to_csv(out_dir / "single_variant_summary.csv", index=False)

    agreement_summary, ab_merged = _agreement_summary(single_df)
    agreement_summary.to_csv(out_dir / "prompt_ab_agreement_summary.csv", index=False)
    ab_merged.to_csv(out_dir / "prompt_ab_merged_scores.csv", index=False)

    pair_meta = pd.read_csv(args.pairwise_pilot, low_memory=False)
    pairwise_overall, pairwise_by_field, pairwise_merged = _pairwise_summary(pair_df, pair_meta)
    pairwise_overall.to_csv(out_dir / "pairwise_overall_summary.csv", index=False)
    pairwise_by_field.to_csv(out_dir / "pairwise_by_field_summary.csv", index=False)
    pairwise_merged.to_csv(out_dir / "pairwise_merged_scores.csv", index=False)

    candidate_meta = pd.read_csv(args.candidate_pilot, low_memory=False)
    _collect_examples(ab_merged, candidate_meta, pairwise_merged, out_dir)

    weak_examples = pd.read_csv(out_dir / "examples_consistently_weak.csv")
    strong_examples = pd.read_csv(out_dir / "examples_consistently_strong.csv")
    disagreement_examples = pd.read_csv(out_dir / "examples_prompt_ab_disagreement.csv")
    reversal_examples = pd.read_csv(out_dir / "examples_pairwise_reversals.csv")
    _render_note(
        out_dir,
        single_summary,
        agreement_summary,
        pairwise_overall,
        pairwise_by_field,
        weak_examples,
        strong_examples,
        disagreement_examples,
        reversal_examples,
    )

    manifest = {
        "run_dir": str(args.run_dir),
        "candidate_pilot": str(args.candidate_pilot),
        "pairwise_pilot": str(args.pairwise_pilot),
        "n_parsed_rows": int(len(parsed_df)),
        "n_single_rows": int(len(single_df)),
        "n_pairwise_rows": int(len(pair_df)),
        "n_parse_failures": int(len(failures_df)),
        "n_repaired_rows": int((parsed_df["parse_mode"] != "direct").sum()),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
