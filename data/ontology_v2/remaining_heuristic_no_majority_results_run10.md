# Remaining-Heuristic No-Majority Results run10

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `132,841`

## Decisions
- `promote_new_concept_family`: `469`
- `accept_existing_broad`: `170`
- `keep_unresolved`: `44`
- `accept_existing_alias`: `40`
- `reject_match_keep_raw`: `14`
- `unclear`: `1`

## Confidence
- `medium`: `427`
- `high`: `287`
- `low`: `24`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label             | confidence   | reason                                                                                                                                  |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:-------------------------------------|:-------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                         | medium       | The label is a valid economics concept, but the suggested ontology matches are too specific or off-target.                              |
| row                | chartists                               | candidate              | unclear                     | promote_new_concept_family |                              | chartists (financial market traders) | medium       | In economics papers, chartists usually means traders using charts, not the Chartism movement or the occupation.                         |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | promote_new_concept_family |                              | realized volatility (RV)             | high         | This is a valid distinct finance measure and should not be forced into realized variance.                                               |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_broad      | United States                |                                      | high         | The label refers to US-based data, so the broader geographic concept United States is the best fit.                                     |
| row                | var model                               | candidate              | broader_concept_available   | keep_unresolved            |                              |                                      | medium       | Abbreviated label is ambiguous and the suggested ontology matches are not reliable.                                                     |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity              | high         | This is a valid research concept, but the suggested ontology targets are not the right grounding.                                       |
| row                | model results                           | candidate              | broader_concept_available   | promote_new_concept_family |                              | model results                        | medium       | The label is valid but too generic for the suggested ontology matches, so it should be added as its own concept family.                 |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | promote_new_concept_family |                              | Russian invasion of Ukraine          | high         | This is a valid event label, but the ontology candidates are too broad or incorrect.                                                    |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                                      | medium       | The ontology target is a reasonable broader umbrella for this energy-use variable, though it is less specific than the extracted label. |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks                   | medium       | Valid climate exposure label; broader ontology match is too generic and no exact concept is given.                                      |
| row                | endowments                              | candidate              | unclear                     | keep_unresolved            |                              |                                      | high         | The label is economically valid but too ambiguous to force a specific ontology match.                                                   |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents          | medium       | This is a valid research label, but the proposed ontology match is not the right concept.                                               |

## Run details

- run label: `run10`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
