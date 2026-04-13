# ReCITE full-292 strict fallback result

Date: 2026-04-03

## What we did

We operationalized the prompt-routing rule derived from the `100`-paper node-alignment scale-up on the full `292`-paper ReCITE benchmark.

Routing rule:
- keep `variable_v1` as the default
- rerun `variable_v2` only when:
  - `v1_predicted_nodes <= 6`
  - `abstract_words <= 210`
  - no strong sustainability markers (`sustainab*`, `circular economy`)

On the full `292` rows, this selected `25` fallback candidates.

Files:
- strict fallback candidate list:
  - `next_steps/validation/data/reCITE/frontiergraph_full292_v2_fallback_candidates_strict.jsonl`
- benchmark-materialized strict subset:
  - `next_steps/validation/data/reCITE/frontiergraph_full292_v2_fallback_candidates_strict_benchmark.jsonl`
- v2 extraction run:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v2_strictfallback25`
- v2 node-alignment judge run:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v2_strictfallback25_node_alignment_gpt5nano_low_v1`
- matched v1 node-alignment judge run on the same `25` rows:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_strictfallback25_node_alignment_gpt5nano_low_v1`

## Aggregate result on the routed subset

### `variable_v1` on the strict `25`

- mean node precision: `0.710`
- mean node recall: `0.544`
- mean adjusted node recall: `0.694`
- mean node F1: `0.586`

### `variable_v2` on the same strict `25`

- mean node precision: `0.700`
- mean node recall: `0.609`
- mean adjusted node recall: `0.754`
- mean node F1: `0.631`

### Direct subset comparison

- rows compared: `25`
- mean `delta_f1 = +0.045` for `v2 - v1`
- `v2` better on `14/25`
- `v1` better on `11/25`
- ties: `0`

So the routing rule does hold up on the full-292-selected subset:
- not perfectly
- but well enough to justify keeping `v2` as a targeted fallback rather than a global replacement

## Interpretation

This result sharpens the current recommendation:

1. do **not** replace `variable_v1` globally
2. do keep a **strict fallback rerun path**
3. judge fallback success at the subset level, not by assuming it will transform full-dataset averages

### Exact full-292 hybrid result

We also completed the full `292`-paper node-alignment denominator for `variable_v1`, then replaced the routed `25` rows with their `variable_v2` fallback results.

Full `variable_v1` node-alignment baseline:
- mean node precision: `0.678`
- mean node recall: `0.650`
- mean adjusted node recall: `0.813`
- mean node F1: `0.631`

Exact hybrid (`v1` on `267` rows, `v2` on routed `25` rows):
- mean node precision: `0.682`
- mean node recall: `0.663`
- mean adjusted node recall: `0.814`
- mean node F1: `0.642`

So the exact pooled gain from the strict fallback policy is:
- `+0.011` in mean node F1

Why the full-dataset average shift is still limited:
- only `25/292` rows are rerouted
- the subset improvement is real, but the routed subset is small
- the pooled gain is meaningful but still modest relative to the overall benchmark

So the value of the fallback is mostly:
- rescuing sparse first-pass cases
- improving paper-level outputs in a targeted way
- lifting pooled benchmark averages somewhat, but not dramatically

## What this means for next steps

The best next scale-up is now:

1. decide whether broader routing is worth it:
   - loose-fallback routing (`40` rows)
2. or move to a new validation object:
   - edge alignment
3. or turn this into paper-facing validation text:
   - full-sample versus fairness-filtered subset reporting

## Spend for this strict-fallback step

Approximate added spend for the strict-fallback step itself:
- `v2` extraction on `25` rows: about `$0.128`
- `v2` node-alignment judge on `25` rows: about `$0.050`
- matched `v1` node-alignment judge on `25` rows: about `$0.048`

Total added spend for this step:
- about `$0.225`

Approximate added spend for the full `292` `variable_v1` node-alignment denominator:
- about `$0.603`

Combined added spend for:
- the strict-fallback step, plus
- the completed full-292 `variable_v1` node-alignment denominator

is about:
- `$0.828`

This remains comfortably below the current `$10` no-ask ceiling.
