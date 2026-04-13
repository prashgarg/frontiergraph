# ReCITE 100-paper node-alignment comparison: `variable_v1` vs `variable_v2`

Date: 2026-04-03

## Goal

This run scales the earlier `20`-paper node-alignment comparison to a much larger and more stable ReCITE slice.

The sample is a balanced `100`-paper subset drawn from the full ReCITE variable-prompt judge summary:
- `15` fair abstract-level comparisons
- `75` partly fair but resolution-mismatched rows
- `10` mostly unfair rows

Files:
- sample manifest: `next_steps/validation/data/reCITE/frontiergraph_alignment_pilot100_manifest.json`
- v1 alignment input: `next_steps/validation/judge_inputs/recite_alignment_pilot100_variable_v1_node_alignment.jsonl`
- v2 alignment input: `next_steps/validation/judge_inputs/recite_alignment_pilot100_variable_v2_node_alignment.jsonl`
- deduped judged results: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/parsed_results_complete.jsonl`
- aggregate summary: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/node_alignment_summary_complete/aggregate.json`
- row summary: `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/node_alignment_summary_complete/summary.csv`

Models:
- extraction: `gpt-5-mini`, `low`
- node-alignment judge: `gpt-5-nano`, `low`

## Main result

The larger `100`-paper comparison does **not** replicate the `20`-paper pilot win for `variable_v2`.

Instead, the older `variable_v1` prompt is slightly better on average.

### `variable_v1`
- mean node precision: `0.679`
- mean node recall: `0.642`
- mean adjusted node recall: `0.797`
- mean node F1: `0.634`
- mean gold coverage at `>= 0.50`: `0.788`
- mean gold coverage at `>= 0.70`: `0.552`
- mean predicted coverage at `>= 0.50`: `0.862`
- mean predicted coverage at `>= 0.70`: `0.563`

### `variable_v2`
- mean node precision: `0.663`
- mean node recall: `0.632`
- mean adjusted node recall: `0.784`
- mean node F1: `0.611`
- mean gold coverage at `>= 0.50`: `0.766`
- mean gold coverage at `>= 0.70`: `0.544`
- mean predicted coverage at `>= 0.50`: `0.829`
- mean predicted coverage at `>= 0.70`: `0.557`

### Difference (`v2 - v1`)
- node precision: `-0.016`
- node recall: `-0.010`
- adjusted node recall: `-0.013`
- node F1: `-0.023`

So the simple conclusion is:

- the softer `variable_v2` prompt helped on the small development slice
- but on the larger `100`-paper comparison, that gain does not hold
- for now, `variable_v1` remains the better benchmark-facing variable prompt overall

## Why this matters

This is exactly why the `100`-paper scale-up was worth doing.

The `20`-paper pilot was real, but it was not stable enough to support a prompt switch on its own.
On the larger sample, `variable_v2` helps some papers a lot, but hurts enough others that it loses on average.

That means:
- the smaller pilot was useful for debugging the metric
- but not sufficient for choosing the better extraction prompt

## Where `variable_v2` helps most

Large positive changes in node F1 include:

- `14`: `0.000 -> 0.772`
- `289`: `0.000 -> 0.675`
- `259`: `0.249 -> 0.814`
- `261`: `0.318 -> 0.859`
- `8`: `0.197 -> 0.677`
- `239`: `0.226 -> 0.652`
- `266`: `0.000 -> 0.373`
- `142`: `0.264 -> 0.602`
- `225`: `0.478 -> 0.781`
- `41`: `0.578 -> 0.875`
- `271`: `0.461 -> 0.756`
- `45`: `0.358 -> 0.631`

These cases are consistent with the original intuition behind `variable_v2`:
- some papers are written in a broader or more policy-facing way
- a less rigid prompt can recover a graph closer to the benchmark object

## Where `variable_v2` hurts most

Large negative changes in node F1 include:

- `245`: `0.726 -> 0.435`
- `270`: `0.807 -> 0.499`
- `149`: `0.732 -> 0.416`
- `163`: `0.328 -> 0.000`
- `279`: `0.742 -> 0.405`
- `37`: `0.655 -> 0.229`
- `86`: `0.526 -> 0.000`
- `98`: `0.847 -> 0.221`
- `81`: `0.755 -> 0.059`
- `33`: `0.714 -> 0.000`
- `131`: `0.809 -> 0.000`
- `184`: `0.809 -> 0.000`

This is the more important pattern.

In a substantial minority of papers, `variable_v2` seems to preserve too much broader framing or fail to hold on to the compact factor-like labels that align well to benchmark nodes.

So the prompt is not simply "better but softer." It is trading off:
- flexibility and tolerance for abstract-level writing
- against the ability to stay tightly benchmark-facing on compact variable graphs

## Interpretation

The right interpretation is now:

1. `variable_v1` is still the better default for benchmark-facing variable extraction.
2. `variable_v2` is a useful alternative prompt family, but not a replacement.
3. The node-alignment metric itself was still worth building, because it made this comparison much more interpretable than exact label overlap alone.

So the metric survives this test better than the prompt revision does.

## Operational notes

This scaled run also surfaced an engineering lesson:

- the extraction and judge runners were vulnerable to silent early exits in this environment
- patching the extraction runner to log all exceptions fixed the chunked extraction side
- the node-alignment judge needed a resumable wrapper because repeated partial runs appended duplicates before reaching all unique pairs

Relevant files:
- patched extraction runner: `scripts/run_frontiergraph_extraction_pilot.py`
- resume wrapper: `next_steps/validation/run_node_alignment_until_complete.py`

Judge cleanup details:
- `parsed_results.jsonl` contains repeated rows from resumptions
- `parsed_results_complete.jsonl` is the deduped file and should be treated as canonical
- `errors.jsonl` contains a few transient timeouts / parse failures, but all affected pairs were eventually recovered in `parsed_results_complete.jsonl`

## Spend

This scaled step remained cheap:

- `variable_v2` extraction on the `100`-paper slice: about `$0.6811`
- `200`-row node-alignment judge: about `$0.4289`
- total for this scaled step: about `$1.1100`

This stays comfortably under the current no-ask ceiling.

## Recommendation

For now:

1. keep `variable_v1` as the default benchmark-facing variable prompt
2. keep `variable_v2` as an alternative prompt family for selected cases, not as the new default
3. keep the node-alignment metric as the main semantic validation layer

If we continue, the next useful question is not "is v2 better overall?" We now know the answer is no.

The better next question is:

- **what kinds of papers are improved by `variable_v2`, and can we predict those cases in advance?**

That would be a stronger next refinement than swapping the default prompt globally.
