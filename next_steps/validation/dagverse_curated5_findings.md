# DAGverse Curated 5: Findings

Date: 2026-04-01

## Goal

Test whether a hand-curated, more natural-language slice of DAGverse is a fairer external benchmark for FrontierGraph than the broad ArXiv abstract-level slice.

## Files

- Curated benchmark input:
  - `next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_curated5.jsonl`
- Curated benchmark manifest:
  - `next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_curated5_manifest.json`
- FrontierGraph run:
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_curated5_gpt5mini_low_v1/parsed_results.jsonl`
- Curated review outputs:
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_curated5_gpt5mini_low_v1/dagverse_review_explicit/aggregate.json`
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_curated5_gpt5mini_low_v1/dagverse_review_explicit/summary.csv`
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_curated5_gpt5mini_low_v1/dagverse_review_explicit/manual_review.jsonl`

## Result relative to the broad DAGverse pilot

Broad DAGverse pilot (`5` papers):
- mean node precision (alias): `0.000`
- mean node recall (alias): `0.000`
- mean directed edge recall (alias): `0.000`
- mean relaxed edge recall (alias): `0.000`

Curated DAGverse pilot (`5` papers):
- mean node precision (alias): `0.053`
- mean node recall (alias): `0.089`
- mean directed edge recall (alias): `0.046`
- mean relaxed edge recall (alias): `0.046`

So the curated slice is still hard, but it is clearly fairer than the broad slice.

## Best case in the curated set

The strongest row is:
- `arxiv_2208_04144_0`
- *An Urban Population Health Observatory for Disease Causal Pathway Analysis and Decision Support*

For that paper:
- gold nodes: `9`
- predicted nodes: `15`
- alias-matched gold nodes: `4`
- node recall: `0.444`
- node precision: `0.267`
- gold edges: `13`
- predicted edges: `11`
- alias-matched directed edges: `3`
- directed edge recall: `0.231`

This is the first DAGverse row where the benchmark starts to look genuinely comparable to FrontierGraph's abstract-level semantic graph object.

## Interpretation

The broad DAGverse pilot mostly failed because many gold graphs were symbolic, formal, or instantiation-level. FrontierGraph instead extracts semantic abstract-level concepts from titles and abstracts.

The curated slice reduces that mismatch, but does not eliminate it.

There are still three recurring mismatch types:

1. **Variable-level vs semantic-level**
- Gold graph uses compact variables or named observables.
- FrontierGraph uses paper-summary concepts.

2. **Outcome-system framing vs mechanistic variable framing**
- FrontierGraph often extracts the higher-level problem setting or method object.
- Gold DAG may stay closer to the core causal variables only.

3. **Abstract insufficiency**
- Some DAG nodes or relations are recoverable from the full paper or figure, but not really from the abstract alone.

## What this means for validation

This result supports the following position:

- ReCITE is a hard stress test for ontology mismatch and graph-object mismatch.
- Broad DAGverse is a hard stress test for symbolic or formal DAG mismatch.
- Curated DAGverse is a better external benchmark for our current semantic abstract-level extraction.

It is not yet a strong benchmark in the sense of producing high exact or alias metrics, but it is much more diagnostically useful.

## Recommended next step

Move to the second branch:

1. design a variable-level extraction prompt tailored to symbolic or compact DAG benchmarks
2. rerun it on:
   - the broad DAGverse pilot
   - the curated DAGverse pilot
3. compare semantic-prompt vs variable-prompt behavior

That will tell us whether the remaining mismatch is mainly:
- prompt/object mismatch, or
- unavoidable text-to-graph information loss from title + abstract alone
