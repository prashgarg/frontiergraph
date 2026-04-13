# Final Grounding Review Results run3

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `11,569`
- batches: `811`
- prompt tokens: `2,036,785`
- completion tokens: `1,008,433`

## Decisions
- `accept_existing_broad`: `5,148`
- `promote_new_concept_family`: `4,221`
- `accept_existing_alias`: `1,214`
- `reject_match_keep_raw`: `656`
- `keep_unresolved`: `301`
- `unclear`: `29`

## Confidence
- `high`: `8,047`
- `medium`: `3,039`
- `low`: `483`

## Sample rows

| review_item_type   | label                 | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                 | confidence   | reason                                                                                                     |
|:-------------------|:----------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:-----------------------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------|
| cluster_medoid     | gdp per capita        | candidate              | attach_existing_broad       | accept_existing_broad      | GDP                      |                                          | high         | The cluster is mostly GDP and GDP-per-capita variants, so GDP is the right broad home.                     |
| cluster_medoid     | institutional quality | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Institutional quality                    | high         | This cluster centers on institutional quality, which is distinct from reform and widely used in economics. |
| cluster_medoid     | firm characteristics  | rescue                 | propose_new_concept_family  | keep_unresolved            |                          |                                          | low          | The labels mix many unrelated characteristic types, so no clean ontology target is clear.                  |
| cluster_medoid     | financial constraints | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | Financial constraints                    | high         | This is a recurring financing-constraint concept that is not well captured by financial distress.          |
| cluster_medoid     | covid-19 crisis       | candidate              | attach_existing_broad       | accept_existing_broad      | COVID-19                 |                                          | high         | These are all pandemic-period and shock variants, so COVID-19 is the correct broad target.                 |
| cluster_medoid     | policy implications   | candidate              | add_alias_to_existing       | accept_existing_alias      | Policy Issues            |                                          | high         | The cluster is essentially wording variants of policy implications, matching Policy Issues.                |
| cluster_medoid     | economic fundamentals | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Economic fundamentals                    | medium       | The cluster captures a recurring fundamentals concept family not well represented by Basic Economics.      |
| cluster_medoid     | medicaid expansion    | candidate              | attach_existing_broad       | accept_existing_broad      | Medicaid                 |                                          | high         | The items are all Medicaid expansion or eligibility variants, which fit Medicaid broadly.                  |
| cluster_medoid     | monetary shocks       | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | monetary shocks / monetary policy shocks | high         | Cluster centers on a specific shock concept family distinct from general monetary economics.               |
| cluster_medoid     | inflation persistence | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                          | medium       | The cluster mixes persistence across many variables, so no single clean ontology target fits.              |
| cluster_medoid     | small firms           | candidate              | add_alias_to_existing       | accept_existing_alias      | Small business           |                                          | high         | The labels are simple wording variants of the same small-firm concept.                                     |
| cluster_medoid     | equilibrium price     | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                          | low          | Equilibrium is too generic and heterogeneous here for a reliable ontology attachment.                      |

## Micro retry details

- pending before micro retry: `0`
- recovered on micro retry: `0`
- remaining missing after micro retry: `0`
- micro retry batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- micro retry concurrency: `8`
