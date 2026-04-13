# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `200`
- batches: `10`
- prompt tokens: `35,471`
- completion tokens: `10,056`

## Decisions
- `valid_parent`: `93`
- `invalid`: `59`
- `sibling_or_related`: `30`
- `context_not_parent`: `9`
- `alias_or_duplicate`: `7`
- `plausible_but_too_broad`: `2`

## Confidence
- `high`: `170`
- `medium`: `30`

## Sample rows

| review_tier             | candidate_channel     | child_label                                            | candidate_parent_label      | decision           | confidence   | reason                                                                                                  |
|:------------------------|:----------------------|:-------------------------------------------------------|:----------------------------|:-------------------|:-------------|:--------------------------------------------------------------------------------------------------------|
| existing_parent_cleanup | existing_parent_label | 60-As                                                  | Roman currency              | alias_or_duplicate | high         | Both labels refer to the same Roman coin denomination concept.                                          |
| existing_parent_cleanup | existing_parent_label | Analytical bias correction                             | Bias distortion             | sibling_or_related | medium       | Analytical bias correction addresses bias distortion, but it is not a subtype of it.                    |
| existing_parent_cleanup | existing_parent_label | AutoREALM                                              | Macroeconomics              | invalid            | high         | AutoREALM is a software/tool, not a kind of macroeconomics.                                             |
| existing_parent_cleanup | existing_parent_label | Autocrat vehicles                                      | Brand                       | invalid            | high         | Autocrat vehicles is unrelated to the brand concept.                                                    |
| existing_parent_cleanup | existing_parent_label | Bunesfjorden                                           | Unemployment                | invalid            | high         | Bunesfjorden is a geographic feature, not unemployment.                                                 |
| existing_parent_cleanup | existing_parent_label | C2.LOP                                                 | spyware                     | alias_or_duplicate | medium       | C2.LOP appears to be the same spyware concept under a coded name.                                       |
| existing_parent_cleanup | existing_parent_label | Cotton made in Africa                                  | Economic Development        | context_not_parent | medium       | Cotton made in Africa is an initiative associated with development, not a type of economic development. |
| existing_parent_cleanup | existing_parent_label | Drum Connection                                        | Economic inequality         | invalid            | high         | Drum Connection is unrelated to economic inequality.                                                    |
| existing_parent_cleanup | existing_parent_label | Environmental concern and public environmental concern | Environmental consciousness | alias_or_duplicate | high         | The child is a verbose rewording of environmental consciousness.                                        |
| existing_parent_cleanup | existing_parent_label | G-4                                                    | proposed aircraft           | valid_parent       | high         | G-4 is a specific proposed aircraft, so proposed aircraft is the right broader concept.                 |
| existing_parent_cleanup | existing_parent_label | Gau Westmark                                           | Behavioral Economics        | invalid            | high         | Gau Westmark is unrelated to behavioral economics.                                                      |
| existing_parent_cleanup | existing_parent_label | Innværfjorden                                          | Unemployment                | invalid            | high         | Innværfjorden is a place name, not unemployment.                                                        |
