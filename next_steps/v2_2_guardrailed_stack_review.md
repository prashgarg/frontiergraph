# v2.2 Guardrailed Stack Review

This note reviews the guarded child-family pass built on top of the canonicalized+tuned `v2.1` stack.

## What We Ran

We executed the next-stage ontology-growth sequence in order:

1. built a second-stage guardrail over the `study_subfamily_candidate` endpoints
2. promoted only guarded substantive child clusters into a new ontology `v2.2` layer
3. rebuilt ontology sqlite, hybrid corpus, and funding enrichment on the guarded mapping
4. reran transparent model search
5. reran learned reranker tuning
6. rebuilt the current frontier with the calibrated sink regularizer still active

## Core Artifacts

- guardrail study: `outputs/paper/63_flexible_endpoint_guardrail/`
- guardrailed child promotions: `data/ontology_v2/ontology_v2_2_guardrailed_child_families.parquet`
- ontology `v2.2`: `data/ontology_v2/ontology_v2_2_guardrailed.json`
- mapping `v2.2`: `data/ontology_v2/extraction_label_mapping_v2_2_guardrailed.parquet`
- ontology sqlite: `data/production/frontiergraph_ontology_v2_2_guardrailed/ontology_v2_2_guardrailed.sqlite`
- hybrid corpus: `data/processed/research_allocation_v2_2_guardrailed/hybrid_corpus.parquet`
- funding enrichment: `outputs/paper/64_v2_2_funding_guardrailed/`
- transparent model search: `outputs/paper/65_v2_2_model_search_guardrailed/`
- reranker tuning: `outputs/paper/66_v2_2_learned_reranker_tuning_guardrailed/`
- current frontier: `outputs/paper/67_current_reranked_frontier_v2_2_guardrailed_search_tuned/`

## Guardrail Outcome

From `next_steps/flexible_endpoint_guardrail.md`:

- endpoint guardrail counts:
  - `substantive_family_candidate`: `26`
  - `generic_behavior_or_theory_container`: `13`
  - `method_or_measurement_container`: `7`
  - `contextual_bucket`: `6`
- promoted or attached child clusters: `33`
- new child ontology rows: `32`
- existing ontology child attachments: `1`
- parent endpoints with promoted children: `20`

The promoted set is conservative relative to the first raw split pass:

- many generic containers are blocked from creating new ontology rows
- cluster labels are chosen from clean example labels rather than noisy mixed exemplars
- only `1,973` mapping rows move away from the `v2.1` parent concepts (`1,971` new child-family remaps plus `2` existing-child attachments)

## Ontology and Corpus Effect

Relative to the canonicalized `v2.1` stack:

- ontology rows: `154,490 -> 154,522`
- unique grounded concepts in corpus: `57,935 -> 57,967`
- normalized hybrid rows: `1,241,749 -> 1,241,808`
- unique directed causal pairs: `75,750 -> 75,898`
- unique undirected noncausal pairs: `975,826 -> 977,568`

Interpretation:

- the guardrailed child layer is small and targeted
- it preserves more concept and pair resolution than `v2.1`
- but it does not blow up the benchmark corpus

## Funding Layer

From `outputs/paper/64_v2_2_funding_guardrailed/funding_manifest.json`:

- benchmark papers: `228,796`
- papers with grants: `26,026`
- grant coverage rate: `0.1138`

This is essentially stable relative to the `v2.1` canonicalized stack, which is what we would expect because ontology growth does not materially change the paper set.

## Transparent Model Search

The best transparent config moved noticeably relative to `v2.1`.

Canonicalized `v2.1` best config:

- `alpha=0.3000`
- `beta=0.0073`
- `gamma=0.6927`
- `delta=0.0921`
- `cooc_trend_coef=0.2162`

Guardrailed `v2.2` best config:

- `alpha=0.2525`
- `beta=0.3269`
- `gamma=0.4205`
- `delta=0.0592`
- `cooc_trend_coef=0.1810`

Interpretation:

