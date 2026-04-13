# Motif Inventory and Candidate Schema Note

Date: 2026-04-09

## Purpose

This note extends the paper-graph-shape read by asking:

- what local motif types actually show up in the extracted paper graphs
- which of those should define top-level candidate families
- which should instead remain evidence tags inside a richer local evidence object

The goal is to avoid an arbitrary design where we hard-code only two or three motif types because they are easy to imagine.

## Data

This read uses:

- `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`

and the derived motif analysis:

- `data/processed/research_allocation_v2_2_effective/paper_graph_motif_analysis/paper_graph_motif_summary.json`
- `data/processed/research_allocation_v2_2_effective/paper_graph_motif_analysis/paper_graph_motif_per_paper.parquet`

The motif script is:

- `scripts/analyze_paper_graph_motifs.py`

## Motif inventory we checked

### Undirected or mixed local shapes

- open triad
  - three nodes with two edges sharing a center but no closure edge between endpoints
- triangle
  - three mutually connected nodes in the undirected projection
- branch or star-like neighborhood
  - any node with undirected degree at least `3`

### Directed local shapes

- directed chain length `2`
  - `A -> B -> C`
- directed chain length `3`
  - `A -> B -> C -> D`
- fork or common-driver shape
  - `A -> B` and `A -> C`
- collider or common-consequence shape
  - `A -> B` and `C -> B`
- parallel mediator or diamond-like shape
  - `A -> M1 -> C` and `A -> M2 -> C`
- directed triangle or partial closure
  - `A -> B`, `B -> C`, and `A -> C`

These do not exhaust all possible motifs, but they cover the main local structures that are both easy to define and plausibly relevant to research-question generation.

## How grounded are these in the actual paper graphs?

Across all `228,796` papers:

- undirected open triad: `92.1%`
- undirected branch: `70.2%`
- undirected triangle: `8.6%`
- directed chain length `2`: `3.1%`
- directed chain length `3`: `0.4%`
- directed fork: `5.3%`
- directed collider: `5.3%`
- directed parallel mediator: `0.4%`
- directed triangle: `1.3%`

Among the `22,827` papers that contain at least one directed causal edge:

- undirected open triad: `94.0%`
- undirected branch: `75.7%`
- directed fork: `52.8%`
- directed collider: `53.3%`
- directed chain length `2`: `30.8%`
- directed triangle: `12.7%`
- directed parallel mediator: `4.4%`
- directed chain length `3`: `4.2%`

So the data say:

1. mixed local structure is ubiquitous
2. inside the directed-causal subset, forks and colliders are more common than clean serial chains
3. longer serial chains and parallel-mediator diamonds are real, but much rarer

That is an important corrective. If we only think in terms of `A -> B -> C`, we will miss common local structures that actually show up in the papers.

## What kinds of idea objects do these motifs suggest?

### 1. Open endpoint question with path support

Pattern:

- `A - B - C` or `A -> B -> C`, with `A -> C` absent

Question form:

- "Should we test whether `A` affects `C`, perhaps through `B`?"

Status:

- core candidate family

This is the clearest bridge between graph retrieval and historical benchmarking.

### 2. Endpoint-plus-mediator question

Pattern:

- one or more candidate mediators connect endpoints

Question form:

- "Does `B` mediate the relation between `A` and `C`?"

Status:

- core candidate family

This is especially natural when there is one strong mediator or a short path inventory.

### 3. Endpoint-plus-parallel-mediators question

Pattern:

- `A -> M1 -> C` and `A -> M2 -> C`

Question form:

- "Through which mechanism does `A` affect `C`: `M1`, `M2`, or both?"

Status:

- probably a second-layer candidate family

It is real in the data, but rare enough that it may be better as a richer subtype of mediator-expansion rather than a first headline family in the paper.

### 4. Direct relation thickening question

Pattern:

- `A -> C` already exists
- later work adds mediator structure such as `A -> B -> C`

Question form:

