from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from build_objective_specific_frontier_packages import _field_memberships
from prepare_llm_screening_batches import (
    PROMPT_E,
    _build_response_request,
    _pairwise_schema,
    _record_aware_schema,
    _sha1_text,
    _veto_schema,
    _write_json,
    _write_jsonl,
    _write_markdown,
)
from prepare_llm_screening_within_field_v3 import (
    CONSTRUCTION_CONTEXT,
    CONFIDENCE_ANCHORS,
    PAIRWISE_CONFIDENCE_ANCHORS,
    SCORE_ANCHORS,
)


PROMPT_G = f"""You are scoring candidate research-question objects derived from prior economics papers.

{CONSTRUCTION_CONTEXT}

Judge only the local screening quality of the candidate object in the provided JSON record.
Use only the supplied fields. Do not use outside knowledge, web search, author prestige, topic prestige, expected citations, or beliefs about which topics matter.

You are not judging whether the topic is important, true, or publishable.
You are judging whether the candidate is a sharp, interpretable, non-generic research-question object for screening purposes.

Use label coherence and question-object clarity as primary. Use the numeric diagnostics as local evidence, but do not let numeric support rescue a semantically weak object.
If labels and diagnostics conflict, prefer the more skeptical interpretation unless the diagnostics clearly support a coherent, non-generic object.

Higher scores should go to candidates with:
- specific endpoints
- a plausible focal mechanism
- a coherent question object
- wording that reads like a research question rather than a concept bucket

Lower scores should go to candidates with:
- broad or underspecified endpoints
- generic mediators
- method-as-mechanism wording
- placeholder-like labels
- overly canonical or obvious pairings
- semantically odd source-mediator-target combinations, even when local support is nonzero

{SCORE_ANCHORS}

{CONFIDENCE_ANCHORS}

If the supplied record does not support a confident judgment, use lower confidence and flag insufficient_information.

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


PROMPT_H = f"""You are comparing two candidate research-question objects from the same broad comparison bucket and forecast horizon.

{CONSTRUCTION_CONTEXT}

Judge only their local screening quality for global-scan browsing.
Use only the supplied fields. Do not use outside knowledge, web search, author prestige, topic prestige, expected citations, or beliefs about which topics matter.

You are not judging whether the topic is important, true, or publishable.
You are judging which candidate is the sharper, more interpretable, less generic research-question object for screening purposes.

Prefer the candidate with:
- more specific endpoints
- a clearer focal mechanism
- a more coherent question object
- less canonical or textbook-like wording

Return tie whenever the difference is small, ambiguous, or driven mainly by one weak signal.
Do not force a choice.

{PAIRWISE_CONFIDENCE_ANCHORS}

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


def _record_aware_schema_for_variant(variant_name: str) -> dict[str, Any]:
    schema = _record_aware_schema()
    schema["properties"]["variant"]["enum"] = [variant_name]
    return schema


def _pairwise_schema_for_variant(variant_name: str) -> dict[str, Any]:
    schema = _pairwise_schema(variant_name)
    schema["properties"]["variant"]["enum"] = [variant_name]
    return schema


