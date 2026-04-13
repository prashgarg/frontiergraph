from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from prepare_llm_screening_batches import (
    FLAG_ENUM,
    PROMPT_E,
    _build_pairwise_sample,
    _build_response_request,
    _pairwise_schema,
    _record_aware_schema,
    _sha1_text,
    _veto_schema,
    _write_json,
    _write_jsonl,
    _write_markdown,
)


CONSTRUCTION_CONTEXT = """Context on how these records were created:
- Each candidate comes from a literature graph built from prior economics papers.
- Nodes are extracted topical entities or concepts, not guaranteed causal variables.
- A candidate object is a compressed local neighborhood: source -> focal mediator -> target.
- path_support_raw measures local neighborhood support in prior papers. It is support, not truth.
- endpoint_broadness_pct: higher means broader and more generic endpoints.
- endpoint_resolution_score: higher means the source-target pair is sharper and better resolved.
- focal_mediator_specificity_score: higher means the focal mediator is more specific and less generic.
- compression_confidence: higher means the local neighborhood compresses cleanly into one interpretable question object.
- candidate_family and candidate_subfamily describe where the candidate sits in the closure/progression pipeline.
Use these diagnostics as screening evidence only. Do not treat them as proof that the candidate is correct, important, or publishable."""


SCORE_ANCHORS = """Score anchors for overall_screening_value:
- 5: very sharp question object; specific endpoints; plausible focal mechanism; little obvious genericity
- 4: strong but with one moderate weakness
- 3: mixed or usable only with noticeable revision
- 2: weak object; broad, generic, or poorly compressed
- 1: not a usable research-question object from the supplied record"""


CONFIDENCE_ANCHORS = """Confidence anchors:
- 5: the supplied record clearly supports the judgment
- 3: the judgment is plausible but several fields point in different directions
- 1: the record is too ambiguous for a reliable judgment"""


PAIRWISE_CONFIDENCE_ANCHORS = """Confidence anchors:
- 5: one candidate is clearly better on several dimensions
- 3: preference is modest or mixed
- 1: near tie or highly ambiguous"""


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


PROMPT_H = f"""You are comparing two candidate research-question objects from the same broad field shelf and forecast horizon.

{CONSTRUCTION_CONTEXT}

Judge only their local screening quality for within-field browsing.
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


PROMPT_J = """You are screening candidate research-question objects for an intentionally high downstream bar.

This is an experimental prompt, not the core screening prompt.
It asks whether the supplied candidate looks more like:
- top_journal_bar
- solid_field_journal_bar
- not_journal_ready

This construct mixes question sharpness with a stronger taste/publication standard.
Use only the supplied fields. Do not use outside knowledge or prestige.