- the child-family layer changes the transparent candidate landscape enough that the best transparent weighting shifts substantially
- the transparent path is still a weak model in absolute performance terms, but the shift is evidence that the ontology change is real rather than cosmetic

## Learned Reranker

Canonicalized `v2.1` best tuned variants:

- `h=5`: `pairwise_logit + composition`, `alpha=0.1`, `MRR=0.012061`, `Recall@100=0.137211`
- `h=10`: `glm_logit + composition`, `alpha=0.1`, `MRR=0.008396`, `Recall@100=0.126266`

Guardrailed `v2.2` best tuned variants:

- `h=5`: `glm_logit + boundary_gap`, `alpha=0.01`, `MRR=0.012963`, `Recall@100=0.108335`
- `h=10`: `glm_logit + boundary_gap`, `alpha=0.1`, `MRR=0.010659`, `Recall@100=0.096919`

Interpretation:

- `MRR` improves at both horizons
- `Recall@100` falls at both horizons
- the best feature family switches from `composition` to `boundary_gap`

So the child-family layer appears to make the reranker more precise at the top of the list, but less broad in recoverable top-100 coverage.

## Frontier Effect

Comparing the final `v2.2` frontier (`67`) with the canonicalized `v2.1` frontier (`61`):

### Horizon 5

- top-100 unique endpoints: `49 -> 91`
- top target share in top 100: `0.07 -> 0.02`
- top-100 endpoint HHI: `0.0330 -> 0.0118`
- top-100 edge overlap with `v2.1`: `18`

### Horizon 10

- top-100 unique endpoints: `46 -> 45`
- top target share in top 100: `0.09 -> 0.08`
- top-100 endpoint HHI: `0.0360 -> 0.0350`
- top-100 edge overlap with `v2.1`: `83`

Interpretation:

- the short-horizon frontier changes a lot and becomes much more endpoint-diverse
- the long-horizon frontier remains fairly close to the canonicalized `v2.1` frontier
- the guardrailed child layer is therefore affecting short-horizon ranking much more than long-horizon ranking

## WTP and Concentration

The sink controls remain effective in `v2.2`.

- `Willingness to Pay.` is absent from the `h=5` top 100 in `v2.2`
- `Willingness to Pay.` appears `5` times in the `h=10` top 100, down from `7` in canonicalized `v2.1`
- `Economic Growth` does not re-emerge as a top-100 sink endpoint

So the guarded child-family layer does not undo the sink cleanup work.

## Child-Family Visibility in the Frontier

The new child concepts are active in the corpus but do not dominate the frontier.

- promoted/attached child concepts used in the corpus: `33 / 33`
- promoted child concepts appearing as top-100 frontier endpoints:
  - `h=5`: `0`
  - `h=10`: `0`

This is an important result:

- the child-family layer increases representational precision in the benchmark corpus
- but it does not simply flood the frontier with newly minted ontology nodes

## What Looks Good

- ontology growth is controlled rather than explosive
- WTP-style sink behavior remains contained
- concept and pair resolution both improve
- short-horizon frontier concentration falls sharply
- the new child concepts are genuinely used in the corpus

## What Still Looks Risky

- some promoted child labels are still borderline or context-heavy:
  - `us stock market`
  - `environmental pressure`
  - `geopolitical risk index`
- the shift to `boundary_gap` rerankers with lower recall suggests the v2.2 layer may be making the system more selective but also less coverage-oriented
- the horizon-5 frontier may now be overly diverse, which is better than sink collapse but could also mean weaker thematic coherence

## Bottom Line

This pass is promising but not yet the final default.

The strongest positive result is:

- the guardrailed child-family layer improves representational precision with only a very small corpus-scale change
- while preserving the sink-control gains from the canonicalized `v2.1` stack

The main open question is:

- whether the short-horizon frontier is now genuinely better, or merely more diversified and less recall-oriented

So the next best move is not more ontology growth. It is:

1. review the borderline promoted child labels
2. compare shortlist quality/coherence between `v2.1` and `v2.2`
3. decide whether to keep `v2.2` as the active frontier stack or trim the child-family set further
