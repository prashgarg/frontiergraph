#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research_allocation_v2 import candidate_layer_mask
from src.utils import load_corpus


def _log(message: str) -> None:
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-sources", type=int, default=160)
    parser.add_argument("--sample-targets-per-source", type=int, default=20)
    return parser.parse_args()


def five_year_grid(years: pd.Series) -> list[int]:
    ymin = int(years.min())
    ymax = int(years.max())
    start = ((ymin + 4) // 5) * 5
    end = (ymax // 5) * 5
    return list(range(start, end + 1, 5))


def build_support_edges(corpus_df: pd.DataFrame) -> pd.DataFrame:
    ordered = corpus_df[candidate_layer_mask(corpus_df, "ordered_claim")][["year", "src_code", "dst_code"]].copy()
    contextual = corpus_df[candidate_layer_mask(corpus_df, "contextual_pair")][["year", "src_code", "dst_code"]].copy()

    ordered["u"] = ordered["src_code"].astype(str)
    ordered["v"] = ordered["dst_code"].astype(str)

    contextual["u"] = contextual["src_code"].astype(str)
    contextual["v"] = contextual["dst_code"].astype(str)
    swap = contextual["u"] > contextual["v"]
    left = contextual.loc[swap, "u"].copy()
    contextual.loc[swap, "u"] = contextual.loc[swap, "v"].values
    contextual.loc[swap, "v"] = left.values

    edges = pd.concat(
        [
            ordered[["year", "u", "v"]],
            contextual[["year", "u", "v"]],
        ],
        ignore_index=True,
    )
    edges["year"] = pd.to_numeric(edges["year"], errors="coerce").fillna(0).astype(int)
    edges = edges[edges["u"] != edges["v"]].drop_duplicates(subset=["year", "u", "v"])
    return edges.sort_values(["year", "u", "v"]).reset_index(drop=True)


def sampled_path_stats(
    graph: nx.Graph,
    rng: np.random.Generator,
    sample_sources: int,
    sample_targets_per_source: int,
) -> dict[str, float]:
    if graph.number_of_nodes() <= 1 or graph.number_of_edges() == 0:
        return {
            "mean_sampled_distance": np.nan,
            "share_len_2": np.nan,
            "share_len_3": np.nan,
            "share_len_4": np.nan,
            "share_len_5plus": np.nan,
        }

    component = max(nx.connected_components(graph), key=len)
    if len(component) <= 1:
        return {
            "mean_sampled_distance": np.nan,
            "share_len_2": np.nan,
            "share_len_3": np.nan,
            "share_len_4": np.nan,
            "share_len_5plus": np.nan,
        }
    component_nodes = np.array(sorted(component))
    n_sources = min(sample_sources, len(component_nodes))
    source_nodes = rng.choice(component_nodes, size=n_sources, replace=False)
    lengths: list[int] = []
    for src in source_nodes:
        dist_map = nx.single_source_shortest_path_length(graph, src)
        vals = [d for node, d in dist_map.items() if node != src and d >= 1]
        if not vals:
            continue
        if len(vals) > sample_targets_per_source:
            idx = rng.choice(len(vals), size=sample_targets_per_source, replace=False)
            vals = [vals[i] for i in idx]
        lengths.extend(vals)
    if not lengths:
        return {
            "mean_sampled_distance": np.nan,
            "share_len_2": np.nan,
            "share_len_3": np.nan,
            "share_len_4": np.nan,
            "share_len_5plus": np.nan,
        }
    arr = np.array(lengths, dtype=float)
    return {
        "mean_sampled_distance": float(arr.mean()),
        "share_len_2": float(np.mean(arr == 2)),
        "share_len_3": float(np.mean(arr == 3)),
        "share_len_4": float(np.mean(arr == 4)),
        "share_len_5plus": float(np.mean(arr >= 5)),
    }


def build_stats(
    edges: pd.DataFrame,
    years: list[int],
    sample_sources: int,
    sample_targets_per_source: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for year in years:
        _log(f"[graph-evolution] year={year}: building cumulative graph")
        sub = edges[edges["year"] <= year][["u", "v"]].drop_duplicates()
        g = nx.Graph()
        g.add_edges_from(sub.itertuples(index=False, name=None))
        n = g.number_of_nodes()
        m = g.number_of_edges()
        if n:
            degrees = np.array([deg for _, deg in g.degree()], dtype=float)
            avg_degree = float(degrees.mean())
            p90_degree = float(np.quantile(degrees, 0.9))
            giant = max((len(c) for c in nx.connected_components(g)), default=0)
            giant_share = float(giant) / float(n)
            transitivity = float(nx.transitivity(g))
        else:
            avg_degree = np.nan
            p90_degree = np.nan
            giant_share = np.nan
            transitivity = np.nan
        rows.append(
            {
                "year": year,
                "n_concepts": n,
                "n_support_edges": m,
                "avg_degree": avg_degree,
                "p90_degree": p90_degree,
                "giant_component_share": giant_share,
                "transitivity": transitivity,
                **sampled_path_stats(g, rng, sample_sources, sample_targets_per_source),
            }
        )
        _log(
            f"[graph-evolution] year={year}: nodes={n:,} edges={m:,} "
            f"giant_share={giant_share if n else float('nan'):.4f}"
        )
    return pd.DataFrame(rows)


def plot_stats(df: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12.2, 7.2), constrained_layout=True)
    years = df["year"]

    ax = axes[0, 0]
    ax.plot(years, df["n_concepts"], color="#46627f", lw=2.2, label="Concepts")
    ax2 = ax.twinx()
    ax2.plot(years, df["n_support_edges"], color="#c97255", lw=2.2, label="Support edges")
    ax.set_title("Concepts and support edges", fontsize=10)
    ax.set_ylabel("Concepts", fontsize=9)
    ax2.set_ylabel("Support edges", fontsize=9)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.tick_params(labelsize=8)
    ax2.tick_params(labelsize=8)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [l.get_label() for l in lines], loc="upper left", frameon=False, fontsize=8)

    ax = axes[0, 1]
    ax.plot(years, df["avg_degree"], color="#46627f", lw=2.2, label="Average degree")
    ax.plot(years, df["p90_degree"], color="#c97255", lw=2.2, label="90th percentile degree")
    ax.set_title("Degree growth", fontsize=10)
    ax.set_ylabel("Degree", fontsize=9)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.tick_params(labelsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper left")

    ax = axes[0, 2]
    ax.plot(years, 100 * df["giant_component_share"], color="#3f8f6b", lw=2.2)
    ax.set_title("Giant component share", fontsize=10)
    ax.set_ylabel("Percent of concepts", fontsize=9)
    ax.set_ylim(0, 105)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.tick_params(labelsize=8)

    ax = axes[1, 0]
    ax.stackplot(
        years,
        100 * df["share_len_2"].fillna(0),
        100 * df["share_len_3"].fillna(0),
        100 * df["share_len_4"].fillna(0),
        100 * df["share_len_5plus"].fillna(0),
        labels=["Length 2", "Length 3", "Length 4", "Length 5+"],
        colors=["#46627f", "#78a6c8", "#d8b266", "#c97255"],
        alpha=0.95,
    )
    ax.set_title("Sampled shortest-path mix", fontsize=10)
    ax.set_ylabel("Percent of sampled pairs", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.legend(frameon=False, fontsize=8, loc="upper right")

    ax = axes[1, 1]
    ax.plot(years, df["mean_sampled_distance"], color="#6f5aa5", lw=2.2)
    ax.set_title("Mean sampled distance", fontsize=10)
    ax.set_ylabel("Steps", fontsize=9)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.tick_params(labelsize=8)

    ax = axes[1, 2]
    ax.plot(years, df["transitivity"], color="#aa6f39", lw=2.2)
    ax.set_title("Transitivity", fontsize=10)
    ax.set_ylabel("Transitivity", fontsize=9)
    ax.grid(color="#e1e1e1", lw=0.6)
    ax.tick_params(labelsize=8)

    for ax in axes.ravel():
        ax.set_xlabel("Cumulative graph year", fontsize=9)
        for spine in ["top", "right"]:
            if ax is not axes[0, 0]:
                ax.spines[spine].set_visible(False)

    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def write_summary(df: pd.DataFrame, out_path: Path) -> None:
    start = df.iloc[0]
    end = df.iloc[-1]
    lines = [
        "# Graph evolution summary",
        "",
        f"- Concepts: {int(start['n_concepts']):,} -> {int(end['n_concepts']):,}",
        f"- Support edges: {int(start['n_support_edges']):,} -> {int(end['n_support_edges']):,}",
        f"- Average degree: {start['avg_degree']:.2f} -> {end['avg_degree']:.2f}",
        f"- 90th percentile degree: {start['p90_degree']:.2f} -> {end['p90_degree']:.2f}",
        f"- Giant component share: {100*start['giant_component_share']:.1f}% -> {100*end['giant_component_share']:.1f}%",
        f"- Mean sampled distance: {start['mean_sampled_distance']:.2f} -> {end['mean_sampled_distance']:.2f}",
        f"- Transitivity: {start['transitivity']:.4f} -> {end['transitivity']:.4f}",
    ]
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _log(f"[graph-evolution] out={out}")
    corpus = load_corpus(args.corpus)
    _log(f"[graph-evolution] corpus rows={len(corpus):,}")
    edges = build_support_edges(corpus)
    _log(f"[graph-evolution] support edges rows={len(edges):,}")
    years = five_year_grid(edges["year"])
    _log(f"[graph-evolution] years={years}")
    stats = build_stats(edges, years, args.sample_sources, args.sample_targets_per_source)
    stats.to_csv(out / "graph_evolution_stats.csv", index=False)
    plot_stats(stats, out / "graph_evolution_over_time.png", out / "graph_evolution_over_time.pdf")
    write_summary(stats, out / "summary.md")
    _log(f"[graph-evolution] wrote {out / 'graph_evolution_over_time.pdf'}")


if __name__ == "__main__":
    main()
