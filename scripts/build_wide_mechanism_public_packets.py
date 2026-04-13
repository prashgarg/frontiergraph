from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from build_mechanism_public_packets import (
    candidate_nodes_and_pairs,
    clean_text,
    load_relevant_corpus,
    parse_list,
    parse_paths,
    starter_papers_for_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE_A = ROOT / "outputs" / "paper" / "173_wide_mechanism_stage_a" / "wide_mechanism_stage_a_kept.csv"
DEFAULT_CORPUS = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_corpus.parquet"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "174_wide_mechanism_mini_triage_pack"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build wide mechanism packets for mini-model public-site triage.")
    parser.add_argument("--stage-a-kept", default=str(DEFAULT_STAGE_A), dest="stage_a_kept")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), dest="corpus")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-paths", type=int, default=5, dest="max_paths")
    parser.add_argument("--max-starter-papers", type=int, default=3, dest="max_starter_papers")
    return parser.parse_args()


def packet_rows(df: pd.DataFrame, corpus: pd.DataFrame, max_paths: int, max_papers: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = df.sort_values(["stage_a_score", "surface_rank"], ascending=[False, True]).reset_index(drop=True)
    for position, row in enumerate(ordered.to_dict(orient="records"), start=1):
        primary_channels = parse_list(row.get("primary_mediator_labels"))
        top_paths = parse_paths(row.get("top_paths_json"))[:max_paths]
        starter_papers = starter_papers_for_candidate(pd.Series(row), corpus, max_paths, max_papers)
        packet = {
            "pair_key": clean_text(row.get("pair_key")),
            "packet_rank": int(position),
            "horizon": int(row.get("horizon", 10) or 10),
            "available_horizons": parse_list(row.get("available_horizons")),
            "best_horizon": int(row.get("best_horizon", row.get("horizon", 10)) or 10),
            "surface_rank": int(row.get("surface_rank", 0) or 0),
            "reranker_rank": int(row.get("reranker_rank", 0) or 0),
            "transparent_rank": int(row.get("transparent_rank", 0) or 0),
            "source_label": clean_text(row.get("source_label")),
            "target_label": clean_text(row.get("target_label")),
            "source_theme": clean_text(row.get("source_theme")),
            "target_theme": clean_text(row.get("target_theme")),
            "semantic_family_key": clean_text(row.get("semantic_family_key")),
            "theme_pair_key": clean_text(row.get("theme_pair_key")),
            "route_family": clean_text(row.get("route_family")),
            "display_title": clean_text(row.get("display_title")),
            "display_why": clean_text(row.get("display_why")),
            "display_first_step": clean_text(row.get("display_first_step")),
            "baseline_direct_title": clean_text(row.get("baseline_direct_title")),
            "field_shelves_stage_a": parse_list(row.get("field_shelves")),
            "collection_tags_stage_a": parse_list(row.get("collection_tags")),
            "primary_use_case_stage_a": clean_text(row.get("primary_use_case")),
            "stage_a_score": float(row.get("stage_a_score", 0.0) or 0.0),
            "clarity_score_stage_a": float(row.get("clarity_score", 0.0) or 0.0),
            "plausibility_score_stage_a": float(row.get("plausibility_score", 0.0) or 0.0),
            "specificity_score_stage_a": float(row.get("specificity_score", 0.0) or 0.0),
            "endpoint_specificity_score_stage_a": float(row.get("endpoint_specificity_score", 0.0) or 0.0),
            "channel_specificity_score_stage_a": float(row.get("channel_specificity_score", 0.0) or 0.0),
            "primary_channels": primary_channels,
            "top_paths": top_paths,
            "starter_papers": starter_papers,
            "mediator_count": int(row.get("mediator_count", 0) or 0),
            "supporting_path_count": int(row.get("supporting_path_count", 0) or 0),
            "reranker_score": float(row.get("reranker_score", 0.0) or 0.0),
            "transparent_score": float(row.get("transparent_score", 0.0) or 0.0),
            "cooc_count": float(row.get("cooc_count", 0.0) or 0.0),
            "duplicate_family_flag_stage_a": int(row.get("duplicate_family_flag", 0) or 0),
            "semantic_family_duplicate_count_stage_a": int(row.get("semantic_family_duplicate_count", 0) or 0),
            "theme_pair_duplicate_count_stage_a": int(row.get("theme_pair_duplicate_count", 0) or 0),
            "primary_clean_channel_count_stage_a": int(row.get("primary_clean_channel_count", 0) or 0),
            "primary_blocked_channel_count_stage_a": int(row.get("primary_blocked_channel_count", 0) or 0),
            "cross_theme_flag_stage_a": int(row.get("cross_theme_flag", 0) or 0),
            "stage_a_keep_reason": clean_text(row.get("stage_a_keep_reason")),
            "stage_a_drop_reason": clean_text(row.get("stage_a_drop_reason")),
        }
        rows.append(packet)
    return rows


def write_outputs(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "candidate_packets.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_rows: list[dict[str, Any]] = []
    note_lines = [
        "# Wide Mechanism Candidate Packets",
        "",
        "These packets feed the full mini-model public-site triage pass for the widened mechanism pool.",
        "",
    ]
    for row in rows:
        csv_row = dict(row)
        for key in [
            "available_horizons",
            "field_shelves_stage_a",
            "collection_tags_stage_a",
            "primary_channels",
            "top_paths",
            "starter_papers",
        ]:
            csv_row[key] = json.dumps(row[key], ensure_ascii=False)
        csv_rows.append(csv_row)
        note_lines.append(f"## {row['source_label']} -> {row['target_label']}")
        note_lines.append(f"- title seed: {row['display_title']}")
        note_lines.append(f"- Stage A score: {row['stage_a_score']:.3f}")
        note_lines.append(f"- Stage A shelves: {', '.join(row['field_shelves_stage_a'])}")
        note_lines.append(f"- Stage A use cases: {', '.join(row['collection_tags_stage_a'])}")
        note_lines.append(f"- starter papers found: {len(row['starter_papers'])}")
        note_lines.append("")
    pd.DataFrame(csv_rows).to_csv(out_dir / "candidate_packets.csv", index=False)
    (out_dir / "candidate_packets_note.md").write_text("\n".join(note_lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    stage_a_path = Path(args.stage_a_kept)
    corpus_path = Path(args.corpus)
    out_dir = Path(args.out_dir)
    stage_a_df = pd.read_csv(stage_a_path, low_memory=False)
    if args.limit is not None:
        stage_a_df = stage_a_df.head(int(args.limit)).copy()
    node_ids, pair_keys = candidate_nodes_and_pairs(stage_a_df, args.max_paths)
    corpus = load_relevant_corpus(corpus_path, node_ids, pair_keys)
    rows = packet_rows(stage_a_df, corpus, args.max_paths, args.max_starter_papers)
    write_outputs(rows, out_dir)
    print(f"Wrote {out_dir / 'candidate_packets.csv'}")
    print(f"Wrote {out_dir / 'candidate_packets.jsonl'}")


if __name__ == "__main__":
    main()
