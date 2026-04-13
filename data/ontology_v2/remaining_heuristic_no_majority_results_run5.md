# Remaining-Heuristic No-Majority Results run5

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `134,758`

## Decisions
- `promote_new_concept_family`: `462`
- `accept_existing_broad`: `185`
- `keep_unresolved`: `43`
- `accept_existing_alias`: `35`
- `reject_match_keep_raw`: `11`
- `unclear`: `2`

## Confidence
- `medium`: `439`
- `high`: `263`
- `low`: `36`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label               | confidence   | reason                                                                                                                               |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:---------------------------------------|:-------------|:-------------------------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | accept_existing_broad      | Market impact                |                                        | medium       | Price impact is a valid research label, and market impact is a broader economically meaningful ontology target.                      |
| row                | chartists                               | candidate              | unclear                     | promote_new_concept_family |                              | chartists (technical-analysis traders) | medium       | The ontology candidates miss the finance meaning commonly used in economics papers.                                                  |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | accept_existing_broad      | Realized variance            |                                        | high         | Realized volatility is a standard broader volatility measure closely aligned with realized variance.                                 |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_broad      | United States                |                                        | medium       | The label refers broadly to U.S.-based data, which is a meaningful geographic context in economics research.                         |
| row                | var model                               | candidate              | broader_concept_available   | promote_new_concept_family |                              | VAR model                              | medium       | This is a valid econometric method label, but the proposed ontology match is too generic and not clearly the right concept.          |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity                | high         | This is a valid research concept, but neither Study heterogeneity nor Household Economics is the right ontology target.              |
| row                | model results                           | candidate              | broader_concept_available   | promote_new_concept_family |                              | model results                          | medium       | The label is a valid generic research-output concept, but the suggested ontology matches are too specific.                           |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | accept_existing_broad      | War                          |                                        | medium       | The label refers to a specific war event, and the ontology’s broader war concept is an acceptable grounding.                         |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                                        | medium       | The label is a narrower energy-consumption variant, and aggregate energy consumption is the closest usable broader ontology concept. |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks                     | high         | This is a valid economics/climate exposure label, but it is broader than the suggested extreme weather match.                        |
| row                | endowments                              | candidate              | unclear                     | promote_new_concept_family |                              | economic endowments                    | medium       | The label is economically meaningful, but the proposed ontology matches point to the wrong kind of endowment.                        |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents            | medium       | This is a valid, specific patent-category label, but the proposed ontology match is not the right concept.                           |

## Run details

- run label: `run5`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
