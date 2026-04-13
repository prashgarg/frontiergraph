# Broader Ontology Architecture Questions

## Why zoom out now

The narrow patch work is useful, but it also reveals the limits of the original ontology design.

The current graph is based on a strong but relatively flat normalization layer:
- extracted strings were embedded
- similar items were clustered
- one canonical node was chosen
- the downstream graph mostly works on that single canonical layer

That was a reasonable first system. It made the graph tractable and enabled the current paper.

But the work so far now suggests that the next big gains may come from rethinking **what kind of ontology this is**, not only which local labels should merge.

## 1. What type of ontology we currently have

At a high level, the current ontology behaves like:

- a **single-layer canonical concept ontology**
- optimized for graph construction and de-duplication
- with limited representation of:
  - hierarchy
  - mapping uncertainty
  - context
  - edge attributes

This means it is good at turning many strings into one graph node, but weaker at preserving the **kind of sameness** involved.

Examples of the missing distinctions:
- synonym versus broader/narrower relation
- outcome versus mechanism
- generic umbrella label versus paper-specific construct
- place-specific or sample-specific version of a concept

## 2. The next ontology should probably be multi-layered

The strongest redesign direction now looks like a layered ontology.

### Layer A. Mention layer

Store the paper-local concept mention:
- original string
- normalized string
- extraction provenance
- paper and edge context

This is the level where we preserve exactly what the paper said.

### Layer B. Canonical concept layer

Store the graph-ready concept:
- the node used for most ranking and retrieval

This is the current system's strongest layer and should remain.

### Layer C. Family / parent layer

Store a broader grouping for concepts that should be linked but not fully merged.

Examples:
- `CO2 emissions`
- `carbon emissions`
- `ecological footprint`
- `environmental quality`

These should sometimes live in the same broader family without being identical canonical concepts.

### Layer D. Type layer

Store lightweight semantic type tags such as:
- outcome
- mechanism
- policy / intervention
- institution
- population
- geography
- method
- data artifact
- broad theoretical construct

This would help both surfacing and filtering.

## 3. Context should partly live on nodes

Right now a node is mostly treated as a concept-level item stripped away from much of its context.

But many concepts are only really interpretable with context such as:
- geography
- sector
- population
- time period
- unit of analysis
- level of aggregation

Examples:
- employment in one national context versus another
- urbanization in city-level panels versus national development studies
- willingness to pay in environmental valuation versus other settings

### Recommendation

Do not force all of that into the node identity itself.

Instead, attach **context signatures** to nodes:
- top geographies
- top populations
- top sectors
- top units of analysis
- top methods
- top journals / domains

Then allow the surfaced question layer to use that context when needed.

This is likely better than exploding the graph into too many narrow nodes.

## 4. Some context should live on edges, not nodes

This is one of the biggest missing pieces.

At the moment, the graph mostly knows:
- source concept
- target concept
- a broad causal / noncausal distinction
- some stability / evidence flags

But many users would care whether a relation is supported by:
- theory
- empirics
- experiment
- quasi-experiment
- descriptive observational work
- calibration / simulation
- survey valuation

That is not a small detail. It changes what the “next question” should be.

Examples:
- a relation supported only by theory may invite empirical testing
- a relation supported only by reduced-form empirics may invite mechanism work
- a relation established in one geography may invite transport or replication elsewhere

### Recommendation

Treat edge attributes as a first-class part of the ontology-adjacent design.

Potential edge dimensions:
- evidence mode:
  - theory
  - empirics
  - mixed
- empirical design family:
  - experiment
  - IV
  - DiD
  - panel FE
  - descriptive
  - survey valuation
- causal explicitness
- directionality confidence
- context coverage

Then the frontier can expand not only in **node space** but also in **evidence space**.

## 5. This opens a richer frontier object

The current paper already moved from:
- “missing edge”

to:
- “path-rich or mechanism-rich question”

The next broader move may be:
- “what is missing in the evidence/configuration around this relation?”

That could include:
- missing direct connection
- missing mechanism
- missing empirical confirmation
- missing evidence in a new context
- missing transport across geography or population

That would make the paper much more useful.

## 6. A future ontology could support several frontier types

Once node context and edge attributes exist, the system could surface several distinct frontier types:

1. **node-link frontier**
   - a missing relation between concepts
2. **mechanism frontier**
   - a relation missing a plausible mediating channel
3. **context frontier**
   - a relation established in one setting but not another
4. **evidence frontier**
   - a relation supported by theory but weak in empirics, or vice versa
5. **family frontier**
   - a broad canonical relation whose narrower children are underexplored

This is much richer than a single missing-edge object.

## 7. What this means for the paper

For the current paper pass, we should stay disciplined:
- keep the frozen ontology backbone
- use narrow patches and current reranking
- do not pretend we already built the richer ontology

But for the broader research program, this is likely the right direction.

The bigger contribution may not just be:
- predicting missing links in a concept graph

It may be:
- building a research frontier system that understands:
  - concepts
  - families
  - context
  - and evidence type

## 8. Recommended design sequence

### Near term
- continue narrow, evidence-led ontology patches
- keep measuring the effect on shortlist quality and concentration

### Next ontology redesign
- add layered family structure
- keep mention -> canonical -> family separation

### After that
- add node context signatures
- add edge evidence attributes
- expand the frontier object beyond node-link closure alone

## Bottom line

The current ontology was a good first-generation graph ontology.

But it is best understood as:
- a **single-layer canonicalization system**

The next-generation ontology should be:
- **layered**
- **context-aware**
- and partly **edge-typed**

That is likely where the project becomes not just cleaner, but substantially more useful.
