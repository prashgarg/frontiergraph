# Final Hard-Case Adjudication

- Former no-majority set size: `352`
- Resolved by modal vote: `350`
- Resolved by manual override: `2`

## Manual Adjudications

### `socioeconomic conditions` (`gr_03780_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Socioeconomics`
- Reason:
This phrase functions as a broad socioeconomic context label rather than a distinct missing concept family. It is too broad to justify a new family and not exact enough to force aliasing, so broad grounding is the safest fit.

### `ramsey pricing` (`gr_04350_row`)
- Final decision: `promote_new_concept_family`
- New concept family: `Ramsey pricing`
- Reason:
Ramsey pricing is a real economics concept in regulated pricing and public finance. It is semantically related to Ramsey-rule reasoning, but it is not simply an alias of `Ramsey Rule`, so a new-family promotion is cleaner.

## Hard-Case Decision Counts
- `promote_new_concept_family`: `248`
- `reject_match_keep_raw`: `47`
- `accept_existing_broad`: `28`
- `accept_existing_alias`: `18`
- `keep_unresolved`: `11`
