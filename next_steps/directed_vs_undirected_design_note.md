# Directed vs Undirected Design Note

Date: 2026-04-09

## Purpose

This note clarifies what "directed" and "undirected" mean in the current pipeline, why that can be confusing, and what the most reasonable target design is for method v2.

The underlying substantive question is important. In real research, people often establish relationships before they establish direction, and they often establish direction before they establish causality. So a method that treats everything as either "causal directed" or "undirected context" risks collapsing distinctions that matter to economists.

## The three concepts that should be kept separate

There are at least three different axes here:

1. textual directionality
   - does the paper state the relation as `A -> B`, or just as a relation between `A` and `B`?

2. causal credibility or identification status
   - does the paper have an empirical design that the pipeline treats as causal enough for the main benchmark?

3. benchmark role
   - is this relation part of the headline prediction target, a support signal, or an auxiliary task?

Current discussions often compress those into one "directed versus undirected" distinction. That is the source of much of the confusion.

## What the current pipeline actually does

### Extraction layer

The extraction schema records:

- `directionality`
- `causal_presentation`
- `evidence_method`

So the raw paper-local object already distinguishes:

- whether the text is directional
- how the paper talks about the relation
- what method underlies the claim

That is good.

### Hybrid graph layer

The current hybrid corpus then defines:

- `edge_kind = directed_causal` if `evidence_method` is in the directed causal method set
- otherwise `edge_kind = undirected_noncausal`

In code this happens in:

- `src/research_allocation_v2.py`

using the method set:

- `experiment`
- `did`
- `iv`
- `rdd`
- `event_study`
- `panel_fe_or_twfe`

So in the current graph object, "directed" does not mean "the text pointed from A to B." It means "the relation is treated as causally directed for benchmarking purposes."

Everything else is pushed into the undirected contextual layer.

## How large is the missing middle in the current data?

Using the latest effective hybrid corpus:

- `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`

the relevant layer sizes are:

- all rows: `1,241,705`
- rows with `directionality_raw = directed`: `1,087,348`
- rows in the current benchmark-causal layer: `86,012`
- rows in the missing middle
  - directed in wording
  - but not in the current benchmark-causal layer
  - total: `1,006,597`

So the missing middle is not marginal. It is the dominant part of the ordered-claim universe.

At the pair and paper levels:

- directional ordered pairs: `925,908`
- benchmark-causal pairs: `75,877`
- missing-middle pairs: `862,037`

- papers with any directional row: `224,015`
- papers with any benchmark-causal row: `22,827`
- papers with any missing-middle row: `213,381`

This makes the design trade-off concrete. The current benchmark is very sharp, but it is also a very narrow slice of the ordered literature graph.

## What is inside the missing middle?

The missing middle is not just vague association language.

By `causal_presentation` inside the missing middle:

- `explicit_causal`: `515,151`
- `implicit_causal`: `96,318`
- `noncausal`: `390,217`
- `unclear`: `4,911`

By `relation_type` inside the missing middle:

- `effect`: `565,710`
- `other`: `261,603`
- `association`: `97,450`
- `difference`: `45,612`
- `prediction`: `36,222`

So a large share of the missing middle consists of ordered, effect-like, often causally worded claims that are currently excluded from the benchmark-causal layer because the evidence method is not in the strict identifying set.

### Important implication

A relation can be directional in language and still be stored as undirected contextual support downstream if its evidence method is not treated as causally identifying.

That is a strong and conservative design choice. It improves benchmark sharpness, but it also throws away some directional information.

## What the current benchmark predicts

The headline historical anchor is:

- future first appearance of a missing directed causal edge

So the main benchmark question is not:

- do `A` and `B` become related?

It is:

- does `A -> B` appear later in the directed causal subgraph?

This is exactly the object described in:

- `paper/research_allocation_paper.tex`

The undirected task exists too, but mainly as a secondary or atlas-style object rather than the headline paper benchmark.

## Where undirected information enters today

This is the subtle part.

When the candidate builder creates directed candidates, it does not use only the directed causal subgraph as support. It builds `support_edges` from:

- directed causal edges
- undirected contextual edges
- and the reverse copy of undirected contextual edges

So for the directed task, the system currently does:

- predict a future directed causal edge
- using both directed causal support and undirected contextual support

