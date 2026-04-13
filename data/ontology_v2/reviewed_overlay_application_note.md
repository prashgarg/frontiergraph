# Reviewed Overlay Application Note

This pass applies adjudicated grounding-review decisions back into the ontology-v2 overlay layer.

Key rules used:
- row-level reviews override cluster-level reviews
- reviewed cluster-medoid decisions propagate to labels in reviewed clusters when no row review exists
- unresolved raw labels are always preserved
- broad or alias decisions require a resolvable existing ontology target; otherwise they fall back to new-family or unresolved

## Final overlay action counts
- `attach_existing_broad`: `24,888`
- `propose_new_concept_family`: `10,891`
- `add_alias_to_existing`: `2,771`
- `keep_unresolved`: `797`
- `reject_cluster`: `742`

## Proposal counts
- `propose_new_concept_family`: `11,077`
- `keep_unresolved`: `980`

## Sensitivity snapshot
- threshold `0.85`: overlay labels `119,908`, overlay occurrences `356,890`, unique grounded concepts `17,237`
- threshold `0.75`: overlay labels `343,951`, overlay occurrences `668,470`, unique grounded concepts `25,495`
- threshold `0.65`: overlay labels `842,618`, overlay occurrences `1,194,091`, unique grounded concepts `40,162`
- threshold `0.50`: overlay labels `1,379,972`, overlay occurrences `1,752,830`, unique grounded concepts `57,640`
