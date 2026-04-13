# Retry Grounding Review Results v2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `531`
- batches: `79`
- prompt tokens: `104,780`
- completion tokens: `58,101`

## Decisions
- `promote_new_concept_family`: `208`
- `accept_existing_broad`: `203`
- `accept_existing_alias`: `60`
- `reject_match_keep_raw`: `32`
- `keep_unresolved`: `19`
- `missing`: `8`
- `unclear`: `1`

## Confidence
- `high`: `304`
- `medium`: `189`
- `low`: `30`
- `missing`: `8`

## Sample rows

| review_item_type   | label                           | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label             | confidence   | reason                                                                                                            |
|:-------------------|:--------------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:-------------------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | policy decisions                | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Decision-making and policy decisions | medium       | Cluster centers on decision types across domains, not production measurement.                                     |
| cluster_medoid     | hours worked                    | candidate              | add_alias_to_existing       | accept_existing_alias      | Hours of Work            |                                      | high         | Items are straightforward wording variants of hours worked.                                                       |
| cluster_medoid     | female sex                      | rescue                 | add_alias_to_existing       | accept_existing_alias      | Sex                      |                                      | high         | Cluster is a clear female/male sex wording variant set.                                                           |
| cluster_medoid     | administrative costs            | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                      | low          | The cluster mixes administrative costs, data, efficiency, and capacity into no single clean concept.              |
| cluster_medoid     | hospitals                       | candidate              | add_alias_to_existing       | accept_existing_broad      | Public hospital          |                                      | medium       | Cluster mostly contains hospital wording variants, but some labels are broader than strictly public institutions. |
| cluster_medoid     | distance                        | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                      | high         | The cluster denotes generic distance, not the specific distance-decay concept.                                    |
| cluster_medoid     | revenues                        | rescue                 | propose_new_concept_family  | promote_new_concept_family |                          | Revenue measures and types           | medium       | The labels form a recurring family of revenue measures, sources, and contexts beyond a single revenue concept.    |
| cluster_medoid     | robustness tests                | candidate              | attach_existing_broad       | accept_existing_alias      | Robustness (evolution)   |                                      | high         | These are straightforward wording variants of robustness checks and robustness of results.                        |
| cluster_medoid     | fdi inflows                     | candidate              | attach_existing_broad       | accept_existing_broad      | FDI                      |                                      | high         | “FDI inflows” is a standard broader variant of FDI.                                                               |
| cluster_medoid     | household welfare               | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                      | high         | “Household welfare” is not well captured by the current welfare-care label.                                       |
| cluster_medoid     | catastrophic health expenditure | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Catastrophic health expenditure      | high         | The cluster consistently names a distinct health-finance concept family.                                          |
| cluster_medoid     | governments                     | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                      | medium       | The cluster refers to governments generally, not a list of current governments.                                   |
