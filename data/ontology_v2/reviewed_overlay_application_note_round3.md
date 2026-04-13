# Reviewed Overlay Application Note Round 3

This pass applies the manual adjudications for the last remaining 38 tied rows from the remaining-heuristic hard-case panel.

Key rules used:
- original adjudicated row reviews still override everything else
- remaining heuristic rows with a three-run majority remain `remaining_row_majority_review`
- remaining hard-case rows now use modal or manual row-level review rather than heuristic fallback
- cluster reviews remain a separate neighborhood-level layer
- unresolved raw labels are always preserved

## Final overlay action counts
- `attach_existing_broad`: `21,725`
- `propose_new_concept_family`: `14,237`
- `add_alias_to_existing`: `2,354`
- `keep_unresolved`: `932`
- `reject_cluster`: `841`

## Decision source counts
- `remaining_row_majority_review`: `27,245`
- `row_review`: `9,566`
- `cluster_review`: `2,537`
- `remaining_hard_modal_review`: `700`
- `remaining_manual_override_review`: `38`
- `unresolved_row_review`: `3`

## Proposal counts
- `propose_new_concept_family`: `14,423`
- `keep_unresolved`: `980`

## Sensitivity snapshot
- threshold `0.85`: overlay labels `116,328`, overlay occurrences `344,463`, unique grounded concepts `16,107`
- threshold `0.75`: overlay labels `340,371`, overlay occurrences `656,043`, unique grounded concepts `24,779`
- threshold `0.65`: overlay labels `842,336`, overlay occurrences `1,192,520`, unique grounded concepts `40,091`
- threshold `0.50`: overlay labels `1,379,966`, overlay occurrences `1,752,804`, unique grounded concepts `57,640`
