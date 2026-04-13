# Ranker v3 Full-Sample Confirmation and Surface Layer

Date: 2026-04-09

## Scope

This note records two follow-on checks after the sampled quality-layer pass:

1. a narrow full-sample reranker confirmation on the three finalist feature families
2. a first paper-worthiness / de-crowding surface layer applied to the existing paper-grade `path_to_direct` frontier

The ontology remains frozen. The benchmark object remains broad `path_to_direct` on the
`causal_claim` anchor.

## 1. Full-sample reranker confirmation

Run:

- corpus: `data/processed/research_allocation_v2/hybrid_corpus.parquet`
- family: `path_to_direct`
- scope: `broad`
- pool: `10000`
- horizons: `5, 10, 15`
- feature families:
  - `family_aware_composition`
  - `quality`
  - `family_aware_boundary_gap`
- model kind:
  - `glm_logit`
- alphas:
  - `0.05, 0.10, 0.20`

Output directory:

- `outputs/paper/81_quality_layer_fullsample_confirm_path_to_direct`

Result:

- `quality` wins all three horizons in the narrow full-sample confirmation

Best configs:

- `h=5`: `glm_logit + quality`, `alpha=0.20`, pool `10000`
- `h=10`: `glm_logit + quality`, `alpha=0.20`, pool `10000`
- `h=15`: `glm_logit + quality`, `alpha=0.10`, pool `10000`

Mean benchmark metrics:

- `h=5`: `MRR = 0.003515`, `Recall@100 = 0.045837`
- `h=10`: `MRR = 0.003697`, `Recall@100 = 0.047950`
- `h=15`: `MRR = 0.003560`, `Recall@100 = 0.042358`

Mean deltas:

- versus transparent:
  - `h=5`: `delta MRR = +0.001713`, `delta Recall@100 = +0.012971`
  - `h=10`: `delta MRR = +0.001612`, `delta Recall@100 = +0.018829`
  - `h=15`: `delta MRR = +0.000940`, `delta Recall@100 = +0.011723`
- versus preferential attachment:
  - `h=5`: `delta MRR = +0.002055`, `delta Recall@100 = +0.026234`
  - `h=10`: `delta MRR = +0.001611`, `delta Recall@100 = +0.024268`
  - `h=15`: `delta MRR = +0.001045`, `delta Recall@100 = +0.017793`

Interpretation:

- the sampled result was not a fluke
- the quality-layer features are doing real historical work
- `family_aware_composition` remains competitive, but `quality` is now the clean leading challenger and the narrow full-sample winner

## 2. Surface-layer defaults

The first paper-worthiness / de-crowding pass is implemented as a paper-facing surface
layer rather than as a new historical benchmark.

Current defaults:

- `top_window = 200`
- `broad_endpoint_start_pct = 0.85`
- `broad_endpoint_lambda = 6.0`
- `resolution_floor = 0.08`
- `resolution_lambda = 4.0`
- `generic_endpoint_lambda = 2.0`
- `mediator_specificity_floor = 0.45`
- `mediator_specificity_lambda = 2.5`

These parameters are not yet tuned on a historical benchmark objective. They are an
explicit paper-facing surfacing rule applied after frontier ranking. That is deliberate:
the goal here is shortlist quality, not a hidden change to the benchmark target.

The implemented static penalties are:

- broad endpoint penalty
- low-resolution penalty
- generic endpoint flag penalty
- weak or generic mediator penalty

The dynamic penalties are:

- repeated source family
- repeated target family
- repeated semantic family
- repeated source theme
- repeated target theme
- repeated theme pair

## 3. First surface-layer comparison

For a fast comparison, the layer was applied directly to the existing paper-grade
frontier:

- source frontier:
  - `outputs/paper/78_current_reranked_frontier_path_to_direct/current_reranked_frontier.csv`
- comparison output:
  - `outputs/paper/82_surface_layer_from_existing_frontier`

Top-100 comparison:

- `h=5`
  - green share: `0.49 -> 0.41`
  - WTP share: `0.14 -> 0.17`
  - unique theme pairs: `31 -> 40`
- `h=10`
  - green share: `0.51 -> 0.39`
  - WTP share: `0.14 -> 0.15`
  - unique theme pairs: `37 -> 43`
- `h=15`
  - green share: `0.52 -> 0.42`
  - WTP share: `0.14 -> 0.17`
  - unique theme pairs: `31 -> 39`

Interpretation:

- the surface layer clearly improves theme diversity
- it reduces climate/green crowding in the top-100 at all three horizons
- it does not reduce WTP repetition yet
- it does not, by itself, make the shortlist dramatically sharper or narrower

So the first de-crowding layer looks useful, but partial.

## 4. What this means

Two conclusions are now strong:

1. `quality` should be treated as the current leading reranker family for the next
   `path_to_direct` reranker comparison.
2. paper-worthiness should be treated as a post-frontier surfacing layer, at least in
   the next pass, rather than silently folded into the historical benchmark.

The next improvement should target what is still not fixed:

- repeated broad economic endpoints
- repeated `Willingness to Pay`
- obvious or textbook-like endpoint pairs
- mediator questions that are graph-plausible but not especially worth attention

## 5. Paper-consistent effective-corpus confirmation

The narrow full-sample confirmation above was useful, but it was not run on the exact
effective corpus and pool setup used by the paper-facing frontier build. So a second
paper-consistent confirmation was run on:

- corpus: `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`
- pool: `5000`
- cutoffs: `2000, 2005, 2010, 2015`
- horizons: `5, 10, 15`
- output:
  - `outputs/paper/83_quality_confirm_path_to_direct_effective`

Result:

- `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`
- `h=10`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`
- `h=15`: `glm_logit + quality`, `alpha=0.05`

Under the adoption rule for the surface-layer backtest:

- `h=5`: keep paper-grade fallback `glm_logit + family_aware_boundary_gap`, `alpha=0.20`
- `h=10`: keep paper-grade fallback `pairwise_logit + family_aware_composition`, `alpha=0.10`
- `h=15`: adopt `glm_logit + quality`, `alpha=0.05`

So the paper-consistent conclusion is more qualified than the earlier narrow full-sample
check. `quality` remains important and is the adopted winner at `h=15`, but it does not
replace the horizon-specific stack on the effective paper corpus.

## 6. Tuned surface-layer backtest

The full balanced surface-layer backtest was then run by horizon and combined into:

- `outputs/paper/84_surface_layer_backtest_path_to_direct`

Selected paper-facing surface configs:

- `h=5`:
  - model: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`
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
- `h=10`:
  - model: `pairwise_logit + family_aware_composition`, `alpha=0.10`
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
- `h=15`:
  - model: `glm_logit + quality`, `alpha=0.05`
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

Historical impact:

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

So the tuned surface layer is not just cosmetically different. On the historical
backtest it lowers concentration and slightly improves ranking metrics at the same time.

## 7. Current-frontier rebuild

The current frontier was rebuilt with the selected horizon-specific reranker and
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

Interpretation:

- the tuned surface layer does reduce crowding in a real way
- WTP repetition is materially lower than in the earlier paper-facing shortlist
- but the surfaced frontier is still dominated by broad anchored progression items
- the top surfaced questions still often read as plausible but too broad, too familiar,
  or too label-driven to use as a stable paper-facing shortlist without another
  paper-worthiness pass

So this pass should be read as:

- a successful concentration and surface-quality improvement
- not yet the final public-facing shortlist
