# No-Majority Grounding Review Results run7

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `64,596`

## Decisions
- `promote_new_concept_family`: `229`
- `accept_existing_broad`: `44`
- `reject_match_keep_raw`: `42`
- `accept_existing_alias`: `20`
- `keep_unresolved`: `17`

## Confidence
- `medium`: `180`
- `high`: `157`
- `low`: `15`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label        | confidence   | reason                                                                                                                                  |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:--------------------------------|:-------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_broad      | FLEX                     |                                 | high         | The cluster is a clear set of flexibility variants best grounded under the existing broad FLEX concept.                                 |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | private information             | high         | Cluster is coherent and economics-relevant, but the current ontology target is the wrong concept family.                                |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | short-sale constraints          | high         | The cluster is a clean concept family about short-sale restrictions, not naked short selling.                                           |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | The cluster denotes governments generally, not a list of current governments.                                                           |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | technological progress and bias | high         | Labels center on technological progress and factor-biased progress, not green technology.                                               |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | All-cause mortality is not equivalent to adult mortality, so the proposed ontology match is misleading.                                 |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                 | high         | Managed competition is a distinct policy concept, not a wording variant of effective competition.                                       |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | political connections           | high         | The cluster cleanly reflects political connections, which is distinct from political capital and should not be forced into that target. |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | transition dynamics             | high         | The cluster cleanly reflects a distinct economics concept, not historical dynamics, and merits its own family.                          |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | limit orders                    | high         | The cluster clearly centers on limit order concepts, not the broader and misleading order flow trading label.                           |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | price and temporal variation    | low          | Cluster mixes generic temporal variation with price-specific variation, suggesting a recurring but broader concept family.              |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | accept_existing_alias      | Fiscal conservatism      |                                 | medium       | The cluster is mainly wording variants of fiscal conservatism, centered on fiscal/financial discipline.                                 |

## Run details

- run label: `run7`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
