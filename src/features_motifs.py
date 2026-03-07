from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils import apply_evidence_filters, ensure_parent_dir, load_corpus


def compute_motif_features(
    corpus_df: pd.DataFrame,
    cutoff_year: int | None = None,
    top_k_mediators: int = 10,
    max_neighbors_per_mediator: int = 150,
) -> pd.DataFrame:
    df = corpus_df.copy()
    if cutoff_year is not None:
        df = df[df["year"] <= cutoff_year]
    if df.empty:
        return pd.DataFrame(columns=["u", "v", "motif_count", "motif_bonus_raw", "top_motif_mediators_json"])

    edge_agg = (
        df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(edge_count=("paper_id", "size"), edge_weight=("weight", "sum"))
        .sort_values("edge_count", ascending=False)
    )
    edge_set = set(zip(edge_agg["src_code"], edge_agg["dst_code"]))
    in_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    out_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in edge_agg.itertuples(index=False):
        in_map[str(row.dst_code)].append((str(row.src_code), float(row.edge_count)))
        out_map[str(row.src_code)].append((str(row.dst_code), float(row.edge_count)))

    candidates: dict[tuple[str, str], dict] = {}
    for w in sorted(set(in_map) & set(out_map)):
        ins = sorted(in_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        outs = sorted(out_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        for u, in_count in ins:
            for v, out_count in outs:
                if u == v or (u, v) in edge_set:
                    continue
                contrib = float(np.sqrt(in_count * out_count))
                key = (u, v)
                slot = candidates.setdefault(
                    key,
                    {"motif_count": 0, "motif_bonus_raw": 0.0, "mediators": defaultdict(float)},
                )
                slot["motif_count"] += 1
                slot["motif_bonus_raw"] += contrib
                slot["mediators"][w] += contrib

    rows = []
    for (u, v), payload in candidates.items():
        mediator_list = [
            {"mediator": m, "score": float(s)}
            for m, s in sorted(payload["mediators"].items(), key=lambda x: x[1], reverse=True)[:top_k_mediators]
        ]
        rows.append(
            {
                "u": u,
                "v": v,
                "motif_count": int(payload["motif_count"]),
                "motif_bonus_raw": float(payload["motif_bonus_raw"]),
                "top_motif_mediators_json": json.dumps(mediator_list, ensure_ascii=True),
            }
        )

    if not rows:
        return pd.DataFrame(columns=["u", "v", "motif_count", "motif_bonus_raw", "top_motif_mediators_json"])
    return pd.DataFrame(rows).sort_values("motif_bonus_raw", ascending=False).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute motif-completion features for missing edges.")
    parser.add_argument("--in", required=True, dest="in_path", help="Input corpus parquet")
    parser.add_argument("--out", required=True, dest="out_path", help="Output motif parquet")
    parser.add_argument("--cutoff_year", type=int, default=None)
    parser.add_argument("--top_k_mediators", type=int, default=10)
    parser.add_argument("--max_neighbors_per_mediator", type=int, default=150)
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
    out_df = compute_motif_features(
        corpus_df,
        cutoff_year=args.cutoff_year,
        top_k_mediators=args.top_k_mediators,
        max_neighbors_per_mediator=args.max_neighbors_per_mediator,
    )
    out_path = Path(args.out_path)
    ensure_parent_dir(out_path)
    out_df.to_parquet(out_path, index=False)
    print(f"Wrote motif features: {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
