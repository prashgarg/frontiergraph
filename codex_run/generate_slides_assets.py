from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT_TABLES = ROOT / "outputs" / "paper" / "slides_tables"
OUT_FIGURES = ROOT / "outputs" / "paper" / "figures"
OUT_SLIDES_FIGURES = ROOT / "outputs" / "paper" / "slides_figures"


def _harmonic(n: int) -> float:
    return float(np.sum(1.0 / np.arange(1, n + 1)))


def build_metric_scale_table() -> None:
    main_path = ROOT / "outputs" / "paper" / "02_eval" / "main_table_with_ci.csv"
    ablation_path = ROOT / "outputs" / "paper" / "03_model_search" / "ablation_grid.csv"
    enrich_path = ROOT / "outputs" / "paper" / "05_benchmarks" / "enrichment_results.csv"
    candidates_path = ROOT / "data" / "processed" / "candidates_causalclaims.parquet"

    main = pd.read_csv(main_path)
    ablation = pd.read_csv(ablation_path)
    enrich = pd.read_csv(enrich_path)

    if candidates_path.exists():
        n_candidates = int(len(pd.read_parquet(candidates_path)))
    else:
        n_candidates = int(enrich.loc[enrich["bucket"] == "overall", "n"].iloc[0])

    random_recall = 100.0 / n_candidates
    random_mrr = _harmonic(n_candidates) / n_candidates

    rows: List[Dict[str, object]] = []

    # Full rolling setting
    for horizon in [1, 3, 5]:
        pref_r100 = float(
            main[
                (main["model"] == "pref_attach")
                & (main["horizon"] == horizon)
                & (main["metric"] == "recall_at_100")
            ]["mean"].iloc[0]
        )
        pref_mrr = float(
            main[
                (main["model"] == "pref_attach")
                & (main["horizon"] == horizon)
                & (main["metric"] == "mrr")
            ]["mean"].iloc[0]
        )
        for model, metric, rand in [
            ("main", "recall_at_100", random_recall),
            ("main", "mrr", random_mrr),
            ("pref_attach", "recall_at_100", random_recall),
            ("pref_attach", "mrr", random_mrr),
        ]:
            raw = float(
                main[
                    (main["model"] == model)
                    & (main["horizon"] == horizon)
                    & (main["metric"] == metric)
                ]["mean"].iloc[0]
            )
            if metric == "recall_at_100":
                delta = raw - pref_r100
            else:
                delta = raw - pref_mrr

            rows.append(
                {
                    "setting": "internal_full_rolling",
                    "horizon": horizon,
                    "model": model,
                    "metric": metric,
                    "raw_value": raw,
                    "random_expectation": rand,
                    "lift_vs_random": raw / rand if rand > 0 else np.nan,
                    "delta_vs_pref": delta,
                }
            )

    # Tuned holdout-anchor setting
    for horizon in [1, 3, 5]:
        pref = ablation[
            (ablation["config_name"] == "pref_attach") & (ablation["horizon"] == horizon)
        ].iloc[0]
        opt = ablation[
            (ablation["config_name"] == "full_optimized")
            & (ablation["horizon"] == horizon)
        ].iloc[0]

        holdout_rows = [
            ("full_optimized", "recall_at_100", float(opt["mean_recall_at_100"]), random_recall),
            ("pref_attach", "recall_at_100", float(pref["mean_recall_at_100"]), random_recall),
            ("full_optimized", "mrr", float(opt["mean_mrr"]), random_mrr),
            ("pref_attach", "mrr", float(pref["mean_mrr"]), random_mrr),
        ]
        for model, metric, raw, rand in holdout_rows:
            pref_raw = float(pref["mean_recall_at_100"]) if metric == "recall_at_100" else float(pref["mean_mrr"])
            rows.append(
                {
                    "setting": "tuned_anchor_holdout",
                    "horizon": horizon,
                    "model": model,
                    "metric": metric,
                    "raw_value": raw,
                    "random_expectation": rand,
                    "lift_vs_random": raw / rand if rand > 0 else np.nan,
                    "delta_vs_pref": raw - pref_raw,
                }
            )

    out = pd.DataFrame(rows)
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_TABLES / "metric_scale_interpretation.csv", index=False)


