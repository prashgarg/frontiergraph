# FrontierGraph: Methodology Directions

Date: 2026-04-04

This note collects the main methodology directions that now look most promising, given what we learned from the internal validation work.

The immediate sequencing has now changed.

The current recommendation is:

- **freeze the ontology through the next paper pass**
- first improve the paper's object, ranking, and ripeness story on the existing graph
- only then redesign ontology if the remaining failures still point there

The most current execution order lives in:

- [frozen_ontology_execution_plan.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/frozen_ontology_execution_plan.md)

## 1. What the current method is

The current paper uses a deliberately transparent ranking rule.

The working object is:

- a **missing directed link** between two normalized concepts

The current score reads the local graph around that missing link using four ingredients:

1. **path support**
   - are the endpoints already connected by short nearby paths?
2. **underexploration gap**
   - is the direct link still absent despite that support?
3. **motif support**
   - does the same endpoint pair reappear in several nearby patterns?
4. **hub penalty**
   - is the score high only because both endpoints are generic, high-degree nodes?

The benchmark is:

- **preferential attachment**
  - source out-degree times target in-degree

This is a good baseline because it is transparent and easy to interpret. But it is also limited. It treats the graph as a fixed ontology of nodes and mostly ranks single missing edges.

## 2. What the validation work changed

The recent benchmark work clarified two things.

First, ontology is a real issue. The problem is not only label matching. It is also:

- broader versus narrower concepts
- semantic summary graph versus variable graph
- figure-level object versus paper-level object
- what is or is not recoverable from title and abstract alone

Second, this has implications for both stages of the pipeline:

1. **ontology formation**
2. **question prediction once the graph exists**

That means the next methodology improvements should not focus only on prompt tweaks. They should also change how concepts are represented and how prediction is done downstream.

## 3. Ontology: what should improve

The current ontology is strong enough to build a graph, but it is probably too flat.

The paper now condenses the graph into about `6,752` concept codes. That is useful for tractability, but it likely forces too many cases into a single canonical node when the true relation is:

- exact synonym
- broader parent category
- narrower child category
- context-specific variant
- related but not mergeable concept

### Recommendation: move from a flat ontology to a layered one

Instead of one canonical node level only, the ontology should have at least three layers:

1. **paper-local mention**
   - the exact concept string extracted from a given paper
2. **canonical concept**
   - the best normalized node for graph construction
3. **concept family / parent**
   - a broader grouping that captures cases where two concepts should be linked but not fully merged

This would help with cases such as:

- `institutional factor` versus `institutional quality`
- `antipsychotic drug group` versus `haloperidol group`
- `energy consumption` versus `residential energy consumption`

The goal is not to avoid normalization. It is to preserve more structure about the type of normalization being made.

### Concrete ontology upgrades

#### A. Parent-child concept structure

Store:

- `concept_id`
- `parent_concept_id`
- `mapping_type`
  - `exact`
  - `synonym`
  - `broader`
  - `narrower`
  - `related`

This would let the graph operate at multiple resolutions.

#### B. Keep mapping uncertainty

Instead of forcing every tail label into one accepted concept, store:

- top 2 or 3 candidate mappings
- confidence band
- provenance

This is especially useful for:

- high-centrality nodes
- highly reused ambiguous terms
- concepts that appear to bridge fields

#### C. Add type information

Nodes should carry a lightweight type system such as:

- intervention / policy
- outcome
- mechanism
- institution
- population
- method / design
- variable / factor
- place / geography

That would help both normalization and downstream prediction.

#### D. Build "do not merge" constraints

The validation work suggests that some mistakes are not missed merges but **bad merges**. A useful next step is to create explicit separation rules for common failure modes.

Examples:

- do not merge a treatment class with one named drug
- do not merge a policy mechanism with a final welfare outcome
- do not merge a broad factor family with one of its components

### How internal validation helps ontology

The benchmark failures can be turned into ontology supervision.

Each reviewed mismatch can be coded as one of:

- exact concept but wrong wording
- should be parent-child, not merged
- should be separate nodes
- graph-object mismatch, so not an ontology problem
- not recoverable from abstract

That creates a much more useful ontology-improvement dataset than a single exact-match score.

## 4. Prediction: what the current method is missing

The current score is transparent, but it is still a hand-built additive rule.

That is useful for:

- interpretability
- public inspection
- paper clarity

But it is probably leaving signal on the table.

### Recommendation: move to a two-stage prediction system

I would keep the current transparent score, but change its role.

