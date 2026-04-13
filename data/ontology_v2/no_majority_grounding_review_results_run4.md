# No-Majority Grounding Review Results run4

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `352`
- batches: `352`
- prompt tokens: `170,834`
- completion tokens: `64,930`

## Decisions
- `promote_new_concept_family`: `226`
- `reject_match_keep_raw`: `38`
- `accept_existing_broad`: `37`
- `accept_existing_alias`: `28`
- `keep_unresolved`: `23`

## Confidence
- `medium`: `183`
- `high`: `156`
- `low`: `13`

## Sample rows

| review_item_type   | label                        | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label   | confidence   | reason                                                                                                                    |
|:-------------------|:-----------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------|:-------------|:--------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | flexibility                  | rescue                 | propose_new_concept_family  | accept_existing_broad      | FLEX                     |                            | medium       | The cluster is centered on generic flexibility and its common economic variants, which fit the broad FLEX concept.        |
| cluster_medoid     | private information          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | Private information        | high         | Cluster terms refer to information held privately in economics, not the computer-science retrieval concept.               |
| cluster_medoid     | short-sale constraints       | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | The cluster is about short-sale constraints, not naked short selling, so the current ontology match is misleading.        |
| cluster_medoid     | governments                  | rescue                 | add_alias_to_existing       | accept_existing_broad      | governments              |                            | high         | The cluster clearly refers to governments in general, not a list of current governments.                                  |
| cluster_medoid     | green technological progress | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | high         | The cluster centers on biased and directional technological progress, not the broader concept of green technology.        |
| cluster_medoid     | all-cause mortality          | rescue                 | add_alias_to_existing       | promote_new_concept_family |                          | all-cause mortality        | high         | This is a distinct standard mortality outcome, not a wording variant of adult mortality.                                  |
| cluster_medoid     | managed competition          | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | managed competition        | medium       | Managed competition is a distinct policy concept, not a wording variant of effective competition.                         |
| cluster_medoid     | political connections        | candidate              | add_alias_to_existing       | accept_existing_alias      | Political capital        |                            | medium       | Only singular/plural wording variants appear, and the existing political capital node is the nearest established home.    |
| cluster_medoid     | transitional dynamics        | candidate              | add_alias_to_existing       | promote_new_concept_family |                          | transitional dynamics      | medium       | The cluster is a clean variant set for transitional dynamics, and Historical dynamics is the wrong ontology neighborhood. |
| cluster_medoid     | limit orders                 | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                            | medium       | Limit orders are a distinct market microstructure concept, not a wording variant of order flow trading.                   |
| cluster_medoid     | price variation              | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                            | medium       | The cluster mixes price fluctuation wording with generic time variation, so no single ontology target is clean.           |
| cluster_medoid     | fiscal discipline            | candidate              | add_alias_to_existing       | accept_existing_alias      | Fiscal conservatism      |                            | high         | The labels are clear wording variants of fiscal conservatism and do not suggest a broader new concept.                    |

## Run details

- run label: `run4`
- no-majority target rows: `352`
- remaining missing after retries: `0`
- retry rounds: `3`
- batch sizes: row=`1`, cluster=`1`, unresolved=`1`
- concurrency: `20`
