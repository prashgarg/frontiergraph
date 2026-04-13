from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from prepare_llm_screening_batches import _build_response_request, _write_json, _write_jsonl, _write_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "candidate_packets.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "169_mechanism_public_llm"
DEFAULT_MODEL = "gpt-5.4-mini"


TRIAGE_PROMPT = """You are screening candidate public-facing mechanism research questions for Frontier Graph.

Each record comes from a local economics literature graph. The candidate is not a proven claim. It is a suggested mechanism question built from nearby support paths.

Judge only whether the candidate is good enough for a public site card.
Be skeptical. Prefer to reject broad, awkward, canonical, or weakly compressed objects.

Keep a candidate only when all of the following mostly hold:
- the endpoints are interpretable
- the mechanism story is plausible
- the question reads like something a researcher could inspect
- the first step is concrete rather than generic
- the object is not just a synonym duplicate or a relabeled direct claim

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
        "primary_issue": {
            "type": "string",
            "enum": [
                "none",
                "generic_endpoints",
                "weak_channels",
                "odd_semantics",
                "duplicate_or_alias_risk",
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
        "primary_issue",
        "suggested_priority",
        "confidence",
        "reason",
    ],
}


REWRITE_PROMPT = """You are rewriting kept mechanism-question candidates for the public Frontier Graph site.

The goal is one crisp card per candidate.
Do not invent new claims or mechanisms.
Do not oversell certainty.

Requirements:
- question_title: paper-shaped, concrete, readable, and economist-facing
- short_why: one short sentence saying why this is a mechanism question worth inspecting
- first_next_step: one concrete first empirical or synthesis step
- who_its_for: a short audience phrase
- field_shelves: 1 to 3 lowercase shelf tags
- collection_tags: 1 to 4 lowercase collection tags

Avoid vague phrases such as:
- various channels
- different factors
- important role
- examine the relationship

Return only strict JSON."""


REWRITE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pair_key": {"type": "string"},
        "question_title": {"type": "string", "maxLength": 140},
        "short_why": {"type": "string", "maxLength": 220},
        "first_next_step": {"type": "string", "maxLength": 240},
        "who_its_for": {"type": "string", "maxLength": 120},
        "field_shelves": {
            "type": "array",
            "items": {"type": "string", "maxLength": 40},
            "minItems": 1,
            "maxItems": 3,
        },
        "collection_tags": {
            "type": "array",
            "items": {"type": "string", "maxLength": 40},
            "minItems": 1,
            "maxItems": 4,
        },
    },
    "required": [
        "pair_key",
        "question_title",
        "short_why",
        "first_next_step",
        "who_its_for",
        "field_shelves",
        "collection_tags",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare concurrent LLM triage and rewrite request files for public mechanism questions.")
    parser.add_argument("--packets", default=str(DEFAULT_PACKETS), dest="packets")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--triage-model", default=DEFAULT_MODEL, dest="triage_model")
    parser.add_argument("--rewrite-model", default="gpt-5.4", dest="rewrite_model")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def load_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if limit is not None:
        rows = rows[:limit]
    for row in rows:
        for key in ["primary_channels", "top_paths", "starter_papers"]:
            row[key] = json.loads(row[key]) if row.get(key) else []
        for key in ["shortlist_rank", "surface_rank", "reranker_rank", "transparent_rank", "mediator_count", "supporting_path_count", "horizon"]:
            row[key] = int(float(row[key] or 0))
        for key in ["reranker_score", "transparent_score"]:
            row[key] = float(row[key] or 0.0)
    return rows


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
        "shortlist_rank": row["shortlist_rank"],
        "mediator_count": row["mediator_count"],
        "supporting_path_count": row["supporting_path_count"],
        "source_theme": row["source_theme"],
        "target_theme": row["target_theme"],
        "semantic_family_key": row["semantic_family_key"],
    }


def rewrite_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_key": row["pair_key"],
        "source_label": row["source_label"],
        "target_label": row["target_label"],
        "display_title": row["display_title"],
        "display_why": row["display_why"],
        "display_first_step": row["display_first_step"],
        "primary_channels": row["primary_channels"],
        "starter_papers": [
            {
                "title": paper.get("title"),
                "year": paper.get("year"),
                "venue": paper.get("venue"),
            }
            for paper in row["starter_papers"][:3]
        ],
        "source_theme": row["source_theme"],
        "target_theme": row["target_theme"],
        "semantic_family_key": row["semantic_family_key"],
    }


def main() -> None:
    args = parse_args()
    packets_path = Path(args.packets)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(packets_path, args.limit)

    triage_requests = []
    rewrite_requests = []
    for row in rows:
        pair_key = row["pair_key"]
        triage_requests.append(
            _build_response_request(
                custom_id=f"mechanism-triage-{pair_key}",
                model=args.triage_model,
                prompt=TRIAGE_PROMPT,
                schema_name="mechanism_public_triage",
                schema=TRIAGE_SCHEMA,
                user_payload=triage_payload(row),
                max_output_tokens=220,
                verbosity="low",
            )
        )
        rewrite_requests.append(
            _build_response_request(
                custom_id=f"mechanism-rewrite-{pair_key}",
                model=args.rewrite_model,
                prompt=REWRITE_PROMPT,
                schema_name="mechanism_public_card_rewrite",
                schema=REWRITE_SCHEMA,
                user_payload=rewrite_payload(row),
                max_output_tokens=260,
                verbosity="low",
            )
        )

    _write_json(out_dir / "triage_schema.json", TRIAGE_SCHEMA)
    _write_json(out_dir / "rewrite_schema.json", REWRITE_SCHEMA)
    _write_markdown(
        out_dir / "triage_prompt.md",
        title="Mechanism Public Triage Prompt",
        purpose="Keep-or-drop screening for public mechanism-question cards.",
        hidden_fields=["shortlist_rank", "semantic_family_key", "source_theme", "target_theme"],
        prompt=TRIAGE_PROMPT,
        schema_name="triage_schema.json",
    )
    _write_markdown(
        out_dir / "rewrite_prompt.md",
        title="Mechanism Public Rewrite Prompt",
        purpose="Final public-card rewrite for mechanism questions after triage.",
        hidden_fields=["source_theme", "target_theme", "semantic_family_key"],
        prompt=REWRITE_PROMPT,
        schema_name="rewrite_schema.json",
    )
    _write_jsonl(out_dir / "triage_requests.jsonl", triage_requests)
    _write_jsonl(out_dir / "rewrite_requests_gpt54.jsonl", rewrite_requests)
    print(f"Wrote {out_dir / 'triage_requests.jsonl'}")
    print(f"Wrote {out_dir / 'rewrite_requests_gpt54.jsonl'}")


if __name__ == "__main__":
    main()
