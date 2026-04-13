from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data/production/frontiergraph_concept_public/concept_graph_hard.sqlite"
ALIAS_PATH = REPO_ROOT / "data/processed/ontology_vnext_proto_v1/context_alias_table.csv"
FIG_DIR = REPO_ROOT / "context_extension_paper/figures"
TAB_DIR = REPO_ROOT / "context_extension_paper/tables"


def load_alias_map() -> dict[str, str]:
    alias = pd.read_csv(ALIAS_PATH)
    alias = alias[alias["raw_value"].notna() & alias["normalized_display"].notna()].copy()
    return dict(zip(alias["raw_value"], alias["normalized_display"]))


def parse_country_json(text: str | None, alias_map: dict[str, str]) -> list[str]:
    if not text:
        return []
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[str] = []
    for item in items:
        raw = item.get("value") if isinstance(item, dict) else item
        if raw is None:
            continue
        norm = alias_map.get(raw, raw)
        out.append(norm)
    return out


def load_edge_instances(alias_map: dict[str, str]) -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT
                openalex_work_id,
                title,
                publication_year,
                source_concept_id,
                target_concept_id,
                source_concept_label,
                target_concept_label,
                source_countries_json,
                target_countries_json
            FROM concept_edge_instances
            """,
            con,
        )
    finally:
        con.close()

    df["src_countries"] = df["source_countries_json"].map(lambda s: parse_country_json(s, alias_map))
    df["dst_countries"] = df["target_countries_json"].map(lambda s: parse_country_json(s, alias_map))
    df["all_countries"] = df.apply(
        lambda r: sorted(set(r["src_countries"]) | set(r["dst_countries"])), axis=1
    )
    return df


def build_unit_panels(inst: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paper = (
        inst.groupby("openalex_work_id", as_index=False)
        .agg(
            title=("title", "first"),
            year=("publication_year", "first"),
            countries=("all_countries", lambda s: sorted(set(c for lst in s for c in lst))),
            edge_instances=("all_countries", "size"),
        )
        .rename(columns={"openalex_work_id": "paper_id"})
    )
    paper["n_countries"] = paper["countries"].map(len)
    paper["has_country"] = paper["n_countries"] > 0

    edge = (
        inst.groupby(["source_concept_id", "target_concept_id"], as_index=False)
        .agg(
            source_label=("source_concept_label", "first"),
            target_label=("target_concept_label", "first"),
            countries=("all_countries", lambda s: sorted(set(c for lst in s for c in lst))),
            supports=("all_countries", "size"),
        )
    )
    edge["edge_label"] = edge["source_label"] + " -> " + edge["target_label"]
    edge["n_countries"] = edge["countries"].map(len)
    edge["has_country"] = edge["n_countries"] > 0

    source_nodes = inst[["source_concept_id", "source_concept_label", "src_countries"]].rename(
        columns={
            "source_concept_id": "concept_id",
            "source_concept_label": "label",
            "src_countries": "countries",
        }
    )
    target_nodes = inst[["target_concept_id", "target_concept_label", "dst_countries"]].rename(
        columns={
            "target_concept_id": "concept_id",
            "target_concept_label": "label",
            "dst_countries": "countries",
        }
    )
    node_inst = pd.concat([source_nodes, target_nodes], ignore_index=True)
    node = (
        node_inst.groupby("concept_id", as_index=False)
        .agg(
            label=("label", "first"),
            countries=("countries", lambda s: sorted(set(c for lst in s for c in lst))),
            context_mentions=("countries", lambda s: sum(len(lst) for lst in s)),
            incident_instances=("countries", "size"),
        )
    )
    node["n_countries"] = node["countries"].map(len)
    node["has_country"] = node["n_countries"] > 0

    yearly = (
        paper.groupby("year", as_index=False)
        .agg(
            papers=("paper_id", "nunique"),
            share_papers_with_country=("has_country", "mean"),
            avg_countries_per_paper=("n_countries", "mean"),
        )
        .sort_values("year")
    )
    edge_inst_yearly = (
        inst.assign(has_country=inst["all_countries"].map(bool))
        .groupby("publication_year", as_index=False)
        .agg(
            edge_instances=("has_country", "size"),
            share_edge_instances_with_country=("has_country", "mean"),
        )
        .rename(columns={"publication_year": "year"})
        .sort_values("year")
    )
    yearly = yearly.merge(edge_inst_yearly, on="year", how="left")

    return paper, edge, node, yearly


def top_country_panel(paper: pd.DataFrame, edge: pd.DataFrame, node: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    paper_counter = Counter(c for lst in paper["countries"] for c in lst)
    edge_counter = Counter(c for lst in edge["countries"] for c in lst)
    node_counter = Counter(c for lst in node["countries"] for c in lst)

    top = [country for country, _ in paper_counter.most_common(n)]
    rows = []
    total_papers = len(paper)
    total_edges = len(edge)
    total_nodes = len(node)
    for country in top:
        rows.append(
            {
                "country": country,
                "paper_share": paper_counter[country] / total_papers,
                "edge_share": edge_counter[country] / total_edges,
                "node_share": node_counter[country] / total_nodes,
                "paper_count": paper_counter[country],
                "edge_count": edge_counter[country],
                "node_count": node_counter[country],
            }
        )
    return pd.DataFrame(rows)


def summarize_units(paper: pd.DataFrame, edge: pd.DataFrame, node: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, df in [("Papers", paper), ("Concept edges", edge), ("Concept nodes", node)]:
        rows.append(
            {
                "Unit": label,
                "Count": int(len(df)),
                "Share with any country context": df["has_country"].mean(),
                "Mean unique countries": df["n_countries"].mean(),
                "Median": df["n_countries"].median(),
                "P90": df["n_countries"].quantile(0.9),
                "P99": df["n_countries"].quantile(0.99),
                "Max": df["n_countries"].max(),
            }
        )
    return pd.DataFrame(rows)


def bucket_counts(series: pd.Series, buckets: list[tuple[str, callable]]) -> pd.DataFrame:
    rows = []
    for label, cond in buckets:
        rows.append({"bucket": label, "count": int(cond(series).sum())})
    out = pd.DataFrame(rows)
    out["share"] = out["count"] / out["count"].sum()
    return out


def make_figures(
    paper: pd.DataFrame,
    edge: pd.DataFrame,
    node: pd.DataFrame,
    yearly: pd.DataFrame,
    top_country: pd.DataFrame,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = {
        "paper": "#486A8A",
        "edge": "#C56B3D",
        "node": "#4D8B65",
        "accent": "#7B5EA7",
        "ink": "#222222",
    }

    paper_buckets = bucket_counts(
        paper["n_countries"],
        [
            ("0", lambda s: s == 0),
            ("1", lambda s: s == 1),
            ("2", lambda s: s == 2),
            ("3", lambda s: s == 3),
            ("4", lambda s: s == 4),
            ("5+", lambda s: s >= 5),
        ],
    )
    edge_buckets = bucket_counts(
        edge["n_countries"],
        [
            ("0", lambda s: s == 0),
            ("1", lambda s: s == 1),
            ("2", lambda s: s == 2),
            ("3", lambda s: s == 3),
            ("4", lambda s: s == 4),
            ("5", lambda s: s == 5),
            ("6-10", lambda s: (s >= 6) & (s <= 10)),
            ("11+", lambda s: s >= 11),
        ],
    )
    node_buckets = bucket_counts(
        node["n_countries"],
        [
            ("0", lambda s: s == 0),
            ("1", lambda s: s == 1),
            ("2", lambda s: s == 2),
            ("3-4", lambda s: (s >= 3) & (s <= 4)),
            ("5-10", lambda s: (s >= 5) & (s <= 10)),
            ("11-20", lambda s: (s >= 11) & (s <= 20)),
            ("21+", lambda s: s >= 21),
        ],
    )

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5))

    for ax, df, title, color in [
        (axes[0, 0], paper_buckets, "A. Unique countries per paper", colors["paper"]),
        (axes[0, 1], edge_buckets, "B. Unique countries per concept edge", colors["edge"]),
        (axes[1, 0], node_buckets, "C. Unique countries per concept node", colors["node"]),
    ]:
        ax.bar(df["bucket"], df["share"], color=color, alpha=0.9)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
        ax.set_ylabel("Share of units")
        ax.set_ylim(0, max(df["share"]) * 1.18)
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
        ax.grid(axis="x", visible=False)

    ax = axes[1, 1]
    ax.plot(
        yearly["year"],
        yearly["share_papers_with_country"],
        color=colors["paper"],
        lw=2.2,
        label="papers",
    )
    ax.plot(
        yearly["year"],
        yearly["share_edge_instances_with_country"],
        color=colors["edge"],
        lw=2.2,
        label="edge instances",
    )
    ax.set_title("D. Country context becomes more common over time", loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("Share with any country context")
    ax.set_xlabel("Publication year")
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", visible=False)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "context_coverage_distributions.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "context_coverage_distributions.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1.0, 1.05]})

    ax = axes[0]
    country_plot = top_country.sort_values("paper_share", ascending=True)
    y = np.arange(len(country_plot))
    h = 0.22
    ax.barh(y + h, country_plot["paper_share"], height=h, color=colors["paper"], label="papers")
    ax.barh(y, country_plot["edge_share"], height=h, color=colors["edge"], label="edges")
    ax.barh(y - h, country_plot["node_share"], height=h, color=colors["node"], label="nodes")
    ax.set_yticks(y)
    ax.set_yticklabels(country_plot["country"])
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.set_xlabel("Share of units in which country appears")
    ax.set_title("A. Country context is highly concentrated", loc="left", fontsize=11, fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="y", visible=False)

    ax = axes[1]
    node_plot = node[node["n_countries"] > 0].copy()
    ax.scatter(
        node_plot["incident_instances"],
        node_plot["n_countries"],
        s=18,
        alpha=0.35,
        color=colors["accent"],
        edgecolor="none",
    )
    top_nodes = node_plot.sort_values(["n_countries", "incident_instances"], ascending=False).head(8)
    for row in top_nodes.itertuples(index=False):
        ax.annotate(
            row.label,
            (row.incident_instances, row.n_countries),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
            color=colors["ink"],
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Incident edge instances (log scale)")
    ax.set_ylabel("Unique countries linked to node (log scale)")
    ax.set_title("B. Broad country coverage sits on a small set of nodes", loc="left", fontsize=11, fontweight="bold")
    ax.grid(True, which="major", alpha=0.25)
    ax.grid(False, which="minor")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "context_concentration_and_scope.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "context_concentration_and_scope.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_tables(summary: pd.DataFrame, top_nodes: pd.DataFrame, top_edges: pd.DataFrame) -> None:
    summary_fmt = summary.copy()
    summary_fmt = summary_fmt.rename(
        columns={
            "Count": "N",
            "Share with any country context": "Share with context",
            "Mean unique countries": "Mean countries",
        }
    )
    for col in ["Share with context"]:
        summary_fmt[col] = summary_fmt[col].map(lambda x: f"{x:.1%}".replace("%", r"\%"))
    for col in ["Mean unique countries", "Median", "P90", "P99", "Max"]:
        summary_fmt[col] = summary_fmt[col].map(lambda x: f"{x:,.1f}" if float(x) % 1 else f"{int(x):,}")

    top_nodes_fmt = top_nodes.copy()
    top_nodes_fmt["Incident instances"] = top_nodes_fmt["Incident instances"].map(lambda x: f"{x:,}")
    top_edges_fmt = top_edges.copy()
    top_edges_fmt["Supporting instances"] = top_edges_fmt["Supporting instances"].map(lambda x: f"{x:,}")

    (TAB_DIR / "context_summary.tex").write_text(
        summary_fmt.to_latex(index=False, escape=False, column_format="lrrrrrrr"),
        encoding="utf-8",
    )
    (TAB_DIR / "top_nodes_by_country_breadth.tex").write_text(
        top_nodes_fmt.to_latex(index=False, escape=False, column_format="p{7.5cm}rr"),
        encoding="utf-8",
    )
    (TAB_DIR / "top_edges_by_country_breadth.tex").write_text(
        top_edges_fmt.to_latex(index=False, escape=False, column_format="p{8.5cm}rr"),
        encoding="utf-8",
    )


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TAB_DIR.mkdir(parents=True, exist_ok=True)

    alias_map = load_alias_map()
    inst = load_edge_instances(alias_map)
    paper, edge, node, yearly = build_unit_panels(inst)
    top_country = top_country_panel(paper, edge, node)

    summary = summarize_units(paper, edge, node)
    top_nodes = (
        node.sort_values(["n_countries", "incident_instances"], ascending=False)
        .head(10)[["label", "n_countries", "incident_instances"]]
        .rename(columns={"label": "Node", "n_countries": "Unique countries", "incident_instances": "Incident instances"})
    )
    top_edges = (
        edge.sort_values(["n_countries", "supports"], ascending=False)
        .head(10)[["edge_label", "n_countries", "supports"]]
        .rename(columns={"edge_label": "Edge", "n_countries": "Unique countries", "supports": "Supporting instances"})
    )

    make_figures(paper, edge, node, yearly, top_country)
    write_tables(summary, top_nodes, top_edges)

    summary.to_csv(TAB_DIR / "context_summary.csv", index=False)
    top_nodes.to_csv(TAB_DIR / "top_nodes_by_country_breadth.csv", index=False)
    top_edges.to_csv(TAB_DIR / "top_edges_by_country_breadth.csv", index=False)


if __name__ == "__main__":
    main()
