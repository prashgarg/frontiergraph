"""Hypothesis discovery from graph features: SHAP, interactions, SAE on residuals,
and enriched HypotheSAEs.

Approach A: SHAP values on the walk-forward reranker
Approach B: Pairwise interaction discovery
Approach C: SAE on reranker residuals (what does the model miss?)
Approach D: HypotheSAEs v2 with graph-feature-enriched text
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import warnings
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore", category=FutureWarning)

PANEL_PATH = ROOT / "outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet"
OUT_DIR = ROOT / "outputs/paper/52_hypothesis_discovery"
NOTE_PATH = ROOT / "next_steps/hypothesis_discovery_note.md"

KEY_PATH = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt")
if KEY_PATH.exists():
    os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

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

def _safe(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)

def load_panel():
    panel = pd.read_parquet(PANEL_PATH)
    pool_col = [c for c in panel.columns if c.startswith("in_pool_")]
    if pool_col:
        panel = panel[panel[pool_col[0]].astype(bool)]
    panel = panel[panel["horizon"] == HORIZON].copy()
    available = [f for f in ALL_FEATURES if f in panel.columns]
    for f in available:
        panel[f] = _safe(panel[f])
    panel["label"] = panel["appears_within_h"].astype(float)
    return panel, available


# ======================================================================= #
# APPROACH A: SHAP
# ======================================================================= #
def approach_a_shap(panel, features):
    import shap
    from sklearn.linear_model import LogisticRegression
    print("\n=== APPROACH A: SHAP VALUES ===")
    t0 = time.time()

    X = panel[features].values
    y = panel["label"].values
    mean, std = X.mean(0), X.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X - mean) / std

    # Use sklearn LogisticRegression (SHAP-compatible)
    lr = LogisticRegression(C=20.0, penalty="l2", class_weight="balanced", max_iter=500, solver="lbfgs")
    lr.fit(Xz, y)

    coefs = lr.coef_[0]
    coef_df = pd.DataFrame({
        "feature": features,
        "coefficient": coefs,
        "abs_coefficient": np.abs(coefs),
    }).sort_values("abs_coefficient", ascending=False)

    print("  Computing SHAP values (linear explainer)...")
    Xz_df = pd.DataFrame(Xz, columns=features)

    rng = np.random.RandomState(42)
    idx = rng.choice(len(Xz_df), size=min(5000, len(Xz_df)), replace=False)
    background = Xz_df.iloc[idx[:500]]

    explainer = shap.LinearExplainer(lr, background, feature_names=features)
    shap_values = explainer.shap_values(Xz_df.iloc[idx])

    # Global importance: mean |SHAP|
    mean_shap = np.abs(shap_values).mean(axis=0)
    shap_importance = pd.DataFrame({
        "feature": features,
        "mean_abs_shap": mean_shap,
    }).sort_values("mean_abs_shap", ascending=False)

    # SHAP interaction: which features co-contribute?
    # Use correlation between SHAP values as proxy for interaction
    shap_corr = np.corrcoef(shap_values.T)
    top_interactions = []
    for i in range(len(features)):
        for j in range(i+1, len(features)):
            top_interactions.append({
                "feature_1": features[i],
                "feature_2": features[j],
                "shap_correlation": float(shap_corr[i, j]),
            })
    interaction_df = pd.DataFrame(top_interactions).sort_values("shap_correlation", key=abs, ascending=False)

    # Cluster predictions by SHAP profile
    from sklearn.cluster import KMeans
    n_clusters = 5
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = km.fit_predict(shap_values)
    cluster_profiles = []
    for c in range(n_clusters):
        mask = clusters == c
        cluster_shap = shap_values[mask].mean(axis=0)
        cluster_label_rate = y[idx][mask].mean()
        top_features = sorted(zip(features, cluster_shap), key=lambda x: abs(x[1]), reverse=True)[:5]
        cluster_profiles.append({
            "cluster": c,
            "n_pairs": int(mask.sum()),
            "positive_rate": float(cluster_label_rate),
            "top_features": [(f, float(v)) for f, v in top_features],
        })

    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"\n  Top 10 features by mean |SHAP|:")
    for _, row in shap_importance.head(10).iterrows():
        print(f"    {row['feature']:35s} {row['mean_abs_shap']:.4f}")

    print(f"\n  Top 5 SHAP interactions:")
    for _, row in interaction_df.head(5).iterrows():
        print(f"    {row['feature_1']:25s} × {row['feature_2']:25s}  r={row['shap_correlation']:.3f}")

    print(f"\n  Cluster profiles:")
    for cp in cluster_profiles:
        top_str = ", ".join(f"{f}={v:.3f}" for f, v in cp["top_features"][:3])
        print(f"    Cluster {cp['cluster']}: n={cp['n_pairs']}, pos_rate={cp['positive_rate']:.3f}, top: {top_str}")

    return {
        "coef_df": coef_df,
        "shap_importance": shap_importance,
        "interaction_df": interaction_df,
        "cluster_profiles": cluster_profiles,
        "shap_values": shap_values,
    }


# ======================================================================= #
# APPROACH B: Interaction Discovery
# ======================================================================= #
def approach_b_interactions(panel, features):
    print("\n=== APPROACH B: INTERACTION DISCOVERY ===")
    t0 = time.time()

    X = panel[features].values
    y = panel["label"].values
    mean, std = X.mean(0), X.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X - mean) / std

    # Test all pairwise interactions
    results = []
    n_features = len(features)
    total_pairs = n_features * (n_features - 1) // 2
    print(f"  Testing {total_pairs} pairwise interactions...")

    for i, j in combinations(range(n_features), 2):
        interaction = Xz[:, i] * Xz[:, j]
        if interaction.std() < 1e-10:
            continue
        r, p = pearsonr(interaction, y)
        # Also compute main effect correlations for comparison
        r_i, _ = pearsonr(Xz[:, i], y)
        r_j, _ = pearsonr(Xz[:, j], y)
        results.append({
            "feature_1": features[i],
            "feature_2": features[j],
            "interaction_r": float(r),
            "interaction_p": float(p),
            "main_r_1": float(r_i),
            "main_r_2": float(r_j),
            "interaction_above_mains": float(abs(r) - max(abs(r_i), abs(r_j))),
        })

    interaction_df = pd.DataFrame(results)

    # Sort by interaction strength
    by_strength = interaction_df.sort_values("interaction_r", key=abs, ascending=False)

    # Sort by interaction ABOVE main effects (genuine synergy)
    by_synergy = interaction_df.sort_values("interaction_above_mains", ascending=False)

    print(f"  Done in {time.time()-t0:.1f}s")

    print(f"\n  Top 10 interactions by |correlation|:")
    for _, row in by_strength.head(10).iterrows():
        print(f"    {row['feature_1']:25s} × {row['feature_2']:25s}  r={row['interaction_r']:.4f}  (mains: {row['main_r_1']:.4f}, {row['main_r_2']:.4f})")

    print(f"\n  Top 10 interactions by synergy (above main effects):")
    for _, row in by_synergy.head(10).iterrows():
        print(f"    {row['feature_1']:25s} × {row['feature_2']:25s}  synergy={row['interaction_above_mains']:.4f}  (int_r={row['interaction_r']:.4f})")

    # Also test triple interactions for the top features
    top_singles = by_strength["feature_1"].head(5).tolist() + by_strength["feature_2"].head(5).tolist()
    top_singles = list(set(top_singles))[:8]
    triple_results = []
    for i, j, k in combinations(range(len(top_singles)), 3):
        fi, fj, fk = top_singles[i], top_singles[j], top_singles[k]
        if fi not in features or fj not in features or fk not in features:
            continue
        ii, jj, kk = features.index(fi), features.index(fj), features.index(fk)
        triple = Xz[:, ii] * Xz[:, jj] * Xz[:, kk]
        if triple.std() < 1e-10:
            continue
        r, p = pearsonr(triple, y)
        triple_results.append({
            "features": f"{fi} × {fj} × {fk}",
            "triple_r": float(r),
            "triple_p": float(p),
        })

    triple_df = pd.DataFrame(triple_results).sort_values("triple_r", key=abs, ascending=False) if triple_results else pd.DataFrame()

    if not triple_df.empty:
        print(f"\n  Top 5 triple interactions:")
        for _, row in triple_df.head(5).iterrows():
            print(f"    {row['features']:60s}  r={row['triple_r']:.4f}")

    return {
        "by_strength": by_strength,
        "by_synergy": by_synergy,
        "triple_df": triple_df,
    }


# ======================================================================= #
# APPROACH C: SAE on Reranker Residuals
# ======================================================================= #
def approach_c_sae_residuals(panel, features):
    import torch
    from hypothesaes import SparseAutoencoder
    print("\n=== APPROACH C: SAE ON RERANKER RESIDUALS ===")
    t0 = time.time()

    X = panel[features].values
    y = panel["label"].values

    # Fit a simple logistic to get predictions
    import statsmodels.api as sm
    mean, std = X.mean(0), X.std(0)
    std[std < 1e-10] = 1.0
    Xz = (X - mean) / std

    n_pos, n_neg = y.sum(), len(y) - y.sum()
    weights = np.where(y == 1, len(y)/(2*n_pos), len(y)/(2*n_neg))
    model = sm.GLM(y, sm.add_constant(Xz), family=sm.families.Binomial(), freq_weights=weights)
    result = model.fit_regularized(alpha=0.05, L1_wt=0.0, maxiter=200)
    preds = result.predict(sm.add_constant(Xz))

    # Residuals
    residuals = y - preds
    print(f"  Residuals: mean={residuals.mean():.4f}, std={residuals.std():.4f}")
    print(f"  Large positive residuals (model misses): {(residuals > 0.5).sum()}")
    print(f"  Large negative residuals (false alarms): {(residuals < -0.3).sum()}")

    # Train SAE on the graph features
    X_tensor = torch.tensor(Xz, dtype=torch.float32)
    sae = SparseAutoencoder(
        input_dim=Xz.shape[1],
        m_total_neurons=128,
        k_active_neurons=8,
    )
    sae.initialize_weights_(X_tensor[:1000])
    sae.fit(X_tensor, batch_size=256, n_epochs=15, learning_rate=1e-3, patience=5, show_progress=False)

    activations = sae.get_activations(X_tensor, show_progress=False)
    if isinstance(activations, torch.Tensor):
        activations = activations.detach().cpu().numpy()
    print(f"  SAE activations shape: {activations.shape}")

    # Correlate each neuron with RESIDUALS (not labels)
    neuron_residual_corrs = []
    for j in range(activations.shape[1]):
        col = activations[:, j]
        if col.std() < 1e-10:
            continue
        r, p = pearsonr(col, residuals)
        neuron_residual_corrs.append((j, float(r), float(p)))

    neuron_residual_corrs.sort(key=lambda x: abs(x[1]), reverse=True)

    # Also correlate with labels for comparison
    neuron_label_corrs = []
    for j in range(activations.shape[1]):
        col = activations[:, j]
        if col.std() < 1e-10:
            continue
        r, p = pearsonr(col, y)
        neuron_label_corrs.append((j, float(r), float(p)))
    neuron_label_corrs.sort(key=lambda x: abs(x[1]), reverse=True)

    # For top residual neurons, characterize what features drive them
    # by correlating each neuron's activation with each input feature
    neuron_profiles = []
    for j, r_resid, p_resid in neuron_residual_corrs[:15]:
        col = activations[:, j]
        feature_corrs = []
        for fi, fname in enumerate(features):
            r_feat, _ = pearsonr(col, Xz[:, fi])
            feature_corrs.append((fname, float(r_feat)))
        feature_corrs.sort(key=lambda x: abs(x[1]), reverse=True)
        neuron_profiles.append({
            "neuron": j,
            "residual_r": r_resid,
            "residual_p": p_resid,
            "top_features": feature_corrs[:5],
            "positive_rate_when_active": float(y[col > col.mean() + col.std()].mean()) if (col > col.mean() + col.std()).sum() > 10 else None,
        })

    print(f"\n  Done in {time.time()-t0:.1f}s")

    print(f"\n  Top 10 neurons correlated with RESIDUALS (what the model misses):")
    for np_ in neuron_profiles[:10]:
        top_str = ", ".join(f"{f}={v:.2f}" for f, v in np_["top_features"][:3])
        print(f"    Neuron {np_['neuron']:3d}: resid_r={np_['residual_r']:.4f}  features: {top_str}")

    print(f"\n  Top 5 neurons correlated with LABELS (what predicts appearance):")
    for j, r, p in neuron_label_corrs[:5]:
        print(f"    Neuron {j:3d}: label_r={r:.4f}")

    return {
        "neuron_residual_corrs": neuron_residual_corrs,
        "neuron_label_corrs": neuron_label_corrs,
        "neuron_profiles": neuron_profiles,
        "residuals": residuals,
    }


# ======================================================================= #
# APPROACH D: HypotheSAEs v2 with graph-feature-enriched text
# ======================================================================= #
async def approach_d_enriched_hypothesaes(panel, features):
    import openai
    import torch
    from hypothesaes import SparseAutoencoder
    print("\n=== APPROACH D: ENRICHED HYPOTHESAES ===")
    t0 = time.time()

    concepts = pd.read_csv(ROOT / "site/public/data/v2/central_concepts.csv")
    label_map = dict(zip(concepts["concept_id"].astype(str), concepts["plain_label"].astype(str)))

    # Build enriched text: graph features + concept labels
    texts = []
    for _, row in panel.iterrows():
        u_label = label_map.get(str(row["u"]), str(row["u"]))
        v_label = label_map.get(str(row["v"]), str(row["v"]))

        # Graph-structural description
        cooc = int(row.get("cooc_count", 0))
        path = float(row.get("path_support_norm", 0))
        motif = int(row.get("motif_count", 0))
        gap = float(row.get("gap_bonus", 0))
        boundary = int(row.get("boundary_flag", 0))
        ddp = int(row.get("direct_degree_product", 0))
        sdp = int(row.get("support_degree_product", 0))
        stability = float(row.get("pair_mean_stability", 0))
        ev_div = float(row.get("pair_evidence_diversity_mean", 0))
        fwci = float(row.get("pair_mean_fwci", 0))
        recency = float(row.get("recent_support_age_years", 0))

        density = "dense" if cooc > 20 else "sparse" if cooc < 5 else "moderate"
        structure = "gap-like" if gap > 0.5 and path > 0 else "boundary" if boundary else "standard"
        evidence = "high-diversity" if ev_div > 3 else "low-diversity"
        impact = "high-FWCI" if fwci > 6 else "low-FWCI" if fwci < 4 else "moderate-FWCI"

        text = (
            f"Pair: {u_label} -> {v_label}. "
            f"Co-occurrence: {density} ({cooc} papers). "
            f"Structure: {structure} (path_support={path:.2f}, motifs={motif}, gap={gap:.2f}). "
            f"Popularity: directed_degree_product={ddp}, support_degree_product={sdp}. "
            f"Evidence: {evidence} (diversity={ev_div:.1f}, stability={stability:.2f}). "
            f"Impact: {impact} (FWCI={fwci:.1f}). "
            f"Recency: last_support={recency:.0f} years ago."
        )
        texts.append(text)

    y = panel["label"].values

    # Embed
    client = openai.AsyncOpenAI(timeout=60.0)
    sem = asyncio.Semaphore(10)

    async def embed_batch(batch):
        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.embeddings.create(input=batch, model="text-embedding-3-small")
                    return [d.embedding for d in resp.data]
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
                    else:
                        raise

    print(f"  Embedding {len(texts)} enriched texts...")
    batches = [texts[i:i+500] for i in range(0, len(texts), 500)]
    all_emb = []
    for batch in batches:
        result = await embed_batch(batch)
        all_emb.extend(result)
    embeddings = np.array(all_emb, dtype=np.float32)
    print(f"  Embeddings: {embeddings.shape}")

    # Train SAE
    X_tensor = torch.tensor(embeddings, dtype=torch.float32)
    sae = SparseAutoencoder(
        input_dim=embeddings.shape[1],
        m_total_neurons=128,
        k_active_neurons=8,
    )
    sae.initialize_weights_(X_tensor[:1000])
    sae.fit(X_tensor, batch_size=256, n_epochs=10, learning_rate=1e-3, patience=3, show_progress=False)

    activations = sae.get_activations(X_tensor, show_progress=False)
    if isinstance(activations, torch.Tensor):
        activations = activations.detach().cpu().numpy()

    # Select top neurons
    corrs = []
    for j in range(activations.shape[1]):
        col = activations[:, j]
        if col.std() < 1e-10:
            continue
        r, p = pearsonr(col, y)
        corrs.append((j, float(r), float(p)))
    corrs.sort(key=lambda x: abs(x[1]), reverse=True)

    # Interpret top 15 neurons
    print(f"  Interpreting top 15 neurons with gpt-4.1-mini...")
    hypotheses = []
    for j, r, p in corrs[:15]:
        col = activations[:, j]
        top_idx = np.argsort(col)[-10:][::-1]
        bottom_idx = np.argsort(col)[:5]

        prompt = f"""Below are text descriptions of candidate research connections in economics. These are concept pairs that may or may not become linked in the literature.

