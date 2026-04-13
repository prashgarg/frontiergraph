# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-nano`
- reviewed items: `200`
- batches: `10`
- prompt tokens: `35,471`
- completion tokens: `11,208`

## Decisions
- `invalid`: `55`
- `valid_parent`: `54`
- `plausible_but_too_broad`: `30`
- `alias_or_duplicate`: `25`
- `sibling_or_related`: `19`
- `context_not_parent`: `17`

## Confidence
- `medium`: `100`
- `high`: `78`
- `low`: `22`

## Sample rows

| review_tier             | candidate_channel     | child_label                                            | candidate_parent_label      | decision                | confidence   | reason                                                                                                           |
|:------------------------|:----------------------|:-------------------------------------------------------|:----------------------------|:------------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------|
| existing_parent_cleanup | existing_parent_label | 60-As                                                  | Roman currency              | alias_or_duplicate      | high         | Child and candidate parent are the same label 'Roman currency'.                                                  |
| existing_parent_cleanup | existing_parent_label | Analytical bias correction                             | Bias distortion             | alias_or_duplicate      | high         | Child 'Analytical bias correction' is essentially under the same parent label 'Bias distortion'.                 |
| existing_parent_cleanup | existing_parent_label | AutoREALM                                              | Macroeconomics              | plausible_but_too_broad | medium       | AutoREALM relates to macroeconomics but is not clearly a direct subtype of the generic area.                     |
| existing_parent_cleanup | existing_parent_label | Autocrat vehicles                                      | Brand                       | invalid                 | medium       | Auto 'Autocrat vehicles' is not a kind of 'Brand' in a semantic hierarchy.                                       |
| existing_parent_cleanup | existing_parent_label | Bunesfjorden                                           | Unemployment                | invalid                 | medium       | 'Bunesfjorden' is a place, while 'Unemployment' is an economic variable.                                         |
| existing_parent_cleanup | existing_parent_label | C2.LOP                                                 | spyware                     | alias_or_duplicate      | high         | Child 'C2.LOP' matches the candidate parent 'spyware' only at the label level and otherwise differs.             |
| existing_parent_cleanup | existing_parent_label | Cotton made in Africa                                  | Economic Development        | invalid                 | medium       | 'Cotton made in Africa' is a specific program/initiative, not a direct subtype of economic development.          |
| existing_parent_cleanup | existing_parent_label | Drum Connection                                        | Economic inequality         | invalid                 | low          | 'Drum Connection' appears unrelated to 'Economic inequality' as a direct parent-child type.                      |
| existing_parent_cleanup | existing_parent_label | Environmental concern and public environmental concern | Environmental consciousness | plausible_but_too_broad | medium       | Environmental concern can fall under environmental consciousness, but the child seems an extracted text variant. |
| existing_parent_cleanup | existing_parent_label | G-4                                                    | proposed aircraft           | alias_or_duplicate      | high         | Child 'G-4' is a labeled item where the candidate parent 'proposed aircraft' is not a direct semantic parent.    |
| existing_parent_cleanup | existing_parent_label | Gau Westmark                                           | Behavioral Economics        | invalid                 | medium       | Gau Westmark is an entity name and not clearly a behavioral-economics subtype.                                   |
| existing_parent_cleanup | existing_parent_label | Innværfjorden                                          | Unemployment                | invalid                 | medium       | 'Innværfjorden' is geographic/place context, not a direct child of the unemployment concept.                     |
