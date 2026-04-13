# Session Checkpoint — 7 April 2026

## Branch status

- `main` — public, untouched
- `paper-incubation` — all paper work from this session (manuscript, analyses, figures)
- `paper-incubation-v2ontology` — CURRENT branch, just created, for ontology v2 work

## What was accomplished this session

### New analyses (11 total)
1. Co-occurrence ablation → directed features beat co-occurrence
2. Single-feature importance → direct_degree_product #1
3. Feature-set decomposition → directed-only features alone beat co-occurrence features
4. Sparse-dense regime split → graph helps most in sparse neighborhoods
5. Impact regime split → graph helps most in low-FWCI neighborhoods
6. Temporal generalization → reranker advantage GROWS in held-out era
7. Failure mode analysis → reranker misses sparse "alien" pairs
8. All-horizons reranker → beats PA at h=3,5,10,15
9. Grouped SHAP with VIF resolution → directed causal degree is dominant signal
10. Multi-model robustness → Spearman > 0.8 across logistic/GBT/RF after grouping
11. Author-awareness test → fully saturated in economics, no incremental signal

### Hypothesis discovery (4 approaches)
- SHAP (individual + grouped with multicollinearity resolution)
- Interaction testing (no synergy above main effects)
- SAE on residuals (rare structural features in the "alien" zone)
- HypotheSAEs with enriched text (~$3 spent, method-specific artifacts dominated)

### Manuscript changes
- Abstract rewritten (~170 words, crisp)
- Introduction tightened (removed repetition, moved footnotes)
- Related Literature deepened (~25 new citations total)
- Section 5 split into subsections (popularity+cooc / reranker rescue / frontier / etc.)
- New figures: pipeline overview, evaluation design, real neighborhood, feature decomposition, precision-at-K, temporal generalization, grouped SHAP, VIF comparison, beeswarm, multi-model, all-horizons, sparse-dense, corpus growth, feature importance bars
- New tables: benchmark summary, positioning, regime splits, failure modes, temporal generalization, single-feature importance, feature families, benchmark model inventory
- Discussion rewritten: tested author-awareness (negative finding), honest limitations with caveats, forward-looking close
- Appendix expanded: reranker design with grouped SHAP, robustness figures
- All terminology standardized ("benchmark anchor", no "retrieval layer", no "surfaced object")
- Extra results testbed at paper/extra_results.pdf

### New data collected
- Author data from OpenAlex: 572K authorship rows, 233K unique authors
- Extended feature panel: h=3,5,10,15 (240K rows)
- HypotheSAEs embeddings (text-embedding-3-small and large)

## Raw data for ontology v2

The extraction database has:
- 1,762,898 node instances across 242,595 papers
- 1,389,907 unique raw labels (lowercased)
- 93.8% appear only once (paper-specific phrasing)
- 6,890 appear 10+ times (recurring concepts)
- Currently compressed 206:1 to 6,752 concept codes

## Ontology v2 plan (on paper-incubation-v2ontology branch)

Target: ~20K-50K grounded, hierarchical concepts

Four seed sources:
1. JEL classification (scraped, hierarchical, economics-specific)
2. Wikidata economics concepts (external, hierarchical, grounded)
3. OpenAlex keywords (corpus-grounded, per-paper)
4. Raw LLM labels (paper-specific, context-rich)

Architecture: Wikidata Q-IDs → JEL codes → OpenAlex keywords → paper-level labels

## What to do next

### Immediate (ontology v2):
- Scrape JEL guide (all levels + keywords + examples)
- Query Wikidata for economics concepts (SPARQL)
- Fetch OpenAlex keywords for all 230K papers
- Research OpenAlex topic methodology for building our own
- Design the hierarchical mapping

### Deferred (paper):
- Human validation (need actual raters)
- LLM-only baseline comparison
- Journal submission preparation
- Website update with new ontology

## API spend this session
- OpenAI embeddings: ~$1
- OpenAI GPT-4.1-mini interpretation: ~$1
- OpenAI GPT-4.1-nano fidelity: ~$1
- Total: ~$3 (well under $10 budget)
