"""Regime-split analyses: where does graph structure help more?

Two analyses in one script:

1. SPARSE-VS-DENSE: Split candidates by local co-occurrence density.
   Does the graph score / reranker add more value over preferential
   attachment in sparse neighborhoods than in dense ones?
   (Borrows from Sourati et al. 2023, Nature Human Behaviour.)

2. HIGH-VS-LOW IMPACT: Split candidates by endpoint citation impact (FWCI).
   Does the reranker predict high-impact realizations better than low-impact
   ones?  (Borrows from Gu & Krenn 2025, Impact4Cast.)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PANEL_CACHE = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
CONCEPTS_CSV = ROOT / "site/public/data/v2/central_concepts.csv"
OUT_DIR = ROOT / "outputs/paper/142_regime_split_refresh"
NOTE_PATH = ROOT / "next_steps/regime_split_refresh_note.md"

K_VALUES = [50, 100, 500]
REPORT_YEAR_MIN = 1990
REPORT_YEAR_MAX = 2015

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with",
}


def _safe_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


def _tokenize(v: str) -> tuple[str, ...]:
    t = re.sub(r"\s*\([^)]*\)", " ", str(v or "").lower())
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return tuple(tok for tok in t.split() if tok and tok not in STOPWORDS)


def _jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    sa, sb = set(a), set(b)
    d = len(sa | sb)
    return float(len(sa & sb) / d) if d else 0.0


def _containment(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return float(len(sa & sb) / min(len(sa), len(sb)))


# --------------------------------------------------------------------------- #
# Score construction (same as benchmark expansion)
# --------------------------------------------------------------------------- #
def _add_scores(panel_df: pd.DataFrame) -> pd.DataFrame:
    out = panel_df.copy()
    pool_col = [c for c in out.columns if c.startswith("in_pool_")]
    if pool_col:
        out = out[out[pool_col[0]].astype(bool)].copy()

    support_degree = _safe_numeric(out["support_degree_product"])
    recent_degree = (
        (_safe_numeric(out["source_recent_support_out_degree"]) + 1.0)
        * (_safe_numeric(out["target_recent_support_in_degree"]) + 1.0)
    )
    cooc = _safe_numeric(out["cooc_count"])

    out["graph_score"] = _safe_numeric(
        out["transparent_score"] if "transparent_score" in out.columns else out["score"]
    )
    out["pref_attach_score"] = support_degree
    out["degree_recency_score"] = np.log1p(support_degree) + 0.5 * np.log1p(recent_degree)
    out["cooc_count_score"] = cooc
    out["cooc_pref_attach_score"] = cooc * np.log1p(support_degree)
    out["direct_degree_product_score"] = _safe_numeric(out["direct_degree_product"])
    return out


MODEL_COLS = {
    "graph_score": "graph_score",
    "pref_attach": "pref_attach_score",
    "degree_recency": "degree_recency_score",
    "cooc_count": "cooc_count_score",
    "cooc_pref_attach": "cooc_pref_attach_score",
    "direct_degree_product": "direct_degree_product_score",
}


# --------------------------------------------------------------------------- #
# Evaluation helpers
# --------------------------------------------------------------------------- #
def _eval_slice(group: pd.DataFrame, positives: set, model_cols: dict, k_values: list[int]) -> list[dict]:
    rows = []
    for model_name, score_col in model_cols.items():
        ranked = (
            group[["u", "v", score_col]]
            .rename(columns={score_col: "score"})
            .sort_values(["score", "u", "v"], ascending=[False, True, True])
            .reset_index(drop=True)
        )
        ranked["rank"] = ranked.index + 1
        # Only count positives that are in this slice
        slice_pairs = {(str(r.u), str(r.v)) for r in group[["u", "v"]].itertuples(index=False)}
        slice_positives = positives & slice_pairs
        if not slice_positives:
            continue
        metrics = evaluate_binary_ranking(
            ranked[["u", "v", "score", "rank"]], positives=slice_positives, k_values=k_values
        )
        row: dict[str, Any] = {
            "model": model_name,
            "mrr": float(metrics.get("mrr", 0.0)),
            "n_candidates": len(group),
            "n_positives": len(slice_positives),
        }
        for k in k_values:
            row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
            row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
            row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Analysis 1: Sparse vs Dense
# --------------------------------------------------------------------------- #
def run_sparse_dense(panel_df: pd.DataFrame) -> pd.DataFrame:
    """Split candidates by co-occurrence density within each (cutoff, horizon) cell."""
    metric_rows: list[dict[str, Any]] = []

    for (cutoff, horizon), cell in panel_df.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives = {
            (str(r.u), str(r.v))
            for r in cell[cell["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)
        }
        if not positives:
            continue

        cooc = _safe_numeric(cell["cooc_count"])
        median_cooc = cooc.median()

        for regime, mask in [
            ("sparse", cooc <= median_cooc),
            ("dense", cooc > median_cooc),
        ]:
            sub = cell[mask]
            if len(sub) < 50:
                continue
            rows = _eval_slice(sub, positives, MODEL_COLS, K_VALUES)
            for r in rows:
                r["cutoff_year_t"] = int(cutoff)
                r["horizon"] = int(horizon)
                r["regime"] = regime
                r["median_cooc"] = float(median_cooc)
                r["slice_size"] = int(len(sub))
            metric_rows.extend(rows)

    return pd.DataFrame(metric_rows)


# --------------------------------------------------------------------------- #
# Analysis 2: High vs Low Impact Endpoints
# --------------------------------------------------------------------------- #
def run_impact_split(panel_df: pd.DataFrame) -> pd.DataFrame:
    """Split candidates by endpoint FWCI within each (cutoff, horizon) cell."""
    metric_rows: list[dict[str, Any]] = []

    for (cutoff, horizon), cell in panel_df.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives = {
            (str(r.u), str(r.v))
            for r in cell[cell["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)
        }
        if not positives:
            continue

        fwci = _safe_numeric(cell["pair_mean_fwci"])
        median_fwci = fwci.median()

        for regime, mask in [
            ("low_fwci", fwci <= median_fwci),
            ("high_fwci", fwci > median_fwci),
        ]:
            sub = cell[mask]
            if len(sub) < 50:
                continue
            rows = _eval_slice(sub, positives, MODEL_COLS, K_VALUES)
            for r in rows:
                r["cutoff_year_t"] = int(cutoff)
                r["horizon"] = int(horizon)
                r["regime"] = regime
                r["median_fwci"] = float(median_fwci)
                r["slice_size"] = int(len(sub))
            metric_rows.extend(rows)

    return pd.DataFrame(metric_rows)


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
def _summarize(metric_df: pd.DataFrame) -> pd.DataFrame:
    agg: dict[str, tuple[str, str]] = {
        "mean_mrr": ("mrr", "mean"),
        "mean_precision_at_100": ("precision_at_100", "mean"),
        "mean_recall_at_100": ("recall_at_100", "mean"),
        "mean_hits_at_100": ("hits_at_100", "mean"),
        "n_cutoffs": ("cutoff_year_t", "nunique"),
        "mean_n_positives": ("n_positives", "mean"),
    }
    return (
        metric_df.groupby(["regime", "model", "horizon"], as_index=False)
        .agg(**agg)
        .sort_values(["horizon", "regime", "mean_precision_at_100"], ascending=[True, True, False])
    )


def _delta_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Compute graph_score - pref_attach delta by regime and horizon."""
    rows = []
    for (regime, horizon), block in summary_df.groupby(["regime", "horizon"]):
        gs = block[block["model"] == "graph_score"]
        pa = block[block["model"] == "pref_attach"]
        dr = block[block["model"] == "degree_recency"]
        if gs.empty or pa.empty:
            continue
        gs_p = float(gs["mean_precision_at_100"].iloc[0])
        pa_p = float(pa["mean_precision_at_100"].iloc[0])
        dr_p = float(dr["mean_precision_at_100"].iloc[0]) if not dr.empty else None
        rows.append({
            "regime": regime,
            "horizon": int(horizon),
            "graph_score_p100": gs_p,
            "pref_attach_p100": pa_p,
            "degree_recency_p100": dr_p,
            "delta_gs_minus_pa": gs_p - pa_p,
            "delta_pct": ((gs_p - pa_p) / pa_p * 100) if pa_p > 0 else None,
        })
    return pd.DataFrame(rows)


