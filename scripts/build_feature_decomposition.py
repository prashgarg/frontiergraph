"""Feature-set decomposition: what does each feature group contribute?

Trains three reranker variants on the same walk-forward panel:
  1. cooc_only    — features computable from undirected co-occurrence
  2. directed_only — features requiring directed causal extraction
  3. all_features  — both groups combined

This directly answers: how much screening value does the directed
extraction add ON TOP OF co-occurrence?  And how much does co-occurrence
add on top of directed features?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking

# --------------------------------------------------------------------------- #
PANEL_CACHE = ROOT / "outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/48_feature_decomposition"
NOTE_PATH = ROOT / "next_steps/feature_decomposition_note.md"
K_VALUES = [50, 100, 500]

# --------------------------------------------------------------------------- #
# Feature groups
# --------------------------------------------------------------------------- #
# Directed-only: require LLM extraction of directed causal edges
DIRECTED_ONLY = [
    "path_support_norm", "motif_bonus_norm", "gap_bonus", "hub_penalty",
    "mediator_count", "motif_count",
    "source_direct_out_degree", "target_direct_in_degree", "direct_degree_product",
    "source_mean_stability", "target_mean_stability", "pair_mean_stability",
    "source_evidence_diversity", "target_evidence_diversity", "pair_evidence_diversity_mean",
    "boundary_flag", "gap_like_flag", "nearby_closure_density",
]

# Co-occurrence-available: computable from undirected co-occurrence + metadata
COOC_AVAILABLE = [
    "cooc_count", "cooc_trend_norm", "field_same_group",
    "source_support_out_degree", "target_support_in_degree", "support_degree_product",
    "support_age_years", "recent_support_age_years",
    "source_recent_support_out_degree", "target_recent_support_in_degree",
    "source_recent_incident_count", "target_recent_incident_count",
    "source_recent_share", "target_recent_share",
    "source_venue_diversity", "target_venue_diversity",
    "source_source_diversity", "target_source_diversity",
    "source_mean_fwci", "target_mean_fwci", "pair_mean_fwci",
    "pair_venue_diversity_mean", "pair_source_diversity_mean",
]

ALL_FEATURES = DIRECTED_ONLY + COOC_AVAILABLE

FEATURE_SETS = {
    "directed_only": DIRECTED_ONLY,
    "cooc_only": COOC_AVAILABLE,
    "all_features": ALL_FEATURES,
}


def _safe_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


# --------------------------------------------------------------------------- #
# Simple GLM reranker (logistic, L2, walk-forward)
# --------------------------------------------------------------------------- #
def _fit_and_score(
    train_X: np.ndarray, train_y: np.ndarray,
    eval_X: np.ndarray,
    alpha: float = 0.05,
) -> np.ndarray:
    """Fit class-balanced logistic regression, return eval scores."""
    import statsmodels.api as sm

    n = len(train_y)
    n_pos = train_y.sum()
    n_neg = n - n_pos
    if n_pos < 2 or n_neg < 2:
        return np.zeros(len(eval_X))

    weights = np.where(train_y == 1, n / (2 * n_pos), n / (2 * n_neg))

    try:
        model = sm.GLM(
            train_y, sm.add_constant(train_X),
            family=sm.families.Binomial(),
            freq_weights=weights,
        )
        result = model.fit_regularized(alpha=alpha, L1_wt=0.0, maxiter=200)
        scores = result.predict(sm.add_constant(eval_X))
        return np.asarray(scores, dtype=float)
    except Exception:
        return np.zeros(len(eval_X))


def _run_reranker(panel_df: pd.DataFrame, feature_cols: list[str], alpha: float = 0.05) -> pd.DataFrame:
    """Walk-forward evaluation with given feature set."""
    # Standardize features
    available = [f for f in feature_cols if f in panel_df.columns]
    if not available:
        return pd.DataFrame()

    metric_rows: list[dict[str, Any]] = []

    for horizon in sorted(panel_df["horizon"].unique()):
        h_panel = panel_df[panel_df["horizon"] == horizon].copy()
        cutoffs = sorted(h_panel["cutoff_year_t"].unique())

        for eval_t in cutoffs:
            train_mask = h_panel["cutoff_year_t"] < eval_t
            eval_mask = h_panel["cutoff_year_t"] == eval_t

            train_rows = h_panel[train_mask]
            eval_rows = h_panel[eval_mask]

            if len(train_rows) < 50 or len(eval_rows) < 50:
                continue

            train_y = train_rows["appears_within_h"].astype(float).values
            if train_y.sum() < 2 or (len(train_y) - train_y.sum()) < 2:
                continue

            # Standardize
            X_train_raw = train_rows[available].apply(_safe_numeric).values
            X_eval_raw = eval_rows[available].apply(_safe_numeric).values

            mean = X_train_raw.mean(axis=0)
            std = X_train_raw.std(axis=0)
            std[std < 1e-10] = 1.0

            X_train = (X_train_raw - mean) / std
            X_eval = (X_eval_raw - mean) / std

            scores = _fit_and_score(X_train, train_y, X_eval, alpha=alpha)

            eval_df = eval_rows[["u", "v"]].copy()
            eval_df["score"] = scores
            eval_df = eval_df.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
            eval_df["rank"] = eval_df.index + 1

            positives = {
                (str(r.u), str(r.v))
                for r in eval_rows[eval_rows["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)
            }
            if not positives:
                continue

            metrics = evaluate_binary_ranking(
                eval_df[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES
            )

            row: dict[str, Any] = {
                "cutoff_year_t": int(eval_t),
                "horizon": int(horizon),
                "n_positives": len(positives),
                "mrr": float(metrics.get("mrr", 0.0)),
            }
            for k in K_VALUES:
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
            metric_rows.append(row)

    return pd.DataFrame(metric_rows)


# --------------------------------------------------------------------------- #
def main() -> None:
    print(f"Loading panel ...")
    panel_df = pd.read_parquet(PANEL_CACHE)
    pool_col = [c for c in panel_df.columns if c.startswith("in_pool_")]
    if pool_col:
        panel_df = panel_df[panel_df[pool_col[0]].astype(bool)].copy()
    print(f"  Panel rows: {len(panel_df):,}")

    results: dict[str, pd.DataFrame] = {}

    for name, features in FEATURE_SETS.items():
        available = [f for f in features if f in panel_df.columns]
        print(f"\n--- {name}: {len(available)} features ---")
        metric_df = _run_reranker(panel_df, available, alpha=0.05)
        results[name] = metric_df

    # Also run simple baselines for comparison
    print("\n--- baselines ---")
    baseline_rows: list[dict[str, Any]] = []
    for (cutoff, horizon), group in panel_df.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives = {
            (str(r.u), str(r.v))
            for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)
        }
        if not positives:
            continue
        for bname, bcol in [("pref_attach", "support_degree_product"), ("cooc_count", "cooc_count")]:
            ranked = (
                group[["u", "v", bcol]].rename(columns={bcol: "score"})
                .sort_values(["score", "u", "v"], ascending=[False, True, True])
                .reset_index(drop=True)
            )
            ranked["rank"] = ranked.index + 1
            metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES)
            row: dict[str, Any] = {
                "cutoff_year_t": int(cutoff), "horizon": int(horizon),
                "n_positives": len(positives), "mrr": float(metrics.get("mrr", 0.0)),
            }
            for k in K_VALUES:
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
            baseline_rows.append({"model": bname, **row})

    baseline_df = pd.DataFrame(baseline_rows)

    # Summarize
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for name, mdf in results.items():
        if mdf.empty:
            continue
        for h in sorted(mdf["horizon"].unique()):
            block = mdf[mdf["horizon"] == h]
            summary_rows.append({
                "model": f"reranker_{name}",
                "horizon": int(h),
                "mean_precision_at_100": float(block["precision_at_100"].mean()),
                "mean_recall_at_100": float(block["recall_at_100"].mean()),
                "mean_mrr": float(block["mrr"].mean()),
                "mean_hits_at_100": float(block["hits_at_100"].mean()),
                "n_cutoffs": int(block["cutoff_year_t"].nunique()),
            })

    for bname in ["pref_attach", "cooc_count"]:
        bsub = baseline_df[baseline_df["model"] == bname]
        for h in sorted(bsub["horizon"].unique()):
            block = bsub[bsub["horizon"] == h]
            summary_rows.append({
                "model": bname,
                "horizon": int(h),
                "mean_precision_at_100": float(block["precision_at_100"].mean()),
                "mean_recall_at_100": float(block["recall_at_100"].mean()),
                "mean_mrr": float(block["mrr"].mean()),
                "mean_hits_at_100": float(block["hits_at_100"].mean()),
                "n_cutoffs": int(block["cutoff_year_t"].nunique()),
            })

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["horizon", "mean_precision_at_100"], ascending=[True, False]
    )
    summary_df.to_csv(OUT_DIR / "feature_decomposition_summary.csv", index=False)

    # Write note
    lines = [
        "# Feature-Set Decomposition",
        "",
        "## Question",
        "",
        "How much screening value does each feature group contribute?",
        "- `directed_only`: 18 features requiring directed causal extraction",
        "- `cooc_only`: 23 features computable from undirected co-occurrence + metadata",
        "- `all_features`: all 41 features combined",
        "",
        "All three use the same GLM logit reranker with L2 regularization (alpha=0.05)",
        "and the same walk-forward temporal split.",
        "",
        "## Results",
        "",
    ]
    for h in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == h]
        lines.append(f"### h={int(h)}")
        lines.append("")
        lines.append("| Model | P@100 | R@100 | MRR | Hits@100 |")
        lines.append("|-------|-------|-------|-----|----------|")
        for r in block.itertuples(index=False):
            lines.append(
                f"| {r.model} | {r.mean_precision_at_100:.6f} "
                f"| {r.mean_recall_at_100:.6f} | {r.mean_mrr:.6f} "
                f"| {r.mean_hits_at_100:.1f} |"
            )
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "The decomposition answers three questions:",
        "1. Do directed-only features beat co-occurrence baselines on their own?",
        "2. Do co-occurrence features beat directed-only features on their own?",
        "3. Does combining both add value over either alone?",
        "",
        "If the combined reranker substantially outperforms both subsets,",
        "the directed extraction adds value ON TOP OF co-occurrence (additive claim).",
        "If directed-only features alone already beat co-occurrence baselines,",
        "that is an even stronger result (substitutive claim).",
    ])

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n=== SUMMARY ===\n")
    for h in sorted(summary_df["horizon"].unique()):
        print(f"--- h={int(h)} ---")
        block = summary_df[summary_df["horizon"] == h]
        for r in block.itertuples(index=False):
            print(
                f"  {r.model:30s}  P@100={r.mean_precision_at_100:.6f}  "
                f"R@100={r.mean_recall_at_100:.6f}  MRR={r.mean_mrr:.6f}  "
                f"Hits={r.mean_hits_at_100:.1f}"
            )
        print()

    print(f"Outputs: {OUT_DIR}")
    print(f"Note: {NOTE_PATH}")


if __name__ == "__main__":
    main()
