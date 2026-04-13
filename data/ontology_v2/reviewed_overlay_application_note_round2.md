# Reviewed Overlay Application Note Round 2

This pass applies the three-run GPT-5.4-mini majority decisions for the remaining heuristic row-review universe.

Key rules used:
- original adjudicated row reviews still override everything else
- remaining heuristic rows with a three-run majority now use `remaining_row_majority_review`
- cluster reviews remain a separate neighborhood-level layer
- rows with no row majority still fall back to cluster review or heuristic decisions
- unresolved raw labels are always preserved

## Final overlay action counts
- `attach_existing_broad`: `22,087`
- `propose_new_concept_family`: `13,751`
- `add_alias_to_existing`: `2,474`
- `keep_unresolved`: `942`
- `reject_cluster`: `835`

## Decision source counts
- `remaining_row_majority_review`: `27,245`
- `row_review`: `9,566`
- `cluster_review`: `2,537`
- `heuristic`: `738`
- `unresolved_row_review`: `3`

## Proposal counts
- `propose_new_concept_family`: `13,937`
- `keep_unresolved`: `980`

## Sensitivity snapshot
- threshold `0.85`: overlay labels `116,810`, overlay occurrences `345,958`, unique grounded concepts `16,235`
- threshold `0.75`: overlay labels `340,853`, overlay occurrences `657,538`, unique grounded concepts `24,862`
- threshold `0.65`: overlay labels `842,368`, overlay occurrences `1,192,675`, unique grounded concepts `40,099`
- threshold `0.50`: overlay labels `1,379,967`, overlay occurrences `1,752,809`, unique grounded concepts `57,640`