- "What mechanism or route explains the existing `A -> C` relation?"

Status:

- core candidate family

This corresponds to `direct_to_path`.

### 5. Common-driver consequence expansion

Pattern:

- `A -> B` and `A -> C`

Question form:

- "If `A` affects both `B` and `C`, is there a broader downstream consequence map still missing?"

Status:

- evidence-rich, but not yet a core historical family

This motif is common, but the clean benchmark object is less obvious. It is often better treated as evidence that a node is a meaningful driver rather than as a standalone recommendation family.

### 6. Common-consequence convergence question

Pattern:

- `A -> B` and `C -> B`

Question form:

- "Do `A` and `C` jointly shape `B`, or does `B` connect otherwise separate literatures?"

Status:

- evidence-rich, but not yet a core historical family

This is conceptually interesting, but it is harder to benchmark under the current missing-directed-link anchor.

### 7. Longer serial mechanism question

Pattern:

- `A -> B -> C -> D`

Question form:

- "Should we study the endpoint relation `A -> D`, and if so which intermediate route is most plausible?"

Status:

- evidence form, usually not headline family

This is real, but rare. In most cases it should be compressed into an endpoint-plus-mediator or endpoint-plus-route summary.

### 8. Closure or overdetermined relation question

Pattern:

- `A -> B`, `B -> C`, `A -> C`

Question form:

- "Is the direct effect `A -> C` already well explained, or is there still mechanism thickening left to do?"

Status:

- diagnostic evidence, not usually recommendation family

This is more useful for ranking and concentration control than for top-level question surfacing.

## Design conclusion: candidate families should be fewer than evidence motifs

This is the central design rule.

We should not make every real motif into its own top-level candidate family. That would produce a brittle and hard-to-explain method.

Instead:

- candidate families should represent a small number of benchmarkable recommendation objects
- evidence motifs should be a richer vocabulary that describes the local neighborhood supporting that recommendation

## Proposed split

### Top-level candidate families

Keep the paper-facing family set compact:

- `path_to_direct`
- `direct_to_path`
- `mediator_expansion`

Optionally add one carefully defined subtype later:

- `parallel_mediator_expansion`

but only if it improves interpretability enough to justify the extra complexity.

### Evidence motif tags

Candidate rows should be able to carry multiple evidence tags such as:

- `open_triad`
- `branching_neighborhood`
- `directed_chain2`
- `directed_chain3`
- `common_driver`
- `common_consequence`
- `parallel_mediators`
- `directed_triangle`

This lets the retrieval object be richer without exploding the headline taxonomy.

## Recommended candidate row schema additions

In addition to the endpoint pair and score, candidate-generation v2 should emit:

- `candidate_family`
- `anchor_type`
- `focal_mediator` if one exists
- `alternative_mediators_json`
- `top_paths_json`
- `evidence_motif_tags_json`
- `local_topology_class`
  - for example `tree_like`, `branched`, `parallel`, `closure_heavy`
- `path_support_count`
- `mediator_support_count`
- `branch_support_count`
- `closure_state`
  - for example `open`, `partially_closed`, `closed`
- provenance fields tying the local evidence back to paper IDs or support summaries

## What should stay out of the core historical paper for now

The following are intellectually real but should probably not become first-line candidate families yet:

- common-driver exploration as its own main benchmark family
- common-consequence or collider questions as their own main benchmark family
- long raw motifs as the paper-facing recommended object

Reason:

- they are harder to benchmark cleanly
- they are harder to express in a crisp paper-facing question
- they are better suited as evidence tags now, and possibly LLM-assisted forward-looking question types later

## Bottom line

The right expansion is not:

- add every motif we can think of as a new candidate family

The right expansion is:

- keep a small set of benchmarkable recommendation families
- attach a much richer local evidence object to each candidate
- let that evidence object record the broader motif inventory actually present in the papers

That makes candidate-generation v2 both less arbitrary and more faithful to the real paper graphs we have.
