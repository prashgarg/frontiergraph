from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils import apply_evidence_filters, ensure_parent_dir, load_corpus


def compute_underexplored_pairs(
    corpus_df: pd.DataFrame,
    tau: int = 2,
    cutoff_year: int | None = None,
) -> pd.DataFrame:
    df = corpus_df.copy()
    if cutoff_year is not None:
        df = df[df["year"] <= cutoff_year]
    if df.empty:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "cooc_count",
                "first_year_seen",
                "last_year_seen",
                "gap_bonus",
                "underexplored",
            ]
        )

    paper_nodes = {}
    paper_year = {}
    for row in df.itertuples(index=False):
        pid = str(row.paper_id)
        if pid not in paper_nodes:
            paper_nodes[pid] = set()
            paper_year[pid] = int(row.year)
        paper_nodes[pid].add(str(row.src_code))
        paper_nodes[pid].add(str(row.dst_code))
        paper_year[pid] = min(paper_year[pid], int(row.year))

    records: list[tuple[str, str, int]] = []
    for pid, nodes in paper_nodes.items():
        year = paper_year[pid]
        ordered = sorted(nodes)
        if len(ordered) < 2:
            continue
        for u, v in itertools.combinations(ordered, 2):
            records.append((u, v, year))

    if not records:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "cooc_count",
                "first_year_seen",
                "last_year_seen",
                "gap_bonus",
                "underexplored",
            ]
        )

    pairs = pd.DataFrame(records, columns=["u", "v", "year"])
    out = (
        pairs.groupby(["u", "v"], as_index=False)
        .agg(
            cooc_count=("year", "size"),
            first_year_seen=("year", "min"),
            last_year_seen=("year", "max"),
        )
        .sort_values(["cooc_count", "u", "v"], ascending=[True, True, True])
    )
    out["gap_bonus"] = np.clip((tau - out["cooc_count"]) / float(max(tau, 1)), 0.0, 1.0)
    out["underexplored"] = out["cooc_count"] < tau
    return out.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute underexplored concept-pair gaps.")
    parser.add_argument("--in", required=True, dest="in_path", help="Input corpus parquet")
    parser.add_argument("--out", required=True, dest="out_path", help="Output pairs parquet")
    parser.add_argument("--tau", type=int, default=2, help="Underexplored threshold")
    parser.add_argument("--cutoff_year", type=int, default=None)
    parser.add_argument("--causal_only", action="store_true")
    parser.add_argument("--min_stability", type=float, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corpus_df = load_corpus(args.in_path)
    corpus_df = apply_evidence_filters(
        corpus_df,
        causal_only=args.causal_only,
        min_stability=args.min_stability,
    )
    out_df = compute_underexplored_pairs(corpus_df, tau=args.tau, cutoff_year=args.cutoff_year)
    out_path = Path(args.out_path)
    ensure_parent_dir(out_path)
    out_df.to_parquet(out_path, index=False)
    print(f"Wrote pair features: {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
