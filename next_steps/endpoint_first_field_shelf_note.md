# Endpoint-First Field Shelf Note

This note records the move from combined endpoint-plus-mediator field matching to endpoint-first field assignment with mediator fallback.

## Why this change

The earlier within-field shelf builder allowed field placement whenever a field token appeared anywhere in:

- source label
- target label
- focal mediator label

That made the shelves easy to distort through mediator text. The first shelf audit showed a non-trivial mediator-only share, which meant some shelf placement was being driven more by mechanism wording than by the endpoint object being browsed.

## New rule

Field assignment is now:

1. endpoint-first
   - use source/target endpoint matches when they exist
2. mediator fallback
   - only use mediator-only placement if endpoints give no field signal
3. otherwise `other`

The builder now also writes:

- `field_assignment_source`
- `field_endpoint_match`
- `field_mediator_match`

into the within-field package.

## Rebuild result

Rebuilt package:

- `outputs/paper/98_objective_specific_frontier_packages_endpoint_first/within_field_top100_pool2000`

Comparison versus the earlier within-field package:

- total rows fall slightly from `1800` to `1791`
- mean mediator-only placement falls from roughly `0.16` in the earlier audit to about `0.11`
- mean broad share falls modestly
- mean low-compression share falls modestly
- top-target concentration is essentially unchanged or slightly better

Macro read:

- the shelf cleanup is real
- the shelves are still not fully clean subfield browse objects
- `macro-finance` remains the noisiest shelf, with mediator-only placement still around `0.22-0.25`

## Interpretation

This is the right direction because it aligns the shelf object more closely with what a user thinks they are browsing:

- endpoints first
- mediator second

It should therefore be treated as the working default for within-field browsing unless later robustness checks show a better alternative.

## Implication for LLM screening

If we run the pairwise within-field LLM pilot, it should use the endpoint-first shelves rather than the older combined-match shelves.
