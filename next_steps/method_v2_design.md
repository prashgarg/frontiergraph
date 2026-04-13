# Method v2 Design on Frozen Ontology v2.3

Date: 2026-04-09

## Status

This note is the governing design for the next method phase.

- ontology baseline: frozen `v2.3`
- scope here: design plus the first paper-grade method refresh on the frozen ontology
- completed paper-grade refresh:
  - headline family `path_to_direct`
  - main anchor `causal_claim`
  - family-aware reranker retune by horizon
  - concentration comparison between diversification-only and sink-plus-diversification
  - current frontier build with the refreshed winner stack
  - prepared human-validation protocol and blinded rating materials
- still pending at paper-grade standard:
  - full non-sampled reranker retune for `direct_to_path`
  - collected human ratings and downstream analysis
  - supply-vs-demand ranking extension
  - upstream candidate-generation v3 pass
  - clean separation between historically validated generator changes and current-frontier screening rules

The ontology is treated as fixed support infrastructure throughout this note. Method
changes must not quietly smuggle in ontology changes.

Companion notes:

- LLM role note: `next_steps/llm_role_in_method_v2.md`
- benchmark target note: `next_steps/method_v2_benchmark_target_note.md`
- paper graph shape note: `next_steps/paper_graph_shape_and_idea_object_note.md`
- motif inventory note: `next_steps/motif_inventory_and_candidate_schema_note.md`
- directed-vs-undirected note: `next_steps/directed_vs_undirected_design_note.md`
- benchmark-anchor rethink note: `next_steps/benchmark_anchor_rethink_note.md`
- schema and model choices note: `next_steps/method_v2_schema_and_model_choices_note.md`
- broad `path_to_direct` reranker note: `next_steps/broad_path_to_direct_sampled_reranker_grid_note.md`
- broad `path_to_direct` full reranker note: `next_steps/broad_path_to_direct_full_reranker_and_diversification_note.md`
- gap-vs-market ranking note: `next_steps/gap_vs_market_ranking_note.md`
- diversification note: `next_steps/method_v2_diversification_note.md`
- human-validation note: `next_steps/method_v2_human_validation_note.md`
- full-sample quality confirmation and surface layer note: `next_steps/ranker_v3_fullsample_confirmation_and_surface_layer.md`
- upstream retrieval and candidate-generation note: `next_steps/upstream_retrieval_and_candidate_generation_note.md`
- candidate generation v3 spec: `next_steps/candidate_generation_v3_spec.md`
- candidate generation vs current-screening note: `next_steps/candidate_generation_historical_vs_screening_note.md`
- retrieval budget evaluation note: `next_steps/retrieval_budget_eval_note.md`
- reranker pool-depth evaluation note: `next_steps/reranker_pool_depth_eval_note.md`
- field-conditioned budget evaluation note: `next_steps/field_conditioned_budget_eval_note.md`
- objective-specific pool defaults note: `next_steps/objective_specific_pool_defaults_note.md`
- field-shelf cleanup audit note: `next_steps/field_shelf_cleanup_and_paperworthiness_audit.md`
- endpoint-first field-shelf note: `next_steps/endpoint_first_field_shelf_note.md`
- LLM screening prompt-pack note: `next_steps/llm_screening_prompt_pack.md`
- within-field LLM v3 findings note: `next_steps/llm_within_field_v3_findings.md`
- LLM operational rule and appendix table note: `next_steps/llm_operational_rule_and_appendix_table.md`
- within-field LLM browse package note: `next_steps/within_field_llm_browse_package_note.md`
- global top-250 LLM screening note: `next_steps/global_top250_llm_screening_note.md`
- widened benchmark note: `next_steps/effective_benchmark_widened_1990_2015_note.md`
- timing taxonomy note: `next_steps/hot_vs_enduring_idea_taxonomy_note.md`
- historical appendix usefulness LLM note: `next_steps/historical_appendix_usefulness_llm_note.md`
- aligned human-usefulness pack note: `next_steps/method_v2_human_usefulness_pack_v2_note.md`
- human-usefulness analysis note: `next_steps/method_v2_human_usefulness_analysis_note.md`
- paper paragraph draft note: `next_steps/paper_paragraphs_widened_benchmark_and_appendix_validation.md`
- current locked/open decisions: `next_steps/current_locked_vs_open_decisions.md`
- frozen ontology baseline: `data/ontology_v2/ontology_v2_3_freeze_note.md`
- prepared human-usefulness pack: `next_steps/human_validation_plan.md`
- execution queue: `next_steps/method_v2_execution_queue.md`

