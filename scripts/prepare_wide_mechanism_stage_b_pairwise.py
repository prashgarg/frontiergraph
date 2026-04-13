from __future__ import annotations

import argparse
import ast
import csv
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from prepare_llm_screening_batches import _build_response_request, _write_json, _write_jsonl, _write_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_DIR = ROOT / "outputs" / "paper" / "177_wide_mechanism_stage_b_seed"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "178_wide_mechanism_stage_b_pairwise_pack"
DEFAULT_MODEL = "gpt-5.4-mini"

FIELD_SHELVES = [
    "macro-finance",
    "climate-energy",
    "innovation-productivity",
    "labor-household-outcomes",
    "development-urban",
    "trade-globalization",
    "other",
]

USE_CASES = [
    "cross-area-mechanism",
    "phd-topic",
    "paper-ready",
    "strong-nearby-evidence",
    "open-little-direct",
]

PAIRWISE_PROMPT = """You are comparing two candidate public-facing mechanism-question cards for Frontier Graph.

Both candidates are already plausible enough to have survived an earlier screen.
Your job now is narrower: decide which card should rank higher within the same website shelf.

Judge only the supplied records. Do not use outside knowledge, citations, prestige, or beliefs about topic importance.
The earlier numeric scores are useful evidence, but they are not authoritative. Use them only as supporting diagnostics.

Prefer the candidate that is more likely to work as a credible public-facing research question card:
- clearer source and target endpoints
- more concrete mechanism channels
- sharper question wording
- a more usable first empirical step
- less generic, canonical, or duplicate-like
- less like a relabeled direct claim

Return tie if the two cards are genuinely close.
Do not force a winner.

Return only strict JSON.
Keep the reason short and evidence-based."""


PAIRWISE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pair_id": {"type": "string"},
        "variant": {"type": "string", "enum": ["mechanism_stage_b_pairwise", "mechanism_stage_b_pairwise_swapped"]},
        "preferred_candidate": {"type": "string", "enum": ["A", "B", "tie"]},
        "question_clarity_preference": {"type": "string", "enum": ["A", "B", "tie"]},
        "mechanism_specificity_preference": {"type": "string", "enum": ["A", "B", "tie"]},
        "first_step_preference": {"type": "string", "enum": ["A", "B", "tie"]},
        "credibility_preference": {"type": "string", "enum": ["A", "B", "tie"]},
        "confidence": {"type": "integer", "minimum": 1, "maximum": 5},
        "reason": {"type": "string", "maxLength": 220},
    },
    "required": [
        "pair_id",
        "variant",
        "preferred_candidate",
        "question_clarity_preference",
        "mechanism_specificity_preference",
        "first_step_preference",
        "credibility_preference",
        "confidence",
        "reason",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Stage B pairwise reranking requests for the wide mechanism website shelves.")
    parser.add_argument("--seed-dir", default=str(DEFAULT_SEED_DIR), dest="seed_dir")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit-shelves", type=int, default=None, dest="limit_shelves")
    parser.add_argument("--limit-pairs-per-shelf", type=int, default=None, dest="limit_pairs_per_shelf")
    parser.add_argument("--window", type=int, default=8, dest="window")
    parser.add_argument("--anchor-count", type=int, default=5, dest="anchor_count")
    parser.add_argument("--anchor-depth", type=int, default=30, dest="anchor_depth")
    parser.add_argument("--include-swapped", action="store_true", default=False, dest="include_swapped")
    return parser.parse_args()


def parse_json_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    text = str(raw).strip()
    if not text:
        return []
    try:
        value = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    parsed: list[dict[str, Any]] = []
    for row in rows:
        out = dict(row)
        for key in [
            "available_horizons",
            "field_shelves_stage_a",
            "collection_tags_stage_a",
            "primary_channels",
            "field_shelves",
            "collection_tags",
        ]:
            out[key] = parse_json_list(row.get(key))
        for key in ["top_paths", "starter_papers"]:
            try:
                out[key] = json.loads(row.get(key) or "[]")
            except json.JSONDecodeError:
                out[key] = []
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
            "field_shelf_count_mini",
            "collection_tag_count_mini",
            "priority_rank",
            "issue_rank",
        ]:
            out[key] = int(float(row.get(key) or 0))
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
            "endpoint_specificity",
            "channel_specificity",
            "question_object_clarity",
            "mechanism_plausibility",
            "duplicate_family_risk",
            "confidence",
        ]:
            out[key] = float(row.get(key) or 0.0)
        for key in [
            "keep_for_public_site",
            "plausible_mechanism_question",
            "reader_facing",
            "too_generic",
            "alias_like_duplicate_risk",
            "has_model_response",
        ]:
            val = row.get(key)
            out[key] = str(val).lower() == "true"
        parsed.append(out)
    return parsed


