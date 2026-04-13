# Remaining-Heuristic No-Majority Results run4

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `132,375`

## Decisions
- `promote_new_concept_family`: `476`
- `accept_existing_broad`: `169`
- `keep_unresolved`: `49`
- `accept_existing_alias`: `38`
- `reject_match_keep_raw`: `6`

## Confidence
- `medium`: `404`
- `high`: `304`
- `low`: `30`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label          | confidence   | reason                                                                                                                |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:----------------------------------|:-------------|:----------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                      | medium       | The label is valid and economically meaningful, but the suggested ontology neighbors are not the right match.         |
| row                | chartists                               | candidate              | unclear                     | promote_new_concept_family |                              | chartists                         | medium       | The label is valid in economics, but the proposed ontology matches appear too specific or mismatched.                 |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | promote_new_concept_family |                              | realized volatility               | high         | This is a distinct finance measure, not just a wording variant of realized variance.                                  |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_broad      | United States                |                                   | medium       | The label refers to U.S.-based data, which grounds cleanly to the broader United States context.                      |
| row                | var model                               | candidate              | broader_concept_available   | promote_new_concept_family |                              | vector autoregression (VAR) model | medium       | This appears to be the econometric VAR model, not a fit or matrix model, so a new concept family is more appropriate. |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | Household heterogeneity           | high         | This is a valid research concept, but the proposed ontology matches are too broad or off-target.                      |
| row                | model results                           | candidate              | broader_concept_available   | promote_new_concept_family |                              | model results                     | medium       | The label is valid but too generic for the proposed model-specific ontology matches.                                  |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | promote_new_concept_family |                              | Russian invasion of Ukraine       | high         | This is a valid research event label and a distinct geopolitical shock not captured by the proposed matches.          |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                                   | medium       | The label is a specific energy-consumption measure that can be grounded to the broader existing concept.              |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks                | high         | This is a valid economics-relevant climate exposure term and should be modeled as its own concept family.             |
| row                | endowments                              | candidate              | unclear                     | accept_existing_alias      | Endowment                    |                                   | medium       | Plural surface form matches the existing Endowment concept used in economics research.                                |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents       | medium       | The proposed ontology matches are too broad or off-target, but the label is a valid, distinct patent concept.         |

## Run details

- run label: `run4`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
