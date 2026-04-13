# Surfaced Shortlist Quality Review Note

## Scope

This note reviews:

- `outputs/paper/35_surfaced_shortlist_quality_review/top50_unique_shortlist_quality_review.csv`
- `outputs/paper/35_surfaced_shortlist_quality_review/summary.json`

The goal is to judge the surfaced shortlist after the residual semantics freeze and one display-only phrasing improvement.

## Main result

The display cleanup worked.

After rewriting only the path/mechanism display layer on the frozen shortlist rows:

- `top_unique_rows`: `50`
- `keep`: `25`
- `drop_or_merge`: `25`
- `light_rewrite`: `0`

The earlier recurring display issue:

- `awkward_path_phrase`

is no longer active in the top-50 review pack.

## What now looks like the main remaining problem

The shortlist is no longer mainly suffering from clunky phrasing.

The main remaining issue is:

- `redundant_pair`

Current counts:

- `redundant_pair`: `25`

That means the next shortlist-quality gain is more about:

- semantic redundancy
- repeated endpoint families
- and example curation

than about wording.

## Best paper-facing examples right now

Strong examples to keep in the paper-facing example set:

- baseline path/mechanism: `price changes -> CO2 emissions`
- context-transfer overlay: `financial development -> green innovation`
- evidence-type-expansion overlay: `willingness to pay -> CO2 emissions`
- family-aware comparison: `state of the business cycle -> house prices`

## Rows to suppress from headline examples

These are readable enough, but they should not be headline examples because they mainly reflect redundancy pressure:

- `income tax rate -> CO2 emissions`
- `regional heterogeneity -> CO2 emissions`
- `income tax rate -> environmental quality`
- `state of the business cycle -> willingness to pay`
- `environmental regulation -> sustainable development`

## Current judgment

The surfaced shortlist is now good enough to support paper consolidation.

The next shortlist pass, if we do one, should be:

- redundancy-aware
- example-focused
- and explicitly separate “good but crowded” from “actually weak”

not another broad wording pass