def candidate_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_key": row["pair_key"],
        "source_label": row["source_label"],
        "target_label": row["target_label"],
        "display_title": row["display_title"],
        "display_why": row["display_why"],
        "display_first_step": row["display_first_step"],
        "baseline_direct_title": row["baseline_direct_title"],
        "primary_channels": row["primary_channels"][:4],
        "field_shelves": row["field_shelves"][:3],
        "collection_tags": row["collection_tags"][:4],
        "primary_use_case": row["primary_use_case"],
        "question_diagnostics": {
            "endpoint_specificity": int(row["endpoint_specificity"]),
            "channel_specificity": int(row["channel_specificity"]),
            "question_object_clarity": int(row["question_object_clarity"]),
            "mechanism_plausibility": int(row["mechanism_plausibility"]),
            "duplicate_family_risk": int(row["duplicate_family_risk"]),
            "primary_issue": row["primary_issue"],
            "suggested_priority": row["suggested_priority"],
        },
        "evidence_snapshot": {
            "best_horizon": int(row["best_horizon"]),
            "available_horizons": row["available_horizons"],
            "surface_rank": int(row["surface_rank"]),
            "reranker_rank": int(row["reranker_rank"]),
            "transparent_rank": int(row["transparent_rank"]),
            "mediator_count": int(row["mediator_count"]),
            "supporting_path_count": int(row["supporting_path_count"]),
            "top_path_labels": [path.get("path_labels", []) for path in row["top_paths"][:3]],
        },
        "screen_reason": row["reason"],
    }


def build_pair_payload(pair_id: str, shelf_kind: str, shelf_name: str, row_a: dict[str, Any], row_b: dict[str, Any], *, swapped: bool, variant: str) -> dict[str, Any]:
    cand_a = candidate_payload(row_b if swapped else row_a)
    cand_b = candidate_payload(row_a if swapped else row_b)
    return {
        "pair_id": pair_id,
        "shelf_kind": shelf_kind,
        "shelf_name": shelf_name,
        "candidate_a": cand_a,
        "candidate_b": cand_b,
        "note": "Both candidates come from the same website shelf. Choose the one that should rank higher within that shelf.",
        "variant": variant,
    }


