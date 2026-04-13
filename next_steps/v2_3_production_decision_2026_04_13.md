# v2.3 production decision

Date: 2026-04-13

## Decision

Use the `v2.3` frozen baseline as the production ontology baseline for the next
rebuild.

This means:

- the current paper-facing ontology is the canonical baseline
- the current grounding thresholds remain unchanged unless a concrete failure is found
- unmatched tail labels stay unresolved by default
- no further hierarchy promotions are made unless a concrete ontology error is identified

## Why

The current paper already describes a conservative open-world ontology regime:

- exact grounding first
- embedding retrieval after that
- explicit confidence bands
- reviewed broader attachment where justified
- unresolved labels preserved rather than silently dropped
- reviewed hierarchy overlays with conservative duplicate handling

That regime is already consistent with the `v2.3` freeze notes and the current
paper counts. Reopening thresholds or hierarchy policy now would add instability
without a clearly identified empirical failure.

## Operational rule

Treat `v2.3` as fixed support infrastructure for the next rebuild. The next
method phase should focus on:

- candidate generation
- ranking
- concentration control
- evaluation design
- paper-facing object construction

and not on another broad ontology redesign.

## Exception rule

Only reopen the ontology if one of the following is true:

- a clearly wrong high-frequency grounding is identified
- a forced parent-child relation creates repeated substantive distortion
- an unresolved label cluster is both semantically coherent and important enough
  to justify promotion into a new concept family

Absent one of those cases, leave the ontology unchanged.
