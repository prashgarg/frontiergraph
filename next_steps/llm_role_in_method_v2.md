# LLM Role in Method v2

Date: 2026-04-09

## Purpose

This note pins down where LLMs should and should not sit in the project as we move from
the current paper toward the eventual forward-looking frontier-question system.

The main design goal is:

- keep the paper historically disciplined
- keep the forward-looking system useful
- use LLMs where they add contextual judgment and wording help
- do not let LLMs silently replace the benchmarkable graph-based core

## End goal

The end goal is not just a link predictor.

It is a frontier-question engine that can:

- retrieve plausible open research opportunities from the literature graph
- turn them into readable, paper-shaped questions
- critique generic, saturated, or weakly supported candidates
- support present-day forward-looking exploration where historical leakage is no longer the central issue

That implies a layered architecture:

1. graph retrieval
2. candidate-family assignment
3. LLM interpretation and rewriting
4. LLM critique / diagnostic labeling
5. shortlist control
6. human judgment

## What LLMs may do in the historical paper

Allowed historical-paper roles:

- render structured graph candidates into readable path-rich or mechanism-rich question wording
- audit current candidates for structured diagnostic attributes
- identify whether a candidate is too generic, too hub-driven, weakly supported, badly merged, or misframed
- suggest deterministic implications for method improvement

Good historical-paper LLM outputs are therefore things like:

- `paper_shapedness`
- `specificity`
- `mechanism_clarity`
- `too_generic_or_hub_driven`
- `needs_reframing_as_path_question`
- `needs_reframing_as_mediator_question`
- `unclear_directionality`
- `insufficient_local_support`

These are best treated as:

- structured sidecar labels
- diagnostic outputs
- interpretation aids

not as the main benchmark signal.

## What LLMs should not do in the historical paper

Disallowed or highly disfavored roles:

- act as the main historical baseline for “would this idea later happen?”
- score candidates using world knowledge of later literature
- rank historical opportunities based on perceived hindsight importance
- replace the deterministic candidate universe with free-form idea generation
- serve as the paper’s main causal claim for benchmark success

Reason:

the model has seen later history, so historical evaluation would be contaminated if the
LLM were asked to judge future success directly.

## What LLMs can do in the forward-looking system

For current and future-facing use, the leakage objection weakens materially.

So LLMs can play a larger role in:

- rewriting graph candidates into better research-question phrasing
- selecting among path-question versus mediator-question renderings
- flagging crowded or redundant items
- identifying what kind of next study would move the literature
- proposing bounded idea variants from a fixed local graph neighborhood

Even there, the preferred role is still:

- graph retrieves
- LLM interprets and critiques

not:

- LLM invents the candidate universe from scratch

## Academic pushback we should expect

### 1. “This is just hindsight contamination dressed up as evaluation.”

This is the strongest pushback if LLMs are used carelessly in the historical paper.

Best response:

- do not use LLMs as the main historical benchmark
- use them only for rendering and structured diagnostic labels
- keep the historical benchmark anchored in graph-derived objects and dated outcomes

### 2. “The LLM is just doing semantic common sense, not literature-based screening.”

Best response:

- give the model only a bounded local evidence bundle
- ask for within-context attributes, not free-form omniscient ranking
- keep deterministic retrieval separate from LLM critique

### 3. “These candidate families look hand-engineered.”

Best response:

- keep the family set small and interpretable
- tie each family to an observable development margin in the literature
- distinguish clearly between continuity anchor, family label, and surfaced wording

### 4. “The method is getting too flexible.”

Best response:

- keep the historical anchor narrow
- keep the benchmark family compact
- use LLM outputs as sidecars rather than hidden score multipliers
- document what each layer does

### 5. “You are rating readability, not scientific value.”

Best response:

- agree in part
- treat readability and paper-shapedness as screening attributes, not truth claims
- keep them separate from historical realization and from human-usefulness validation

## What counts as an “idea” or recommended object

This is where family assignment matters.

The default recommendation unit should usually be:

- a bounded research question
- with focal endpoints
- plus route evidence

not:

- an arbitrary whole subgraph

So the recommended object is usually not “this entire motif” in the abstract.
It is more like:

- “Does `A` affect `C`, given the existing `A -> B -> C` support?”
- “Through which mediator does `A` affect `C`?”
- “What mechanism thickens the already-known `A -> C` relation?”

## Default idea-object shapes

### 1. Path-supported endpoint question

Canonical shape:

- evidence: `A -> B -> C`
- recommended question: should we study `A -> C` directly?

This is the cleanest `path_to_direct` object.

### 2. Multi-mediator endpoint question

Canonical shape:

- evidence: `A -> B1 -> C` and `A -> B2 -> C`
- recommended question: which mechanisms connect `A` to `C`, and does a direct `A -> C` relation deserve study?

This is still one bounded endpoint question, with richer route evidence.

### 3. Direct-plus-mechanism thickening question

Canonical shape:

- evidence: direct `A -> C` already exists, and later or nearby structure suggests `A -> B -> C`
- recommended question: through what mechanisms does `A` affect `C`?

This is the cleanest `direct_to_path` object.

### 4. Mediator-expansion question

Canonical shape:

- evidence: endpoints `A` and `C` look plausibly related, but the main open object is the mediator
- recommended question: is `B` the relevant mechanism linking `A` and `C`?

This is the cleanest `mediator_expansion` object.

## Shapes that can exist as evidence but should not usually be the primary recommended object

### Longer chains

Example:

- `A -> B -> C -> D`

This can be useful evidence for a recommendation, but it is usually too complex to be the
primary paper-facing object.

Default use:

- support context
- not the main recommended question

unless the chain can be compressed into a cleaner endpoint-plus-mechanism question.

### Branched motifs

Example:

- `A -> B <- C` and `B -> D`

This can be substantively interesting, but by default it is still too graph-native to be
the main recommended object.

Default use:

- evidence for convergence, shared mechanism, or mechanism competition
- not the default paper-facing recommendation

unless it can be rendered as a bounded question such as:

- do `A` and `C` jointly shape `D` through `B`?
- is `B` the shared mechanism through which `A` and `C` matter for `D`?

## Practical default

So the practical answer is:

- yes, paths and motifs can underlie a recommendation
- but the recommendation itself should usually stay bounded
- default paper-facing object = endpoint question or endpoint-plus-mediator question
- longer or branched motifs should usually remain supporting evidence, not the headline object

That keeps the method:

- benchmarkable
- readable
- easier to validate
- less vulnerable to the criticism that we are surfacing arbitrary graph art rather than research questions

## Working rule for method v2

Candidate generation should emit:

- family labels
- focal endpoints
- top mediator or route evidence

LLM layers should consume that bounded object and decide:

- how to phrase it
- whether it is too generic
- whether it should be reframed

They should not redefine the candidate object from scratch.

## Prompt that led to this note

If you want, the next useful move is for me to write a short `llm_role_in_method_v2.md` note that pins this down:

- what LLMs may do in the historical paper
- what they should not do
- and what they can do in the forward-looking system.
