from __future__ import annotations

import argparse
import csv
import hashlib
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


PROMPT_A = """You are scoring candidate research-question objects derived from prior economics papers.

Judge only the local screening quality of the candidate object in the provided JSON record.
Use only the supplied fields. Do not use outside knowledge, web search, author prestige, topic prestige, expected citations, or beliefs about which topics matter.

You are not judging whether the topic is important, true, or publishable.
You are judging whether the candidate is a sharp, interpretable, non-generic research-question object for screening purposes.

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

If the supplied record does not support a confident judgment, use lower confidence and flag insufficient_information.

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


PROMPT_B = """You are scoring candidate research-question objects derived from prior economics papers.

Judge only the local screening quality of the candidate object in the provided JSON record.
Use only the supplied fields. Do not use outside knowledge, web search, author prestige, topic prestige, expected citations, or beliefs about which topics matter.

You are not judging whether the topic is important, true, or publishable.
You are judging whether the candidate is a sharp, interpretable, non-generic research-question object for screening purposes.

The supplied record includes graph-local diagnostics such as endpoint broadness, endpoint resolution, mediator specificity, path support, motif count, mediator count, and compression confidence.
Use these as local evidence, but do not let numeric support rescue a semantically weak object.
Treat label coherence and question-object clarity as primary.
If labels and diagnostics conflict, prefer the more skeptical interpretation unless the diagnostics clearly show a sharp, coherent, non-generic object.

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

If the supplied record does not support a confident judgment, use lower confidence and flag insufficient_information.

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


PROMPT_C = """You are comparing two candidate research-question objects from the same broad field shelf and forecast horizon.

Judge only their local screening quality for within-field browsing.
Use only the supplied fields. Do not use outside knowledge, web search, author prestige, topic prestige, expected citations, or beliefs about which topics matter.

You are not judging whether the topic is important, true, or publishable.
You are judging which candidate is the sharper, more interpretable, less generic research-question object for screening purposes.

Prefer the candidate with:
- more specific endpoints
- a clearer focal mechanism
- a more coherent question object
- less canonical or textbook-like wording

Return tie whenever the difference is small, ambiguous, or driven by only one weak signal.
Do not force a choice.

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


PROMPT_D = """You are rewriting already-screened candidate research-question objects into cleaner economist-facing question phrasing.

Preserve the substantive object. Do not invent new concepts, new mechanisms, or stronger claims than the supplied record supports.

Your job is to improve phrasing, not to rescore the candidate.
Prefer short, concrete, paper-like wording.
Avoid hype, jargon inflation, and vague concept-bucket phrasing.

Return only JSON matching the schema."""


PROMPT_E = """You are screening candidate research-question objects derived from prior economics papers.

Judge only whether the supplied candidate should pass a first-pass paper-worthiness screen.
Use only the supplied fields. Do not use outside knowledge, web search, prestige, citations, or beliefs about topic importance.

This is a coarse screen, not a ranking task.
Use a skeptical standard.

Fail the candidate if one or more of these are true:
- the endpoints are broad or weakly resolved
- the mediator is generic, list-like, method-like, or semantically mismatched
- the object reads like a canonical textbook pairing rather than a sharp question
- the record is too unclear to support a confident question object

Pass the candidate only if it is locally interpretable as a specific question object with a plausible focal mechanism.

Return only JSON matching the schema.
Keep the reason evidence-based and under 25 words."""


PROMPT_F = """You are comparing two candidate research-question objects from the same broad field shelf and forecast horizon.

Judge only their local screening quality for within-field browsing.
Use only the supplied fields. Do not use outside knowledge, web search, prestige, citations, or beliefs about topic importance.

This prompt is intentionally order-sensitive only in presentation, not in evaluation.
Do not assume candidate A is better because it is shown first.
Return tie whenever the difference is small, ambiguous, or driven by only one weak signal.

Prefer the candidate with:
- more specific endpoints
- a clearer focal mechanism
- a more coherent question object
- less canonical or textbook-like wording

