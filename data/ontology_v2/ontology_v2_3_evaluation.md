# Ontology v2.3 Evaluation

- ontology rows: `154,359`
- display-label changes: `602`
- ambiguous containers: `4`
- allowed roots: `22`
- duplicate merges applied: `2`
- promoted intermediate groups: `0`
- promoted child rows: `0`
- effective-parent coverage: `13,820`
- cycle count in effective hierarchy: `0`

## Source mix
- `frontiergraph_v2_1_reviewed_family`: `767`
- `frontiergraph_v2_2_guardrailed_child_family`: `29`
- `jel`: `5,001`
- `openalex_keyword`: `9,271`
- `openalex_topic`: `1,876`
- `wikidata`: `8,383`
- `wikipedia`: `129,032`

## Remaining too-broad backlog
- `broad_root_acceptable`: `77`
- `dirty_parent_zone`: `247`
- `missing_standard_intermediate`: `124`
- `unresolved_holdout`: `279`

## Manual spot checks
- formatting-only cleanup: `Environment.` -> `Environment`
- source-backed cleanup: `Willingness to Pay.` -> `Willingness to pay`
- true duplicate merge: `Aureus³` -> `aureus`
- held-out non-merge: `Welfare Economics.` vs `Welfare Economics.`
- promoted intermediate: none met the conservative promotion bar
- rejected intermediate candidate: `economics` -> `economic collapse`

## Freeze decision
- freeze ready: `true`

### Checks
- `raw_provenance_preserved`: `true`
- `no_new_hierarchy_cycles`: `true`
- `display_changes_have_explicit_basis`: `true`
- `duplicate_merges_have_strict_evidence`: `true`
- `promoted_intermediates_have_review_evidence`: `true`
- `unresolved_backlog_is_explicitly_parked`: `true`
- `ontology_decisions_do_not_depend_on_ranker_gains`: `true`
