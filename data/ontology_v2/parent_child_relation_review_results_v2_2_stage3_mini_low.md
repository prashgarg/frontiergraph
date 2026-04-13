# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `8,531`
- batches: `342`
- prompt tokens: `1,522,249`
- completion tokens: `356,855`

## Decisions
- `invalid`: `6,497`
- `sibling_or_related`: `1,109`
- `valid_parent`: `693`
- `context_not_parent`: `113`
- `alias_or_duplicate`: `79`
- `plausible_but_too_broad`: `36`
- `missing`: `4`

## Confidence
- `high`: `7,897`
- `medium`: `618`
- `low`: `12`
- `missing`: `4`

## Sample rows

| review_tier       | candidate_channel         | child_label                                                          | candidate_parent_label               | decision   | confidence   | reason                                                                                                 |
|:------------------|:--------------------------|:---------------------------------------------------------------------|:-------------------------------------|:-----------|:-------------|:-------------------------------------------------------------------------------------------------------|
| inferred_semantic | semantic_broader_neighbor | Zimbabwe African People's Union                                      | Single Tax Party                     | invalid    | high         | These are unrelated political organizations; one is not a broader type of the other.                   |
| inferred_semantic | semantic_broader_neighbor | Scottish Land Restoration League                                     | Single Tax Party                     | invalid    | high         | These are separate political organizations, not a parent-child relation.                               |
| inferred_semantic | semantic_broader_neighbor | The Generalissimo: Chiang Kai-shek and the Struggle for Modern China | Party Reform Program                 | invalid    | high         | A book title cannot be the broader concept of another publication or work.                             |
| inferred_semantic | semantic_broader_neighbor | Brookfield Properties                                                | BGIS                                 | invalid    | high         | These are different companies with no parent-child relationship implied.                               |
| inferred_semantic | semantic_broader_neighbor | Land Tax Redemption (No. 2) Act 1799                                 | Land Tax Perpetuation Act 1798       | invalid    | high         | These are distinct legislation acts, not broader and narrower versions of each other.                  |
| inferred_semantic | semantic_broader_neighbor | Land Tax Redemption (No. 2) Act 1800                                 | Land Tax Perpetuation Act 1798       | invalid    | high         | These are distinct legislation acts, not broader and narrower versions of each other.                  |
| inferred_semantic | semantic_broader_neighbor | 2023 Speaker of the Koshi Provincial Assembly election               | 2024 Ethiopian presidential election | invalid    | high         | An election in Koshi province is unrelated to an Ethiopian presidential election as a broader concept. |
| inferred_semantic | semantic_broader_neighbor | Radical People's Party (Norway)                                      | Single Tax Party                     | invalid    | high         | These are different political parties; the candidate is not the child's broader category.              |
| inferred_semantic | semantic_broader_neighbor | Bryan–Chamorro Treaty                                                | Boxer Protocol                       | invalid    | high         | These are different treaties, so the candidate is not a broader parent concept.                        |
| inferred_semantic | semantic_broader_neighbor | Belarusian Hajun project                                             | AltLaw                               | invalid    | high         | The candidate is a different legal-tech project, not a broader category for the child.                 |
| inferred_semantic | semantic_broader_neighbor | Democratic Alliance (Hong Kong)                                      | 123 Democratic Alliance              | invalid    | high         | These are different political groups; the labels do not indicate a hierarchical relation.              |
| inferred_semantic | semantic_broader_neighbor | Korean National Revolutionary Party                                  | 123 Democratic Alliance              | invalid    | high         | These are different political organizations, not parent and child.                                     |
