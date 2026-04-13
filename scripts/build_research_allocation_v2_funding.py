from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYBRID_PAPERS = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_papers.parquet"
DEFAULT_HYBRID_CORPUS = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_corpus.parquet"
DEFAULT_EXTRACTION_DB = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_extraction_v2"
    / "fwci_core150_adj150"
    / "merged"
    / "fwci_core150_adj150_extractions.sqlite"
)
DEFAULT_ENRICHED_DB = ROOT / "data" / "processed" / "openalex" / "published_enriched" / "openalex_published_enriched.sqlite"
DEFAULT_OUT_DIR = ROOT / "data" / "processed" / "research_allocation_v2"
DEFAULT_PAPER_OUT = ROOT / "outputs" / "paper" / "03_funding"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach OpenAlex grant/funder coverage to the research-allocation v2 benchmark papers.")
    parser.add_argument("--hybrid-papers", default=str(DEFAULT_HYBRID_PAPERS))
    parser.add_argument("--hybrid-corpus", default=str(DEFAULT_HYBRID_CORPUS))
    parser.add_argument("--extraction-db", default=str(DEFAULT_EXTRACTION_DB))
    parser.add_argument("--enriched-db", default=str(DEFAULT_ENRICHED_DB))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--paper-out-dir", default=str(DEFAULT_PAPER_OUT))
    return parser.parse_args()


def _read_sql(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, conn)


def load_paper_map(extraction_db: Path) -> pd.DataFrame:
    conn = sqlite3.connect(f"file:{extraction_db}?mode=ro", uri=True)
    try:
        return _read_sql(
            conn,
            """
            SELECT custom_id AS paper_id, openalex_work_id
            FROM works
            """,
        )
    finally:
        conn.close()


