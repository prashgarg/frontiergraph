# Remaining Heuristic Row Review Results

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `27,983`
- batches: `1,400`
- prompt tokens: `4,893,479`
- completion tokens: `2,236,003`

## Decisions
- `accept_existing_broad`: `15,297`
- `promote_new_concept_family`: `8,675`
- `missing`: `1,382`
- `accept_existing_alias`: `1,367`
- `keep_unresolved`: `879`
- `reject_match_keep_raw`: `336`
- `unclear`: `47`

## Confidence
- `high`: `17,963`
- `medium`: `7,219`
- `low`: `1,419`
- `missing`: `1,382`

## Sample rows

| review_item_type   | label                                  | effective_score_band   | effective_proposed_action   | decision              | canonical_target_label    | new_concept_family_label   | confidence   | reason                                                                                    |
|:-------------------|:---------------------------------------|:-----------------------|:----------------------------|:----------------------|:--------------------------|:---------------------------|:-------------|:------------------------------------------------------------------------------------------|
| row                | renewable energy consumption           | candidate              | broader_concept_available   | accept_existing_broad | Renewable Energy          |                            | high         | The label is a standard subcase of renewable energy and broader grounding is appropriate. |
| row                | trade openness                         | candidate              | broader_concept_available   | accept_existing_broad | Trade Liberalization      |                            | high         | Trade openness is commonly used as a broader trade liberalization concept in economics.   |
| row                | economic policy uncertainty (epu)      | candidate              | broader_concept_available   | accept_existing_broad | Policy uncertainty        |                            | high         | EPU is a specific form of policy uncertainty and fits the broader concept.                |
| row                | economic policy uncertainty            | candidate              | broader_concept_available   | accept_existing_broad | Policy uncertainty        |                            | high         | The extracted label is the standard economics term under policy uncertainty.              |
| row                | profitability                          | candidate              | bad_match_or_noise          | reject_match_keep_raw |                           |                            | medium       | The candidate attachments are too generic and do not clearly match the intended label.    |
| row                | monte carlo experiments                | candidate              | broader_concept_available   | accept_existing_broad | Monte Carlo               |                            | high         | Monte Carlo experiments are a specific application of the Monte Carlo method.             |
| row                | stock market returns                   | candidate              | broader_concept_available   | accept_existing_broad | Stock Returns             |                            | high         | Stock market returns are a direct instance of stock returns.                              |
| row                | non-renewable energy consumption       | candidate              | broader_concept_available   | accept_existing_broad | Non-renewable resource    |                            | high         | Non-renewable energy consumption is grounded in non-renewable resources.                  |
| row                | profits                                | candidate              | bad_match_or_noise          | reject_match_keep_raw |                           |                            | medium       | The proposed profit-related matches are too weak for the bare plural label.               |
| row                | green total factor productivity (gtfp) | candidate              | broader_concept_available   | accept_existing_broad | Total factor productivity |                            | high         | Green total factor productivity is a variant of total factor productivity.                |
| row                | costs                                  | candidate              | unclear                     | keep_unresolved       |                           |                            | low          | Cost is too generic to ground confidently without more context.                           |
| row                | future stock returns                   | candidate              | broader_concept_available   | accept_existing_broad | Stock Returns             |                            | high         | Future stock returns are a forecasting-oriented instance of stock returns.                |