## What stays fixed from the current paper

- The corpus and paper-local extraction layer stay fixed.
- The ontology baseline is the frozen `v2.3` package.
- The current strict identified-causal anchor remains available as a nested continuity check.
- The paper still separates the benchmark anchor from the surfaced research question.
- The benchmark family stays compact and readable rather than expanding into a large ML horse race.

## What method v2 reopens

Method v2 is allowed to reopen the object above the historical anchor.

The redesign must make explicit choices on five components:

1. candidate generation
2. transparent retrieval and scoring
3. learned reranking
4. concentration control
5. evaluation design

Each component is specified below so implementation can proceed without new conceptual decisions.

## 1. Candidate generation

### Goal

Build one family-tagged candidate universe rather than one undifferentiated pair pool.

The motivating object is not a bare missing edge. The descriptive paper-graph read
shows that the typical extracted paper is a small sparse local graph, so candidate
generation should retrieve endpoint-centered opportunities together with their local
path and mediator evidence.

### Historical anchor

Use a layered anchor design.

- main anchor:
  - missing ordered causal-language claim
  - `directionality_raw = directed`
  - `causal_presentation in {explicit_causal, implicit_causal}`
- nested strict anchor:
  - missing identified-causal claim in the current method-based causal layer

The nested strict anchor preserves continuity with the current paper without forcing that sparse layer to remain the only headline object.

### Candidate families

- `path_to_direct`
  - unresolved direct pair
  - nearby directed or mixed support path already exists
  - later direct closure is the anchor event
- `direct_to_path`
  - direct edge already exists
  - later work thickens the relation through new mediator structure
- `mediator_expansion`
  - unresolved endpoint pair
  - the substantive open question is which mediator or mechanism carries the relation

### Current implementation status

The family-tagged candidate object is now implemented. In the paper-grade `path_to_direct`
refresh, the strongest surfaced shortlist is almost entirely in the anchored progression
slice, especially `candidate_subfamily = causal_to_identified`. So while the headline
family remains `path_to_direct`, the current top shortlists often read more naturally as
mechanism-deepening or anchoring questions rather than fully open missing-link questions.
That is a substantive empirical finding, not just a presentation quirk.

The first candidate-generation v3 threshold sweep adds an important caution:

- some broad-anchored cleanup rules do improve the current surfaced shortlist
- but they do not yet show clear bite on the cached historical panel

So, for now, candidate-generation changes need to be split into two tracks:

- **historical generator changes**
  - only promoted when they move historical candidate pools in a measurable,
    vintage-respecting way
- **current-frontier screening**
  - allowed to improve the surfaced shortlist, but not yet counted as historical
    generator evidence

### Required outputs

Every candidate row must carry:

- `candidate_family`
- `candidate_subfamily`
- `candidate_scope_bucket`
- `anchor_type`
- endpoint IDs and labels
- the local evidence object used to justify the family assignment
- enough provenance to render the surfaced question later without recomputing the neighborhood from scratch
- richer evidence tags than family alone, including motif or topology descriptors where available

### Design rules

- benchmark anchor and surfaced question must remain separate fields
- family tags must be emitted by the candidate generator, not inferred later in presentation code
- subfamily and scope tags should expose whether a candidate is fully open, contextual, or already anchored by ordered/causal evidence
- candidate-family assignment must be deterministic once the frozen graph inputs are fixed
- candidate families stay compact, while evidence motifs may be richer and multi-valued

## 2. Transparent retrieval and scoring

### Role

The transparent model remains the interpretable first-stage screen. It is not required to
be the strongest strict top-K model.

### Allowed component families

- path support
- underexploration / gap terms
- motif support
- hub or generic-endpoint penalties
- co-occurrence trend or recency-weighted support only if historically disciplined
- family-specific support summaries when those can be computed without leakage

### Required outputs

The retrieval layer must emit:

