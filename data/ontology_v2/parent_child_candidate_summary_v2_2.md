# Parent-Child Candidate Pass v2.2

This file summarizes the first full candidate-generation pass for ontology parent-child relations.

## Scope

- ontology concepts considered: `154,522`
- concepts with existing parent labels: `9,182`
- concepts without parents: `145,340`

## Candidate Channels

- `lexical_ngram_parent`: `94,248`
- `semantic_broader_neighbor`: `43,459`
- `existing_parent_label`: `9,182`
- `jel_code_hierarchy`: `4,868`
- `openalex_topic_field`: `1,881`
- `openalex_topic_subfield`: `1,881`

## Structured Signals

- structured candidate rows: `17,812`
- structured rows with ontology-resolved parent ids: `9,347`
- existing inherited parent-label rows: `9,182`
- JEL code-hierarchy rows: `4,868`
- OpenAlex topic subfield rows: `1,881`
- OpenAlex topic field rows: `1,881`

## Notes

- JEL and OpenAlex topic hierarchy signals are imported as structured candidates rather than left implicit.
- Existing parent labels, mostly from Wikidata and reviewed family nodes, are treated as weak priors rather than ground truth.
- Semantic candidates use ontology label embeddings where available and a local lexical fallback for appended reviewed-family nodes.
- Lexical candidates are generated from shorter contiguous label spans and filtered to avoid generic one-word parents when possible.