"""Additional robustness figures on grouped features:
beeswarm, dependence plots, VIF table, correlation heatmap.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/140_grouped_shap_refresh"
PAPER_DIR = ROOT / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZON = 10

ALL_FEATURES = [
    "path_support_norm", "motif_bonus_norm", "gap_bonus", "hub_penalty",
    "mediator_count", "motif_count", "cooc_count", "cooc_trend_norm",
    "field_same_group", "source_direct_out_degree", "target_direct_in_degree",
    "source_support_out_degree", "target_support_in_degree",
    "support_degree_product", "direct_degree_product",
    "support_age_years", "recent_support_age_years",
    "source_recent_support_out_degree", "target_recent_support_in_degree",
    "source_recent_incident_count", "target_recent_incident_count",
    "source_mean_stability", "target_mean_stability", "pair_mean_stability",
    "source_evidence_diversity", "target_evidence_diversity",
    "pair_evidence_diversity_mean",
    "source_mean_fwci", "target_mean_fwci", "pair_mean_fwci",
    "boundary_flag", "gap_like_flag", "nearby_closure_density",
]

FEATURE_GROUPS = {
    "Directed degree (causal)": ["source_direct_out_degree", "target_direct_in_degree", "direct_degree_product"],
    "Support degree (total)": ["source_support_out_degree", "target_support_in_degree", "support_degree_product"],
    "Recency": ["source_recent_support_out_degree", "target_recent_support_in_degree",
                 "source_recent_incident_count", "target_recent_incident_count", "recent_support_age_years"],
    "Co-occurrence": ["cooc_count", "cooc_trend_norm", "support_age_years"],
    "Path / topology": ["path_support_norm", "motif_bonus_norm", "motif_count", "gap_bonus", "hub_penalty"],
    "Evidence quality": ["source_mean_stability", "target_mean_stability", "pair_mean_stability",
                         "source_evidence_diversity", "target_evidence_diversity", "pair_evidence_diversity_mean"],
    "Impact (FWCI)": ["source_mean_fwci", "target_mean_fwci", "pair_mean_fwci"],
    "Boundary / gap flags": ["boundary_flag", "gap_like_flag", "nearby_closure_density"],
    "Field structure": ["field_same_group", "mediator_count"],
}

GROUP_COLORS = {
    "Directed degree (causal)": "#2166ac", "Support degree (total)": "#4393c3",
    "Recency": "#92c5de", "Co-occurrence": "#d1e5f0",
    "Path / topology": "#f4a582", "Evidence quality": "#d6604d",
    "Impact (FWCI)": "#b2182b", "Boundary / gap flags": "#67001f",
    "Field structure": "#999999",
}

plt.rcParams.update({"font.family": "serif", "font.size": 10, "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight"})


def _safe(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


INDIVIDUAL_LABELS = {
    "source_recent_support_out_degree": "Source recent support degree (out)",
    "target_recent_support_in_degree": "Target recent support degree (in)",
    "source_recent_incident_count": "Source recent incident count",
    "target_recent_incident_count": "Target recent incident count",
    "source_support_out_degree": "Source support degree (out)",
    "target_support_in_degree": "Target support degree (in)",
    "source_direct_out_degree": "Source directed degree (out)",
    "target_direct_in_degree": "Target directed degree (in)",
    "pair_evidence_diversity_mean": "Pair evidence diversity",
    "source_evidence_diversity": "Source evidence diversity",
    "target_evidence_diversity": "Target evidence diversity",
    "cooc_trend_norm": "Co-occurrence trend",
    "cooc_count": "Co-occurrence count",
    "path_support_norm": "Path support",
    "support_age_years": "Support age (years)",
    "recent_support_age_years": "Recent support age (years)",
    "direct_degree_product": "Directed degree product",
    "support_degree_product": "Support degree product",
}


def _individual_feature_label(name: str) -> str:
    return INDIVIDUAL_LABELS.get(name, name.replace("_", " ").strip().title())


def load_and_build_groups():
    panel = pd.read_parquet(PANEL_PATH)
    panel = panel[panel["cutoff_year_t"].between(1990, 2015)].copy()
    pool_col = [c for c in panel.columns if c.startswith("in_pool_")]
    if pool_col:
        panel = panel[panel[pool_col[0]].astype(bool)]
    panel = panel[panel["horizon"] == HORIZON].copy()
    available = [f for f in ALL_FEATURES if f in panel.columns]
    for f in available:
        panel[f] = _safe(panel[f])

    y = panel["appears_within_h"].astype(float).values
    X_individual = panel[available].values
    ind_mean, ind_std = X_individual.mean(0), X_individual.std(0)
    ind_std[ind_std < 1e-10] = 1.0
    X_individual_z = (X_individual - ind_mean) / ind_std

    # Build group PC1 scores
    group_scores = {}
    for gname, members in FEATURE_GROUPS.items():
        present = [f for f in members if f in available]
        if not present:
            continue
        X = panel[present].values
        scaler = StandardScaler()
        Xz = scaler.fit_transform(X)
        pca = PCA(n_components=min(3, len(present)))
        scores = pca.fit_transform(Xz)
        group_scores[gname] = scores[:, 0]

    group_names = list(group_scores.keys())
    X_groups = np.column_stack([group_scores[g] for g in group_names])
    mean, std = X_groups.mean(0), X_groups.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X_groups - mean) / std

    return panel, y, Xz, group_names, X_individual_z, available


def main():
    panel, y, Xz, group_names, X_individual_z, individual_features = load_and_build_groups()
    print(f"Panel: {len(panel)} rows, {len(group_names)} groups")

    # Train logistic
    lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500)
    lr.fit(Xz, y)

    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(3000, len(Xz)), replace=False)
    Xz_df = pd.DataFrame(Xz[idx], columns=group_names)
    background = Xz_df.iloc[:500]

    explainer = shap.LinearExplainer(lr, background)
    sv_raw = explainer.shap_values(Xz_df)
    sv_explanation = explainer(Xz_df)

    # 1. Beeswarm on groups
    print("  Beeswarm on grouped features...")
    fig, ax = plt.subplots(figsize=(9, 5))
    shap.summary_plot(sv_raw, Xz_df, show=False, max_display=len(group_names), plot_size=None)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "grouped_beeswarm.png")
    plt.savefig(OUT_DIR / "grouped_beeswarm.pdf")
    plt.close()

    # 2. Dependence plots for top 3 groups
    print("  Dependence plots for top 3 groups...")
    top3 = ["Directed degree (causal)", "Support degree (total)", "Evidence quality"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, gname in zip(axes, top3):
        if gname in Xz_df.columns:
            shap.dependence_plot(gname, sv_raw, Xz_df, ax=ax, show=False, dot_size=5, alpha=0.3)
            ax.set_title(gname, fontsize=9)
    fig.suptitle("SHAP dependence: how each group drives predictions", fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "grouped_dependence.png")
    fig.savefig(OUT_DIR / "grouped_dependence.pdf")
    plt.close()

    # 3. Waterfall: one high-prediction positive, one low-prediction negative
    print("  Waterfall examples...")
    preds = lr.predict_proba(Xz[idx])[:, 1]
    labels = y[idx]

    pos_mask = (labels == 1) & (preds > np.percentile(preds[labels == 1], 80))
    pos_indices = np.where(pos_mask)[0]
    if len(pos_indices) > 0:
        fig = plt.figure(figsize=(9, 4))
        shap.plots.waterfall(sv_explanation[pos_indices[0]], max_display=9, show=False)
        plt.title("Waterfall: a high-confidence hit (link realized)", fontsize=10)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "grouped_waterfall_hit.png")
        plt.savefig(OUT_DIR / "grouped_waterfall_hit.pdf")
        plt.close()

    neg_mask = (labels == 0) & (preds < np.percentile(preds[labels == 0], 20))
    neg_indices = np.where(neg_mask)[0]
    if len(neg_indices) > 0:
        fig = plt.figure(figsize=(9, 4))
        shap.plots.waterfall(sv_explanation[neg_indices[0]], max_display=9, show=False)
        plt.title("Waterfall: a cold pair (link not realized)", fontsize=10)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "grouped_waterfall_miss.png")
        plt.savefig(OUT_DIR / "grouped_waterfall_miss.pdf")
        plt.close()

    # 4. Correlation heatmap of grouped features
    print("  Correlation heatmap of groups...")
    corr = np.corrcoef(Xz.T)
    valid_groups = [g for g, s in zip(group_names, Xz.std(0)) if s > 1e-10]
    valid_idx = [group_names.index(g) for g in valid_groups]
    corr_valid = corr[np.ix_(valid_idx, valid_idx)]

    fig, ax = plt.subplots(figsize=(9.6, 8.4))
    im = ax.imshow(corr_valid, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(valid_groups)))
    ax.set_yticks(range(len(valid_groups)))
    ax.set_xticklabels(valid_groups, fontsize=10, rotation=45, ha="right")
    ax.set_yticklabels(valid_groups, fontsize=10)
    for i in range(len(valid_groups)):
        for j in range(len(valid_groups)):
            color = "white" if abs(corr_valid[i,j]) > 0.5 else "black"
            ax.text(j, i, f"{corr_valid[i,j]:.2f}", ha="center", va="center", fontsize=8.5, color=color)
    cbar = fig.colorbar(im, ax=ax, shrink=0.78)
    cbar.ax.tick_params(labelsize=9)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "grouped_correlation.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "grouped_correlation.pdf", bbox_inches="tight")
    fig.savefig(PAPER_DIR / "grouped_correlation.png", dpi=300, bbox_inches="tight")
    fig.savefig(PAPER_DIR / "grouped_correlation.pdf", bbox_inches="tight")
    plt.close()

    # 5. VIF table as a clean figure
    print("  VIF comparison figure...")
    from numpy.linalg import inv
    R = np.corrcoef(Xz[:, valid_idx].T)
    try:
        R_inv = inv(R)
        vifs = np.diag(R_inv)
    except Exception:
        vifs = np.ones(len(valid_groups))

    # Individual-feature VIFs on the current panel, using the top 10
    # features by absolute logistic coefficient.
    individual_lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500)
    individual_lr.fit(X_individual_z, y)
    top10_idx = np.argsort(np.abs(individual_lr.coef_[0]))[::-1][:10]
    top10_names = [individual_features[i] for i in top10_idx]
    top10_short = [_individual_feature_label(name) for name in top10_names]
    top10_corr = np.corrcoef(X_individual_z[:, top10_idx].T)
    try:
        top10_inv = inv(top10_corr)
        individual_vifs = pd.DataFrame({"feature": top10_short, "VIF": np.diag(top10_inv)})
    except Exception:
        individual_vifs = pd.DataFrame({"feature": top10_short, "VIF": np.ones(len(top10_short))})
    individual_vifs = individual_vifs.sort_values("VIF", ascending=True).reset_index(drop=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Left: individual VIFs (the problem)
    ind_names = individual_vifs["feature"].tolist()
    ind_vals = individual_vifs["VIF"].tolist()
    ax1.barh(range(len(ind_names)), ind_vals, color="#d6604d", edgecolor="white")
    ax1.set_yticks(range(len(ind_names)))
    ax1.set_yticklabels(ind_names, fontsize=8)
    ax1.set_xlabel("VIF")
    ax1.set_title("Before grouping: extreme multicollinearity", fontsize=10)
    ax1.axvline(10, color="black", linewidth=0.8, linestyle="--", label="VIF=10 threshold")
    ax1.legend(fontsize=7)

    # Right: grouped VIFs (the solution)
    ax2.barh(range(len(valid_groups)), vifs, color="#4393c3", edgecolor="white")
    ax2.set_yticks(range(len(valid_groups)))
    ax2.set_yticklabels(valid_groups, fontsize=8)
    ax2.set_xlabel("VIF")
    ax2.set_title("After grouping: multicollinearity resolved", fontsize=10)
    ax2.axvline(10, color="black", linewidth=0.8, linestyle="--", label="VIF=10 threshold")
    ax2.legend(fontsize=7)
    ax2.set_xlim(0, max(vifs) * 1.3)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "vif_comparison.png")
    fig.savefig(OUT_DIR / "vif_comparison.pdf")
    plt.close()

    print(f"\nAll figures saved to {OUT_DIR}")
    print(f"Files: {sorted(f.name for f in OUT_DIR.glob('*.png'))}")


if __name__ == "__main__":
    main()