def _assign_primary_bucket(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        memberships = _field_memberships(pd.Series(row._asdict()))
        primary = memberships[0]
        row_dict = dict(row._asdict())
        row_dict["field_slug"] = primary["field_slug"]
        row_dict["field_assignment_source"] = primary["field_assignment_source"]
        row_dict["field_endpoint_match"] = primary["field_endpoint_match"]
        row_dict["field_mediator_match"] = primary["field_mediator_match"]
        rows.append(row_dict)
    return pd.DataFrame(rows)


def _pair_record(a: pd.Series, b: pd.Series) -> dict[str, Any]:
    keep_cols = [
        "candidate_id",
        "surface_rank",
        "u_label",
        "focal_mediator_label",
        "v_label",
        "candidate_family",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "local_topology_class",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "path_support_raw",
        "motif_count",
        "mediator_count",
        "compression_confidence",
        "compression_failure_reason",
    ]
    out: dict[str, Any] = {}
    for prefix, source in [("a", a), ("b", b)]:
        for col in keep_cols:
            out[f"{prefix}_{col}"] = source.get(col)
    return out


def _build_pairwise_sample(df: pd.DataFrame, target_pairs: int = 2000) -> pd.DataFrame:
    work = df.sort_values(["horizon", "field_slug", "surface_rank"]).reset_index(drop=True)
    pair_rows: list[dict[str, Any]] = []
    extra_candidates: list[dict[str, Any]] = []

    for (horizon, field_slug), sub in work.groupby(["horizon", "field_slug"], sort=True):
        sub = sub.sort_values("surface_rank").reset_index(drop=True)
        for i in range(len(sub) - 1):
            a = sub.iloc[i]
            b = sub.iloc[i + 1]
            pair_rows.append(
                {
                    "pair_type": "adjacent",
                    "horizon": int(horizon),
                    "field_slug": str(field_slug),
                    "a_idx": int(i),
                    "b_idx": int(i + 1),
                    **_pair_record(a, b),
                }
            )
        for gap in [3, 5, 8]:
            for i in range(max(0, len(sub) - gap)):
                a = sub.iloc[i]
                b = sub.iloc[i + gap]
                extra_candidates.append(
                    {
                        "pair_type": f"gap_{gap}",
                        "horizon": int(horizon),
                        "field_slug": str(field_slug),
                        "a_idx": int(i),
                        "b_idx": int(i + gap),
                        **_pair_record(a, b),
                    }
                )

    need_extra = target_pairs - len(pair_rows)
    if need_extra > 0:
        buckets: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for row in extra_candidates:
            key = (int(row["horizon"]), str(row["field_slug"]))
            buckets.setdefault(key, []).append(row)
        keys = sorted(buckets)
        added: list[dict[str, Any]] = []
        positions = {key: 0 for key in keys}
        while len(added) < need_extra:
            progressed = False
            for key in keys:
                idx = positions[key]
                bucket = buckets[key]
                if idx < len(bucket):
                    added.append(bucket[idx])
                    positions[key] += 1
                    progressed = True
                    if len(added) >= need_extra:
                        break
            if not progressed:
                break
        pair_rows.extend(added)

    out = pd.DataFrame(pair_rows).head(target_pairs).copy()
    out["pair_id"] = [f"pair_{i:04d}" for i in range(1, len(out) + 1)]
    return out


def _candidate_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "candidate_id": str(row["candidate_id"]),
        "field_slug": str(row["field_slug"]),
        "horizon": int(row["horizon"]),
        "source_label": str(row["u_label"]),
        "focal_mediator_label": str(row["focal_mediator_label"]),
        "target_label": str(row["v_label"]),
        "candidate_family": str(row["candidate_family"]),
        "candidate_subfamily": str(row["candidate_subfamily"]),
        "candidate_scope_bucket": str(row["candidate_scope_bucket"]),
        "local_topology_class": str(row["local_topology_class"]),
        "endpoint_broadness_pct": float(row["endpoint_broadness_pct"]),
        "endpoint_resolution_score": float(row["endpoint_resolution_score"]),
        "focal_mediator_specificity_score": float(row["focal_mediator_specificity_score"]),
        "path_support_raw": float(row["path_support_raw"]),
        "motif_count": int(row["motif_count"]),
        "mediator_count": int(row["mediator_count"]),
        "compression_confidence": float(row["compression_confidence"]),
        "compression_failure_reason": None if pd.isna(row["compression_failure_reason"]) else str(row["compression_failure_reason"]),
        "comparison_bucket": str(row["field_slug"]),
    }


