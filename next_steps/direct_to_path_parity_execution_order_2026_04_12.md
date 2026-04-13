# Direct-to-Path Parity Execution Order

Date: 2026-04-12

This note turns the `must rerun` bucket from
`next_steps/option_c_dual_family_parity_map_2026_04_12.md` into a concrete execution
order.

The governing rule is:

- change family first
- hold path length fixed
- do not mix in the longer-path exercise yet

So the immediate target is:

- bring `direct-to-path` to parity with the current paper-grade `path-to-direct` stack
- at the current path setting
- on the current effective corpus

## 0. Precondition

Before running anything:

- keep the corpus fixed at `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`
- keep the current ontology fixed
- keep the current path setting fixed
- do not reopen the more speculative `something-from-nothing` object

Current graph fact worth keeping in mind:

- the support graph is already short-path
- sampled reachable-pair shortest paths are mostly length `3` or `4`
- so a later `max_len` exercise should probably test `2, 3, 4, maybe 5`, not jump to `10`

## 1. Stage order

The correct sequence is:

1. family-level historical panel and strict shortlist
2. reranker parity
3. concentration / surfaced frontier parity
4. budget frontier parity
5. heterogeneity parity
6. temporal generalization parity
7. current surfaced examples
8. only then decide:
   - what goes in the main text
   - what stays appendix

## 2. Stage 1: Family-level historical panel and strict shortlist

### Goal

Answer the first question before spending time on rerankers:

- is `direct-to-path` a sensible historical object on the current corpus?

### Deliverables

- candidate counts by cutoff year and horizon
- realized-positive counts in universe
- strict shortlist metrics for:
  - preferential attachment
  - transparent graph score
  - co-occurrence if we keep it in the auxiliary comparison set
- family comparison summary against current `path-to-direct`

### Scripts

- `scripts/compare_method_v2_families.py`
- `scripts/run_effective_benchmark_widened.py`

### Why this stage comes first

If `direct-to-path` produces a candidate universe or positive-rate profile that is too
thin, too dense, or too unstable, that should be visible before we spend compute on full
reranker retuning.

### Output directory recommendation

- `outputs/paper/144_family_compare_fixed_pathlen`
- `outputs/paper/145_effective_benchmark_direct_to_path`

### Stop/go rule

Proceed only if all of the following hold:

- the candidate universe is large enough to support a top-100 task
- realized positives in universe are not pathologically sparse
- the transparent score is not obviously degenerate
- the family comparison is substantively interpretable rather than mechanically broken

If this stage fails, stop and rethink the object before any reranker work.

## 3. Stage 2: Reranker parity

### Goal

Bring `direct-to-path` to the same reranker standard as the current `path-to-direct`
paper stack.

### Deliverables

- feature panel for `direct-to-path`
- sampled or narrow tuning only if needed to prune the grid
- full non-sampled reranker tuning
- horizon-specific winner selection
- paper-facing benchmark summary table for `direct-to-path`

### Scripts

- `scripts/run_learned_reranker_tuning.py`
- `src/analysis/learned_reranker.py`

### Notes

The existing tuning script already accepts `--candidate-family-mode`. So the key issue is
not wiring but compute and result discipline.

### Output directory recommendation

- `outputs/paper/146_direct_to_path_reranker_tuning_sampled` only if needed
- `outputs/paper/147_direct_to_path_reranker_tuning_full`

### Stop/go rule

Proceed only if:

- the reranker beats or at least meaningfully differs from the transparent score
- the best winner is stable enough to summarize by horizon
- the result reads like a real family, not a thin appendix curiosity

If the reranker adds nothing, that itself is a substantive finding. But we should know it
before building the rest of the comparison package.

## 4. Stage 3: Concentration and current-frontier parity

### Goal

Produce readable surfaced shortlists for `direct-to-path`, not just historical metrics.

### Deliverables

- concentration comparison
- adopted surface-layer choice by horizon
- current reranked frontier
- initial shortlist inspection note

### Scripts

- `scripts/build_current_reranked_frontier.py`
- the same concentration layer machinery used in the current `path-to-direct` chain

### Output directory recommendation

- `outputs/paper/148_direct_to_path_concentration`
- `outputs/paper/149_current_reranked_frontier_direct_to_path`

### Why this stage matters

The paper will not be persuasive if `direct-to-path` is historically strong but its
surfaced top ranks are unreadable or repetitive. This is where we find out whether the
family produces economist-facing examples that belong in the paper.

### Stop/go rule

Proceed only if:

