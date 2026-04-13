# External Validation Workflow for FrontierGraph

Date: 2026-03-31

This note sketches how to use external graph-text datasets to validate and stress-test FrontierGraph's extraction layer.

## Goal

The goal is not only:
- "can we match a gold graph exactly?"

It is also:
- how does our ontology differ?
- when do we produce broader or narrower concepts?
- when do we fragment one concept into several nodes?
- when do we merge distinct concepts into one?
- when do we recover the right local idea but at the wrong level of abstraction?

## Best first targets

### 1. ReCITE

Why first:
- includes `input_text`
- includes nodes and edges directly
- moderate size
- exactly about causal graph extraction from real-world scientific text

### 2. DAGverse example

Why second:
- very high-value graph supervision
- graph and image are present
- paper URI is present

Caveat:
- may require fetching paper text separately

## Core process

### Step 1. Download the smallest useful slices first

Recommended:
- ReCITE `test.parquet`
- DAGverse example parquet

Do not start by downloading:
- ReCITE responses
- ReCITE evaluations

Those are useful later, but not needed for the first pass.

### Step 2. Build a common benchmark schema

For each external example, normalize into one local schema:
- `dataset_name`
- `example_id`
- `source_text`
- `source_url`
- `gold_nodes`
- `gold_edges`
- `gold_graph_metadata`
- `text_span_type` if known

For DAGverse:
- likely fetch source text from `paper_uri`
- keep the figure image and DAG strings

For ReCITE:
- use `input_text`
- store `nodes` and `edges` directly

### Step 3. Run our own extraction prompt

Use our current extraction prompt on the external source text.

For consistency:
- run one baseline prompt first
- do not overfit to each benchmark before we understand failure modes

Store:
- extracted nodes
- extracted edges
- any edge metadata we can infer
- confidence / explanation fields if available

### Step 4. Align nodes

This is where ontology becomes the real issue.

We should not expect exact string matching to be enough.

Use a staged mapping process:

#### 4A. Exact and normalized string matching
- lowercase
- punctuation removal
- singular/plural normalization
- acronym normalization where obvious

#### 4B. Embedding-based candidate matching
- embed extracted node labels and gold node labels
- propose top-k candidate matches
- use similarity thresholds

This is useful but not sufficient.

Risk:
- embeddings can make wrong-but-plausible semantic merges
- especially for broader/narrower concept pairs

#### 4C. Agentic mapping

This is the "pretend to be a careful human" stage.

For hard or ambiguous node pairs:
- inspect source text
- inspect local graph context
- decide whether the match is:
  - exact
  - broader
  - narrower
  - related but distinct
  - no match

This is effectively semi-manual adjudication with high reasoning effort.

It is expensive, but likely the right thing to do on a small validation benchmark.

## Proposed node-level labels

For each extracted node versus gold node:
- `exact_match`
- `broader_than_gold`
- `narrower_than_gold`
- `partial_overlap`
- `no_match`

This is important because ontology error is not binary.

## Proposed edge-level labels

For each extracted edge versus gold edge:
- `exact_match`
- `direction_reversed`
- `endpoint_mismatch`
- `relation_present_but_weaker`
- `relation_present_but_stronger`
- `missing`
- `hallucinated`

If possible, also separately record:
- whether the edge is explicit in text
- whether it seems derived from context

## Key metrics to compute

### Node metrics
- node precision
- node recall
- exact-match rate
- broader/narrower rate
- unmatched rate

### Edge metrics
- edge precision
- edge recall
- direction accuracy
- endpoint alignment accuracy

### Graph-level metrics
- connectedness / fragmentation
- average node abstraction level
- whether our graph is too sparse or too dense
- whether we recover major mediator structure

## What to look for substantively

This exercise should tell us more than whether we "win."

The main things to learn are:

### 1. Ontology mismatch pattern
- Are we too broad?
- Are we too narrow?
- Are we too literal?
- Are we missing the document's intended abstraction level?

### 2. Graph fragmentation
- Do we recover many correct pairwise edges but fail to build a coherent graph object?

### 3. Directionality mistakes
- Are we capturing the right relation but in the wrong direction?

### 4. Missing mediators
- Do we skip important intermediate variables that are present in the gold graph?

### 5. Over-generation
- Do we hallucinate plausible edges not actually supported by the source text?

## Recommended first empirical pass

### Pass A: ReCITE only

Use ReCITE first because:
- text is already present
- graph is already present
- size is manageable

Goal:
- understand basic node/edge alignment failure modes

### Pass B: DAGverse small sample

Then use a small sample from DAGverse.

Goal:
- compare our extracted graph to a figure-backed semantic DAG
- evaluate graph coherence and abstraction level more seriously

## Recommended initial sample sizes

Start small:
- ReCITE: 25 to 50 examples
- DAGverse: 15 to 25 examples

This is enough to:
- build the mapping machinery
- see where ontology fails
- decide whether the benchmark is worth scaling

## Why agentic mapping is worth doing

The hard part here is not pure extraction.
It is interpretation.

If a gold node is:
- "education level"

and our extraction gives:
- "college degree or higher"

that is neither a clean hit nor a clean miss.

An automated metric will often handle this badly.

So a careful agentic adjudication stage is likely worth it for:
- the first 50 to 100 hard cases

This can later become:
- a rubric
- a smaller human-coded validation set
- or a model-assisted alignment step

## Practical near-term plan

1. Download ReCITE core benchmark.
2. Download DAGverse example release.
3. Inspect schemas and convert them to one internal format.
4. Run one fixed FrontierGraph extraction prompt.
5. Build simple exact + normalized node matching.
6. Add embedding-based candidate matching.
7. Manually/agentically adjudicate ambiguous matches.
8. Write up failure modes.

## What success would look like

The best outcome is not necessarily:
- exact graph recovery

The best outcome is:
- we understand exactly how our extraction differs
- we can characterize ontology errors clearly
- we can say whether FrontierGraph is recovering the right research structure at a useful level of abstraction

