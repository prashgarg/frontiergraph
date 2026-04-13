# v2.1 Canonicalized Stack Review

## What We Ran

We executed the cleanup sequence in order:

1. apply conservative cross-source canonicalization merges to ontology `v2.1`
2. rebuild ontology sqlite, hybrid corpus, and funding enrichment on the canonicalized mapping
3. integrate the calibrated sink regularizer into the current frontier builder
4. build a focused sink cleanup pack for the top sink-like endpoints
5. make transparent `model_search` scale-safe on `v2.1`
6. rerun transparent model search, rerun learned reranker tuning, and rebuild the current frontier on the fully consistent stack

## Core Artifacts

- canonicalized ontology: `data/ontology_v2/ontology_v2_1_canonicalized.json`
- canonicalized mapping: `data/ontology_v2/extraction_label_mapping_v2_1_canonicalized.parquet`
- canonicalized sqlite: `data/production/frontiergraph_ontology_v2_1_canonicalized/ontology_v2_1.sqlite`
- canonicalized corpus: `data/processed/research_allocation_v2_1_canonicalized/hybrid_corpus.parquet`
- transparent model search: `outputs/paper/58_v2_1_model_search_canonicalized/`
- sink cleanup pack: `outputs/paper/59_v2_1_top_sink_cleanup_pack/top_sink_cleanup_pack.csv`
- retuned reranker: `outputs/paper/60_v2_1_learned_reranker_tuning_canonicalized/`
- final current frontier: `outputs/paper/61_current_reranked_frontier_v2_1_canonicalized_search_tuned/`

## Canonicalization Effect

From `data/ontology_v2/canonicalization_application_note_v2_1.md`:

- duplicate merges applied: `77`
- ontology rows: `154,567 -> 154,490`
- remapped primary concept ids in label mapping: `11,538`

From `data/processed/research_allocation_v2_1_canonicalized/hybrid_corpus_manifest.json`:

- unique grounded concepts: `57,989 -> 57,935`
- hybrid rows: `1,241,854 -> 1,241,749`
- directed pairs: `75,772 -> 75,750`
- undirected pairs: `976,385 -> 975,826`

Interpretation:

- canonicalization cleans ontology identity more than it changes corpus scale
- the effect is targeted and conservative, not disruptive

## Sink Regularizer Effect

Comparing the old frontier (`53`) to the canonicalized+tuned frontier (`61`):

### Horizon 5

- top-20 unique targets: `4 -> 15`
- top-100 unique targets: `34 -> 49`
- `Willingness to pay`: `9/15 -> 2/7` in top-20/top-100
- `Economic Growth`: `9/24 -> 0/0`

### Horizon 10

- top-20 unique targets: `9 -> 17`
- top-100 unique targets: `25 -> 46`
- `Willingness to pay`: `3/17 -> 0/7`
- `Economic Growth`: `7/24 -> 0/0`

Interpretation:

- the calibrated sink regularizer materially reduces endpoint concentration
- the frontier is much more diverse than the original v2.1 frontier
- concentration still exists, but it is no longer dominated by a few sink endpoints

## Top Sink Cleanup Pack

The strongest cleanup signals are:

- `Willingness to pay`: `canonicalize_and_regularize`
- `Consumption`: `review_for_subfamily_promotion`
- `R&D`: `regularize_only`

Most other high-sink endpoints currently look more like broad-but-valid sink nodes than clean split candidates.

This is useful because it says:

- WTP was mostly an identity + sink problem, not yet a strong automatic split case
- Consumption is the first endpoint where semantic subfamily review looks justified

## Transparent Model Search

`src.analysis.model_search` is now scale-safe enough to complete on the canonicalized `v2.1` corpus because it no longer builds the all-pairs universe up front when the graph candidate universe already exists.

Outputs:

- `outputs/paper/58_v2_1_model_search_canonicalized/ablation_grid.csv`
- `outputs/paper/58_v2_1_model_search_canonicalized/best_config.yaml`
- `outputs/paper/58_v2_1_model_search_canonicalized/win_loss_summary.md`

Best transparent config:

- `alpha=0.3000`
- `beta=0.0073`
- `gamma=0.6927`
- `delta=0.0921`
- `cooc_trend_coef=0.2162`
- `recency_decay_lambda=0.08`
- `stability_coef=0.5`
- `causal_bonus=0.2`
- `field_hub_penalty_scale=0.2`

Important caveat:

- transparent model-search metrics are still tiny in absolute magnitude
- it now completes, which was the main blocker removed here
- but the transparent ranking still remains much weaker than the learned reranker layer

## Retuned Learned Reranker

From `outputs/paper/60_v2_1_learned_reranker_tuning_canonicalized/tuning_best_configs.csv`:

- `h=5`: `pairwise_logit + composition`, `alpha=0.1`
- `h=10`: `glm_logit + composition`, `alpha=0.1`

Best held-out metrics:

- `h=5`: `MRR=0.012061`, `Recall@100=0.137211`
- `h=10`: `MRR=0.008396`, `Recall@100=0.126266`

Interpretation:

- after making the transparent layer scale-safe, the best reranker still prefers rich composition features
- the retuned canonicalized stack is broadly consistent with earlier v2.1 results, but slightly different in horizon-10 preference

## Bottom Line

The ordered cleanup pass worked.

- ontology identity is cleaner
- the frontier is far less concentrated
- transparent model search now runs on `v2.1`
- WTP is better understood as a canonicalization + sink-control case
- Consumption emerges as the first serious subfamily-promotion candidate

The next highest-value move is:

1. apply the `77` canonicalizations as internal canonical ids in the default path
2. use the sink-regularized frontier as the default paper-facing shortlist layer
3. review subfamilies only for endpoints that look like `Consumption`, not for every broad sink