def _pairwise_payload(row: pd.Series, *, variant_name: str) -> dict[str, Any]:
    return {
        "pair_id": str(row["pair_id"]),
        "field_slug": str(row["field_slug"]),
        "horizon": int(row["horizon"]),
        "candidate_a": {
            "candidate_id": str(row["a_candidate_id"]),
            "source_label": str(row["a_u_label"]),
            "focal_mediator_label": str(row["a_focal_mediator_label"]),
            "target_label": str(row["a_v_label"]),
            "candidate_family": str(row["a_candidate_family"]),
            "candidate_subfamily": str(row["a_candidate_subfamily"]),
            "candidate_scope_bucket": str(row["a_candidate_scope_bucket"]),
            "local_topology_class": str(row["a_local_topology_class"]),
            "endpoint_broadness_pct": float(row["a_endpoint_broadness_pct"]),
            "endpoint_resolution_score": float(row["a_endpoint_resolution_score"]),
            "focal_mediator_specificity_score": float(row["a_focal_mediator_specificity_score"]),
            "path_support_raw": float(row["a_path_support_raw"]),
            "motif_count": int(row["a_motif_count"]),
            "mediator_count": int(row["a_mediator_count"]),
            "compression_confidence": float(row["a_compression_confidence"]),
            "compression_failure_reason": None if pd.isna(row["a_compression_failure_reason"]) else str(row["a_compression_failure_reason"]),
        },
        "candidate_b": {
            "candidate_id": str(row["b_candidate_id"]),
            "source_label": str(row["b_u_label"]),
            "focal_mediator_label": str(row["b_focal_mediator_label"]),
            "target_label": str(row["b_v_label"]),
            "candidate_family": str(row["b_candidate_family"]),
            "candidate_subfamily": str(row["b_candidate_subfamily"]),
            "candidate_scope_bucket": str(row["b_candidate_scope_bucket"]),
            "local_topology_class": str(row["b_local_topology_class"]),
            "endpoint_broadness_pct": float(row["b_endpoint_broadness_pct"]),
            "endpoint_resolution_score": float(row["b_endpoint_resolution_score"]),
            "focal_mediator_specificity_score": float(row["b_focal_mediator_specificity_score"]),
            "path_support_raw": float(row["b_path_support_raw"]),
            "motif_count": int(row["b_motif_count"]),
            "mediator_count": int(row["b_mediator_count"]),
            "compression_confidence": float(row["b_compression_confidence"]),
            "compression_failure_reason": None if pd.isna(row["b_compression_failure_reason"]) else str(row["b_compression_failure_reason"]),
        },
        "variant": variant_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare global top-250 LLM screening experiment pack.")
    parser.add_argument(
        "--global-scan",
        type=Path,
        default=Path("outputs/paper/95_objective_specific_frontier_packages/global_scan_top250_pool2000/package.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper/112_llm_screening_global_top250_prompt_pack"),
    )
    parser.add_argument(
        "--current-frontier",
        type=Path,
        default=Path("outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv"),
    )
    parser.add_argument("--model", type=str, default="gpt-5.4-mini")
    parser.add_argument("--target-pairs", type=int, default=2000)
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    base = pd.read_csv(args.global_scan, low_memory=False)
    current = pd.read_csv(args.current_frontier, low_memory=False)
    enrich_cols = [
        "horizon",
        "u",
        "v",
        "path_support_raw",
        "motif_count",
        "mediator_count",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "compression_confidence",
        "compression_failure_reason",
    ]
    current_small = current[enrich_cols].drop_duplicates(subset=["horizon", "u", "v"]).copy()
    base = base.merge(current_small, on=["horizon", "u", "v"], how="left", suffixes=("", "_current"))
    fill_map = {
        "path_support_raw": "path_support_raw_current",
        "motif_count": "motif_count_current",
        "mediator_count": "mediator_count_current",
        "endpoint_broadness_pct": "endpoint_broadness_pct_current",
        "endpoint_resolution_score": "endpoint_resolution_score_current",
        "focal_mediator_specificity_score": "focal_mediator_specificity_score_current",
        "compression_confidence": "compression_confidence_current",
        "compression_failure_reason": "compression_failure_reason_current",
    }
    for base_col, enrich_col in fill_map.items():
        if enrich_col not in base.columns:
            continue
        if base_col in base.columns:
            base[base_col] = base[base_col].combine_first(base[enrich_col])
        else:
            base[base_col] = base[enrich_col]
    base["candidate_id"] = (
        base["candidate_subfamily"].astype(str)
        + ":"
        + base["u"].astype(str)
        + "->"
        + base["v"].astype(str)
        + ":h"
        + base["horizon"].astype(str)
    )
    work = _assign_primary_bucket(base)
    work = work.sort_values(["horizon", "surface_rank", "u", "v"]).reset_index(drop=True)
    work["candidate_row_id"] = [f"glob_cand_{i:04d}" for i in range(1, len(work) + 1)]

    pair_df = _build_pairwise_sample(work, target_pairs=int(args.target_pairs))

    work.to_csv(out_dir / "global_top250_candidate_rows.csv", index=False)
    pair_df.to_csv(out_dir / "global_top250_pairwise_rows.csv", index=False)

    schema_g = _record_aware_schema_for_variant("construction_aware_record_aware")
    schema_h = _pairwise_schema_for_variant("construction_aware_pairwise_global_scan")
    schema_e = _veto_schema()

    _write_json(out_dir / "schema_g_construction_aware_scalar.json", schema_g)
    _write_json(out_dir / "schema_h_construction_aware_pairwise.json", schema_h)
    _write_json(out_dir / "schema_e_veto_screen.json", schema_e)

    hidden_common = [
        "transparent_rank",
        "reranker_rank",
        "frontier_rank",
        "surface_rank",
        "theme keys",
        "derived penalties",
    ]
    _write_markdown(
        out_dir / "prompt_g_construction_aware_scalar.md",
        "Prompt G: Construction-Aware Scalar",
        "Single-candidate screening on the global top-250 object using labels plus graph-local diagnostics.",
        hidden_common,
        PROMPT_G,
        "schema_g_construction_aware_scalar.json",
    )
    _write_markdown(
        out_dir / "prompt_h_construction_aware_pairwise.md",
        "Prompt H: Construction-Aware Pairwise Global Scan",
        "Local pairwise screening on the global top-250 object using broad comparison buckets and forecast horizon.",
        hidden_common,
        PROMPT_H,
        "schema_h_construction_aware_pairwise.json",
    )
    _write_markdown(
        out_dir / "prompt_e_veto_screen.md",
        "Prompt E: Veto Screen",
        "Coarse pass/review/fail screen on the same global top-250 candidate universe. Used only as a weak veto.",
        hidden_common,
        PROMPT_E,
        "schema_e_veto_screen.json",
    )

    batch_g: list[dict[str, Any]] = []
    batch_e: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        payload = _candidate_payload(row)
        custom_core = str(row["candidate_row_id"])
        batch_g.append(
            _build_response_request(
                custom_id=f"prompt-g-{custom_core}",
                model=args.model,
                prompt=PROMPT_G,
                schema_name="construction_aware_scalar_global_top250_v1",
                schema=schema_g,
                user_payload=payload,
                max_output_tokens=320,
            )
        )
        batch_e.append(
            _build_response_request(
                custom_id=f"prompt-e-{custom_core}",
                model=args.model,
                prompt=PROMPT_E,
                schema_name="veto_screen_global_top250_v1",
                schema=schema_e,
                user_payload=payload,
                max_output_tokens=180,
            )
        )

    batch_h: list[dict[str, Any]] = []
    for _, row in pair_df.iterrows():
        batch_h.append(
            _build_response_request(
                custom_id=f"prompt-h-{row['pair_id']}",
                model=args.model,
                prompt=PROMPT_H,
                schema_name="construction_aware_pairwise_global_top250_v1",
                schema=schema_h,
                user_payload=_pairwise_payload(row, variant_name="construction_aware_pairwise_global_scan"),
                max_output_tokens=240,
            )
        )

    _write_jsonl(out_dir / "prompt_g_batch.jsonl", batch_g)
    _write_jsonl(out_dir / "prompt_e_batch.jsonl", batch_e)
    _write_jsonl(out_dir / "prompt_h_batch.jsonl", batch_h)

    manifest = {
        "model": args.model,
        "source_files": {
            "global_scan_package": str(args.global_scan),
            "current_frontier": str(args.current_frontier),
        },
        "counts": {
            "candidate_rows": int(len(work)),
            "pairwise_rows": int(len(pair_df)),
            "prompt_g_requests": int(len(batch_g)),
            "prompt_e_requests": int(len(batch_e)),
            "prompt_h_requests": int(len(batch_h)),
        },
        "comparison_bucket_rule": "endpoint-first field overlay with mediator fallback; first matching bucket only",
        "schema_hashes": {
            "prompt_g": _sha1_text(json.dumps(schema_g, sort_keys=True)),
            "prompt_e": _sha1_text(json.dumps(schema_e, sort_keys=True)),
            "prompt_h": _sha1_text(json.dumps(schema_h, sort_keys=True)),
        },
    }
    _write_json(out_dir / "manifest.json", manifest)


if __name__ == "__main__":
    main()
