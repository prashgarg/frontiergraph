# No-Majority Grounding Review Results run11

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `21`
- batches: `21`
- prompt tokens: `10,120`
- completion tokens: `4,191`

## Decisions
- `promote_new_concept_family`: `11`
- `accept_existing_broad`: `4`
- `reject_match_keep_raw`: `3`
- `keep_unresolved`: `3`

## Confidence
- `medium`: `10`
- `high`: `10`
- `low`: `1`

## Sample rows

| review_item_type   | label                     | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label                               | confidence   | reason                                                                                                     |
|:-------------------|:--------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:-------------------------------------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------|
| cluster_medoid     | managed competition       | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | managed competition                                    | medium       | Managed competition is a distinct policy concept, not just a wording variant of effective competition.     |
| cluster_medoid     | demand effect             | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                                        | high         | The cluster clearly refers to demand-effect wording, and 'Demand set' is a misleading ontology neighbor.   |
| cluster_medoid     | technological catch-up    | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | technological catch-up                                 | medium       | This is a distinct growth concept, not just a wording variant of technological innovation.                 |
| cluster_medoid     | physician productivity    | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                                        | medium       | The cluster centers on physician productivity, and the suggested physician supply target is misleading.    |
| cluster_medoid     | non-aeronautical revenues | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                                        | high         | Non-aeronautical revenues are airport commercial revenues, not generic non-tax revenue.                    |
| cluster_medoid     | har-rv model              | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | Heterogeneous autoregressive realized volatility model | high         | HAR-RV is a distinct volatility forecasting model family, not a wording variant of stochastic volatility.  |
| row                | global economic activity  | candidate              | missing_alias               | accept_existing_broad      | World economy            |                                                        | medium       | The label denotes a global macroeconomic aggregate closely covered by World economy.                       |
| row                | speculative trading       | candidate              | unclear                     | promote_new_concept_family |                          | speculative trading                                    | high         | This is a valid economics concept and the nearest candidates do not cleanly capture trading activity.      |
| row                | socioeconomic conditions  | candidate              | unclear                     | accept_existing_broad      | Socioeconomics           |                                                        | medium       | The label is a broad socioeconomic context and fits the existing Socioeconomics concept.                   |
| row                | aviation emissions        | candidate              | missing_alias               | promote_new_concept_family |                          | Aviation emissions                                     | high         | This is a valid specific research concept, but the suggested ontology matches are too broad or mismatched. |
| row                | competitive forces        | rescue                 | missing_alias               | promote_new_concept_family |                          | competitive forces                                     | medium       | The label is valid but the suggested competition concepts are too specific or mismatched.                  |
| row                | ramsey pricing            | candidate              | missing_alias               | accept_existing_broad      | Ramsey Rule              |                                                        | medium       | Ramsey pricing is closely related to the Ramsey rule, though the label is a broader pricing application.   |

## Run details

- run label: `run11`
- target set: `tied_modal_10run`
- target rows: `21`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `12`