def _make_delta_figure(sparse_dense_delta: pd.DataFrame, impact_delta: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6), sharey=True)
    panels = [
        ("Sparse vs dense neighborhoods", sparse_dense_delta, ["sparse", "dense"]),
        ("Low vs high FWCI neighborhoods", impact_delta, ["low_fwci", "high_fwci"]),
    ]
    horizon_order = sorted(set(sparse_dense_delta["horizon"]).union(set(impact_delta["horizon"])))
    x = np.arange(len(horizon_order))
    width = 0.34

    for ax, (title, df, regime_order) in zip(axes, panels):
        for offset, regime in [(-width / 2, regime_order[0]), (width / 2, regime_order[1])]:
            sub = (
                df[df["regime"] == regime][["horizon", "delta_gs_minus_pa"]]
                .set_index("horizon")
                .reindex(horizon_order)
            )
            vals = sub["delta_gs_minus_pa"].fillna(0.0).to_numpy()
            label = regime.replace("_", " ")
            ax.bar(x + offset, vals, width=width, label=label)
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([f"h={int(h)}" for h in horizon_order])
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Horizon")
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel(r"$\Delta$ Precision@100 (graph $-$ PA)")
    axes[1].legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Markdown note
# --------------------------------------------------------------------------- #
def _write_note(
    sparse_dense_summary: pd.DataFrame,
    sparse_dense_delta: pd.DataFrame,
    impact_summary: pd.DataFrame,
    impact_delta: pd.DataFrame,
    note_path: Path,
) -> None:
    lines = [
        "# Regime-Split Analyses",
        "",
        "## Analysis 1: Sparse vs Dense (by co-occurrence density)",
        "",
        "**Question:** Does the graph score's advantage over PA vary with local neighborhood density?",
        "",
        "Candidates split at within-cell median co-occurrence count. Sparse = below median, Dense = above.",
        "",
    ]

    for horizon in sorted(sparse_dense_summary["horizon"].unique()):
        block = sparse_dense_summary[sparse_dense_summary["horizon"] == horizon]
        lines.append(f"### h={int(horizon)}")
        lines.append("")
        lines.append("| Regime | Model | P@100 | R@100 | MRR | Hits@100 |")
        lines.append("|--------|-------|-------|-------|-----|----------|")
        for r in block.itertuples(index=False):
            lines.append(
                f"| {r.regime} | {r.model} | {r.mean_precision_at_100:.6f} "
                f"| {r.mean_recall_at_100:.6f} | {r.mean_mrr:.6f} | {r.mean_hits_at_100:.1f} |"
            )
        lines.append("")

    lines.append("### Graph score minus PA (delta by regime)")
    lines.append("")
    lines.append("| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |")
    lines.append("|--------|---------|----------|----------|-------|---------|")
    for r in sparse_dense_delta.itertuples(index=False):
        pct = f"{r.delta_pct:.1f}%" if r.delta_pct is not None else "n/a"
        lines.append(
            f"| {r.regime} | {r.horizon} | {r.graph_score_p100:.6f} "
            f"| {r.pref_attach_p100:.6f} | {r.delta_gs_minus_pa:+.6f} | {pct} |"
        )
    lines.append("")

    lines.extend([
        "## Analysis 2: High vs Low Impact Endpoints (by pair FWCI)",
        "",
        "**Question:** Do the models screen differently in high-impact vs low-impact neighborhoods?",
        "",
        "Candidates split at within-cell median pair_mean_fwci.",
        "",
    ])

    for horizon in sorted(impact_summary["horizon"].unique()):
        block = impact_summary[impact_summary["horizon"] == horizon]
        lines.append(f"### h={int(horizon)}")
        lines.append("")
        lines.append("| Regime | Model | P@100 | R@100 | MRR | Hits@100 |")
        lines.append("|--------|-------|-------|-------|-----|----------|")
        for r in block.itertuples(index=False):
            lines.append(
                f"| {r.regime} | {r.model} | {r.mean_precision_at_100:.6f} "
                f"| {r.mean_recall_at_100:.6f} | {r.mean_mrr:.6f} | {r.mean_hits_at_100:.1f} |"
            )
        lines.append("")

    lines.append("### Graph score minus PA (delta by impact regime)")
    lines.append("")
    lines.append("| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |")
    lines.append("|--------|---------|----------|----------|-------|---------|")
    for r in impact_delta.itertuples(index=False):
        pct = f"{r.delta_pct:.1f}%" if r.delta_pct is not None else "n/a"
        lines.append(
            f"| {r.regime} | {r.horizon} | {r.graph_score_p100:.6f} "
            f"| {r.pref_attach_p100:.6f} | {r.delta_gs_minus_pa:+.6f} | {pct} |"
        )
    lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "**Sparse-dense:** If the graph score's deficit relative to PA is smaller in sparse regimes,",
        "that aligns with Sourati et al. (2023): graph structure is most useful where the literature",
        "is thinnest, i.e., where popularity signals are weakest and local topology carries more",
        "incremental information.",
        "",
        "**Impact split:** If models screen differently in high-FWCI vs low-FWCI neighborhoods,",
        "that reveals whether the reranker and graph score are better at predicting the appearance",
        "of connections involving high-impact topics or low-impact topics. This connects to the",
        "Impact4Cast finding that predicting *impactful* connections is harder than predicting any",
        "connection.",
    ])

    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    print(f"Loading panel from {PANEL_CACHE} ...")
    panel_df = pd.read_parquet(PANEL_CACHE)
    panel_df = _add_scores(panel_df)
    panel_df = panel_df[
        panel_df["cutoff_year_t"].between(REPORT_YEAR_MIN, REPORT_YEAR_MAX, inclusive="both")
    ].copy()
    print(f"  Panel rows after pool filter: {len(panel_df):,}")

    print("\n--- Analysis 1: Sparse vs Dense ---")
    sd_metric = run_sparse_dense(panel_df)
    sd_summary = _summarize(sd_metric)
    sd_delta = _delta_table(sd_summary)

    print("\n--- Analysis 2: High vs Low Impact ---")
    imp_metric = run_impact_split(panel_df)
    imp_summary = _summarize(imp_metric)
    imp_delta = _delta_table(imp_summary)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sd_metric.to_csv(OUT_DIR / "sparse_dense_panel.csv", index=False)
    sd_summary.to_csv(OUT_DIR / "sparse_dense_summary.csv", index=False)
    sd_delta.to_csv(OUT_DIR / "sparse_dense_delta.csv", index=False)
    imp_metric.to_csv(OUT_DIR / "impact_split_panel.csv", index=False)
    imp_summary.to_csv(OUT_DIR / "impact_split_summary.csv", index=False)
    imp_delta.to_csv(OUT_DIR / "impact_split_delta.csv", index=False)
    _make_delta_figure(sd_delta, imp_delta, OUT_DIR / "regime_split_delta_refreshed.png")

    _write_note(sd_summary, sd_delta, imp_summary, imp_delta, NOTE_PATH)

    print("\n=== SPARSE VS DENSE: DELTA TABLE ===\n")
    print(sd_delta.to_string(index=False))

    print("\n=== SPARSE VS DENSE: TOP MODELS ===\n")
    for h in sorted(sd_summary["horizon"].unique()):
        for regime in ["sparse", "dense"]:
            block = sd_summary[(sd_summary["horizon"] == h) & (sd_summary["regime"] == regime)].head(4)
            print(f"  h={int(h)}, {regime}:")
            for r in block.itertuples(index=False):
                print(f"    {r.model:25s}  P@100={r.mean_precision_at_100:.6f}  Hits={r.mean_hits_at_100:.1f}")
        print()

    print("\n=== IMPACT SPLIT: DELTA TABLE ===\n")
    print(imp_delta.to_string(index=False))

    print("\n=== IMPACT SPLIT: TOP MODELS ===\n")
    for h in sorted(imp_summary["horizon"].unique()):
        for regime in ["low_fwci", "high_fwci"]:
            block = imp_summary[(imp_summary["horizon"] == h) & (imp_summary["regime"] == regime)].head(4)
            print(f"  h={int(h)}, {regime}:")
            for r in block.itertuples(index=False):
                print(f"    {r.model:25s}  P@100={r.mean_precision_at_100:.6f}  Hits={r.mean_hits_at_100:.1f}")
        print()

    print(f"Outputs written to {OUT_DIR}")
    print(f"Note written to {NOTE_PATH}")


if __name__ == "__main__":
    main()
