# Policy Outcome Or Boundary Manual Review

## Scope

This note reviews the current top of the `policy_outcome_or_boundary` slice inside the `substantive_unresolved` queue after the event / institution / context typing refinement.

The goal is to decide what kind of unresolved work remains at the top once obvious event-context and institution-context entanglements are peeled away.

## Main result

The top of the queue is now meaningfully cleaner.

For the current top reviewed rows, both endpoints are now typed as:

- `source_context_entity_type = none`
- `target_context_entity_type = none`

That is an important improvement.
It means the event / institution / geography typing pass is doing useful separation work before we even make substantive judgments about the rows themselves.

## What now sits at the top

Representative current top rows include:

- `CO2 emissions -> Kyoto Protocol`
- `CO2 emissions -> policy recommendations`
- `green innovation -> digital transformation`
- `Kyoto Protocol -> emissions reduction`
- `environmental quality -> environmental policies`
- `environmental quality -> Kyoto Protocol`
- `National Institute for Health and Clinical Excellence (NICE) -> clinical practice guidelines`
- `policy -> drug prices`
- `quality of care -> health care delivery`
- `price changes -> policy`
- `health technology assessment (HTA) -> access to medicines`
- `energy efficiency -> energy efficiency improvements`
- `drug prices -> option price`
- `emissions -> local air quality`
- `housing stock -> income tax rate`
- `permit prices -> auctioning`

## Judgment by subtype

### 1. Strong substantive frontier candidates

These look like real policy or outcome objects that may deserve later direct review as edge objects or typed evidence problems:

- `CO2 emissions -> Kyoto Protocol`
- `environmental quality -> environmental policies`
- `Kyoto Protocol -> emissions reduction`
- `quality of care -> health care delivery`
- `health technology assessment (HTA) -> access to medicines`
- `emissions -> local air quality`

These are not all equally strong paper-facing objects, but they look like real substantive unresolved relations rather than pure ontology debris.

### 2. Policy-boundary or near-duplicate cases

These still look more like ontology-boundary or granularity problems than novel frontier objects:

- `energy efficiency -> energy efficiency improvements`
- `policy -> drug prices`
- `price changes -> policy`
- `green innovation -> digital transformation`

The issue here is usually one of:

- generic endpoint overbreadth
- closely adjacent concepts that want clearer family or boundary treatment
- or a concept pair that mixes object level and policy framing

### 3. Regime / instrument / implementation bundles

These look substantive, but they also bundle policy regimes, implementation choices, or applied governance objects together:

- `CO2 emissions -> policy recommendations`
- `permit prices -> auctioning`
- `environmental quality -> Kyoto Protocol`
- `National Institute for Health and Clinical Excellence (NICE) -> clinical practice guidelines`

These are useful to keep in the review queue, but they likely want more structured edge typing before they become strong surfaced objects.

### 4. Weak or awkward current objects

Some rows still read weakly even after the typing refinement:

- `drug prices -> option price`
- `housing stock -> income tax rate`

These are the kinds of rows that still look like mixed-domain spillovers, generic bundle effects, or unresolved boundary noise.

## What changed because of the context-entity pass

Before the latest pass, the broader substantive queue still mixed:

- genuine policy/outcome unresolved pairs
- event-context rows
- institution or actor entanglements
- geography-bearing context objects

After the refinement, the top policy slice is much more concentrated in true policy/outcome/boundary rows.

That does not make every row good.
But it does mean the queue is now reviewable for the right reason.

## Current interpretation

The top of `policy_outcome_or_boundary` is now a useful next audit surface.

It is not one homogeneous thing.
It contains at least three distinguishable problems:

1. real substantive unresolved policy or outcome relations
2. ontology-boundary or near-duplicate concept relations
3. policy regime / implementation bundles that want richer edge typing

That is already a meaningful improvement over the earlier single unresolved mass.

## Recommendation

The next manual audit inside the unresolved tail should keep focusing here.

Priority order within this slice should be:

1. environment and energy policy/outcome rows
2. health policy / implementation rows
3. boundary and near-duplicate rows
4. awkward mixed-domain leftovers

The main practical lesson is:

- the context-entity pass helped
- the active reviewed family set should stay unchanged for now
- and the next gains are more likely to come from better boundary handling and richer edge typing than from adding more broad families immediately
