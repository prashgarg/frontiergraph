# Remaining-Heuristic No-Majority Results run8

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `134,549`

## Decisions
- `promote_new_concept_family`: `487`
- `accept_existing_broad`: `165`
- `keep_unresolved`: `40`
- `accept_existing_alias`: `37`
- `reject_match_keep_raw`: `9`

## Confidence
- `medium`: `422`
- `high`: `281`
- `low`: `35`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label                         | confidence   | reason                                                                                                                           |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:-------------------------------------------------|:-------------|:---------------------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                                     | medium       | Valid economics label, but the proposed ontology matches are too broad or off-target.                                            |
| row                | chartists                               | candidate              | unclear                     | promote_new_concept_family |                              | chartists (technical traders/technical analysts) | medium       | Economically relevant trading-term; existing candidates are about historical movements or occupations, not market chartists.     |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | accept_existing_broad      | Realized variance            |                                                  | medium       | Realized volatility is closely related to realized variance and can be grounded as the broader existing concept.                 |
| row                | us data                                 | rescue                 | broader_concept_available   | promote_new_concept_family |                              | United States data                               | high         | This is a valid empirical context label, but USDA is the wrong ontology target.                                                  |
| row                | var model                               | candidate              | broader_concept_available   | promote_new_concept_family |                              | VAR model                                        | medium       | Likely refers to vector autoregression, a valid econometric method not matched by the proposed ontology labels.                  |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity                          | high         | This is a valid economics research concept, but the proposed broader match is not the same as household-level heterogeneity.     |
| row                | model results                           | candidate              | broader_concept_available   | promote_new_concept_family |                              | model results                                    | medium       | Valid research label, but no ontology candidate matches this generic results concept.                                            |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | accept_existing_broad      | War                          |                                                  | medium       | The label refers to a specific war event, and War is the appropriate broader ontology concept.                                   |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                                                  | medium       | The label is a valid energy-use variable, and the ontology’s broader energy consumption concept is an acceptable generalization. |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks                               | high         | This is a valid economics research label, but it is broader and distinct from the proposed extreme weather match.                |
| row                | endowments                              | candidate              | unclear                     | accept_existing_alias      | Endowment                    |                                                  | medium       | Plural ‘endowments’ is a surface-form variant of the existing Endowment concept.                                                 |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents                      | medium       | This is a valid specific patent category, but the proposed ontology targets are too broad or mismatched.                         |

## Run details

- run label: `run8`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
