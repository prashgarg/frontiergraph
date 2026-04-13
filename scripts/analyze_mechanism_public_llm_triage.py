from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from analyze_llm_screening_v2_run import _parse_responses


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "candidate_packets.csv"
DEFAULT_RUN_DIR = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "triage_run"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "169_mechanism_public_llm"
DEFAULT_REWRITE_REQUESTS = ROOT / "outputs" / "paper" / "169_mechanism_public_llm" / "rewrite_requests_gpt54.jsonl"


PRIORITY_MAP = {"high": 3, "medium": 2, "low": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze public mechanism-question triage responses and prepare kept sets plus rewrite-ready packets.")
    parser.add_argument("--packets", default=str(DEFAULT_PACKETS), dest="packets")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), dest="run_dir")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--rewrite-limit", type=int, default=24, dest="rewrite_limit")
    parser.add_argument("--rewrite-requests", default=str(DEFAULT_REWRITE_REQUESTS), dest="rewrite_requests")
    return parser.parse_args()


def load_packets(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for key in ["primary_channels", "top_paths", "starter_papers"]:
        df[key] = df[key].fillna("[]").apply(json.loads)
    return df


def expand_triage(parsed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in parsed_df.itertuples(index=False):
        if row.source_name != "triage_requests":
            continue
        payload = dict(row.parsed)
        rows.append(
            {
                "custom_id": row.custom_id,
                "pair_key": payload.get("pair_key"),
                "keep_for_public_site": payload.get("keep_for_public_site"),
                "plausible_mechanism_question": payload.get("plausible_mechanism_question"),
                "reader_facing": payload.get("reader_facing"),
                "too_generic": payload.get("too_generic"),
                "alias_like_duplicate_risk": payload.get("alias_like_duplicate_risk"),
                "primary_issue": payload.get("primary_issue"),
                "suggested_priority": payload.get("suggested_priority"),
                "confidence": payload.get("confidence"),
                "reason": payload.get("reason"),
                "parse_mode": row.parse_mode,
                "response_id": row.response_id,
                "model": row.model,
            }
        )
    return pd.DataFrame(rows)


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["priority_score"] = out["suggested_priority"].map(PRIORITY_MAP).fillna(0).astype(int)
    out["keep_candidate_initial"] = (
        out["keep_for_public_site"].astype(bool)
        & out["plausible_mechanism_question"].astype(bool)
        & out["reader_facing"].astype(bool)
        & ~out["too_generic"].astype(bool)
        & (out["confidence"].fillna(0).astype(float) >= 3.0)
    )
    out["dedupe_bucket"] = out["semantic_family_key"].fillna("").replace("", pd.NA).fillna(out["source_target_norm_key"])
    out = out.sort_values(
        [
            "keep_candidate_initial",
            "priority_score",
            "confidence",
            "shortlist_rank",
            "surface_rank",
        ],
        ascending=[False, False, False, True, True],
    ).reset_index(drop=True)

    keep_flags: list[bool] = []
    seen_buckets: set[str] = set()
    for row in out.itertuples(index=False):
        if not bool(row.keep_candidate_initial):
            keep_flags.append(False)
            continue
        bucket = str(row.dedupe_bucket)
        if bucket in seen_buckets:
            keep_flags.append(False)
            continue
        seen_buckets.add(bucket)
        keep_flags.append(True)
    out["keep_after_dedupe"] = keep_flags
    return out


def write_summary(df: pd.DataFrame, out_path: Path) -> None:
    total = len(df)
    initial_keep = int(df["keep_candidate_initial"].sum())
    final_keep = int(df["keep_after_dedupe"].sum())
    issue_counts = df["primary_issue"].fillna("missing").value_counts().to_dict()
    lines = [
        "# Mechanism Public Triage Summary",
        "",
        f"- candidates scored: `{total}`",
        f"- candidates kept before dedupe: `{initial_keep}`",
        f"- candidates kept after dedupe: `{final_keep}`",
        "",
        "## Primary issues",
    ]
    for key, value in issue_counts.items():
        lines.append(f"- `{key}`: `{value}`")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_rewrite_preview(df: pd.DataFrame, out_dir: Path, rewrite_limit: int) -> None:
    kept = df[df["keep_after_dedupe"]].copy().sort_values(
        ["priority_score", "confidence", "shortlist_rank"],
        ascending=[False, False, True],
    )
    kept["rewrite_order"] = range(1, len(kept) + 1)
    kept.to_csv(out_dir / "triage_kept_candidates.csv", index=False)
    dropped = df[~df["keep_after_dedupe"]].copy().sort_values(
        ["keep_candidate_initial", "priority_score", "confidence", "shortlist_rank"],
        ascending=[False, False, False, True],
    )
    dropped.to_csv(out_dir / "triage_dropped_candidates.csv", index=False)
    kept.head(rewrite_limit).to_csv(out_dir / "rewrite_ready_candidates.csv", index=False)


def write_filtered_rewrite_requests(
    rewrite_requests_path: Path,
    rewrite_ready_pairs: set[str],
    out_path: Path,
) -> None:
    with rewrite_requests_path.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    filtered = [
        row
        for row in rows
        if str(row.get("custom_id", "")).removeprefix("mechanism-rewrite-") in rewrite_ready_pairs
    ]
    with out_path.open("w", encoding="utf-8") as handle:
        for row in filtered:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    packets_path = Path(args.packets)
    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    packets = load_packets(packets_path)
    parsed_df, failures_df = _parse_responses(run_dir / "responses.jsonl")
    triage = expand_triage(parsed_df)
    merged = packets.merge(triage, on="pair_key", how="left", validate="one_to_one")
    merged = apply_rules(merged)

    merged.to_csv(out_dir / "triage_all_candidates.csv", index=False)
    if not failures_df.empty:
        failures_df.to_csv(out_dir / "triage_parse_failures.csv", index=False)
    write_summary(merged, out_dir / "triage_summary.md")
    write_rewrite_preview(merged, out_dir, args.rewrite_limit)
    rewrite_ready = pd.read_csv(out_dir / "rewrite_ready_candidates.csv")
    write_filtered_rewrite_requests(
        Path(args.rewrite_requests),
        set(rewrite_ready["pair_key"].astype(str)),
        out_dir / "rewrite_requests_gpt54_filtered.jsonl",
    )
    print(f"Wrote {out_dir / 'triage_all_candidates.csv'}")
    print(f"Wrote {out_dir / 'triage_kept_candidates.csv'}")
    print(f"Wrote {out_dir / 'triage_dropped_candidates.csv'}")
    print(f"Wrote {out_dir / 'rewrite_ready_candidates.csv'}")
    print(f"Wrote {out_dir / 'rewrite_requests_gpt54_filtered.jsonl'}")


if __name__ == "__main__":
    main()