Return only JSON matching the schema.
Keep the reason evidence-based and under 30 words."""


def _semantic_blind_schema() -> dict[str, Any]:
    evidence_enum = [
        "candidate_family",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "local_topology_class",
        "source_label",
        "focal_mediator_label",
        "target_label",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidate_id": {"type": "string", "description": "Original candidate identifier."},
            "variant": {"type": "string", "enum": ["semantic_blind"]},
            "overall_screening_value": {"type": "integer", "minimum": 1, "maximum": 5},
            "endpoint_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "mediator_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "question_object_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "mechanism_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "canonicality_risk": {"type": "integer", "minimum": 1, "maximum": 5},
            "local_crowding_risk": {"type": "integer", "minimum": 1, "maximum": 5},
            "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
            "flags": {
                "type": "array",
                "items": {"type": "string", "enum": FLAG_ENUM},
            },
            "evidence_fields": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_enum},
            },
            "reason": {
                "type": "string",
                "description": "Concise evidence-based reason.",
                "maxLength": 220,
            },
        },
        "required": [
            "candidate_id",
            "variant",
            "overall_screening_value",
            "endpoint_specificity",
            "mediator_specificity",
            "question_object_clarity",
            "mechanism_clarity",
            "canonicality_risk",
            "local_crowding_risk",
            "confidence",
            "flags",
            "evidence_fields",
            "reason",
        ],
    }


def _record_aware_schema() -> dict[str, Any]:
    evidence_enum = [
        "candidate_family",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "local_topology_class",
        "source_label",
        "focal_mediator_label",
        "target_label",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "path_support_raw",
        "motif_count",
        "mediator_count",
        "compression_confidence",
        "compression_failure_reason",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidate_id": {"type": "string"},
            "variant": {"type": "string", "enum": ["record_aware"]},
            "overall_screening_value": {"type": "integer", "minimum": 1, "maximum": 5},
            "endpoint_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "mediator_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "question_object_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "mechanism_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "canonicality_risk": {"type": "integer", "minimum": 1, "maximum": 5},
            "local_crowding_risk": {"type": "integer", "minimum": 1, "maximum": 5},
            "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
            "flags": {
                "type": "array",
                "items": {"type": "string", "enum": FLAG_ENUM},
            },
            "evidence_fields": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_enum},
            },
            "reason": {"type": "string", "maxLength": 220},
        },
        "required": [
            "candidate_id",
            "variant",
            "overall_screening_value",
            "endpoint_specificity",
            "mediator_specificity",
            "question_object_clarity",
            "mechanism_clarity",
            "canonicality_risk",
            "local_crowding_risk",
            "confidence",
            "flags",
            "evidence_fields",
            "reason",
        ],
    }


def _pairwise_schema(variant_name: str) -> dict[str, Any]:
    evidence_enum = [
        "field_slug",
        "horizon",
        "a.source_label",
        "a.focal_mediator_label",
        "a.target_label",
        "a.endpoint_resolution_score",
        "a.focal_mediator_specificity_score",
        "a.compression_confidence",
        "b.source_label",
        "b.focal_mediator_label",
        "b.target_label",
        "b.endpoint_resolution_score",
        "b.focal_mediator_specificity_score",
        "b.compression_confidence",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "pair_id": {"type": "string"},
            "variant": {"type": "string", "enum": [variant_name]},
            "preferred_candidate": {"type": "string", "enum": ["A", "B", "tie"]},
            "endpoint_specificity_preference": {"type": "string", "enum": ["A", "B", "tie"]},
            "mechanism_clarity_preference": {"type": "string", "enum": ["A", "B", "tie"]},
            "question_object_clarity_preference": {"type": "string", "enum": ["A", "B", "tie"]},
            "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
            "flags_a": {
                "type": "array",
                "items": {"type": "string", "enum": FLAG_ENUM},
            },
            "flags_b": {
                "type": "array",
                "items": {"type": "string", "enum": FLAG_ENUM},
            },
            "evidence_fields": {
                "type": "array",
                "items": {"type": "string", "enum": evidence_enum},
            },
            "reason": {"type": "string", "maxLength": 220},
        },
        "required": [
            "pair_id",
            "variant",
            "preferred_candidate",
            "endpoint_specificity_preference",
            "mechanism_clarity_preference",
            "question_object_clarity_preference",
            "confidence",
            "flags_a",
            "flags_b",
            "evidence_fields",
            "reason",
        ],
    }


def _rewrite_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidate_id": {"type": "string"},
            "rewrite_style": {"type": "string", "enum": ["economist_facing_question"]},
            "rewritten_question": {"type": "string"},
            "warnings": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["broad_endpoint", "generic_mediator", "unclear_object", "leave_unrewritten"],
                },
            },
        },
        "required": ["candidate_id", "rewrite_style", "rewritten_question", "warnings"],
    }


def _veto_schema() -> dict[str, Any]:
    evidence_enum = [
        "candidate_family",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "local_topology_class",
        "source_label",
        "focal_mediator_label",
        "target_label",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "path_support_raw",
        "motif_count",
        "mediator_count",
        "compression_confidence",
        "compression_failure_reason",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidate_id": {"type": "string"},
            "variant": {"type": "string", "enum": ["veto_screen"]},
            "screen_decision": {"type": "string", "enum": ["pass", "review", "fail"]},
            "primary_failure_mode": {
                "type": "string",
                "enum": [
                    "none",
                    "broad_endpoint",
                    "generic_mediator",
                    "method_not_mechanism",
                    "canonical_pairing",
                    "placeholder_like",
                    "unclear_question_object",
                    "insufficient_information",
                ],
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
            "screen_decision",
            "primary_failure_mode",
            "confidence",
            "flags",
            "evidence_fields",
            "reason",
        ],
    }


def _even_positions(n_available: int, n_select: int) -> list[int]:
    if n_select <= 0:
        return []
    if n_select >= n_available:
        return list(range(n_available))
    if n_select == 1:
        return [n_available // 2]
    raw = [round(i * (n_available - 1) / (n_select - 1)) for i in range(n_select)]
    used: set[int] = set()
    out: list[int] = []
    for idx in raw:
        if idx not in used:
            used.add(idx)
            out.append(idx)
            continue
        probe = idx
        while probe < n_available and probe in used:
            probe += 1
        if probe >= n_available:
            probe = idx
            while probe >= 0 and probe in used:
                probe -= 1
        used.add(probe)
        out.append(probe)
    return sorted(out)


def _sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _build_candidate_sample(current_path: Path) -> pd.DataFrame:
    df = pd.read_csv(current_path, low_memory=False).copy()
    quotas = {
        5: {"top": 200, "mid": 200, "deep": 267},
        10: {"top": 200, "mid": 200, "deep": 267},
        15: {"top": 200, "mid": 200, "deep": 266},
    }
    bands = {
        "top": (1, 250),
        "mid": (251, 750),
        "deep": (751, 2000),
    }
    rows: list[pd.DataFrame] = []
    for horizon, band_map in quotas.items():
        hdf = df[df["horizon"].astype(int) == horizon].sort_values("surface_rank").copy()
        for band_name, quota in band_map.items():
            lo, hi = bands[band_name]
            sub = hdf[(hdf["surface_rank"].astype(int) >= lo) & (hdf["surface_rank"].astype(int) <= hi)].copy()
            positions = _even_positions(len(sub), quota)
            picked = sub.iloc[positions].copy()
            picked["rank_band"] = band_name
            rows.append(picked)
    out = pd.concat(rows, ignore_index=True)
    out = out.sort_values(["horizon", "surface_rank"]).reset_index(drop=True)
    out["pilot_row_id"] = [f"cand_{i:04d}" for i in range(1, len(out) + 1)]
    return out


def _build_pairwise_sample(within_field_path: Path, current_frontier_path: Path) -> pd.DataFrame:
    df = pd.read_csv(within_field_path, low_memory=False).copy()
    current_df = pd.read_csv(current_frontier_path, low_memory=False)
    enrich_cols = [
        "horizon",
        "u",
        "v",
        "candidate_id",
        "path_support_raw",
        "motif_count",
        "mediator_count",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "compression_confidence",
        "compression_failure_reason",
    ]
    current_small = (
        current_df[enrich_cols]
        .drop_duplicates(subset=["horizon", "u", "v"])
        .rename(
            columns={
                "candidate_id": "current_candidate_id",
                "path_support_raw": "current_path_support_raw",
                "motif_count": "current_motif_count",
                "mediator_count": "current_mediator_count",
                "endpoint_broadness_pct": "current_endpoint_broadness_pct",
                "endpoint_resolution_score": "current_endpoint_resolution_score",
                "focal_mediator_specificity_score": "current_focal_mediator_specificity_score",
                "compression_confidence": "current_compression_confidence",
                "compression_failure_reason": "current_compression_failure_reason",
            }
        )
    )
    df = df.merge(current_small, on=["horizon", "u", "v"], how="left")
    fill_map = {
        "candidate_id": "current_candidate_id",
        "path_support_raw": "current_path_support_raw",
        "motif_count": "current_motif_count",
        "mediator_count": "current_mediator_count",
        "endpoint_broadness_pct": "current_endpoint_broadness_pct",
        "endpoint_resolution_score": "current_endpoint_resolution_score",
        "focal_mediator_specificity_score": "current_focal_mediator_specificity_score",
        "compression_confidence": "current_compression_confidence",
        "compression_failure_reason": "current_compression_failure_reason",
    }
    for base_col, enrich_col in fill_map.items():
        if base_col not in df.columns:
            df[base_col] = df[enrich_col]
        else:
            df[base_col] = df[base_col].combine_first(df[enrich_col])
    df = df.sort_values(["horizon", "field_slug", "surface_rank"]).reset_index(drop=True)
    pair_rows: list[dict[str, Any]] = []
    extra_candidates: list[dict[str, Any]] = []

    for (horizon, field_slug), sub in df.groupby(["horizon", "field_slug"], sort=True):
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
        for i in range(max(0, len(sub) - 4)):
            a = sub.iloc[i]
            b = sub.iloc[i + 4]
            extra_candidates.append(
                {
                    "pair_type": "wider_gap",
                    "horizon": int(horizon),
                    "field_slug": str(field_slug),
                    "a_idx": int(i),
                    "b_idx": int(i + 4),
                    **_pair_record(a, b),
                }
            )

    need_extra = 2000 - len(pair_rows)
    if need_extra > 0:
        # Round-robin across shelves to keep the extra set balanced.
        buckets: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for row in extra_candidates:
            key = (int(row["horizon"]), str(row["field_slug"]))
            buckets.setdefault(key, []).append(row)
        keys = sorted(buckets)
        added: list[dict[str, Any]] = []
        bucket_pos = {key: 0 for key in keys}
        while len(added) < need_extra:
            progressed = False
            for key in keys:
                idx = bucket_pos[key]
                bucket = buckets[key]
                if idx < len(bucket):
                    added.append(bucket[idx])
                    bucket_pos[key] += 1
                    progressed = True
                    if len(added) >= need_extra:
                        break
            if not progressed:
                break
        pair_rows.extend(added)

    out = pd.DataFrame(pair_rows).head(2000).copy()
    out["pair_id"] = [f"pair_{i:04d}" for i in range(1, len(out) + 1)]
    return out


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
    row: dict[str, Any] = {}
    for prefix, source in [("a", a), ("b", b)]:
        for col in keep_cols:
            row[f"{prefix}_{col}"] = source.get(col)
    return row


def _candidate_payload(row: pd.Series, variant: str) -> dict[str, Any]:
    base = {
        "candidate_id": str(row["candidate_id"]),
        "horizon": int(row["horizon"]),
        "source_label": str(row["u_label"]),
        "focal_mediator_label": str(row["focal_mediator_label"]),
        "target_label": str(row["v_label"]),
        "candidate_family": str(row["candidate_family"]),
        "candidate_subfamily": str(row["candidate_subfamily"]),
        "candidate_scope_bucket": str(row["candidate_scope_bucket"]),
        "local_topology_class": str(row["local_topology_class"]),
    }
    if variant == "semantic_blind":
        return base
    return {
        **base,
        "endpoint_broadness_pct": float(row["endpoint_broadness_pct"]),
        "endpoint_resolution_score": float(row["endpoint_resolution_score"]),
        "focal_mediator_specificity_score": float(row["focal_mediator_specificity_score"]),
        "path_support_raw": float(row["path_support_raw"]),
        "motif_count": int(row["motif_count"]),
        "mediator_count": int(row["mediator_count"]),
        "compression_confidence": float(row["compression_confidence"]),
        "compression_failure_reason": None if pd.isna(row["compression_failure_reason"]) else str(row["compression_failure_reason"]),
    }


def _pairwise_payload(row: pd.Series, *, swap: bool = False, variant_name: str = "pairwise_within_field") -> dict[str, Any]:
    left = "b" if swap else "a"
    right = "a" if swap else "b"
    return {
        "pair_id": str(row["pair_id"]),
        "field_slug": str(row["field_slug"]),
        "horizon": int(row["horizon"]),
        "candidate_a": {
            "candidate_id": str(row[f"{left}_candidate_id"]),
            "source_label": str(row[f"{left}_u_label"]),
            "focal_mediator_label": str(row[f"{left}_focal_mediator_label"]),
            "target_label": str(row[f"{left}_v_label"]),
            "candidate_family": str(row[f"{left}_candidate_family"]),
            "candidate_subfamily": str(row[f"{left}_candidate_subfamily"]),
            "candidate_scope_bucket": str(row[f"{left}_candidate_scope_bucket"]),
            "local_topology_class": str(row[f"{left}_local_topology_class"]),
            "endpoint_broadness_pct": float(row[f"{left}_endpoint_broadness_pct"]),
            "endpoint_resolution_score": float(row[f"{left}_endpoint_resolution_score"]),
            "focal_mediator_specificity_score": float(row[f"{left}_focal_mediator_specificity_score"]),
            "path_support_raw": float(row[f"{left}_path_support_raw"]),
            "motif_count": int(row[f"{left}_motif_count"]),
            "mediator_count": int(row[f"{left}_mediator_count"]),
            "compression_confidence": float(row[f"{left}_compression_confidence"]),
            "compression_failure_reason": None if pd.isna(row[f"{left}_compression_failure_reason"]) else str(row[f"{left}_compression_failure_reason"]),
        },
        "candidate_b": {
            "candidate_id": str(row[f"{right}_candidate_id"]),
            "source_label": str(row[f"{right}_u_label"]),
            "focal_mediator_label": str(row[f"{right}_focal_mediator_label"]),
            "target_label": str(row[f"{right}_v_label"]),
            "candidate_family": str(row[f"{right}_candidate_family"]),
            "candidate_subfamily": str(row[f"{right}_candidate_subfamily"]),
            "candidate_scope_bucket": str(row[f"{right}_candidate_scope_bucket"]),
            "local_topology_class": str(row[f"{right}_local_topology_class"]),
            "endpoint_broadness_pct": float(row[f"{right}_endpoint_broadness_pct"]),
            "endpoint_resolution_score": float(row[f"{right}_endpoint_resolution_score"]),
            "focal_mediator_specificity_score": float(row[f"{right}_focal_mediator_specificity_score"]),
            "path_support_raw": float(row[f"{right}_path_support_raw"]),
            "motif_count": int(row[f"{right}_motif_count"]),
            "mediator_count": int(row[f"{right}_mediator_count"]),
            "compression_confidence": float(row[f"{right}_compression_confidence"]),
            "compression_failure_reason": None if pd.isna(row[f"{right}_compression_failure_reason"]) else str(row[f"{right}_compression_failure_reason"]),
        },
        "variant": variant_name,
    }


def _write_markdown(path: Path, title: str, purpose: str, hidden_fields: list[str], prompt: str, schema_name: str) -> None:
    lines = [
        f"# {title}",
        "",
        f"## Purpose",
        f"- {purpose}",
        "",
        "## Hidden Fields",
    ]
    for field in hidden_fields:
        lines.append(f"- `{field}`")
    lines.extend(
        [
            "",
            "## Prompt",
            "```text",
            prompt,
            "```",
            "",
            "## Structured Output",
            f"- Strict JSON schema file: `{schema_name}`",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def _build_response_request(
    custom_id: str,
    model: str,
    prompt: str,
    schema_name: str,
    schema: dict[str, Any],
    user_payload: dict[str, Any],
    *,
    max_output_tokens: int = 260,
    verbosity: str = "low",
) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
                "verbosity": verbosity,
            },
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": "none"},
        },
    }


def _write_batch_submission_example(path: Path) -> None:
    text = """# Batch Submission Example

