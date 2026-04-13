# vNext Object Manual Review

## What I reviewed

I compared:

- the active path/mechanism shortlist at `h=5`
- the direct-scored `context_transfer` objects
- the direct-scored `evidence_type_expansion` objects

Files reviewed:

- `outputs/paper/23_current_path_mediator_shortlist_patch_v1_labels_generic/current_path_mediator_shortlist.csv`
- `outputs/paper/29_vnext_object_scored_frontier/context_transfer_scored.csv`
- `outputs/paper/29_vnext_object_scored_frontier/evidence_type_expansion_scored.csv`

## Main judgment

The new vNext objects are real improvements, but in a specific way.

They are **not** better as a replacement for the whole current path/mechanism shortlist.
They **are** better as a second-layer interpretation of what the next study should do.

So the right structure is:

1. keep the current path/mechanism object as the main frontier surface
2. use the new vNext objects to say what kind of follow-up frontier the pair suggests

## Strongest family

### Context transfer

This is the strongest new family overall.

Why:

- it uses genuinely new information from the ontology overlay
- it turns context metadata into a substantive question
- it often sharpens a broad path question into a concrete next-study object

Best examples:

- `CO2 emissions -> exports`
  - baseline object: a broad path question
  - stronger vNext object: where should we test the relation beyond `EU-15`?
  - this is clearly more actionable

- `financial development -> green innovation`
  - baseline object: a good path question already
  - stronger vNext object: test beyond `South Africa`
  - this is a very plausible empirical frontier object

- `environmental regulation -> sustainable development`
  - baseline object: a mechanism question
  - stronger vNext object: test beyond `China`
  - this is a clean context-transfer framing

Weakness:

- when endpoints are too generic, context-transfer can still sound shallow
- examples like `output -> CO2 emissions` are less compelling than the best examples above

## Second strongest family

### Evidence-type expansion

This is also strong and is easier to explain methodologically.

Why:

- it directly uses edge evidence structure
- it says what evidence is missing, not just what concept link is missing
- it is especially good for turning repetitive descriptive literatures into a sharper research question

Best examples:

- `willingness to pay -> CO2 emissions`
  - baseline object: a path question
  - stronger vNext object: the next step is quasi-experimental or panel-based evidence
  - this is much more concrete

- `CO2 emissions -> exports`
  - baseline object: broad path question
  - stronger vNext object: move beyond time-series work toward panel / IV / quasi-experimental evidence
  - this is excellent

- `price changes -> CO2 emissions`
  - baseline object: broad path question
  - stronger vNext object: ask for stronger evidence than descriptive observation
  - this is useful, though less exciting than the best examples

Weakness:

- the family can become templated
- if the underlying pair is not interesting, “what evidence should come next?” does not rescue it

So this family needs to sit on top of a decent pair-quality screen.

## What should not be overclaimed

### These objects do not replace path/mechanism questions entirely

Path/mechanism questions are still the best default object when:

- the main uncertainty is conceptual or mechanistic
- we do not yet have enough context or edge evidence to sharpen the question further

### Family-aware questions are not yet paper-central

They are useful, but only one meaningful broader family is seeded right now.
So they are not yet a strong general method object.

### Missing empirical confirmation is good, but currently narrower than evidence-type expansion

This family works especially well for theory-heavy links.
It is promising, but I would keep it behind evidence-type expansion for now because:

- it applies to a smaller slice
- it overlaps conceptually with the broader evidence-expansion framing

## Recommendation for the paper

I would present the ontology-vNext insight this way:

- the current main surfaced object remains a path/mechanism question
- richer ontology structure makes it possible to derive more specific frontier objects
- the two strongest examples are:
  - context-transfer questions
  - evidence-type expansion questions

That is a strong methodological extension without pretending we have already rebuilt the whole system around those objects.

## Recommendation for implementation

Next implementation should probably be:

1. keep the current frontier retrieval and path/mechanism renderer
2. add a second-layer routing rule:
   - if context gap is high and pair evidence is narrow, emit a context-transfer question
   - if evidence profile is narrow and support is otherwise decent, emit an evidence-expansion question
3. keep those as internal or appendix objects first, before any public integration

## Bottom line

The review is favorable.

The new ontology-vNext objects are not just prettier descriptions.
At their best, they are better research objects.

But they work best as **structured follow-up views on top of the current frontier**, not as a full replacement for the current path/mechanism object.
