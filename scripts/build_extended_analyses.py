"""Extended analyses bundle: h=3/h=15 reranker, failure modes,
journal-quality realization split, and temporal generalization test.

This script rebuilds the feature panel with all four horizons,
then runs each analysis sequentially.
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

from src.analysis.learned_reranker import build_candidate_feature_panel
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking
from src.analysis.common import ensure_output_dir
from src.utils import load_config, load_corpus

# --------------------------------------------------------------------------- #
# Paths & config
# --------------------------------------------------------------------------- #
CORPUS_PATH = "data/processed/research_allocation_v2/hybrid_corpus.parquet"
CONFIG_PATH = "config/config_causalclaims.yaml"
BEST_CONFIG_PATH = "outputs/paper/03_model_search/best_config.yaml"
PAPER_META_PATH = "data/processed/research_allocation_v2/hybrid_papers_funding.parquet"
CONCEPTS_CSV = ROOT / "site/public/data/v2/central_concepts.csv"

EXTENDED_PANEL_PATH = ROOT / "outputs/paper/49_extended_analyses/extended_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/49_extended_analyses"
NOTE_PATH = ROOT / "next_steps/extended_analyses_note.md"

CUTOFF_YEARS = [1990, 1995, 2000, 2005, 2010, 2015]
HORIZONS = [3, 5, 10, 15]
POOL_SIZE = 10000
K_VALUES = [50, 100, 500]


def _safe_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


# --------------------------------------------------------------------------- #
# Panel building
# --------------------------------------------------------------------------- #
def build_extended_panel() -> pd.DataFrame:
    if EXTENDED_PANEL_PATH.exists():
        print(f"Loading cached extended panel from {EXTENDED_PANEL_PATH}")
        return pd.read_parquet(EXTENDED_PANEL_PATH)

    print("Building extended panel (h=3,5,10,15) — this may take a while...")
    corpus_df = load_corpus(CORPUS_PATH)
    config = load_config(CONFIG_PATH)
    cfg = candidate_cfg_from_config(config, best_config_path=BEST_CONFIG_PATH)
    paper_meta_path = Path(PAPER_META_PATH)
    paper_meta_df = pd.read_parquet(paper_meta_path) if paper_meta_path.exists() else None

    panel_df = build_candidate_feature_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=CUTOFF_YEARS,
        horizons=HORIZONS,
        pool_sizes=[POOL_SIZE],
        paper_meta_df=paper_meta_df,
    )

    EXTENDED_PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel_df.to_parquet(EXTENDED_PANEL_PATH, index=False)
    print(f"Extended panel saved: {len(panel_df)} rows")
    return panel_df


# --------------------------------------------------------------------------- #
# Reranker training (simple GLM, walk-forward)
# --------------------------------------------------------------------------- #
DIRECTED_ONLY = [
    "path_support_norm", "motif_bonus_norm", "gap_bonus", "hub_penalty",
    "mediator_count", "motif_count",
    "source_direct_out_degree", "target_direct_in_degree", "direct_degree_product",
    "source_mean_stability", "target_mean_stability", "pair_mean_stability",
    "source_evidence_diversity", "target_evidence_diversity", "pair_evidence_diversity_mean",
    "boundary_flag", "gap_like_flag", "nearby_closure_density",
]
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


def _fit_glm(train_X, train_y, eval_X, alpha=0.05):
    import statsmodels.api as sm
    n = len(train_y)
    n_pos = train_y.sum()
    n_neg = n - n_pos
    if n_pos < 2 or n_neg < 2:
        return np.zeros(len(eval_X))
    weights = np.where(train_y == 1, n / (2 * n_pos), n / (2 * n_neg))
    try:
        model = sm.GLM(train_y, sm.add_constant(train_X), family=sm.families.Binomial(), freq_weights=weights)
        result = model.fit_regularized(alpha=alpha, L1_wt=0.0, maxiter=200)
        return np.asarray(result.predict(sm.add_constant(eval_X)), dtype=float)
    except Exception:
        return np.zeros(len(eval_X))


def run_reranker_walkforward(panel_df, feature_cols, alpha=0.05, restrict_train_cutoffs=None):
    """Walk-forward reranker. Returns panel with 'reranker_score' column added."""
    available = [f for f in feature_cols if f in panel_df.columns]
    if not available:
        return panel_df.assign(reranker_score=0.0)

    scores_all = pd.Series(np.zeros(len(panel_df)), index=panel_df.index)

    for horizon in sorted(panel_df["horizon"].unique()):
        h_mask = panel_df["horizon"] == horizon
        h_panel = panel_df[h_mask]
        cutoffs = sorted(h_panel["cutoff_year_t"].unique())

        for eval_t in cutoffs:
            if restrict_train_cutoffs is not None:
                train_mask = h_mask & panel_df["cutoff_year_t"].isin(restrict_train_cutoffs) & (panel_df["cutoff_year_t"] < eval_t)
            else:
                train_mask = h_mask & (panel_df["cutoff_year_t"] < eval_t)
            eval_mask = h_mask & (panel_df["cutoff_year_t"] == eval_t)

            train_rows = panel_df[train_mask]
            eval_rows = panel_df[eval_mask]
            if len(train_rows) < 50 or len(eval_rows) < 50:
                continue

            train_y = train_rows["appears_within_h"].astype(float).values
            if train_y.sum() < 2 or (len(train_y) - train_y.sum()) < 2:
                continue

            X_train = train_rows[available].apply(_safe_numeric).values
            X_eval = eval_rows[available].apply(_safe_numeric).values
            mean = X_train.mean(axis=0)
            std = X_train.std(axis=0)
            std[std < 1e-10] = 1.0
            X_train = (X_train - mean) / std
            X_eval = (X_eval - mean) / std

            s = _fit_glm(X_train, train_y, X_eval, alpha=alpha)
            scores_all.loc[eval_rows.index] = s

    return panel_df.assign(reranker_score=scores_all)


# --------------------------------------------------------------------------- #
# Analysis 1: Reranker at all horizons
# --------------------------------------------------------------------------- #
def analysis_reranker_all_horizons(panel_df):
    print("\n=== ANALYSIS 1: Reranker at h=3,5,10,15 ===")
    pool_col = [c for c in panel_df.columns if c.startswith("in_pool_")]
    pdf = panel_df[panel_df[pool_col[0]].astype(bool)].copy() if pool_col else panel_df.copy()

    pdf = run_reranker_walkforward(pdf, ALL_FEATURES, alpha=0.05)

    # Also compute baselines
    pdf["pref_attach_score"] = _safe_numeric(pdf["support_degree_product"])
    pdf["cooc_score"] = _safe_numeric(pdf["cooc_count"])
    pdf["direct_degree_score"] = _safe_numeric(pdf["direct_degree_product"])
    pdf["graph_score_val"] = _safe_numeric(pdf["transparent_score"] if "transparent_score" in pdf.columns else pdf["score"])

    models = {
        "reranker": "reranker_score",
        "pref_attach": "pref_attach_score",
        "cooc_count": "cooc_score",
        "direct_degree_product": "direct_degree_score",
        "graph_score": "graph_score_val",
    }

    rows = []
    for (cutoff, horizon), group in pdf.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives = {(str(r.u), str(r.v)) for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)}
        if not positives:
            continue
        for mname, mcol in models.items():
            ranked = group[["u", "v", mcol]].rename(columns={mcol: "score"}).sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
            ranked["rank"] = ranked.index + 1
            metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES)
            row = {"model": mname, "cutoff_year_t": int(cutoff), "horizon": int(horizon), "n_positives": len(positives), "mrr": float(metrics.get("mrr", 0.0))}
            for k in K_VALUES:
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
            rows.append(row)

    metric_df = pd.DataFrame(rows)
    summary = metric_df.groupby(["model", "horizon"], as_index=False).agg(
        mean_p100=("precision_at_100", "mean"), mean_r100=("recall_at_100", "mean"),
        mean_mrr=("mrr", "mean"), mean_hits100=("hits_at_100", "mean"), n_cutoffs=("cutoff_year_t", "nunique")
    ).sort_values(["horizon", "mean_p100"], ascending=[True, False])

    metric_df.to_csv(OUT_DIR / "reranker_all_horizons_panel.csv", index=False)
    summary.to_csv(OUT_DIR / "reranker_all_horizons_summary.csv", index=False)

    print("\nReranker at all horizons:")
    for h in sorted(summary["horizon"].unique()):
        print(f"\n  h={int(h)}:")
        for r in summary[summary["horizon"] == h].itertuples(index=False):
            print(f"    {r.model:25s}  P@100={r.mean_p100:.6f}  R@100={r.mean_r100:.6f}  MRR={r.mean_mrr:.6f}  Hits={r.mean_hits100:.1f}")

    return pdf, metric_df, summary


# --------------------------------------------------------------------------- #
# Analysis 2: Failure mode analysis
# --------------------------------------------------------------------------- #
def analysis_failure_modes(pdf):
    print("\n=== ANALYSIS 2: Failure mode analysis ===")
    rows = []
    for (cutoff, horizon), group in pdf.groupby(["cutoff_year_t", "horizon"], sort=True):
        ranked = group.sort_values("reranker_score", ascending=False).reset_index(drop=True)
        ranked["reranker_rank"] = ranked.index + 1
        top100 = ranked.head(100)
        hits = top100[top100["appears_within_h"].astype(bool)]
        misses = top100[~top100["appears_within_h"].astype(bool)]

        for label, sub in [("hit", hits), ("miss", misses)]:
            if sub.empty:
                continue
            rows.append({
                "cutoff_year_t": int(cutoff), "horizon": int(horizon), "type": label,
                "count": len(sub),
                "mean_cooc_count": float(_safe_numeric(sub["cooc_count"]).mean()),
                "mean_support_degree_product": float(_safe_numeric(sub["support_degree_product"]).mean()),
                "mean_direct_degree_product": float(_safe_numeric(sub["direct_degree_product"]).mean()),
                "mean_pair_mean_fwci": float(_safe_numeric(sub["pair_mean_fwci"]).mean()),
                "mean_pair_mean_stability": float(_safe_numeric(sub["pair_mean_stability"]).mean()),
                "mean_boundary_flag": float(_safe_numeric(sub["boundary_flag"]).mean()),
                "mean_gap_like_flag": float(_safe_numeric(sub["gap_like_flag"]).mean()),
                "mean_pair_evidence_diversity": float(_safe_numeric(sub["pair_evidence_diversity_mean"]).mean()),
            })

        # Also: realized links that reranker misses (rank > 500)
        bottom_realized = ranked[(ranked["reranker_rank"] > 500) & ranked["appears_within_h"].astype(bool)]
        if not bottom_realized.empty:
            rows.append({
                "cutoff_year_t": int(cutoff), "horizon": int(horizon), "type": "missed_realized",
                "count": len(bottom_realized),
                "mean_cooc_count": float(_safe_numeric(bottom_realized["cooc_count"]).mean()),
                "mean_support_degree_product": float(_safe_numeric(bottom_realized["support_degree_product"]).mean()),
                "mean_direct_degree_product": float(_safe_numeric(bottom_realized["direct_degree_product"]).mean()),
                "mean_pair_mean_fwci": float(_safe_numeric(bottom_realized["pair_mean_fwci"]).mean()),
                "mean_pair_mean_stability": float(_safe_numeric(bottom_realized["pair_mean_stability"]).mean()),
                "mean_boundary_flag": float(_safe_numeric(bottom_realized["boundary_flag"]).mean()),
                "mean_gap_like_flag": float(_safe_numeric(bottom_realized["gap_like_flag"]).mean()),
                "mean_pair_evidence_diversity": float(_safe_numeric(bottom_realized["pair_evidence_diversity_mean"]).mean()),
            })

    fm_df = pd.DataFrame(rows)
    fm_summary = fm_df.groupby(["type", "horizon"], as_index=False).agg(
        mean_count=("count", "mean"),
        mean_cooc=("mean_cooc_count", "mean"),
        mean_sdp=("mean_support_degree_product", "mean"),
        mean_ddp=("mean_direct_degree_product", "mean"),
        mean_fwci=("mean_pair_mean_fwci", "mean"),
        mean_stability=("mean_pair_mean_stability", "mean"),
        mean_boundary=("mean_boundary_flag", "mean"),
        mean_gap=("mean_gap_like_flag", "mean"),
        mean_evid_div=("mean_pair_evidence_diversity", "mean"),
    )
    fm_df.to_csv(OUT_DIR / "failure_modes_panel.csv", index=False)
    fm_summary.to_csv(OUT_DIR / "failure_modes_summary.csv", index=False)

    print("\nFailure mode profiles (averaged across cutoffs):")
    for h in sorted(fm_summary["horizon"].unique()):
        print(f"\n  h={int(h)}:")
        for r in fm_summary[fm_summary["horizon"] == h].itertuples(index=False):
            print(f"    {r.type:20s}  n={r.mean_count:.0f}  cooc={r.mean_cooc:.1f}  ddp={r.mean_ddp:.0f}  fwci={r.mean_fwci:.2f}  boundary={r.mean_boundary:.3f}  gap={r.mean_gap:.3f}")

    return fm_df, fm_summary


# --------------------------------------------------------------------------- #
# Analysis 3: Journal-quality realization split
# --------------------------------------------------------------------------- #
def analysis_journal_quality(pdf):
    print("\n=== ANALYSIS 3: Journal-quality realization split ===")

    # Load paper metadata with FWCI
    paper_meta_path = Path(PAPER_META_PATH)
    if not paper_meta_path.exists():
        print("  Paper metadata not found — skipping journal-quality analysis")
        return None, None

    paper_meta = pd.read_parquet(paper_meta_path)
    # Get corpus to find which papers realize each edge
    corpus_df = load_corpus(CORPUS_PATH)

    # For each realized link, find the FWCI of the realizing paper(s)
    # We use first_realized_year and the corpus to find realizing papers
    realized = pdf[pdf["appears_within_h"].astype(bool)].copy()
    if realized.empty:
        print("  No realized links found")
        return None, None

    # Join: for each (u, v, first_realized_year), find papers in that year with that edge
    # Simplified: use the corpus to get paper-level FWCI for papers published in the realization year
    if "fwci" in paper_meta.columns and "work_id" in paper_meta.columns:
        paper_fwci = paper_meta[["work_id", "fwci"]].dropna().drop_duplicates("work_id")
        paper_fwci_map = dict(zip(paper_fwci["work_id"].astype(str), paper_fwci["fwci"].astype(float)))
    else:
        # Try to compute from corpus
        if "fwci" in corpus_df.columns:
            paper_fwci_map = corpus_df.groupby("work_id")["fwci"].first().to_dict()
        else:
            print("  No FWCI column in paper metadata or corpus — using pair_mean_fwci as proxy")
            # Fallback: split realized links by their endpoint FWCI
            median_fwci = _safe_numeric(realized["pair_mean_fwci"]).median()

            rows = []
            for (cutoff, horizon), group in pdf.groupby(["cutoff_year_t", "horizon"], sort=True):
                positives = {(str(r.u), str(r.v)) for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)}
                if not positives:
                    continue

                fwci = _safe_numeric(group["pair_mean_fwci"])
                cell_median = fwci.median()

                for regime, mask in [("low_fwci_endpoint", fwci <= cell_median), ("high_fwci_endpoint", fwci > cell_median)]:
                    sub = group[mask]
                    sub_positives = positives & {(str(r.u), str(r.v)) for r in sub[["u", "v"]].itertuples(index=False)}
                    if not sub_positives or len(sub) < 50:
                        continue

                    for mname, mcol in [("reranker", "reranker_score"), ("pref_attach", "pref_attach_score")]:
                        ranked = sub[["u", "v", mcol]].rename(columns={mcol: "score"}).sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
                        ranked["rank"] = ranked.index + 1
                        metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=sub_positives, k_values=K_VALUES)
                        rows.append({
                            "model": mname, "regime": regime, "cutoff_year_t": int(cutoff),
                            "horizon": int(horizon), "n_positives": len(sub_positives),
                            "precision_at_100": float(metrics.get("precision_at_100", 0.0)),
                            "recall_at_100": float(metrics.get("recall_at_100", 0.0)),
                            "mrr": float(metrics.get("mrr", 0.0)),
                            "hits_at_100": int(metrics.get("hits_at_100", 0)),
                        })

            jq_df = pd.DataFrame(rows)
            jq_summary = jq_df.groupby(["regime", "model", "horizon"], as_index=False).agg(
                mean_p100=("precision_at_100", "mean"), mean_r100=("recall_at_100", "mean"),
                mean_mrr=("mrr", "mean"), mean_hits100=("hits_at_100", "mean"),
            ).sort_values(["horizon", "regime", "mean_p100"], ascending=[True, True, False])

            jq_df.to_csv(OUT_DIR / "journal_quality_panel.csv", index=False)
            jq_summary.to_csv(OUT_DIR / "journal_quality_summary.csv", index=False)

            print("\nJournal-quality split (endpoint FWCI proxy):")
            for h in sorted(jq_summary["horizon"].unique()):
                print(f"\n  h={int(h)}:")
                for r in jq_summary[jq_summary["horizon"] == h].itertuples(index=False):
                    print(f"    {r.regime:25s} {r.model:15s}  P@100={r.mean_p100:.6f}  Hits={r.mean_hits100:.1f}")

            return jq_df, jq_summary

    return None, None


# --------------------------------------------------------------------------- #
# Analysis 4: Temporal generalization test
# --------------------------------------------------------------------------- #
def analysis_temporal_generalization(panel_df):
    print("\n=== ANALYSIS 4: Temporal generalization test ===")
    pool_col = [c for c in panel_df.columns if c.startswith("in_pool_")]
    pdf = panel_df[panel_df[pool_col[0]].astype(bool)].copy() if pool_col else panel_df.copy()

    # Train only on 1990-2005, evaluate on 2010-2015
    train_cutoffs = [1990, 1995, 2000, 2005]
    eval_cutoffs = [2010, 2015]

    pdf_restricted = run_reranker_walkforward(pdf, ALL_FEATURES, alpha=0.05, restrict_train_cutoffs=train_cutoffs)
    pdf_restricted["pref_attach_score"] = _safe_numeric(pdf_restricted["support_degree_product"])

    rows = []
    for (cutoff, horizon), group in pdf_restricted.groupby(["cutoff_year_t", "horizon"], sort=True):
        era = "train_era" if cutoff in train_cutoffs else "held_out_era"
        positives = {(str(r.u), str(r.v)) for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)}
        if not positives:
            continue

        for mname, mcol in [("reranker_restricted", "reranker_score"), ("pref_attach", "pref_attach_score")]:
            ranked = group[["u", "v", mcol]].rename(columns={mcol: "score"}).sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
            ranked["rank"] = ranked.index + 1
            metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES)
            rows.append({
                "model": mname, "era": era, "cutoff_year_t": int(cutoff),
                "horizon": int(horizon), "n_positives": len(positives),
                "precision_at_100": float(metrics.get("precision_at_100", 0.0)),
                "recall_at_100": float(metrics.get("recall_at_100", 0.0)),
                "mrr": float(metrics.get("mrr", 0.0)),
                "hits_at_100": int(metrics.get("hits_at_100", 0)),
            })

    tg_df = pd.DataFrame(rows)
    tg_summary = tg_df.groupby(["era", "model", "horizon"], as_index=False).agg(
        mean_p100=("precision_at_100", "mean"), mean_r100=("recall_at_100", "mean"),
        mean_mrr=("mrr", "mean"), mean_hits100=("hits_at_100", "mean"),
        n_cutoffs=("cutoff_year_t", "nunique"),
    ).sort_values(["horizon", "era", "mean_p100"], ascending=[True, True, False])

    tg_df.to_csv(OUT_DIR / "temporal_generalization_panel.csv", index=False)
    tg_summary.to_csv(OUT_DIR / "temporal_generalization_summary.csv", index=False)

    print("\nTemporal generalization (train on 1990-2005, evaluate on 2010-2015):")
    for h in sorted(tg_summary["horizon"].unique()):
        print(f"\n  h={int(h)}:")
        for r in tg_summary[tg_summary["horizon"] == h].itertuples(index=False):
            print(f"    {r.era:15s} {r.model:25s}  P@100={r.mean_p100:.6f}  Hits={r.mean_hits100:.1f}  (n_cutoffs={r.n_cutoffs})")

    return tg_df, tg_summary


# --------------------------------------------------------------------------- #
# Note writer
# --------------------------------------------------------------------------- #
def write_note(horizon_summary, fm_summary, jq_summary, tg_summary):
    lines = ["# Extended Analyses Note", ""]

    # Analysis 1
    lines.extend(["## Analysis 1: Reranker at all horizons (h=3,5,10,15)", ""])
    if horizon_summary is not None:
        for h in sorted(horizon_summary["horizon"].unique()):
            block = horizon_summary[horizon_summary["horizon"] == h]
            lines.append(f"### h={int(h)}")
            lines.append("| Model | P@100 | R@100 | MRR | Hits@100 |")
            lines.append("|-------|-------|-------|-----|----------|")
            for r in block.itertuples(index=False):
                lines.append(f"| {r.model} | {r.mean_p100:.6f} | {r.mean_r100:.6f} | {r.mean_mrr:.6f} | {r.mean_hits100:.1f} |")
            lines.append("")

    # Analysis 2
    lines.extend(["## Analysis 2: Failure mode profiles", ""])
    if fm_summary is not None:
        lines.append("| Type | Horizon | Count | CoOc | DirectDegProd | FWCI | Boundary | Gap |")
        lines.append("|------|---------|-------|------|---------------|------|----------|-----|")
        for r in fm_summary.itertuples(index=False):
            lines.append(f"| {r.type} | {r.horizon} | {r.mean_count:.0f} | {r.mean_cooc:.1f} | {r.mean_ddp:.0f} | {r.mean_fwci:.2f} | {r.mean_boundary:.3f} | {r.mean_gap:.3f} |")
        lines.append("")

    # Analysis 3
    lines.extend(["## Analysis 3: Journal-quality realization split", ""])
    if jq_summary is not None:
        for h in sorted(jq_summary["horizon"].unique()):
            block = jq_summary[jq_summary["horizon"] == h]
            lines.append(f"### h={int(h)}")
            lines.append("| Regime | Model | P@100 | Hits@100 |")
            lines.append("|--------|-------|-------|----------|")
            for r in block.itertuples(index=False):
                lines.append(f"| {r.regime} | {r.model} | {r.mean_p100:.6f} | {r.mean_hits100:.1f} |")
            lines.append("")

    # Analysis 4
    lines.extend(["## Analysis 4: Temporal generalization", ""])
    if tg_summary is not None:
        for h in sorted(tg_summary["horizon"].unique()):
            block = tg_summary[tg_summary["horizon"] == h]
            lines.append(f"### h={int(h)}")
            lines.append("| Era | Model | P@100 | Hits@100 | Cutoffs |")
            lines.append("|-----|-------|-------|----------|---------|")
            for r in block.itertuples(index=False):
                lines.append(f"| {r.era} | {r.model} | {r.mean_p100:.6f} | {r.mean_hits100:.1f} | {r.n_cutoffs} |")
            lines.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build or load extended panel
    panel_df = build_extended_panel()
    print(f"Panel: {len(panel_df)} rows, horizons={sorted(panel_df['horizon'].unique().tolist())}")

    # Analysis 1: Reranker at all horizons
    pdf, metric_df, horizon_summary = analysis_reranker_all_horizons(panel_df)

    # Analysis 2: Failure modes
    fm_df, fm_summary = analysis_failure_modes(pdf)

    # Analysis 3: Journal-quality split
    jq_df, jq_summary = analysis_journal_quality(pdf)

    # Analysis 4: Temporal generalization
    tg_df, tg_summary = analysis_temporal_generalization(panel_df)

    # Write note
    write_note(horizon_summary, fm_summary, jq_summary, tg_summary)

    print(f"\nAll outputs written to {OUT_DIR}")
    print(f"Note written to {NOTE_PATH}")
    print("\nDone.")


if __name__ == "__main__":
    main()
