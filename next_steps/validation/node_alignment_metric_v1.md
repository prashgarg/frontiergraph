# Node Alignment Metric V1

Date: 2026-04-03

## Purpose

This metric is designed for validation settings where:
- the gold graph and predicted graph may differ in size
- node labels may differ lexically
- one graph may be broader, narrower, or more compressed than the other
- some gold content may not really be recoverable from title + abstract alone

The goal is to score **semantic overlap under natural graph differences** without pretending that every mismatch is an extraction failure.

## Design principles

The metric should be:
- **consistent**: same labels and rules across papers
- **defensible**: interpretable enough to explain in a paper appendix
- **reasonable**: flexible about abstraction differences, but not so flexible that everything counts as a match

The metric therefore has:
- a simple, interpretable primary score
- separate diagnostic dimensions
- an adjusted version that excludes gold content not recoverable from abstract text

## Objects

For each paper:

- gold graph:
  - nodes `G = {g_1, ..., g_m}`
  - edges `E_G`
- predicted graph:
  - nodes `P = {p_1, ..., p_n}`
  - edges `E_P`
- text context:
  - title
  - abstract

## High-level workflow

1. Generate a small candidate set of plausible node alignments.
2. Ask a structured judge to classify those candidate alignments.
3. Build:
   - gold-to-predicted node alignment
   - predicted-to-gold node alignment
4. Score node overlap.
5. Use aligned nodes to score edge overlap.
6. Report:
   - full-sample score
   - fair-abstract-only score
   - comparability diagnostics

## Step 1: candidate node pairs

Do **not** compare every node to every other node blindly in production.
Instead build a candidate set for each node using cheap filters:

### Candidate generation

For each gold node `g`:
- keep any predicted node with:
  - exact normalized string match, or
  - strong lexical overlap, or
  - top-`k` embedding similarity

For each predicted node `p`:
- keep any gold node with the same rule

Recommended defaults:
- `k = 5`
- normalized exact match always included
- embedding cosine stored as a diagnostic, not as the primary score

## Step 2: pairwise semantic classification

For each candidate pair `(g, p)`, ask the judge for:

### A. overlap class

One of:
- `exact_match`
- `near_synonym`
- `broader_than_gold`
- `narrower_than_gold`
- `partial_overlap`
- `context_only`
- `no_match`

### B. abstraction relation

One of:
- `same_level`
- `gold_more_specific`
- `pred_more_specific`
- `different_graph_object`

### C. causal-role relation

One of:
- `same_role`
- `compatible_role`
- `different_role`
- `contextual_only`

Example:
- `clean energy` vs `development and diffusion of clean energy technologies`
  - overlap class: `broader_than_gold` or `partial_overlap`
  - abstraction relation: `pred_more_specific`
  - causal-role relation: `compatible_role`

### D. abstract recoverability

The judge should also say whether the **gold node itself** is:
- `yes`
- `partly`
- `no`

recoverable from title + abstract.

This matters because unrecoverable gold content should not count the same as a bad miss.

### E. confidence

Confidence can be stored for audit and manual triage, but it should **not** be the main score driver.

## Step 3: pairwise weight table

Use a simple fixed weight table for the primary metric:

### Node pair weights

- `exact_match` = `1.00`
- `near_synonym` = `0.90`
- `broader_than_gold` = `0.70`
- `narrower_than_gold` = `0.70`
- `partial_overlap` = `0.50`
- `context_only` = `0.15`
- `no_match` = `0.00`

Reasoning:
- exact and near-synonym should count strongly
- broader/narrower should count materially but not fully
- partial overlap should count, but clearly less
- context-only should not be treated as full semantic recovery

## Step 4: node alignment

### Gold-to-predicted alignment

For each gold node `g_i`, define:

`s_R(g_i) = max_j w(g_i, p_j)`

where `w(g_i, p_j)` is the pairwise weight.

Interpretation:
- this is the best semantic coverage of gold node `g_i` by the predicted graph

### Predicted-to-gold alignment

For each predicted node `p_j`, define:

`s_P(p_j) = max_i w(g_i, p_j)`

Interpretation:
- this is how well predicted node `p_j` maps back to the gold graph

### Why no strict one-to-one matching

Strict one-to-one alignment is too brittle here.
Many-to-one alignment should be allowed because:
- several narrower gold nodes may map to one broader predicted node
- one predicted node may summarize a small set of gold variables

If needed, a separate one-to-one sensitivity check can be reported later.

## Step 5: node metrics

### Weighted node recall

