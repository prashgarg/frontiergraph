# Direct-Scored vNext Frontier Object Findings

## What we did

We built direct scorers for the two strongest ontology-vNext question families:

- context-transfer
- evidence-type expansion

Unlike the first prototype pass, these objects are scored directly from family/context/evidence fields and collapsed across horizons to avoid duplicate `h=5`/`h=10` entries.

## Coverage

- context-transfer shortlist after direct scoring: `25`
- evidence-type-expansion shortlist after direct scoring: `25`

## First read

This is a better object than the first prototype pass because it stops repeating the same pair twice and forces the ontology-vNext fields to do real work in the score.

Current read:
- context-transfer remains the strongest new object family
- evidence-type expansion also looks strong and is easier to explain cleanly in methodological terms
- these two object families now look mature enough for a paper-facing methodology discussion, even if they remain internal-only for now

## Next step

The next step should be a human review pass comparing these direct-scored vNext objects against the current path/mechanism shortlist, asking which ones are genuinely better research objects and which are just better metadata.
If that review is favorable, the natural next move is a paper note and then a ranking experiment that mixes these richer object scores with the existing frontier retrieval system.
