from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from src.explain import build_explanation_tables
from src.features_pairs import compute_underexplored_pairs
from src.utils import ensure_parent_dir, load_config, load_corpus


def _build_nodes_table(corpus_df: pd.DataFrame) -> pd.DataFrame:
    src_nodes = corpus_df[["src_code", "src_label"]].rename(columns={"src_code": "code", "src_label": "label"})
    dst_nodes = corpus_df[["dst_code", "dst_label"]].rename(columns={"dst_code": "code", "dst_label": "label"})
    nodes = pd.concat([src_nodes, dst_nodes], ignore_index=True)
    nodes["code"] = nodes["code"].astype(str)
    nodes["label"] = nodes["label"].fillna(nodes["code"]).astype(str)
    nodes = nodes.drop_duplicates(subset=["code"])
    return nodes


def _build_papers_table(corpus_df: pd.DataFrame) -> pd.DataFrame:
    papers = (
        corpus_df[["paper_id", "year", "title", "authors", "venue", "source"]]
        .drop_duplicates(subset=["paper_id"])
        .sort_values("year")
    )
    return papers


def _build_edges_table(corpus_df: pd.DataFrame) -> pd.DataFrame:
    return corpus_df[
        [
            "paper_id",
            "year",
            "src_code",
            "dst_code",
            "relation_type",
            "evidence_type",
            "is_causal",
            "weight",
            "stability",
        ]
    ].copy()


def write_sqlite(
    corpus_path: str | Path,
    candidates_path: str | Path,
    out_path: str | Path,
    config_path: str | Path = "config/config.yaml",
) -> None:
    config = load_config(config_path)
    tau = int(config.get("features", {}).get("tau", 2))
    top_k_papers_per_edge = int(config.get("features", {}).get("top_k_supporting_papers_per_edge", 3))

    corpus_df = load_corpus(corpus_path)
    candidates_df = pd.read_parquet(candidates_path)
    expl_tables = build_explanation_tables(
        corpus_df=corpus_df,
        candidates_df=candidates_df,
        top_k_papers_per_edge=top_k_papers_per_edge,
    )
    underexplored_pairs = compute_underexplored_pairs(corpus_df, tau=tau)

    nodes_df = _build_nodes_table(corpus_df)
    papers_df = _build_papers_table(corpus_df)
    edges_df = _build_edges_table(corpus_df)

    out_path = Path(out_path)
    ensure_parent_dir(out_path)
    conn = sqlite3.connect(out_path)
    try:
        nodes_df.to_sql("nodes", conn, if_exists="replace", index=False)
        papers_df.to_sql("papers", conn, if_exists="replace", index=False)
        edges_df.to_sql("edges", conn, if_exists="replace", index=False)
        candidates_df.to_sql("candidates", conn, if_exists="replace", index=False)
        underexplored_pairs.to_sql("underexplored_pairs", conn, if_exists="replace", index=False)
        expl_tables["candidate_mediators"].to_sql("candidate_mediators", conn, if_exists="replace", index=False)
        expl_tables["candidate_paths"].to_sql("candidate_paths", conn, if_exists="replace", index=False)
        expl_tables["candidate_supporting_papers"].to_sql(
            "candidate_supporting_papers",
            conn,
            if_exists="replace",
            index=False,
        )
        # Alias table name used by the app contract.
        expl_tables["candidate_supporting_papers"].to_sql("candidate_papers", conn, if_exists="replace", index=False)
        expl_tables["candidate_neighborhoods"].to_sql("candidate_neighborhoods", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_code ON nodes(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_u ON candidates(u)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_v ON candidates(v)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_underexplored_u ON underexplored_pairs(u)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_underexplored_v ON underexplored_pairs(v)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_mediators_uv ON candidate_mediators(candidate_u, candidate_v)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidate_paths_uv ON candidate_paths(candidate_u, candidate_v)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidate_papers_uv ON candidate_papers(candidate_u, candidate_v)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_neighborhoods_uv ON candidate_neighborhoods(candidate_u, candidate_v)"
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Wrote SQLite store: {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Store corpus + candidates + explanations in SQLite.")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", required=True, dest="out_path")
    parser.add_argument("--config", default="config/config.yaml", dest="config_path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_sqlite(args.corpus, args.candidates, args.out_path, config_path=args.config_path)


if __name__ == "__main__":
    main()