These 10 examples MOST strongly activate neuron {j} (correlation {r:.3f} with link realization):

HIGH-ACTIVATION:
{chr(10).join(f'  [{i+1}] (realized={int(y[idx])}) {texts[idx][:350]}' for i, idx in enumerate(top_idx))}

LOW-ACTIVATION:
{chr(10).join(f'  [{i+1}] {texts[idx][:350]}' for i, idx in enumerate(bottom_idx))}

What GRAPH-STRUCTURAL pattern (not specific concepts) distinguishes the high-activation from low-activation examples? Focus on density, structure type, evidence diversity, impact, and recency patterns. State as a testable hypothesis starting with "Hypothesis: ..." """

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model="gpt-4.1-mini", messages=[{"role": "user", "content": prompt}], max_tokens=250,
                    )
                    hypothesis_text = resp.choices[0].message.content.strip()
                    break
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
                    else:
                        hypothesis_text = "[failed]"

        hypotheses.append({
            "neuron": j, "correlation": r, "p_value": p,
            "hypothesis": hypothesis_text,
            "positive_rate_top10": float(y[top_idx].mean()),
        })

    print(f"  Done in {time.time()-t0:.1f}s")
    print(f"\n  Top 10 enriched hypotheses:")
    for i, h in enumerate(hypotheses[:10], 1):
        hyp_short = h["hypothesis"][:150].replace("\n", " ")
        print(f"    {i:2d}. [r={h['correlation']:.3f}, pos_rate_top={h['positive_rate_top10']:.2f}] {hyp_short}")

    return {"hypotheses": hypotheses, "neuron_corrs": corrs}


# ======================================================================= #
# MAIN
# ======================================================================= #
async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel, features = load_panel()
    print(f"Panel: {len(panel)} rows, {len(features)} features, {panel['label'].sum():.0f} positives")

    # Approach A
    shap_results = approach_a_shap(panel, features)
    shap_results["coef_df"].to_csv(OUT_DIR / "shap_coefficients.csv", index=False)
    shap_results["shap_importance"].to_csv(OUT_DIR / "shap_importance.csv", index=False)
    shap_results["interaction_df"].head(50).to_csv(OUT_DIR / "shap_interactions_top50.csv", index=False)

    # Approach B
    int_results = approach_b_interactions(panel, features)
    int_results["by_strength"].to_csv(OUT_DIR / "interactions_by_strength.csv", index=False)
    int_results["by_synergy"].head(50).to_csv(OUT_DIR / "interactions_by_synergy_top50.csv", index=False)
    if not int_results["triple_df"].empty:
        int_results["triple_df"].to_csv(OUT_DIR / "triple_interactions.csv", index=False)

    # Approach C
    sae_results = approach_c_sae_residuals(panel, features)

    # Approach D
    hypo_results = await approach_d_enriched_hypothesaes(panel, features)
    pd.DataFrame(hypo_results["hypotheses"]).to_csv(OUT_DIR / "enriched_hypotheses.csv", index=False)

    # ----------------------------------------------------------------- #
    # Write comprehensive note
    # ----------------------------------------------------------------- #
    lines = [
        "# Hypothesis Discovery Results",
        "",
        f"Panel: {len(panel)} pairs at h={HORIZON}, {panel['label'].sum():.0f} positives ({panel['label'].mean()*100:.1f}%)",
        "",
        "---",
        "",
        "## Approach A: SHAP Values",
        "",
        "### Global feature importance (mean |SHAP|)",
        "",
        "| Rank | Feature | Mean |SHAP| | Coefficient |",
        "|------|---------|-------------|-------------|",
    ]
    merged = shap_results["shap_importance"].merge(shap_results["coef_df"][["feature","coefficient"]], on="feature")
    for i, (_, row) in enumerate(merged.head(15).iterrows(), 1):
        lines.append(f"| {i} | {row['feature']} | {row['mean_abs_shap']:.4f} | {row['coefficient']:.4f} |")
    lines.append("")

    lines.append("### SHAP-based prediction clusters")
    lines.append("")
    for cp in shap_results["cluster_profiles"]:
        top_str = ", ".join(f"{f}={v:.3f}" for f, v in cp["top_features"][:3])
        lines.append(f"- **Cluster {cp['cluster']}** (n={cp['n_pairs']}, positive rate={cp['positive_rate']:.3f}): {top_str}")
    lines.append("")

    lines.append("### Top SHAP interactions (feature pairs that co-contribute)")
    lines.append("")
    for _, row in shap_results["interaction_df"].head(10).iterrows():
        lines.append(f"- {row['feature_1']} × {row['feature_2']}: r={row['shap_correlation']:.3f}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## Approach B: Interaction Discovery",
        "",
        "### Top pairwise interactions by |correlation|",
        "",
        "| Feature 1 | Feature 2 | Interaction r | Main r₁ | Main r₂ | Synergy |",
        "|-----------|-----------|--------------|---------|---------|---------|",
    ])
    for _, row in int_results["by_strength"].head(15).iterrows():
        lines.append(f"| {row['feature_1']} | {row['feature_2']} | {row['interaction_r']:.4f} | {row['main_r_1']:.4f} | {row['main_r_2']:.4f} | {row['interaction_above_mains']:.4f} |")
    lines.append("")

    lines.append("### Top interactions by synergy (above main effects)")
    lines.append("")
    for _, row in int_results["by_synergy"].head(10).iterrows():
        lines.append(f"- {row['feature_1']} × {row['feature_2']}: synergy={row['interaction_above_mains']:.4f} (interaction_r={row['interaction_r']:.4f})")
    lines.append("")

    if not int_results["triple_df"].empty:
        lines.append("### Top triple interactions")
        lines.append("")
        for _, row in int_results["triple_df"].head(5).iterrows():
            lines.append(f"- {row['features']}: r={row['triple_r']:.4f}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Approach C: SAE on Reranker Residuals",
        "",
        "### Top neurons correlated with residuals (what the linear model misses)",
        "",
    ])
    for np_ in sae_results["neuron_profiles"][:10]:
        top_str = ", ".join(f"{f}={v:.2f}" for f, v in np_["top_features"][:3])
        pr = f", pos_rate_when_active={np_['positive_rate_when_active']:.3f}" if np_["positive_rate_when_active"] is not None else ""
        lines.append(f"- **Neuron {np_['neuron']}** (resid_r={np_['residual_r']:.4f}): {top_str}{pr}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## Approach D: Enriched HypotheSAEs (graph-feature text)",
        "",
    ])
    for i, h in enumerate(hypo_results["hypotheses"][:10], 1):
        lines.append(f"### Hypothesis {i} (r={h['correlation']:.3f}, top-10 positive rate={h['positive_rate_top10']:.2f})")
        lines.append("")
        lines.append(h["hypothesis"])
        lines.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Summary JSON
    summary = {
        "shap_top5": [{"feature": r["feature"], "importance": float(r["mean_abs_shap"])}
                      for _, r in shap_results["shap_importance"].head(5).iterrows()],
        "top5_interactions": [{"pair": f"{r['feature_1']} × {r['feature_2']}", "r": float(r["interaction_r"])}
                             for _, r in int_results["by_strength"].head(5).iterrows()],
        "top5_synergies": [{"pair": f"{r['feature_1']} × {r['feature_2']}", "synergy": float(r["interaction_above_mains"])}
                          for _, r in int_results["by_synergy"].head(5).iterrows()],
        "n_enriched_hypotheses": len(hypo_results["hypotheses"]),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(f"\n=== ALL DONE ===")
    print(f"Outputs: {OUT_DIR}")
    print(f"Note: {NOTE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
