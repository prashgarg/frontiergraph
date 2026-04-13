from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from prepare_llm_screening_batches import _build_response_request, _write_json, _write_jsonl, _write_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = ROOT / "outputs" / "paper" / "174_wide_mechanism_mini_triage_pack" / "candidate_packets.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "174_wide_mechanism_mini_triage_pack"
DEFAULT_MODEL = "gpt-5.4-mini"

FIELD_ENUM = [
    "macro-finance",
    "development-urban",
    "trade-globalization",
    "climate-energy",
    "innovation-productivity",
    "labor-household-outcomes",
    "other",
]
USE_CASE_ENUM = [
    "strong-nearby-evidence",
    "phd-topic",
    "open-little-direct",
    "cross-area-mechanism",
    "paper-ready",
]

TRIAGE_PROMPT = """You are screening candidate public-facing mechanism research questions for Frontier Graph.

Each record comes from a local economics literature graph. The candidate is not a proven claim. It is a suggested mechanism question built from nearby support paths.

Your job is stricter than the deterministic Stage A filter. Many candidates are still too broad, repetitive, weakly compressed, or badly shelved.

Judge only whether the candidate is good enough for the public site.
Be skeptical. Prefer to reject broad, awkward, canonical, or weakly specified objects.

Keep a candidate only when all of the following mostly hold:
- the endpoints are interpretable
- the mechanism story is plausible
- the question reads like something a researcher could inspect
- the first step is concrete rather than generic
- the object is not mainly a synonym duplicate or a relabeled direct claim

Field shelves must come from this set:
- macro-finance
- development-urban
- trade-globalization
- climate-energy
- innovation-productivity
- labor-household-outcomes
- other

Use-case tags must come from this set:
- strong-nearby-evidence
- phd-topic
- open-little-direct
- cross-area-mechanism
- paper-ready

You may disagree with the Stage A shelf and tag suggestions.
Do not use outside knowledge, prestige, citations, or beliefs about importance.
Use only the supplied record.

Return only strict JSON.
Keep the reason short and evidence-based."""


TRIAGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pair_key": {"type": "string"},
        "keep_for_public_site": {"type": "boolean"},
        "plausible_mechanism_question": {"type": "boolean"},
        "reader_facing": {"type": "boolean"},
        "too_generic": {"type": "boolean"},
        "alias_like_duplicate_risk": {"type": "boolean"},
        "field_shelves": {
            "type": "array",
            "items": {"type": "string", "enum": FIELD_ENUM},
            "minItems": 1,
            "maxItems": 3,
        },
        "collection_tags": {
            "type": "array",
            "items": {"type": "string", "enum": USE_CASE_ENUM},
            "minItems": 1,
            "maxItems": 4,
        },
        "primary_use_case": {"type": "string", "enum": USE_CASE_ENUM},
        "endpoint_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
        "channel_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
        "question_object_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
        "mechanism_plausibility": {"type": "integer", "minimum": 1, "maximum": 5},
        "duplicate_family_risk": {"type": "integer", "minimum": 1, "maximum": 5},
        "primary_issue": {
            "type": "string",
            "enum": [
                "none",
                "generic_endpoints",
                "weak_channels",
                "odd_semantics",
                "duplicate_or_alias_risk",
                "field_misfit",
                "use_case_misfit",
                "not_reader_facing",
                "too_close_to_direct_claim",
                "missing_support",
                "other",
            ],
        },
        "suggested_priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
        "reason": {"type": "string", "maxLength": 180},
    },
    "required": [
        "pair_key",
        "keep_for_public_site",
        "plausible_mechanism_question",
        "reader_facing",
        "too_generic",
        "alias_like_duplicate_risk",
        "field_shelves",
        "collection_tags",
        "primary_use_case",
        "endpoint_specificity",
        "channel_specificity",
        "question_object_clarity",
        "mechanism_plausibility",
        "duplicate_family_risk",
        "primary_issue",
        "suggested_priority",
        "confidence",
        "reason",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare wide-pool mini-model triage requests for mechanism website candidates.")
    parser.add_argument("--packets", default=str(DEFAULT_PACKETS), dest="packets")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def load_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if limit is not None:
        rows = rows[:limit]
    parsed: list[dict[str, Any]] = []
    for row in rows:
        out = dict(row)
        for key in [
            "available_horizons",
            "field_shelves_stage_a",
            "collection_tags_stage_a",
            "primary_channels",
            "top_paths",
            "starter_papers",
        ]:
            out[key] = json.loads(row[key]) if row.get(key) else []
        for key in [
            "packet_rank",
            "horizon",
            "best_horizon",
            "surface_rank",
            "reranker_rank",
            "transparent_rank",
            "mediator_count",
            "supporting_path_count",
            "duplicate_family_flag_stage_a",
            "semantic_family_duplicate_count_stage_a",
            "theme_pair_duplicate_count_stage_a",
            "primary_clean_channel_count_stage_a",
            "primary_blocked_channel_count_stage_a",
            "cross_theme_flag_stage_a",
        ]:
            out[key] = int(float(row[key] or 0))
        for key in [
            "stage_a_score",
            "clarity_score_stage_a",
            "plausibility_score_stage_a",
            "specificity_score_stage_a",
            "endpoint_specificity_score_stage_a",
            "channel_specificity_score_stage_a",
            "reranker_score",
            "transparent_score",
            "cooc_count",
        ]:
            out[key] = float(row[key] or 0.0)
        parsed.append(out)
    return parsed


def triage_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_key": row["pair_key"],
        "source_label": row["source_label"],
        "target_label": row["target_label"],
        "route_family": row["route_family"],
        "display_title": row["display_title"],
        "display_why": row["display_why"],
        "display_first_step": row["display_first_step"],
        "baseline_direct_title": row["baseline_direct_title"],
        "primary_channels": row["primary_channels"],
        "top_paths": [
            {
                "path_labels": path.get("path_labels", []),
                "score": path.get("score"),
            }
            for path in row["top_paths"][:5]
        ],
        "starter_papers": [
            {
                "title": paper.get("title"),
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "matched_edge_count": paper.get("matched_edge_count"),
            }
            for paper in row["starter_papers"][:3]
        ],
        "deterministic_stage_a": {
            "field_shelves": row["field_shelves_stage_a"],
            "collection_tags": row["collection_tags_stage_a"],
            "primary_use_case": row["primary_use_case_stage_a"],
            "stage_a_score": row["stage_a_score"],
            "clarity_score": row["clarity_score_stage_a"],
            "plausibility_score": row["plausibility_score_stage_a"],
            "specificity_score": row["specificity_score_stage_a"],
            "endpoint_specificity_score": row["endpoint_specificity_score_stage_a"],
            "channel_specificity_score": row["channel_specificity_score_stage_a"],
            "duplicate_family_flag": row["duplicate_family_flag_stage_a"],
            "semantic_family_duplicate_count": row["semantic_family_duplicate_count_stage_a"],
            "theme_pair_duplicate_count": row["theme_pair_duplicate_count_stage_a"],
        },
        "best_horizon": row["best_horizon"],
        "available_horizons": row["available_horizons"],
        "surface_rank": row["surface_rank"],
        "reranker_rank": row["reranker_rank"],
        "transparent_rank": row["transparent_rank"],
        "mediator_count": row["mediator_count"],
        "supporting_path_count": row["supporting_path_count"],
        "source_theme": row["source_theme"],
        "target_theme": row["target_theme"],
        "semantic_family_key": row["semantic_family_key"],
        "theme_pair_key": row["theme_pair_key"],
        "cross_theme_flag_stage_a": row["cross_theme_flag_stage_a"],
    }


def main() -> None:
    args = parse_args()
    packets_path = Path(args.packets)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(packets_path, args.limit)

    requests = []
    for row in rows:
        pair_key = row["pair_key"]
        requests.append(
            _build_response_request(
                custom_id=f"wide-mechanism-triage-{pair_key}",
                model=args.model,
                prompt=TRIAGE_PROMPT,
                schema_name="wide_mechanism_public_triage",
                schema=TRIAGE_SCHEMA,
                user_payload=triage_payload(row),
                max_output_tokens=320,
                verbosity="low",
            )
        )

    _write_json(out_dir / "triage_schema.json", TRIAGE_SCHEMA)
    _write_jsonl(out_dir / "wide_mechanism_triage_requests.jsonl", requests)
    _write_markdown(
        out_dir / "triage_prompt.md",
        title="Wide Mechanism Mini Triage",
        purpose="Full widened-pool mechanism screening for the public site.",
        hidden_fields=[],
        prompt=TRIAGE_PROMPT,
        schema_name="triage_schema.json",
    )
    manifest = {
        "packets": str(packets_path),
        "model": args.model,
        "n_requests": len(requests),
    }
    _write_json(out_dir / "triage_manifest.json", manifest)
    print(f"Wrote {out_dir / 'wide_mechanism_triage_requests.jsonl'}")


if __name__ == "__main__":
    main()
