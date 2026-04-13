# Regime Implementation Edge Typing Note

## Scope

This note reviews:

- `outputs/paper/32_strong_substantive_regime_review/regime_bundle_typed.csv`

The goal is to test whether a small coarse internal schema is enough to organize the current regime / implementation bundle rows.

## Main result

Yes.
The current coarse schema is already doing useful work.

Current counts are:

- `regime_bundle_rows`: `3`
- `policy_target`: `2`
- `policy_instrument`: `1`

There were no `unclassified` rows in the current regime bundle set.

That is a strong outcome for a first coarse pass.

## Current classifications

The three current rows classify as:

- `CO2 emissions -> carbon neutrality target` -> `policy_target`
- `CO2 emissions -> Intended Nationally Determined Contributions (INDCs)` -> `policy_target`
- `CO2 emissions -> international emissions trading` -> `policy_instrument`

All three classify from the target label at confidence `1.0`.

That is exactly the behavior we wanted from this pass.

## What this means

The regime/implementation rows were not mainly blocked by ontology-family structure.
They were blocked by missing edge semantics.

The coarse schema is already enough to distinguish:

- target-like policy objects
- instrument-like policy objects

without needing a larger redesign first.

## Current judgment

Keep this schema internal for now.

Do not route or rank on it yet.

But it is now strong enough to serve as a design seed for a later edge-semantics layer inside ontology-vNext.

## Recommendation

The next useful move is to extend this same coarse schema to a somewhat broader regime-bundle queue, not just the top three manually reviewed rows.

That will tell us whether the clean current result is:

- a real reusable pattern
- or just a success on a very small set

## Stability note

This pass did not change:

- ranking
- routed shortlist counts
- reviewed family membership

It only improved the internal interpretation layer.
