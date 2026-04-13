# Broad `path_to_direct` Sampled Reranker Grid Note

Date: 2026-04-09

## Purpose

This note records the first broader sampled learned-reranker comparison for broad
`path_to_direct` after:

- freezing ontology `v2.3`
- redesigning the main anchor around `causal_claim`
- adding family-aware candidate fields
- gating the weakest `fully_open_frontier` mass conservatively

The goal is not to declare a final paper result. The goal is to decide which
learned-reranker family should be the default next candidate for broad
`path_to_direct` before we invest in a full paper-grade rerun.

## Scope and Caveat

This is a sampled design diagnostic, not a final benchmark.

Artifacts:

- sample corpus:
  - `outputs/paper/73_method_v2_sampled_reranker_grid/hybrid_corpus_sample_5pct_seed42.parquet`
- main output directory:
  - `outputs/paper/73_method_v2_sampled_reranker_grid/broad_path_to_direct`
- summary CSV:
  - `outputs/paper/73_method_v2_sampled_reranker_grid/broad_path_to_direct/reranker_summary.csv`
- script-generated markdown:
  - `outputs/paper/73_method_v2_sampled_reranker_grid/broad_path_to_direct/learned_reranker_summary.md`

Grid setup:

- paper sample fraction: `5%`
- sample seed: `42`
- cutoff years: `2000`, `2005`, `2010`, `2015`
- horizons: `5`, `10`
- pool sizes: `5000`, `10000`
- model kinds:
  - `glm_logit`
  - `pairwise_logit`
- feature families:
  - `structural`
  - `composition`
  - `boundary_gap`
  - `family_aware`
  - `family_aware_composition`
  - `family_aware_boundary_gap`

## What We Tested

The comparison asks a narrow question:

- for broad `path_to_direct`, once the candidate universe is fixed and the new
  family-aware row object is available, which learned-reranker feature family is
  the strongest default next choice?

This is a reranker question, not a candidate-generation question and not a
concentration-control question.

## Main Aggregate Result

Averaging over the sampled cutoffs, horizons, and pool sizes:

| Model | Feature family | Mean MRR | Mean Recall@100 | Mean delta Recall@100 vs pref |
|---|---|---:|---:|---:|
| `pairwise_logit` | `family_aware_boundary_gap` | `0.012190` | `0.092730` | `+0.008523` |
| `pairwise_logit` | `family_aware_composition` | `0.012104` | `0.093914` | `+0.009707` |
| `pairwise_logit` | `boundary_gap` | `0.011225` | `0.080925` | `-0.003282` |
| `pairwise_logit` | `composition` | `0.011039` | `0.081098` | `-0.003109` |
| `pairwise_logit` | `family_aware` | `0.009453` | `0.095650` | `+0.011443` |
| `pairwise_logit` | `structural` | `0.008374` | `0.074212` | `-0.009995` |
| `glm_logit` | `family_aware` | `0.004625` | `0.083562` | `-0.000645` |

Three takeaways matter.

1. Pairwise rerankers dominate GLM-style rerankers on this sampled broad
   `path_to_direct` task.

2. Richer family-aware feature sets beat plain `structural` on mean MRR.

3. The best overall mean MRR comes from `pairwise_logit +
   family_aware_boundary_gap`, with `pairwise_logit + family_aware_composition`
   extremely close behind.

## How To Read The Close Race

The top three pairwise candidates are doing slightly different things.

### `pairwise_logit + family_aware_boundary_gap`

Strengths:

- best average MRR across the sampled grid
- positive average delta against preferential attachment on both MRR and
  Recall@100
- strongest single default if we want one family that still respects the fact
  that broad `path_to_direct` remains a gap-like screening task

Interpretation:

- once the candidate universe contains explicit subfamily and scope signals, the
  classic gap and boundary cues become more useful again, but only when they are
  layered on top of the richer family-aware object

### `pairwise_logit + family_aware_composition`

Strengths:

- essentially tied on mean MRR
- slightly better average Recall@100 than `family_aware_boundary_gap`
- strongest result at `pool = 5000`, `h = 10` by mean MRR

Interpretation:

- evidence-quality and composition signals still matter a lot, especially once
  the broad frontier object has been cleaned up and subfamily-aware fields are
  available

### `pairwise_logit + family_aware`

Strengths:

- highest mean Recall@100 of the tested pairwise families
- largest average Recall@100 improvement over preferential attachment

Weakness:

- noticeably lower mean MRR than the two richer family-aware variants

Interpretation:

- if we cared mostly about broader shortlist coverage, this would still be a
  serious candidate
- if we care about the top of the ranking, it is not the best default

## Variation Across Pools and Horizons

The best model is not literally identical in every sampled cell.

By mean MRR within each `(pool_size, horizon)` cell:

- `pool=5000`, `h=5`:
  - `pairwise_logit + family_aware_boundary_gap`
- `pool=5000`, `h=10`:
  - `pairwise_logit + family_aware_composition`
- `pool=10000`, `h=5`:
  - `pairwise_logit + family_aware_boundary_gap`
- `pool=10000`, `h=10`:
  - `pairwise_logit + boundary_gap`

The script's saved `reranker_best_configs.csv` uses its own selection objective,
which picks `glm_logit + family_aware` at `pool=10000`, `h=10`. I do not think
that one-cell exception should drive the default. The larger pattern is more
important:

- pairwise models are stronger overall
- enriched family-aware families are where the gains are
- the contest is mainly between:
  - `family_aware_boundary_gap`
  - `family_aware_composition`

## Recommendation

My recommendation for the next full run is:

- default learned reranker for broad `path_to_direct`:
  - `pairwise_logit + family_aware_boundary_gap`
- appendix or close alternative:
  - `pairwise_logit + family_aware_composition`
- recall-first alternative:
  - `pairwise_logit + family_aware`

Why this default:

1. It has the best mean MRR in the sampled grid.
2. It remains positive against preferential attachment on average.
3. It matches the substantive interpretation of broad `path_to_direct`:
   - still a gap-screening task
   - but now one that should know whether the gap is fully open, contextual, or
     already anchored by ordered/causal evidence.

## What This Does Not Yet Settle

This note does not settle:

- the final paper reranker
- the concentration-control default
- whether the full paper should eventually use one reranker for all families or
  separate rerankers by family

It only settles the next best candidate default for the broad `path_to_direct`
family on the sampled design loop.

## Next Step

The next evidence step should be:

1. run the same comparison on the full non-sampled corpus for broad
   `path_to_direct`
2. keep the main contenders fixed:
   - `pairwise_logit + family_aware_boundary_gap`
   - `pairwise_logit + family_aware_composition`
   - `pairwise_logit + family_aware`
3. then move to concentration-control comparison on top of the winning reranker

That keeps the decision path clean:

- candidate object first
- reranker family second
- concentration control third
