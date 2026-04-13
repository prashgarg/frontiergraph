# Remaining-Heuristic No-Majority Results run9

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `136,111`

## Decisions
- `promote_new_concept_family`: `464`
- `accept_existing_broad`: `180`
- `keep_unresolved`: `51`
- `accept_existing_alias`: `39`
- `reject_match_keep_raw`: `4`

## Confidence
- `medium`: `425`
- `high`: `277`
- `low`: `36`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label   | confidence   | reason                                                                                                                          |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:---------------------------|:-------------|:--------------------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact               | high         | The label is a valid economics concept but the suggested ontology matches are too narrow or generic.                            |
| row                | chartists                               | candidate              | unclear                     | keep_unresolved            |                              |                            | low          | Chartists is ambiguous in economics papers and no ontology candidate is clearly correct.                                        |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | accept_existing_broad      | Realized variance            |                            | medium       | Realized volatility is closely related and reasonably grounded under realized variance as a broader financial measure.          |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_broad      | United States                |                            | medium       | The label refers broadly to US-based data, which fits the existing United States concept better than USDA.                      |
| row                | var model                               | candidate              | broader_concept_available   | promote_new_concept_family |                              | VAR model                  | medium       | This is likely a vector autoregression model, but the ontology match is absent and the label is still a valid research concept. |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity    | high         | This is a valid economics research concept but not the same as study heterogeneity or household economics.                      |
| row                | model results                           | candidate              | broader_concept_available   | keep_unresolved            |                              |                            | high         | The label is too generic for a safe ontology match, and the proposed candidates are not equivalent.                             |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | accept_existing_broad      | War                          |                            | medium       | The label is a specific conflict event and reasonably grounds to the broader ontology concept War.                              |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                            | medium       | Broader energy-consumption concept fits the variable, though it is less specific than non-renewable energy consumption.         |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks         | high         | This is a valid climate shock concept used in economics and not well captured by the broad extreme weather candidate.           |
| row                | endowments                              | candidate              | unclear                     | accept_existing_alias      | Endowment                    |                            | medium       | Plural form likely refers to the existing Endowment concept in economics research.                                              |
| row                | green utility model patents             | candidate              | broader_concept_available   | accept_existing_broad      | Public utility model         |                            | low          | A public utility model is the closest broader patent concept, though the green qualifier is not captured.                       |

## Run details

- run label: `run9`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