- total transparent score
- a score decomposition table for every shortlisted item
- family-specific evidence summaries that can be shown in the paper appendix or UI

### Benchmark comparison set

The comparison family stays compact:

- preferential attachment
- degree/recency baseline
- directed closure baseline
- transparent graph score
- learned reranker

No extra baseline should be added unless it answers a specific critique.

### Paper reminder

In the next methods-text revision, the paper should say explicitly that:

- the transparent score is a retrieval layer
- the learned model reranks only the retrieved top pool
- pool size is a tuned design parameter, not a scientific constant
- retrieval quality and reranking quality are distinct objects

The next evaluation pass should also add multi-`K` reporting rather than relying too
heavily on `Recall@100` alone.

The first field-conditioned budget pass now reinforces that point:

- `2000` is strong for concentration-focused global top-`100`
- but it is not universally best once we look at within-field slices or larger
  budget ladders such as `250` and `1000`
- so pool size should now be treated as dependent on the user-facing shortlist
  object, not as one globally fixed method constant

Objective-specific frontier packages now exist for the current build:

- global exploratory top-`100` using `pool=5000`
- within-field top-`100` using `pool=2000`
- global scan top-`250` using `pool=2000`
- global scan top-`1000` using `pool=2000`

The first operational LLM rule is now also clear enough to describe plainly:

- the LLM is used only on the within-field browse object
- it first applies a weak veto to obvious local failures
- it then reranks surviving candidates by repeated within-field pairwise comparisons
- a scalar screening score is retained only as a secondary diagnostic

That should be the paper-facing description unless a later pass materially changes the role
of the LLM layer.

The widened effective-corpus benchmark should also now be treated as part of the paper
baseline rather than as an optional side check. On the widened `1990-2015` grid, the
adopted reranker still beats both transparent retrieval and preferential attachment.
The widening also clarifies that early years are not just thinner. They are a distinct
regime: fewer realized positives, younger support, higher recent-share measures, and
lower diversity/stability. The paper should say that directly.

The aligned human-usefulness check is now also populated rather than merely prepared.
Its current read is cautious: there is no overall mean-score gap between graph-selected
and preferential-attachment-selected items on the 24-row pack, but graph-selected items
do somewhat better on interpretability, usefulness, and artifact risk, while the
preferential-attachment set reads slightly more fluently on average. So the paper should
use the human result as modest external validation, not as evidence of a large
human-perceived quality gap.

## 3. Learned reranker

### Role

The reranker is the main graph-screening comparator once retrieval fixes the candidate pool.

### Training discipline

- only candidates from the retrieval layer are eligible
- all training uses vintage-respecting splits
- no future-year features
- no direct leakage from outcome construction into reranker inputs

### Feature families to compare

Use the existing repo families as the starting comparison set:

- `base`
- `structural`
- `dynamic`
- `composition`
- `boundary_gap`

### Model families to compare

- regularized logistic / GLM-style reranker
- pairwise or listwise ranking model only if it remains historically disciplined and interpretable enough for appendix reporting

### Selection rule

Choose:

- one main reranker for the paper
- one appendix reranker for robustness

using:

- historical stability across cutoffs
- interpretability
- performance over the fixed benchmark family

The design note for the paper must say explicitly what the reranker does not get to see.

### Current paper-grade winner on the headline family

The full non-sampled `path_to_direct` retune does not produce one global winner across
horizons. The paper-grade winner is horizon-specific:

- `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`, pool `5000`
- `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`, pool `5000`
- `h=15`: `glm_logit + quality`, `alpha=0.05`, pool `5000`

Against the refreshed `path_to_direct` benchmark, those winners reach:

- `h=5`: `P@100 = 0.1050`, `Recall@100 = 0.1376`, `MRR = 0.0133`
- `h=10`: `P@100 = 0.2067`, `Recall@100 = 0.1391`, `MRR = 0.0103`
- `h=15`: `P@100 = 0.2640`, `Recall@100 = 0.1541`, `MRR = 0.0116`

### New quality-layer confirmation

A later narrow full-sample confirmation on the three finalist feature families changes the
ranking-design read in an important way. In that confirmatory pass, `quality` is the
winner at all three horizons:

