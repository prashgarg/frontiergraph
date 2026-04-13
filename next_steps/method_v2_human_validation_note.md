# Method-v2 Human Validation Note

## Status

This pass prepares the refreshed next-day rating materials. It does not claim completed ratings.

## Main blinded pack

- total rows: `24`
- graph-selected rows: `12`
- preferential-attachment-selected rows: `12`
- horizons covered: `5, 10, 15`
- target repeat cap per arm: `2`
- source repeat cap per arm: `2`

The main pack is balanced across horizons and de-duplicated across pairs so the comparison does not collapse into one crowded endpoint neighborhood.

Obvious paper-facing label artifacts such as `Fit model`, `Alternative model`, and `proposed technology` are excluded so raters are judging candidate quality rather than ontology cleanup.

## Wording comparison pack

- total rows: `24`
- underlying graph-selected items: `12`

This smaller pack compares raw-anchor wording against mechanism/path wording on the same underlying candidate pairs.

## Files

- `human_validation_pack.csv`
- `human_validation_blinded_sheet.csv`
- `human_validation_key.csv`
- `instructions.md`
- `wording_validation_pack.csv`
- `wording_validation_blinded_sheet.csv`
- `wording_validation_key.csv`
- `wording_instructions.md`

## Intended paper use

The paper can describe this as a prepared blinded validation protocol comparing graph-selected items with preferential-attachment-selected items, plus a smaller wording audit that tests whether mechanism-rich phrasing improves readability and actionability.
