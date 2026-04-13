# Policy Outcome Or Boundary Deep Review

## Scope

This note reviews the top `25` rows from:

- `outputs/paper/31_substantive_unresolved_review/policy_outcome_or_boundary_top.csv`

The goal is to decide what the top of the `policy_outcome_or_boundary` queue now actually contains after:

- dictionary-backed context typing
- stronger substantive-unresolved subtyping
- and the dedicated review-pack build

## Main result

The queue is now strong enough to review directly.

Manual labels for the top `25` rows split as:

- `strong_substantive`: `14`
- `boundary_or_near_duplicate`: `5`
- `regime_or_implementation_bundle`: `3`
- `weak_or_mixed`: `3`

That is a good outcome.
The queue is no longer dominated by context noise, and it is no longer one undifferentiated mass.

## Strongest next substantive candidates

The best next substantive review targets are:

- `CO2 emissions -> environmental quality`
- `CO2 emissions -> energy efficiency`
- `house prices -> housing stock`
- `inflation -> unemployment`
- `unemployment -> wages`
- `economic growth -> inflation`
- `drug prices -> Generic drugs`
- `drug prices -> access to medicines`
- `tax evasion -> income tax rate`
- `CO2 emissions -> coal`
- `CO2 emissions -> clean energy`
- `CO2 emissions -> fossil fuel use`
- `water quality -> land use`
- `consumption -> income distribution`

These are the rows that now look most worth prioritizing if we want a next substantive unresolved-edge audit.

They are not all equally paper-ready, but they are the clearest candidates for:

- richer edge typing
- direct substantive review
- or later promotion into a dedicated internal frontier-object family

## Boundary or near-duplicate cases

These rows still look more like ontology-boundary or granularity problems than genuinely new edge objects:

- `taxes -> income tax rate`
- `business cycle -> state of the business cycle`
- `prices -> price changes`
- `income inequality -> income distribution`
- `CO2 emissions -> global carbon emissions`

These should stay in the ontology-boundary cleanup queue, not the substantive frontier queue.

## Regime or implementation bundles

These rows look meaningful, but the main next need is richer edge typing rather than immediate surfacing:

- `CO2 emissions -> carbon neutrality target`
- `CO2 emissions -> Intended Nationally Determined Contributions (INDCs)`
- `CO2 emissions -> international emissions trading`

These are best understood as policy-regime / implementation bundles.
They are useful, but they want more structured edge semantics before they become strong surfaced objects.

## Weak or mixed current rows

These are the rows that still look too broad or mixed to treat as high-value next objects:

- `CO2 emissions -> energy`
- `price changes -> drug prices`
- `CO2 emissions -> global climate change`

They are not necessarily wrong.
They are just weaker next-review targets than the stronger substantive rows above.

## What the dictionary-backed typing changed

The context typing pass helped materially here.

The top policy rows now remain concentrated in:

- `none -> none`

for `source_context_entity_type -> target_context_entity_type`.

That means named geographies and other context-bearing labels are no longer leaking into this queue as much as before.

So the current top policy slice is cleaner for the right reason:

- it contains substantive policy/outcome relations
- ontology-boundary pairs
- and regime-bundle rows

not just mixed context artifacts.

## Recommendation

The next substantive unresolved-edge audit should start from the `strong_substantive` rows above.

Priority order should be:

1. environment and energy rows
2. macro and labor rows
3. health / pharmaceutical access rows
4. boundary cases
5. regime-bundle rows that want richer edge typing

The practical takeaway is:

- this queue is now worth taking seriously
- but only part of it should be treated as the next substantive frontier surface
