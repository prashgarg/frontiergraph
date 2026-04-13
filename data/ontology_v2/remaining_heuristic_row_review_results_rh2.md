# Remaining Heuristic Row Review Results

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `27,983`
- batches: `1,400`
- prompt tokens: `4,894,261`
- completion tokens: `2,278,274`

## Decisions
- `accept_existing_broad`: `14,920`
- `promote_new_concept_family`: `8,564`
- `missing`: `1,880`
- `accept_existing_alias`: `1,341`
- `keep_unresolved`: `903`
- `reject_match_keep_raw`: `326`
- `unclear`: `49`

## Confidence
- `high`: `17,540`
- `medium`: `7,092`
- `missing`: `1,880`
- `low`: `1,471`

## Sample rows

| review_item_type   | label                                  | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label    | new_concept_family_label   | confidence   | reason                                                                               |
|:-------------------|:---------------------------------------|:-----------------------|:----------------------------|:---------------------------|:--------------------------|:---------------------------|:-------------|:-------------------------------------------------------------------------------------|
| row                | renewable energy consumption           | candidate              | broader_concept_available   | accept_existing_broad      | Renewable Energy          |                            | high         | The label is a standard narrower variant of renewable energy.                        |
| row                | trade openness                         | candidate              | broader_concept_available   | accept_existing_broad      | Trade Liberalization      |                            | high         | Trade openness is commonly grounded to the broader trade liberalization concept.     |
| row                | economic policy uncertainty (epu)      | candidate              | broader_concept_available   | accept_existing_broad      | Policy uncertainty        |                            | high         | EPU is a surface-form variant of policy uncertainty.                                 |
| row                | economic policy uncertainty            | candidate              | broader_concept_available   | accept_existing_broad      | Policy uncertainty        |                            | high         | The extracted label clearly refers to policy uncertainty.                            |
| row                | profitability                          | candidate              | bad_match_or_noise          | promote_new_concept_family |                           | profitability              | medium       | Profitability is valid but the suggested ontology targets are not the right concept. |
| row                | monte carlo experiments                | candidate              | broader_concept_available   | accept_existing_alias      | Monte Carlo method        |                            | high         | Monte Carlo experiments is an alias-like wording for the Monte Carlo method.         |
| row                | stock market returns                   | candidate              | broader_concept_available   | accept_existing_alias      | Stock Returns             |                            | high         | Stock market returns is a wording variant of stock returns.                          |
| row                | non-renewable energy consumption       | candidate              | broader_concept_available   | accept_existing_broad      | Non-renewable resource    |                            | high         | The label is a narrower energy-consumption use of non-renewable resources.           |
| row                | profits                                | candidate              | bad_match_or_noise          | promote_new_concept_family |                           | profits                    | medium       | Profits is valid, but the proposed ontology attachments are off-target.              |
| row                | green total factor productivity (gtfp) | candidate              | broader_concept_available   | accept_existing_broad      | Total factor productivity |                            | high         | Green total factor productivity is a narrower variant of total factor productivity.  |
| row                | costs                                  | candidate              | unclear                     | keep_unresolved            |                           |                            | low          | Costs is too generic to force a specific ontology attachment.                        |
| row                | future stock returns                   | candidate              | broader_concept_available   | accept_existing_broad      | Stock Returns             |                            | high         | Future stock returns fits the broader stock returns concept.                         |
