# Remaining-Heuristic No-Majority Results run11

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `134,570`

## Decisions
- `promote_new_concept_family`: `480`
- `accept_existing_broad`: `161`
- `keep_unresolved`: `48`
- `accept_existing_alias`: `36`
- `reject_match_keep_raw`: `12`
- `unclear`: `1`

## Confidence
- `medium`: `432`
- `high`: `285`
- `low`: `21`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label    | confidence   | reason                                                                                                                |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:----------------------------|:-------------|:----------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                | high         | The label is a valid economics concept, but the proposed ontology matches are too generic or mismatched.              |
| row                | chartists                               | candidate              | unclear                     | unclear                    |                              |                             | low          | The label is ambiguous between historical Chartism and chart-based traders, so no safe ontology match is justified.   |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | accept_existing_broad      | Realized variance            |                             | medium       | Realized volatility is commonly used as a close broader proxy for realized variance in economics research.            |
| row                | us data                                 | rescue                 | broader_concept_available   | accept_existing_broad      | United States                |                             | medium       | The label refers broadly to U.S. data, so grounding to United States is a reasonable higher-level match.              |
| row                | var model                               | candidate              | broader_concept_available   | promote_new_concept_family |                              | VAR model                   | medium       | This likely refers to vector autoregression, a valid econometric method not matched by the proposed ontology targets. |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | promote_new_concept_family |                              | household heterogeneity     | high         | This is a valid economics research concept but the suggested ontology matches are not the right concept.              |
| row                | model results                           | candidate              | broader_concept_available   | promote_new_concept_family |                              | model results               | medium       | This is a valid research label, but the suggested ontology targets are not a clean match.                             |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | promote_new_concept_family |                              | Russian invasion of Ukraine | high         | This is a distinct geopolitical event used as a research shock, not just generic war.                                 |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                             | medium       | The label is a specific energy-use measure and fits the broader aggregate energy consumption concept.                 |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks          | medium       | Economically relevant climate exposure term, but not a clean match to extreme weather.                                |
| row                | endowments                              | candidate              | unclear                     | accept_existing_alias      | Endowment                    |                             | medium       | Plural surface form matches the existing Endowment concept, and the broader ontology candidate is plausible.          |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents | medium       | This is a valid patent-category label, but the suggested ontology match is not the right concept.                     |

## Run details

- run label: `run11`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
