# ReCITE Edge Alignment on 100 Rows

Date: 2026-04-03

## What was run

We ran an LLM-based edge-alignment judge on the existing `100`-paper ReCITE slice, using:

- extraction prompt family: `variable_v1`
- source extraction run:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/parsed_results.jsonl`
- node-alignment context:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_v1_node_alignment_complete_gpt5nano_low_v1/parsed_results_complete.jsonl`
- edge-alignment judge model:
  - `gpt-5-nano`, `low`
- canonical completed edge-alignment outputs:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_edge_alignment_gpt5nano_low_v1/parsed_results_complete.jsonl`

The main pass completed `99/100` rows cleanly, with one timeout on benchmark `80`. That row was rerun separately with a longer timeout and merged into the canonical complete file.

## Aggregate result

From:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_edge_alignment_gpt5nano_low_v1/edge_alignment_summary_complete/aggregate.json`

The key metrics are:

- mean edge precision: `0.419`
- mean edge recall: `0.432`
- mean adjusted edge recall: `0.525`
- mean edge F1: `0.378`

Coverage-style summaries:

- mean gold-edge coverage at `>= 0.60`: `0.469`
- mean gold-edge coverage at `>= 0.75`: `0.354`
- mean predicted-edge coverage at `>= 0.60`: `0.449`
- mean predicted-edge coverage at `>= 0.75`: `0.306`

## Interpretation

This is a useful result.

The node-alignment layer already showed that ontology and graph-object mismatch were the main bottlenecks. The edge-alignment result shows that, once we allow semantically reasonable node matching, FrontierGraph is recovering a meaningful amount of directed structure from title + abstract alone.

The most important comparison is:

- raw edge recall: `0.432`
- adjusted edge recall: `0.525`

That gap is informative. It means a nontrivial share of the apparent edge misses are concentrated in gold edges that the judge regards as not really recoverable from title + abstract alone.

So the edge result tells the same overall story as the node result:

- exact benchmark overlap is too harsh
- the fairer semantic metric is materially stronger
- the benchmark is useful, but only after we account for recoverability and graph-resolution mismatch

## Class-count breakdown

Gold-edge side:

- `exact_edge_match`: `551`
- `same_direction_broader_nodes`: `214`
- `same_direction_partial_nodes`: `278`
- `same_relation_different_graph_resolution`: `141`
- `not_recoverable_from_abstract`: `254`
- `no_match`: `824`
- `context_or_method_edge`: `26`
- `reversed_direction`: `3`

Predicted-edge side:

- `exact_edge_match`: `194`
- `same_direction_broader_nodes`: `108`
- `same_direction_partial_nodes`: `125`
- `same_relation_different_graph_resolution`: `116`
- `not_recoverable_from_abstract`: `202`
- `no_match`: `103`
- `context_or_method_edge`: `30`
- `reversed_direction`: `5`

The main takeaways are:

1. Exact edge agreement is far from zero once we use node alignment.
2. There is still a large `no_match` mass on the gold side, so this is not a trivial benchmark.
3. The `not_recoverable_from_abstract` bucket is large enough that it should be reported explicitly in any paper-facing validation table.

## Best and worst rows

From:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_edge_alignment_gpt5nano_low_v1/edge_alignment_summary_complete/summary.csv`

Best rows by edge F1:

- `149`: precision `1.000`, recall `1.000`, F1 `1.000`
- `189`: precision `0.787`, recall `0.879`, F1 `0.831`
- `286`: precision `0.963`, recall `0.714`, F1 `0.820`
- `52`: precision `0.600`, recall `1.000`, F1 `0.750`
- `80`: precision `0.825`, recall `0.658`, F1 `0.732`

Worst rows by edge F1:

- `206`: precision `0.230`, recall `0.000`, F1 `0.000`
- `230`: precision `0.000`, recall `0.000`, F1 `0.000`
- `237`: precision `0.000`, recall `0.000`, F1 `0.000`
- `259`: precision `0.000`, recall `0.000`, F1 `0.000`
- `275`: precision `0.000`, recall `0.000`, F1 `0.000`

So the edge layer is discriminating meaningfully across rows; it is not just compressing everything into one middling score.

## Cost

Summing actual response usage across the `100` completed edge-judge responses gives:

- input tokens: `1,431,329`
- output tokens: `327,875`
- estimated cost: about `$0.203`

Projected linear cost for all `292` ReCITE rows:

- about `$0.592`

This is comfortably cheap relative to current budget.

## Recommendation

Yes, scaling edge alignment from `100` to all `292` ReCITE rows is worth doing.

Why:

1. The `100`-row run already shows real signal, so this is not a dead end.
2. The full-scale cost is very low.
3. A full-`292` edge result would let us report:
   - node alignment on all `292`
   - edge alignment on all `292`
   - full-sample and recoverability-adjusted metrics

That would make the external-validation appendix substantially stronger and more complete.

## Bottom line

The `100`-row edge-alignment run is strong enough to justify full scaling.

If we continue, the natural next step is:

1. run edge alignment on all `292` ReCITE rows
2. summarize full-sample and adjusted edge metrics
3. then turn the node + edge results into paper-facing validation text
