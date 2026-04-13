"""Generate figures for hypothesis discovery results."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "outputs/paper/52_hypothesis_discovery"
OUT_DIR = IN_DIR  # same dir

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
    "structural": "#4393c3",
    "dynamic": "#92c5de",
    "composition": "#d6604d",
    "boundary_gap": "#b2182b",
}

plt.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
})


def fig_shap_importance():
    df = pd.read_csv(IN_DIR / "shap_importance.csv")
    df = df.head(20).sort_values("mean_abs_shap", ascending=True)
    df["family"] = df["feature"].map(FAMILY_MAP).fillna("other")
    colors = [FAMILY_COLORS.get(f, "#999999") for f in df["family"]]

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(range(len(df)), df["mean_abs_shap"], color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([f.replace("_", " ").title() for f in df["feature"]], fontsize=8)
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title("SHAP feature importance: what drives the reranker's predictions")

    legend_patches = [mpatches.Patch(color=c, label=f.replace("_", " ").title())
                     for f, c in FAMILY_COLORS.items()]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=8, title="Feature family")
    ax.grid(True, axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_importance.png")
    fig.savefig(OUT_DIR / "shap_importance.pdf")
    plt.close(fig)
    print("  shap_importance.png")


def fig_interaction_heatmap():
    df = pd.read_csv(IN_DIR / "interactions_by_strength.csv")

    # Get top 12 features by involvement in strong interactions
    top_feats = []
    for col in ["feature_1", "feature_2"]:
        top_feats.extend(df.head(20)[col].tolist())
    from collections import Counter
    counts = Counter(top_feats)
    top_feats = [f for f, _ in counts.most_common(12)]

    # Build matrix
    matrix = pd.DataFrame(0.0, index=top_feats, columns=top_feats)
    for _, row in df.iterrows():
        if row["feature_1"] in top_feats and row["feature_2"] in top_feats:
            matrix.loc[row["feature_1"], row["feature_2"]] = row["interaction_r"]
            matrix.loc[row["feature_2"], row["feature_1"]] = row["interaction_r"]

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix.values, cmap="RdBu_r", vmin=-0.15, vmax=0.20, aspect="auto")
    ax.set_xticks(range(len(top_feats)))
    ax.set_yticks(range(len(top_feats)))
    labels = [f.replace("_", "\n").replace("support\ndegree\nproduct", "support\ndeg prod")[:25] for f in top_feats]
    ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title("Pairwise interaction strength (correlation with link appearance)")
    fig.colorbar(im, ax=ax, shrink=0.7, label="Interaction correlation")

    # Annotate top cells
    for i in range(len(top_feats)):
        for j in range(len(top_feats)):
            val = matrix.values[i, j]
            if abs(val) > 0.10:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=6,
                       color="white" if abs(val) > 0.15 else "black")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "interaction_heatmap.png")
    fig.savefig(OUT_DIR / "interaction_heatmap.pdf")
    plt.close(fig)
    print("  interaction_heatmap.png")


def fig_synergy_bar():
    df = pd.read_csv(IN_DIR / "interactions_by_synergy_top50.csv")
    top = df.head(15).sort_values("interaction_above_mains", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    labels = [f"{r['feature_1']}\n× {r['feature_2']}" for _, r in top.iterrows()]
    colors = ["#2166ac" if v > 0 else "#b2182b" for v in top["interaction_above_mains"]]
    ax.barh(range(len(top)), top["interaction_above_mains"], color=colors, edgecolor="white")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([l.replace("_", " ")[:40] for l in labels], fontsize=7)
    ax.set_xlabel("Synergy: interaction correlation minus max(main effects)")
    ax.set_title("Feature interactions with genuine synergy\n(above and beyond main effects)")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.grid(True, axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "synergy_bar.png")
    fig.savefig(OUT_DIR / "synergy_bar.pdf")
    plt.close(fig)
    print("  synergy_bar.png")


def fig_cluster_profiles():
    # Read from the note (cluster profiles aren't in CSV)
    # Hard-code from the run output
    clusters = [
        {"cluster": 0, "n": 689, "pos_rate": 0.087, "driver": "High target recency,\nlow target total degree"},
        {"cluster": 1, "n": 624, "pos_rate": 0.082, "driver": "High source recency,\nlow source total degree"},
        {"cluster": 2, "n": 2944, "pos_rate": 0.047, "driver": "Low recency for both\nendpoints (cold pairs)"},
        {"cluster": 3, "n": 440, "pos_rate": 0.136, "driver": "Very high source recency\n(hot source concept)"},
        {"cluster": 4, "n": 303, "pos_rate": 0.086, "driver": "Very high target recency\n(hot target concept)"},
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(clusters))
    bars = ax.bar(x, [c["pos_rate"] for c in clusters],
                  color=["#4393c3", "#4393c3", "#92c5de", "#b2182b", "#d6604d"],
                  edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([c["driver"] for c in clusters], fontsize=8, ha="center")
    ax.set_ylabel("Positive rate (link appears)")
    ax.set_title("SHAP-based prediction clusters: what drives different predictions")
    ax.axhline(0.063, color="black", linewidth=0.8, linestyle="--", label="Overall positive rate")
    ax.legend(loc="upper right")

    for bar, c in zip(bars, clusters):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
               f"n={c['n']}", ha="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "cluster_profiles.png")
    fig.savefig(OUT_DIR / "cluster_profiles.pdf")
    plt.close(fig)
    print("  cluster_profiles.png")


if __name__ == "__main__":
    print("Generating hypothesis discovery figures...")
    fig_shap_importance()
    fig_interaction_heatmap()
    fig_synergy_bar()
    fig_cluster_profiles()
    print(f"Done. Figures in {OUT_DIR}")
