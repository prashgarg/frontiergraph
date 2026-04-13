"""SHAP robustness suite: beeswarm, bootstrap CIs, correlation/VIF,
multi-model comparison, dependence plots, waterfall examples, log-odds check.

All outputs go to outputs/paper/53_shap_robustness/
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import shap

PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/141_shap_robustness_refresh"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZON = 10
FEATURES = [
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

FAMILY_MAP = {
    "path_support_norm": "structural", "motif_bonus_norm": "structural",
    "gap_bonus": "structural", "hub_penalty": "structural",
    "mediator_count": "structural", "motif_count": "structural",
    "cooc_count": "structural", "cooc_trend_norm": "structural",
    "field_same_group": "structural",
    "source_direct_out_degree": "structural", "target_direct_in_degree": "structural",
    "source_support_out_degree": "structural", "target_support_in_degree": "structural",
    "support_degree_product": "structural", "direct_degree_product": "structural",
    "support_age_years": "dynamic", "recent_support_age_years": "dynamic",
    "source_recent_support_out_degree": "dynamic", "target_recent_support_in_degree": "dynamic",
    "source_recent_incident_count": "dynamic", "target_recent_incident_count": "dynamic",
    "source_mean_stability": "composition", "target_mean_stability": "composition",
    "pair_mean_stability": "composition",
    "source_evidence_diversity": "composition", "target_evidence_diversity": "composition",
    "pair_evidence_diversity_mean": "composition",
    "source_mean_fwci": "composition", "target_mean_fwci": "composition",
    "pair_mean_fwci": "composition",
    "boundary_flag": "boundary_gap", "gap_like_flag": "boundary_gap",
    "nearby_closure_density": "boundary_gap",
}

FAMILY_COLORS = {
    "structural": "#4393c3", "dynamic": "#92c5de",
    "composition": "#d6604d", "boundary_gap": "#b2182b",
}

plt.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
})

SHORT_NAMES = {f: f.replace("_", " ").replace("source ", "src ").replace("target ", "tgt ").replace("support ", "sup ").replace("degree product", "deg prod").replace("evidence diversity", "evid div").replace("recent support", "rec sup").replace("incident count", "inc cnt").replace("mean stability", "stab").replace("mean fwci", "fwci")[:30] for f in FEATURES}


def _safe(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


def load_data():
    panel = pd.read_parquet(PANEL_PATH)
    panel = panel[panel["cutoff_year_t"].between(1990, 2015)].copy()
    pool_col = [c for c in panel.columns if c.startswith("in_pool_")]
    if pool_col:
        panel = panel[panel[pool_col[0]].astype(bool)]
    panel = panel[panel["horizon"] == HORIZON].copy()
    available = [f for f in FEATURES if f in panel.columns]
    for f in available:
        panel[f] = _safe(panel[f])
    X = panel[available].values
    y = panel["appears_within_h"].astype(float).values
    mean, std = X.mean(0), X.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X - mean) / std
    return panel, available, Xz, y, mean, std


def train_logistic(Xz, y):
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500, solver="lbfgs")
    lr.fit(Xz, y)
    return lr


# ======================================================================= #
# 1. BEESWARM PLOT
# ======================================================================= #
def fig_beeswarm(lr, Xz, features):
    print("  1. Beeswarm plot...")
    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(3000, len(Xz)), replace=False)
    Xz_df = pd.DataFrame(Xz[idx], columns=[SHORT_NAMES[f] for f in features])
    background = Xz_df.iloc[:500]
    explainer = shap.LinearExplainer(lr, background)
    sv = explainer.shap_values(Xz_df)

    fig, ax = plt.subplots(figsize=(10, 9))
    shap.summary_plot(sv, Xz_df, show=False, max_display=20, plot_size=None)
    plt.title("SHAP beeswarm: feature contributions to link-appearance prediction", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "beeswarm.png")
    plt.savefig(OUT_DIR / "beeswarm.pdf")
    plt.close()
    return sv, Xz_df


# ======================================================================= #
# 2. BOOTSTRAP CONFIDENCE INTERVALS
# ======================================================================= #
def bootstrap_shap(Xz, y, features, n_boot=100):
    from sklearn.linear_model import LogisticRegression
    print(f"  2. Bootstrap CIs ({n_boot} iterations)...")
    t0 = time.time()
    rng = np.random.RandomState(42)
    n = len(Xz)
    all_importances = []

    for b in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        Xb, yb = Xz[idx], y[idx]
        if yb.sum() < 5 or (len(yb) - yb.sum()) < 5:
            continue
        lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=300, solver="lbfgs")
        lr.fit(Xb, yb)
        # SHAP for linear model = |coef * std(X)| approximately
        importances = np.abs(lr.coef_[0])
        all_importances.append(importances)

    all_imp = np.array(all_importances)
    ranks = np.argsort(-all_imp, axis=1)  # rank each bootstrap
    rank_matrix = np.zeros_like(ranks)
    for b in range(len(ranks)):
        for pos, feat_idx in enumerate(ranks[b]):
            rank_matrix[b, feat_idx] = pos + 1

    results = []
    for i, f in enumerate(features):
        results.append({
            "feature": f,
            "mean_importance": float(all_imp[:, i].mean()),
            "std_importance": float(all_imp[:, i].std()),
            "ci_lo": float(np.percentile(all_imp[:, i], 2.5)),
            "ci_hi": float(np.percentile(all_imp[:, i], 97.5)),
            "mean_rank": float(rank_matrix[:, i].mean()),
            "rank_ci_lo": float(np.percentile(rank_matrix[:, i], 2.5)),
            "rank_ci_hi": float(np.percentile(rank_matrix[:, i], 97.5)),
        })

    boot_df = pd.DataFrame(results).sort_values("mean_importance", ascending=False)
    boot_df.to_csv(OUT_DIR / "bootstrap_importance.csv", index=False)
    print(f"    Done in {time.time()-t0:.1f}s")

    # Figure: importance with CIs
    top = boot_df.head(15).sort_values("mean_importance", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = [FAMILY_COLORS.get(FAMILY_MAP.get(f, ""), "#999") for f in top["feature"]]
    ax.barh(range(len(top)), top["mean_importance"], xerr=[top["mean_importance"]-top["ci_lo"], top["ci_hi"]-top["mean_importance"]],
            color=colors, edgecolor="white", linewidth=0.5, capsize=3)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([SHORT_NAMES[f] for f in top["feature"]], fontsize=8)
    ax.set_xlabel("Mean |coefficient| (bootstrap 95% CI)")
    ax.set_title("Feature importance with bootstrap confidence intervals (n=100)")
    legend_patches = [mpatches.Patch(color=c, label=f.replace("_", " ").title()) for f, c in FAMILY_COLORS.items()]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=7)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "bootstrap_importance.png")
    fig.savefig(OUT_DIR / "bootstrap_importance.pdf")
    plt.close()

    # Rank stability
    print(f"\n    Rank stability (top 10):")
    for _, row in boot_df.head(10).iterrows():
        print(f"      {SHORT_NAMES[row['feature']]:30s}  mean_rank={row['mean_rank']:.1f}  [{row['rank_ci_lo']:.0f}-{row['rank_ci_hi']:.0f}]")

    return boot_df


# ======================================================================= #
# 3. CORRELATION MATRIX + VIF
# ======================================================================= #
def correlation_vif(Xz, features):
    print("  3. Correlation matrix + VIF...")
    # Top 10 by SHAP
    top10 = ["target_recent_support_in_degree", "source_recent_support_out_degree",
             "target_support_in_degree", "target_recent_incident_count",
             "source_support_out_degree", "source_recent_incident_count",
             "target_direct_in_degree", "source_direct_out_degree",
             "support_age_years", "pair_evidence_diversity_mean"]
    top10_idx = [features.index(f) for f in top10 if f in features]
    top10_names = [features[i] for i in top10_idx]

    corr = np.corrcoef(Xz[:, top10_idx].T)
    corr_df = pd.DataFrame(corr, index=[SHORT_NAMES[f] for f in top10_names],
                           columns=[SHORT_NAMES[f] for f in top10_names])
    corr_df.to_csv(OUT_DIR / "correlation_matrix_top10.csv")

    # VIF
    from numpy.linalg import inv
    try:
        R = np.corrcoef(Xz[:, top10_idx].T)
        R_inv = inv(R)
        vifs = np.diag(R_inv)
        vif_df = pd.DataFrame({"feature": top10_names, "VIF": vifs,
                                "short_name": [SHORT_NAMES[f] for f in top10_names]}).sort_values("VIF", ascending=False)
        vif_df.to_csv(OUT_DIR / "vif_top10.csv", index=False)
        print(f"\n    VIF for top 10 SHAP features:")
        for _, row in vif_df.iterrows():
            flag = " *** HIGH" if row["VIF"] > 10 else " ** moderate" if row["VIF"] > 5 else ""
            print(f"      {row['short_name']:30s}  VIF={row['VIF']:.1f}{flag}")
    except Exception as e:
        print(f"    VIF computation failed: {e}")
        vif_df = pd.DataFrame()

    # Heatmap
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(top10_names)))
    ax.set_yticks(range(len(top10_names)))
    ax.set_xticklabels([SHORT_NAMES[f] for f in top10_names], fontsize=7, rotation=45, ha="right")
    ax.set_yticklabels([SHORT_NAMES[f] for f in top10_names], fontsize=7)
    for i in range(len(top10_names)):
        for j in range(len(top10_names)):
            color = "white" if abs(corr[i,j]) > 0.6 else "black"
            ax.text(j, i, f"{corr[i,j]:.2f}", ha="center", va="center", fontsize=6, color=color)
    fig.colorbar(im, ax=ax, shrink=0.7)
    ax.set_title("Correlation matrix: top 10 SHAP features")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "correlation_heatmap.png")
    fig.savefig(OUT_DIR / "correlation_heatmap.pdf")
    plt.close()

    return corr_df, vif_df


# ======================================================================= #
# 4. MULTI-MODEL COMPARISON
# ======================================================================= #
def multi_model_comparison(Xz, y, features):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    print("  4. Multi-model comparison...")
    t0 = time.time()

    models = {
        "Logistic Regression": LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=4, subsample=0.8, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1),
    }

    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(10000, len(Xz)), replace=False)
    Xs, ys = Xz[idx], y[idx]

    all_rankings = {}
    for name, model in models.items():
        print(f"    Training {name}...")
        model.fit(Xs, ys)

        # Get feature importance
        if hasattr(model, "coef_"):
            imp = np.abs(model.coef_[0])
        elif hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
        else:
            imp = np.zeros(len(features))

        ranking = pd.DataFrame({"feature": features, "importance": imp}).sort_values("importance", ascending=False)
        ranking["rank"] = range(1, len(ranking)+1)
        all_rankings[name] = ranking

    # Compare top 10 across models
    print(f"\n    Top 10 by model:")
    for name, ranking in all_rankings.items():
        print(f"\n    {name}:")
        for _, row in ranking.head(10).iterrows():
            print(f"      {row['rank']:2.0f}. {SHORT_NAMES[row['feature']]:30s}  imp={row['importance']:.4f}")

    # Rank correlation between models
    from scipy.stats import spearmanr
    model_names = list(all_rankings.keys())
    for i in range(len(model_names)):
        for j in range(i+1, len(model_names)):
            r1 = all_rankings[model_names[i]].set_index("feature")["rank"]
            r2 = all_rankings[model_names[j]].set_index("feature")["rank"]
            common = r1.index.intersection(r2.index)
            rho, p = spearmanr(r1[common], r2[common])
            print(f"\n    Spearman rank correlation ({model_names[i]} vs {model_names[j]}): rho={rho:.3f}, p={p:.4f}")

    # Figure: side-by-side bar chart of top 10 per model
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
    for ax, (name, ranking) in zip(axes, all_rankings.items()):
        top = ranking.head(15).sort_values("importance", ascending=True)
        colors = [FAMILY_COLORS.get(FAMILY_MAP.get(f, ""), "#999") for f in top["feature"]]
        ax.barh(range(len(top)), top["importance"], color=colors, edgecolor="white", linewidth=0.5)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels([SHORT_NAMES[f] for f in top["feature"]], fontsize=7)
        ax.set_title(name, fontsize=10)
        ax.grid(True, axis="x", alpha=0.3)
    fig.suptitle("Feature importance: multi-model comparison", fontsize=12, y=1.01)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "multi_model_comparison.png")
    fig.savefig(OUT_DIR / "multi_model_comparison.pdf")
    plt.close()
    print(f"    Done in {time.time()-t0:.1f}s")

    return all_rankings


# ======================================================================= #
# 5. DEPENDENCE PLOTS
# ======================================================================= #
def dependence_plots(sv, Xz_df, features):
    print("  5. Dependence plots for top 3 features...")
    top3 = ["tgt rec sup in degree", "src rec sup out degree", "tgt sup in degree"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, feat_name in zip(axes, top3):
        if feat_name not in Xz_df.columns:
            continue
        shap.dependence_plot(feat_name, sv, Xz_df, ax=ax, show=False, dot_size=5, alpha=0.3)
        ax.set_title(feat_name, fontsize=9)
    fig.suptitle("SHAP dependence plots: top 3 features", fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "dependence_plots.png")
    fig.savefig(OUT_DIR / "dependence_plots.pdf")
    plt.close()


# ======================================================================= #
# 6. WATERFALL EXAMPLES
# ======================================================================= #
def waterfall_examples(lr, Xz, y, features, panel):
    print("  6. Waterfall examples...")
    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(3000, len(Xz)), replace=False)
    Xz_df = pd.DataFrame(Xz[idx], columns=[SHORT_NAMES[f] for f in features])
    background = Xz_df.iloc[:500]
    explainer = shap.LinearExplainer(lr, background)
    sv = explainer(Xz_df)

    # Find a "rising attention" hit (positive, high recency, low total degree)
    preds = lr.predict_proba(Xz[idx])[:, 1]
    labels = y[idx]

    # High-prediction positive
    pos_mask = (labels == 1) & (preds > np.percentile(preds[labels == 1], 80))
    pos_idx = np.where(pos_mask)[0]
    if len(pos_idx) > 0:
        example_pos = pos_idx[0]
        fig, ax = plt.subplots(figsize=(10, 6))
        shap.plots.waterfall(sv[example_pos], max_display=12, show=False)
        plt.title("Waterfall: a 'rising attention' hit (link realized)", fontsize=10)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "waterfall_hit.png")
        plt.savefig(OUT_DIR / "waterfall_hit.pdf")
        plt.close()

    # Low-prediction negative (cold pair)
    neg_mask = (labels == 0) & (preds < np.percentile(preds[labels == 0], 20))
    neg_idx = np.where(neg_mask)[0]
    if len(neg_idx) > 0:
        example_neg = neg_idx[0]
        fig, ax = plt.subplots(figsize=(10, 6))
        shap.plots.waterfall(sv[example_neg], max_display=12, show=False)
        plt.title("Waterfall: a 'cold pair' miss (link not realized)", fontsize=10)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "waterfall_miss.png")
        plt.savefig(OUT_DIR / "waterfall_miss.pdf")
        plt.close()


# ======================================================================= #
# 7. LOG-ODDS CHECK
# ======================================================================= #
def log_odds_check(lr, features):
    print("  7. Log-odds confirmation...")
    # For linear logistic regression, SHAP on log-odds = coefficient * (x - mean)
    # This is exact. Just confirm and note it.
    coefs = lr.coef_[0]
    intercept = lr.intercept_[0]
    print(f"    Model: logistic regression on standardized features")
    print(f"    SHAP is computed on log-odds scale (linear, exact)")
    print(f"    Intercept: {intercept:.4f}")
    print(f"    Top 5 coefficients (= SHAP weights on standardized features):")
    sorted_idx = np.argsort(np.abs(coefs))[::-1]
    for i in sorted_idx[:5]:
        print(f"      {SHORT_NAMES[features[i]]:30s}  coef={coefs[i]:.4f}")

    # Save confirmation
    with open(OUT_DIR / "log_odds_note.txt", "w") as f:
        f.write("SHAP values are computed on the log-odds scale.\n")
        f.write("For a linear logistic regression, SHAP(feature_j) = coef_j * (x_j - mean_j) / std_j.\n")
        f.write("This is exact (no approximation). The beeswarm and bar plots reflect log-odds contributions.\n")
        f.write(f"Intercept: {intercept:.4f}\n")


# ======================================================================= #
# MAIN
# ======================================================================= #
def main():
    print("Loading data...")
    panel, features, Xz, y, mean, std = load_data()
    print(f"  {len(panel)} rows, {len(features)} features, {y.sum():.0f} positives")

    print("\nTraining base logistic regression...")
    lr = train_logistic(Xz, y)

    print("\nGenerating robustness suite:\n")
    sv, Xz_df = fig_beeswarm(lr, Xz, features)
    boot_df = bootstrap_shap(Xz, y, features, n_boot=100)
    corr_df, vif_df = correlation_vif(Xz, features)
    all_rankings = multi_model_comparison(Xz, y, features)
    dependence_plots(sv, Xz_df, features)
    waterfall_examples(lr, Xz, y, features, panel)
    log_odds_check(lr, features)

    # Write summary note
    lines = [
        "# SHAP Robustness Suite Results",
        "",
        f"Panel: {len(panel)} pairs at h={HORIZON}",
        "",
        "## 1. Beeswarm: see beeswarm.png",
        "Shows direction and heterogeneity of each feature's contribution.",
        "",
        "## 2. Bootstrap CIs",
        "",
        "| Rank | Feature | Mean |coef| | 95% CI | Mean Rank | Rank CI |",
        "|------|---------|-------------|--------|-----------|---------|",
    ]
    for _, r in boot_df.head(10).iterrows():
        lines.append(f"| {r['mean_rank']:.0f} | {SHORT_NAMES[r['feature']]} | {r['mean_importance']:.3f} | [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] | {r['mean_rank']:.1f} | [{r['rank_ci_lo']:.0f}-{r['rank_ci_hi']:.0f}] |")
    lines.append("")

    lines.append("## 3. VIF (multicollinearity)")
    lines.append("")
    if not vif_df.empty:
        for _, r in vif_df.iterrows():
            flag = " HIGH" if r["VIF"] > 10 else " moderate" if r["VIF"] > 5 else ""
            lines.append(f"- {r['short_name']}: VIF={r['VIF']:.1f}{flag}")
    lines.append("")

    lines.append("## 4. Multi-model comparison: see multi_model_comparison.png")
    lines.append("Logistic, Gradient Boosting, Random Forest — check if top features are stable.")
    lines.append("")
    lines.append("## 5. Dependence plots: see dependence_plots.png")
    lines.append("## 6. Waterfall examples: see waterfall_hit.png, waterfall_miss.png")
    lines.append("## 7. Log-odds: SHAP is exact on log-odds scale for linear logistic.")

    (OUT_DIR / "robustness_note.md").write_text("\n".join(lines) + "\n")

    print(f"\n=== ALL DONE ===")
    print(f"Outputs: {OUT_DIR}")
    print(f"Files: {sorted(f.name for f in OUT_DIR.glob('*'))}")


if __name__ == "__main__":
    main()
