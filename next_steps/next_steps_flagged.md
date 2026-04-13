# Flagged Next Steps

Items to revisit in the next session. Flag these whenever someone asks "what's next?"

---

## 1. CONCEPT GRANULARITY — the biggest structural question

### The issue

The ontology has 6,752 concepts. These are broad labels like "economic growth," "CO2 emissions," "trade liberalization," "public debt." The ontology-vNext work (Phases 2-8 in the chat history) focused on *edge typing* (classifying edges by design family, policy semantics, relation type) and *unresolved queue cleanup* — NOT on making concepts finer-grained. The concept vocabulary itself is the same as before.

This matters because:
- Author-awareness analysis found 100% saturation at this granularity (every pair has author overlap)
- The top concept ("Method of Moments Quantile Regression") has 76K edges — it's an extraction artifact, not a real concept
- Many concept codes (FG3C004419 etc.) don't have human-readable labels in the 200-row central_concepts.csv
- The minimum edge count is 7 — even tail concepts have decent support
- Sourati & Evans work with millions of fine-grained material-property nodes where many have zero researcher overlap

### What was done vs what wasn't

**Done:** Edge-level typing (causal/contextual, method, stability, role), unresolved-edge audit, design-family overrides, policy-edge semantics, regime guardrails, family-aware comparison. All of this enriches the *edges* without changing the *concept inventory*.

**Not done:** Making the concept inventory finer-grained. A concept like "trade liberalization" could be split into "trade liberalization in Vietnam," "trade liberalization in NAFTA countries," "tariff reduction in manufacturing" — each of which would have different researcher expertise and different benchmark behavior. The extraction schema already stores context (countries, years, units) in dedicated fields — but these are NOT used to create finer concept nodes.

### What it would take

Two paths:
1. **Context-conditional concept splitting** — use the stored country/year/context fields to create sub-concept nodes (e.g., "trade liberalization [China]" vs "trade liberalization [general]"). This would multiply the concept count substantially.
2. **Paper-local concept preservation** — instead of normalizing 1.4M raw labels down to 6,752 concepts, keep a finer-grained layer (e.g., 50K-100K concepts) and build a two-level graph.

Either would be a significant pipeline change. Not a quick fix.

### Why it matters for the paper

At coarser granularity: author-awareness is saturated, the graph is dense, the benchmark is dominated by popularity. At finer granularity: author-awareness might matter, the graph would be sparser, and structural features might carry more signal. The paper should at least acknowledge this as a limitation and extension.

---

## 2. EXTRACTION ARTIFACT: MMQR dominates

"Method of Moments Quantile Regression (MMQR)" is the #1 concept by edge count (76K edges — 6x more than #2). This is clearly an extraction artifact — MMQR is a specific econometric method that became overrepresented because the LLM consistently extracts it as a node from papers that mention quantile regression. It appeared in the HypotheSAEs analysis too (dominated the top neurons).

### What to do

- Check if MMQR is driving benchmark results (it probably inflates the top candidate pool)
- Consider filtering or down-weighting it in the evaluation
- At minimum, note it as a known extraction artifact

---

## 3. REMAINING ANALYSIS PRIORITIES

From `remaining_analyses_plan.md`:
- h=3 and h=15 reranker extension — DONE
- Failure mode analysis — DONE
- Temporal generalization — DONE
- Journal-quality realization split — partially done (endpoint FWCI proxy)
- LLM-only baseline comparison — NOT DONE (acknowledged in Discussion)

From hypothesis discovery:
- Grouped SHAP — DONE with robustness
- Interaction testing — DONE (no synergy)
- Author-awareness — DONE (saturated)

---

## 4. HUMAN VALIDATION — still the #1 missing evidence

Blinded pack exists. Instructions exist. Answer key exists. Ratings not collected. This is the single biggest gap for any top journal submission. The paper acknowledges this prominently.

---

## 5. NEW COMPARABLES TO POTENTIALLY CITE

From the round-2 search (see `new_comparables_round2.md`):
- Lee et al. (2024) EconCausal — CITED
- Leng, Wang & Yuan (2024) — CITED
- Dell (2025) — bib entry added, not yet cited inline
- Marwitz et al. (2026) Nature Machine Intelligence — already in comparables
- Bergeaud, Jaffe & Papanikolaou (2025) NBER WP — NLP for innovation, not yet cited
- Korinek (2025) "AI Agents for Economic Research" — not yet cited (Discussion extension)
- Cohrs et al. (2025) LLMs for causal hypothesis generation — not yet cited
- Survey on hypothesis generation with LLMs (2025) — not yet cited

---

## 6. FIGURES GENERATED BUT NOT IN MANUSCRIPT

In `outputs/paper/50_extra_figures/`:
- concept_tsne.png — noisy but interesting, needs refinement

In `outputs/paper/53_shap_robustness/`:
- beeswarm.png — individual-feature beeswarm (stale, use grouped version)
- dependence_plots.png — individual-feature dependence (stale)
- waterfall_hit.png, waterfall_miss.png — individual (stale)
- multi_model_comparison.png — individual (stale, replaced by grouped)

In `outputs/paper/54_grouped_shap/`:
- grouped_dependence.png — NOT in manuscript yet
- grouped_waterfall_hit.png — NOT in manuscript yet
- grouped_waterfall_miss.png — NOT in manuscript yet

---

## 7. JOURNAL TARGETING

Assessment from earlier:
- **ReStat** or **Research Policy** — most natural homes now
- **QJE** — would need human validation + stronger Ludwig/Mullainathan connection
- **PNAS** — good for the metascience audience, faster turnaround
- **Nature Human Behaviour** — where Sourati & Evans published, but may want broader scope

The author-awareness negative finding actually strengthens the PNAS/NHB pitch — it's a cross-domain comparison.

---

## 8. WEBSITE / PUBLIC RELEASE

frontiergraph.com shows the current surfaced questions. The website data (graph_backbone.json with 518 nodes) is much smaller than the full evaluation graph (6,752 concepts). This is intentional — the website shows a curated subset.

No website changes have been made in this session. The paper-incubation branch should NOT be pushed to the public repo.
