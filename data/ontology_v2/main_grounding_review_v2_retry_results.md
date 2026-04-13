# Retry Grounding Review Results v2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `708`
- batches: `105`
- prompt tokens: `138,168`
- completion tokens: `78,533`

## Decisions
- `promote_new_concept_family`: `260`
- `accept_existing_broad`: `252`
- `accept_existing_alias`: `99`
- `reject_match_keep_raw`: `50`
- `keep_unresolved`: `31`
- `missing`: `16`

## Confidence
- `high`: `403`
- `medium`: `263`
- `low`: `26`
- `missing`: `16`

## Sample rows

| review_item_type   | label                     | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label         | new_concept_family_label   | confidence   | reason                                                                                                             |
|:-------------------|:--------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------------|:---------------------------|:-------------|:-------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | mineral rents             | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                                |                            | high         | Mineral rents and mineral prices are not aliases of mineral rights, and the current ontology target is misleading. |
| cluster_medoid     | private firms             | candidate              | attach_existing_broad       | accept_existing_broad      | Firms                          |                            | high         | Private firms are straightforward instances of the broader firms concept.                                          |
| cluster_medoid     | efficiency change         | candidate              | attach_existing_broad       | accept_existing_broad      | Efficiency                     |                            | medium       | The cluster is a specific efficiency-change variant that fits under the broader efficiency concept.                |
| cluster_medoid     | machine learning models   | candidate              | attach_existing_broad       | keep_unresolved            |                                |                            | medium       | The cluster mixes machine learning terms with unrelated learning-cost and learning-rate labels.                    |
| cluster_medoid     | book-to-market ratio      | candidate              | attach_existing_broad       | accept_existing_alias      | book market                    |                            | high         | All labels are wording variants of the book-to-market ratio concept.                                               |
| cluster_medoid     | trading frequency         | candidate              | add_alias_to_existing       | promote_new_concept_family |                                | trading frequency          | medium       | The cluster reflects trade-frequency measurement, not high-frequency trading.                                      |
| cluster_medoid     | random walk benchmark     | candidate              | attach_existing_broad       | accept_existing_broad      | Random walk                    |                            | high         | The cluster is a straightforward set of random-walk benchmark variants.                                            |
| cluster_medoid     | cash holdings             | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                                |                            | high         | Cash holdings is distinct from cash concentration, so the current ontology neighborhood is misleading.             |
| cluster_medoid     | stochastic interest rates | candidate              | add_alias_to_existing       | accept_existing_broad      | Stochastic finance             |                            | high         | Stochastic interest rates are a specific case of stochastic finance.                                               |
| cluster_medoid     | environmental impacts     | candidate              | add_alias_to_existing       | accept_existing_alias      | Energy and Environment Impacts |                            | high         | Environmental impact/impacts is a straightforward wording variant of the existing impact concept.                  |
| cluster_medoid     | plant size                | candidate              | add_alias_to_existing       | accept_existing_broad      | Plant growth                   |                            | low          | Plant size is related but broader ontology grounding under plant growth is acceptable.                             |
| cluster_medoid     | incomplete information    | candidate              | add_alias_to_existing       | accept_existing_alias      | Imperfect Information          |                            | high         | Incomplete information is a direct synonym of imperfect information.                                               |
