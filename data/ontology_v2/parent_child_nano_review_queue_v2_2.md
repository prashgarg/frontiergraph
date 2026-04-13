# Parent-Child Nano Review Queue v2.2

- review rows: `37,208`
- child concepts covered: `29,870`

## Tier counts

- `inferred_lexical`: `19,330`
- `inferred_semantic`: `8,531`
- `existing_parent_cleanup`: `6,304`
- `structured_validation`: `3,043`

## Notes

- `structured_validation` uses JEL code hierarchy and OpenAlex topic field/subfield parents where the parent resolves to an ontology concept.
- `existing_parent_cleanup` captures inherited parent labels already present in the ontology and should be reviewed both for validation and for cleanup.
- `inferred_lexical` keeps only exact normalized subphrase parents with decent lexical support.
- `inferred_semantic` keeps only stronger broader-neighbor candidates from the embedding search.