- `h=5`: `glm_logit + quality`, `alpha=0.20`, pool `10000`
- `h=10`: `glm_logit + quality`, `alpha=0.20`, pool `10000`
- `h=15`: `glm_logit + quality`, `alpha=0.10`, pool `10000`

That means the quality-layer features should now be treated as the leading reranker family
for the next `path_to_direct` comparison pass, rather than just as an appendix challenger.

For paper-facing language, `quality` should likely be renamed to something narrower such
as `candidate_sharpness`, because the actual signals are broadness, resolution, mediator
specificity, and node age rather than scientific merit in a global sense.

### Paper-consistent effective-corpus confirmation

When the same question is rerun on the exact effective corpus and pool setup used by the
paper-facing frontier, the result is more qualified. The adopted reranker stack is:

- `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`, pool `5000`
- `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`, pool `5000`
- `h=15`: `glm_logit + quality`, `alpha=0.05`, pool `5000`

So `quality` is now a real adopted winner on the paper-consistent stack, but only at the
longer horizon. The practical read is not “switch everything to quality,” but rather:

- keep the horizon-specific winner stack for the paper-consistent build
- keep `quality` as a real main-family component, not just an appendix challenger

### Current appendix-refresh interpretation

Two later appendix reruns matter for how the paper should summarize the benchmark:

- the graph score's edge is budget-dependent rather than universal:
  - strongest at tight shortlist sizes
  - fading as the shortlist becomes very broad
- the graph score does not help most in the sparsest neighborhoods:
  - the refreshed regime split shows a larger edge in dense local neighborhoods
  - sparse neighborhoods remain the hardest cases rather than the benchmark's cleanest win

## 4. Concentration control

### Role

Concentration is its own design layer. It is not an ontology patch and it is not allowed
to hide poor retrieval quality.

### Methods to compare

- no control
- calibrated soft sink penalty
- shortlist diversification or quota-style control

### Diagnostics

Every concentration comparison must report:

- top target share
- unique endpoints in top-K
- repeated-endpoint concentration
- candidate-family mix
- whether the intervention changes retrieval quality materially

### Selection rule

Adopt a default concentration control only if it improves diversity and reduces endpoint
crowding without materially breaking the main retrieval metrics.

The defense must be calibration-based:

- historical Pareto comparison
- not hand-picked penalty shapes
- not one-off fixes for a single concept such as WTP

### Current extension: paper-worthiness surface layer

The first paper-worthiness pass is now implemented as a post-frontier surfacing layer,
not as a replacement benchmark. This is deliberate. It lets the project improve surfaced
question quality without quietly changing the historical target object.

The current layer applies:

- static penalties for:
  - broad endpoint pairs
  - low-resolution endpoint combinations
  - generic endpoint flags
  - weak or generic mediators
- dynamic penalties for repeated:
  - source families
  - target families
  - semantic families
  - source themes
  - target themes
  - theme pairs

The fully tuned surface-layer backtest is now complete in:

- `outputs/paper/84_surface_layer_backtest_path_to_direct`

Selected horizon-specific surface configs:

- `h=5`
  - `top_window = 300`
  - `broad_endpoint_start_pct = 0.85`
  - `broad_endpoint_lambda = 6.0`
  - `resolution_floor = 0.08`
  - `resolution_lambda = 4.0`
  - `generic_endpoint_lambda = 2.0`
  - `mediator_specificity_floor = 0.45`
  - `mediator_specificity_lambda = 2.5`
  - `textbook_like_start_pct = 0.85`
  - `textbook_like_lambda = 4.0`
  - `source_repeat_lambda = 2.0`
  - `target_repeat_lambda = 4.0`
  - `family_repeat_lambda = 6.0`
  - `theme_repeat_lambda = 1.0`
  - `theme_pair_repeat_lambda = 4.0`
  - `broad_repeat_start_pct = 0.85`
  - `broad_repeat_lambda = 4.0`
