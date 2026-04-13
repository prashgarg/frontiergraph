# Environmental Boundary Audit for Conservative Patch v2

## Purpose

This note fixes the conservative interpretation of the environmental outcome family for patch `v2`.

The goal is not to redesign the ontology yet. The goal is to make one explicit boundary rule that we can rerun and defend:

- keep the main environmental outcome nodes **separate**
- treat a smaller set of adjacent labels as **mechanism-like**
- avoid risky merges that would make the current frontier cleaner at the cost of semantic structure

## Canonical endpoint / outcome nodes

These remain separate canonical nodes in patch `v2`:

- `FG3C000081` = `environmental quality`
- `FG3C000203` = `environmental pollution`
- `FG3C000130` = `environmental degradation`
- `FG3C000003` = `CO2 emissions`
- `FG3C000064` = `ecological footprint`

These are not treated as synonyms in `v2`.

## Why they stay separate

### `environmental quality`

Interpretation:
- umbrella or broad outcome construct
- often used as a higher-level environmental state variable

Why not merge:
- broader than emissions
- broader than ecological footprint
- not interchangeable with pollution or degradation in many papers

### `environmental pollution`

Interpretation:
- pollution-focused outcome bucket
- often closer to direct pollutant burden than to broad “quality”

Why not merge:
- more specific than `environmental quality`
- not always equivalent to degradation or CO2 emissions

### `environmental degradation`

Interpretation:
- damage / deterioration framing
- often used as a broader harm concept

Why not merge:
- overlaps with pollution and emissions, but not identical
- often appears as a degradation narrative rather than a measured pollutant variable

### `CO2 emissions`

Interpretation:
- concrete emissions outcome

Why not merge:
- much narrower and more measurable than the umbrella constructs above
- already central enough; merging more mass into it would likely distort the surfaced frontier further

### `ecological footprint`

Interpretation:
- environmental pressure / sustainability outcome

Why not merge:
- related to emissions and environmental quality, but not the same object
- often behaves like a sibling outcome rather than a synonym

## Adjacent mechanism-like labels

These are not treated as endpoint synonyms. They are better interpreted as mechanism-like or theory-like adjacent labels:

- `pollution abatement`
- `environmental taxes`
- `environmental governance`
- `Environmental Kuznets Curve (EKC) hypothesis`

These can appear in explanations or path renderings, but they should not be used as justification for collapsing the endpoint family.

## Observed support in the patched corpus

From the `v2` boundary family report:

- `CO2 emissions`: `16,190` rows, `5,927` unique papers
- `environmental quality`: `4,694` rows, `2,265` unique papers
- `ecological footprint`: `2,351` rows, `606` unique papers
- `environmental pollution`: `1,642` rows, `810` unique papers
- `environmental degradation`: `1,086` rows, `400` unique papers

Mechanism-like adjacent labels:

- `pollution abatement`: `90` rows, `55` unique papers
- `environmental taxes`: `307` rows, `162` unique papers
- `environmental governance`: `157` rows, `97` unique papers
- `Environmental Kuznets Curve (EKC) hypothesis`: `241` rows, `207` unique papers

This is enough support to treat the family seriously, but not enough evidence to justify aggressive merging.

## Locked rule for patch v2

Patch `v2` is allowed to:

- normalize labels inside this family
- resolve raw code labels to readable canonical labels
- clean explanation aliases around the family

Patch `v2` is **not** allowed to:

- merge `environmental quality` with `environmental pollution`
- merge `environmental quality` with `environmental degradation`
- merge `environmental pollution` with `environmental degradation`
- merge `ecological footprint` into emissions or environmental-quality nodes
- use topic-specific ranking penalties to reduce how often these nodes appear

## What this implies for vNext

This boundary audit is one of the clearest signals that the next ontology should distinguish:

- synonym
- broader / narrower
- related
- do-not-merge

In other words, this family is a strong example of why the next ontology should be layered rather than forced into a single canonical layer.
