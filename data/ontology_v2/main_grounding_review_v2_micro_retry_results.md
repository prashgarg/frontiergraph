# Micro Retry Grounding Review Results run1

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `16`
- batches: `16`
- prompt tokens: `8,146`
- completion tokens: `2,822`

## Decisions
- `promote_new_concept_family`: `11`
- `accept_existing_broad`: `5`

## Confidence
- `medium`: `8`
- `high`: `8`

## Sample rows

| review_item_type   | label                         | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label   | confidence   | reason                                                                                                               |
|:-------------------|:------------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------|:-------------|:---------------------------------------------------------------------------------------------------------------------|
| row                | long-term contracts           | rescue                 | missing_alias               | promote_new_concept_family |                          | long-term contracts        | medium       | The label is economically meaningful, but the suggested finance matches are incorrect and too specific.              |
| row                | incomes                       | candidate              | unclear                     | promote_new_concept_family |                          | income                     | high         | Plural income is a valid economics variable, but the listed ontology candidates are not the right attachment.        |
| row                | increased competition         | rescue                 | broader_concept_available   | accept_existing_broad      | Competition              |                            | high         | The label denotes a broader competition condition and fits the existing Competition concept well.                    |
| row                | skill-biased technical change | rescue                 | broader_concept_available   | accept_existing_broad      | Technical change         |                            | high         | The label is a specific subtype of technical change, so the broader ontology concept is appropriate.                 |
| row                | pattern of trade              | candidate              | broader_concept_available   | promote_new_concept_family |                          | pattern of trade           | medium       | The label is a valid economics concept but the proposed trade-specific matches are too narrow and not a clean alias. |
| row                | equilibrium allocation        | candidate              | broader_concept_available   | accept_existing_broad      | Equilibrium              |                            | medium       | The label is a valid economics concept and maps reasonably to the broader ontology concept Equilibrium.              |
| row                | optimal fiscal policy         | candidate              | broader_concept_available   | accept_existing_broad      | Fiscal Policy            |                            | high         | The label is a broader fiscal-policy concept, and the ontology already has an appropriate existing target.           |
| row                | market dynamics               | candidate              | missing_concept_family      | promote_new_concept_family |                          | market dynamics            | high         | Economically meaningful label missing from ontology; existing candidates are too broad and not equivalent.           |
| row                | endogenous prices             | rescue                 | broader_concept_available   | promote_new_concept_family |                          | endogenous prices          | high         | This is a valid economics concept and the suggested ontology matches are too generic or off-target.                  |
| row                | spatial factors               | rescue                 | missing_alias               | promote_new_concept_family |                          | spatial factors            | medium       | The label is valid and economically relevant, but the suggested ontology matches are unrelated surface neighbors.    |
| row                | disaggregated data            | rescue                 | missing_alias               | promote_new_concept_family |                          | disaggregated data         | medium       | This is a valid research label but not a clean alias of aggregate data or microdata.                                 |
| row                | earned income                 | candidate              | missing_alias               | promote_new_concept_family |                          | earned income              | high         | Earned income is a valid economics label and not the same as real or disposable income.                              |