- `h=10`
  - `top_window = 200`
  - `broad_endpoint_start_pct = 0.85`
  - `broad_endpoint_lambda = 9.0`
  - `resolution_floor = 0.08`
  - `resolution_lambda = 4.0`
  - `generic_endpoint_lambda = 2.0`
  - `mediator_specificity_floor = 0.45`
  - `mediator_specificity_lambda = 2.5`
  - `textbook_like_start_pct = 0.85`
  - `textbook_like_lambda = 4.0`
  - `source_repeat_lambda = 1.0`
  - `target_repeat_lambda = 4.0`
  - `family_repeat_lambda = 6.0`
  - `theme_repeat_lambda = 1.0`
  - `theme_pair_repeat_lambda = 2.0`
  - `broad_repeat_start_pct = 0.90`
  - `broad_repeat_lambda = 4.0`
- `h=15`
  - `top_window = 200`
  - `broad_endpoint_start_pct = 0.90`
  - `broad_endpoint_lambda = 6.0`
  - `resolution_floor = 0.08`
  - `resolution_lambda = 4.0`
  - `generic_endpoint_lambda = 2.0`
  - `mediator_specificity_floor = 0.45`
  - `mediator_specificity_lambda = 2.5`
  - `textbook_like_start_pct = 0.85`
  - `textbook_like_lambda = 4.0`
  - `source_repeat_lambda = 1.0`
  - `target_repeat_lambda = 4.0`
  - `family_repeat_lambda = 6.0`
  - `theme_repeat_lambda = 2.0`
  - `theme_pair_repeat_lambda = 4.0`
  - `broad_repeat_start_pct = 0.85`
  - `broad_repeat_lambda = 4.0`

Historical backtest effect:

- `h=5`
  - `Recall@100`: `0.128426 -> 0.134486`
  - `MRR`: `0.012286 -> 0.013765`
  - top-target share: `0.140 -> 0.107`
  - unique theme pairs: `22.33 -> 27.33`
- `h=10`
  - `Recall@100`: `0.130343 -> 0.131185`
  - `MRR`: `0.009999 -> 0.010485`
  - top-target share: `0.233 -> 0.143`
  - unique theme pairs: `29.33 -> 31.67`
- `h=15`
  - `Recall@100`: `0.118993 -> 0.122636`
  - `MRR`: `0.010971 -> 0.011147`
  - top-target share: `0.163 -> 0.107`
  - unique theme pairs: `22.00 -> 28.33`

So the surface layer is now historically useful, not just cosmetically different.

### Current paper-grade winner on the headline family

The concentration winner is also horizon-specific:

- `h=5`: `sink_plus_diversification`
- `h=10`: `diversification_only`
- `h=15`: `sink_plus_diversification`

This improves shortlist diversity without degrading the refreshed main retrieval metrics,
but it does not eliminate endpoint crowding completely. Repeated targets such as
`Willingness to Pay.`, `Renewable Energy`, and `R&D` still recur often enough that the
paper should describe the concentration result as a real improvement rather than a full fix.

### Current-frontier rebuild under the tuned surface layer

The current frontier has now been rebuilt with the selected horizon-specific reranker and
surface-layer stack in:

- `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface`

Current top-100 surfaced diagnostics:

- `h=5`
  - green share: `0.38`
  - WTP share: `0.07`
  - unique theme pairs: `32`
  - top-target share: `0.07`
- `h=10`
  - green share: `0.35`
  - WTP share: `0.11`
  - unique theme pairs: `35`
  - top-target share: `0.11`
- `h=15`
  - green share: `0.37`
  - WTP share: `0.08`
  - unique theme pairs: `32`
  - top-target share: `0.09`

This is a real concentration improvement, but it does not yet produce a fully convincing
paper-facing shortlist. The surfaced ranks still lean heavily toward broad
`causal_to_identified` anchored progression questions.

## 5. Evaluation design

### Principle

Evaluation is layered because the target family is reopened.

### Layer A. Historical continuity anchor

Main benchmark:

- later appearance of a missing ordered causal-language claim

Nested stricter benchmark:

- later appearance of a missing identified-causal claim

Metrics:

- `MRR`
- `Recall@50`
- `Recall@100`
- `Recall@500`
- `Recall@1000`

### Layer B. Family-aware historical extensions

Add family-aware tasks where the family definition makes them coherent:

- later path thickening for `direct_to_path`
- mediator growth or mechanism thickening for `mediator_expansion`

These are extensions, not replacements for the continuity anchor.

### Layer C. Screening-quality outputs

Report:

