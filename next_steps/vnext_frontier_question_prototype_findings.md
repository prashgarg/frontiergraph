# vNext Frontier Question Prototype Findings

## What was built

We generated four deterministic frontier question families on top of the enriched shortlist:

- family-aware questions
- context-transfer questions
- missing empirical confirmation questions
- evidence-type expansion questions

These are interpretive overlays only. They do not rerank the active frontier.

## Prototype coverage

- `family_aware` rows: `25`
- `context_transfer` rows: `25`
- `missing_empirical_confirmation` rows: `24`
- `evidence_type_expansion` rows: `25`

## First read

The layered overlay is already rich enough to support new frontier objects.

Most promising prototype families on first pass:
- context-transfer questions look strongest as a direct use of node context
- evidence-type expansion questions look strongest as a direct use of edge evidence
- missing empirical confirmation questions also look good, especially for theory-heavy macro/public-finance style links
- family-aware questions are more credible once reviewed families go beyond the environmental family, but they still depend heavily on comparator phrasing

What looks most useful conceptually:
- family-aware questions help when related outcomes should stay separate but clearly belong together
- context-transfer questions turn context metadata into a substantive frontier object
- missing empirical confirmation questions make theory-heavy links legible as empirical opportunities
- evidence-type expansion questions make the edge-evidence layer matter, not just the node layer

## Practical next step

The next step should be a review pass over these prototypes to decide which of the four families belong in the paper and which should remain internal tools.
If one or two families look clearly stronger, we can then build a second-generation prototype that scores those objects directly rather than only deriving them from the existing shortlist.
