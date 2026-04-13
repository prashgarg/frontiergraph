# Remaining Analyses Plan

## What was done in this session

### New analyses run
1. **Co-occurrence ablation** — co-occurrence ≈ PA; reranker beats both. Integrated into main text and appendix.
2. **Single-feature importance** — 34 single-feature models ranked. Direct degree product (#1) requires directed extraction. Integrated into appendix.
3. **Sparse-vs-dense and impact regime splits** — graph structure adds most value in sparse, low-FWCI neighborhoods. Integrated into main text and appendix.
4. **Feature-set decomposition** — directed-only features alone (P@100=0.204) beat co-occurrence-only features (0.168) even when both are learned optimally. Integrated into main text.

### Manuscript changes
- Reranker fully explained (Section 3.4, appendix section with tables)
- Co-occurrence benchmark motivated and results reported
- Feature decomposition reported in Section 5.1
- Transparent score's role clarified (reading tool vs ranking tool)
- ~25 new citations added (Krenn, Sourati, Tong, Ludwig/Mullainathan, Kleinberg, Foster, Park, Wang, Petersen, Rzhetsky, Korinek, Agrawal, Si, Hoelzemann, Packalen, Fort, etc.)
- Section transitions and lit connections strengthened throughout
- Discussion updated with extraction noise, concept sensitivity, temporal generalization, exploration-efficiency tradeoff, LLM-only baseline, verification, and policy implications

---

## Remaining analyses (ordered by priority)

### Priority 1: Extend reranker to h=3 and h=15

**What:** Rebuild the feature panel with horizons=[3, 5, 10, 15] and re-run the reranker evaluation.

**Why:** The transparent score is evaluated at h=3, 5, 10, 15. The reranker is currently only at h=5 and h=10. A referee will ask whether the reranker also works at the shorter and longer horizons. If it does, the paper becomes stronger. If it doesn't, that's informative and should be discussed.

**How:** Modify the panel-building script to include h=3 and h=15. Re-run `build_candidate_feature_panel()`. This takes ~30-60 minutes of compute time. Then re-run the benchmark strategy review on the expanded panel.

**Effort:** Medium (panel rebuild + re-evaluation). Mostly compute time, not code.

### Priority 2: Reranker failure mode analysis

**What:** Among the reranker's top-100 predictions that did NOT realize within the horizon, characterize what kinds of links they are. Also, among realized links that the reranker ranks low, characterize what it misses.

**Why:** The paper reports where the reranker wins but doesn't examine what it gets wrong. Sourati & Evans's "alien" concept is partly about understanding mismatches. A failure-mode analysis would make the paper more honest and more interesting.

**How:**
- Take the reranker's top-100 at each cutoff/horizon cell
- Split into hits (realized) and misses (not realized)
- For misses: are they mostly boundary questions (sparse, low-cooc) or gap questions (dense, high-cooc)? Are they concentrated in particular subfields? Do they involve young or old concepts?
- For realized links that the reranker ranks poorly: are they popularity-driven (high PA score) or structurally surprising?

**Effort:** Medium. Uses existing panel data, no retraining needed.

### Priority 3: Journal-quality split

**What:** Among realized links, split by the journal FWCI of the paper that first realizes the link. Does the reranker predict links that appear in high-quality journals better than low-quality journals?

**Why:** FWCI of endpoints measures evidence *quality* of existing research. But we also care about realization *quality* — did the future paper appear in a top journal or a marginal one? This is the analog of Impact4Cast's impact-ratio thresholds.

**How:** We already have `first_realized_year` in the panel. We'd need to join back to the corpus to get the journal FWCI of the realizing paper. Then split realized links into high-journal-FWCI vs low-journal-FWCI and evaluate models in each bin.

**Effort:** Medium. Requires a join to paper metadata.

### Priority 4: Temporal generalization test

**What:** Hold out the most recent cutoff era entirely (e.g., train only on cutoffs 1990-2005, evaluate on 2010-2015). Compare reranker performance on in-sample vs held-out eras.

**Why:** The current walk-forward design prevents within-cutoff leakage but all cutoffs were used during model selection. Impact4Cast explicitly tests cross-era generalization. Doing this would address the temporal generalization caveat now in the Discussion.

**How:** Re-run the reranker with a restricted training set. Compare metrics on the held-out era vs the in-sample cutoffs.

**Effort:** Low-medium. Uses existing panel, just changes the train/eval split.

### Priority 5: LLM-only baseline

**What:** Prompt a language model with the two endpoint concepts and ask it to generate a research question — without access to the graph. Compare the quality of LLM-only questions with graph-surfaced questions.

**Why:** Tong et al. do this in psychology and find the graph adds value. The paper currently acknowledges the missing LLM-only comparison in the Discussion. Running it would close the gap.

**How:** For the same 24-item human validation pack, generate LLM-only questions using GPT-4 with concept names but no graph context. Then include these in the human validation exercise when ratings are collected.

**Effort:** Low for generation, high for evaluation (requires human raters).

---

## Natural extensions uniquely enabled by directed edges

These are analyses that co-occurrence-based systems (Impact4Cast, SemNet) cannot do because they don't have directed, typed edges:

### 1. Causal direction prediction
**What:** Among pairs where A→B is missing but B→A exists, predict whether A→B will later appear. This is a direction-specific prediction that co-occurrence systems can't distinguish from B→A.

### 2. Method-transfer prediction
**What:** Predict which missing links will be realized using a specific evidence method (e.g., RDD, IV, experiment). The extraction schema records method for each edge. We could ask: which missing causal claims will be established using a design-based method specifically?

### 3. Evidence-quality-conditional screening
**What:** Among the reranker's predictions, which are likely to be realized by high-quality evidence? Use the composition features (stability, evidence diversity) to predict not just appearance but appearance-with-quality.

### 4. Mechanism-path completion prediction
**What:** Instead of predicting direct links, predict the appearance of mediating paths (the "direct-to-path" transitions). This is a separate benchmarkable object mentioned in the Discussion as a natural extension.

### 5. Causal chain discovery
**What:** Predict multi-hop causal chains (A→B→C) where only partial links exist. This requires directed edges and path structure that co-occurrence can't provide.

---

## Papers that hint at these extensions

- **Sourati & Evans (2023):** Discuss "alien" hypotheses that bridge disconnected research communities. Our boundary questions are analogous. They suggest alien predictions as a tool for funding agencies.

- **Gu & Krenn (2025):** Discuss hypergraph representations (papers linking multiple concepts simultaneously) as a needed extension. Our paper-local extraction already produces paper-level hyperedges.

- **Foster et al. (2025):** Show that gap-opening papers are more disruptive. Our gap/boundary distinction could be tested against the disruption index directly.

- **Ludwig & Mullainathan (2024):** Emphasize the three-step procedure: train, communicate, verify. Our "surfaced object" is the communication step. The verification step (human ratings) is next.
