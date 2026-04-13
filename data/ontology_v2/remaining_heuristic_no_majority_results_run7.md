# Remaining-Heuristic No-Majority Results run7

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `135,126`

## Decisions
- `promote_new_concept_family`: `460`
- `accept_existing_broad`: `183`
- `keep_unresolved`: `50`
- `accept_existing_alias`: `38`
- `reject_match_keep_raw`: `7`

## Confidence
- `medium`: `421`
- `high`: `279`
- `low`: `38`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label    | confidence   | reason                                                                                                                 |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:----------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                | high         | This is a valid economics outcome label, but the suggested ontology matches are not the right concept.                 |
| row                | chartists                               | candidate              | unclear                     | accept_existing_broad      | Chartism                     |                             | medium       | Chartists are the people associated with Chartism, so the broader movement concept fits better than the occupation.    |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | promote_new_concept_family |                              | realized volatility         | medium       | Realized volatility is a distinct but closely related risk measure, not a plain alias of realized variance.            |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_alias      | US-A                         |                             | high         | This is a surface-form variant for United States data, which matches the existing US-A concept.                        |
| row                | var model                               | candidate              | broader_concept_available   | accept_existing_broad      | Vector autoregression model  |                             | medium       | VAR model is a standard abbreviation for vector autoregression model, a valid econometric method.                      |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity     | high         | This is a valid economics research concept, but no listed ontology target captures it well.                            |
| row                | model results                           | candidate              | broader_concept_available   | keep_unresolved            |                              |                             | medium       | The label is too generic to force an ontology match, but it remains a valid research descriptor.                       |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | accept_existing_broad      | War                          |                             | medium       | This is a specific war event that fits the broader ontology concept War.                                               |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                             | medium       | The label is a specific energy-use measure, and the ontology’s broader energy consumption concept is a reasonable fit. |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks          | high         | This is a valid climate exposure concept and is broader than the proposed extreme weather match.                       |
| row                | endowments                              | candidate              | unclear                     | keep_unresolved            |                              |                             | medium       | The label is valid but too ambiguous to safely attach to Endowment or Financial endowment.                             |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents | high         | This is a valid innovation-policy label, but the suggested ontology matches are not the right concept.                 |

## Run details

- run label: `run7`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
