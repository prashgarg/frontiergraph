from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def canonical_undirected_edge(u: str, v: str) -> tuple[str, str]:
    return (u, v) if u <= v else (v, u)


def any_open_triad(adj: dict[str, set[str]]) -> bool:
    for center, nbrs in adj.items():
        nbr_list = list(nbrs)
        if len(nbr_list) < 2:
            continue
        for i in range(len(nbr_list)):
            a = nbr_list[i]
            for j in range(i + 1, len(nbr_list)):
                b = nbr_list[j]
                if b not in adj[a]:
                    return True
    return False


def any_triangle(adj: dict[str, set[str]]) -> bool:
    for a, nbrs in adj.items():
        nbr_list = list(nbrs)
        for i in range(len(nbr_list)):
            b = nbr_list[i]
            if b <= a:
                continue
            for j in range(i + 1, len(nbr_list)):
                c = nbr_list[j]
                if c <= b:
                    continue
                if c in adj[b]:
                    return True
    return False


def any_directed_chain3(out_map: dict[str, set[str]]) -> bool:
    for a, bs in out_map.items():
        for b in bs:
            for c in out_map[b]:
                if c in {a, b}:
                    continue
                for d in out_map[c]:
                    if d not in {a, b, c}:
                        return True
    return False


def any_parallel_mediator(out_map: dict[str, set[str]]) -> bool:
    for src, mids in out_map.items():
        mids = [m for m in mids if m != src]
        if len(mids) < 2:
            continue
        target_counts: dict[str, int] = {}
        for mid in mids:
            for dst in out_map[mid]:
                if dst in {src, mid}:
                    continue
                target_counts[dst] = target_counts.get(dst, 0) + 1
                if target_counts[dst] >= 2:
                    return True
    return False


def any_directed_triangle(out_map: dict[str, set[str]]) -> bool:
    for a, bs in out_map.items():
        for b in bs:
            for c in out_map[b]:
                if c not in {a, b} and c in out_map[a]:
                    return True
    return False


def analyze_group(group: pd.DataFrame) -> dict[str, object]:
    paper_id = str(group["paper_id"].iloc[0])
    year = int(group["year"].iloc[0])
    title = str(group["title"].iloc[0])

    nodes = set(group["src_code"]).union(set(group["dst_code"]))
    undir_adj: dict[str, set[str]] = {node: set() for node in nodes}
    out_map: dict[str, set[str]] = {node: set() for node in nodes}
    in_map: dict[str, set[str]] = {node: set() for node in nodes}
    undirected_edges: set[tuple[str, str]] = set()
    directed_edges: set[tuple[str, str]] = set()

    for row in group.itertuples(index=False):
        u = str(row.src_code)
        v = str(row.dst_code)
        if not u or not v or u == v:
            continue
        undir_adj[u].add(v)
        undir_adj[v].add(u)
        undirected_edges.add(canonical_undirected_edge(u, v))
        if str(row.edge_kind) == "directed_causal":
            out_map[u].add(v)
            in_map[v].add(u)
            directed_edges.add((u, v))

    nodes = {node for node, nbrs in undir_adj.items() if nbrs}
    undir_adj = {node: undir_adj[node] for node in nodes}
    out_map = {node: out_map[node] for node in nodes}
    in_map = {node: in_map[node] for node in nodes}

    any_branch = any(len(nbrs) >= 3 for nbrs in undir_adj.values())
    any_mediator = any(len(in_map[node]) >= 1 and len(out_map[node]) >= 1 for node in nodes)
    any_fork = any(len(out_map[node]) >= 2 for node in nodes)
    any_collider = any(len(in_map[node]) >= 2 for node in nodes)

    return {
        "paper_id": paper_id,
        "year": year,
        "title": title,
        "nodes_total": len(nodes),
        "edges_total": len(undirected_edges),
        "directed_edges": len(directed_edges),
        "motif_undir_open_triad": any_open_triad(undir_adj),
        "motif_undir_triangle": any_triangle(undir_adj),
        "motif_undir_branch": any_branch,
        "motif_directed_chain2": any_mediator,
        "motif_directed_chain3": any_directed_chain3(out_map),
        "motif_directed_fork": any_fork,
        "motif_directed_collider": any_collider,
        "motif_directed_parallel_mediator": any_parallel_mediator(out_map),
        "motif_directed_triangle": any_directed_triangle(out_map),
    }


def build_summary(df: pd.DataFrame) -> dict[str, object]:
    motif_cols = [col for col in df.columns if col.startswith("motif_")]
    summary: dict[str, object] = {
        "paper_count": int(len(df)),
        "motif_shares_all": {},
        "motif_shares_directed_subset": {},
        "examples": {},
    }

    directed_subset = df[df["directed_edges"] > 0].copy()
    summary["directed_subset_paper_count"] = int(len(directed_subset))

    for col in motif_cols:
        summary["motif_shares_all"][col] = float(df[col].mean())
        summary["motif_shares_directed_subset"][col] = (
            0.0 if len(directed_subset) == 0 else float(directed_subset[col].mean())
        )
        examples = df[df[col]].sort_values(["year", "paper_id"]).head(5)[["year", "paper_id", "title"]]
        summary["examples"][col] = examples.to_dict(orient="records")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cols = ["paper_id", "year", "title", "src_code", "dst_code", "edge_kind"]
    df = pd.read_parquet(args.input, columns=cols)
    df = df.dropna(subset=cols).copy()
    df["paper_id"] = df["paper_id"].astype(str)
    df["src_code"] = df["src_code"].astype(str)
    df["dst_code"] = df["dst_code"].astype(str)
    df["title"] = df["title"].astype(str)
    df["edge_kind"] = df["edge_kind"].astype(str)
    df["year"] = df["year"].astype(int)

    per_paper_rows = [analyze_group(group) for _, group in df.groupby("paper_id", sort=False)]
    per_paper = pd.DataFrame(per_paper_rows)
    summary = build_summary(per_paper)

    per_paper.to_parquet(outdir / "paper_graph_motif_per_paper.parquet", index=False)
    with (outdir / "paper_graph_motif_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    for col, share in summary["motif_shares_all"].items():
        print(f"{col}={share:.4f}")


if __name__ == "__main__":
    main()
