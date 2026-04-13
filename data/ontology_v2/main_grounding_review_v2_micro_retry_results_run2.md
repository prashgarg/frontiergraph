# Micro Retry Grounding Review Results run2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `8`
- batches: `8`
- prompt tokens: `4,048`
- completion tokens: `1,431`

## Decisions
- `promote_new_concept_family`: `4`
- `accept_existing_broad`: `3`
- `accept_existing_alias`: `1`

## Confidence
- `high`: `4`
- `medium`: `4`

## Sample rows

| review_item_type   | label                     | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label   | confidence   | reason                                                                                                                  |
|:-------------------|:--------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------------|
| row                | time-varying risk premium | candidate              | missing_concept_family      | promote_new_concept_family |                          | time-varying risk premium  | high         | This is a valid finance concept and broader than the listed aliases, so it should be added as a new family.             |
| row                | fiscal discipline         | candidate              | missing_alias               | promote_new_concept_family |                          | fiscal discipline          | high         | This is a valid fiscal policy concept, but the suggested ontology match is too political and not an exact alias.        |
| row                | economic outcomes         | candidate              | broader_concept_available   | accept_existing_broad      | economic impact          |                            | medium       | Economic outcomes is a valid broader label, and economic impact is the closest existing ontology concept.               |
| row                | tourist arrivals          | candidate              | broader_concept_available   | accept_existing_broad      | Tourism                  |                            | medium       | Tourist arrivals are a standard tourism-demand measure and fit the broader tourism concept.                             |
| row                | forest area               | candidate              | missing_alias               | accept_existing_broad      | Forest cover             |                            | medium       | Forest area is commonly used as a broad land-cover measure and fits forest cover better than the proposed alternatives. |
| row                | revenues                  | rescue                 | unclear                     | accept_existing_alias      | Revenue                  |                            | high         | Plural surface form clearly refers to the existing Revenue concept.                                                     |
| row                | export intensity          | rescue                 | missing_alias               | promote_new_concept_family |                          | export intensity           | high         | This is a valid economics research concept, but the provided ontology candidates are unrelated intensity measures.      |
| row                | global economic activity  | candidate              | missing_alias               | promote_new_concept_family |                          | Global economic activity   | medium       | The label is a valid economics concept, but the nearest ontology candidates are related rather than exact matches.      |
