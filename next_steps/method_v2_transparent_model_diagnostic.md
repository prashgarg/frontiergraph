# Method v2 Transparent Model Diagnostic

## Scope

This note records the first transparent-model redesign step after freezing the ontology baseline and introducing family-aware candidate generation.

Important caveat:
- this is a design diagnostic, not a paper-grade benchmark run
- it uses a sampled slice of the latest effective corpus to make the iteration tractable
- results should guide the next implementation step, not replace a full backtest

## Diagnostic Setup

Corpus:
- `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`

Target:
- `candidate_kind = causal_claim`

Family comparison setting:
- cutoff year `t = 2010`
- horizon `h = 5`
- paper sample fraction `0.05`
- sample seed `42`
- `max_neighbors_per_mediator = 2`

Artifacts:
- pre-redesign sampled run:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled`
- first family-aware transparent-score run:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled_v2score`
- corrected coverage-aware sampled run:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled_v2score_cov`
- anchored `path_to_direct` robustness slice:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled_v3anchored_cov`
- coverage-aware sampled run with explicit subfamily labels:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled_v4subfamily_cov`
- coverage-aware sampled run with conservative `fully_open_frontier` gating:
  - `outputs/paper/72_method_v2_family_comparison_t2010_h5_sampled_v5fullyopen_gate`

## What The Sample Says

Candidate-universe shape:
- `path_to_direct` is much larger: `30,923` candidates
- `direct_to_path` is smaller: `12,018` candidates
- but `path_to_direct` has very low future-event coverage once we intersect with the actual candidate universe:
  - `27` in-universe future positives out of `5,519` global future positives
  - `0.49%` future coverage
  - `0.000873` positive rate
- `direct_to_path` also has low global-event coverage, but it is a much cleaner task inside its own candidate universe:
  - `393` in-universe future positives out of `473,451` global future path events
  - `0.083%` future coverage
  - `0.032701` positive rate

Status mix:
- `path_to_direct` is overwhelmingly `fully_open` (`97.0%`)
- `direct_to_path` is overwhelmingly `main_direct_present__path_missing` (`96.6%`)

Subfamily mix:
- `path_to_direct` broad is overwhelmingly `fully_open_frontier` (`97.0%`)
- the only substantial non-open slice is `contextual_to_ordered` (`2.1%`)
- the most anchored slice is `ordered_to_causal` (`0.8%`)
- `direct_to_path` is mostly `causal_direct_to_path` (`96.6%`) with a small `identified_direct_to_path` tail (`3.4%`)

Interpretation:
- `direct_to_path` is a comparatively clean “existing claim, missing mechanism path” task
- `path_to_direct` is a much broader and more heterogeneous open-frontier task
- the new row schema confirms that broad `path_to_direct` is mixing:
  - a huge fully-open frontier
  - a smaller contextual-to-ordered progression slice
  - a very small anchored ordered-to-causal slice

## Why The Old Transparent Score Was Not Enough

Before the redesign:
- `direct_to_path` main score lost to preferential attachment
  - recall@100: `0.0076` versus `0.0229`
  - MRR: `0.000726` versus `0.001621`
- `path_to_direct` main score only barely beat the weak co-occurrence baseline at the very top, and did not clearly dominate preferential attachment at deeper cutoffs

This suggested:
- `direct_to_path` needed an opportunity-style score based on the surrounding support graph, not a weak direct-support-only heuristic
- `path_to_direct` needed clearer decomposition into support, provenance, specificity, and topology, even if candidate-side improvements would still be necessary later

## First Redesign

The new transparent score in `src/analysis/common.py` now makes five components explicit:
- `transparent_support_strength_component`
- `transparent_opportunity_component`
- `transparent_specificity_component`
- `transparent_provenance_component`
- `transparent_topology_component`

And it combines them differently by family:
- `path_to_direct`: support-heavy but still includes opportunity, specificity, provenance, and topology
- `direct_to_path`: opportunity-heavy, reflecting the empirical fact that endpoint opportunity was what the preferential-attachment baseline was exploiting

## What Improved

The key result is on `direct_to_path`.

Main score before:
- recall@100: `0.0076`
- MRR: `0.000726`

Main score after redesign:
- recall@100: `0.0254`
- MRR: `0.001831`

Preferential attachment on the same sampled slice:
- recall@100: `0.0229`
- MRR: `0.001621`

So on this sampled diagnostic:
- the new transparent score overtakes preferential attachment on `direct_to_path`
- this is the main success of the redesign

## What Did Not Improve Enough

`path_to_direct` broad remains weak.

Coverage-aware broad sampled run:
- recall@100: `0.0370`
- MRR: `0.001063`
- preferential attachment still does at least as well or slightly better on the same slice:
  - recall@100: `0.0370`
  - MRR: `0.001451`

Interpretation:
- the family-aware score is not enough to rescue broad `path_to_direct`
- the limiting issue is not just weights; it is the composition of the candidate universe
- most of that universe is still `fully_open_frontier`, which is precisely the weakest and noisiest slice

## My Read

This diagnostic supports three conclusions.

1. The transparent model should stay family-aware.
- A single one-pool score is not the right object.
- `direct_to_path` and `path_to_direct` behave differently enough to justify different transparent scoring logic.

2. The `direct_to_path` redesign direction is correct.
- Opportunity around an existing direct claim is the right transparent object.
- Preferential attachment was telling us something real here, and the new score now captures more of it directly.

3. Broad `path_to_direct` needs more than weight tuning.
- The dominant problem is that the current universe is mostly `fully_open_frontier`.
- That suggests the family is too diffuse in its broad form.
- The right next move is to keep the broad family for continuity, but expose and evaluate subfamilies explicitly.

4. The anchored `path_to_direct` slice is promising but far too narrow to replace the broad default.
- In the sampled anchored run, `path_to_direct` shrinks to `254` candidates and only `1` in-universe future positive.
- That yields much better headline ranking numbers mechanically, but only because the task has become tiny.
- Future coverage falls to `0.018%`, so this is not a defensible replacement for the broad task.
- It is better understood as:
  - a robustness slice
  - a high-signal subfamily
  - or a later shortlist filter

5. A conservative `fully_open_frontier` gate helps, but it does not fully solve broad `path_to_direct`.
- The gate used here keeps a fully open candidate only if it has:
  - both contextual co-occurrence and motif support
  - or unusually strong indirect path support
- On the sampled run, this shrinks `path_to_direct` from `30,923` to `8,474` candidates.
- The fully-open mass falls from `30,008` to `7,559`.
- In-universe future positives fall from `27` to `13`, but positive rate rises from `0.000873` to `0.001534`.
- The main transparent score improves:
  - recall@100: `0.0370 -> 0.0769`
  - MRR: `0.001063 -> 0.002027`
- Preferential attachment still remains stronger on MRR in this sampled slice, so the gate is useful progress rather than a final solution.

## Recommended Next Steps

1. Keep the family-aware transparent score for `direct_to_path`.

2. Keep broad `path_to_direct` as the default continuity family.
- do not replace it with the anchored slice

3. Make the subfamily split explicit in all diagnostics and later paper-facing tables.
- candidate rows should expose:
  - `candidate_family`
  - `candidate_subfamily`
  - `candidate_scope_bucket`

4. Next implementation step for broad `path_to_direct`:
- test stronger candidate-side restrictions for the `fully_open_frontier` mass
- keep `contextual_to_ordered` and `ordered_to_causal` visible as distinct progression slices
- treat anchored progression as a robustness track, not the main benchmark

5. The next likely improvement is not another blunt gate.
- We should now consider scoring or reranking broad `path_to_direct` with the subfamily visible.
- In practice that means:
  - keep `fully_open_frontier`, `contextual_to_ordered`, and `ordered_to_causal` in one continuity family
  - but allow the model and diagnostics to weight them differently
- That is a cleaner next step than continuing to carve the broad family down by hand.

6. Migrate the search/tuning scripts onto the new component space.
- `model_search.py`
- `targeted_model_search.py`
- `constrained_reranker_search.py`
currently still contain older coefficient-based scoring logic and should be updated once we freeze the transparent component set

7. Run a broader sampled grid next.
- more cutoffs
- more horizons
- same sampled design-diagnostic framing

That should be the next evidence step before any full-scale rerun.