def load_openalex_funding(enriched_db: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(f"file:{enriched_db}?mode=ro", uri=True)
    try:
        works_base = _read_sql(
            conn,
            """
            SELECT work_id, publication_year, cited_by_count, fwci, source_display_name,
                   primary_topic_display_name, primary_subfield_display_name, is_retracted
            FROM works_base
            """,
        )
        works_grants = _read_sql(
            conn,
            """
            SELECT work_id, funder, funder_display_name, award_id
            FROM works_grants
            """,
        )
    finally:
        conn.close()
    return works_base, works_grants


def build_benchmark_flags(hybrid_corpus: pd.DataFrame) -> pd.DataFrame:
    directed = hybrid_corpus[hybrid_corpus["edge_kind"] == "directed_causal"][["paper_id"]].drop_duplicates()
    directed["has_directed_causal_edge"] = True
    undirected = hybrid_corpus[hybrid_corpus["edge_kind"] == "undirected_noncausal"][["paper_id"]].drop_duplicates()
    undirected["has_undirected_noncausal_edge"] = True
    return directed.merge(undirected, on="paper_id", how="outer").fillna(False)


def summarize_funders(benchmark_grants: pd.DataFrame, out_dir: Path) -> None:
    summary = (
        benchmark_grants
        .groupby(["funder", "funder_display_name"], as_index=False)
        .agg(benchmark_papers=("paper_id", "nunique"), grant_mentions=("paper_id", "size"))
        .sort_values(["benchmark_papers", "grant_mentions"], ascending=[False, False])
        .reset_index(drop=True)
    )
    summary.to_csv(out_dir / "top_funders.csv", index=False)


def main() -> None:
    args = parse_args()
    hybrid_papers = pd.read_parquet(Path(args.hybrid_papers))
    hybrid_corpus = pd.read_parquet(Path(args.hybrid_corpus))
    paper_map = load_paper_map(Path(args.extraction_db))
    works_base, works_grants = load_openalex_funding(Path(args.enriched_db))

    out_dir = Path(args.out_dir)
    paper_out_dir = Path(args.paper_out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_out_dir.mkdir(parents=True, exist_ok=True)

    grant_summary = (
        works_grants.groupby("work_id", as_index=False)
        .agg(
            grant_count=("award_id", "size"),
            unique_funder_count=("funder", pd.Series.nunique),
            first_funder=("funder_display_name", "first"),
            funder_display_names=("funder_display_name", lambda s: json.dumps(sorted(set([str(v) for v in s if str(v).strip()]))[:10])),
            funder_ids=("funder", lambda s: json.dumps(sorted(set([str(v) for v in s if str(v).strip()]))[:10])),
        )
    )

    benchmark_flags = build_benchmark_flags(hybrid_corpus)
    enriched = (
        hybrid_papers.merge(paper_map, on="paper_id", how="left")
        .merge(works_base, left_on="openalex_work_id", right_on="work_id", how="left")
        .merge(grant_summary, left_on="openalex_work_id", right_on="work_id", how="left", suffixes=("", "_grant"))
        .merge(benchmark_flags, on="paper_id", how="left")
    )
    enriched["has_grant"] = enriched["grant_count"].fillna(0).astype(int) > 0
    enriched["has_directed_causal_edge"] = enriched["has_directed_causal_edge"].fillna(False).astype(bool)
    enriched["has_undirected_noncausal_edge"] = enriched["has_undirected_noncausal_edge"].fillna(False).astype(bool)
    enriched["grant_count"] = enriched["grant_count"].fillna(0).astype(int)
    enriched["unique_funder_count"] = enriched["unique_funder_count"].fillna(0).astype(int)

    enriched_out = out_dir / "hybrid_papers_funding.parquet"
    enriched.to_parquet(enriched_out, index=False)

    overall = pd.DataFrame(
        [
            {
                "benchmark_papers": int(enriched["paper_id"].nunique()),
                "papers_with_grants": int(enriched["has_grant"].sum()),
                "grant_coverage_rate": float(enriched["has_grant"].mean()),
                "papers_with_directed_causal_edges": int(enriched["has_directed_causal_edge"].sum()),
                "directed_causal_papers_with_grants": int(
                    enriched.loc[enriched["has_directed_causal_edge"], "has_grant"].sum()
                ),
                "directed_causal_grant_coverage_rate": float(
                    enriched.loc[enriched["has_directed_causal_edge"], "has_grant"].mean()
                ),
                "papers_with_undirected_noncausal_edges": int(enriched["has_undirected_noncausal_edge"].sum()),
                "undirected_noncausal_papers_with_grants": int(
                    enriched.loc[enriched["has_undirected_noncausal_edge"], "has_grant"].sum()
                ),
                "undirected_noncausal_grant_coverage_rate": float(
                    enriched.loc[enriched["has_undirected_noncausal_edge"], "has_grant"].mean()
                ),
            }
        ]
    )
    overall.to_csv(paper_out_dir / "funding_overall_summary.csv", index=False)

    by_source = (
        enriched.groupby("source", as_index=False)
        .agg(
            benchmark_papers=("paper_id", "nunique"),
            papers_with_grants=("has_grant", "sum"),
            avg_fwci=("fwci", "mean"),
            median_fwci=("fwci", "median"),
            avg_cited_by_count=("cited_by_count", "mean"),
        )
        .sort_values("benchmark_papers", ascending=False)
        .reset_index(drop=True)
    )
    by_source["grant_coverage_rate"] = by_source["papers_with_grants"] / by_source["benchmark_papers"].clip(lower=1)
    by_source.to_csv(paper_out_dir / "funding_by_source.csv", index=False)

    by_year = (
        enriched.groupby("year", as_index=False)
        .agg(
            benchmark_papers=("paper_id", "nunique"),
            papers_with_grants=("has_grant", "sum"),
        )
        .sort_values("year")
        .reset_index(drop=True)
    )
    by_year["grant_coverage_rate"] = by_year["papers_with_grants"] / by_year["benchmark_papers"].clip(lower=1)
    by_year.to_csv(paper_out_dir / "funding_by_year.csv", index=False)

    benchmark_grants = (
        enriched[["paper_id", "openalex_work_id"]]
        .dropna()
        .merge(works_grants, left_on="openalex_work_id", right_on="work_id", how="inner")
    )
    summarize_funders(benchmark_grants, paper_out_dir)

    manifest = {
        "benchmark_papers": int(enriched["paper_id"].nunique()),
        "papers_with_openalex_match": int(enriched["openalex_work_id"].notna().sum()),
        "papers_with_grants": int(enriched["has_grant"].sum()),
        "grant_coverage_rate": float(enriched["has_grant"].mean()),
        "directed_causal_papers": int(enriched["has_directed_causal_edge"].sum()),
        "directed_causal_papers_with_grants": int(enriched.loc[enriched["has_directed_causal_edge"], "has_grant"].sum()),
        "undirected_noncausal_papers": int(enriched["has_undirected_noncausal_edge"].sum()),
        "undirected_noncausal_papers_with_grants": int(enriched.loc[enriched["has_undirected_noncausal_edge"], "has_grant"].sum()),
        "notes": "Grant coverage is derived from OpenAlex works_grants via openalex_work_id join.",
    }
    (paper_out_dir / "funding_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
