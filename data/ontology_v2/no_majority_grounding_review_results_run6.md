# No-Majority Grounding Review Results run6

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `65,871`

## Decisions
- `promote_new_concept_family`: `219`
- `reject_match_keep_raw`: `52`
- `accept_existing_broad`: `34`
- `accept_existing_alias`: `24`
- `keep_unresolved`: `23`

## Confidence
- `medium`: `185`
- `high`: `153`
- `low`: `14`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label   | confidence   | reason                                                                                                                             |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_alias      | FLEX                     |                            | high         | The cluster is mostly wording variants of flexibility across economic contexts, matching the existing FLEX concept.                |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | These labels refer to private information as an economics concept, not information retrieval.                                      |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | The cluster is about short-sale restrictions generally, not specifically naked short selling.                                      |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | Cluster is generic governments, while the proposed target is a misleading list-specific label.                                     |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | Cluster centers on technological progress bias, not green technology, so the existing ontology neighborhood is misleading.         |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | All-cause mortality is distinct from adult mortality and should not be forced into that ontology label.                            |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | managed competition        | high         | Managed competition is a distinct policy concept, not just a wording variant of effective competition.                             |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | accept_existing_alias      | Political capital        |                            | low          | The cluster is just singular/plural wording variants, though the mapped ontology label may be a slightly broader economic concept. |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | accept_existing_alias      | Transition dynamics      |                            | high         | Both labels are wording variants of the same established concept, and the historical-dynamics neighborhood is misleading.          |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | accept_existing_alias      | Limit orders             |                            | high         | The cluster is a tight wording variant set for limit orders, not order flow trading.                                               |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | accept_existing_broad      | Price fluctuation        |                            | high         | Cluster mostly contains wording variants of price change or fluctuation across time and assets.                                    |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | accept_existing_alias      | Fiscal conservatism      |                            | medium       | The labels are close variants of prudent fiscal restraint and fit the existing fiscal conservatism concept.                        |

## Run details

- run label: `run6`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
