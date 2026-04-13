from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
FRONTIER_PATH = ROOT / "outputs" / "paper" / "78_current_reranked_frontier_path_to_direct" / "current_reranked_frontier.csv"
CORPUS_PATH = ROOT / "data" / "processed" / "research_allocation_v2_2_effective" / "hybrid_corpus.parquet"
OUT_PATH = ROOT / "paper" / "real_neighborhood.png"


COLORS = {
    "bg": "#FBFAF6",
    "undirected": "#C8CDD7",
    "directed": "#2E74C9",
    "source": "#E7B07A",
    "target": "#C62839",
    "mediator": "#F3F4F7",
    "node_edge": "#3A4658",
    "text": "#263445",
    "muted": "#5E677D",
}


def wrap_label(s: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(str(s), width=width, break_long_words=False))


def pick_example() -> tuple[pd.Series, list[dict]]:
    df = pd.read_csv(FRONTIER_PATH, low_memory=False)
    row = (
        df[(df["u_label"] == "Trade Liberalization") & (df["v_label"] == "R&D")]
        .sort_values(["surface_rank", "frontier_rank"])
        .iloc[0]
    )
    paths = json.loads(row["top_paths_json"])[:6]
    return row, paths


def load_local_edges(node_codes: list[str]) -> pd.DataFrame:
    cols = ["src_code", "dst_code", "src_label", "dst_label", "edge_kind", "weight"]
    df = pd.read_parquet(CORPUS_PATH, columns=cols)
    return df[df["src_code"].isin(node_codes) & df["dst_code"].isin(node_codes)].copy()


def build_graph(row: pd.Series, paths: list[dict], edge_df: pd.DataFrame):
    node_order = [row["u"], row["v"]] + [p["path"][1] for p in paths]
    node_order = list(dict.fromkeys(node_order))
    labels = {row["u"]: row["u_label"], row["v"]: row["v_label"]}
    for p in paths:
        labels[p["path"][1]] = p["path_labels"][1]

    G = nx.Graph()
    for n in node_order:
        kind = "mediator"
        if n == row["u"]:
            kind = "source"
        elif n == row["v"]:
            kind = "target"
        G.add_node(n, label=labels[n], kind=kind)

    # Use actual local edges from the current live graph.
    undir_weights: dict[tuple[str, str], float] = {}
    dir_weights: dict[tuple[str, str], float] = {}
    for _, e in edge_df.iterrows():
        a, b = e["src_code"], e["dst_code"]
        w = float(e["weight"]) if pd.notna(e["weight"]) else 1.0
        if e["edge_kind"] == "undirected_noncausal":
            key = tuple(sorted((a, b)))
            undir_weights[key] = undir_weights.get(key, 0.0) + w
        elif e["edge_kind"] == "directed_causal":
            key = (a, b)
            dir_weights[key] = dir_weights.get(key, 0.0) + w

    # Keep the real local neighborhood readable.
    for (a, b), w in sorted(undir_weights.items(), key=lambda kv: kv[1], reverse=True)[:12]:
        G.add_edge(a, b, weight=w)

    return G, labels, dir_weights, undir_weights


