# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-nano`
- reviewed items: `9,347`
- batches: `374`
- prompt tokens: `1,528,023`
- completion tokens: `505,495`

## Decisions
- `valid_parent`: `2,825`
- `alias_or_duplicate`: `1,920`
- `invalid`: `1,757`
- `plausible_but_too_broad`: `1,338`
- `context_not_parent`: `873`
- `sibling_or_related`: `609`
- `missing`: `25`

## Confidence
- `high`: `4,554`
- `medium`: `4,043`
- `low`: `725`
- `missing`: `25`

## Sample rows

| review_tier             | candidate_channel     | child_label                      | candidate_parent_label        | decision           | confidence   | reason                                                                                                                             |
|:------------------------|:----------------------|:---------------------------------|:------------------------------|:-------------------|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------|
| existing_parent_cleanup | existing_parent_label | economy of Lorestan Province     | economy of Iran               | valid_parent       | high         | Economy of a specific province is a narrower instance under the national economy concept.                                          |
| existing_parent_cleanup | existing_parent_label | economy of Bushehr Province      | economy of Iran               | valid_parent       | high         | Economy of a specific province is a narrower instance under the economy of Iran.                                                   |
| existing_parent_cleanup | existing_parent_label | Hitchin Market Place             | marketplace                   | sibling_or_related | high         | A specific market place is not necessarily the same semantic level as the generic marketplace concept.                             |
| existing_parent_cleanup | existing_parent_label | economics of feudal Japan        | economics                     | sibling_or_related | medium       | Economics of feudal Japan is a historical/economic topic, not directly a subtype of the general economics concept.                 |
| existing_parent_cleanup | existing_parent_label | typing game                      | educational video game        | alias_or_duplicate | high         | Typing game is effectively a specific educational video game, making them near-duplicate levels rather than clean hierarchy.       |
| existing_parent_cleanup | existing_parent_label | slow slicing                     | capital punishment            | sibling_or_related | high         | Slow slicing is a specific method of capital punishment, but 'capital punishment' is not a direct broader ontology parent here.    |
| existing_parent_cleanup | existing_parent_label | computer-aided engineering       | science software              | sibling_or_related | medium       | Computer-aided engineering is a domain application, not necessarily a direct child of 'science software'.                          |
| existing_parent_cleanup | existing_parent_label | future of work                   | economics                     | alias_or_duplicate | high         | Future of work is a specific theme under economics, making the 'economics' parent too generic.                                     |
| existing_parent_cleanup | existing_parent_label | basic unemployment allowance     | unemployment benefit          | alias_or_duplicate | high         | Basic unemployment allowance is a specific unemployment benefit type, but mapping to the same label category suggests duplication. |
| existing_parent_cleanup | existing_parent_label | educational support scheme       | government program            | valid_parent       | high         | An educational support scheme is a specific kind of government program.                                                            |
| existing_parent_cleanup | existing_parent_label | economic history of Saudi Arabia | economic history of the world | valid_parent       | medium       | Economic history of a specific country is a narrower instance under economic history of the world.                                 |
| existing_parent_cleanup | existing_parent_label | cryptoeconomics                  | economics                     | valid_parent       | high         | Cryptoeconomics is a subfield within economics.                                                                                    |
