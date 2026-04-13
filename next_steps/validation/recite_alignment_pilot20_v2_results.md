# ReCITE 20-paper node-alignment pilot: `variable_v1` vs `variable_v2`

Date: 2026-04-03

## What this pilot does

This pilot tests two things together on the same `20`-paper ReCITE development slice:

1. a softer `variable_v2` extraction prompt that still prefers variable-like nodes, but no longer forces every abstract into a compact variable DAG
2. a node-alignment validation metric that allows broader/narrower/partial matches instead of relying only on exact label overlap

The judged comparison uses:
- extraction model: `gpt-5-mini`, `low`
- alignment judge: `gpt-5-nano`, `low`

Files:
- extraction prompt v2: `next_steps/validation/prompt_pack/system_prompt_variable_validation_v2.md`
- metric spec: `next_steps/validation/node_alignment_metric_v1.md`
- judged output: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot20_node_alignment_gpt5nano_low_v1/parsed_results_complete.jsonl`
- aggregate summary: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot20_node_alignment_gpt5nano_low_v1/node_alignment_summary_complete/aggregate.json`
- row summary: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot20_node_alignment_gpt5nano_low_v1/node_alignment_summary_complete/summary.csv`

Operational note:
- one batch row (`benchmark_id = 168`, `variable_v2`) timed out in the first judge run
- it was rerun successfully on its own with a longer timeout
- the final comparison uses the merged `parsed_results_complete.jsonl`

## Aggregate result

The softer `variable_v2` prompt improves the alignment-weighted node metrics on this `20`-paper slice.

### `variable_v1`
- mean node precision: `0.620`
- mean node recall: `0.636`
- mean adjusted node recall: `0.776`
- mean node F1: `0.597`
- mean gold coverage at `>= 0.50`: `0.739`
- mean gold coverage at `>= 0.70`: `0.575`
- mean predicted coverage at `>= 0.50`: `0.759`
- mean predicted coverage at `>= 0.70`: `0.530`

### `variable_v2`
- mean node precision: `0.741`
- mean node recall: `0.714`
- mean adjusted node recall: `0.841`
- mean node F1: `0.692`
- mean gold coverage at `>= 0.50`: `0.832`
- mean gold coverage at `>= 0.70`: `0.684`
- mean predicted coverage at `>= 0.50`: `0.885`
- mean predicted coverage at `>= 0.70`: `0.678`

### Change
- node precision: `+0.121`
- node recall: `+0.078`
- adjusted node recall: `+0.065`
- node F1: `+0.095`

This is a meaningful gain. It suggests that the earlier variable prompt was too rigid. The v2 prompt gives up less information when the abstract is written in a broader or more policy-facing way.

## Where v2 helps most

The largest node-F1 gains are:

- `168`: `0.000 -> 0.536`
- `8`: `0.000 -> 0.466`
- `263`: `0.537 -> 0.960`
- `190`: `0.407 -> 0.690`
- `271`: `0.645 -> 0.887`
- `148`: `0.657 -> 0.849`
- `22`: `0.519 -> 0.699`
- `31`: `0.600 -> 0.713`

These are mostly cases where `variable_v1` either:
- over-compressed the abstract into a benchmark-seeking variable DAG
- or drifted into abstract framing nodes that were too far from the gold concepts

The v2 wording seems to help by preserving compact factor labels and allowing some higher-level nodes when the abstract really is written that way.

## Where v2 gets worse

The biggest node-F1 declines are:

- `222`: `0.799 -> 0.443`
- `209`: `0.842 -> 0.580`
- `54`: `0.868 -> 0.745`
- `293`: `0.227 -> 0.161`
- `13`: `0.656 -> 0.615`

These declines matter. They show that v2 should not be treated as an unambiguous replacement in every setting.

The likely pattern is:
- when the abstract already supports a very compact benchmark-friendly variable graph, the softer prompt sometimes keeps too much broader framing
- that can reduce node-level alignment even if the output remains reasonable as a paper-summary graph

So the right interpretation is not "v2 is always better." It is:

- `variable_v2` is better as a general abstract-level extraction prompt for judged semantic alignment
- but some benchmark rows still favor the more aggressively compact `variable_v1` style

## What this means for validation

This pilot supports a more defensible validation story:

1. use strict exact overlap as the hard baseline
2. use weighted node alignment as the semantic validation layer
3. treat broader/narrower/partial matches as real but discounted overlap
4. keep abstract recoverability separate from extraction quality

That is much more reasonable than forcing every row into a same-label, same-cardinality comparison.

## What this means for prompts

The main lesson is not "prompt engineering solves validation." It is narrower:

- prompt design can move the extracted graph closer to a benchmark object
- but only if the benchmark object is at least somewhat comparable to the abstract-supported graph we can reasonably recover

So prompt work helps, but the validation layer is still doing most of the heavy lifting.

## Recommended next step

The best next move is:

1. keep `variable_v2` as the better benchmark-facing variable prompt for now
2. add the same node-alignment evaluation to a larger ReCITE slice, likely `50` or `100` rows
3. only after that, decide whether to:
   - scale node alignment across all `292` ReCITE rows
   - add edge-alignment scoring on top of the current node mapping
   - or keep this as a development metric and report it alongside the full-sample judge results
