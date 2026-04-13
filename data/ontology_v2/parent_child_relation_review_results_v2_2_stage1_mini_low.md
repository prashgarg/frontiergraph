# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `9,347`
- batches: `374`
- prompt tokens: `1,588,237`
- completion tokens: `428,223`

## Decisions
- `valid_parent`: `5,507`
- `invalid`: `2,629`
- `sibling_or_related`: `426`
- `context_not_parent`: `422`
- `plausible_but_too_broad`: `184`
- `alias_or_duplicate`: `179`

## Confidence
- `high`: `7,975`
- `medium`: `1,282`
- `low`: `90`

## Sample rows

| review_tier             | candidate_channel     | child_label                      | candidate_parent_label        | decision     | confidence   | reason                                                                                    |
|:------------------------|:----------------------|:---------------------------------|:------------------------------|:-------------|:-------------|:------------------------------------------------------------------------------------------|
| existing_parent_cleanup | existing_parent_label | economy of Lorestan Province     | economy of Iran               | valid_parent | high         | Lorestan Province economy is a specific regional economy under Iran's economy.            |
| existing_parent_cleanup | existing_parent_label | economy of Bushehr Province      | economy of Iran               | valid_parent | high         | Bushehr Province economy is a specific regional economy under Iran's economy.             |
| existing_parent_cleanup | existing_parent_label | Hitchin Market Place             | marketplace                   | valid_parent | high         | A market place is a specific kind of marketplace.                                         |
| existing_parent_cleanup | existing_parent_label | economics of feudal Japan        | economics                     | valid_parent | high         | Economic history of feudal Japan is a specific regional historical subtopic of economics. |
| existing_parent_cleanup | existing_parent_label | typing game                      | educational video game        | valid_parent | high         | A typing game can be a subtype of educational video game.                                 |
| existing_parent_cleanup | existing_parent_label | slow slicing                     | capital punishment            | invalid      | medium       | Slow slicing is a method of execution, not a type of capital punishment concept.          |
| existing_parent_cleanup | existing_parent_label | computer-aided engineering       | science software              | valid_parent | high         | Computer-aided engineering is a specific kind of science software.                        |
| existing_parent_cleanup | existing_parent_label | future of work                   | economics                     | valid_parent | medium       | Future of work is a recognized economics topic under economics.                           |
| existing_parent_cleanup | existing_parent_label | basic unemployment allowance     | unemployment benefit          | valid_parent | high         | Basic unemployment allowance is a specific type of unemployment benefit.                  |
| existing_parent_cleanup | existing_parent_label | educational support scheme       | government program            | valid_parent | high         | An educational support scheme is a type of government program.                            |
| existing_parent_cleanup | existing_parent_label | economic history of Saudi Arabia | economic history of the world | valid_parent | high         | Economic history of Saudi Arabia is a specific case of world economic history.            |
| existing_parent_cleanup | existing_parent_label | cryptoeconomics                  | economics                     | valid_parent | medium       | Cryptoeconomics is a subfield within economics, though more specific than the parent.     |
