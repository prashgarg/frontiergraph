# Main Grounding Review Results v2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `11,569`
- batches: `730`
- prompt tokens: `1,931,912`
- completion tokens: `946,978`

## Decisions
- `accept_existing_broad`: `4,975`
- `promote_new_concept_family`: `3,982`
- `accept_existing_alias`: `1,109`
- `reject_match_keep_raw`: `662`
- `missing`: `531`
- `keep_unresolved`: `290`
- `unclear`: `20`

## Confidence
- `high`: `7,824`
- `medium`: `2,781`
- `missing`: `531`
- `low`: `433`

## Sample rows

| review_item_type   | label                 | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                 | confidence   | reason                                                                                                    |
|:-------------------|:----------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:-----------------------------------------|:-------------|:----------------------------------------------------------------------------------------------------------|
| cluster_medoid     | gdp per capita        | candidate              | attach_existing_broad       | accept_existing_broad      | GDP                      |                                          | high         | The cluster centers on GDP variants, with per-capita and growth forms fitting under GDP.                  |
| cluster_medoid     | institutional quality | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Institutional Quality                    | high         | These labels describe institutional quality and institutional environment, not reform actions.            |
| cluster_medoid     | firm characteristics  | rescue                 | propose_new_concept_family  | promote_new_concept_family |                          | Characteristics                          | medium       | The cluster is a general characteristics family spanning firms, households, individuals, and countries.   |
| cluster_medoid     | financial constraints | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | Financial Constraints                    | high         | The cluster consistently refers to financing constraints and constrained firms, not financial distress.   |
| cluster_medoid     | covid-19 crisis       | candidate              | attach_existing_broad       | accept_existing_broad      | COVID-19                 |                                          | high         | All variants are pandemic-period or shock formulations that belong under COVID-19.                        |
| cluster_medoid     | policy implications   | candidate              | add_alias_to_existing       | accept_existing_alias      | Policy Issues            |                                          | high         | These are wording variants of policy implications, which map cleanly to policy issues.                    |
| cluster_medoid     | economic fundamentals | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Economic Fundamentals                    | medium       | The cluster captures a recurring fundamentals concept not well covered by Basic Economics.                |
| cluster_medoid     | medicaid expansion    | candidate              | attach_existing_broad       | accept_existing_broad      | Medicaid                 |                                          | high         | The cluster is mainly Medicaid expansion and eligibility variants, which are broader Medicaid references. |
| cluster_medoid     | monetary shocks       | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | monetary shocks / monetary policy shocks | high         | The cluster centers on a distinct shock-treatment family not captured by broad monetary economics.        |
| cluster_medoid     | inflation persistence | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | persistence                              | high         | The items form a recurring persistence construct spanning inflation, volatility, output, and shocks.      |
| cluster_medoid     | small firms           | candidate              | add_alias_to_existing       | accept_existing_alias      | Small business           |                                          | high         | The cluster is mostly wording variants of the existing small business concept.                            |
| cluster_medoid     | equilibrium price     | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                          | medium       | The cluster mixes many equilibrium-specific quantities and models, so no clean single target fits.        |
