# Paper Graph Shape and Idea Object Note

Date: 2026-04-09

## Purpose

This note asks a simple question:

What does the graph inside an average paper look like, and what does that imply for the kind of "idea object" our method should surface?

The motivating concern is substantive and familiar. A plausible paper idea is usually not just "connect two topics that are not yet connected." It is usually a claim with some mechanism, route, or local structure behind it.

## Data and measurement

This read uses the latest effective benchmark corpus:

- `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`

and computes one paper-level graph summary per paper using:

- unique concept nodes within paper
- unique mixed edges within paper
- connected components in the undirected paper graph
- directed causal edges within paper
- mediator nodes with directed in-degree and out-degree both at least one
- directed length-2 paths

Outputs are in:

- `data/processed/research_allocation_v2_2_effective/paper_graph_shape_analysis/paper_graph_shape_summary.json`
- `data/processed/research_allocation_v2_2_effective/paper_graph_shape_analysis/paper_graph_shape_per_paper.parquet`
- `data/processed/research_allocation_v2_2_effective/paper_graph_shape_analysis/paper_graph_shape_by_decade.parquet`

Important caution:

- this is based on the latest effective paper graph, not a fresh full rerun on frozen ontology `v2.3`
- that is acceptable for this question because the shape here is driven mainly by paper-local extraction structure, not by small ontology-policy cleanup choices

## Main descriptive facts

Across `228,796` papers:

- mean unique nodes per paper: `6.56`
- median unique nodes per paper: `6`
- mean unique edges per paper: `5.42`
- median unique edges per paper: `5`
- 90th percentile: `10` nodes and `9` edges

The graph inside the median paper is not tiny, but it is sparse.

- mean undirected density: `0.368`
- median undirected density: `0.300`
- `77.4%` of papers are forests
- `46.0%` of all papers are connected trees
- among connected papers, `72.9%` are trees
- `22.6%` of papers contain at least one cycle

So the typical paper graph is not "one edge only." It is better described as a small, sparse local structure.

## How often do papers look like short paths?

Exactly-two-edge papers are only a minority:

- `6.47%` of all papers have exactly `2` edges

But conditional on being a two-edge paper, the connected-path shape is common:

- `78.2%` of two-edge papers are a connected path rather than two disconnected edges

This is a useful result, but it is not enough to say that the average paper idea should be modeled as a two-edge path. Most papers are not two-edge papers.

Edge-count distribution:

- `4.49%` have `1` edge
- `6.47%` have `2` edges
- `11.89%` have `3` edges
- `73.32%` have between `4` and `10` edges
- `3.82%` have `11+` edges

## Shared-node and branching structure

Most papers are not just bags of disconnected pairwise relations.

- `93.5%` of papers have at least one shared node
- `70.2%` have at least one branching node with degree at least `3`
- `63.1%` are a single connected component

This matters. It means the typical extracted paper is better thought of as a sparse local neighborhood than as a single pair.

## Directed causal structure and mediators

If we ask specifically for explicit directed causal structure, the picture changes.

Overall:

- only `9.98%` of papers contain any directed causal edge
- only `3.07%` contain any mediator node in the directed causal subgraph
- only `3.04%` contain any directed length-2 path

Among papers that do contain at least one directed causal edge:

- mean directed causal edges: `3.77`
- median directed causal edges: `3`
- `30.8%` contain a mediator node
- `30.5%` contain a directed length-2 path

Over time, explicit directed structure becomes more common:

- share of papers with any directed edge rises from `1.3%` in the 1970s to `19.5%` in the 2020s
- share with any directed length-2 path rises from `0.3%` in the 1970s to `6.6%` in the 2020s

So mechanism-like structure is real, but still not the dominant explicit object in the extracted graph.

## What this says about the proposal

The proposal was:

If papers often look like short connected paths, perhaps the method should generally predict a path rather than just a missing connection between two nodes.

My view after looking at the data is:

1. The proposal is directionally right.

