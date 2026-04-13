# ReCITE Full-292 Edge Alignment Result

Date: 2026-04-03

## What was run

We ran the full `292`-row ReCITE edge-alignment judge for the `variable_v1` FrontierGraph extraction outputs.

Inputs:

- benchmark rows:
  - `next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark.jsonl`
- source extraction outputs:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/parsed_results.jsonl`
- node-alignment context:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_node_alignment_complete_gpt5nano_low_v1/parsed_results_complete.jsonl`
- built edge-alignment inputs:
  - `next_steps/validation/judge_inputs/recite_full292_variable_v1_edge_alignment.jsonl`

Judge runs:

- main run:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_edge_alignment_gpt5nano_low_v1`
- retry run for the `6` timeout rows:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_edge_alignment_missing6_gpt5nano_low_v1`

Canonical merged result:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_edge_alignment_gpt5nano_low_v1/parsed_results_complete.jsonl`

## Aggregate result

From:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_edge_alignment_gpt5nano_low_v1/edge_alignment_summary/aggregate.json`

The full pooled result is:

- mean edge precision: `0.446`
- mean edge recall: `0.448`
- mean adjusted edge recall: `0.551`
- mean edge F1: `0.393`

Coverage summaries:

- mean gold-edge coverage at `>= 0.60`: `0.496`
- mean gold-edge coverage at `>= 0.75`: `0.370`
- mean predicted-edge coverage at `>= 0.60`: `0.479`
- mean predicted-edge coverage at `>= 0.75`: `0.343`

## Interpretation

This strengthens the validation story.

Compared with the `100`-row edge pilot:

- `100`-row mean edge F1: `0.378`
- full `292`-row mean edge F1: `0.393`

- `100`-row adjusted edge recall: `0.525`
- full `292`-row adjusted edge recall: `0.551`

So the larger run did not wash out the signal. If anything, the pooled result became a bit stronger.

That matters because it means the edge-alignment layer is not just working on a favorable slice. It appears to be a stable property of the full ReCITE benchmark once node correspondence is handled semantically.

The main interpretive points are now:

1. Exact edge overlap remains too harsh as the only metric.
2. A semantic, node-aware edge metric gives a materially better and more credible picture.
3. Adjusting for abstract recoverability matters a lot.

The gap:

- raw edge recall `0.448`
- adjusted edge recall `0.551`

is still large enough that recoverability should be treated as a first-class reporting object in the paper.

## Class counts

Gold-edge side:

- `exact_edge_match`: `1444`
- `same_direction_broader_nodes`: `738`
- `same_direction_partial_nodes`: `845`
- `same_relation_different_graph_resolution`: `435`
- `not_recoverable_from_abstract`: `446`
- `no_match`: `2460`
- `context_or_method_edge`: `79`
- `reversed_direction`: `25`

Predicted-edge side:

- `exact_edge_match`: `726`
- `same_direction_broader_nodes`: `358`
- `same_direction_partial_nodes`: `400`
- `same_relation_different_graph_resolution`: `280`
- `not_recoverable_from_abstract`: `487`
- `no_match`: `448`
- `context_or_method_edge`: `71`
- `reversed_direction`: `6`

## Cost

Summing actual response usage across the `292` completed edge-judge responses gives:

- input tokens: `4,175,941`
- output tokens: `951,902`
- estimated cost: about `$0.590`

That is fully in line with the earlier projection from the `100`-row pilot.

## Bottom line

The full `292` ReCITE edge-alignment run was worth doing.

We now have, at full ReCITE scale:

1. exact-match extraction benchmarks
2. semantic node-alignment metrics
3. full edge-alignment metrics
4. recoverability-adjusted reporting
5. a defensible default-and-fallback prompt policy

This is enough to support a serious paper-facing external-validation section.