#### Stage 1. Candidate retrieval

Use the current graph-based score to retrieve:

- plausible missing edges
- path-rich candidates
- other structured candidates

This preserves transparency and keeps the system inspectable.

#### Stage 2. Reranking

On the retrieved set, use a more flexible predictive model.

This is a better place for sophistication than replacing the first stage entirely.

## 5. Better predictive models

There are several realistic upgrades.

### A. Pair-year hazard model

Observation:

- one row per pair-year `(u,v,t)`

Outcome:

- whether the direct link appears in `t+1` to `t+h`

Features:

- path count by length
- mediator diversity
- motif counts
- source and target degrees
- degree growth
- support in core versus adjacent journals
- method diversity around the pair
- support credibility or stability
- local citation-weighted support
- undirected support already present
- whether the pair is a gap or boundary type

Model:

- logistic hazard model
- gradient boosted trees
- survival model

This is probably the most practical next upgrade.

Why:

- easy to interpret
- can use time properly
- can learn nonlinear interactions
- does not require a large neural architecture immediately

### B. Learning-to-rank model

Instead of predicting appearance probability directly, train the model to rank future-realized links above non-realized ones within each cutoff year.

This fits the paper's actual use case better than plain classification.

Possible approaches:

- pairwise ranking loss
- LambdaMART-style ranking
- gradient boosting with cutoff-year grouped comparisons

This could be especially helpful if the goal is shortlist quality rather than calibrated probabilities.

### C. Dynamic graph representation model

A more ambitious option is to learn node and pair representations from the evolving graph itself.

Examples in spirit:

- temporal node embeddings
- temporal graph neural networks
- temporal knowledge-graph completion models

Why this is promising:

- can learn higher-order graph structure more flexibly
- can incorporate time directly
- can use node attributes and edge types jointly

Why I would not start here:

- harder to explain in the paper
- easier to overfit
- harder to debug when ontology is still moving

So I would treat this as a second-step model, not the immediate next model.

## 6. Recommendation-system framing

Your intuition here is good.

This can be reframed partly as a recommendation problem:

- recommend which unresolved research questions should receive attention next

A recommendation-style system could use:

- graph structure
- text features
- publication outcomes
- downstream citation or FWCI outcomes
- journal placement
- method patterns

But there is an important design choice:

### What is the target?

We should not collapse everything into one target.

At least three targets should be separated:

1. **appearance**
   - does the link later appear?
2. **impact conditional on appearance**
   - if it appears, is it later reused or cited heavily?
3. **current plausibility / paper-shapedness**
   - does it look like a coherent question worth reading now?

If we merge all of these into one score, popularity will dominate too easily.

### Recommendation

Use multi-objective prediction:

- model A: predict appearance
- model B: predict downstream impact conditional on appearance
- model C: current plausibility or usefulness

Then either:

- keep them separate
- or combine them in a transparent composite

That is much safer than directly optimizing on citation outcomes alone.

## 7. Joint edges and path-level objects

This is one of the most important methodological openings.

Right now the paper mostly predicts:

- one missing direct edge

But science often moves through:

- small bundles of edges
- mediator additions
- path thickening
- mechanism elaboration

### Recommendation: define second-order candidate objects

There are at least three useful objects beyond a single edge.

#### A. Missing path closure

Object:

- `u -> m -> v` already exists locally
- direct `u -> v` is missing

This is the current main object, but it should be treated more explicitly as a path-supported closure candidate.

#### B. Mediator expansion candidate

Object:

- direct `u -> v` already exists
- the next question is which mediator `m` is likely to be added

This matches your direct-to-path result.

#### C. Small research-program candidate

Object:

- a local subgraph involving endpoints plus several candidate mediators
- the question is not one edge but whether a small mechanism program is taking shape

This could be represented as:

- a scored motif
- a small path bundle
- a hyperedge-like research-program object

This is likely closer to how economics research actually develops.

### Practical way to model this

Instead of only scoring `(u,v)`, also score:

- `(u,m,v)` triples
- endpoint pairs plus mediator sets
- motif templates

Then evaluate:

- direct closure
- mediator addition
- path thickening

This would make the paper much richer than a plain link-prediction exercise.

## 8. New nodes: the big missing piece

This is the biggest structural limit in the current setup.

Right now the system assumes:

- the important future moves happen between existing nodes

But scientific progress often introduces:

- new concepts
- new measures
- new methods
- new institutional forms
- new named technologies or policy instruments

So a fuller research-allocation system needs a **node-birth layer**, not only an edge-formation layer.

