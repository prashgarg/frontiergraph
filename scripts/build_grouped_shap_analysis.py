"""Grouped SHAP analysis: resolve multicollinearity by grouping correlated
features into interpretable families, computing group-level importance,
then re-running multi-model comparison on groups.

Also: PCA on the top features to see what the latent dimensions are.
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

PANEL_PATH = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/140_grouped_shap_refresh"
PAPER_DIR = ROOT / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZON = 10

# All 33 features
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

# Interpretable grouping that resolves the collinearity
FEATURE_GROUPS = {
    "Directed degree (causal)": [
        "source_direct_out_degree", "target_direct_in_degree", "direct_degree_product",
    ],
    "Support degree (total)": [
        "source_support_out_degree", "target_support_in_degree", "support_degree_product",
    ],
    "Recency": [
        "source_recent_support_out_degree", "target_recent_support_in_degree",
        "source_recent_incident_count", "target_recent_incident_count",
        "recent_support_age_years",
    ],
    "Co-occurrence": [
        "cooc_count", "cooc_trend_norm", "support_age_years",
    ],
    "Path / topology": [
        "path_support_norm", "motif_bonus_norm", "motif_count",
        "gap_bonus", "hub_penalty",
    ],
    "Evidence quality": [
        "source_mean_stability", "target_mean_stability", "pair_mean_stability",
        "source_evidence_diversity", "target_evidence_diversity", "pair_evidence_diversity_mean",
    ],
    "Impact (FWCI)": [
        "source_mean_fwci", "target_mean_fwci", "pair_mean_fwci",
    ],
    "Boundary / gap flags": [
        "boundary_flag", "gap_like_flag", "nearby_closure_density",
    ],
    "Field structure": [
        "field_same_group", "mediator_count",
    ],
}

GROUP_COLORS = {
    "Directed degree (causal)": "#2166ac",
    "Support degree (total)": "#4393c3",
    "Recency": "#92c5de",
    "Co-occurrence": "#d1e5f0",
    "Path / topology": "#f4a582",
    "Evidence quality": "#d6604d",
    "Impact (FWCI)": "#b2182b",
    "Boundary / gap flags": "#67001f",
    "Field structure": "#999999",
}

SIGN_COLORS = {
    "positive": "#2b6cb0",
    "negative": "#c05621",
}


def _safe(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


def load_data():
    panel = pd.read_parquet(PANEL_PATH)
    panel = panel[panel["cutoff_year_t"].between(1990, 2015)].copy()
    pool_col = [c for c in panel.columns if c.startswith("in_pool_")]
    if pool_col:
        panel = panel[panel[pool_col[0]].astype(bool)]
    panel = panel[panel["horizon"] == HORIZON].copy()
    available = [f for f in ALL_FEATURES if f in panel.columns]
    for f in available:
        panel[f] = _safe(panel[f])
    return panel, available


# ======================================================================= #
# 1. Build group-level features via PCA within each group
# ======================================================================= #
def build_group_features(panel, available):
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    print("Building group-level features via within-group PCA...")
    group_features = {}
    group_loadings = {}
    pca_explained = {}

    for group_name, members in FEATURE_GROUPS.items():
        present = [f for f in members if f in available]
        if not present:
            continue

        X_group = panel[present].values
        scaler = StandardScaler()
        Xz = scaler.fit_transform(X_group)

        # PCA: take first component as the group summary
        pca = PCA(n_components=min(3, len(present)))
        scores = pca.fit_transform(Xz)

        group_features[group_name] = scores[:, 0]  # first PC
        group_loadings[group_name] = {
            "features": present,
            "loadings_pc1": pca.components_[0].tolist(),
            "explained_var_pc1": float(pca.explained_variance_ratio_[0]),
            "explained_var_total": float(pca.explained_variance_ratio_.sum()),
        }
        pca_explained[group_name] = float(pca.explained_variance_ratio_[0])

        print(f"  {group_name}: {len(present)} features, PC1 explains {pca.explained_variance_ratio_[0]*100:.1f}%")
        for feat, loading in zip(present, pca.components_[0]):
            print(f"    {feat:40s}  loading={loading:.3f}")

    return group_features, group_loadings, pca_explained


# ======================================================================= #
# 2. Group-level SHAP importance
# ======================================================================= #
def group_shap_importance(panel, available, group_features):
    import shap
    from sklearn.linear_model import LogisticRegression

    print("\nComputing group-level SHAP importance...")

    y = panel["appears_within_h"].astype(float).values
    group_names = list(group_features.keys())
    X_groups = np.column_stack([group_features[g] for g in group_names])

    # Standardize
    mean, std = X_groups.mean(0), X_groups.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X_groups - mean) / std

    lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500)
    lr.fit(Xz, y)

    # SHAP
    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(5000, len(Xz)), replace=False)
    Xz_df = pd.DataFrame(Xz[idx], columns=group_names)
    background = Xz_df.iloc[:500]
    explainer = shap.LinearExplainer(lr, background)
    sv = explainer.shap_values(Xz_df)

    mean_shap = np.abs(sv).mean(axis=0)
    coefs = lr.coef_[0]

    results = pd.DataFrame({
        "group": group_names,
        "mean_abs_shap": mean_shap,
        "coefficient": coefs,
        "abs_coefficient": np.abs(coefs),
    }).sort_values("mean_abs_shap", ascending=False)

    results.to_csv(OUT_DIR / "group_shap_importance.csv", index=False)

    print("\n  Group-level SHAP importance:")
    for _, row in results.iterrows():
        sign = "+" if row["coefficient"] > 0 else "-"
        print(f"    {row['group']:30s}  |SHAP|={row['mean_abs_shap']:.3f}  coef={sign}{abs(row['coefficient']):.3f}")

    return results, sv, Xz_df, group_names, lr, Xz, y


# ======================================================================= #
# 3. Group-level VIF (should be much lower now)
# ======================================================================= #
def group_vif(Xz, group_names):
    print("\nGroup-level VIF:")
    # Drop any zero-variance columns before computing VIF
    stds = Xz.std(axis=0)
    valid = stds > 1e-10
    valid_names = [n for n, v in zip(group_names, valid) if v]
    Xv = Xz[:, valid]

    from numpy.linalg import inv
    try:
        R = np.corrcoef(Xv.T)
        R_inv = inv(R)
        vifs = np.diag(R_inv)
        result = {}
        for name, vif in zip(valid_names, vifs):
            flag = " HIGH" if vif > 10 else " moderate" if vif > 5 else ""
            print(f"  {name:30s}  VIF={vif:.1f}{flag}")
            result[name] = vif
        for n, v in zip(group_names, valid):
            if not v:
                print(f"  {n:30s}  VIF=n/a (zero variance)")
                result[n] = 0.0
        return result
    except Exception as e:
        print(f"  VIF failed: {e}")
        return {g: 0.0 for g in group_names}


# ======================================================================= #
# 4. Multi-model comparison on grouped features
# ======================================================================= #
def multi_model_grouped(Xz, y, group_names):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

    print("\nMulti-model comparison on grouped features...")

    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz), size=min(15000, len(Xz)), replace=False)
    Xs, ys = Xz[idx], y[idx]

    models = {
        "Logistic": LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500),
        "GBT": GradientBoostingClassifier(n_estimators=100, max_depth=4, subsample=0.8, random_state=42),
        "RF": RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1),
    }

    all_rankings = {}
    for name, model in models.items():
        model.fit(Xs, ys)
        if hasattr(model, "coef_"):
            imp = np.abs(model.coef_[0])
        else:
            imp = model.feature_importances_
        ranking = pd.DataFrame({"group": group_names, "importance": imp}).sort_values("importance", ascending=False)
        ranking["rank"] = range(1, len(ranking)+1)
        all_rankings[name] = ranking
        print(f"\n  {name}:")
        for _, row in ranking.iterrows():
            print(f"    {row['rank']:2.0f}. {row['group']:30s}  imp={row['importance']:.4f}")

    # Rank correlations
    model_names = list(all_rankings.keys())
    for i in range(len(model_names)):
        for j in range(i+1, len(model_names)):
            r1 = all_rankings[model_names[i]].set_index("group")["rank"]
            r2 = all_rankings[model_names[j]].set_index("group")["rank"]
            common = r1.index.intersection(r2.index)
            rho, p = spearmanr(r1[common], r2[common])
            print(f"\n  Spearman ({model_names[i]} vs {model_names[j]}): rho={rho:.3f}")

    return all_rankings


# ======================================================================= #
# 5. Bootstrap CIs on grouped features
# ======================================================================= #
def bootstrap_grouped(Xz, y, group_names, n_boot=100):
    from sklearn.linear_model import LogisticRegression
    print(f"\nBootstrap CIs on grouped features ({n_boot} iterations)...")

    rng = np.random.RandomState(42)
    n = len(Xz)
    all_imp = []
    for b in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=300)
        lr.fit(Xz[idx], y[idx])
        all_imp.append(np.abs(lr.coef_[0]))

    all_imp = np.array(all_imp)
    results = []
    for i, g in enumerate(group_names):
        results.append({
            "group": g,
            "mean_importance": float(all_imp[:, i].mean()),
            "ci_lo": float(np.percentile(all_imp[:, i], 2.5)),
            "ci_hi": float(np.percentile(all_imp[:, i], 97.5)),
        })
    boot_df = pd.DataFrame(results).sort_values("mean_importance", ascending=False)
    boot_df.to_csv(OUT_DIR / "grouped_bootstrap.csv", index=False)

    print("\n  Grouped bootstrap importance:")
    for _, row in boot_df.iterrows():
        print(f"    {row['group']:30s}  {row['mean_importance']:.3f}  [{row['ci_lo']:.3f}, {row['ci_hi']:.3f}]")

    return boot_df


# ======================================================================= #
# 6. Figures
# ======================================================================= #
def make_figures(group_shap_df, boot_df, all_rankings, group_names, sv, Xz_df):
    import shap

    # Fig A: Group-level importance on a single coherent scale:
    # absolute logistic coefficient on the standardized group-PC1 score.
    merged = group_shap_df.merge(boot_df, on="group")
    merged = merged.sort_values("mean_importance", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [
        SIGN_COLORS["positive"] if coef > 0 else SIGN_COLORS["negative"]
        for coef in merged["coefficient"]
    ]
    lo_err = np.maximum(merged["mean_importance"].values - merged["ci_lo"].values, 0)
    hi_err = np.maximum(merged["ci_hi"].values - merged["mean_importance"].values, 0)
    ax.barh(range(len(merged)), merged["mean_importance"],
            xerr=[lo_err, hi_err],
            color=colors, edgecolor="white", capsize=3)
    ax.set_yticks(range(len(merged)))
    ax.set_yticklabels(merged["group"], fontsize=9)
    ax.set_xlabel("Absolute logistic coefficient on standardized group score (bootstrap 95% CI)")
    ax.grid(True, axis="x", alpha=0.3)
    sign_handles = [
        mpatches.Patch(color=SIGN_COLORS["positive"], label="Positive coefficient"),
        mpatches.Patch(color=SIGN_COLORS["negative"], label="Negative coefficient"),
    ]
    ax.legend(
        handles=sign_handles,
        loc="lower right",
        fontsize=8,
        frameon=True,
        title="Coefficient sign",
        title_fontsize=8,
    )

    fig.tight_layout()
    fig.savefig(OUT_DIR / "grouped_shap_importance.png")
    fig.savefig(OUT_DIR / "grouped_shap_importance.pdf")
    plt.close()

    # Fig B: Beeswarm on grouped features
    fig, ax = plt.subplots(figsize=(9, 5))
    shap.summary_plot(sv, Xz_df, show=False, max_display=len(group_names), plot_size=None)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "grouped_beeswarm.png")
    plt.savefig(OUT_DIR / "grouped_beeswarm.pdf")
    plt.close()

    # Fig C: Multi-model comparison on groups
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.2), sharey=True)
    for ax, (name, ranking) in zip(axes, all_rankings.items()):
        ranking = ranking.sort_values("importance", ascending=True)
        colors = [GROUP_COLORS.get(g, "#999") for g in ranking["group"]]
        ax.barh(range(len(ranking)), ranking["importance"], color=colors, edgecolor="white")
        ax.set_yticks(range(len(ranking)))
        ax.set_yticklabels(ranking["group"], fontsize=10)
        ax.set_title(name, fontsize=12)
        ax.grid(True, axis="x", alpha=0.3)
        ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "grouped_multi_model.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "grouped_multi_model.pdf", bbox_inches="tight")
    fig.savefig(PAPER_DIR / "grouped_multi_model.png", dpi=300, bbox_inches="tight")
    fig.savefig(PAPER_DIR / "grouped_multi_model.pdf", bbox_inches="tight")
    plt.close()

    print("  Figures saved.")


# ======================================================================= #
# MAIN
# ======================================================================= #
def main():
    panel, available = load_data()
    y = panel["appears_within_h"].astype(float).values
    print(f"Panel: {len(panel)} rows, {len(available)} features, {y.sum():.0f} positives\n")

    # 1. Build group features
    group_features, group_loadings, pca_explained = build_group_features(panel, available)

    # 2. Group SHAP
    group_shap_df, sv, Xz_df, group_names, lr, Xz, y = group_shap_importance(panel, available, group_features)

    # 3. Group VIF
    vifs = group_vif(Xz, group_names)

    # 4. Multi-model on groups
    all_rankings = multi_model_grouped(Xz, y, group_names)

    # 5. Bootstrap on groups
    boot_df = bootstrap_grouped(Xz, y, group_names)

    # 6. Figures
    make_figures(group_shap_df, boot_df, all_rankings, group_names, sv, Xz_df)

    # Write summary
    lines = [
        "# Grouped SHAP Analysis (Resolving Multicollinearity)",
        "",
        "## Approach",
        "",
        "The individual-feature diagnostic remains collinear at the raw-feature level.",
        "Solution: group the 33 features into 9 interpretable families, compute PC1 within each",
        "group as a summary score, then inspect both coefficient-scale importance and grouped SHAP",
        "direction/heterogeneity on the 9 group-level features.",
        "",
        "## PCA within groups",
        "",
    ]
    for g, info in group_loadings.items():
        lines.append(f"### {g} ({len(info['features'])} features, PC1 explains {info['explained_var_pc1']*100:.1f}%)")
        for feat, load in zip(info["features"], info["loadings_pc1"]):
            lines.append(f"  - {feat}: loading={load:.3f}")
        lines.append("")

    lines.append("## Group-level VIF")
    lines.append("")
    for g, v in vifs.items():
        flag = " HIGH" if v > 10 else ""
        lines.append(f"- {g}: VIF={v:.1f}{flag}")
    lines.append("")

    lines.append("## Group-level importance on standardized group scores")
    lines.append("")
    lines.append("| Group | Mean |coef| | Coef sign | Bootstrap CI | Mean |SHAP| |")
    lines.append("|-------|-------------|-----------|-------------|-------------|")
    merged = group_shap_df.merge(boot_df, on="group").sort_values("mean_importance", ascending=False)
    for _, row in merged.iterrows():
        sign = "+" if row["coefficient"] > 0 else "−"
        lines.append(
            f"| {row['group']} | {row['mean_importance']:.3f} | {sign} | "
            f"[{row['ci_lo']:.3f}, {row['ci_hi']:.3f}] | {row['mean_abs_shap']:.3f} |"
        )
    lines.append("")

    lines.append("## Multi-model comparison (Spearman rank correlations)")
    lines.append("")
    lines.append("Now that groups resolve collinearity, do models agree?")
    lines.append("")

    (OUT_DIR / "grouped_analysis_note.md").write_text("\n".join(lines) + "\n")

    print(f"\n=== ALL DONE ===")
    print(f"Outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