def build_horizon_design_table() -> None:
    rows = [
        {
            "horizon_set": "1,3,5",
            "field_rationale": "Fast feedback and standard link-prediction comparability",
            "pros": "More cutoffs, quicker iteration, better short-run diagnostics",
            "risks": "May understate performance in slow-moving economics subfields",
            "recommended_use": "Core internal benchmark and ablation loop",
        },
        {
            "horizon_set": "3,5,10,15",
            "field_rationale": "Economics knowledge diffusion and publication lags are longer",
            "pros": "Better match to field tempo and delayed claim adoption",
            "risks": "Fewer valid cutoffs and higher horizon overlap complexity",
            "recommended_use": "Primary economics-facing robustness panel",
        },
        {
            "horizon_set": "5,10,15",
            "field_rationale": "Long-cycle institutional and policy mechanisms",
            "pros": "Highlights slow-burn links and durable claim formation",
            "risks": "Very sparse positives and reduced statistical power",
            "recommended_use": "Supplementary long-horizon stress test",
        },
    ]
    pd.DataFrame(rows).to_csv(OUT_TABLES / "horizon_design_options.csv", index=False)


def build_external_dataset_table() -> None:
    rows = [
        {
            "dataset": "OpenAlex (economics-tagged works)",
            "edge_proxy": "Future claim co-linking and directed citation-linked concept pairs",
            "coverage": "Global, broad, multi-decade metadata",
            "latency": "Moderate updates; API and metadata normalization required",
            "strengths": "Large scale, open access, cross-field comparability",
            "risks": "Concept mapping noise and heterogeneous discipline tagging",
        },
        {
            "dataset": "RePEc/IDEAS + NBER working papers",
            "edge_proxy": "Topic-link emergence from working-paper to publication pathway",
            "coverage": "Strong economics coverage with institutional depth",
            "latency": "Fast for working papers, slower for final journal diffusion",
            "strengths": "Economics-native ecosystem and policy relevance",
            "risks": "Metadata fragmentation and code harmonization burden",
        },
        {
            "dataset": "IMF/World Bank/OECD research corpora",
            "edge_proxy": "Claim diffusion into policy-oriented analysis and reports",
            "coverage": "Policy-heavy economics and development domains",
            "latency": "Institution-dependent release cadence",
            "strengths": "External validity in practice-facing research channels",
            "risks": "Different writing style and concept extraction transfer risk",
        },
        {
            "dataset": "PatentsView/USPTO + OpenAlex patent links",
            "edge_proxy": "Claim-to-technology pathway and delayed influence realization",
            "coverage": "Technology domains with long commercialization windows",
            "latency": "Long horizon but rich forward citation signals",
            "strengths": "Direct test of supply-creates-demand narrative",
            "risks": "Mapping economics claims to patents can be sparse and noisy",
        },
    ]
    pd.DataFrame(rows).to_csv(OUT_TABLES / "external_dataset_options.csv", index=False)


def _draw_node(
    ax,
    xy,
    label,
    color="#f8fafc",
    edge="#1f2937",
    radius=0.08,
    fontsize=11,
    textcolor="#111827",
):
    circ = Circle(xy, radius, facecolor=color, edgecolor=edge, linewidth=1.5)
    ax.add_patch(circ)
    ax.text(
        xy[0],
        xy[1],
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=textcolor,
    )


def _draw_arrow(
    ax,
    src,
    dst,
    text=None,
    color="#1f2937",
    style="-|>",
    lw=1.5,
    ls="-",
    text_fs=9,
):
    ax.annotate(
        "",
        xy=dst,
        xytext=src,
        arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls),
    )
    if text:
        mx = (src[0] + dst[0]) / 2
        my = (src[1] + dst[1]) / 2
        ax.text(mx, my + 0.05, text, ha="center", va="center", fontsize=text_fs, color=color)


