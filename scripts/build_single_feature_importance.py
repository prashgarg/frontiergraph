"""Single-feature importance ranking: which individual graph features
carry the most screening signal?

For each of the 34 reranker features, rank candidates by that feature
alone and evaluate precision@100, recall@100, MRR on the same walk-forward
benchmark.  This produces an importance ordering directly comparable to
the 141-feature ablation in Gu & Krenn (2025, Impact4Cast).

The analysis answers: what is actually driving the reranker's advantage?
If a handful of directed-graph-specific features (path_support, mediator_count,
boundary_flag) rank highly even as standalone predictors, that strengthens the
case that directed causal extraction is worth the effort.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PANEL_CACHE = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/139_single_feature_importance_refresh"
NOTE_PATH = ROOT / "next_steps/single_feature_importance_refresh_note.md"

K_VALUES = [50, 100, 500, 1000]

FAMILY_COLORS = {
    "structural": "#4393c3",
    "dynamic": "#92c5de",
    "composition": "#d6604d",
    "boundary_gap": "#b2182b",
    "base": "#999999",
}

# --------------------------------------------------------------------------- #
# Feature inventory — all 34 reranker features grouped by family
# --------------------------------------------------------------------------- #
FEATURE_FAMILIES: dict[str, list[str]] = {
    "base": [
        "score",
    ],
    "structural": [
        "path_support_norm",
        "motif_bonus_norm",
        "gap_bonus",
        "hub_penalty",
        "mediator_count",
        "motif_count",
        "cooc_count",
        "cooc_trend_norm",
        "field_same_group",
        "source_direct_out_degree",
        "target_direct_in_degree",
        "source_support_out_degree",
        "target_support_in_degree",
        "support_degree_product",
        "direct_degree_product",
    ],
    "dynamic": [
        "support_age_years",
        "recent_support_age_years",
        "source_recent_support_out_degree",
        "target_recent_support_in_degree",
        "source_recent_incident_count",
        "target_recent_incident_count",
    ],
    "composition": [
        "source_mean_stability",
        "target_mean_stability",
        "pair_mean_stability",
        "source_evidence_diversity",
        "target_evidence_diversity",
        "pair_evidence_diversity_mean",
        "source_mean_fwci",
        "target_mean_fwci",
        "pair_mean_fwci",
    ],
    "boundary_gap": [
        "boundary_flag",
        "gap_like_flag",
        "nearby_closure_density",
    ],
}

# Flat list
ALL_FEATURES = []
FEATURE_TO_FAMILY: dict[str, str] = {}
for family, feats in FEATURE_FAMILIES.items():
    for f in feats:
        ALL_FEATURES.append(f)
        FEATURE_TO_FAMILY[f] = family


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def _evaluate_single_features(panel_df: pd.DataFrame) -> pd.DataFrame:
    """Rank candidates by each feature independently; compute metrics."""

    # Filter to pool
    pool_col = [c for c in panel_df.columns if c.startswith("in_pool_")]
    if pool_col:
        panel_df = panel_df[panel_df[pool_col[0]].astype(bool)].copy()

    # Identify which features actually exist in the panel
    available = [f for f in ALL_FEATURES if f in panel_df.columns]
    missing = [f for f in ALL_FEATURES if f not in panel_df.columns]
    if missing:
        print(f"  Warning: {len(missing)} features not in panel: {missing[:5]}...")

    # Also check for alternate column names
    alt_map: dict[str, str] = {}
    if "score" not in panel_df.columns and "transparent_score" in panel_df.columns:
        alt_map["score"] = "transparent_score"
    if "path_support_norm" not in panel_df.columns and "path_support_raw" in panel_df.columns:
        alt_map["path_support_norm"] = "path_support_raw"

    metric_rows: list[dict[str, Any]] = []

    groups = list(panel_df.groupby(["cutoff_year_t", "horizon"], sort=True))
    total_cells = len(groups)

    for cell_idx, ((cutoff_year_t, horizon), group) in enumerate(groups):
        pos_df = group[group["appears_within_h"].astype(bool)]
        positives = {
            (str(r.u), str(r.v)) for r in pos_df[["u", "v"]].itertuples(index=False)
        }
        if not positives:
            continue

        if cell_idx % 4 == 0:
            print(f"  Cell {cell_idx+1}/{total_cells}: cutoff={cutoff_year_t}, h={horizon}, positives={len(positives)}")

        for feat in available:
            col = alt_map.get(feat, feat)
            scores = _safe_numeric(group[col])

            ranked = (
                group[["u", "v"]].copy()
                .assign(score=scores.values)
                .sort_values(["score", "u", "v"], ascending=[False, True, True])
                .reset_index(drop=True)
            )
            ranked["rank"] = ranked.index + 1

            metrics = evaluate_binary_ranking(
                ranked[["u", "v", "score", "rank"]],
                positives=positives,
                k_values=K_VALUES,
            )

            row: dict[str, Any] = {
                "feature": feat,
                "family": FEATURE_TO_FAMILY.get(feat, "unknown"),
                "cutoff_year_t": int(cutoff_year_t),
                "horizon": int(horizon),
                "n_positives": int(len(positives)),
                "mrr": float(metrics.get("mrr", 0.0)),
            }
            for k in K_VALUES:
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
            metric_rows.append(row)

    return pd.DataFrame(metric_rows)


def _summarize(metric_df: pd.DataFrame) -> pd.DataFrame:
    agg_dict: dict[str, tuple[str, str]] = {
        "mean_mrr": ("mrr", "mean"),
        "family": ("family", "first"),
    }
    for k in K_VALUES:
        agg_dict[f"mean_precision_at_{k}"] = (f"precision_at_{k}", "mean")
        agg_dict[f"mean_recall_at_{k}"] = (f"recall_at_{k}", "mean")
        agg_dict[f"mean_hits_at_{k}"] = (f"hits_at_{k}", "mean")
    agg_dict["n_cutoffs"] = ("cutoff_year_t", "nunique")

    summary = (
        metric_df.groupby(["feature", "horizon"], as_index=False)
        .agg(**agg_dict)
        .sort_values(["horizon", "mean_precision_at_100", "mean_mrr"], ascending=[True, False, False])
    )
    return summary


# --------------------------------------------------------------------------- #
# Markdown note
# --------------------------------------------------------------------------- #
def _write_note(summary_df: pd.DataFrame, note_path: Path) -> None:
    lines = [
        "# Single-Feature Importance Ranking",
        "",
        "## Question",
        "",
        "Which individual graph features carry the most screening signal when used alone?",
        "",
        "## Method",
        "",
        "For each of the reranker's features, rank candidates by that feature in isolation",
        "and evaluate on the same walk-forward benchmark. This is directly comparable to the",
        "141-feature ablation in Gu and Krenn (2025, Impact4Cast).",
        "",
    ]

    for horizon in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == horizon].head(15).copy()
        lines.append(f"## Top 15 features at h={int(horizon)}")
        lines.append("")
        lines.append("| Rank | Feature | Family | P@100 | R@100 | MRR | Hits@100 |")
        lines.append("|------|---------|--------|-------|-------|-----|----------|")
        for rank_idx, row in enumerate(block.itertuples(index=False), 1):
            lines.append(
                f"| {rank_idx} | {row.feature} | {row.family} | "
                f"{row.mean_precision_at_100:.6f} | {row.mean_recall_at_100:.6f} | "
                f"{row.mean_mrr:.6f} | {row.mean_hits_at_100:.1f} |"
            )
        lines.append("")

        # Family summary
        family_block = (
            summary_df[summary_df["horizon"] == horizon]
            .groupby("family", as_index=False)
            .agg(
                best_precision_at_100=("mean_precision_at_100", "max"),
                mean_precision_at_100=("mean_precision_at_100", "mean"),
                n_features=("feature", "count"),
            )
            .sort_values("best_precision_at_100", ascending=False)
        )
        lines.append(f"### Family summary at h={int(horizon)}")
        lines.append("")
        lines.append("| Family | Best P@100 | Mean P@100 | # Features |")
        lines.append("|--------|-----------|-----------|------------|")
        for row in family_block.itertuples(index=False):
            lines.append(
                f"| {row.family} | {row.best_precision_at_100:.6f} | "
                f"{row.mean_precision_at_100:.6f} | {row.n_features} |"
            )
        lines.append("")

    # Interpretation
    lines.extend([
        "## Interpretation",
        "",
        "Features that rank highly as standalone predictors are doing real screening work.",
        "If directed-graph-specific features (path_support, mediator_count, gap_bonus,",
        "boundary_flag, nearby_closure_density) appear in the top ranks, that directly",
        "strengthens the case that the directed causal extraction adds value beyond",
        "what co-occurrence or degree-based signals deliver.",
        "",
        "If popularity-adjacent features (support_degree_product, cooc_count) dominate,",
        "that confirms the co-occurrence ablation result: cumulative advantage is the",
        "strongest single signal, and the reranker's advantage comes from combining",
        "directed features rather than from any one feature alone.",
    ])

    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_figures(summary_df: pd.DataFrame) -> None:
    for horizon in [5, 10]:
        block = summary_df[summary_df["horizon"] == horizon].head(15).copy()
        if block.empty:
            continue
        block = block.sort_values("mean_precision_at_100", ascending=True)

        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        colors = [FAMILY_COLORS.get(family, "#999999") for family in block["family"]]
        ax.barh(
            range(len(block)),
            block["mean_precision_at_100"],
            color=colors,
            edgecolor="white",
            linewidth=0.5,
        )
        ax.set_yticks(range(len(block)))
        ax.set_yticklabels([feat.replace("_", " ").title() for feat in block["feature"]], fontsize=8)
        ax.set_xlabel("Precision@100 (single-feature ranking)")
        legend_patches = [
            mpatches.Patch(color=color, label=family.replace("_", " ").title())
            for family, color in FAMILY_COLORS.items()
        ]
        ax.legend(handles=legend_patches, loc="lower right", fontsize=8, title="Feature family")
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"feature_importance_h{horizon}.png")
        fig.savefig(OUT_DIR / f"feature_importance_h{horizon}.pdf")
        plt.close(fig)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    print(f"Loading panel from {PANEL_CACHE} ...")
    if not PANEL_CACHE.exists():
        print(f"ERROR: Panel cache not found at {PANEL_CACHE}")
        sys.exit(1)

    panel_df = pd.read_parquet(PANEL_CACHE)
    panel_df = panel_df[panel_df["cutoff_year_t"].between(1990, 2015)].copy()
    print(f"  Panel rows: {len(panel_df):,}")
    print(f"  Columns: {len(panel_df.columns)}")

    # Check available features
    available = [f for f in ALL_FEATURES if f in panel_df.columns]
    print(f"  Available features: {len(available)} / {len(ALL_FEATURES)}")

    # Also try alternate names
    if "score" not in panel_df.columns and "transparent_score" in panel_df.columns:
        print("  Note: using 'transparent_score' as 'score'")
    if "path_support_norm" not in panel_df.columns and "path_support_raw" in panel_df.columns:
        print("  Note: using 'path_support_raw' as 'path_support_norm'")

    print("\nEvaluating single features ...")
    metric_df = _evaluate_single_features(panel_df)
    summary_df = _summarize(metric_df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_df.to_csv(OUT_DIR / "single_feature_panel.csv", index=False)
    summary_df.to_csv(OUT_DIR / "single_feature_summary.csv", index=False)
    _make_figures(summary_df)

    payload = {
        "n_features_evaluated": int(metric_df["feature"].nunique()),
        "horizons": sorted(metric_df["horizon"].unique().tolist()),
        "top5_by_horizon": {},
    }
    for h in sorted(summary_df["horizon"].unique()):
        top5 = summary_df[summary_df["horizon"] == h].head(5)
        payload["top5_by_horizon"][f"h={int(h)}"] = [
            {"feature": r.feature, "family": r.family, "precision_at_100": float(r.mean_precision_at_100)}
            for r in top5.itertuples(index=False)
        ]
    (OUT_DIR / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    _write_note(summary_df, NOTE_PATH)

    print("\n=== TOP 10 BY PRECISION@100 ===\n")
    for horizon in sorted(summary_df["horizon"].unique()):
        print(f"--- h={int(horizon)} ---")
        block = summary_df[summary_df["horizon"] == horizon].head(10)
        for rank_idx, r in enumerate(block.itertuples(index=False), 1):
            print(
                f"  {rank_idx:2d}. {r.feature:35s} [{r.family:14s}]  "
                f"P@100={r.mean_precision_at_100:.6f}  R@100={r.mean_recall_at_100:.6f}  "
                f"MRR={r.mean_mrr:.6f}  Hits@100={r.mean_hits_at_100:.1f}"
            )
        print()

    print(f"Outputs written to {OUT_DIR}")
    print(f"Note written to {NOTE_PATH}")


if __name__ == "__main__":
    main()
