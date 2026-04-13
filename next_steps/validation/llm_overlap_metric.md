# LLM-Assisted Graph Overlap Metric

Date: 2026-04-01

## Motivation

Exact string matching is too harsh for FrontierGraph-style validation.

What we need is a metric that can recognize when:
- two nodes refer to the same concept with different wording
- one graph is broader or more compressed than the other
- a paper-summary graph overlaps semantically with a variable graph
- a gold graph is not really recoverable from title + abstract alone

An LLM can help with this if we use it as a structured semantic judge rather than a free-form reviewer.

## Short answer

Yes, this is operationally possible.

A small cheap model is enough if the task is framed as:
- node mapping
- edge mapping
- comparability labeling
- confidence scoring

The model should not be asked "who is right?"
It should be asked:
- what matches what
- what is broader/narrower
- what is not comparable at the abstract level

## Recommended setup

For each paper, provide:

1. paper title
2. paper abstract
3. gold graph:
   - node list
   - edge list
4. predicted graph:
   - node list
   - edge list

Then ask the model for structured output in three stages.

## Stage 1: node mapping

For each predicted node, judge whether it maps to a gold node as:
- `exact_match`
- `near_synonym`
- `broader_than_gold`
- `narrower_than_gold`
- `partial_overlap`
- `context_only`
- `no_match`
- `not_recoverable_from_abstract`

Also ask the reverse:
- for each gold node, is there a predicted node that covers it?

This matters because coverage is not symmetric.

## Stage 2: edge mapping

After node mapping, map predicted edges to gold edges using the judged node correspondences.

Edge labels should be:
- `exact_edge_match`
- `same_direction_broader_nodes`
- `same_direction_partial_nodes`
- `reversed_direction`
- `same_relation_different_graph_resolution`
- `context_or_method_edge`
- `no_match`
- `not_recoverable_from_abstract`

This lets us separate:
- semantic agreement
- resolution mismatch
- direction mistakes

## Stage 3: whole-graph comparability

Ask the model to classify the row as:
- `fair_abstract_level_comparison`
- `partly_fair_but_resolution_mismatch`
- `mostly_unfair_for_abstract_extraction`

This is especially important for papers like:
- ReCITE `90`
- symbolic DAGverse rows

## Suggested scoring

The LLM should produce labels, not the final score.
We convert labels into scores afterwards.

### Node-level weights

- `exact_match` = `1.00`
- `near_synonym` = `0.90`
- `broader_than_gold` = `0.70`
- `narrower_than_gold` = `0.70`
- `partial_overlap` = `0.50`
- `context_only` = `0.15`
- `no_match` = `0.00`
- `not_recoverable_from_abstract` = excluded from denominator in one adjusted metric

### Edge-level weights

- `exact_edge_match` = `1.00`
- `same_direction_broader_nodes` = `0.75`
- `same_direction_partial_nodes` = `0.60`
- `same_relation_different_graph_resolution` = `0.40`
- `reversed_direction` = `0.10`
- `context_or_method_edge` = `0.10`
- `no_match` = `0.00`
- `not_recoverable_from_abstract` = excluded from denominator in one adjusted metric

## Metrics to report

We should report both strict and adjusted metrics.

### Strict

- exact node precision / recall
- exact edge precision / recall

### LLM-assisted semantic

- semantic node precision / recall
- semantic edge precision / recall
- adjusted semantic node recall excluding abstract-unfair gold nodes
- adjusted semantic edge recall excluding abstract-unfair gold edges
- graph comparability share

## Why this is useful

This gives us a validation story that is much closer to the real issue:

- did we extract the same semantic object?
- did we extract a compressed but still meaningful version?
- is the benchmark target unfair for abstract-level extraction?

## Operational workflow

### Phase 1: calibrate on a tiny set

Start with:
- ReCITE `203`, `258`, `90`
- DAGverse `arxiv_2208_04144_0`, `arxiv_2205_01057_0`, `arxiv_2303_04339_0`

For each:
- run the LLM judge
- compare against our current manual judgments
- adjust labels or weights if needed

### Phase 2: batch on pilot rows

Run on:
- the 10-paper ReCITE pilot
- the 5-paper broad DAGverse pilot
- the 5-paper curated DAGverse pilot

### Phase 3: decide what is scalable

If the judge is stable enough, scale to:
- all `292` ReCITE rows
- a wider curated DAGverse slice

## Why a cheap model may be enough

This is not a creativity task.
It is a local semantic-comparison task on small graphs.

A cheap small model should be able to:
- compare two node labels
- use the abstract for context
- tell broader vs narrower vs partial overlap
- flag unrecoverable gold targets

The main protection we need is not a huge model.
It is:
- structured output
- calibration on a hand-reviewed set
- occasional spot checks

## Important guardrails

1. Do not let the LLM invent hidden nodes from the paper.
2. Do not ask for a single scalar judgment only.
3. Always require explicit mapping evidence.
4. Preserve a human-reviewed calibration set.
5. Report exact metrics and semantic metrics separately.

## Bottom line

Yes, LLM-assisted overlap scoring is feasible, and it is probably the right next validation layer.

The best way to use it is not as a black-box "grader," but as a structured mapper that helps us measure:
- semantic overlap
- abstraction mismatch
- benchmark fairness
