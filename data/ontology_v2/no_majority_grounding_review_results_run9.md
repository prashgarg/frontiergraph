# No-Majority Grounding Review Results run9

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `64,295`

## Decisions
- `promote_new_concept_family`: `224`
- `reject_match_keep_raw`: `45`
- `accept_existing_broad`: `37`
- `accept_existing_alias`: `26`
- `keep_unresolved`: `20`

## Confidence
- `medium`: `180`
- `high`: `157`
- `low`: `15`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label        | confidence   | reason                                                                                                                  |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:--------------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_alias      | FLEX                     |                                 | medium       | The labels are mostly wording variants and modifiers of the same flexibility concept already captured by FLEX.          |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | Labels refer to information asymmetry and value of private information, not the unrelated retrieval concept.            |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | This cluster clearly refers to short-sale constraints, not the misleading ontology target naked short selling.          |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | The ontology target is a misleading list entity; the cluster is just the generic institution governments.               |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | technological progress measures | medium       | The cluster centers on variants of technological progress, not the general notion of green technology.                  |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | All-cause mortality is broader than adult mortality, so the proposed ontology match is misleading.                      |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | Managed competition is a distinct health-policy concept, not a wording variant of effective competition.                |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | political connections           | high         | This is a stable concept family distinct from political capital, with only singular/plural wording variants.            |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Transitional dynamics           | high         | The cluster is a clean synonym set for the economic concept of transitional dynamics, not historical dynamics.          |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | limit orders                    | high         | The cluster cleanly captures a distinct market microstructure concept not adequately represented by order flow trading. |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | accept_existing_broad      | Price fluctuation        |                                 | medium       | Cluster mostly covers price changes over time, which fits the broader existing concept.                                 |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | medium       | The cluster is about fiscal discipline wording, not clearly the ideology implied by fiscal conservatism.                |

## Run details

- run label: `run9`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
