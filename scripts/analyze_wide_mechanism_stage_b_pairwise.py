from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "outputs" / "paper" / "178_wide_mechanism_stage_b_pairwise_pack"
DEFAULT_RUN = ROOT / "outputs" / "paper" / "179_wide_mechanism_stage_b_pairwise_run"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "180_wide_mechanism_stage_b_pairwise_analysis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Stage B pairwise shelf reranking responses.")
    parser.add_argument("--pack-dir", default=str(DEFAULT_PACK), dest="pack_dir")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN), dest="run_dir")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    return parser.parse_args()


def extract_text_payload(response: dict[str, Any]) -> str | None:
    for output in response.get("output", []):
        if output.get("type") != "message":
            continue
        for item in output.get("content", []):
            if item.get("type") == "output_text":
                return item.get("text")
    return None


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
    except (ValueError, SyntaxError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def parse_responses(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            text = extract_text_payload(raw["response"])
            if not text:
                failures.append({"custom_id": raw.get("custom_id"), "error": "missing_output_text"})
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                failures.append({"custom_id": raw.get("custom_id"), "error": f"json_decode_error: {exc}"})
                continue
            rows.append(
                {
                    "custom_id": str(raw.get("custom_id") or ""),
                    "source_name": str(raw.get("source_name") or ""),
                    "model": raw["response"].get("model"),
                    "parsed": parsed,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(failures)


def mapped_preference(pref: str, *, swapped: bool) -> str:
    pref = str(pref or "tie")
    if not swapped:
        return pref
    if pref == "A":
        return "B"
    if pref == "B":
        return "A"
    return "tie"


def stable_preference(values: list[str]) -> str:
    clean = [v for v in values if v in {"A", "B", "tie"}]
    non_ties = [v for v in clean if v != "tie"]
    if not non_ties:
        return "tie"
    if all(v == non_ties[0] for v in non_ties):
        return non_ties[0]
    return "tie"


def main() -> None:
    args = parse_args()
    pack_dir = Path(args.pack_dir)
    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pair_meta = pd.read_csv(pack_dir / "pairwise_rows.csv")
    candidate_rows = pd.read_csv(pack_dir / "candidate_rows.csv", low_memory=False)
    candidate_rows["field_shelves"] = candidate_rows["field_shelves"].apply(parse_json_list)
    candidate_rows["collection_tags"] = candidate_rows["collection_tags"].apply(parse_json_list)
    candidate_rows["priority_rank"] = candidate_rows["priority_rank"].fillna(3)
    candidate_rows["issue_rank"] = candidate_rows["issue_rank"].fillna(2)

    parsed_df, failures_df = parse_responses(run_dir / "responses.jsonl")
    expanded_rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        payload = dict(row.parsed)
        variant = str(payload.get("variant") or "")
        pair_id = str(payload.get("pair_id") or "")
        swapped = "swapped" in variant or "swapped" in str(row.custom_id)
        expanded_rows.append(
            {
                "custom_id": row.custom_id,
                "source_name": row.source_name,
                "pair_id": pair_id,
                "variant": variant,
                "swapped": swapped,
                "preferred_candidate_raw": str(payload.get("preferred_candidate") or "tie"),
                "preferred_candidate": mapped_preference(str(payload.get("preferred_candidate") or "tie"), swapped=swapped),
                "question_clarity_preference": mapped_preference(str(payload.get("question_clarity_preference") or "tie"), swapped=swapped),
                "mechanism_specificity_preference": mapped_preference(str(payload.get("mechanism_specificity_preference") or "tie"), swapped=swapped),
                "first_step_preference": mapped_preference(str(payload.get("first_step_preference") or "tie"), swapped=swapped),
                "credibility_preference": mapped_preference(str(payload.get("credibility_preference") or "tie"), swapped=swapped),
                "confidence": int(payload.get("confidence") or 0),
                "reason": str(payload.get("reason") or ""),
            }
        )
    expanded = pd.DataFrame(expanded_rows)

    pair_summary_rows: list[dict[str, Any]] = []
    for pair_id, sub in expanded.groupby("pair_id", sort=False):
        prefs = list(sub["preferred_candidate"])
        clarity = list(sub["question_clarity_preference"])
        mechanism = list(sub["mechanism_specificity_preference"])
        first_step = list(sub["first_step_preference"])
        credibility = list(sub["credibility_preference"])
        pair_summary_rows.append(
            {
                "pair_id": pair_id,
                "n_responses": int(len(sub)),
                "stable_preference": stable_preference(prefs),
                "stable_question_clarity": stable_preference(clarity),
                "stable_mechanism_specificity": stable_preference(mechanism),
                "stable_first_step": stable_preference(first_step),
                "stable_credibility": stable_preference(credibility),
                "mean_confidence": float(sub["confidence"].mean()) if len(sub) else float("nan"),
                "direct_pref": next((p for p, s in zip(sub["preferred_candidate"], sub["swapped"]) if not s), "tie"),
                "swapped_pref_mapped": next((p for p, s in zip(sub["preferred_candidate"], sub["swapped"]) if s), "tie"),
            }
        )
    pair_summary = pd.DataFrame(pair_summary_rows).merge(pair_meta, on="pair_id", how="left")

    pair_summary.to_csv(out_dir / "pairwise_consensus.csv", index=False)
    expanded.to_csv(out_dir / "pairwise_expanded_votes.csv", index=False)
    failures_df.to_csv(out_dir / "pairwise_failures.csv", index=False)

    ranking_rows: list[pd.DataFrame] = []
    edge_df = pair_summary[pair_summary["stable_preference"].isin(["A", "B"])].copy()
    for (shelf_kind, shelf_name), candidates in candidate_rows.groupby(["shelf_kind", "shelf_name"], sort=True):
        shelf = candidates.drop_duplicates(subset=["pair_key"]).copy()
        score_map = {str(cid): 0.0 for cid in shelf["pair_key"]}
        local_edges = edge_df[(edge_df["shelf_kind"] == shelf_kind) & (edge_df["shelf_name"] == shelf_name)]
        for edge in local_edges.itertuples(index=False):
            a_id = str(edge.a_pair_key)
            b_id = str(edge.b_pair_key)
            if a_id not in score_map or b_id not in score_map:
                continue
            if edge.stable_preference == "A":
                score_map[a_id] += 1.0
                score_map[b_id] -= 1.0
            elif edge.stable_preference == "B":
                score_map[b_id] += 1.0
                score_map[a_id] -= 1.0
        shelf["pairwise_copeland_score"] = shelf["pair_key"].map(score_map).astype(float)
        shelf = shelf.sort_values(
            [
                "pairwise_copeland_score",
                "priority_rank",
                "issue_rank",
                "mechanism_plausibility",
                "question_object_clarity",
                "endpoint_specificity",
                "packet_rank",
            ],
            ascending=[False, True, True, False, False, False, True],
        ).reset_index(drop=True)
        shelf["stage_b_rank"] = range(1, len(shelf) + 1)
        ranking_rows.append(shelf)

    ranking = pd.concat(ranking_rows, ignore_index=True) if ranking_rows else pd.DataFrame()
    ranking.to_csv(out_dir / "stage_b_shelf_rankings.csv", index=False)

    top_rows: list[dict[str, Any]] = []
    for (shelf_kind, shelf_name), sub in ranking.groupby(["shelf_kind", "shelf_name"], sort=True):
        top = sub.head(20).copy()
        top_rows.extend(top.to_dict(orient="records"))
    pd.DataFrame(top_rows).to_csv(out_dir / "stage_b_top20_by_shelf.csv", index=False)

    lines = [
        "# Wide Mechanism Stage B Pairwise Analysis",
        "",
        f"- parsed response rows: {len(parsed_df):,}",
        f"- failed parses: {len(failures_df):,}",
        f"- unique pair ids: {pair_summary['pair_id'].nunique():,}",
        "",
        "## Pairwise consensus",
        "",
    ]
    for pref, count in pair_summary["stable_preference"].value_counts().items():
        lines.append(f"- {pref}: {int(count):,}")

    lines.extend(["", "## Top shelves", ""])
    for (shelf_kind, shelf_name), sub in ranking.groupby(["shelf_kind", "shelf_name"], sort=True):
        lines.append(f"- `{shelf_kind}:{shelf_name}`")
        for row in sub.head(8).itertuples(index=False):
            lines.append(
                f"  - rank {int(row.stage_b_rank)} | {row.display_title} | copeland={float(row.pairwise_copeland_score):.1f} | issue={row.primary_issue}"
            )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
