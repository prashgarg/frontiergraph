# vNext Frontier Objects Working Note

This is a working note, not a paper commitment.

## Why these objects exist

The layered ontology prototype added three kinds of structure that the active flat ontology does not preserve directly:

- broader family structure
- node context
- edge evidence type

Once those are available, some frontier questions become better framed as:

- **context-transfer** questions
- **evidence-type expansion** questions
- **missing empirical confirmation** questions
- **family-aware** questions

These are not meant to replace the current path/mechanism shortlist wholesale.
Right now they are best understood as richer follow-up views on top of the current frontier.

## Current read on the four object families

### 1. Context transfer

Core question:

- where should an already-suggestive relation be tested next?

When it helps:

- pair-level evidence is concentrated in one setting
- the endpoint concepts themselves already appear in a wider range of geographies or units

Why it matters:

- it turns context metadata into a substantive research object
- it often converts a broad path question into a concrete next-study object

Current status:

- strongest new family

### 2. Evidence-type expansion

Core question:

- what kind of evidence should come next for this relation?

When it helps:

- the relation already has support
- but that support is dominated by one design family

Why it matters:

- it moves the frontier from node space alone into edge-evidence space
- it can say “the next step is panel / IV / quasi-experimental evidence,” not just “study this link”

Current status:

- second strongest new family

### 3. Missing empirical confirmation

Core question:

- this relation is theory-heavy or model-heavy; what empirical test would best check it?

When it helps:

- current support is mostly theory, simulation, or structural work

Why it matters:

- it makes theory-heavy links legible as empirical opportunities

Current status:

- useful and promising
- narrower than evidence-type expansion in the current slice

### 4. Family-aware

Core question:

- what is specific to this relation within a broader family of related concepts?

When it helps:

- multiple concepts belong in one broader family
- but should remain separate canonical nodes

Why it matters:

- it avoids both over-merging and over-fragmenting related outcomes

Current status:

- conceptually right
- currently narrow because only one explicit nontrivial family is seeded

## Working implementation stance

For now, the safe stance is:

1. keep the current path/mechanism shortlist as the main surface
2. add routing rules that emit a richer object when the ontology-vNext signal is especially strong

That means:

- emit `context_transfer` when context gap is high
- emit `evidence_type_expansion` when evidence design is narrow

This is a conservative step because it does not replace the whole frontier object.
It only upgrades the wording and interpretation where the richer ontology is clearly informative.

## What would change this view

This note should be revised if any of the following happen:

- we seed many more nontrivial families
- context signatures become much richer
- edge-evidence coverage improves materially
- a second-generation scoring experiment shows one of these richer objects should become primary rather than secondary

## Bottom line

The main current object remains:

- path/mechanism question

The main ontology-vNext additions that already look genuinely useful are:

- context-transfer
- evidence-type expansion

Those should be treated as the first serious richer frontier objects in the next internal iteration.
