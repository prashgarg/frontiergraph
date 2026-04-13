# No-Majority Grounding Review Results run8

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `64,106`

## Decisions
- `promote_new_concept_family`: `223`
- `reject_match_keep_raw`: `41`
- `accept_existing_broad`: `40`
- `accept_existing_alias`: `24`
- `keep_unresolved`: `24`

## Confidence
- `medium`: `188`
- `high`: `155`
- `low`: `9`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                  | confidence   | reason                                                                                                                          |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:------------------------------------------|:-------------|:--------------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_broad      | FLEX                     |                                           | high         | The cluster is a coherent family of flexibility concepts already well covered by FLEX.                                          |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                           | high         | The cluster is about private information in economics, not information retrieval, so the current ontology target is misleading. |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Short-sale constraints                    | high         | All members are spelling variants of the same distinct research concept, not naked short selling.                               |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | accept_existing_broad      | Government               |                                           | high         | Cluster clearly denotes governments generally, not a list of specific current governments.                                      |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Technological Progress Bias and Direction | medium       | Cluster mixes green and factor-biased technological progress, which is broader than Green Technology.                           |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | accept_existing_broad      | Mortality                |                                           | medium       | All-cause mortality is a general mortality measure, broader than adult mortality but still within the mortality concept.        |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | managed competition                       | medium       | Managed competition is a distinct policy concept, not merely a wording variant of effective competition.                        |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | political connections                     | medium       | The cluster is a tight wording variant set for a distinct economics concept not well covered by political capital.              |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | transition dynamics                       | medium       | The labels consistently refer to transition dynamics, a distinct concept not well captured by historical dynamics.              |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Limit orders                              | high         | This is a distinct market microstructure concept family, not just a wording variant of order flow trading.                      |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | accept_existing_broad      | Price fluctuation        |                                           | medium       | Labels are mostly wording variants of price changes over time, which fits the existing price fluctuation concept broadly.       |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | accept_existing_alias      | Fiscal conservatism      |                                           | medium       | The cluster is a tight wording variant set for the same fiscal restraint concept.                                               |

## Run details

- run label: `run8`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
