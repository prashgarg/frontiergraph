# Main Grounding Review Results v2 (Merged After Retry)

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `11,569`
- batches: `835`
- prompt tokens: `2,070,080`
- completion tokens: `1,036,821`

## Decisions
- `accept_existing_broad`: `5,229`
- `promote_new_concept_family`: `4,170`
- `accept_existing_alias`: `1,151`
- `reject_match_keep_raw`: `674`
- `keep_unresolved`: `308`
- `unclear`: `21`
- `missing`: `16`

## Confidence
- `high`: `8,032`
- `medium`: `3,044`
- `low`: `477`
- `missing`: `16`

## Sample rows

| review_item_type   | label                 | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                   | confidence   | reason                                                                                                           |
|:-------------------|:----------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:-------------------------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | gdp per capita        | candidate              | attach_existing_broad       | accept_existing_broad      | GDP                      |                                            | high         | These labels are variations of GDP measured per capita or in growth terms.                                       |
| cluster_medoid     | institutional quality | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Institutional Quality                      | high         | The cluster centers on institutional quality, not reform, and recurs as a distinct research concept.             |
| cluster_medoid     | firm characteristics  | rescue                 | propose_new_concept_family  | promote_new_concept_family |                          | Characteristics                            | high         | The cluster spans firm, household, individual, and country characteristics as a broad analytic descriptor.       |
| cluster_medoid     | financial constraints | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | Financial Constraints                      | high         | The labels consistently refer to financing constraints rather than financial distress.                           |
| cluster_medoid     | covid-19 crisis       | candidate              | attach_existing_broad       | accept_existing_broad      | COVID-19                 |                                            | high         | These are all period and shock variants of the COVID-19 pandemic.                                                |
| cluster_medoid     | policy implications   | candidate              | add_alias_to_existing       | accept_existing_alias      | Policy Issues            |                                            | high         | The cluster is mostly wording variants of policy implications.                                                   |
| cluster_medoid     | economic fundamentals | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Economic Fundamentals                      | high         | This cluster captures fundamentals as a recurring concept family, broader than basic economics.                  |
| cluster_medoid     | medicaid expansion    | candidate              | attach_existing_broad       | accept_existing_broad      | Medicaid                 |                                            | high         | These labels are all Medicaid expansion or eligibility variants.                                                 |
| cluster_medoid     | monetary shocks       | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | monetary shocks and monetary policy shocks | high         | Cluster centers on monetary policy shock variants, a recurring concept family beyond general monetary economics. |
| cluster_medoid     | inflation persistence | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | persistence                                | medium       | Labels span inflation and other persistence notions, forming a broader recurring concept family.                 |
| cluster_medoid     | small firms           | candidate              | add_alias_to_existing       | accept_existing_alias      | Small business           |                                            | high         | These labels are straightforward wording variants of small business.                                             |
| cluster_medoid     | equilibrium price     | candidate              | propose_new_concept_family  | accept_existing_broad      | Equilibrium              |                                            | high         | The cluster is broadly about equilibrium concepts across different economic contexts.                            |

## Retry details

- retry queue rows: `708`
- recovered decisions on retry: `692`
- remaining missing after retry: `16`
- retry batch sizes: row=`8`, cluster=`4`, unresolved=`4`
- retry concurrency: `64`
