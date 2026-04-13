# Broader Regime Queue Review Note

## Scope

This note reviews:

- `outputs/paper/33_policy_edge_typing_review/broader_regime_bundle_typed.csv`

The goal is to test whether the coarse regime schema still works once we move beyond the three manually labeled regime rows and apply it to the broader regime-like queue.

## Main result

Yes, mostly.

Current counts are:

- `broader_regime_like_rows`: `11`

Semantic-type split:

- `policy_instrument`: `7`
- `policy_target`: `2`
- `governance_regime`: `2`

Queue-status split:

- `clean_policy_semantic`: `9`
- `generic_policy_object`: `1`
- `mixed_boundary_case`: `1`

That is a good result.
The coarse schema generalizes better than the earlier top-three-only check suggested.

## What held up well

The following rows still look clean under the broader pass:

- `CO2 emissions -> international emissions trading` -> `policy_instrument`
- `CO2 emissions -> Emission Trading Scheme (ETS)` -> `policy_instrument`
- `tax revenues -> income tax rate` -> `policy_instrument`
- `tax rates -> income tax rate` -> `policy_instrument`
- `income tax rate -> capital income taxes` -> `policy_instrument`
- `CO2 emissions -> carbon neutrality target` -> `policy_target`
- `CO2 emissions -> Intended Nationally Determined Contributions (INDCs)` -> `policy_target`
- `monetary policy -> state of the business cycle` -> `governance_regime`

That means the coarse schema is not just working on the easiest three examples.

## Where the broader queue shows stress

Two rows now clearly show the limits of the current broad regime-like selection:

### Generic policy object

- `CO2 emissions -> policy`

This is not a failure of the edge-semantics schema.
It is a failure of the regime-like queue itself being a bit too permissive.

### Mixed boundary case

- `taxes -> income tax rate`

This row classifies as an instrument-like object, but it is still mainly an ontology-boundary case rather than a clean policy edge.

## Current judgment

The coarse regime schema is worth keeping.

The thing that now wants refinement is not the schema first.
It is the **queue selection rule** for broader regime-like rows.

## Recommendation

The next useful move is:

1. keep the coarse regime schema
2. tighten the broader regime-like queue so generic rows such as `target = policy` drop out earlier
3. keep boundary rows like `taxes -> income tax rate` separated from cleaner regime rows

So the broader pass tells us:

- the schema generalizes
- but the queue still needs a light genericity / boundary guardrail
