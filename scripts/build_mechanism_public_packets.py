from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCREENED = ROOT / "outputs" / "paper" / "168_mechanism_public_screen" / "screened_candidates.csv"
DEFAULT_CORPUS = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_corpus.parquet"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "169_mechanism_public_llm"
MAX_PATHS = 5
MAX_STARTER_PAPERS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build richer candidate packets for public mechanism-question LLM triage.")
    parser.add_argument("--screened", default=str(DEFAULT_SCREENED), dest="screened")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), dest="corpus")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--max-paths", type=int, default=MAX_PATHS, dest="max_paths")
    parser.add_argument("--max-starter-papers", type=int, default=MAX_STARTER_PAPERS, dest="max_starter_papers")
    return parser.parse_args()


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
      return [clean_text(item) for item in raw if clean_text(item)]
    text = clean_text(raw)
    if not text:
      return []
    for parser in (json.loads, ast.literal_eval):
        try:
            value = parser(text)
            if isinstance(value, list):
                return [clean_text(item) for item in value if clean_text(item)]
        except Exception:
            continue
    return []


def parse_paths(raw: Any) -> list[dict[str, Any]]:
    text = clean_text(raw)
    if not text:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            value = parser(text)
            if isinstance(value, list):
                out: list[dict[str, Any]] = []
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    out.append(item)
                return out
        except Exception:
            continue
    return []


def unordered_pair_key(left: str, right: str) -> str:
    a = clean_text(left)
    b = clean_text(right)
    return "__".join(sorted((a, b)))


def candidate_nodes_and_pairs(df: pd.DataFrame, max_paths: int) -> tuple[set[str], set[str]]:
    node_ids: set[str] = set()
    pair_keys: set[str] = set()
    for row in df.itertuples(index=False):
        for path in parse_paths(getattr(row, "top_paths_json", ""))[:max_paths]:
            codes = [clean_text(item) for item in path.get("path", []) if clean_text(item)]
            node_ids.update(codes)
            for left, right in zip(codes, codes[1:]):
                pair_keys.add(unordered_pair_key(left, right))
    return node_ids, pair_keys


def load_relevant_corpus(corpus_path: Path, node_ids: set[str], pair_keys: set[str]) -> pd.DataFrame:
    cols = [
        "paper_id",
        "year",
        "title",
        "authors",
        "venue",
        "src_code",
        "dst_code",
        "src_label",
        "dst_label",
        "edge_kind",
        "causal_presentation",
        "evidence_type",
        "stability",
    ]
    corpus = pd.read_parquet(corpus_path, columns=cols)
    corpus["src_code"] = corpus["src_code"].astype(str)
    corpus["dst_code"] = corpus["dst_code"].astype(str)
    corpus = corpus[corpus["src_code"].isin(node_ids) & corpus["dst_code"].isin(node_ids)].copy()
    corpus["edge_pair_key"] = corpus.apply(lambda row: unordered_pair_key(row["src_code"], row["dst_code"]), axis=1)
    corpus = corpus[corpus["edge_pair_key"].isin(pair_keys)].copy()
    return corpus