These JSONL files target the Responses API with Structured Outputs.

Official references used here:
- Structured Outputs via `text.format`: https://developers.openai.com/api/docs/guides/structured-outputs
- Batch API JSONL shape: https://developers.openai.com/api/docs/guides/batch#1-prepare-your-batch-file

Example workflow:

1. Upload one JSONL file as a batch input file.
2. Create a batch targeting `/v1/responses`.
3. Download the output file when the batch completes.

Illustrative commands:

```bash
curl https://api.openai.com/v1/files \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -F purpose="batch" \\
  -F file="@outputs/paper/97_llm_screening_prompt_pack/prompt_a_batch_2000.jsonl"

curl https://api.openai.com/v1/batches \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input_file_id": "file-REPLACE_ME",
    "endpoint": "/v1/responses",
    "completion_window": "24h"
  }'
```
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare appendix-ready LLM prompt pack and batch files.")
    parser.add_argument(
        "--current-frontier",
        type=Path,
        default=Path("outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv"),
    )
    parser.add_argument(
        "--within-field",
        type=Path,
        default=Path("outputs/paper/95_objective_specific_frontier_packages/within_field_top100_pool2000/package.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper/97_llm_screening_prompt_pack"),
    )
    parser.add_argument("--model", type=str, default="gpt-5.4-mini")
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_df = _build_candidate_sample(args.current_frontier)
    pair_df = _build_pairwise_sample(args.within_field, args.current_frontier)

    sample_df.to_csv(out_dir / "candidate_pilot2000.csv", index=False)
    pair_df.to_csv(out_dir / "pairwise_pilot2000.csv", index=False)

    schema_a = _semantic_blind_schema()
    schema_b = _record_aware_schema()
    schema_c = _pairwise_schema("pairwise_within_field")
    schema_d = _rewrite_schema()
    schema_e = _veto_schema()
    schema_f = _pairwise_schema("pairwise_within_field_swapped")

    _write_json(out_dir / "schema_a_semantic_blind.json", schema_a)
    _write_json(out_dir / "schema_b_record_aware.json", schema_b)
    _write_json(out_dir / "schema_c_pairwise_within_field.json", schema_c)
    _write_json(out_dir / "schema_d_rewrite_survivor.json", schema_d)
    _write_json(out_dir / "schema_e_veto_screen.json", schema_e)
    _write_json(out_dir / "schema_f_pairwise_swapped_within_field.json", schema_f)

    _write_markdown(
        out_dir / "prompt_a_semantic_blind.md",
        "Prompt A: Semantic-Blind",
        "Single-candidate screening using only labels and family tags, without graph-local numeric diagnostics.",
        [
            "surface_rank",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "field_slug",
            "semantic_family_key",
            "theme_pair_key",
            "source_theme",
            "target_theme",
            "all derived penalties",
        ],
        PROMPT_A,
        "schema_a_semantic_blind.json",
    )
    _write_markdown(
        out_dir / "prompt_b_record_aware.md",
        "Prompt B: Record-Aware",
        "Single-candidate screening using labels plus graph-local diagnostics such as broadness, resolution, support, and compression.",
        [
            "surface_rank",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "field_slug",
            "semantic_family_key",
            "theme_pair_key",
            "source_theme",
            "target_theme",
            "all derived penalties",
        ],
        PROMPT_B,
        "schema_b_record_aware.json",
    )
    _write_markdown(
        out_dir / "prompt_c_pairwise_within_field.md",
        "Prompt C: Pairwise Within-Field",
        "Within-field pairwise screening for shelf ordering using two candidates from the same field and horizon.",
        [
            "surface_rank",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "semantic_family_key",
            "theme_pair_key",
            "source_theme",
            "target_theme",
            "all derived penalties",
        ],
        PROMPT_C,
        "schema_c_pairwise_within_field.json",
    )
    _write_markdown(
        out_dir / "prompt_d_rewrite_survivor.md",
        "Prompt D: Rewrite Survivor",
        "Second-stage rewrite prompt for already-screened survivors. This is not batched in the first pilot.",
        ["all ranking fields", "all scores from the screening model"],
        PROMPT_D,
        "schema_d_rewrite_survivor.json",
    )
    _write_markdown(
        out_dir / "prompt_e_veto_screen.md",
        "Prompt E: Veto Screen",
        "Single-candidate coarse screening variant that returns pass/review/fail instead of a 1-5 score.",
        [
            "surface_rank",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "field_slug",
            "semantic_family_key",
            "theme_pair_key",
            "source_theme",
            "target_theme",
            "all derived penalties",
        ],
        PROMPT_E,
        "schema_e_veto_screen.json",
    )
    _write_markdown(
        out_dir / "prompt_f_pairwise_swapped_within_field.md",
        "Prompt F: Pairwise Within-Field Swapped",
        "Same pairwise screening task as Prompt C, but with candidate order swapped to measure position bias.",
        [
            "surface_rank",
            "frontier_rank",
            "reranker_rank",
            "transparent_rank",
            "semantic_family_key",
            "theme_pair_key",
            "source_theme",
            "target_theme",
            "all derived penalties",
        ],
        PROMPT_F,
        "schema_f_pairwise_swapped_within_field.json",
    )

    batch_a: list[dict[str, Any]] = []
    batch_b: list[dict[str, Any]] = []
    batch_e: list[dict[str, Any]] = []
    for _, row in sample_df.iterrows():
        payload_a = _candidate_payload(row, "semantic_blind")
        payload_b = _candidate_payload(row, "record_aware")
        custom_core = str(row["pilot_row_id"])
        batch_a.append(
            _build_response_request(
                custom_id=f"prompt-a-{custom_core}",
                model=args.model,
                prompt=PROMPT_A,
                schema_name="semantic_blind_screen_v1",
                schema=schema_a,
                user_payload=payload_a,
                max_output_tokens=220,
            )
        )
        batch_b.append(
            _build_response_request(
                custom_id=f"prompt-b-{custom_core}",
                model=args.model,
                prompt=PROMPT_B,
                schema_name="record_aware_screen_v2",
                schema=schema_b,
                user_payload=payload_b,
                max_output_tokens=320,
            )
        )
        batch_e.append(
            _build_response_request(
                custom_id=f"prompt-e-{custom_core}",
                model=args.model,
                prompt=PROMPT_E,
                schema_name="veto_screen_v1",
                schema=schema_e,
                user_payload=payload_b,
                max_output_tokens=180,
            )
        )

    batch_c: list[dict[str, Any]] = []
    batch_f: list[dict[str, Any]] = []
    for _, row in pair_df.iterrows():
        payload_c = _pairwise_payload(row, variant_name="pairwise_within_field")
        batch_c.append(
            _build_response_request(
                custom_id=f"prompt-c-{row['pair_id']}",
                model=args.model,
                prompt=PROMPT_C,
                schema_name="pairwise_within_field_v1",
                schema=schema_c,
                user_payload=payload_c,
                max_output_tokens=240,
            )
        )
        payload_f = _pairwise_payload(row, swap=True, variant_name="pairwise_within_field_swapped")
        batch_f.append(
            _build_response_request(
                custom_id=f"prompt-f-{row['pair_id']}",
                model=args.model,
                prompt=PROMPT_F,
                schema_name="pairwise_within_field_swapped_v1",
                schema=schema_f,
                user_payload=payload_f,
                max_output_tokens=240,
            )
        )

    _write_jsonl(out_dir / "prompt_a_batch_2000.jsonl", batch_a)
    _write_jsonl(out_dir / "prompt_b_batch_2000.jsonl", batch_b)
    _write_jsonl(out_dir / "prompt_c_batch_2000.jsonl", batch_c)
    _write_jsonl(out_dir / "prompt_e_batch_2000.jsonl", batch_e)
    _write_jsonl(out_dir / "prompt_f_batch_2000.jsonl", batch_f)
    _write_batch_submission_example(out_dir / "batch_submission_example.md")

    manifest = {
        "model": args.model,
        "source_files": {
            "candidate_frontier": str(args.current_frontier),
            "within_field_package": str(args.within_field),
        },
        "counts": {
            "candidate_pilot_rows": int(len(sample_df)),
            "pairwise_pilot_rows": int(len(pair_df)),
            "prompt_a_requests": int(len(batch_a)),
            "prompt_b_requests": int(len(batch_b)),
            "prompt_c_requests": int(len(batch_c)),
            "prompt_e_requests": int(len(batch_e)),
            "prompt_f_requests": int(len(batch_f)),
        },
        "sampling_design": {
            "candidate_pilot": {
                "source": "pool=2000 current frontier",
                "bands_per_horizon": {"top": [1, 250], "mid": [251, 750], "deep": [751, 2000]},
                "quotas": {
                    "h5": {"top": 200, "mid": 200, "deep": 267},
                    "h10": {"top": 200, "mid": 200, "deep": 267},
                    "h15": {"top": 200, "mid": 200, "deep": 266},
                },
                "selection": "deterministic evenly spaced rows within each band",
            },
            "pairwise_pilot": {
                "source": "within-field top100 package",
                "base_pairs": "all adjacent pairs within each field shelf",
                "extra_pairs": "round-robin wider-gap pairs within shelves until 2000 total pairs",
            },
        },
        "hidden_fields": {
            "prompt_a": ["all ranks", "field_slug", "theme keys", "derived penalties", "numeric graph diagnostics"],
            "prompt_b": ["all ranks", "field_slug", "theme keys", "derived penalties"],
            "prompt_c": ["all ranks", "theme keys", "derived penalties"],
            "prompt_e": ["all ranks", "field_slug", "theme keys", "derived penalties"],
            "prompt_f": ["all ranks", "theme keys", "derived penalties"],
        },
        "schema_hashes": {
            "prompt_a": _sha1_text(json.dumps(schema_a, sort_keys=True)),
            "prompt_b": _sha1_text(json.dumps(schema_b, sort_keys=True)),
            "prompt_c": _sha1_text(json.dumps(schema_c, sort_keys=True)),
            "prompt_d": _sha1_text(json.dumps(schema_d, sort_keys=True)),
            "prompt_e": _sha1_text(json.dumps(schema_e, sort_keys=True)),
            "prompt_f": _sha1_text(json.dumps(schema_f, sort_keys=True)),
        },
        "docs_basis": {
            "structured_outputs": "https://developers.openai.com/api/docs/guides/structured-outputs",
            "batch_api": "https://developers.openai.com/api/docs/guides/batch#1-prepare-your-batch-file",
            "prompt_guidance": "https://developers.openai.com/api/docs/guides/prompt-guidance#keep-outputs-compact-and-structured",
        },
    }
    _write_json(out_dir / "manifest.json", manifest)


if __name__ == "__main__":
    main()
