# Unresolved Method-Heavy Evidence Tail Audit

## Scope

This audit looks at the highest-support unresolved evidence edges after the conservative evidence-taxonomy cleanup.

The focus is not the whole unknown tail.
It is the **method-heavy, high-support** tail that still survives after summary-layer cleanup.

## Main finding

The unresolved tail is dominated by a **method-artifact region**, not by subtle evidence-taxonomy ambiguity on substantive research relations.

The clearest example is the large cluster around:

- `Method of Moments Quantile Regression (MMQR)`

paired with things like:

- `simulation`
- `estimation accuracy`
- `place of residence`
- `spatial autoregressive model`
- `estimation`
- `OECD countries`
- `CO2 emissions`
- `forecasts`
- `weighting schemes`
- `policy variables`

These rows mostly share:

- `dominant_evidence_type = do_not_know`
- `edge_design_family = do_not_know`
- `taxonomy_confidence = 0.5`
- `unknown_reason = missing_raw_evidence_type`

## Interpretation

This is **not mainly a design-family classification problem**.

It is mostly one of three things:

1. method nodes
2. metadata-like or broad container nodes
3. extraction / ontology artifacts that should not be treated as substantive frontier evidence objects

So the right response is **not**:

- "force these into a cleaner evidence type"

The right response is:

- recognize them as a separate method-artifact tail
- keep the evidence label unresolved when it is genuinely unresolved
- and treat them differently in audit prioritization and surfaced interpretation

## What the cleanup already achieved

The recent conservative cleanup did the right thing:

- genuinely strong pair-level dominant designs can now clear leftover ambiguity
- unresolved rows no longer keep misleading high confidence

That means the remaining method-heavy tail is more honest than before.

## What this tail is telling us

The method-heavy unresolved tail is useful diagnostically because it reveals a structural issue:

- the ontology currently allows method-centric and metadata-like nodes to accumulate very large support in some subregions

That matters for ontology and frontier interpretation, but it does **not** mean the evidence taxonomy is wrong.

## Deterministic opportunities

### 1. Add a method-artifact audit bucket

For future audit notes and unknown-evidence queues, split unresolved rows into:

- substantive unresolved edges
- method-artifact unresolved edges
- metadata/container unresolved edges

This can be done with deterministic node-label heuristics plus existing container/method flags.

### 2. Keep method-artifact rows out of substantive evidence cleanup priorities

The highest-value evidence cleanup should focus on:

- substantive pairs that still have unresolved or ambiguous evidence labels

not on:

- `MMQR`-style method clusters

### 3. Consider an explicit concept-type layer later

The broader ontology-vNext design should likely include concept-type tags such as:

- method
- data artifact
- metadata/container
- substantive mechanism
- substantive outcome

That would help separate:

- evidence attached to real relations

from:

- evidence attached to methods or generic scaffolding nodes

## What not to do

Do **not** force the method-heavy tail into:

- `theory`
- `empirics`
- or any more specific design family

unless the raw evidence signal actually supports that move.

That would make the taxonomy look cleaner while making it less truthful.

## Audit verdict

The remaining high-support unresolved method-heavy tail should be treated as:

- a **node-type / ontology / extraction-region issue**

more than:

- an evidence-taxonomy labeling problem

## Recommended next move

The next targeted action should be:

1. add a deterministic `method_artifact` review bucket for unresolved evidence audits
2. keep method-heavy unresolved rows out of substantive frontier-evidence cleanup priorities
3. revisit them later as part of concept-type tagging or ontology restructuring, not as part of ordinary evidence-taxonomy cleanup

## Bottom line

The unresolved method-heavy tail is real, but it does not mean the evidence taxonomy failed.

It mostly tells us that:

- some high-support regions of the graph are method-centric rather than substantively frontier-centric

That is a useful ontology insight, not just a cleanup nuisance.