`NodeRecall = (1 / |G|) * Σ_i s_R(g_i)`

### Weighted node precision

`NodePrecision = (1 / |P|) * Σ_j s_P(p_j)`

### Weighted node F-score

Use the harmonic mean of weighted node precision and recall.

### Coverage thresholds

Also report coverage shares:
- share of gold nodes with best-match score `>= 0.50`
- share of gold nodes with best-match score `>= 0.70`
- share of predicted nodes with best-match score `>= 0.50`

These are easier to interpret than a single scalar alone.

## Step 6: adjusted node metrics

Let `G_yespartly` be the set of gold nodes whose recoverability label is:
- `yes`
- `partly`

Then define:

`AdjustedNodeRecall = (1 / |G_yespartly|) * Σ_{g_i in G_yespartly} s_R(g_i)`

This gives a fairer score for abstract-level extraction.

Report both:
- full node recall
- adjusted node recall

## Step 7: edge alignment

Edge scoring should be built on node alignment, but should not rely on node score alone.

### Candidate edge mapping

For each gold edge `e = (g_a -> g_b)`:
- take the top aligned predicted nodes for `g_a` and `g_b`
- gather predicted edges between or around those aligned nodes
- ask the judge for the best edge relation class

### Edge relation labels

Use:
- `exact_edge_match`
- `same_direction_broader_nodes`
- `same_direction_partial_nodes`
- `same_relation_different_graph_resolution`
- `reversed_direction`
- `context_or_method_edge`
- `no_match`
- `not_recoverable_from_abstract`

### Edge weights

- `exact_edge_match` = `1.00`
- `same_direction_broader_nodes` = `0.75`
- `same_direction_partial_nodes` = `0.60`
- `same_relation_different_graph_resolution` = `0.40`
- `reversed_direction` = `0.10`
- `context_or_method_edge` = `0.10`
- `no_match` = `0.00`

### Edge recall

`EdgeRecall = average weighted match over gold edges`

### Edge precision

`EdgePrecision = average weighted match over predicted edges`

### Adjusted edge recall

Exclude gold edges labeled `not_recoverable_from_abstract`.

## Step 8: whole-graph comparability

In parallel, classify each paper as:
- `fair_abstract_level_comparison`
- `partly_fair_but_resolution_mismatch`
- `mostly_unfair_for_abstract_extraction`

This is not the score itself.
It is the interpretation layer that tells us how much weight to put on the score.

## Step 9: embedding similarity

Embedding cosine similarity is useful, but should be treated as a **diagnostic**, not the primary metric.

Recommended use:
- as a candidate generator
- as a tie-breaker among multiple plausible matches
- as a reported secondary field for aligned pairs

Do **not** use raw cosine similarity as the main paper metric.
It is too opaque and too sensitive to wording style.

## Step 10: extra diagnostic dimensions

For each accepted node alignment, store:
- embedding cosine similarity
- overlap class
- abstraction relation
- causal-role relation
- recoverability

This lets us say things like:
- “overlap exists, but the prediction is broader”
- “overlap exists, but the prediction is context-heavy”
- “the gold node is not really recoverable from abstract text”

## What to report in the paper

The paper should report:

1. strict exact node / edge metrics
2. weighted semantic node / edge metrics
3. adjusted semantic metrics excluding unrecoverable gold content
4. comparability-class shares
5. a few hand-worked examples

That keeps the main story transparent:
- exact match is harsh
- semantic overlap is more meaningful
- some benchmark rows are simply not fair abstract-level targets

## What not to do

Avoid:
- a single opaque scalar based mostly on embeddings
- a purely free-form LLM judgment with no explicit mapping labels
- forcing one-to-one alignment when abstraction mismatch is common
- treating unrecoverable gold content as ordinary extraction failure

## Why this is defensible

This metric is defensible because:
- the primary weights are simple and inspectable
- the abstraction mismatch is explicit, not hidden
- exact metrics remain available as a baseline
- adjusted metrics are clearly justified by abstract recoverability
- the method separates:
  - extraction quality
  - graph-object mismatch
  - benchmark unfairness

## Recommended next implementation step

Implement this in two layers:

1. **Node alignment layer**
   - exact / lexical / embedding candidate generation
   - structured pairwise judge labels
   - weighted node recall / precision

2. **Edge alignment layer**
   - judge-assisted edge mapping using node-aligned candidates
   - weighted edge recall / precision

This gives a practical validation pipeline without forcing the extraction model to overfit the benchmark ontology.
