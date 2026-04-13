# Mini Pilot Grounding Review Results v2

- model: `gpt-4.1-mini`
- reviewed items: `300`
- batches: `24`
- prompt tokens: `49,304`
- completion tokens: `21,734`

## Decisions
- `accept_existing_broad`: `133`
- `promote_new_concept_family`: `83`
- `reject_match_keep_raw`: `43`
- `accept_existing_alias`: `35`
- `keep_unresolved`: `4`
- `unclear`: `2`

## Confidence
- `high`: `223`
- `medium`: `77`

## Sample rows

| review_item_type   | label                             | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label                   | new_concept_family_label   | confidence   | reason                                                                                     |
|:-------------------|:----------------------------------|:-----------------------|:----------------------------|:---------------------------|:-----------------------------------------|:---------------------------|:-------------|:-------------------------------------------------------------------------------------------|
| unresolved_row     | hurst exponent h                  | unresolved             | broader_concept_available   | promote_new_concept_family |                                          | Hurst exponent             | high         | Hurst exponent is a valid economics-related concept needing new concept family promotion.  |
| unresolved_row     | hurst exponent estimates          | unresolved             | broader_concept_available   | promote_new_concept_family |                                          | Hurst exponent estimates   | high         | Estimates of Hurst exponent are valid research labels needing new concept family.          |
| unresolved_row     | hubei pilot                       | unresolved             | missing_concept_family      | reject_match_keep_raw      |                                          |                            | medium       | Hubei pilot is a geographic/policy context but no clear ontology match exists.             |
| row                | industrial structures             | candidate              | bad_match_or_noise          | reject_match_keep_raw      |                                          |                            | high         | Proposed ontology matches are incorrect and label is valid but no suitable ontology match. |
| row                | complexity of time series         | candidate              | broader_concept_available   | accept_existing_broad      | Complex Systems and Time Series Analysis |                            | high         | Broader concept covers complexity of time series well.                                     |
| row                | linking emissions trading schemes | candidate              | broader_concept_available   | accept_existing_broad      | Emissions trading                        |                            | high         | Linking emissions trading schemes fits under broader emissions trading.                    |
| row                | electricity deregulation          | candidate              | broader_concept_available   | accept_existing_broad      | Electric Utilities Regulation            |                            | high         | Electricity deregulation is a subset of electric utilities regulation.                     |
| row                | rapid urbanization                | candidate              | broader_concept_available   | accept_existing_broad      | Urbanization                             |                            | high         | Rapid urbanization is a specific form of urbanization.                                     |
| row                | crude oil price uncertainty       | candidate              | broader_concept_available   | accept_existing_broad      | Oil price                                |                            | medium       | Crude oil price uncertainty fits broadly under oil price concepts.                         |
| row                | transportation distance           | candidate              | broader_concept_available   | accept_existing_broad      | Transportation                           |                            | high         | Transportation distance is a specific aspect of transportation.                            |
| row                | standard economic models          | candidate              | broader_concept_available   | accept_existing_broad      | Economic model                           |                            | high         | Standard economic models fit under economic model broadly.                                 |
| row                | international crude oil price     | candidate              | broader_concept_available   | accept_existing_broad      | Crude Oil                                |                            | high         | International crude oil price is a specific crude oil price concept.                       |

## Nano vs Mini agreement

- overlapping pilot items: `300`
- exact decision agreement: `0.570`

| review_id               | nano_decision              | nano_confidence   | mini_decision              | mini_confidence   |
|:------------------------|:---------------------------|:------------------|:---------------------------|:------------------|
| gr_00029_cluster_medoid | accept_existing_broad      | high              | accept_existing_broad      | high              |
| gr_00069_cluster_medoid | accept_existing_alias      | high              | accept_existing_alias      | high              |
| gr_00084_cluster_medoid | promote_new_concept_family | medium            | promote_new_concept_family | high              |
| gr_00105_cluster_medoid | accept_existing_broad      | high              | reject_match_keep_raw      | medium            |
| gr_00107_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00114_cluster_medoid | accept_existing_broad      | high              | accept_existing_broad      | high              |
| gr_00132_cluster_medoid | accept_existing_broad      | high              | reject_match_keep_raw      | medium            |
| gr_00136_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00147_cluster_medoid | accept_existing_broad      | high              | reject_match_keep_raw      | high              |
| gr_00204_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00214_cluster_medoid | accept_existing_alias      | high              | keep_unresolved            | medium            |
| gr_00234_cluster_medoid | accept_existing_alias      | high              | accept_existing_alias      | high              |
| gr_00258_cluster_medoid | accept_existing_broad      | high              | accept_existing_broad      | high              |
| gr_00266_cluster_medoid | promote_new_concept_family | medium            | promote_new_concept_family | high              |
| gr_00277_cluster_medoid | accept_existing_alias      | high              | accept_existing_alias      | high              |
| gr_00287_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00299_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00309_cluster_medoid | accept_existing_broad      | high              | accept_existing_alias      | high              |
| gr_00323_cluster_medoid | accept_existing_broad      | high              | accept_existing_broad      | high              |
| gr_00349_cluster_medoid | accept_existing_broad      | high              | reject_match_keep_raw      | high              |
