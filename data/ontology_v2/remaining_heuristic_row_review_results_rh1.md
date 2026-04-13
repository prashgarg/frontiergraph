# Remaining Heuristic Row Review Results

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `27,983`
- batches: `1,400`
- prompt tokens: `4,893,479`
- completion tokens: `2,261,402`

## Decisions
- `accept_existing_broad`: `15,111`
- `promote_new_concept_family`: `8,740`
- `missing`: `1,561`
- `accept_existing_alias`: `1,384`
- `keep_unresolved`: `864`
- `reject_match_keep_raw`: `279`
- `unclear`: `44`

## Confidence
- `high`: `17,713`
- `medium`: `7,303`
- `missing`: `1,561`
- `low`: `1,406`

## Sample rows

| review_item_type   | label                                  | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label    | new_concept_family_label   | confidence   | reason                                                                                                 |
|:-------------------|:---------------------------------------|:-----------------------|:----------------------------|:---------------------------|:--------------------------|:---------------------------|:-------------|:-------------------------------------------------------------------------------------------------------|
| row                | renewable energy consumption           | candidate              | broader_concept_available   | accept_existing_broad      | Renewable Energy          |                            | high         | The label is a standard broader economics/environment concept already represented by Renewable Energy. |
| row                | trade openness                         | candidate              | broader_concept_available   | accept_existing_broad      | Trade Liberalization      |                            | high         | Trade openness is closely captured by the broader ontology concept Trade Liberalization.               |
| row                | economic policy uncertainty (epu)      | candidate              | broader_concept_available   | accept_existing_broad      | Policy uncertainty        |                            | high         | EPU is a common narrower variant of policy uncertainty in applied economics.                           |
| row                | economic policy uncertainty            | candidate              | broader_concept_available   | accept_existing_broad      | Policy uncertainty        |                            | high         | The extracted label is a direct surface variant of policy uncertainty.                                 |
| row                | profitability                          | candidate              | bad_match_or_noise          | promote_new_concept_family |                           | Profitability              | medium       | The proposed matches are too narrow or off-target, but profitability is a valid economics concept.     |
| row                | monte carlo experiments                | candidate              | broader_concept_available   | accept_existing_broad      | Monte Carlo               |                            | high         | Monte Carlo experiments are a narrower wording of the Monte Carlo method.                              |
| row                | stock market returns                   | candidate              | broader_concept_available   | accept_existing_broad      | Stock Returns             |                            | high         | Stock market returns are encompassed by the broader stock returns concept.                             |
| row                | non-renewable energy consumption       | candidate              | broader_concept_available   | accept_existing_broad      | Non-renewable resource    |                            | medium       | Non-renewable energy consumption is reasonably grounded to the broader non-renewable resource concept. |
| row                | profits                                | candidate              | bad_match_or_noise          | promote_new_concept_family |                           | Profits                    | medium       | The suggested targets are not good, but profits is a valid standalone economics label.                 |
| row                | green total factor productivity (gtfp) | candidate              | broader_concept_available   | accept_existing_broad      | Total factor productivity |                            | high         | Green total factor productivity is a recognized narrower variant of total factor productivity.         |
| row                | costs                                  | candidate              | unclear                     | accept_existing_broad      | Cost                      |                            | high         | Costs is simply the plural form of the core concept Cost.                                              |
| row                | future stock returns                   | candidate              | broader_concept_available   | accept_existing_broad      | Stock Returns             |                            | high         | Future stock returns are a temporal variant of stock returns.                                          |
