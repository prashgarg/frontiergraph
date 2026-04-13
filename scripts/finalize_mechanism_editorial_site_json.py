from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from analyze_llm_screening_v2_run import _parse_responses


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEEP = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "rewrite_ready_candidates.csv"
DEFAULT_REWRITE_RUN = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "rewrite_run"
DEFAULT_EXISTING = ROOT / "site" / "src" / "content" / "mechanism-editorial-opportunities.json"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "mechanism_editorial_opportunities.generated.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize site JSON for mechanism-editorial opportunities after rewrite responses are approved.")
    parser.add_argument("--keep", default=str(DEFAULT_KEEP), dest="keep_csv")
    parser.add_argument("--rewrite-run", default=str(DEFAULT_REWRITE_RUN), dest="rewrite_run")
    parser.add_argument("--existing", default=str(DEFAULT_EXISTING), dest="existing_json")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_json")
    return parser.parse_args()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "mechanism-question"


def parse_listish(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            continue
    return []


def load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): value for key, value in payload.items()}


def expand_rewrites(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if not str(row.source_name).startswith("rewrite_requests_gpt54"):
            continue
        payload = dict(row.parsed)
        rows.append(
            {
                "pair_key": payload.get("pair_key"),
                "question_title": payload.get("question_title"),
                "short_why": payload.get("short_why"),
                "first_next_step": payload.get("first_next_step"),
                "who_its_for": payload.get("who_its_for"),
                "field_shelves": payload.get("field_shelves", []),
                "collection_tags": payload.get("collection_tags", []),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    keep_df = pd.read_csv(Path(args.keep_csv))
    for key in ["primary_channels"]:
        if key in keep_df.columns:
            keep_df[key] = keep_df[key].fillna("[]").apply(parse_listish)

    parsed_df, failures_df = _parse_responses(Path(args.rewrite_run) / "responses.jsonl")
    rewrite_df = expand_rewrites(parsed_df)
    if not failures_df.empty:
        raise SystemExit("Rewrite parse failures present. Fix those before finalizing site JSON.")

    merged = keep_df.merge(rewrite_df, on="pair_key", how="inner", validate="one_to_one")
    existing = load_existing(Path(args.existing_json))

    out: dict[str, dict[str, Any]] = {}
    for display_order, row in enumerate(merged.to_dict(orient="records"), start=1):
        pair_key = str(row["pair_key"])
        entry = {
            "pair_key": pair_key,
            "question_title": row["question_title"],
            "short_why": row["short_why"],
            "first_next_step": row["first_next_step"],
            "who_its_for": row["who_its_for"],
            "display_order": display_order,
            "field_shelves": row["field_shelves"],
            "collection_tags": row["collection_tags"],
            "question_family": f"mechanism-{slugify(row['question_title'])}",
            "graph_query": row["source_label"],
            "graph_family": "mechanism",
            "source_label": row["source_label"],
            "target_label": row["target_label"],
            "channel_labels": row.get("primary_channels", []),
            "route_family": row["route_family"],
        }
        if pair_key in existing:
            entry["display_order"] = existing[pair_key].get("display_order", display_order)
        out[pair_key] = entry

    Path(args.out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out_json}")


if __name__ == "__main__":
    main()
