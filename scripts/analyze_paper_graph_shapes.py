from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


def quantile(series: pd.Series, q: float) -> float:
    return float(series.quantile(q))


def canonical_undirected_edge(u: str, v: str) -> tuple[str, str]:
    return (u, v) if u <= v else (v, u)


def connected_components(adj: dict[str, set[str]]) -> int:
    seen: set[str] = set()
    comps = 0
    for start in adj:
        if start in seen:
            continue
        comps += 1
        stack = [start]
        seen.add(start)
        while stack:
            node = stack.pop()
            for nbr in adj[node]:
                if nbr not in seen:
                    seen.add(nbr)
                    stack.append(nbr)
    return comps


def bucket_counts(values: pd.Series, buckets: list[tuple[str, tuple[int | None, int | None]]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for label, (lo, hi) in buckets:
        mask = pd.Series(True, index=values.index)
        if lo is not None:
            mask &= values >= lo
        if hi is not None:
            mask &= values <= hi
        out[label] = int(mask.sum())
    return out


def analyze_group(group: pd.DataFrame) -> dict[str, object]:
    raw_nodes = set(group["src_code"]).union(set(group["dst_code"]))

    undir_edges: set[tuple[str, str]] = set()
    dir_edges: set[tuple[str, str]] = set()
    mixed_edges: set[tuple[str, str]] = set()

    undir_adj: dict[str, set[str]] = {node: set() for node in raw_nodes}
    dir_out: dict[str, set[str]] = {node: set() for node in raw_nodes}
    dir_in: dict[str, set[str]] = {node: set() for node in raw_nodes}

    for row in group.itertuples(index=False):
        u = str(row.src_code)
        v = str(row.dst_code)
        if not u or not v:
            continue
        if u == v:
            continue
        mixed_edge = canonical_undirected_edge(u, v)
        mixed_edges.add(mixed_edge)
        undir_adj[u].add(v)
        undir_adj[v].add(u)
        if str(row.edge_kind) == "directed_causal":
            dir_edges.add((u, v))
            dir_out[u].add(v)
            dir_in[v].add(u)
        else:
            undir_edges.add(mixed_edge)

    nodes = {node for node, nbrs in undir_adj.items() if nbrs}
    if not nodes:
        return {
            "paper_id": group["paper_id"].iloc[0],
            "year": int(group["year"].iloc[0]),
            "nodes_total": 0,
            "edges_total": 0,
            "undirected_edges": 0,
            "directed_edges": 0,
            "density_undirected": 0.0,
            "components": 0,
            "largest_component_size": 0,
            "branching_nodes": 0,
            "has_any_shared_node": False,
            "mediator_nodes": 0,
            "directed_path2_count": 0,
            "has_directed_path2": False,
            "is_two_edge_connected_path": False,
            "is_two_directed_edge_path": False,
        }

    adj = {node: undir_adj[node] for node in nodes}
    comps = connected_components(adj)
    largest_component = 0
    seen: set[str] = set()
    for start in adj:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            node = stack.pop()
            size += 1
            for nbr in adj[node]:
                if nbr not in seen:
                    seen.add(nbr)
                    stack.append(nbr)
        largest_component = max(largest_component, size)

    n = len(nodes)
    m = len(mixed_edges)
    density = 0.0 if n < 2 else (2.0 * m) / (n * (n - 1))
    degrees = {node: len(adj[node]) for node in adj}
    branching_nodes = sum(1 for deg in degrees.values() if deg >= 3)
    has_any_shared_node = any(deg >= 2 for deg in degrees.values())

    mediator_nodes = 0
    path2_count = 0
    for node in nodes:
        indeg = len(dir_in[node])
        outdeg = len(dir_out[node])
        if indeg >= 1 and outdeg >= 1:
            mediator_nodes += 1
            for src in dir_in[node]:
                for dst in dir_out[node]:
                    if src != dst:
                        path2_count += 1

    is_two_edge_connected_path = (
        m == 2 and n == 3 and any(len(adj[node]) == 2 for node in adj)
    )
    is_two_directed_edge_path = (
        len(dir_edges) == 2
        and len({u for edge in dir_edges for u in edge}) == 3
        and any(len(dir_in[node]) == 1 and len(dir_out[node]) == 1 for node in nodes)
    )

    return {
        "paper_id": group["paper_id"].iloc[0],
        "year": int(group["year"].iloc[0]),
        "nodes_total": n,
        "edges_total": m,
        "undirected_edges": len(undir_edges),
        "directed_edges": len(dir_edges),
        "density_undirected": density,
        "components": comps,
        "largest_component_size": largest_component,
        "branching_nodes": branching_nodes,
        "has_any_shared_node": has_any_shared_node,
        "mediator_nodes": mediator_nodes,
        "directed_path2_count": path2_count,
        "has_directed_path2": path2_count > 0,
        "is_two_edge_connected_path": is_two_edge_connected_path,
        "is_two_directed_edge_path": is_two_directed_edge_path,
    }


def summarize(per_paper: pd.DataFrame) -> dict[str, object]:
    edge_buckets = [
        ("1", (1, 1)),
        ("2", (2, 2)),
        ("3", (3, 3)),
        ("4-5", (4, 5)),
        ("6-10", (6, 10)),
        ("11+", (11, None)),
    ]
    node_buckets = [
        ("2", (2, 2)),
        ("3", (3, 3)),
        ("4", (4, 4)),
        ("5", (5, 5)),
        ("6-10", (6, 10)),
        ("11+", (11, None)),
    ]

    summary = {
        "paper_count": int(len(per_paper)),
        "year_min": int(per_paper["year"].min()),
        "year_max": int(per_paper["year"].max()),
        "nodes_mean": float(per_paper["nodes_total"].mean()),
        "nodes_median": float(per_paper["nodes_total"].median()),
        "nodes_p90": quantile(per_paper["nodes_total"], 0.9),
        "edges_mean": float(per_paper["edges_total"].mean()),
        "edges_median": float(per_paper["edges_total"].median()),
        "edges_p90": quantile(per_paper["edges_total"], 0.9),
        "directed_edges_mean": float(per_paper["directed_edges"].mean()),
        "directed_edges_median": float(per_paper["directed_edges"].median()),
        "density_undirected_mean": float(per_paper["density_undirected"].mean()),
        "density_undirected_median": float(per_paper["density_undirected"].median()),
        "share_with_any_shared_node": float(per_paper["has_any_shared_node"].mean()),
        "share_with_any_mediator": float((per_paper["mediator_nodes"] > 0).mean()),
        "share_with_directed_path2": float(per_paper["has_directed_path2"].mean()),
        "share_connected_single_component": float((per_paper["components"] == 1).mean()),
        "share_with_branching_node": float((per_paper["branching_nodes"] > 0).mean()),
        "share_two_edge_connected_path_all": float(per_paper["is_two_edge_connected_path"].mean()),
        "share_two_directed_edge_path_all": float(per_paper["is_two_directed_edge_path"].mean()),
        "edge_count_buckets": bucket_counts(per_paper["edges_total"], edge_buckets),
        "node_count_buckets": bucket_counts(per_paper["nodes_total"], node_buckets),
    }

    two_edge = per_paper[per_paper["edges_total"] == 2]
    two_directed = per_paper[per_paper["directed_edges"] == 2]
    summary["two_edge_paper_count"] = int(len(two_edge))
    summary["share_two_edge_connected_path_conditional"] = (
        0.0 if len(two_edge) == 0 else float(two_edge["is_two_edge_connected_path"].mean())
    )
    summary["two_directed_edge_paper_count"] = int(len(two_directed))
    summary["share_two_directed_edge_path_conditional"] = (
        0.0 if len(two_directed) == 0 else float(two_directed["is_two_directed_edge_path"].mean())
    )

    decade = (per_paper["year"] // 10) * 10
    decade_rows: list[dict[str, object]] = []
    for dec, grp in per_paper.assign(decade=decade).groupby("decade", sort=True):
        decade_rows.append(
            {
                "decade": int(dec),
                "paper_count": int(len(grp)),
                "nodes_mean": float(grp["nodes_total"].mean()),
                "nodes_median": float(grp["nodes_total"].median()),
                "edges_mean": float(grp["edges_total"].mean()),
                "edges_median": float(grp["edges_total"].median()),
                "share_with_any_mediator": float((grp["mediator_nodes"] > 0).mean()),
                "share_with_directed_path2": float(grp["has_directed_path2"].mean()),
                "share_two_edge_connected_path_conditional": (
                    0.0
                    if int((grp["edges_total"] == 2).sum()) == 0
                    else float(grp.loc[grp["edges_total"] == 2, "is_two_edge_connected_path"].mean())
                ),
            }
        )
    summary["by_decade"] = decade_rows

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cols = ["paper_id", "year", "src_code", "dst_code", "edge_kind"]
    df = pd.read_parquet(args.input, columns=cols)
    df = df.dropna(subset=["paper_id", "year", "src_code", "dst_code", "edge_kind"]).copy()
    df["paper_id"] = df["paper_id"].astype(str)
    df["src_code"] = df["src_code"].astype(str)
    df["dst_code"] = df["dst_code"].astype(str)
    df["edge_kind"] = df["edge_kind"].astype(str)
    df["year"] = df["year"].astype(int)

    per_paper_rows = [analyze_group(group) for _, group in df.groupby("paper_id", sort=False)]
    per_paper = pd.DataFrame(per_paper_rows)
    summary = summarize(per_paper)

    per_paper.to_parquet(outdir / "paper_graph_shape_per_paper.parquet", index=False)
    pd.DataFrame(summary["by_decade"]).to_parquet(outdir / "paper_graph_shape_by_decade.parquet", index=False)
    with (outdir / "paper_graph_shape_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    key_lines = [
        f"papers={summary['paper_count']}",
        f"nodes_mean={summary['nodes_mean']:.3f}",
        f"nodes_median={summary['nodes_median']:.1f}",
        f"edges_mean={summary['edges_mean']:.3f}",
        f"edges_median={summary['edges_median']:.1f}",
        f"share_with_any_mediator={summary['share_with_any_mediator']:.3f}",
        f"share_with_directed_path2={summary['share_with_directed_path2']:.3f}",
        f"share_two_edge_connected_path_conditional={summary['share_two_edge_connected_path_conditional']:.3f}",
        f"share_two_directed_edge_path_conditional={summary['share_two_directed_edge_path_conditional']:.3f}",
    ]
    print("\n".join(key_lines))


if __name__ == "__main__":
    main()
