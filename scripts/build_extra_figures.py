"""Generate all extra figures for extra_results.tex testbed.

Figures:
  1. Real graph neighborhood (subgraph around curated example)
  2. Precision-at-K curves (reranker vs PA vs co-occurrence)
  3. Corpus and graph growth time series
  4. Concept embedding t-SNE visualization
  5. Feature importance bar chart by family
  6. Reranker vs baselines radar/comparison chart
  7. Temporal generalization comparison
  8. Sparse-vs-dense regime comparison
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "outputs/paper/50_extra_figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PAPER_DIR = ROOT / "paper"

# Color palette (economics-paper friendly, colorblind-safe)
C_RERANKER = "#2166ac"   # deep blue
C_PA = "#b2182b"          # deep red
C_COOC = "#d6604d"        # salmon
C_GRAPH = "#4393c3"       # medium blue
C_CLOSURE = "#92c5de"     # light blue
C_DEGREE = "#f4a582"      # light salmon
C_DIRECTED = "#2166ac"    # directed features
C_STRUCTURAL = "#4393c3"
C_DYNAMIC = "#92c5de"
C_COMPOSITION = "#d6604d"
C_BOUNDARY = "#b2182b"
C_BASE = "#999999"

FAMILY_COLORS = {
    "structural": C_STRUCTURAL,
    "boundary_gap": C_BOUNDARY,
    "composition": C_COMPOSITION,
    "dynamic": C_DYNAMIC,
    "base": C_BASE,
}

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def _safe_numeric(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


# ======================================================================= #
# FIGURE 1: Real graph neighborhood
# ======================================================================= #
def fig_real_neighborhood():
    print("  Fig 1: Real graph neighborhood...")
    corpus = pd.read_parquet("data/processed/research_allocation_v2/hybrid_corpus.parquet")
    concepts_csv = pd.read_csv("site/public/data/v2/central_concepts.csv")
    label_map = dict(zip(concepts_csv["concept_id"].astype(str), concepts_csv["plain_label"].astype(str)))

    # Find "CO2 emissions" concept
    co2_candidates = [c for c, l in label_map.items() if "co2" in l.lower() or "carbon" in l.lower() or "emission" in l.lower()]
    # Find "price changes" concept
    price_candidates = [c for c, l in label_map.items() if "price" in l.lower()]

    # Use the full corpus to find the neighborhood
    # Pick a well-connected target node
    target_label = "CO2 emissions"
    target_code = None
    for c, l in label_map.items():
        if l.lower().strip() == "co2 emissions":
            target_code = c
            break

    if target_code is None:
        # Fallback: find the most connected concept with "co2" or "emission"
        for c in co2_candidates:
            if c in label_map:
                target_code = c
                target_label = label_map[c]
                break

    if target_code is None:
        print("    Could not find CO2 emissions concept — skipping")
        return

    # Get all edges involving the target
    edges_src = corpus[corpus["src_code"].astype(str) == str(target_code)]
    edges_dst = corpus[corpus["dst_code"].astype(str) == str(target_code)]
    neighbors_src = set(edges_src["dst_code"].astype(str).unique())
    neighbors_dst = set(edges_dst["src_code"].astype(str).unique())
    all_neighbors = (neighbors_src | neighbors_dst) - {str(target_code)}

    # Pick top 15 neighbors by edge count
    neighbor_counts = {}
    for n in all_neighbors:
        count = len(corpus[(corpus["src_code"].astype(str) == n) | (corpus["dst_code"].astype(str) == n)])
        neighbor_counts[n] = count
    top_neighbors = sorted(neighbor_counts.keys(), key=lambda x: neighbor_counts[x], reverse=True)[:15]

    # Build subgraph
    nodes = [str(target_code)] + top_neighbors
    node_labels = {n: label_map.get(n, n)[:25] for n in nodes}

    # Get edges between these nodes
    node_set = set(nodes)
    sub_edges = corpus[
        (corpus["src_code"].astype(str).isin(node_set)) &
        (corpus["dst_code"].astype(str).isin(node_set))
    ].copy()

    # Deduplicate edges
    edge_list = []
    seen = set()
    for _, row in sub_edges.iterrows():
        s, d, ek = str(row["src_code"]), str(row["dst_code"]), str(row["edge_kind"])
        key = (s, d, ek)
        if key not in seen:
            seen.add(key)
            edge_list.append((s, d, ek))

    # Layout: spring layout
    import networkx as nx
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    for s, d, ek in edge_list:
        G.add_edge(s, d, kind=ek)

    pos = nx.spring_layout(G, seed=42, k=2.5, iterations=80)

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Draw edges
    for s, d, ek in edge_list:
        x0, y0 = pos[s]
        x1, y1 = pos[d]
        if ek == "directed_causal":
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color=C_RERANKER, lw=1.2, alpha=0.7))
        else:
            ax.plot([x0, x1], [y0, y1], color="#cccccc", lw=0.6, alpha=0.5)

    # Draw nodes
    for n in nodes:
        x, y = pos[n]
        if n == str(target_code):
            ax.scatter(x, y, s=300, c=C_BOUNDARY, zorder=5, edgecolors="black", linewidths=1.5)
        else:
            ax.scatter(x, y, s=150, c="#f0f0f0", zorder=5, edgecolors="black", linewidths=0.8)
        ax.text(x, y + 0.08, node_labels[n], ha="center", va="bottom", fontsize=7,
                fontweight="bold" if n == str(target_code) else "normal")

    # Legend
    legend_elements = [
        Line2D([0], [0], color=C_RERANKER, lw=1.5, label="Directed causal edge"),
        Line2D([0], [0], color="#cccccc", lw=1.0, label="Undirected contextual"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=C_BOUNDARY,
               markersize=10, label=f"Target: {target_label}"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", framealpha=0.9)
    ax.set_title(f"Real graph neighborhood around '{target_label}'", fontsize=13)
    ax.set_xlim(ax.get_xlim()[0] - 0.15, ax.get_xlim()[1] + 0.15)
    ax.set_ylim(ax.get_ylim()[0] - 0.15, ax.get_ylim()[1] + 0.15)
    ax.axis("off")

    fig.savefig(OUT_DIR / "real_neighborhood.png")
    fig.savefig(OUT_DIR / "real_neighborhood.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 2: Precision-at-K curves
# ======================================================================= #
def fig_precision_at_k():
    print("  Fig 2: Precision-at-K curves...")
    panel = pd.read_parquet("outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet")
    pool_col = [c for c in panel.columns if c.startswith("in_pool_")]
    if pool_col:
        panel = panel[panel[pool_col[0]].astype(bool)].copy()

    from src.analysis.ranking_utils import evaluate_binary_ranking

    # Build scores
    panel["graph_score_val"] = _safe_numeric(panel["transparent_score"] if "transparent_score" in panel.columns else panel["score"])
    panel["pa_score"] = _safe_numeric(panel["support_degree_product"])
    panel["cooc_score"] = _safe_numeric(panel["cooc_count"])
    panel["ddp_score"] = _safe_numeric(panel["direct_degree_product"])

    models = {
        "Graph score": ("graph_score_val", C_GRAPH, "-"),
        "Pref. attachment": ("pa_score", C_PA, "--"),
        "Co-occurrence": ("cooc_score", C_COOC, "-."),
        "Direct degree prod.": ("ddp_score", C_DIRECTED, ":"),
    }

    k_range = [25, 50, 100, 200, 500, 1000, 2000, 5000]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)

    for ax, horizon in zip(axes, [5, 10]):
        h_panel = panel[panel["horizon"] == horizon]

        for model_name, (score_col, color, ls) in models.items():
            precisions = []
            for k in k_range:
                precs = []
                for cutoff, group in h_panel.groupby("cutoff_year_t"):
                    positives = {(str(r.u), str(r.v)) for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)}
                    if not positives:
                        continue
                    ranked = group[["u", "v", score_col]].rename(columns={score_col: "score"}).sort_values("score", ascending=False).head(k)
                    hits = sum(1 for _, row in ranked.iterrows() if (str(row["u"]), str(row["v"])) in positives)
                    precs.append(hits / k)
                precisions.append(np.mean(precs) if precs else 0)

            ax.plot(k_range, precisions, color=color, ls=ls, lw=2, marker="o", markersize=4, label=model_name)

        ax.set_xlabel("Shortlist size K")
        ax.set_ylabel("Precision@K")
        ax.set_title(f"h = {horizon} years")
        ax.set_xscale("log")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Precision-at-K: how screening quality changes with shortlist size", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "precision_at_k_curves.png")
    fig.savefig(OUT_DIR / "precision_at_k_curves.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 3: Corpus and graph growth
# ======================================================================= #
def fig_corpus_growth():
    print("  Fig 3: Corpus and graph growth...")
    corpus = pd.read_parquet("data/processed/research_allocation_v2/hybrid_corpus.parquet")

    # Papers per year (deduplicate by paper_id)
    papers = corpus[["paper_id", "year"]].drop_duplicates()
    papers_by_year = papers.groupby("year").size().sort_index()

    # Edges per year (cumulative)
    edges_by_year_directed = corpus[corpus["edge_kind"] == "directed_causal"].groupby("year").size().sort_index().cumsum()
    edges_by_year_undirected = corpus[corpus["edge_kind"] == "undirected_noncausal"].groupby("year").size().sort_index().cumsum()
    edges_by_year_total = corpus.groupby("year").size().sort_index().cumsum()

    # Concepts per year (cumulative unique)
    all_concepts_by_year = {}
    seen_concepts = set()
    for year in sorted(corpus["year"].unique()):
        yr_data = corpus[corpus["year"] == year]
        new_concepts = set(yr_data["src_code"].astype(str)) | set(yr_data["dst_code"].astype(str))
        seen_concepts |= new_concepts
        all_concepts_by_year[year] = len(seen_concepts)
    concepts_cumulative = pd.Series(all_concepts_by_year).sort_index()

    fig, axes = plt.subplots(2, 2, figsize=(13.4, 10.0))

    # Panel A: Papers per year
    ax = axes[0, 0]
    ax.bar(papers_by_year.index, papers_by_year.values, color=C_GRAPH, alpha=0.8, width=0.8)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Papers", fontsize=11)
    ax.set_title("A. Papers per year", fontsize=12)
    ax.set_xlim(1975, 2027)
    ax.tick_params(labelsize=10)

    # Panel B: Cumulative concepts
    ax = axes[0, 1]
    ax.plot(concepts_cumulative.index, concepts_cumulative.values, color=C_RERANKER, lw=2)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Cumulative concepts", fontsize=11)
    ax.set_title("B. Concept vocabulary growth", fontsize=12)
    ax.set_xlim(1975, 2027)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=10)

    # Panel C: Cumulative edges (stacked by type)
    ax = axes[1, 0]
    years = sorted(set(edges_by_year_directed.index) & set(edges_by_year_undirected.index))
    ax.fill_between(years, [edges_by_year_directed.get(y, 0) for y in years], alpha=0.7, color=C_RERANKER, label="Directed causal")
    ax.fill_between(years, [edges_by_year_directed.get(y, 0) for y in years],
                    [edges_by_year_total.get(y, 0) for y in years], alpha=0.4, color="#cccccc", label="Undirected contextual")
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Cumulative edges", fontsize=11)
    ax.set_title("C. Graph edge growth by type", fontsize=12)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_xlim(1975, 2027)
    ax.tick_params(labelsize=10)

    # Panel D: Directed-to-total ratio
    ax = axes[1, 1]
    ratio_years = sorted(set(edges_by_year_directed.index) & set(edges_by_year_total.index))
    ratios = [edges_by_year_directed.get(y, 0) / max(edges_by_year_total.get(y, 1), 1) for y in ratio_years]
    ax.plot(ratio_years, ratios, color=C_BOUNDARY, lw=2)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Directed causal share", fontsize=11)
    ax.set_title("D. Causal edge share over time", fontsize=12)
    ax.set_xlim(1975, 2027)
    ax.set_ylim(0, 0.15)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=10)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "corpus_growth.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "corpus_growth.pdf", bbox_inches="tight")
    fig.savefig(PAPER_DIR / "corpus_growth.png", dpi=300, bbox_inches="tight")
    fig.savefig(PAPER_DIR / "corpus_growth.pdf", bbox_inches="tight")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 4: Concept embedding t-SNE
# ======================================================================= #
def fig_concept_tsne():
    print("  Fig 4: Concept t-SNE (from TF-IDF on neighbor labels)...")
    corpus = pd.read_parquet("data/processed/research_allocation_v2/hybrid_corpus.parquet")
    concepts_csv = pd.read_csv("site/public/data/v2/central_concepts.csv")
    label_map = dict(zip(concepts_csv["concept_id"].astype(str), concepts_csv["plain_label"].astype(str)))

    # Get top concepts by degree
    all_codes = pd.concat([corpus["src_code"].astype(str), corpus["dst_code"].astype(str)])
    code_counts = all_codes.value_counts()
    top_codes = code_counts.head(500).index.tolist()

    # Build neighbor-label "documents" for each concept
    docs = {}
    for code in top_codes:
        neighbors_src = corpus[corpus["src_code"].astype(str) == code]["dst_code"].astype(str).tolist()
        neighbors_dst = corpus[corpus["dst_code"].astype(str) == code]["src_code"].astype(str).tolist()
        neighbor_labels = [label_map.get(n, n) for n in (neighbors_src + neighbors_dst)]
        docs[code] = " ".join(neighbor_labels)

    # TF-IDF + t-SNE
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.manifold import TSNE

    codes = list(docs.keys())
    texts = [docs[c] for c in codes]
    tfidf = TfidfVectorizer(max_features=500, stop_words="english")
    X = tfidf.fit_transform(texts).toarray()

    tsne = TSNE(n_components=2, random_state=42, perplexity=30, n_iter=1000)
    coords = tsne.fit_transform(X)

    # Color by causal share
    causal_share = {}
    for code in codes:
        total = len(corpus[(corpus["src_code"].astype(str) == code) | (corpus["dst_code"].astype(str) == code)])
        causal = len(corpus[((corpus["src_code"].astype(str) == code) | (corpus["dst_code"].astype(str) == code)) & (corpus["edge_kind"] == "directed_causal")])
        causal_share[code] = causal / max(total, 1)

    colors = [causal_share.get(c, 0) for c in codes]
    sizes = [np.log1p(code_counts.get(c, 1)) * 8 for c in codes]
    labels = [label_map.get(c, c) for c in codes]

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    scatter = ax.scatter(coords[:, 0], coords[:, 1], c=colors, cmap="RdYlBu_r",
                         s=sizes, alpha=0.7, edgecolors="white", linewidths=0.3)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, label="Causal edge share")

    # Label top 30 by degree
    for i in range(min(30, len(codes))):
        ax.annotate(labels[i], (coords[i, 0], coords[i, 1]),
                   fontsize=6, ha="center", va="bottom", alpha=0.8)

    ax.set_title("t-SNE of top 500 concepts (colored by causal edge share, sized by degree)", fontsize=12)
    ax.axis("off")

    fig.savefig(OUT_DIR / "concept_tsne.png")
    fig.savefig(OUT_DIR / "concept_tsne.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 5: Feature importance bar chart
# ======================================================================= #
def fig_feature_importance():
    print("  Fig 5: Feature importance bar chart...")
    summary = pd.read_csv("outputs/paper/46_single_feature_importance/single_feature_summary.csv")

    for horizon in [5, 10]:
        block = summary[summary["horizon"] == horizon].head(15).copy()
        block = block.sort_values("mean_precision_at_100", ascending=True)  # for horizontal bars

        fig, ax = plt.subplots(1, 1, figsize=(8, 6))

        colors = [FAMILY_COLORS.get(f, "#999999") for f in block["family"]]
        bars = ax.barh(range(len(block)), block["mean_precision_at_100"], color=colors, edgecolor="white", linewidth=0.5)

        ax.set_yticks(range(len(block)))
        ax.set_yticklabels([f.replace("_", " ").title() for f in block["feature"]], fontsize=8)
        ax.set_xlabel("Precision@100 (single-feature ranking)")
        ax.set_title(f"Single-feature importance ranking (h = {horizon})")

        # Add family legend
        legend_patches = [mpatches.Patch(color=c, label=f.replace("_", " ").title())
                         for f, c in FAMILY_COLORS.items()]
        ax.legend(handles=legend_patches, loc="lower right", fontsize=8, title="Feature family")
        ax.grid(True, axis="x", alpha=0.3)

        fig.tight_layout()
        fig.savefig(OUT_DIR / f"feature_importance_h{horizon}.png")
        fig.savefig(OUT_DIR / f"feature_importance_h{horizon}.pdf")
        plt.close(fig)

    print("    Done.")


# ======================================================================= #
# FIGURE 6: Temporal generalization comparison
# ======================================================================= #
def fig_temporal_generalization():
    print("  Fig 6: Temporal generalization...")
    tg = pd.read_csv("outputs/paper/49_extended_analyses/temporal_generalization_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, horizon in zip(axes, [5, 10]):
        block = tg[tg["horizon"] == horizon]

        eras = ["train_era", "held_out_era"]
        era_labels = ["Train era\n(1990–2005)", "Held-out era\n(2010–2015)"]
        x = np.arange(len(eras))
        width = 0.35

        reranker_vals = [float(block[(block["era"] == e) & (block["model"] == "reranker_restricted")]["mean_p100"].iloc[0])
                        if len(block[(block["era"] == e) & (block["model"] == "reranker_restricted")]) > 0 else 0
                        for e in eras]
        pa_vals = [float(block[(block["era"] == e) & (block["model"] == "pref_attach")]["mean_p100"].iloc[0])
                  if len(block[(block["era"] == e) & (block["model"] == "pref_attach")]) > 0 else 0
                  for e in eras]

        ax.bar(x - width/2, reranker_vals, width, label="Reranker", color=C_RERANKER, alpha=0.85)
        ax.bar(x + width/2, pa_vals, width, label="Pref. attachment", color=C_PA, alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(era_labels)
        ax.set_ylabel("Precision@100")
        ax.set_title(f"h = {horizon} years")
        ax.legend(loc="upper left")

        # Add percentage labels
        for i, (rv, pv) in enumerate(zip(reranker_vals, pa_vals)):
            if pv > 0:
                pct = (rv - pv) / pv * 100
                ax.text(i, max(rv, pv) + 0.01, f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%",
                       ha="center", fontsize=9, fontweight="bold", color=C_RERANKER)

    fig.suptitle("Temporal generalization: reranker trained on 1990–2005, tested on held-out 2010–2015", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "temporal_generalization.png")
    fig.savefig(OUT_DIR / "temporal_generalization.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 7: Sparse vs Dense regime comparison
# ======================================================================= #
def fig_sparse_dense():
    print("  Fig 7: Sparse vs Dense regime...")
    sd = pd.read_csv("outputs/paper/47_regime_split_analyses/sparse_dense_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, horizon in zip(axes, [5, 10]):
        block = sd[sd["horizon"] == horizon]
        regimes = ["sparse", "dense"]
        regime_labels = ["Sparse\n(low co-occurrence)", "Dense\n(high co-occurrence)"]
        x = np.arange(len(regimes))
        width = 0.2

        models_to_plot = ["graph_score", "pref_attach", "direct_degree_product"]
        model_labels = ["Graph score", "Pref. attachment", "Direct degree prod."]
        model_colors = [C_GRAPH, C_PA, C_DIRECTED]

        for j, (mname, mlabel, mcol) in enumerate(zip(models_to_plot, model_labels, model_colors)):
            vals = []
            for regime in regimes:
                sub = block[(block["regime"] == regime) & (block["model"] == mname)]
                vals.append(float(sub["mean_precision_at_100"].iloc[0]) if len(sub) > 0 else 0)
            ax.bar(x + (j - 1) * width, vals, width, label=mlabel, color=mcol, alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(regime_labels)
        ax.set_ylabel("Precision@100")
        ax.set_title(f"h = {horizon} years")
        ax.legend(loc="upper left", fontsize=8)

    fig.suptitle("Where does graph structure help more? Sparse vs. dense neighborhoods", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "sparse_dense_comparison.png")
    fig.savefig(OUT_DIR / "sparse_dense_comparison.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 8: Feature decomposition comparison
# ======================================================================= #
def fig_feature_decomposition():
    print("  Fig 8: Feature decomposition...")
    decomp = pd.read_csv("outputs/paper/48_feature_decomposition/feature_decomposition_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    model_order = ["reranker_directed_only", "reranker_cooc_only", "reranker_all_features", "pref_attach", "cooc_count"]
    model_labels = ["Directed features\nonly (18)", "Co-occurrence features\nonly (23)", "All features\n(41)", "Pref. attachment\n(baseline)", "Co-occurrence count\n(baseline)"]
    model_colors = [C_DIRECTED, C_COOC, C_RERANKER, C_PA, C_COOC]
    model_hatches = ["", "", "", "//", "//"]

    for ax, horizon in zip(axes, [5, 10]):
        block = decomp[decomp["horizon"] == horizon]
        vals = []
        for m in model_order:
            sub = block[block["model"] == m]
            vals.append(float(sub["mean_precision_at_100"].iloc[0]) if len(sub) > 0 else 0)

        bars = ax.bar(range(len(vals)), vals, color=model_colors, edgecolor="black", linewidth=0.5, alpha=0.85)
        for bar, hatch in zip(bars, model_hatches):
            bar.set_hatch(hatch)

        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels(model_labels, fontsize=7, ha="center")
        ax.set_ylabel("Precision@100")
        ax.set_title(f"h = {horizon} years")
        ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Feature-set decomposition: directed features alone beat co-occurrence features", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "feature_decomposition.png")
    fig.savefig(OUT_DIR / "feature_decomposition.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# FIGURE 9: All-horizons reranker comparison
# ======================================================================= #
def fig_all_horizons():
    print("  Fig 9: All-horizons reranker comparison...")
    summary = pd.read_csv("outputs/paper/49_extended_analyses/reranker_all_horizons_summary.csv")

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))

    models_to_plot = [
        ("reranker", "Learned reranker", C_RERANKER, "-", "o"),
        ("pref_attach", "Pref. attachment", C_PA, "--", "s"),
        ("cooc_count", "Co-occurrence", C_COOC, "-.", "^"),
        ("graph_score", "Graph score", C_GRAPH, ":", "D"),
    ]
    horizons = sorted(summary["horizon"].unique())

    for mname, mlabel, mcol, mls, mmarker in models_to_plot:
        vals = []
        for h in horizons:
            sub = summary[(summary["model"] == mname) & (summary["horizon"] == h)]
            vals.append(float(sub["mean_p100"].iloc[0]) if len(sub) > 0 else 0)
        ax.plot(horizons, vals, color=mcol, ls=mls, marker=mmarker, lw=2, markersize=7, label=mlabel)

    ax.set_xlabel("Evaluation horizon (years)")
    ax.set_ylabel("Precision@100")
    ax.set_title("Benchmark comparison across all horizons")
    ax.legend(loc="upper left")
    ax.set_xticks(horizons)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "all_horizons_comparison.png")
    fig.savefig(OUT_DIR / "all_horizons_comparison.pdf")
    plt.close(fig)
    print("    Done.")


# ======================================================================= #
# MAIN
# ======================================================================= #
def main():
    print("Generating extra figures...\n")

    fig_real_neighborhood()
    fig_precision_at_k()
    fig_corpus_growth()
    fig_concept_tsne()
    fig_feature_importance()
    fig_temporal_generalization()
    fig_sparse_dense()
    fig_feature_decomposition()
    fig_all_horizons()

    print(f"\nAll figures saved to {OUT_DIR}")
    print(f"Files: {sorted(f.name for f in OUT_DIR.glob('*.png'))}")


if __name__ == "__main__":
    main()
