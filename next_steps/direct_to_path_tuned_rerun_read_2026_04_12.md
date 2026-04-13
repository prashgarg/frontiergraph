# Direct-to-Path Tuned Rerun Read

Date: 2026-04-12

This note summarizes the rerun of the widened `direct-to-path` benchmark after replacing
the provisional adopted model file with the direct-to-path-specific tuning results from
`147_direct_to_path_reranker_tuning_full`.

Sources:

- provisional widened benchmark:
  - `outputs/paper/145_effective_benchmark_direct_to_path`
- direct-to-path reranker tuning:
  - `outputs/paper/147_direct_to_path_reranker_tuning_full`
- tuned widened benchmark:
  - `outputs/paper/148_effective_benchmark_direct_to_path_tuned`

## 1. Adopted models now used in the widened benchmark

- `h=5`: `pairwise_logit + structural`, `alpha=0.01`
- `h=10`: `glm_logit + structural`, `alpha=0.01`
- `h=15`: `pairwise_logit + boundary_gap`, `alpha=0.01`

## 2. Headline change relative to the provisional direct-to-path benchmark

Recall@100:

- `h=5`: `0.0656 -> 0.0765`
- `h=10`: `0.0775 -> 0.0998`
- `h=15`: `0.0832 -> 0.0866`

MRR:

- `h=5`: `0.00461 -> 0.00499`
- `h=10`: `0.00459 -> 0.00874`
- `h=15`: `0.00616 -> 0.00575`

Interpretation:

- the direct-to-path-specific tuning materially improves the widened benchmark
- the gain is especially large at `h=10`
- at `h=15`, the tuned model improves Recall@100 but gives up some MRR relative to the
  provisional model

## 3. Current direct-to-path picture

The tuned widened benchmark now looks strong enough for the dual-family paper.

Average Recall@100 in the tuned widened run:

- `h=5`: adopted `0.0765`, transparent `0.0165`, preferential attachment `0.0099`
- `h=10`: adopted `0.0998`, transparent `0.0129`, preferential attachment `0.0070`
- `h=15`: adopted `0.0866`, transparent `0.0122`, preferential attachment `0.0067`

So the broad conclusion is stable:

- `direct-to-path` is a real and useful object
- the transparent score alone is not enough
- the family-specific reranker changes the picture substantially

## 4. What this means for the paper

The paper should no longer compare `path-to-direct` against a provisional
`direct-to-path` adopted model.

The correct comparison object is now:

- path-to-direct refreshed benchmark stack
- direct-to-path tuned benchmark stack from `148`

That is the right basis for:

- strict shortlist comparison
- reranker comparison
- reading-budget frontier
- heterogeneity
- surfaced examples

## 5. Remaining caution

The `h=15` model choice is not unambiguously dominant on every metric. The selected
`pairwise_logit + boundary_gap` variant wins on the tuning objective, but the older
provisional widened benchmark had slightly higher MRR at `h=15`.

That does not invalidate the tuned run. It does mean that when we pair families in the
paper, we should not overstate a single scalar notion of “best” without saying whether we
care most about MRR or Recall@100 at the shortlist size economists actually inspect.
