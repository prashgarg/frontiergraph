# Nano Grounding Review Results v2

- model: `gpt-4.1-nano`
- reviewed items: `11,569`
- batches: `730`
- prompt tokens: `1,932,642`
- completion tokens: `844,857`

## Decisions
- `accept_existing_broad`: `9,013`
- `promote_new_concept_family`: `1,173`
- `accept_existing_alias`: `1,110`
- `missing`: `89`
- `keep_unresolved`: `89`
- `reject_match_keep_raw`: `58`
- `unclear`: `37`

## Confidence
- `high`: `7,049`
- `medium`: `4,136`
- `low`: `293`
- `missing`: `91`

## Sample rows

| review_item_type   | label                 | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label   | confidence   | reason                                                                                                       |
|:-------------------|:----------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------|:-------------|:-------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | gdp per capita        | candidate              | attach_existing_broad       | accept_existing_broad      | GDP                      |                            | high         | Cluster clearly centers on GDP and its variants, fitting well under the broad GDP concept.                   |
| cluster_medoid     | institutional quality | candidate              | add_alias_to_existing       | accept_existing_alias      | Institutional Quality    |                            | high         | Labels consistently refer to institutional quality, matching the existing concept family.                    |
| cluster_medoid     | firm characteristics  | rescue                 | propose_new_concept_family  | promote_new_concept_family |                          | Firm Characteristics       | medium       | Cluster covers diverse firm and individual traits, indicating a broader concept family not yet formalized.   |
| cluster_medoid     | financial constraints | rescue                 | add_alias_to_existing       | accept_existing_alias      | Financial Constraints    |                            | high         | Labels all relate to financial constraints, fitting under the existing concept.                              |
| cluster_medoid     | covid-19 crisis       | candidate              | attach_existing_broad       | accept_existing_broad      | COVID-19                 |                            | high         | Cluster clearly pertains to COVID-19 and its pandemic context, suitable under the broad COVID-19 concept.    |
| cluster_medoid     | policy implications   | candidate              | add_alias_to_existing       | accept_existing_alias      | Policy Issues            |                            | high         | Labels consistently relate to policy implications, fitting well within the existing policy issues concept.   |
| cluster_medoid     | economic fundamentals | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Economic Fundamentals      | medium       | Cluster covers various fundamental economic factors, suggesting a broader concept family not yet formalized. |
| cluster_medoid     | medicaid expansion    | candidate              | attach_existing_broad       | accept_existing_broad      | Medicaid                 |                            | high         | Cluster clearly pertains to Medicaid and its expansions, fitting under the broad Medicaid concept.           |
| cluster_medoid     | monetary shocks       | candidate              | propose_new_concept_family  | promote_new_concept_family | monetary shocks          | monetary shocks            | high         | Cluster clearly centers on monetary shocks and policy responses, not just monetary economics.                |
| cluster_medoid     | inflation persistence | candidate              | propose_new_concept_family  | promote_new_concept_family | inflation persistence    | inflation persistence      | high         | Cluster captures persistent inflation and related phenomena, not just chronic inflation.                     |
| cluster_medoid     | small firms           | candidate              | add_alias_to_existing       | accept_existing_alias      | Small business           |                            | high         | Labels are variants of 'Small business' and align well with existing concept.                                |
| cluster_medoid     | equilibrium price     | candidate              | propose_new_concept_family  | promote_new_concept_family | equilibrium price        | equilibrium price          | high         | Cluster includes various equilibrium-related prices and rates, indicating a broader concept family.          |
