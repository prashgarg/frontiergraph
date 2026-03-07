from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.utils import candidate_id, ensure_dir, ensure_parent_dir, load_corpus, parse_json_list


def _build_edge_paper_lookup(corpus_df: pd.DataFrame) -> dict[tuple[str, str], list[dict]]:
    needed = ["src_code", "dst_code", "paper_id", "title", "year"]
    edge_papers = (
        corpus_df[needed]
        .sort_values(["src_code", "dst_code", "year"], ascending=[True, True, False])
        .drop_duplicates(subset=["src_code", "dst_code", "paper_id"])
    )
    lookup: dict[tuple[str, str], list[dict]] = {}
    for row in edge_papers.itertuples(index=False):
        key = (str(row.src_code), str(row.dst_code))
        lookup.setdefault(key, []).append(
            {
                "paper_id": str(row.paper_id),
                "title": str(row.title),
                "year": int(row.year),
            }
        )
    return lookup


def build_explanation_tables(
    corpus_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    top_k_papers_per_edge: int = 3,
) -> dict[str, pd.DataFrame]:
    candidate_mediators_rows: list[dict] = []
    candidate_paths_rows: list[dict] = []
    candidate_papers_rows: list[dict] = []
    candidate_neighborhood_rows: list[dict] = []

    edge_papers = _build_edge_paper_lookup(corpus_df)
    out_neigh = (
        corpus_df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(weight=("weight", "sum"), count=("paper_id", "size"))
        .sort_values(["src_code", "weight"], ascending=[True, False])
    )
    in_neigh = (
        corpus_df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(weight=("weight", "sum"), count=("paper_id", "size"))
        .sort_values(["dst_code", "weight"], ascending=[True, False])
    )
    out_map: dict[str, list[dict]] = {}
    for row in out_neigh.itertuples(index=False):
        out_map.setdefault(str(row.src_code), []).append(
            {"neighbor": str(row.dst_code), "weight": float(row.weight), "count": int(row.count)}
        )
    in_map: dict[str, list[dict]] = {}
    for row in in_neigh.itertuples(index=False):
        in_map.setdefault(str(row.dst_code), []).append(
            {"neighbor": str(row.src_code), "weight": float(row.weight), "count": int(row.count)}
        )

    for cand in candidates_df.itertuples(index=False):
        u = str(cand.u)
        v = str(cand.v)
        cid = candidate_id(u, v)
        mediators = parse_json_list(getattr(cand, "top_mediators_json", "[]"))
        for rank, med in enumerate(mediators, start=1):
            candidate_mediators_rows.append(
                {
                    "candidate_u": u,
                    "candidate_v": v,
                    "candidate_id": cid,
                    "rank": rank,
                    "mediator": str(med.get("mediator", "")),
                    "score": float(med.get("score", 0.0)),
                }
            )

        paths = parse_json_list(getattr(cand, "top_paths_json", "[]"))
        for rank, p in enumerate(paths, start=1):
            node_path = [str(x) for x in p.get("path", [])]
            if len(node_path) < 3:
                continue
            path_text = " -> ".join(node_path)
            path_len = int(p.get("len", len(node_path) - 1))
            path_score = float(p.get("score", 0.0))
            candidate_paths_rows.append(
                {
                    "candidate_u": u,
                    "candidate_v": v,
                    "candidate_id": cid,
                    "rank": rank,
                    "path_len": path_len,
                    "path_score": path_score,
                    "path_text": path_text,
                    "path_nodes_json": json.dumps(node_path, ensure_ascii=True),
                }
            )
            for i in range(len(node_path) - 1):
                a, b = node_path[i], node_path[i + 1]
                for p_rank, paper in enumerate(edge_papers.get((a, b), [])[:top_k_papers_per_edge], start=1):
                    candidate_papers_rows.append(
                        {
                            "candidate_u": u,
                            "candidate_v": v,
                            "candidate_id": cid,
                            "path_rank": rank,
                            "edge_src": a,
                            "edge_dst": b,
                            "paper_rank": p_rank,
                            "paper_id": paper["paper_id"],
                            "title": paper["title"],
                            "year": paper["year"],
                        }
                    )

        candidate_neighborhood_rows.append(
            {
                "candidate_u": u,
                "candidate_v": v,
                "candidate_id": cid,
                "top_out_neighbors_u_json": json.dumps(out_map.get(u, [])[:5], ensure_ascii=True),
                "top_in_neighbors_v_json": json.dumps(in_map.get(v, [])[:5], ensure_ascii=True),
            }
        )

    return {
        "candidate_mediators": pd.DataFrame(candidate_mediators_rows),
        "candidate_paths": pd.DataFrame(candidate_paths_rows),
        "candidate_supporting_papers": pd.DataFrame(candidate_papers_rows),
        "candidate_neighborhoods": pd.DataFrame(candidate_neighborhood_rows),
    }


def build_idea_brief_markdown(
    candidate_row: pd.Series,
    mediators_df: pd.DataFrame,
    paths_df: pd.DataFrame,
    papers_df: pd.DataFrame,
    neighborhood_row: pd.Series | None = None,
) -> str:
    u = str(candidate_row["u"])
    v = str(candidate_row["v"])
    lines = [
        f"# Idea Brief: {u} -> {v}",
        "",
        "## Score Decomposition",
        f"- score: {float(candidate_row.get('score', 0.0)):.4f}",
        f"- path_support_norm: {float(candidate_row.get('path_support_norm', 0.0)):.4f}",
        f"- gap_bonus: {float(candidate_row.get('gap_bonus', 0.0)):.4f}",
        f"- motif_bonus_norm: {float(candidate_row.get('motif_bonus_norm', 0.0)):.4f}",
        f"- hub_penalty: {float(candidate_row.get('hub_penalty', 0.0)):.4f}",
        "",
        "## Top Mediators",
    ]
    if mediators_df.empty:
        lines.append("- none")
    else:
        for row in mediators_df.head(5).itertuples(index=False):
            lines.append(f"- {row.mediator}: {float(row.score):.4f}")
    lines.append("")
    lines.append("## Top Supporting Paths")
    if paths_df.empty:
        lines.append("- none")
    else:
        for row in paths_df.head(5).itertuples(index=False):
            lines.append(f"- {row.path_text} (score={float(row.path_score):.4f})")
    lines.append("")
    lines.append("## Example Supporting Papers")
    if papers_df.empty:
        lines.append("- none")
    else:
        for row in papers_df.head(10).itertuples(index=False):
            lines.append(f"- [{row.paper_id}] ({int(row.year)}) {row.title} [{row.edge_src}->{row.edge_dst}]")
    if neighborhood_row is not None:
        lines.extend(
            [
                "",
                "## Local Neighborhood Snapshot",
                f"- top outgoing neighbors of {u}: {neighborhood_row.get('top_out_neighbors_u_json', '[]')}",
                f"- top incoming neighbors of {v}: {neighborhood_row.get('top_in_neighbors_v_json', '[]')}",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build explanation bundle tables from candidates.")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corpus_df = load_corpus(args.corpus)
    candidates_df = pd.read_parquet(args.candidates)
    tables = build_explanation_tables(corpus_df, candidates_df)
    outdir = Path(args.outdir)
    ensure_dir(outdir)
    for name, df in tables.items():
        out_path = outdir / f"{name}.parquet"
        ensure_parent_dir(out_path)
        df.to_parquet(out_path, index=False)
        print(f"Wrote {name}: {out_path} ({len(df)} rows)")


if __name__ == "__main__":
    main()
