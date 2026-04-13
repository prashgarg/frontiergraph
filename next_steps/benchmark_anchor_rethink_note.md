# Benchmark Anchor Rethink Note

Date: 2026-04-09

## Question

What should the main historical benchmark anchor be once we stop treating the current conservative `directed_causal` layer as untouchable?

The decision matters because the current benchmark is clean but narrow, and the names can mislead:

- "directed" in the current main task really means benchmark-causal by evidence method
- the graph retains a much larger ordered-claim universe that is not currently the headline task

## What we have in the data already

From the latest effective hybrid corpus:

- all rows: `1,241,705`
- rows with `directionality_raw = directed`: `1,087,348`
- rows with directional claim language
  - `directionality_raw = directed`
  - `causal_presentation in {explicit_causal, implicit_causal}`
  - total: `677,357`
- rows in the current benchmark-causal layer: `86,012`

So we already have the ingredients for a layered benchmark redesign without re-running extraction:

- `directionality_raw`
- `causal_presentation`
- `evidence_type`
- `relation_type`

## Four plausible anchors

### Option A. Strict benchmark-causal anchor

Definition:

- ordered edge
- evidence method in the benchmark-causal set

Pros:

- sharpest and most economics-facing benchmark
- easiest to defend as a credibility-oriented target
- strongest continuity with the current paper

Cons:

- very sparse
- excludes most ordered claims
- makes "directed" easy to misunderstand
- risks benchmarking only a narrow elite slice of the graph

### Option B. All ordered claims anchor

Definition:

- `directionality_raw = directed`

Pros:

- matches the plain-language meaning of direction
- much larger and less sparse
- closest to how many papers actually frame claims in text
- avoids the "directed really means identified causal" confusion

Cons:

- includes many weak or descriptive ordered statements
- may drift toward a broader discovery-prediction task than economists expect
- could make the main object feel less discipline-specific

### Option C. Ordered causal-language anchor

Definition:

- `directionality_raw = directed`
- `causal_presentation in {explicit_causal, implicit_causal}`

Pros:

- much larger than strict benchmark-causal
- closer to paper-shaped substantive claims than all ordered relations
- clearer to explain than the current benchmark-causal layer
- still nested inside a causal-oriented reading of the literature

Cons:

- depends on how papers talk, not only on method
- may reward rhetorical causal language that is not strongly identified
- still excludes directional but explicitly noncausal predictive questions

### Option D. Coequal dual-anchor design

Definition:

- report one broad main ordered-claim anchor
- and one strict benchmark-causal anchor side by side

Pros:

- most transparent about the trade-off
- lets readers see the conservative subset directly
- avoids pretending one object serves every purpose

Cons:

- risks making the paper feel over-specified
- weakens the headline comparison unless one anchor is clearly primary

## Recommendation

The most balanced redesign is:

### Primary anchor

Use an ordered-claim anchor defined by:

- `directionality_raw = directed`
- and, preferably, a causal-language restriction
  - `causal_presentation in {explicit_causal, implicit_causal}`

### Nested stricter anchor

Keep the current benchmark-causal layer as a stricter secondary evaluation:

- evidence method in the identified-causal set

### Auxiliary relation-establishing layer

Keep undirected contextual relations as:

- support structure
- and, if useful, an auxiliary non-headline benchmark

## Why this is the best balance

This design keeps three good things at once:

1. the main object is no longer absurdly sparse
2. the main object still reads like an economics-facing substantive claim
3. the conservative method-based causal subset remains available as a stricter test rather than disappearing

It also fixes the naming problem. We can stop calling the main benchmark "directed" when what we really mean is "identified causal."

## Suggested naming

Avoid ambiguous names like:

- `directed_causal`
- `undirected_noncausal`

Prefer:

- `contextual_pair`
- `ordered_claim`
- `causal_claim`
- `identified_causal_claim`

The exact names can be tuned, but the principle is important:

- one name for ordering
- one for causal language
- one for identification strength

## Scope and feasibility

This redesign is feasible with existing artifacts.

It requires:

1. deriving new edge-layer labels from the hybrid corpus fields already present
2. extending first-appearance maps and future-positive construction to the new anchor type
3. updating candidate generation so support provenance is explicit by layer
4. rerunning benchmark and reranker evaluation on the redesigned anchor

It does not require:

- re-running extraction from scratch
- redoing ontology work

## Bottom line

If the paper's main question is "what research-shaped claim is likely to emerge next?", the current strict benchmark-causal anchor is too narrow to carry the whole story.

The best redesign is:

- main benchmark on a broader ordered claim layer, ideally causal-language ordered claims
- stricter benchmark-causal evaluation as a nested secondary test
- undirected contextual structure retained as support and auxiliary signal