def draw():
    row, paths = pick_example()
    node_codes = [row["u"], row["v"]] + [p["path"][1] for p in paths]
    node_codes = list(dict.fromkeys(node_codes))
    edge_df = load_local_edges(node_codes)
    G, labels, dir_weights, undir_weights = build_graph(row, paths, edge_df)

    pos = {
        row["u"]: (-1.55, -0.02),
        row["v"]: (1.58, -0.02),
        "jel:D24:Productivity": (-0.38, 1.0),
        "jel:I:Welfare": (-0.98, 0.38),
        "https://openalex.org/T10393": (0.32, 0.98),
        "jel:O34:Intellectual Property Rights": (0.92, 0.33),
        "https://openalex.org/keywords/market-competition": (0.2, -0.74),
        "https://openalex.org/keywords/industrial-pollution": (-0.96, -0.86),
    }

    fig, ax = plt.subplots(figsize=(8.8, 5.9), facecolor=COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])
    ax.axis("off")

    # Undirected contextual support.
    for (a, b), w in sorted(undir_weights.items(), key=lambda kv: kv[1], reverse=True)[:11]:
        if a not in pos or b not in pos:
            continue
        width = 0.55 + 1.9 * min(w / 90.0, 1.0)
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=[(a, b)],
            width=width,
            edge_color=COLORS["undirected"],
            alpha=0.58,
            ax=ax,
        )

    # Directed causal edges.
    for (a, b), w in sorted(dir_weights.items(), key=lambda kv: kv[1], reverse=True):
        if a not in pos or b not in pos:
            continue
        width = 1.0 + 2.0 * min(w / 18.0, 1.0)
        patch = plt.matplotlib.patches.FancyArrowPatch(
            posA=pos[a],
            posB=pos[b],
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=width,
            color=COLORS["directed"],
            alpha=0.9,
            connectionstyle="arc3,rad=0.08" if pos[a][1] <= pos[b][1] else "arc3,rad=-0.08",
            shrinkA=10,
            shrinkB=10,
            zorder=2,
        )
        ax.add_patch(patch)

    # Nodes.
    node_sizes = {}
    for n in G.nodes:
        node_sizes[n] = 460
        if G.nodes[n]["kind"] in {"source", "target"}:
            node_sizes[n] = 680

    for kind, face in [("mediator", COLORS["mediator"]), ("source", COLORS["source"]), ("target", COLORS["target"])]:
        nodes = [n for n, d in G.nodes(data=True) if d["kind"] == kind]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=nodes,
            node_size=[node_sizes[n] for n in nodes],
            node_color=face,
            edgecolors=COLORS["node_edge"],
            linewidths=1.2 if kind == "mediator" else 1.5,
            ax=ax,
        )

    # Labels with light halo, not boxes.
    label_offsets = {
        row["u"]: (-0.02, 0.16),
        row["v"]: (0.02, 0.16),
        "jel:D24:Productivity": (0.0, 0.17),
        "jel:I:Welfare": (-0.08, 0.15),
        "https://openalex.org/T10393": (0.1, 0.14),
        "jel:O34:Intellectual Property Rights": (0.16, 0.12),
        "https://openalex.org/keywords/market-competition": (0.22, 0.02),
        "https://openalex.org/keywords/industrial-pollution": (-0.06, 0.13),
    }
    for n, (x, y) in pos.items():
        dx, dy = label_offsets.get(n, (0.0, 0.11))
        txt = ax.text(
            x + dx,
            y + dy,
            wrap_label(labels[n], width=17),
            fontsize=10.8 if G.nodes[n]["kind"] in {"source", "target"} else 9.4,
            ha="center",
            va="center" if n == "https://openalex.org/keywords/market-competition" else "bottom",
            color=COLORS["text"],
            zorder=5,
        )
        txt.set_path_effects([pe.withStroke(linewidth=3, foreground=COLORS["bg"])])

    legend_handles = [
        Line2D([0], [0], color=COLORS["directed"], lw=2.2, label="Directed causal edge"),
        Line2D([0], [0], color=COLORS["undirected"], lw=1.8, label="Undirected contextual"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["source"], markeredgecolor=COLORS["node_edge"], markersize=9, label="Candidate endpoints"),
    ]
    leg = ax.legend(
        handles=legend_handles,
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#D5D8DE",
        fontsize=9.4,
    )
    leg.get_frame().set_alpha(0.96)

    ax.set_xlim(-2.1, 2.15)
    ax.set_ylim(-1.25, 1.35)
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT_PATH, dpi=300, facecolor=COLORS["bg"], bbox_inches="tight", pad_inches=0.02)


if __name__ == "__main__":
    draw()