- shortlist diversity
- family balance
- endpoint concentration
- crowding / near-duplicate diagnostics

### Layer D. Human-usefulness validation

Prepare a paper-facing validation pack that compares:

- graph-selected versus baseline-selected items
- raw anchor wording versus path/mechanism wording

The rating dimensions should include:

- readability
- plausibility
- usefulness
- attention-worthiness

## Deliverables

Before implementation starts, method v2 should produce:

- one candidate-generation spec with family tags
- one transparent-model spec with decomposed outputs
- one reranker comparison spec
- one concentration-control comparison spec
- one layered evaluation spec

## Implementation order

After this design is signed off, implement in this order:

1. candidate-generation v2
2. transparent retrieval/scoring v2
3. reranker v2
4. concentration-control layer
5. evaluation runner and benchmark tables
6. paper result refresh

That ordering preserves attribution because ontology is fixed first, then the candidate
universe is fixed, then ranking changes, then concentration handling is compared, and only
then are paper results refreshed.

## Current state after the first refresh

That implementation sequence has now been completed for the headline `path_to_direct`
family. The remaining work is no longer the main method redesign. It is the secondary
family and the next extensions:

1. decide whether the `85` current frontier is good enough to support paper-facing
   examples, or whether one more paper-worthiness pass is needed first
2. complete or explicitly park the full paper-grade `direct_to_path` reranker refresh
3. run the human-usefulness pack
4. reopen supply-vs-demand ranking and node activation as the next method layer

## Current LLM role after the within-field v3 pass

The LLM layer now has a narrower and more defensible job.

- It should not be used as the main historical benchmark.
- It is currently most useful as a current-frontier cleanup layer for within-field shelves.
- The strongest current LLM object is local pairwise reranking inside a field shelf, not a global scalar score.

The working design after the v3 pass is:

1. graph retrieval and graph reranking define the candidate universe
2. a weak LLM veto removes only clear local failures
3. repeated pairwise within-field LLM judgments reorder the surviving shelf
4. scalar LLM scores remain secondary diagnostics

Current evidence also says:

- repeated `none`-reasoning pairwise screening is stable enough to use
- `low` reasoning is not yet a good replacement for structured pairwise screening because parse reliability drops too much
- a widened historical appendix usefulness sweep can be run cheaply enough to keep as supplementary evidence
- that appendix sweep should be described as a current-usefulness comparison on historical shortlist objects, not as a historical forecasting layer

## Historical benchmark scope

For the paper, the historical benchmark should likely be widened beyond the later-era cutoffs used in some recent effective-corpus passes.

- The corpus spans `1976–2026`.
- Five-year cutoff spacing is a design choice for readability and compute control, not a data constraint.
- Earlier cutoffs such as `1990` and `1995` are feasible for the main paper horizons and should be included in the widened paper benchmark unless they prove unusably noisy.
- `1985` is also feasible and should be treated as a secondary robustness extension rather than the default headline schedule.
- The main historical graph at cutoff `t` is built from the full literature observed through `t-1`, not from a hard rolling lookback window.
- Older support is downweighted using a recency transform, while stability and causal-presentation bonuses adjust edge weights within that full pre-cutoff graph.
- The widened current-stack benchmark has now been run on `1990–2015` with `1985` used only as a training warm-up cutoff.
- Main read from that widened pass:
  - the adopted reranker still beats transparent retrieval and preferential attachment
  - early cutoffs are not only thinner; they are also structurally different
  - early cutoffs look younger, more recent-share-heavy, and less diverse / stable than the later era

## Hot vs enduring interpretation

Keep a separate interpretation layer that classifies surfaced ideas into a small timing taxonomy rather than pushing this upstream into the ranking stack immediately.

- Candidate buckets to inspect later:
  - recent-surge
  - enduring-structural
  - revived / rediscovered
  - event-driven transient
- The current feature set already contains most of the needed proxies:
  - support age
  - recent-share measures
  - cooccurrence trend
  - stability
  - evidence / venue / source diversity
- Near-term plan:
  - first widen and stabilize the historical benchmark
  - then inspect whether shorter horizons load more on recent-surge signals and longer horizons on enduring-structural signals
  - only then decide whether this becomes a formal appendix interpretation or a next method extension
