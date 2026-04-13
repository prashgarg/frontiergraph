# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-nano`
- reviewed items: `20`
- batches: `1`
- prompt tokens: `3,392`
- completion tokens: `1,261`

## Decisions
- `plausible_but_too_broad`: `9`
- `alias_or_duplicate`: `6`
- `sibling_or_related`: `3`
- `invalid`: `2`

## Confidence
- `medium`: `14`
- `high`: `6`

## Sample rows

| review_tier             | candidate_channel     | child_label                      | candidate_parent_label        | decision                | confidence   | reason                                                                                                                                          |
|:------------------------|:----------------------|:---------------------------------|:------------------------------|:------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| existing_parent_cleanup | existing_parent_label | economy of Lorestan Province     | economy of Iran               | alias_or_duplicate      | high         | Child is a province-specific economy concept; same parent label repeats exactly without evidence of proper broader semantics.                   |
| existing_parent_cleanup | existing_parent_label | economy of Bushehr Province      | economy of Iran               | alias_or_duplicate      | high         | Province-specific economy under 'economy of Iran' is effectively a contextual variant, not a unique parent-child semantic hierarchy.            |
| existing_parent_cleanup | existing_parent_label | Hitchin Market Place             | marketplace                   | alias_or_duplicate      | high         | Hitchin Market Place appears to be a specific marketplace instance; 'marketplace' is too generic and not a distinct parent mapping.             |
| existing_parent_cleanup | existing_parent_label | economics of feudal Japan        | economics                     | plausible_but_too_broad | medium       | 'economics of feudal Japan' is a thematic specialization; parent 'economics' is overly generic to be the direct broader concept.                |
| existing_parent_cleanup | existing_parent_label | typing game                      | educational video game        | invalid                 | medium       | A 'typing game' is not the same as an 'educational video game'; labels suggest different ontology neighborhoods.                                |
| existing_parent_cleanup | existing_parent_label | slow slicing                     | capital punishment            | invalid                 | medium       | 'slow slicing' is a specific execution method; 'capital punishment' is an associated category rather than direct broader ontology parent.       |
| existing_parent_cleanup | existing_parent_label | computer-aided engineering       | science software              | sibling_or_related      | medium       | Computer-aided engineering is related to science software but not necessarily a subtype of 'science software' directly.                         |
| existing_parent_cleanup | existing_parent_label | future of work                   | economics                     | plausible_but_too_broad | medium       | 'future of work' is a specific economics/sociopolitical theme; direct parent 'economics' is too broad.                                          |
| existing_parent_cleanup | existing_parent_label | basic unemployment allowance     | unemployment benefit          | alias_or_duplicate      | high         | Basic unemployment allowance is essentially an unemployment-benefit subtype; the mapping mirrors the parent label without clear structure.      |
| existing_parent_cleanup | existing_parent_label | educational support scheme       | government program            | plausible_but_too_broad | medium       | An educational support scheme is a specific policy type under government programs; 'government program' may be a broader but not direct parent. |
| existing_parent_cleanup | existing_parent_label | economic history of Saudi Arabia | economic history of the world | plausible_but_too_broad | medium       | Economic history of Saudi Arabia is a specialization of world economic history, but 'world' is too specific or mismatched for direct parent.    |
| existing_parent_cleanup | existing_parent_label | cryptoeconomics                  | economics                     | plausible_but_too_broad | medium       | Cryptoeconomics is a subfield of economics, but the direct parent 'economics' may be too generic for immediate broader relation.                |
