# External Validation: Immediate Next Action

Date: 2026-04-03

## Current state

We have now completed:

1. a `10`-paper ReCITE pilot
2. a broad `5`-paper DAGverse pilot
3. a curated `5`-paper DAGverse pilot
4. a full `292`-paper ReCITE variable-prompt extraction run
5. a full `292`-paper ReCITE semantic-overlap judge run
6. a full `292`-paper ReCITE semantic-prompt matched comparison
7. a `20`-paper ReCITE node-alignment pilot comparing `variable_v1` vs `variable_v2`
8. a `100`-paper ReCITE node-alignment scale-up comparing `variable_v1` vs `variable_v2`
9. a prompt-selection analysis and fallback recommendation derived from the `100`-paper scale-up
10. a strict full-292 fallback operationalization on the `25` routed ReCITE papers
11. a `100`-paper ReCITE edge-alignment run using the full-292 `variable_v1` node alignments as context
12. a full `292`-paper ReCITE edge-alignment run for `variable_v1`, including retry cleanup on the timeout rows

Key lesson so far:
- the main problem is not that FrontierGraph extracts nonsense
- the main problem is mismatch between our semantic abstract-level graph object and the external benchmark graph object

The curated DAGverse slice is the fairest benchmark tried so far.
At full ReCITE scale, the judge confirms the same pattern:
- only `43/292` rows look like clean abstract-level comparisons
- `220/292` are partly fair but resolution-mismatched
- `29/292` are mostly unfair for abstract-only extraction

Matched semantic-vs-variable result:
- the variable prompt is better than the semantic prompt on the full ReCITE benchmark
- but the gain is modest at the semantic-judge level
- that means prompt engineering helps, but benchmark comparability remains the central issue

Node-alignment result, updated after scale-up:
- on the `20`-paper development slice, `variable_v2` beat `variable_v1`
- on the larger `100`-paper comparison, that gain does **not** hold
- `variable_v1` ends up slightly better overall:
  - node F1: `0.634` vs `0.611`
  - node precision: `0.679` vs `0.663`
  - adjusted node recall: `0.797` vs `0.784`
- conclusion: `variable_v2` is useful as an alternative prompt family, but not strong enough to replace `variable_v1` as the default benchmark-facing variable prompt

Prompt-selection result:
- the best current policy is **not** to swap prompts globally
- instead:
  - keep `variable_v1` as the default
  - use `variable_v2` only as a targeted fallback when the first-pass `variable_v1` graph is sparse
- the best strict fallback rule from the `100`-paper analysis is:
  - `v1_predicted_nodes <= 6`
  - `abstract_words <= 210`
  - no strong sustainability markers (`sustainab*`, `circular economy`)
- on the `100`-paper comparison, that subset had:
  - `11` papers
  - mean `delta_f1 = +0.216`
  - `72.7%` improved under `variable_v2`

Strict full-292 fallback result:
- applying the strict routing rule to the full `292` ReCITE rows selected `25` papers
- on that routed subset, the matched node-alignment comparison is:
  - `variable_v1` mean node F1: `0.586`
  - `variable_v2` mean node F1: `0.631`
  - mean `delta_f1 = +0.045` for `v2 - v1`
  - `v2` better on `14/25`
  - `v1` better on `11/25`
- conclusion:
  - the fallback policy does work on the subset it selects
  - but the subset is small, so the pooled full-dataset gain from this strict rerouting policy is modest
  - the fallback should be treated as a targeted rescue path, not as a global replacement strategy

Full `292` node-alignment denominator for `variable_v1` is now complete:
- mean node precision: `0.678`
- mean node recall: `0.650`
- mean adjusted node recall: `0.813`
- mean node F1: `0.631`

Exact hybrid pooled result (`v1` on `267`, `v2` on routed `25`):
- mean node precision: `0.682`
- mean node recall: `0.663`
- mean adjusted node recall: `0.814`
- mean node F1: `0.642`

So the exact pooled gain from the strict fallback policy is:
- `+0.011` in mean node F1

Edge-alignment result on the `100`-paper ReCITE slice:
- mean edge precision: `0.419`
- mean edge recall: `0.432`
- mean adjusted edge recall: `0.525`
- mean edge F1: `0.378`
- actual judge cost for the `100` rows: about `$0.203`
- projected full-`292` cost: about `$0.592`

Conclusion from the edge-alignment pilot:
- the edge layer shows real signal once node matching is handled semantically
- the recoverability-adjusted edge metric is materially stronger than the raw one
- full-scale edge alignment on all `292` ReCITE rows is worth doing

Full `292` edge-alignment result:
- mean edge precision: `0.446`
- mean edge recall: `0.448`
- mean adjusted edge recall: `0.551`
- mean edge F1: `0.393`
- exact edge signal survives and slightly strengthens at full scale
- estimated full edge-judge cost: about `$0.590`