- the surfaced shortlist is readable enough to inspect
- concentration is improved enough that examples are not all the same endpoint
- the shortlist reveals substantive mechanism questions economists would care about

## 5. Stage 4: Budget frontier parity

### Goal

Compare how the two families behave when the reading budget changes.

### Deliverables

- attention-allocation frontier for `direct-to-path`
- broader-shortlist or pooled-frontier comparison
- if useful, simple-score-at-`K` curves

### Scripts

- `scripts/run_attention_allocation_refresh.py`
- `scripts/run_retrieval_budget_eval.py`

### Output directory recommendation

- `outputs/paper/150_attention_allocation_direct_to_path`
- `outputs/paper/151_retrieval_budget_direct_to_path`

### Why this stage comes after the reranker and frontier build

The reading-budget figures matter only once we know the family is historically viable and
surfaceable.

### Stop/go rule

Proceed if the frontier is interpretable enough to compare with `path-to-direct` in paper
space.

If the family is historically viable but budget behavior is nearly identical, that is
useful too. It would suggest family differences belong more in surfaced examples and path
development than in every benchmark figure.

## 6. Stage 5: Heterogeneity parity

### Goal

See whether the two families help in the same kinds of literatures.

### Deliverables

- journal-tier heterogeneity
- method-family heterogeneity
- if worth keeping, funding interaction
- if worth keeping, regime split

### Scripts

- `src/analysis/field_heterogeneity.py`
- `scripts/run_field_conditioned_budget_eval.py`

### Output directory recommendation

- `outputs/paper/152_direct_to_path_heterogeneity`

### Why this stage matters

This is where the paper can move from “two tasks” to “two kinds of research progress.”
If the subgroup patterns differ meaningfully, that becomes a substantive result rather
than just a benchmarking complication.

## 7. Stage 6: Temporal generalization parity

### Goal

Check whether the `direct-to-path` reranker generalizes forward.

### Deliverables

- held-out-era performance table or figure
- direct comparison with the current `path-to-direct` temporal result

### Scripts

- `scripts/run_temporal_generalization_refresh.py`

### Output directory recommendation

- `outputs/paper/153_temporal_generalization_direct_to_path`

### Why this is not earlier

Temporal generalization is a credibility check on a family that is already otherwise
worth keeping. It should not be the first screen.

## 8. Stage 7: Current surfaced examples and paired paper examples

### Goal

Build the actual paired examples the paper will use.

### Deliverables

- curated `path-to-direct` examples
- curated `direct-to-path` examples
- paired examples showing how the two objects differ

### Suggested criterion

Try to build pairs where the same broad domain could plausibly support both objects:

- `broadband access -> search frictions -> business formation`
- `trade liberalization -> imported inputs -> firm productivity`
- `transit investment -> commute time -> employment`

That will make the distinction legible in the introduction and path-development section.

## 9. Main-text pieces to build only after Stage 7

Do not rewrite the paper in parallel with the reruns.

Wait until the family comparison exists, then decide which of these become paired
main-text displays:

- main benchmark figure
- main benchmark summary table
- budget frontier
- pooled frontier
- heterogeneity figure
- curated examples table
- path-development section

At that point the paper can decide whether:

- both families belong in the main text at equal weight
- one is main text and the other appendix
- or the paper should be explicitly structured around the comparison itself

## 10. What should still wait

Even after parity, do not immediately reopen:

- longer-path support variation
- grouped SHAP and deep reranker interpretation for both families
- expanded human-usefulness packs
- more open-ended `something-from-nothing` graph emergence

Those are the second wave. The first wave is dual-family parity.

## 11. Recommended execution order in one list

1. `compare_method_v2_families.py` on the effective corpus
2. `run_effective_benchmark_widened.py` for `direct-to-path`
3. `run_learned_reranker_tuning.py` for `direct-to-path`
4. concentration selection and current frontier build for `direct-to-path`
5. attention-allocation / retrieval-budget runs
6. heterogeneity runs
7. temporal generalization run
8. curate paired examples
9. only then rewrite the paper structure around the dual-family comparison

## 12. Practical recommendation

If we want to move quickly and stay disciplined, we should treat Stages 1 and 2 as the
first checkpoint.

After those two stages, we should stop and assess:

- is `direct-to-path` strong enough to justify doubling the main result displays?
- does it tell a substantively different story from `path-to-direct`?
- is the surfaced object strong enough to be economist-facing rather than only
  method-facing?

If the answer is yes, we proceed through Stages 3 to 7 and then rebuild the paper around
Option C. If the answer is mixed, we still learned something important before spending
time on path-length exercises or more speculative graph objects.
