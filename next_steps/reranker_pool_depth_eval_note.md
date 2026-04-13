# Reranker Pool Depth Evaluation Note

Date: 2026-04-10

## Purpose

This note asks a more specific question than the transparent retrieval-budget note:

- once we fix the reranker, how much does a larger retrieval pool actually buy us?
- does `5000` look justified relative to `500`, `2000`, and `10000`?

Outputs:

- conditional-only first pass:
  - `outputs/paper/91_reranker_pool_depth_eval_path_to_direct`
- corrected common-universe pass:
  - `outputs/paper/92_reranker_pool_depth_eval_path_to_direct_maxpool`

The corrected `92` run is the one to use.

## Setup

This pass uses the effective corpus and the already adopted paper-consistent reranker
specification by horizon:

- `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`
- `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`
- `h=15`: `glm_logit + quality`, `alpha=0.05`

Pool sizes compared:

- `500`
- `2000`
- `5000`
- `10000`

Cutoffs requested:

- `2000, 2005, 2010, 2015`

Valid evaluation cutoffs by horizon after requiring enough look-ahead and at least one
earlier training cutoff:

- `h=5`: `2005, 2010, 2015`
- `h=10`: `2005, 2010, 2015`
- `h=15`: `2005, 2010`

## Why the corrected run matters

The first pass (`91`) measured reranker performance only against positives inside the
same pool. That is useful, but not enough for a pool-size decision.

The corrected pass (`92`) also measures each pool against a common positive universe:

- the positives inside the `top10000` pool for the same cutoff and horizon

That gives a cleaner comparison of how much of the available rerankable universe each
pool actually recovers.

## Main result

The cleanest metric here is:

- `Recall@100 vs top10000`

On that metric:

### h=5

- pool `500`: `0.0977`
- pool `2000`: `0.1108`
- pool `5000`: `0.0968`
- pool `10000`: `0.0925`

### h=10

- pool `500`: `0.0739`
- pool `2000`: `0.0906`
- pool `5000`: `0.0962`
- pool `10000`: `0.0750`

### h=15

- pool `500`: `0.0787`
- pool `2000`: `0.0939`
- pool `5000`: `0.0880`
- pool `10000`: `0.0760`

So:

- `500` is too small
- `10000` is too large for this top-100 objective
- `2000` is best at `h=5` and `h=15`
- `5000` is only slightly best at `h=10`

## What this means intuitively

This is the key tradeoff:

- larger pools expose more future positives to the reranker
- but they also expose much more noise

The corrected results suggest:

- moving from `500` to `2000` gives the reranker meaningfully better room to work
- moving from `2000` to `5000` gives only mixed gains
- moving from `5000` to `10000` mostly hurts top-100 performance

So the reranker does benefit from a pool larger than `500`, but not from the largest
pool available.

## Depth usage still matters

Even though `5000` is not clearly best on the common-universe top-100 metric, the
depth-usage diagnostics still show that larger pools let the reranker reach much deeper
into the transparent ranking.

For example at `h=5`:

- pool `2000`: mean transparent rank in reranked top-100 is about `637`
- pool `5000`: about `1421`
- pool `10000`: about `2947`

So deeper pools do change what the reranker can surface. The question is whether that
extra depth pays off on the historical objective. The answer here is:

- only partly, and not enough to justify `10000`

## Practical takeaway

If we want one historically defensible default pool for the top-100 benchmark,

- `2000` now looks like the strongest challenger to the current `5000` default

More precisely:

- `2000` looks like the best single compromise on this evidence
- `5000` remains defensible as a robustness setting or a medium-run alternative
- `10000` does not look worthwhile for the current top-100 objective

## What this does not settle

This note does not by itself settle the final paper default, because:

- current-frontier shortlist quality may still differ between pool sizes
- the pool-size comparison here holds the reranker family fixed by horizon rather than
  re-tuning the full model class at each pool

So this is strong evidence, but not yet the last word.

## Recommended next step

The next clean follow-up is:

- run one current-frontier build at pool `2000`
- compare it directly to the current pool-`5000` frontier on:
  - shortlist quality
  - concentration
  - broadness
  - readability

That will tell us whether the historical advantage of `2000` also carries into the
current surfaced shortlist.