def starter_papers_for_candidate(row: pd.Series, corpus: pd.DataFrame, max_paths: int, max_papers: int) -> list[dict[str, Any]]:
    path_rows = parse_paths(row.get("top_paths_json"))
    edge_rank: dict[str, int] = {}
    for path_rank, path in enumerate(path_rows[:max_paths], start=1):
        codes = [clean_text(item) for item in path.get("path", []) if clean_text(item)]
        for left, right in zip(codes, codes[1:]):
            pair_key = unordered_pair_key(left, right)
            edge_rank[pair_key] = min(edge_rank.get(pair_key, path_rank), path_rank)
    if not edge_rank:
        return []
    local = corpus[corpus["edge_pair_key"].isin(edge_rank)].copy()
    if local.empty:
        return []
    local["edge_path_rank"] = local["edge_pair_key"].map(edge_rank).astype(int)
    grouped = (
        local.groupby(["paper_id", "title", "year", "venue", "authors"], dropna=False)
        .agg(
            matched_edge_count=("edge_pair_key", "nunique"),
            best_path_rank=("edge_path_rank", "min"),
            mean_stability=("stability", "mean"),
            evidence_types=("evidence_type", lambda s: sorted({clean_text(v) for v in s if clean_text(v)})),
        )
        .reset_index()
        .sort_values(
            ["matched_edge_count", "best_path_rank", "year", "mean_stability"],
            ascending=[False, True, False, False],
        )
    )
    out: list[dict[str, Any]] = []
    for paper in grouped.head(max_papers).itertuples(index=False):
        out.append(
            {
                "paper_id": clean_text(paper.paper_id),
                "title": clean_text(paper.title),
                "year": int(paper.year) if pd.notna(paper.year) else None,
                "venue": clean_text(paper.venue),
                "authors": clean_text(paper.authors),
                "matched_edge_count": int(paper.matched_edge_count),
                "best_path_rank": int(paper.best_path_rank),
                "mean_stability": round(float(paper.mean_stability or 0.0), 4),
                "evidence_types": list(paper.evidence_types or []),
            }
        )
    return out


def packet_rows(df: pd.DataFrame, corpus: pd.DataFrame, max_paths: int, max_papers: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        primary_channels = parse_list(row.get("primary_labels") or row.get("primary_mediator_labels"))
        top_paths = parse_paths(row.get("top_paths_json"))[:max_paths]
        starter_papers = starter_papers_for_candidate(pd.Series(row), corpus, max_paths, max_papers)
        packet = {
            "pair_key": clean_text(row.get("pair_key")),
            "horizon": int(row.get("horizon", 10) or 10),
            "shortlist_rank": int(row.get("shortlist_rank", 0) or 0),
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
            "primary_channels": primary_channels,
            "top_paths": top_paths,
            "starter_papers": starter_papers,
            "mediator_count": int(row.get("mediator_count", 0) or 0),
            "supporting_path_count": int(row.get("supporting_path_count", 0) or 0),
            "reranker_score": float(row.get("reranker_score", 0.0) or 0.0),
            "transparent_score": float(row.get("transparent_score", 0.0) or 0.0),
            "source_target_norm_key": "__".join((normalize_text(row.get("source_label")), normalize_text(row.get("target_label")))),
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
        "# Mechanism Candidate Packets",
        "",
        "These packets are the input to the public-site mechanism-question triage pass.",
        "",
    ]
    for row in rows:
        csv_row = dict(row)
        csv_row["primary_channels"] = json.dumps(row["primary_channels"], ensure_ascii=False)
        csv_row["top_paths"] = json.dumps(row["top_paths"], ensure_ascii=False)
        csv_row["starter_papers"] = json.dumps(row["starter_papers"], ensure_ascii=False)
        csv_rows.append(csv_row)
        note_lines.append(f"## {row['source_label']} -> {row['target_label']}")
        note_lines.append(f"- title seed: {row['display_title']}")
        note_lines.append(f"- channels: {', '.join(row['primary_channels'])}")
        note_lines.append(f"- starter papers found: {len(row['starter_papers'])}")
        note_lines.append("")
    pd.DataFrame(csv_rows).to_csv(out_dir / "candidate_packets.csv", index=False)
    (out_dir / "candidate_packets_note.md").write_text("\n".join(note_lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    screened_path = Path(args.screened)
    corpus_path = Path(args.corpus)
    out_dir = Path(args.out_dir)
    screened = pd.read_csv(screened_path)
    node_ids, pair_keys = candidate_nodes_and_pairs(screened, args.max_paths)
    corpus = load_relevant_corpus(corpus_path, node_ids, pair_keys)
    rows = packet_rows(screened, corpus, args.max_paths, args.max_starter_papers)
    write_outputs(rows, out_dir)
    print(f"Wrote {out_dir / 'candidate_packets.csv'}")
    print(f"Wrote {out_dir / 'candidate_packets.jsonl'}")


if __name__ == "__main__":
    main()
