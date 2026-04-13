# No-Majority Grounding Review Results run5

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `64,519`

## Decisions
- `promote_new_concept_family`: `232`
- `reject_match_keep_raw`: `41`
- `accept_existing_broad`: `36`
- `accept_existing_alias`: `25`
- `keep_unresolved`: `18`

## Confidence
- `medium`: `174`
- `high`: `167`
- `low`: `11`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label        | confidence   | reason                                                                                                                              |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:--------------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_broad      | FLEX                     |                                 | medium       | The cluster is a coherent general flexibility concept with many contextual variants already covered by FLEX.                        |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | private information             | high         | Cluster reflects an economics concept family about private information, not information retrieval.                                  |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | accept_existing_alias      | Short sale constraints   |                                 | high         | Variants all refer to short-sale constraints, not naked short selling.                                                              |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | The cluster is about governments generally, while the suggested ontology label is a misleading list-specific entity.                |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | technological progress and bias | medium       | Cluster spans green, biased, and rate-of-progress variants, so it is broader than Green Technology.                                 |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | All-cause mortality is distinct from adult mortality, so the current ontology match is misleading.                                  |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | managed competition             | medium       | Distinct policy concept; not a synonym of effective competition.                                                                    |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | medium       | The cluster is a clean wording variant, but ‘political capital’ is not the right ontology target for ‘political connections’.       |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | The labels are variants of transitional dynamics, not historical dynamics, so the existing ontology target is misleading.           |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | limit orders                    | high         | The cluster clearly refers to the specific market microstructure concept of limit orders, not the broader order flow trading label. |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | accept_existing_broad      | Price fluctuation        |                                 | medium       | The cluster centers on price-related variation, and price fluctuation is the correct broader existing home.                         |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | accept_existing_alias      | Fiscal conservatism      |                                 | high         | The labels are close wording variants of the same fiscal restraint concept already captured by Fiscal conservatism.                 |

## Run details

- run label: `run5`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
