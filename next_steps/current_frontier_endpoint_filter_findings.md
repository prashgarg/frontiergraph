# Current Frontier Endpoint Filter: Updated Findings

## What changed

We added a **two-layer deterministic surfaced-endpoint filter** to the current-frontier application step.

The filter does **not** change:
- the frozen ontology
- the historical reranker backtests
- the tuned model choice

It only changes the **surfaced current ranking** by demoting candidate pairs whose endpoints look like:
- `method_like`
- `metadata_like`
- `generic_like`
- `unresolved_code` when the displayed endpoint label is still an opaque concept code

The first heuristics were:
- method terms such as `regression`, `quantile`, `moments`, `estimator`, `test statistic`, `asymptotic`
- metadata/container terms such as `place of residence`, `region of residence`, `usual care`, `observed data`, `parameter values`

The second heuristics were:
- unresolved displayed labels matching `FG3C...`
- broad container labels such as:
  - `policy`
  - `distance`
  - `economic growth`
  - `innovation`
  - `employment`
  - `wages`
  - `health`
  - `income`
  - `consumption`
  - `productivity`
  - `investment`

## Why we did this

The first current-frontier reranked outputs were historically promising but substantively poor at the top.

In particular, the top reranked lists were heavily pulled toward:
- `Method of Moments Quantile Regression (MMQR)`
- `place of residence`

That made the live frontier look much less credible than the backtest gains suggested.

After the first filter, the obvious method artifacts disappeared, but the top surfaced set still leaned heavily on:
- opaque endpoint codes such as `FG3C001572`
- broad container labels such as `policy` and `distance`

## What improved

### 1. The surfaced shortlist became much more readable

After the two-layer filter:
- `flagged share in surfaced top 100 = 0.000` for `h=5`
- `flagged share in surfaced top 100 = 0.000` for `h=10`

So the surfaced top 100 is no longer being driven by:
- method-like artifacts
- metadata-like artifacts
- opaque endpoint-code labels
- the small broad-label set we explicitly demoted

### 2. The top surfaced rows now look like real research questions

Representative surfaced path/mechanism questions now include:
- `Through which nearby pathways might income tax rate shape CO2 emissions?`
- `Through which nearby pathways might financial development shape green innovation?`
- `Through which nearby pathways might technological innovation shape green innovation?`
- `Which nearby mechanisms most plausibly link environmental pollution to carbon emissions?`
- `Which nearby mechanisms most plausibly link environmental regulation to sustainable development?`

This is a materially better frontier object than the earlier direct-edge-like surfaced list.

### 3. The path/mechanism layer now reads better on top of the filtered shortlist

With the updated surfaced ranking, the rendered top 100 shifts slightly toward mechanism questions:
- `h=5`: `54` mediator questions, `46` path questions
- `h=10`: `53` mediator questions, `47` path questions

That is acceptable for now. The important point is not the exact split; it is that the output no longer looks dominated by obviously poor surfaced endpoints.

## What still needs work

The two-layer filter fixed the main surfaced-endpoint problem, but it did **not** solve everything.

Three remaining issues:

### 1. Some mediator labels are still unresolved codes
Examples from the rendered why-lines:
- `FG3C003915`
- `FG3C004347`
- `FG3C003760`
- `FG3C005211`

So the endpoint filter solved the surfaced-endpoint problem more than the mediator-label problem.

### 2. Some surfaced pairs are still semantically awkward or redundant
Examples:
- `CO2 emissions -> carbon emissions`
- `carbon emissions (CO2 emissions) -> environmental quality (CO2 emissions)`
- repeated `state of the business cycle -> willingness to pay`

These are readable, but not always the strongest paper-facing frontier object.

### 3. The current shortlist may still need a light semantic-deduplication layer
This now looks more like:
- a semantic redundancy problem
- a repeated-family concentration problem

not like the earlier method-artifact problem.

## Practical interpretation

The endpoint filter changes the current read of the project:

- the learned reranker is still useful and should stay
- the raw current reranked frontier should **not** be trusted directly
- a deterministic surfaced-endpoint layer is necessary and now clearly worth keeping
- the project is moving toward:
  - historical reranker for discovery
  - surfaced current shortlist after endpoint-quality filtering
  - path/mechanism question rendering on top of that shortlist

## Next steps

1. Review the filtered path/mechanism shortlist manually and tag:
   - clearly good
   - readable but redundant
   - readable but weak
2. Add a light semantic-deduplication or repeated-family penalty if needed.
3. Use the improved shortlist to sharpen the paper’s examples and object language.
4. Keep the richer ontology redesign deferred until we know whether the remaining weaknesses are mostly redundancy or ontology.
