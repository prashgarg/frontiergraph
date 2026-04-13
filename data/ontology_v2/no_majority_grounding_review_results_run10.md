# No-Majority Grounding Review Results run10

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `66,868`

## Decisions
- `promote_new_concept_family`: `218`
- `accept_existing_broad`: `49`
- `reject_match_keep_raw`: `48`
- `accept_existing_alias`: `21`
- `keep_unresolved`: `16`

## Confidence
- `medium`: `205`
- `high`: `133`
- `low`: `14`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                | confidence   | reason                                                                                                                                   |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:----------------------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_broad      | FLEX                     |                                         | high         | The cluster is a coherent family of flexibility notions best grounded under the existing broad FLEX concept.                             |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                         | high         | The cluster is about economic private information, not the computer-science concept of private information retrieval.                    |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | short-sale constraints                  | high         | The cluster consistently refers to short-sale restrictions, not naked short selling.                                                     |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | accept_existing_broad      | government               |                                         | high         | Cluster is a clear generic government concept, broader than the overly specific current ontology label.                                  |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | green and biased technological progress | medium       | The cluster centers on technological progress variants, not green technology itself, and mixes a recurring bias/progress concept family. |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                         | high         | All-cause mortality is not equivalent to adult mortality, so the proposed ontology neighbor is misleading.                               |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                         | medium       | Managed competition is a distinct policy model, not a wording variant of effective competition.                                          |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | political connections                   | high         | This is a distinct economics concept and not just wording variants of political capital.                                                 |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | transition dynamics                     | medium       | The labels consistently refer to transition dynamics, not historical dynamics.                                                           |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Limit orders                            | high         | The cluster is a coherent market microstructure concept distinct from order flow trading.                                                |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                         | medium       | The cluster mixes price-specific and generic temporal variation phrases, so no single ontology home is clean.                            |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                         | high         | The cluster reflects fiscal discipline wording, not the ideological concept of fiscal conservatism.                                      |

## Run details

- run label: `run10`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