That is actually quite sensible substantively. A contextual association can be useful evidence that a later causal relation may be worth studying. But it means the words "directed benchmark" do not mean "only directed information was used."

## What is potentially confusing for readers

### Confusion 1. "Directed" sounds like a property of the text, but it is partly a property of the benchmark design.

That is true in the current pipeline. The paper should keep saying this clearly.

### Confusion 2. Directional but weakly identified claims are being collapsed into undirected context.

Also true. This is a conservative choice, not a semantic truth.

### Confusion 3. The candidate object and the evaluation object are not the same.

Also true.

Currently the candidate is often a path-rich, mixed-support local opportunity, but the success event is still narrow: later directed causal edge appearance.

### Confusion 4. Undirected edges are not "unimportant"; they are support.

That point needs emphasis. The method already relies on them as contextual evidence, even if the main target is directed causal emergence.

## What is ideal conceptually

The clean conceptual design is not two categories but three.

### Layer 1. Contextual undirected relation

Meaning:

- the paper establishes that `A` and `B` belong in the same local neighborhood
- but not necessarily in a directional or causal way

Use:

- support signal
- exploratory relation-establishing question
- auxiliary benchmark if desired

### Layer 2. Directional but not benchmark-causal relation

Meaning:

- the paper presents an ordered claim or influence direction
- but the evidence is not strong enough to treat it as a causal-benchmark edge

Use:

- valuable support for idea generation
- possibly a separate prediction task later
- especially useful for forward-looking screening

This is the main layer the current pipeline largely collapses away.

### Layer 3. Directed causal benchmark edge

Meaning:

- ordered relation
- backed by a method class the pipeline treats as benchmark-causal

Use:

- main historical benchmark anchor
- strongest profession-facing object for the paper

## What is most reasonable for the current paper

I would not explode the main benchmark right now.

The most reasonable paper design is:

1. keep the headline historical anchor as future directed causal edge appearance
2. keep undirected contextual structure as support and as an auxiliary task
3. acknowledge clearly that this is a conservative choice
4. preserve the possibility of a middle directional-noncausal layer in method v2 or v3

Why keep the main benchmark directed causal?

- it is the cleanest dated event
- it is the most economics-facing benchmark object
- it avoids claiming success from diffuse co-mention growth alone
- it matches the profession's stronger notion of what a substantive paper contribution often looks like

Why not ignore undirected structure?

- because many good ideas begin as relationship-establishing questions
- because the current builder already uses undirected support
- because papers often build causal work on top of prior contextual relation structure

## What I think people will want

Different readers will want different things.

### Economists

They will mostly want to know:

- are you predicting causal claims, or just correlations?
- if I inspect a surfaced idea, does it come with a mechanism or not?
- are weak descriptive relations being mistaken for strong causal findings?

For them, keeping the main anchor directed causal is attractive.

### Network-science or discovery readers

They may want:

- broader relation emergence
- less conservative use of direction
- cleaner comparison with co-occurrence link prediction

For them, the undirected and directional-support layers matter more.

### Forward-looking users

They may want:

- any plausible high-value research question, not only later historically causal edges

For them, it makes sense to use the richer layered object:

- undirected relation-establishing questions
- directional questions
- causal or mechanism questions

## Practical method-v2 recommendation

### Short-run

Keep the main benchmark anchor:

- future directed causal appearance

But make the candidate row more explicit about where its evidence came from:

- directed support count
- undirected support count
- whether the key path is mixed or purely directed
- whether the question is better read as relation-establishing, directional, or causal-mechanistic

### Medium-run

Add an explicit middle layer:

- `directional_noncausal`

This would let us stop forcing all non-benchmark-causal directional claims into the undirected bucket.

### Long-run

Treat idea generation as layered:

- relation-establishing question
- directional question
- causal or mechanism question

Then let the paper focus on the causal layer, while the eventual forward-looking system can use the full stack.

## Bottom line

The current system is conservative in a reasonable way, but the terminology can mislead if we are not careful.

Right now:

- the headline target is future directed causal appearance
- undirected contextual edges are support, not noise
- some directional but non-causal information is being collapsed into the undirected support layer

The best target design is therefore:

- keep the main historical benchmark directed causal
- make support provenance by edge type explicit
- and treat "directional but not benchmark-causal" as the main missing middle layer for future method versions
