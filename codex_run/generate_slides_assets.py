from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle


ROOT = Path(__file__).resolve().parents[1]
OUT_TABLES = ROOT / "outputs" / "paper" / "slides_tables"
OUT_FIGURES = ROOT / "outputs" / "paper" / "figures"


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


def _draw_node(ax, xy, label, color="#f8fafc", edge="#1f2937"):
    circ = Circle(xy, 0.08, facecolor=color, edgecolor=edge, linewidth=1.5)
    ax.add_patch(circ)
    ax.text(xy[0], xy[1], label, ha="center", va="center", fontsize=11, fontweight="bold")


def _draw_arrow(ax, src, dst, text=None, color="#1f2937", style="-|>", lw=1.5, ls="-"):
    ax.annotate(
        "",
        xy=dst,
        xytext=src,
        arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls),
    )
    if text:
        mx = (src[0] + dst[0]) / 2
        my = (src[1] + dst[1]) / 2
        ax.text(mx, my + 0.05, text, ha="center", va="center", fontsize=9, color=color)


def build_method_figures() -> None:
    OUT_FIGURES.mkdir(parents=True, exist_ok=True)

    # Step 1: candidate generation
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    pos = {"u": (0.20, 0.50), "w": (0.50, 0.50), "v": (0.80, 0.50)}
    _draw_node(ax, pos["u"], "u")
    _draw_node(ax, pos["w"], "w")
    _draw_node(ax, pos["v"], "v")
    _draw_arrow(ax, pos["u"], pos["w"], text="observed")
    _draw_arrow(ax, pos["w"], pos["v"], text="observed")
    _draw_arrow(ax, (0.24, 0.43), (0.76, 0.43), text="missing candidate u->v", color="#c2410c", ls="--")
    ax.text(
        0.50,
        0.15,
        "Step 1: From observed paths, enumerate absent direct links as candidates",
        ha="center",
        fontsize=11,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "method_build_step1_candidates.png", dpi=300)
    plt.close(fig)

    # Step 2: signal family
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.6))
    titles = ["Gap", "Path Support", "Motif + Hub Penalty"]
    for ax, title in zip(axes, titles):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, fontsize=11, fontweight="bold")

    # Gap panel
    axes[0].text(0.5, 0.72, "u and v rarely co-appear\nin prior papers", ha="center", fontsize=10)
    _draw_node(axes[0], (0.28, 0.35), "u")
    _draw_node(axes[0], (0.72, 0.35), "v")
    axes[0].text(0.5, 0.12, "higher underexploration bonus", ha="center", fontsize=9, color="#c2410c")

    # Path panel
    _draw_node(axes[1], (0.18, 0.35), "u")
    _draw_node(axes[1], (0.50, 0.65), "w1")
    _draw_node(axes[1], (0.50, 0.20), "w2")
    _draw_node(axes[1], (0.82, 0.35), "v")
    _draw_arrow(axes[1], (0.24, 0.39), (0.44, 0.59))
    _draw_arrow(axes[1], (0.24, 0.31), (0.44, 0.25))
    _draw_arrow(axes[1], (0.56, 0.59), (0.76, 0.39))
    _draw_arrow(axes[1], (0.56, 0.25), (0.76, 0.31))
    axes[1].text(0.5, 0.08, "more independent mediators -> stronger support", ha="center", fontsize=9, color="#0369a1")

    # Motif panel
    _draw_node(axes[2], (0.20, 0.50), "u")
    _draw_node(axes[2], (0.50, 0.75), "w")
    _draw_node(axes[2], (0.80, 0.50), "v")
    _draw_arrow(axes[2], (0.26, 0.56), (0.44, 0.69))
    _draw_arrow(axes[2], (0.56, 0.69), (0.74, 0.56))
    _draw_arrow(axes[2], (0.26, 0.44), (0.74, 0.44), color="#c2410c", ls="--")
    axes[2].text(0.5, 0.12, "open triad suggests closure;\nhub terms prevent popularity artifacts", ha="center", fontsize=8.8, color="#475569")

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
    fig, ax = plt.subplots(figsize=(9.5, 2.8))
    ax.set_xlim(1970, 2026)
    ax.set_ylim(0, 1)
    ax.hlines(0.5, 1973, 2023, linewidth=8, color="#cbd5e1")
    ax.vlines(2015, 0.35, 0.65, linewidth=3, color="#c2410c")
    ax.text(1973, 0.72, "Data start: 1973", fontsize=10)
    ax.text(2023, 0.72, "Data end: 2023", fontsize=10, ha="right")
    ax.text(2015, 0.20, "Cutoff t=2015", fontsize=10, ha="center", color="#c2410c")
    ax.annotate("", xy=(2015, 0.5), xytext=(1973, 0.5), arrowprops=dict(arrowstyle="<->", color="#1f2937", lw=1.3))
    ax.text(1994, 0.58, "Corpus stock G_{t-1}", fontsize=10, ha="center")
    ax.annotate("", xy=(2020, 0.5), xytext=(2015, 0.5), arrowprops=dict(arrowstyle="<->", color="#0369a1", lw=1.3))
    ax.text(2017.5, 0.58, "Future window [t, t+h]", fontsize=10, ha="center", color="#0369a1")
    ax.set_yticks([])
    ax.set_xlabel("Year")
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "corpus_stock_timeline.png", dpi=300)
    plt.close(fig)


def main() -> None:
    build_metric_scale_table()
    build_horizon_design_table()
    build_external_dataset_table()
    build_method_figures()
    print("Slide tables and figures generated.")


if __name__ == "__main__":
    main()
