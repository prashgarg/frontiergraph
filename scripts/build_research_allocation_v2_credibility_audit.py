from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYBRID_CORPUS = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_corpus.parquet"
DEFAULT_PAPER_OUT = ROOT / "outputs" / "paper" / "04_credibility"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize edge-quality distributions in the research-allocation v2 hybrid corpus.")
    parser.add_argument("--hybrid-corpus", default=str(DEFAULT_HYBRID_CORPUS))
    parser.add_argument("--out-dir", default=str(DEFAULT_PAPER_OUT))
    return parser.parse_args()


def stability_band(value: float) -> str:
    if pd.isna(value):
        return "missing"
    if value < 0.4:
        return "low"
    if value < 0.7:
        return "mid"
    return "high"


def main() -> None:
    args = parse_args()
    corpus = pd.read_parquet(Path(args.hybrid_corpus))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = corpus.copy()
    corpus["stability_band"] = corpus["stability"].map(stability_band)

    pair_counts = (
        corpus[["edge_kind", "src_code", "dst_code"]]
        .drop_duplicates()
        .groupby("edge_kind", as_index=False)
        .agg(distinct_pairs=("src_code", "size"))
    )
    by_kind = (
        corpus.groupby("edge_kind", as_index=False)
        .agg(
            rows=("paper_id", "size"),
            papers=("paper_id", "nunique"),
            mean_stability=("stability", "mean"),
            median_stability=("stability", "median"),
            explicit_causal_share=("causal_presentation", lambda s: float((s == "explicit_causal").mean())),
            implicit_causal_share=("causal_presentation", lambda s: float((s == "implicit_causal").mean())),
            unclear_causal_share=("causal_presentation", lambda s: float((s == "unclear").mean())),
        )
        .merge(pair_counts, on="edge_kind", how="left")
        .sort_values("rows", ascending=False)
        .reset_index(drop=True)
    )
    by_kind.to_csv(out_dir / "edge_quality_by_kind.csv", index=False)

    by_method = (
        corpus.groupby(["edge_kind", "evidence_type"], as_index=False)
        .agg(
            rows=("paper_id", "size"),
            papers=("paper_id", "nunique"),
            mean_stability=("stability", "mean"),
            explicit_causal_share=("causal_presentation", lambda s: float((s == "explicit_causal").mean())),
        )
        .sort_values(["edge_kind", "rows"], ascending=[True, False])
        .reset_index(drop=True)
    )
    by_method.to_csv(out_dir / "edge_quality_by_method.csv", index=False)

    by_band = (
        corpus.groupby(["edge_kind", "stability_band"], as_index=False)
        .agg(rows=("paper_id", "size"), papers=("paper_id", "nunique"))
        .sort_values(["edge_kind", "rows"], ascending=[True, False])
        .reset_index(drop=True)
    )
    by_band.to_csv(out_dir / "edge_quality_by_stability_band.csv", index=False)

    manifest = {
        "rows": int(len(corpus)),
        "papers": int(corpus["paper_id"].nunique()),
        "directed_causal_rows": int((corpus["edge_kind"] == "directed_causal").sum()),
        "undirected_noncausal_rows": int((corpus["edge_kind"] == "undirected_noncausal").sum()),
        "mean_stability_directed_causal": float(corpus.loc[corpus["edge_kind"] == "directed_causal", "stability"].mean()),
        "mean_stability_undirected_noncausal": float(corpus.loc[corpus["edge_kind"] == "undirected_noncausal", "stability"].mean()),
        "note": "This is a corpus-quality audit of benchmark inputs, not yet a weighted future-edge evaluation.",
    }
    (out_dir / "credibility_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