### Recommendation: split the problem in two

#### A. Node emergence

Predict which new concepts are likely to become stable enough to enter the ontology.

#### B. Attachment of new or existing nodes

Once a node exists, predict what it connects to.

### What extra data would help

To study node birth well, you probably want more than the current normalized graph.

Useful additional sources:

- raw paper-local extracted labels before force-mapping
- author keywords
- JEL codes or topic codes
- working papers and preprints
- conference titles or abstracts
- citation context or phrase-level novelty signals

### Practical node-birth proxy

Even before collecting more sources, you can use:

- recurring unmapped tail labels over time
- labels with growing frequency but low mapping confidence
- labels that appear across multiple journals before entering the accepted concept inventory

Those are natural candidates for "new nodes that are trying to be born."

### Why this matters

If the system only recommends new edges among old nodes, it may become too conservative.

That is one reason the current paper should remain modest in interpretation. It is a frontier-tracing system inside an existing ontology, not yet a full system for detecting concept creation.

## 9. Where an LLM false-positive filter fits

This idea still looks useful, but only in a narrow role.

The safest role is:

- **current-era precision filter and structured failure audit**

That means:

- take 2026 candidate questions
- ask an LLM whether they look:
  - concrete
  - nontrivial
  - not already saturated
  - supported by a coherent mechanism

This could help reduce false positives in the public recommendation layer.

### Why not use it for old vintage backtests?

Because for cutoffs like 2005, there is a serious leakage risk:

- the model may know later literature
- the filter may silently use future knowledge

Even if the prompt only shows the old snapshot, the model's training data may already encode later developments.

So the right use is:

- present-day reranking or filtering
- not the main historical validation exercise

What makes this more useful than a simple reranker is that the LLM can also explain:

- why a candidate should be pruned
- whether the object should be reframed
- what deterministic implication follows

That makes the LLM layer useful not only for precision, but for learning where the deterministic system is mis-specified.

## 10. What I think is the best next methodology sequence

If I had to pick the highest-value next steps, I would do them in this order.

### Step 1. Change the paper's object and language

- keep the direct edge as the retrieval anchor
- make the surfaced object usually a path-rich or mechanism-rich question
- use the prototype review to revise the paper before larger modeling changes

### Step 2. Build a pair-year hazard or ranking model

- keep the current transparent score as retrieval baseline
- add a learned reranker on top of retrieved candidates
- use historical direct-link appearance as the rigorous benchmark target

This is now the best practical prediction upgrade on the frozen graph.

### Step 3. Keep the LLM audit as a diagnostic sidecar

- use current 2026 top candidates
- keep structured keep/downrank/drop labels
- use explicit prune reasons and reformulation suggestions
- treat this as a precision layer and failure-labelling tool, not the main historical validation device

Why this remains high:

- it already told us that the current direct-edge object is too thin
- it can keep guiding deterministic rerouting and reranking
- it helps reveal whether remaining failures are ontology, ranking, or graph-object failures

### Step 4. Add path-level candidate objects and the ripeness panel

Move beyond:

- only missing direct edges

Toward:

- mediator additions
- path thickening
- research-program candidates
- yearly ripeness measures on unresolved pairs and direct edges

This is the best conceptual upgrade.

What the first current-era audit suggests:

- among the top 100 current candidates, roughly `92%` want path-question framing
- roughly `7%` want mediator-question framing
- only about `1%` plausibly remain direct-edge objects as currently stated

So this is no longer just a theoretical extension. It now looks like the natural output layer for the existing retrieval system.

### Step 5. Redesign ontology if it is still the binding bottleneck

Use the evidence from:

- reranker failures
- audit labels
- path/mechanism review failures

Only then decide whether to start with:

- minimal patch
- layered ontology
- full redesign

### Step 6. Open the node-birth layer

Use:

- recurring tail labels
- growing unmapped concepts
- preprint / working-paper inputs if available

This is the biggest long-run extension.

## 11. My bottom line

The methodology should now move in two directions at once:

1. **better prediction and better surfaced objects on the current graph**
   - learned reranking
   - path-level and program-level candidate objects
   - ripeness analysis

2. **better representation once the stronger paper is visible**
   - richer ontology
   - multi-resolution nodes
   - node birth

The current paper does not need all of this at once.

But the clean next-generation FrontierGraph would likely look like:

- layered ontology
- transparent retrieval stage
- learned reranking stage
- path-rich candidate objects
- separate handling of node birth
