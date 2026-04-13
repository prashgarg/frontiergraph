# Retry Grounding Review Results v2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `532`
- batches: `81`
- prompt tokens: `104,259`
- completion tokens: `57,868`

## Decisions
- `accept_existing_broad`: `226`
- `promote_new_concept_family`: `179`
- `accept_existing_alias`: `75`
- `reject_match_keep_raw`: `31`
- `keep_unresolved`: `20`
- `unclear`: `1`

## Confidence
- `high`: `323`
- `medium`: `178`
- `low`: `31`

## Sample rows

| review_item_type   | label                      | effective_score_band   | effective_proposed_action   | decision                   | canonical_target_label   | new_concept_family_label               | confidence   | reason                                                                                                                       |
|:-------------------|:---------------------------|:-----------------------|:----------------------------|:---------------------------|:-------------------------|:---------------------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------------------|
| cluster_medoid     | policy decisions           | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | Decision-making / decisions            | medium       | Cluster covers multiple domain-specific decision types, not a single existing ontology home.                                 |
| cluster_medoid     | hours worked               | candidate              | add_alias_to_existing       | accept_existing_alias      | Hours of Work            |                                        | high         | All labels are wording variants of hours worked.                                                                             |
| cluster_medoid     | female sex                 | rescue                 | add_alias_to_existing       | accept_existing_alias      | Sex manual               |                                        | high         | The cluster consistently refers to sex as female versus male.                                                                |
| cluster_medoid     | administrative costs       | candidate              | propose_new_concept_family  | keep_unresolved            |                          |                                        | low          | The cluster mixes costs, data, efficiency, and capacity, so no single clean concept is evident.                              |
| cluster_medoid     | hospitals                  | candidate              | add_alias_to_existing       | accept_existing_broad      | Public hospital          |                                        | medium       | Cluster mainly refers to hospitals broadly, so the public-hospital label is too narrow but still the closest existing home.  |
| cluster_medoid     | distance                   | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                        | medium       | The cluster is about distance measures, not distance decay, so the suggested ontology neighborhood is misleading.            |
| cluster_medoid     | revenues                   | rescue                 | propose_new_concept_family  | promote_new_concept_family |                          | Revenue and revenue variants           | high         | The cluster spans many revenue-specific research labels that recur as a broader concept family beyond a single revenue node. |
| cluster_medoid     | robustness tests           | candidate              | attach_existing_broad       | accept_existing_alias      | Robustness (evolution)   |                                        | high         | The labels are clear wording variants of robustness checks and robustness results.                                           |
| cluster_medoid     | price variation            | candidate              | propose_new_concept_family  | promote_new_concept_family |                          | price variation and temporal variation | medium       | The cluster mixes price-change wording with generic time-variation phrases, suggesting a broader recurring concept family.   |
| cluster_medoid     | level of democracy         | candidate              | add_alias_to_existing       | reject_match_keep_raw      |                          |                                        | high         | The ontology target is too specific; the cluster clearly refers to democracy level, not bourgeois democracy.                 |
| cluster_medoid     | house price growth         | candidate              | attach_existing_broad       | accept_existing_broad      | House price              |                                        | high         | The labels are straightforward variants of house price growth, which fits under the broader house price concept.             |
| cluster_medoid     | natural resource endowment | candidate              | attach_existing_broad       | accept_existing_broad      | Natural resource         |                                        | high         | The cluster is a simple wording variant of natural resource endowment, which belongs under natural resource.                 |
