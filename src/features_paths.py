from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils import apply_evidence_filters, ensure_parent_dir, load_corpus


def _clip_top(items: list[dict], top_k: int) -> list[dict]:
    if len(items) <= top_k:
        return items
    return sorted(items, key=lambda x: float(x.get("score", 0.0)), reverse=True)[:top_k]


def _candidate_slot(candidates: dict[tuple[str, str], dict], key: tuple[str, str]) -> dict:
    return candidates.setdefault(
        key,
        {
            "path_support_raw": 0.0,
            "hub_penalty": 0.0,
            "mediators": defaultdict(float),
            "paths": [],
        },
    )


def _aggregate_edges(corpus_df: pd.DataFrame) -> pd.DataFrame:
    if corpus_df.empty:
        return pd.DataFrame(columns=["src_code", "dst_code", "edge_weight", "edge_count"])
    agg = (
        corpus_df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(edge_weight=("weight", "sum"), edge_count=("paper_id", "size"))
        .sort_values("edge_weight", ascending=False)
    )
    agg["src_code"] = agg["src_code"].astype(str)
    agg["dst_code"] = agg["dst_code"].astype(str)
    return agg


def compute_path_features(
    corpus_df: pd.DataFrame,
    cutoff_year: int | None = None,
    max_len: int = 2,
    top_k_paths: int = 10,
    top_k_mediators: int = 10,
    max_neighbors_per_mediator: int = 150,
) -> pd.DataFrame:
    df = corpus_df.copy()
    if cutoff_year is not None:
        df = df[df["year"] <= cutoff_year]
    edge_agg = _aggregate_edges(df)
    if edge_agg.empty:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "path_support_raw",
                "mediator_count",
                "hub_penalty",
                "top_mediators_json",
                "top_paths_json",
            ]
        )

    edge_set = set(zip(edge_agg["src_code"], edge_agg["dst_code"]))
    in_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    out_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in edge_agg.itertuples(index=False):
        in_map[str(row.dst_code)].append((str(row.src_code), float(row.edge_weight)))
        out_map[str(row.src_code)].append((str(row.dst_code), float(row.edge_weight)))

    deg_map = {n: len(in_map.get(n, [])) + len(out_map.get(n, [])) for n in set(in_map) | set(out_map)}
    candidates: dict[tuple[str, str], dict] = {}

    # Length-2 support using mediators w: u->w and w->v imply missing u->v.
    for w in sorted(set(in_map.keys()) & set(out_map.keys())):
        ins = sorted(in_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        outs = sorted(out_map[w], key=lambda x: x[1], reverse=True)[:max_neighbors_per_mediator]
        if not ins or not outs:
            continue
        hub_discount = 1.0 / (1.0 + np.log1p(float(deg_map.get(w, 0))))
        for u, in_w in ins:
            for v, out_w in outs:
                if u == v or (u, v) in edge_set:
                    continue
                contrib = float(in_w * out_w)
                support = contrib * hub_discount
                penalty = contrib * (1.0 - hub_discount)
                key = (u, v)
                slot = _candidate_slot(candidates, key)
                slot["path_support_raw"] += support
                slot["hub_penalty"] += penalty
                slot["mediators"][w] += support
                slot["paths"].append({"path": [u, w, v], "score": support, "len": 2})

    # Optional longer path support. Length-3 was the original extension; lengths
    # 4 and 5 use the same bounded DFS with tighter neighbor caps.
    if max_len >= 3:
        if max_len == 3:
            neighbor_cap = min(max_neighbors_per_mediator, 30)
        elif max_len == 4:
            neighbor_cap = min(max_neighbors_per_mediator, 14)
        else:
            neighbor_cap = min(max_neighbors_per_mediator, 10)
        out_limited = {
            src: sorted(targets, key=lambda t: t[1], reverse=True)[:neighbor_cap]
            for src, targets in out_map.items()
        }

        def _record_path(path_nodes: list[str], contrib: float, hub_discount: float) -> None:
            u = path_nodes[0]
            v = path_nodes[-1]
            if u == v or (u, v) in edge_set:
                return
            support = contrib * hub_discount
            penalty = contrib - support
            slot = _candidate_slot(candidates, (u, v))
            slot["path_support_raw"] += support
            slot["hub_penalty"] += penalty
            slot["paths"].append({"path": list(path_nodes), "score": support, "len": len(path_nodes) - 1})
            if len(slot["paths"]) > top_k_paths * 4:
                slot["paths"] = _clip_top(slot["paths"], top_k_paths * 2)

        def _dfs(path_nodes: list[str], weight_prod: float, hub_discount_prod: float) -> None:
            path_len = len(path_nodes) - 1
            current = path_nodes[-1]
            if path_len >= 3:
                _record_path(path_nodes, weight_prod, hub_discount_prod)
            if path_len >= max_len:
                return
            for nxt, edge_w in out_limited.get(current, []):
                if nxt in path_nodes:
                    continue
                next_weight = float(weight_prod * edge_w)
                next_hub_discount = float(hub_discount_prod)
                # The current node becomes an internal node once the path is extended.
                if len(path_nodes) >= 2:
                    next_hub_discount *= 1.0 / (1.0 + np.log1p(float(deg_map.get(current, 0))))
                _dfs(path_nodes + [nxt], next_weight, next_hub_discount)

        for u, uv_targets in out_limited.items():
            for w1, u_w1 in uv_targets:
                _dfs([u, w1], float(u_w1), 1.0)

    rows = []
    for (u, v), payload in candidates.items():
        mediators = [
            {"mediator": m, "score": float(score)}
            for m, score in sorted(payload["mediators"].items(), key=lambda x: x[1], reverse=True)
        ]
        top_paths = _clip_top(payload["paths"], top_k_paths)
        rows.append(
            {
                "u": u,
                "v": v,
                "path_support_raw": float(payload["path_support_raw"]),
                "mediator_count": int(len(payload["mediators"])),
                "hub_penalty": float(payload["hub_penalty"]),
                "top_mediators_json": json.dumps(mediators[:top_k_mediators], ensure_ascii=True),
                "top_paths_json": json.dumps(top_paths, ensure_ascii=True),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "path_support_raw",
                "mediator_count",
                "hub_penalty",
                "top_mediators_json",
                "top_paths_json",
            ]
        )
    out = pd.DataFrame(rows).sort_values("path_support_raw", ascending=False).reset_index(drop=True)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute path-implied missing edge features.")
    parser.add_argument("--in", required=True, dest="in_path", help="Input corpus parquet")
    parser.add_argument("--out", required=True, dest="out_path", help="Output path features parquet")
    parser.add_argument("--max_len", type=int, default=2, choices=[2, 3, 4, 5], help="Max path length")
    parser.add_argument("--cutoff_year", type=int, default=None)
    parser.add_argument("--top_k_paths", type=int, default=10)
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
    out_df = compute_path_features(
        corpus_df,
        cutoff_year=args.cutoff_year,
        max_len=args.max_len,
        top_k_paths=args.top_k_paths,
        top_k_mediators=args.top_k_mediators,
        max_neighbors_per_mediator=args.max_neighbors_per_mediator,
    )
    out_path = Path(args.out_path)
    ensure_parent_dir(out_path)
    out_df.to_parquet(out_path, index=False)
    print(f"Wrote path features: {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
