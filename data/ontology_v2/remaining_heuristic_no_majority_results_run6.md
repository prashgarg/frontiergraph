# Remaining-Heuristic No-Majority Results run6

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `738`
- batches: `738`
- prompt tokens: `354,906`
- completion tokens: `135,941`

## Decisions
- `promote_new_concept_family`: `452`
- `accept_existing_broad`: `183`
- `keep_unresolved`: `55`
- `accept_existing_alias`: `34`
- `reject_match_keep_raw`: `14`

## Confidence
- `medium`: `448`
- `high`: `258`
- `low`: `32`

## Sample rows

| review_item_type   | label                                   | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label       | new_concept_family_label    | confidence   | reason                                                                                                               |
|:-------------------|:----------------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------|:----------------------------|:-------------|:---------------------------------------------------------------------------------------------------------------------|
| row                | price impact                            | candidate              | broader_concept_available   | promote_new_concept_family |                              | price impact                | high         | The label is valid but the proposed ontology matches are too narrow or off-target.                                   |
| row                | chartists                               | candidate              | unclear                     | keep_unresolved            |                              |                             | low          | The label is ambiguous and the proposed matches do not clearly fit the economics usage.                              |
| row                | realized volatility (rv)                | candidate              | broader_concept_available   | promote_new_concept_family |                              | realized volatility         | medium       | The label is valid and distinct from realized variance, so a new concept family is safer than forcing a match.       |
| row                | us data                                 | rescue                 | broader_concept_available   | promote_new_concept_family |                              | United States data          | medium       | The label is a valid research context but does not cleanly match the proposed ontology candidates.                   |
| row                | var model                               | candidate              | broader_concept_available   | keep_unresolved            |                              |                             | medium       | The label is ambiguous and the suggested ontology candidates do not match it reliably.                               |
| row                | household heterogeneity                 | candidate              | broader_concept_available   | keep_unresolved            |                              |                             | high         | This is a valid economics label, but the suggested ontology targets do not match household-level heterogeneity well. |
| row                | model results                           | candidate              | broader_concept_available   | keep_unresolved            |                              |                             | medium       | The label is valid but too generic to force a reliable ontology match.                                               |
| row                | russian invasion of ukraine             | candidate              | missing_alias               | accept_existing_broad      | War                          |                             | medium       | This is a specific conflict event that reasonably grounds to the broader War concept.                                |
| row                | non-renewable energy consumption (nrec) | candidate              | broader_concept_available   | accept_existing_broad      | Aggregate Energy Consumption |                             | medium       | The label is a valid energy-use measure and fits the broader aggregate energy consumption concept.                   |
| row                | temperature shocks                      | candidate              | unclear                     | promote_new_concept_family |                              | temperature shocks          | high         | This is a valid research concept not safely captured by the generic extreme weather candidate.                       |
| row                | endowments                              | candidate              | unclear                     | accept_existing_broad      | Endowment                    |                             | medium       | Plural endowments plausibly maps to the broader ontology concept Endowment in economics research.                    |
| row                | green utility model patents             | candidate              | broader_concept_available   | promote_new_concept_family |                              | green utility model patents | medium       | This is a valid patent-category label, but the proposed ontology match is not the right concept.                     |

## Run details

- run label: `run6`
- target rows: `738`
- remaining missing after retries: `0`
- retry rounds: `3`
- row batch size: `1`
- concurrency: `48`