The paper-local graph is usually not just a naked pair. Shared-node structure is extremely common, and most paper graphs are sparse enough that local paths and branching neighborhoods are meaningful evidence rather than incidental clutter.

2. The literal version is too strong.

The average paper is not a two-edge path. The median paper has about `6` nodes and `5` edges. So "predict a path by default" is too narrow as a structural summary.

3. The best reorganization is not to replace endpoint questions with raw path objects.

Instead, we should shift from:

- ranking isolated endpoint pairs

to:

- ranking endpoint-centered opportunities with explicit local path and mediator evidence

That is a meaningful change. It says the unit of retrieval is no longer "just an edge." It is an endpoint pair plus its supporting local structure.

## Recommended idea object

The most defensible paper-facing idea object is:

- an endpoint question
- or an endpoint-plus-mediator question

backed by:

- supporting paths
- mediator evidence
- local branching neighborhood
- evidence provenance from nearby papers

In plain language:

- good headline object: "Does `A` affect `C`, perhaps through `B`?"
- weaker headline object: raw graph-native motif notation such as `A -> B <- C` with no compression into a substantive question

So the method should distinguish:

- recommendation unit: endpoint or endpoint-plus-mediator question
- evidence unit: path, mediator set, or larger motif

That fits the data better and is easier to benchmark, explain, and defend.

## Implication for candidate generation v2

Candidate generation v2 should not treat the candidate as a bare pair only. It should emit a local evidence object.

Each candidate should carry:

- endpoint pair
- candidate family
- top mediators
- top supporting paths
- whether the local structure is tree-like, branched, or more cyclic
- support counts and provenance

That lets later stages do three different jobs cleanly:

- graph retrieval
- historical evaluation
- LLM-based interpretation and critique

## Family assignment

The graph-shape evidence supports the family split we already sketched:

- `path_to_direct`
  - a missing endpoint link with path support already present
- `direct_to_path`
  - a direct relation exists, but later work thickens it through mediator structure
- `mediator_expansion`
  - the main open question is which mediator or mechanism carries the relation

This is better than a single undifferentiated pool because it keeps the benchmark anchor and the surfaced question object distinct.

## Academic pushback and self-critique

### Pushback 1. "Your paper graphs reflect extraction, not the true idea structure of papers."

This is fair. The graph is an extracted representation, not the paper itself.

Response:

- treat these statistics as descriptive evidence about the extracted review object, not as claims about the full latent structure of research
- avoid saying "papers are paths"
- say instead that the extracted paper-local graph is usually a sparse local neighborhood, so the retrieval object should not be a naked pair

### Pushback 2. "Sparse local structure does not imply that the predicted object should be a path."

Correct.

Response:

- do not make that leap
- use path and mediator structure as evidence
- keep the headline recommended object compressed into an endpoint or endpoint-plus-mediator question

### Pushback 3. "Directed causal chains are rare in your data, so path-based ideas may be an artifact."

Also fair.

Response:

- acknowledge that explicit directed path structure is still a minority object overall
- note that it is more common inside the directed-causal subset and becomes more common over time
- do not require all candidates to be full explicit directed chains

### Pushback 4. "This still sounds like link prediction with nicer prose."

This is the most important critique.

Response:

- method v2 should explicitly move from bare-pair ranking toward local-structure retrieval
- the candidate row must store the supporting neighborhood, not just the pair and a score
- the paper should describe the screened object as a structured open question, not merely a missing link

## Bottom line

The data support a moderate but important redesign.

We should not say:

- the average paper is a two-edge path
- therefore the method should predict raw paths

We should say:

- the average extracted paper is a small sparse local graph
- shared-node structure is common
- two-edge papers are often paths, but most papers are larger than that
- therefore the method should retrieve endpoint-centered opportunities together with their local path and mediator evidence

That is the right bridge between:

- a historically benchmarkable paper method
- and a richer future system that can surface mechanism-shaped research ideas more directly