Conclusion from the full edge-alignment run:
- the exercise was useful diagnostically
- but the pooled benchmark metrics remain difficult to interpret cleanly because benchmark-object mismatch is still central
- this material should therefore be treated as exploratory internal validation work unless we use it only in a restrained, qualitative way
- the best remaining work is now synthesis, targeted qualitative examples, and a paper-facing validation strategy centered on our own object rather than pooled external benchmark scores

## What is ready now

### ReCITE

Ready to run immediately with the current FrontierGraph extraction prompt.

Files:
- `next_steps/validation/data/reCITE/test.parquet`
- `next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark.jsonl`
- `next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark_manifest.json`

Why this is the best first benchmark:
- real scientific text is included directly
- every row has a title and abstract
- gold nodes and edges are already present
- our prompt is already written for title + abstract

Scale:
- 292 papers
- mean gold nodes: `24.99`
- mean gold edges: `37.37`
- rough total input tokens for title + abstract benchmark: `117,435`

Interpretation:
- these are denser and more ontology-heavy than DAGverse
- that makes ReCITE a strong validation test for both extraction and concept matching

## What is partially ready

### DAGverse

Downloaded and understood, but not yet fully materialized into prompt-ready JSONL because text retrieval needs to happen from the source pages.

Files:
- `next_steps/validation/data/dagverse/train.parquet`
- `next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_manifest.json`

Most relevant subset:
- `source = arxiv`
- `abstract = true`
- 25 rows

Why this subset:
- it is the cleanest match to a title + abstract extraction prompt
- graphs are small and high-quality
- they are grounded in author-provided DAG figures

Scale:
- 108 total rows in the example release
- mean nodes: `5.45`
- mean edges: `6.22`
- 25 ArXiv rows in the abstract-level slice

Current blocker:
- shell-level `curl` fetches work
- Python-internal URL retrieval is sandbox-fragile here
- so the ArXiv abstract pull should be done as a shell-assisted step rather than as pure Python network IO

## What is newly ready

### Node-alignment validation layer

Ready now:
- `next_steps/validation/prompt_pack/system_prompt_variable_validation_v2.md`
- `next_steps/validation/node_alignment_metric_v1.md`
- `next_steps/validation/prompt_pack/system_prompt_node_alignment.md`
- `next_steps/validation/prompt_pack/user_prompt_node_alignment_template.md`
- `next_steps/validation/prompt_pack/node_alignment_schema.json`

Why this matters:
- it allows broader, narrower, and partial node matches
- it separates abstract recoverability from extraction quality
- it gives us a more defensible semantic metric than strict exact overlap alone

Most recent result file:
- `next_steps/validation/recite_alignment_pilot20_v2_results.md`
- `next_steps/validation/recite_alignment_pilot100_scaled_results.md`
- `next_steps/validation/recite_prompt_selection_recommendation.md`
- `next_steps/validation/recite_full292_strictfallback25_results.md`

## Why not start with all datasets

Because they do different jobs:
- `ReCITE` is the best extraction-validation benchmark
- `DAGverse` is the best small high-quality graph-recovery benchmark
- `CLadder` and `CLEAR` are mostly reasoning benchmarks, not paper-text extraction benchmarks

So the highest-value first pass is:
- ReCITE first
- DAGverse second
- everything else later

## Matching strategy once we run our prompt

Comparison should happen in layers:

1. exact node string match
2. normalized string match
3. embedding-based candidate match
4. agentic/manual review for ontology disagreements

Key review labels:
- `exact_match`
- `broader_than_gold`
- `narrower_than_gold`
- `partial_overlap`
- `missed_gold`
- `extra_node`

This matters because ontology disagreement is likely to be one of the main apparent "errors."

## Recommended immediate execution

If we keep moving now, the next concrete step should be:

1. decide whether broader routing is worth trying:
   - loose-fallback routing (`40` rows)
2. or move to a new validation object:
   - edge alignment with `variable_v1` kept as the default
3. or turn the current results into paper-facing validation text:
   - full-sample versus fairness-filtered subset reporting

Useful result file for the current state:
- `next_steps/validation/recite_full292_variable_scaled_results.md`
- `next_steps/validation/recite_full292_matched_prompt_comparison.md`
- `next_steps/validation/recite_alignment_pilot20_v2_results.md`
- `next_steps/validation/recite_alignment_pilot100_scaled_results.md`
- `next_steps/validation/recite_edge_alignment_pilot100_results.md`
- `next_steps/validation/recite_full292_edge_alignment_results.md`
- `next_steps/validation/recite_prompt_selection_recommendation.md`
- `next_steps/validation/recite_full292_strictfallback25_results.md`
- `next_steps/validation/external_benchmark_internal_note.md`
- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/prompt_selection_analysis.json`
- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_node_alignment_complete_gpt5nano_low_v1/node_alignment_summary/aggregate.json`

Operational note:
- the matched full ReCITE semantic baseline is now complete, including cleanup reruns
- the semantic step cost about `$2.5221`
- the `100`-paper scale-up added about `$1.1100`
- the strict full-292 fallback step added about `$0.225`
- the completed full-292 `variable_v1` node-alignment denominator added about `$0.603`
- cumulative validation-track spend remains comfortably below the `$10` no-ask ceiling
