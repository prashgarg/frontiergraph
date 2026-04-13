# Open-World Grounding Decisions v2

This note records the key design choices in the first open-world grounding pass.

## Why the mapping is no longer binary
- low-similarity labels can still represent real economics concepts
- broader grounding is often better than deletion
- unresolved-but-real labels must stay in the graph to avoid fake novelty

## Threshold bands
- `>= 0.85`: linked
- `0.75–0.85`: soft
- `0.65–0.75`: candidate
- `0.50–0.65`: rescue
- `< 0.50`: unresolved

## First-pass implementation choice
- clustering backend: `tfidf_char_fallback`
- clustering universe mode: `audit_top_truncated`
- the base v2 ontology remains unchanged
- enrichment is expressed as overlays and concept-family proposals

## Current examples surfaced by the audit
- `female sex` -> issue `missing_alias` | rank-1 `Sex manual` | proposal `Female`
- `financial frictions` -> issue `missing_concept_family` | rank-1 `Financial toxicity` | proposal `add_alias_to_existing`
- `search frictions` -> issue `broader_concept_available` | rank-1 `Phriction` | proposal `Search`
- `credit constraints` -> issue `broader_concept_available` | rank-1 `Credit Crunch` | proposal `Credit`
- `information frictions` -> issue `broader_concept_available` | rank-1 `Information asymmetry` | proposal `Information`
- `economic policy uncertainty (epu) index` -> issue `broader_concept_available` | rank-1 `Knowledge Economic Index` | proposal `Economic policy`
- `unobserved heterogeneity` -> issue `missing_concept_family` | rank-1 `Spatial heterogeneity` | proposal `keep_unresolved`

## Sensitivity takeaway
- threshold `0.85`: threshold-attached occurrences `241,435`, overlay-attached occurrences `374,954`
- threshold `0.75`: threshold-attached occurrences `553,015`, overlay-attached occurrences `686,534`
- threshold `0.65`: threshold-attached occurrences `1,181,683`, overlay-attached occurrences `1,198,386`
- threshold `0.50`: threshold-attached occurrences `1,752,777`, overlay-attached occurrences `1,752,841`
