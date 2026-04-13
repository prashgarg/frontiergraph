# Method-v2 Human Usefulness Pack v2

## Status

This pass prepares a refreshed human-usefulness pack aligned to the appendix LLM usefulness object. It does not claim completed ratings.

## Main blinded pack

- total rows: `24`
- graph-selected rows: `12`
- preferential-attachment-selected rows: `12`
- horizons covered: `5, 10, 15`
- target repeat cap per arm: `2`
- source repeat cap per arm: `2`

The rating object is now the same as in the appendix LLM usefulness pass:

- raw triplet `A -> B -> C`
- short construction note
- ratings on readability, interpretability, usefulness, and artifact risk

## Files

- `human_usefulness_pack.csv`
- `human_usefulness_blinded_sheet.csv`
- `human_usefulness_key.csv`
- `instructions.md`

## Intended paper use

This pack provides the external human usefulness check that matches the appendix LLM usefulness object. The comparison is graph-selected versus preferential-attachment-selected items under the same current-usefulness rubric.