def build_sampled_pairs(n: int, *, window: int, anchor_count: int, anchor_depth: int) -> list[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()

    for i in range(n):
        upper = min(n, i + 1 + max(window, 0))
        for j in range(i + 1, upper):
            pairs.add((i, j))

    anchor_n = min(max(anchor_count, 0), n)
    anchor_upper = min(max(anchor_depth, 0), n)
    for i in range(anchor_n):
        for j in range(i + 1, anchor_upper):
            pairs.add((i, j))

    return sorted(pairs)


def iter_shelves(seed_dir: Path) -> list[tuple[str, str, Path]]:
    shelves: list[tuple[str, str, Path]] = []
    for shelf in FIELD_SHELVES:
        shelves.append(("field", shelf, seed_dir / f"field_{shelf}.csv"))
    for tag in USE_CASES:
        shelves.append(("use_case", tag, seed_dir / f"use_case_{tag}.csv"))
    shelves.append(("front", "global-front", seed_dir / "global_front.csv"))
    return shelves


def main() -> None:
    args = parse_args()
    seed_dir = Path(args.seed_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pair_rows: list[dict[str, Any]] = []
    direct_requests: list[dict[str, Any]] = []
    swapped_requests: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    shelves = iter_shelves(seed_dir)
    if args.limit_shelves is not None:
        shelves = shelves[: int(args.limit_shelves)]

    for shelf_kind, shelf_name, path in shelves:
        rows = load_rows(path)
        for row in rows:
            candidate_rows.append({"shelf_kind": shelf_kind, "shelf_name": shelf_name, **row})
        sampled_pairs = build_sampled_pairs(
            len(rows),
            window=int(args.window),
            anchor_count=int(args.anchor_count),
            anchor_depth=int(args.anchor_depth),
        )
        if args.limit_pairs_per_shelf is not None:
            sampled_pairs = sampled_pairs[: int(args.limit_pairs_per_shelf)]
        for pair_counter, (a_idx, b_idx) in enumerate(sampled_pairs, start=1):
            row_a = rows[a_idx]
            row_b = rows[b_idx]
            pair_id = f"{shelf_kind}:{shelf_name}:{pair_counter:05d}"
            pair_rows.append(
                {
                    "pair_id": pair_id,
                    "shelf_kind": shelf_kind,
                    "shelf_name": shelf_name,
                    "a_pair_key": row_a["pair_key"],
                    "b_pair_key": row_b["pair_key"],
                    "a_display_title": row_a["display_title"],
                    "b_display_title": row_b["display_title"],
                }
            )

            direct_payload = build_pair_payload(
                pair_id,
                shelf_kind,
                shelf_name,
                row_a,
                row_b,
                swapped=False,
                variant="mechanism_stage_b_pairwise",
            )
            swapped_payload = build_pair_payload(
                pair_id,
                shelf_kind,
                shelf_name,
                row_a,
                row_b,
                swapped=True,
                variant="mechanism_stage_b_pairwise_swapped",
            )
            direct_requests.append(
                _build_response_request(
                    custom_id=f"stageb-direct-{pair_id}",
                    model=args.model,
                    prompt=PAIRWISE_PROMPT,
                    schema_name="mechanism_stage_b_pairwise_v1",
                    schema=PAIRWISE_SCHEMA,
                    user_payload=direct_payload,
                    max_output_tokens=140,
                )
            )
            if args.include_swapped:
                swapped_requests.append(
                    _build_response_request(
                        custom_id=f"stageb-swapped-{pair_id}",
                        model=args.model,
                        prompt=PAIRWISE_PROMPT,
                        schema_name="mechanism_stage_b_pairwise_swapped_v1",
                        schema=PAIRWISE_SCHEMA,
                        user_payload=swapped_payload,
                        max_output_tokens=140,
                    )
                )

    pd.DataFrame(candidate_rows).to_csv(out_dir / "candidate_rows.csv", index=False)
    pd.DataFrame(pair_rows).to_csv(out_dir / "pairwise_rows.csv", index=False)
    _write_jsonl(out_dir / "pairwise_direct.jsonl", direct_requests)
    _write_jsonl(out_dir / "pairwise_swapped.jsonl", swapped_requests)
    _write_json(out_dir / "pairwise_schema.json", PAIRWISE_SCHEMA)
    _write_json(
        out_dir / "manifest.json",
        {
            "seed_dir": str(seed_dir),
            "model": args.model,
            "sampling": {
                "window": int(args.window),
                "anchor_count": int(args.anchor_count),
                "anchor_depth": int(args.anchor_depth),
                "include_swapped": bool(args.include_swapped),
            },
            "shelves": [{"kind": kind, "name": name, "path": str(path)} for kind, name, path in shelves],
            "candidate_rows": len(candidate_rows),
            "pair_rows": len(pair_rows),
            "direct_requests": len(direct_requests),
            "swapped_requests": len(swapped_requests),
        },
    )
    _write_markdown(
        out_dir / "prompt_pairwise.md",
        "Stage B Pairwise Shelf Reranking",
        "Pairwise shelf ordering for mechanism question cards using direct and swapped candidate order.",
        ["display_title", "display_why", "display_first_step", "primary_channels", "question_diagnostics", "screen_reason"],
        PAIRWISE_PROMPT,
        "pairwise_schema.json",
    )

    lines = [
        "# Wide Mechanism Stage B Pairwise Pack",
        "",
        f"- candidate rows across all shelves: {len(candidate_rows):,}",
        f"- unique shelf pair rows: {len(pair_rows):,}",
        f"- direct requests: {len(direct_requests):,}",
        f"- swapped requests: {len(swapped_requests):,}",
        f"- window size: {int(args.window):,}",
        f"- anchor count: {int(args.anchor_count):,}",
        f"- anchor depth: {int(args.anchor_depth):,}",
        "",
        "## Shelves",
        "",
    ]
    for shelf_kind, shelf_name, path in shelves:
        n = len(load_rows(path))
        pair_n = len(
            build_sampled_pairs(
                n,
                window=int(args.window),
                anchor_count=int(args.anchor_count),
                anchor_depth=int(args.anchor_depth),
            )
        )
        if args.limit_pairs_per_shelf is not None:
            pair_n = min(pair_n, int(args.limit_pairs_per_shelf))
        lines.append(f"- `{shelf_kind}:{shelf_name}`: {n:,} candidates, {pair_n:,} pairs")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