def build_method_figures() -> None:
    OUT_FIGURES.mkdir(parents=True, exist_ok=True)
    panel_edge = "#d7dfeb"
    ink = "#172033"

    # Step 1: candidate generation
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.add_patch(
        FancyBboxPatch(
            (0.05, 0.26),
            0.90,
            0.52,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            linewidth=1.0,
            edgecolor=panel_edge,
            facecolor="#ffffff",
        )
    )

    ax.add_patch(
        FancyBboxPatch(
            (0.08, 0.34),
            0.18,
            0.36,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            linewidth=1.0,
            edgecolor=panel_edge,
            facecolor="#eef4ff",
        )
    )
    ax.text(0.17, 0.60, "Corpus stock", ha="center", fontsize=14, fontweight="bold", color=ink)
    ax.text(0.17, 0.49, "Observed papers\nby year $t-1$", ha="center", fontsize=12, color="#475569")
    ax.text(0.17, 0.38, "Freeze one vintage", ha="center", fontsize=11, color="#1d4ed8")

    ax.annotate("", xy=(0.34, 0.52), xytext=(0.28, 0.52), arrowprops=dict(arrowstyle="-|>", color="#1d4ed8", lw=2.2))

    pos = {"u": (0.41, 0.52), "w": (0.55, 0.52), "v": (0.69, 0.52)}
    _draw_node(ax, pos["u"], "u", color="#dbeafe", edge="#2563eb", radius=0.050, fontsize=13)
    _draw_node(ax, pos["w"], "w", color="#ede9fe", edge="#7c3aed", radius=0.050, fontsize=13)
    _draw_node(ax, pos["v"], "v", color="#dcfce7", edge="#0f766e", radius=0.050, fontsize=13)
    _draw_arrow(ax, (0.46, 0.56), (0.50, 0.56), text="observed", color="#475569", lw=1.8, text_fs=10)
    _draw_arrow(ax, (0.60, 0.56), (0.64, 0.56), text="observed", color="#475569", lw=1.8, text_fs=10)
    _draw_arrow(
        ax,
        (0.46, 0.46),
        (0.64, 0.46),
        text="missing direct link",
        color="#c2410c",
        lw=2.0,
        ls="--",
        text_fs=10,
    )
    ax.text(0.55, 0.67, "Local literature structure", ha="center", fontsize=13, fontweight="bold", color=ink)
    ax.text(0.55, 0.35, "Observed paths imply a missing candidate question", ha="center", fontsize=11, color="#475569")

    ax.annotate("", xy=(0.82, 0.52), xytext=(0.75, 0.52), arrowprops=dict(arrowstyle="-|>", color="#0f766e", lw=2.2))
    ax.add_patch(
        FancyBboxPatch(
            (0.83, 0.34),
            0.09,
            0.36,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            linewidth=1.0,
            edgecolor=panel_edge,
            facecolor="#ecfdf5",
        )
    )
    ax.text(0.875, 0.60, "Candidate", ha="center", fontsize=14, fontweight="bold", color=ink)
    ax.text(0.875, 0.49, "$u \\rightarrow v$", ha="center", fontsize=15, fontweight="bold", color="#0f766e")
    ax.text(0.875, 0.38, "Potential next paper", ha="center", fontsize=10.5, color="#475569")

    ax.text(
        0.50,
        0.14,
        "Step 1: turn missing direct links implied by observed paths into candidate research questions",
        ha="center",
        fontsize=13,
        fontweight="bold",
        color=ink,
    )
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "method_build_step1_candidates.png", dpi=300)
    plt.close(fig)

    # Step 2: signal family
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.8))
    titles = ["Gap", "Path Support", "Motif + Hub Penalty"]
    panel_faces = ["#fff7ed", "#eef4ff", "#f5f3ff"]
    title_colors = ["#c2410c", "#1d4ed8", "#7c3aed"]
    for ax, title, face, tcolor in zip(axes, titles, panel_faces, title_colors):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0.03, 0.05),
                0.94,
                0.88,
                boxstyle="round,pad=0.02,rounding_size=0.03",
                linewidth=1.0,
                edgecolor=panel_edge,
                facecolor=face,
            )
        )
        ax.text(0.5, 0.87, title, ha="center", va="center", fontsize=14, fontweight="bold", color=tcolor)

    # Gap panel
    axes[0].text(0.5, 0.68, "u and v rarely co-appear\nin prior papers", ha="center", fontsize=12, color=ink)
    _draw_node(axes[0], (0.30, 0.40), "u", color="#ffedd5", edge="#c2410c", radius=0.075, fontsize=13)
    _draw_node(axes[0], (0.70, 0.40), "v", color="#ffedd5", edge="#c2410c", radius=0.075, fontsize=13)
    _draw_arrow(axes[0], (0.38, 0.40), (0.62, 0.40), color="#c2410c", lw=2.2, ls="--")
    axes[0].text(0.5, 0.18, "higher underexploration bonus", ha="center", fontsize=11, fontweight="bold", color="#c2410c")

    # Path panel
    _draw_node(axes[1], (0.18, 0.42), "u", color="#dbeafe", edge="#1d4ed8", radius=0.070, fontsize=13)
    _draw_node(axes[1], (0.50, 0.66), "w1", color="#dbeafe", edge="#1d4ed8", radius=0.065, fontsize=12)
    _draw_node(axes[1], (0.50, 0.28), "w2", color="#dbeafe", edge="#1d4ed8", radius=0.065, fontsize=12)
    _draw_node(axes[1], (0.82, 0.42), "v", color="#dbeafe", edge="#1d4ed8", radius=0.070, fontsize=13)
    _draw_arrow(axes[1], (0.24, 0.46), (0.43, 0.61), color="#1d4ed8", lw=2.0)
    _draw_arrow(axes[1], (0.24, 0.38), (0.43, 0.31), color="#1d4ed8", lw=2.0)
    _draw_arrow(axes[1], (0.57, 0.61), (0.76, 0.46), color="#1d4ed8", lw=2.0)
    _draw_arrow(axes[1], (0.57, 0.31), (0.76, 0.38), color="#1d4ed8", lw=2.0)
    axes[1].text(0.5, 0.16, "more independent mediators -> stronger support", ha="center", fontsize=11, fontweight="bold", color="#1d4ed8")

    # Motif panel
    _draw_node(axes[2], (0.24, 0.50), "u", color="#ede9fe", edge="#7c3aed", radius=0.070, fontsize=13)
    _draw_node(axes[2], (0.50, 0.72), "w", color="#ede9fe", edge="#7c3aed", radius=0.070, fontsize=13)
    _draw_node(axes[2], (0.76, 0.50), "v", color="#ede9fe", edge="#7c3aed", radius=0.070, fontsize=13)
    _draw_arrow(axes[2], (0.30, 0.56), (0.44, 0.66), color="#7c3aed", lw=2.0)
    _draw_arrow(axes[2], (0.56, 0.66), (0.70, 0.56), color="#7c3aed", lw=2.0)
    _draw_arrow(axes[2], (0.31, 0.44), (0.69, 0.44), color="#c2410c", lw=2.0, ls="--")
    axes[2].text(0.5, 0.16, "closure is useful; hub-heavy artifacts are discounted", ha="center", fontsize=10.5, fontweight="bold", color="#7c3aed")

    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "method_build_step2_signals.png", dpi=300)
    plt.close(fig)

    # Signal-specific examples
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(["cooc(u,v)=0", "cooc(u,v)=1", "cooc(u,v)=2+"], [1.0, 0.5, 0.0], color=["#f97316", "#fb923c", "#cbd5e1"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Gap bonus")
    ax.set_title("Signal Example: Underexplored Pair Bonus")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "signal1_gap_example.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    pos = {"u": (0.12, 0.5), "w1": (0.38, 0.75), "w2": (0.38, 0.25), "w3": (0.62, 0.50), "v": (0.88, 0.50)}
    for k, p in pos.items():
        _draw_node(ax, p, k)
    _draw_arrow(ax, (0.18, 0.56), (0.32, 0.69))
    _draw_arrow(ax, (0.18, 0.44), (0.32, 0.31))
    _draw_arrow(ax, (0.18, 0.50), (0.56, 0.50))
    _draw_arrow(ax, (0.44, 0.69), (0.82, 0.56))
    _draw_arrow(ax, (0.44, 0.31), (0.82, 0.44))
    _draw_arrow(ax, (0.68, 0.50), (0.82, 0.50))
    ax.text(0.5, 0.10, "Multiple mediators linking u to v increase path support", ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "signal2_path_example.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    _draw_node(ax, (0.15, 0.55), "u")
    _draw_node(ax, (0.45, 0.80), "w")
    _draw_node(ax, (0.75, 0.55), "v")
    _draw_node(ax, (0.45, 0.30), "hub")
    _draw_arrow(ax, (0.21, 0.61), (0.39, 0.74), text="u->w")
    _draw_arrow(ax, (0.51, 0.74), (0.69, 0.61), text="w->v")
    _draw_arrow(ax, (0.21, 0.49), (0.69, 0.49), text="missing u->v", color="#c2410c", ls="--")
    _draw_arrow(ax, (0.18, 0.50), (0.39, 0.33), color="#475569")
    _draw_arrow(ax, (0.51, 0.33), (0.72, 0.50), color="#475569")
    ax.text(0.5, 0.08, "Open triad suggests completion; hub-heavy closures are discounted", ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "signal3_motif_example.png", dpi=300)
    plt.close(fig)

    # Transparent score decomposition example
    components = ["Path", "Gap", "Motif", "-Hub"]
    values = [0.50, 0.00, 0.30, -0.20]
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626"]
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    ax.bar(components, values, color=colors)
    ax.axhline(0, color="#334155", linewidth=1.2)
    total = sum(values)
    ax.text(2.85, total + 0.03, f"Total score = {total:.2f}", fontsize=11, fontweight="bold")
    ax.set_title("Transparent Score = Sum of Interpretable Components")
    ax.set_ylabel("Contribution to score")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "score_decomposition_example.png", dpi=300)
    plt.close(fig)

    # Corpus stock timeline
    fig, ax = plt.subplots(figsize=(11.5, 3.6))
    ax.set_xlim(1970, 2026)
    ax.set_ylim(0, 1)
    ax.hlines(0.52, 1973, 2015, linewidth=11, color="#dbeafe")
    ax.hlines(0.52, 2015, 2021, linewidth=11, color="#bfdbfe")
    ax.hlines(0.52, 2021, 2023, linewidth=11, color="#e2e8f0")
    ax.vlines(2015, 0.30, 0.74, linewidth=4, color="#c2410c")
    ax.text(1973, 0.82, "Data start: 1973", fontsize=12, color=ink)
    ax.text(2023, 0.82, "Data end: 2023", fontsize=12, ha="right", color=ink)
    ax.text(2015, 0.15, "Cutoff $t$", fontsize=12, ha="center", color="#c2410c", fontweight="bold")
    ax.annotate("", xy=(2015, 0.52), xytext=(1973, 0.52), arrowprops=dict(arrowstyle="<->", color="#1d4ed8", lw=1.6))
    ax.text(1994, 0.63, "Corpus stock $G_{t-1}$", fontsize=12, ha="center", color="#1d4ed8", fontweight="bold")
    ax.annotate("", xy=(2020.5, 0.52), xytext=(2015, 0.52), arrowprops=dict(arrowstyle="<->", color="#0f766e", lw=1.6))
    ax.text(2017.8, 0.63, "Future window $[t, t+h]$", fontsize=12, ha="center", color="#0f766e", fontweight="bold")
    ax.set_yticks([])
    ax.set_xlabel("Year", color="#475569")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(panel_edge)
    ax.tick_params(axis="x", labelsize=10, colors="#475569")
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "corpus_stock_timeline.png", dpi=300)
    plt.close(fig)


def build_research_allocation_slide_figures() -> None:
    OUT_SLIDES_FIGURES.mkdir(parents=True, exist_ok=True)

    main = pd.read_csv(ROOT / "outputs" / "paper" / "02_eval" / "main_table_with_ci.csv")
    ablation = pd.read_csv(ROOT / "outputs" / "paper" / "03_model_search" / "ablation_grid.csv")
    attention = pd.read_csv(ROOT / "outputs" / "paper" / "07_attention_allocation" / "attention_summary.csv")
    novelty = pd.read_csv(ROOT / "outputs" / "paper" / "09_gap_boundary" / "novelty_mix_by_model.csv")

    model_colors = {
        "main": "#2563eb",
        "pref_attach": "#8b5cf6",
        "full_optimized": "#0f766e",
    }

    # Mainline full rolling benchmark
    full = main[
        main["model"].isin(["main", "pref_attach"])
        & main["metric"].isin(["recall_at_100", "mrr"])
        & main["horizon"].isin([1, 3, 5])
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
    metric_meta = [
        ("recall_at_100", "Recall@100", 1.0),
        ("mrr", "MRR", 1.0),
    ]
    horizons = [1, 3, 5]
    bar_width = 0.34
    x = np.arange(len(horizons))
    for ax, (metric, title, scale) in zip(axes, metric_meta):
        for idx, model in enumerate(["main", "pref_attach"]):
            subset = (
                full[(full["metric"] == metric) & (full["model"] == model)]
                .sort_values("horizon")
                .reset_index(drop=True)
            )
            means = subset["mean"].to_numpy() * scale
            lo = subset["ci_lo"].to_numpy() * scale
            hi = subset["ci_hi"].to_numpy() * scale
            yerr = np.vstack([means - lo, hi - means])
            ax.bar(
                x + (idx - 0.5) * bar_width,
                means,
                width=bar_width,
                color=model_colors[model],
                alpha=0.9,
                label="FrontierGraph main" if model == "main" else "Preferential attachment",
                yerr=yerr,
                capsize=4,
                error_kw={"elinewidth": 1.1, "ecolor": "#475569"},
            )
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xticks(x, [f"h={h}" for h in horizons])
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        ax.spines[["top", "right"]].set_visible(False)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    axes[0].set_ylabel("Mean over rolling cutoffs")
    axes[0].legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("Full rolling backtest: honest benchmark", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_SLIDES_FIGURES / "mainline_full_rolling_vs_pref.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Held-out tuned benchmark
    heldout = ablation[
        ablation["config_name"].isin(["full_optimized", "pref_attach"])
        & ablation["horizon"].isin([1, 3, 5])
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1))
    metric_meta = [
        ("mean_recall_at_100", "Recall@100"),
        ("mean_mrr", "MRR"),
    ]
    for ax, (metric, title) in zip(axes, metric_meta):
        for idx, model in enumerate(["full_optimized", "pref_attach"]):
            subset = heldout[heldout["config_name"] == model].sort_values("horizon")
            ax.bar(
                x + (idx - 0.5) * bar_width,
                subset[metric].to_numpy(),
                width=bar_width,
                color=model_colors[model],
                alpha=0.92,
                label="Optimized transparent model" if model == "full_optimized" else "Preferential attachment",
            )
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xticks(x, [f"h={h}" for h in horizons])
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        ax.spines[["top", "right"]].set_visible(False)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    axes[0].set_ylabel("Held-out anchor mean")
    axes[0].legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("Held-out anchors: transparent tuning can beat the popularity baseline", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_SLIDES_FIGURES / "mainline_heldout_vs_pref.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Attention-allocation frontier
    frontier = attention[
        attention["horizon"].eq(5)
        & attention["model"].isin(["main", "pref_attach"])
        & attention["k"].isin([50, 100, 500, 1000])
    ].copy()
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for model in ["main", "pref_attach"]:
        subset = frontier[frontier["model"] == model].sort_values("k")
        ax.plot(
            subset["k"],
            subset["mean_precision"],
            marker="o",
            linewidth=2.4,
            markersize=6.5,
            color=model_colors[model],
            label="FrontierGraph main" if model == "main" else "Preferential attachment",
        )
    ax.set_xlabel("Top-K questions surfaced")
    ax.set_ylabel("Precision in the future window")
    ax.set_title("Attention frontier (h=5): main catches up as the list broadens", fontsize=13, fontweight="bold")
    ax.grid(alpha=0.25, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT_SLIDES_FIGURES / "attention_allocation_frontier.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Gap vs boundary mix
    mix = novelty[
        novelty["horizon"].eq(5)
        & novelty["k"].eq(100)
        & novelty["model"].isin(["main", "pref_attach", "cooc_gap"])
    ].copy()
    order = ["main", "pref_attach", "cooc_gap"]
    labels = {
        "gap_crossfield": "Gap\ncross-field",
        "gap_internal": "Gap\nsame-field",
        "boundary_crossfield": "Boundary\ncross-field",
        "boundary_internal": "Boundary\nsame-field",
    }
    stack_colors = {
        "gap_crossfield": "#2563eb",
        "gap_internal": "#60a5fa",
        "boundary_crossfield": "#f59e0b",
        "boundary_internal": "#fcd34d",
    }
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    bottom = np.zeros(len(order))
    for novelty_type in ["gap_crossfield", "gap_internal", "boundary_crossfield", "boundary_internal"]:
        vals = []
        for model in order:
            row = mix[(mix["model"] == model) & (mix["novelty_type"] == novelty_type)]
            vals.append(float(row["share_in_top_k"].iloc[0]) if not row.empty else 0.0)
        vals = np.array(vals)
        ax.bar(order, vals, bottom=bottom, color=stack_colors[novelty_type], label=labels[novelty_type])
        bottom += vals
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Share of top-100 surfaced questions")
    ax.set_title("What kind of questions are being surfaced?", fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    fig.savefig(OUT_SLIDES_FIGURES / "gap_boundary_mainline.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    build_metric_scale_table()
    build_horizon_design_table()
    build_external_dataset_table()
    build_method_figures()
    build_research_allocation_slide_figures()
    print("Slide tables and figures generated.")


if __name__ == "__main__":
    main()
