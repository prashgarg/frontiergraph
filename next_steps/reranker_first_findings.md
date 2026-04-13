# Frozen-Ontology Reranker: First Findings

## What we ran

### Initial pass
- Full frozen-ontology reranker pass on the real corpus:
  - corpus: `data/processed/research_allocation_v2/hybrid_corpus.parquet`
  - cutoffs: `1990, 2000, 2010, 2015`
  - horizons: `5, 10`
  - pool sizes: `10,000` and `20,000`
  - model families: `glm_logit`, `pairwise_logit`
  - feature families: `base`, `structural`, `dynamic`, `composition`, `boundary_gap`
- Outputs:
  - `outputs/paper/13_learned_reranker_initial/`

### Focused tuning pass
- Denser frozen-ontology tuning pass:
  - cutoffs: `1990, 1995, 2000, 2005, 2010, 2015`
  - horizons: `5, 10`
  - pool size: `10,000`
  - feature families: `structural`, `composition`, `boundary_gap`
  - model families: `glm_logit`, `pairwise_logit`
  - alpha grid: `0.01, 0.05, 0.10, 0.20`
- Outputs:
  - `outputs/paper/14_learned_reranker_tuning/`

### Current-frontier application
- Applied the best tuned horizon-specific rerankers to the current frontier candidate pool.
- Outputs:
  - `outputs/paper/15_current_reranked_frontier/`
  - `outputs/paper/16_current_path_mediator_shortlist/`

## Main conclusion

Gate 2 is now **passed**.

At least one learned reranker beats both:
- the current transparent score
- preferential attachment

This is true on both:
- `MRR`
- `Recall@100`

So the learned-reranker stage is not speculative anymore. It is a real improvement on the frozen ontology.

## Best current tuned configurations

### Horizon 5
- best tuned variant:
  - `pairwise_logit + composition`
  - `alpha = 0.20`
  - `pool = 10,000`
- aggregate performance:
  - `MRR = 0.008071`
  - `Recall@100 = 0.071303`
  - `delta MRR vs transparent = +0.002803`
  - `delta Recall@100 vs transparent = +0.034882`

### Horizon 10
- best tuned variant:
  - `glm_logit + structural`
  - `alpha = 0.01`
  - `pool = 10,000`
- aggregate performance:
  - `MRR = 0.006402`
  - `Recall@100 = 0.060920`
  - `delta MRR vs transparent = +0.002269`
  - `delta Recall@100 vs transparent = +0.028161`

## What the reranker seems to learn

The first pass and tuning pass together suggest:
- the useful signal is not just the current transparent score
- structural and composition features matter
- the better reranker is horizon-specific:
  - short-horizon ranking seems to benefit more from richer composition-style information
  - longer-horizon ranking seems to benefit more from a simpler structural model

This is encouraging because it is not just “same score, slightly retuned.” The reranker is learning something additional.

## Ripeness panel read

The ripeness outputs are promising even before refinement.

### Path to direct closure
- `h=5` realization rate rises across ripeness quintiles from:
  - `0.0123` to `0.0496`
- `h=10` realization rate rises across ripeness quintiles from:
  - `0.0259` to `0.0971`

### Direct to path thickening
- `h=5` realization rate rises from:
  - `0.0256` to `0.2685`
- `h=10` realization rate rises from:
  - `0.0790` to `0.4807`

So the ripeness object is not empty. There is a usable monotonic pattern already.

The `direct_to_path` thickening signal is especially strong, which matters for the paper: it supports the idea that the better surfaced object is often richer than a single missing edge.

## Current-frontier application: good news and caution

Applying the tuned rerankers to the current frontier produced a very strong reshuffle.

That is useful, but it also revealed two issues.

### 1. The raw reranker is not the right surfaced object
- In the first raw reranked top 100:
  - one endpoint family dominated the surfaced list
  - the list was pulled toward artifacts like `Method of Moments Quantile Regression (MMQR)` and `place of residence`
- That turned out to be a surfaced-endpoint problem, not a reason to discard the historical reranker gains.

### 2. A deterministic surfaced-endpoint filter fixes the main pathology
After adding:
- a method/metadata penalty
- an unresolved-code penalty on displayed endpoint labels
- a small broad-label penalty for a few generic container endpoints

the surfaced shortlist becomes much more credible.

Representative rendered questions now include:
- `Through which nearby pathways might income tax rate shape CO2 emissions?`
- `Through which nearby pathways might financial development shape green innovation?`
- `Through which nearby pathways might technological innovation shape green innovation?`
- `Which nearby mechanisms most plausibly link environmental pollution to carbon emissions?`
- `Which nearby mechanisms most plausibly link environmental regulation to sustainable development?`

That does not mean the current shortlist is publication-ready. It does mean the project now has a plausible internal current-frontier object.

### 3. The next bottleneck is no longer endpoint pathology
After the two-layer surfaced filter, the main remaining weaknesses are:
- unresolved mediator labels in the explanation lines
- semantically awkward or redundant pairs such as `CO2 emissions -> carbon emissions`
- repeated family patterns like business-cycle to willingness-to-pay variants

So the project has moved from:
- endpoint-quality failure

to:
- semantic redundancy and explanation-quality cleanup

## What this means for the paper

The paper can now say, internally and eventually publicly:
- the direct-edge object remains the historical benchmark anchor
- the surfaced research object is usually path-rich or mechanism-rich
- a learned reranker on the current graph improves historical screening
- questions also show a ripeness pattern over time

That is a materially stronger paper than the original transparent-score-only version.

## Recommended next steps

### Immediate
1. Review the filtered path/mechanism shortlist manually and tag:
   - clearly strong examples
   - readable but redundant examples
   - readable but weak examples
2. Improve explanation quality in the path/mechanism layer by reducing unresolved mediator labels where possible.
3. Decide whether a light semantic-deduplication or repeated-family penalty is needed on the surfaced shortlist.

### Next modeling step
4. Trial a light diversity-aware or semantic-deduplication post-rerank layer on the current frontier only.
   Candidate ideas:
   - endpoint cap
   - diminishing returns for repeated endpoint reuse
   - quota on repeated target exposure
   - soft deduplication for near-equivalent target families

This should be treated as a **presentation/ranking regularization layer**, not as the main historical benchmark model unless it also improves backtests.

### Later
5. Only after the above, decide whether the repeated unresolved mediator labels or merged semantic families justify an earlier minimal ontology patch.

## Files to inspect
- `outputs/paper/13_learned_reranker_initial/learned_reranker_summary.md`
- `outputs/paper/14_learned_reranker_tuning/tuning_summary.md`
- `outputs/paper/15_current_reranked_frontier/current_reranked_frontier.md`