Return only JSON matching the schema."""


def _record_aware_schema_for_variant(variant_name: str) -> dict[str, Any]:
    schema = _record_aware_schema()
    schema["properties"]["variant"]["enum"] = [variant_name]
    return schema


def _pairwise_schema_for_variant(variant_name: str) -> dict[str, Any]:
    schema = _pairwise_schema(variant_name)
    schema["properties"]["variant"]["enum"] = [variant_name]
    return schema


def _journal_bar_schema() -> dict[str, Any]:
    evidence_enum = [
        "candidate_family",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "source_label",
        "focal_mediator_label",
        "target_label",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "compression_confidence",
        "compression_failure_reason",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidate_id": {"type": "string"},
            "variant": {"type": "string", "enum": ["journal_bar_experimental"]},
            "journal_bar": {
                "type": "string",
                "enum": ["top_journal_bar", "solid_field_journal_bar", "not_journal_ready"],
            },
            "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
            "flags": {
                "type": "array",
                "items": {"type": "string", "enum": FLAG_ENUM},
            },
            "evidence_fields": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_enum},
            },
            "reason": {"type": "string", "maxLength": 180},
        },
        "required": [
            "candidate_id",
            "variant",
            "journal_bar",
            "confidence",
            "flags",
            "evidence_fields",
            "reason",
        ],
    }


def _candidate_rows_from_pair_df(pair_df: pd.DataFrame) -> pd.DataFrame:
    keep = [
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
    rows: list[pd.DataFrame] = []
    for prefix in ["a", "b"]:
        sub = pair_df[[f"{prefix}_{col}" for col in keep] + ["field_slug", "horizon"]].copy()
        sub.columns = keep + ["field_slug", "horizon"]
        rows.append(sub)
    out = (
        pd.concat(rows, ignore_index=True)
        .drop_duplicates(subset=["horizon", "field_slug", "candidate_id"])
        .copy()
    )
    out = out.sort_values(["horizon", "field_slug", "surface_rank", "candidate_id"]).reset_index(drop=True)
    out["candidate_row_id"] = [f"wf_cand_{i:04d}" for i in range(1, len(out) + 1)]
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
        "compression_failure_reason": None
        if pd.isna(row["compression_failure_reason"])
        else str(row["compression_failure_reason"]),
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
            "compression_failure_reason": None
            if pd.isna(row["a_compression_failure_reason"])
            else str(row["a_compression_failure_reason"]),
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
            "compression_failure_reason": None
            if pd.isna(row["b_compression_failure_reason"])
            else str(row["b_compression_failure_reason"]),
        },
        "variant": variant_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare within-field LLM screening experiment pack.")
    parser.add_argument(
        "--within-field",
        type=Path,
        default=Path("outputs/paper/98_objective_specific_frontier_packages_endpoint_first/within_field_top100_pool2000/package.csv"),
    )
    parser.add_argument(
        "--current-frontier",
        type=Path,
        default=Path("outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper/105_llm_screening_within_field_v3_prompt_pack"),
    )
    parser.add_argument("--model", type=str, default="gpt-5.4-mini")
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    pair_df = _build_pairwise_sample(args.within_field, args.current_frontier)
    candidate_df = _candidate_rows_from_pair_df(pair_df)

    candidate_df.to_csv(out_dir / "within_field_candidate_rows.csv", index=False)
    pair_df.to_csv(out_dir / "within_field_pairwise_rows.csv", index=False)

    schema_g = _record_aware_schema_for_variant("construction_aware_record_aware")
    schema_h = _pairwise_schema_for_variant("construction_aware_pairwise_within_field")
    schema_e = _veto_schema()
    schema_j = _journal_bar_schema()

    _write_json(out_dir / "schema_g_construction_aware_scalar.json", schema_g)
    _write_json(out_dir / "schema_h_construction_aware_pairwise.json", schema_h)
    _write_json(out_dir / "schema_e_veto_screen.json", schema_e)
    _write_json(out_dir / "schema_j_journal_bar_experimental.json", schema_j)

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
        "Single-candidate screening using labels plus graph-local diagnostics, with explicit explanation of how the records were constructed and explicit score anchors.",
        hidden_common,
        PROMPT_G,
        "schema_g_construction_aware_scalar.json",
    )
    _write_markdown(
        out_dir / "prompt_h_construction_aware_pairwise.md",
        "Prompt H: Construction-Aware Pairwise Within-Field",
        "Within-field pairwise screening using graph-construction context, explicit tie guidance, and confidence anchors.",
        hidden_common,
        PROMPT_H,
        "schema_h_construction_aware_pairwise.json",
    )
    _write_markdown(
        out_dir / "prompt_e_veto_screen.md",
        "Prompt E: Veto Screen",
        "Coarse pass/review/fail screen on the same within-field candidate universe. Used only as a weak veto.",
        hidden_common,
        PROMPT_E,
        "schema_e_veto_screen.json",
    )
    _write_markdown(
        out_dir / "prompt_j_journal_bar_experimental.md",
        "Prompt J: Journal-Bar Experimental",
        "Experimental downstream prompt spec for a stronger publication-bar triage. Not used in the main screening runs.",
        hidden_common,
        PROMPT_J,
        "schema_j_journal_bar_experimental.json",
    )

    batch_g: list[dict[str, Any]] = []
    batch_e: list[dict[str, Any]] = []
    for _, row in candidate_df.iterrows():
        payload = _candidate_payload(row)
        custom_core = str(row["candidate_row_id"])
        batch_g.append(
            _build_response_request(
                custom_id=f"prompt-g-{custom_core}",
                model=args.model,
                prompt=PROMPT_G,
                schema_name="construction_aware_scalar_v1",
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
                schema_name="veto_screen_within_field_v1",
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
                schema_name="construction_aware_pairwise_within_field_v1",
                schema=schema_h,
                user_payload=_pairwise_payload(row, variant_name="construction_aware_pairwise_within_field"),
                max_output_tokens=240,
            )
        )

    _write_jsonl(out_dir / "prompt_g_batch.jsonl", batch_g)
    _write_jsonl(out_dir / "prompt_e_batch.jsonl", batch_e)
    _write_jsonl(out_dir / "prompt_h_batch.jsonl", batch_h)

    manifest = {
        "model": args.model,
        "source_files": {
            "within_field_package": str(args.within_field),
            "current_frontier": str(args.current_frontier),
        },
        "counts": {
            "candidate_rows": int(len(candidate_df)),
            "pairwise_rows": int(len(pair_df)),
            "prompt_g_requests": int(len(batch_g)),
            "prompt_e_requests": int(len(batch_e)),
            "prompt_h_requests": int(len(batch_h)),
        },
        "schema_hashes": {
            "prompt_g": _sha1_text(json.dumps(schema_g, sort_keys=True)),
            "prompt_e": _sha1_text(json.dumps(schema_e, sort_keys=True)),
            "prompt_h": _sha1_text(json.dumps(schema_h, sort_keys=True)),
            "prompt_j": _sha1_text(json.dumps(schema_j, sort_keys=True)),
        },
        "docs_basis": {
            "structured_outputs": "https://developers.openai.com/api/docs/guides/structured-outputs",
            "prompt_guidance": "https://developers.openai.com/api/docs/guides/prompt-guidance#keep-outputs-compact-and-structured",
            "gpt5_new_params": "https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools",
        },
    }
    _write_json(out_dir / "manifest.json", manifest)


if __name__ == "__main__":
    main()
