# Hypothesis Discovery: Interpretation Summary

All four approaches completed. Outputs in `outputs/paper/52_hypothesis_discovery/`.

---

## What we learned

### Approach A (SHAP): What drives the reranker's predictions

**Headline:** The reranker is primarily driven by **recency** and **directed degree**, not by topology features like path support or motif counts.

Top 5 by SHAP importance:
1. `target_recent_support_in_degree` (1.67) — how recently active the target concept is
2. `source_recent_support_out_degree` (1.55) — how recently active the source concept is
3. `target_support_in_degree` (1.23) — total target popularity (negative coefficient — popular targets are penalized once recency is controlled for)
4. `target_recent_incident_count` (1.07) — paper mentions of target recently
5. `source_support_out_degree` (1.03) — total source popularity (negative coefficient)

**Interpretation in plain economics:** The reranker finds links that appear between concepts that have been *recently* active but are *not yet* maximally popular. It penalizes already-central concepts (negative coefficients on total degree) while rewarding concepts whose recent activity outpaces their long-run centrality. This is an empirical "rising attention" signal — the model identifies concept pairs where one or both endpoints are gaining traction faster than cumulative advantage would predict.

**What surprised:** Path support (ranked ~15th), motif count, gap bonus, and boundary flag are all low-SHAP features. They carry some signal (that's why they help in the single-feature rankings) but the reranker's actual weight is dominated by the recency-vs-popularity contrast.

**SHAP clusters** reveal five prediction modes:
- Cluster 3 (highest positive rate, 13.6%): "hot source" — source concept has very high recent activity relative to its total degree
- Cluster 4 (8.6%): "hot target" — same pattern on the target side
- Cluster 2 (lowest, 4.7%): "cold pairs" — neither endpoint has recent momentum

This translates to a testable hypothesis: **links are most likely to appear when at least one endpoint is experiencing a recent surge of research activity that outpaces its long-run popularity.**

### Approach B (Interactions): What feature combinations predict link appearance

**Headline:** Pairwise interactions are strong but show **no synergy above main effects**. The strongest interactions (`direct_degree_product × pair_evidence_diversity_mean`, r=0.193) are entirely explained by the main effects of the component features. Synergy values are essentially zero (max 0.004).

**What this means:** The reranker's linear architecture is not missing much. If there were strong nonlinear interactions between graph features, they would show up as positive synergy. The fact that synergy is near-zero confirms the linear model is approximately correct for this feature set.

**Triple interactions** also show no genuine synergy above the pairwise level. `direct_degree_product × pair_evidence_diversity_mean × source_evidence_diversity` (r=0.194) is barely above the pairwise interaction (0.193).

**Practical implication for the paper:** We can state that the linear reranker is not leaving much nonlinear signal on the table. A neural network (Impact4Cast-style) might squeeze out marginal gains but the linear model is a good approximation.

### Approach C (SAE on Residuals): What the linear model misses

**Headline:** The SAE found neurons correlated with residuals (r up to 0.37), but the top neurons are driven by features that have constant values in much of the panel (`gap_bonus`, `mediator_count`, `field_same_group` all have NaN correlations because they're zero for most candidates in the pool).

**What this means:** The linear model's residuals are largest for pairs in unusual structural positions — those with non-zero gap bonus or non-zero mediator counts, which are rare in the top-10K candidate pool. The SAE is essentially detecting the sparse structural features that the linear model underweights because they're too infrequent.

**Practical implication:** The "alien territory" (Sourati & Evans) in our data is characterized by pairs that have rare structural features — they sit in actual gap positions or have mediating paths. The linear model doesn't weight these strongly enough because they're sparse, but when they fire, they carry real signal.

### Approach D (Enriched HypotheSAEs): Graph-structural text hypotheses

**Headline:** With graph-feature-enriched text descriptions, the SAE finds neurons that correlate with link appearance (r up to 0.132) and the LLM generates readable structural hypotheses. But correlations are weaker than the direct feature approaches, and the hypotheses tend to describe "dense + gap-like" patterns rather than discovering new structural dimensions.

**Top hypothesis (r=0.132):** "Candidate research connections that strongly activate neuron 53 are characterized by dense co-occurrence of concepts, gap-like graph structure..."

**What this means:** The text-embedding approach adds noise compared to working with features directly. The LLM interpretation step produces readable output but doesn't discover patterns beyond what SHAP and the interaction analysis already found more precisely.

---

## What we can use in the paper

### Definite additions:

1. **SHAP importance ranking** — the figure showing that recency features dominate the reranker is informative and could go in the appendix reranker section. It answers "what is the reranker actually learning?" more precisely than the single-feature ranking.

2. **The recency-vs-popularity finding** — the key insight that the reranker identifies "rising attention" pairs (high recency, negative coefficient on total degree) is substantively interesting. One sentence in the main text: "The reranker's dominant features are recency measures: it identifies concept pairs where recent research activity outpaces long-run popularity, suggesting that the benchmark captures a momentum signal that cumulative advantage alone misses."

3. **No synergy above main effects** — confirms the linear model is approximately right. One sentence in the reranker appendix: "Pairwise interaction testing finds no significant synergy above main effects, confirming that the linear model is a reasonable approximation for this feature set."

### Exploratory / appendix:

4. **SHAP cluster profiles** — the five prediction modes (hot source, hot target, cold pairs, etc.) are interesting for understanding what the model does. Could go in the reranker appendix.

5. **SAE residual finding** — the "alien territory" is characterized by rare structural features (non-zero gap bonus, mediating paths). Supports the failure-mode analysis already in the appendix.

### Skip:

6. The enriched HypotheSAEs (Approach D) adds little beyond what SHAP provides more precisely. Skip for the paper.

---

## Connection to Ludwig/Mullainathan

The SHAP analysis implements their Step 2 (communicate what the ML learned) on graph features:
- Step 1 (Explore): The reranker trained on 34 graph features ✓
- Step 2 (Communicate): SHAP reveals the model weights rising attention (recency vs total degree) most heavily ✓
- Step 3 (Verify): Walk-forward evaluation + temporal generalization test ✓

The "rising attention" hypothesis is the cleanest output: **links between concepts that are gaining research momentum faster than their long-run popularity predicts are more likely to materialize.** That's an interpretable, testable claim about how economics research evolves.

---

## Files generated

- `outputs/paper/52_hypothesis_discovery/shap_coefficients.csv`
- `outputs/paper/52_hypothesis_discovery/shap_importance.csv`
- `outputs/paper/52_hypothesis_discovery/shap_interactions_top50.csv`
- `outputs/paper/52_hypothesis_discovery/interactions_by_strength.csv`
- `outputs/paper/52_hypothesis_discovery/interactions_by_synergy_top50.csv`
- `outputs/paper/52_hypothesis_discovery/triple_interactions.csv`
- `outputs/paper/52_hypothesis_discovery/enriched_hypotheses.csv`
- `outputs/paper/52_hypothesis_discovery/shap_importance.png` / `.pdf`
- `outputs/paper/52_hypothesis_discovery/interaction_heatmap.png` / `.pdf`
- `outputs/paper/52_hypothesis_discovery/synergy_bar.png` / `.pdf`
- `outputs/paper/52_hypothesis_discovery/cluster_profiles.png` / `.pdf`
- `outputs/paper/52_hypothesis_discovery/summary.json`
