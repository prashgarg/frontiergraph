# Parent-Child Candidate Pass v2.2

This note summarizes the first full parent-child candidate generation pass over the `v2.2` ontology.

## What We Confirmed

- The merged ontology is still structurally flat outside a few sources:
  - total concepts: `154,522`
  - concepts with existing `parent_label`: `9,182`
  - concepts without parent: `145,340`
- Most existing hierarchy comes from:
  - `wikidata`: `8,383`
  - `frontiergraph_v2_1_reviewed_family`: `767`
  - `frontiergraph_v2_2_guardrailed_child_family`: `32`
- JEL and OpenAlex topic source data do contain hierarchy signals, but those were largely flattened in the merged ontology build.

## Candidate Universe

Artifacts:

- candidate table: `data/ontology_v2/parent_child_candidate_pairs_v2_2.parquet`
- queue table: `data/ontology_v2/parent_child_nano_review_queue_v2_2.parquet`
- queue note: `data/ontology_v2/parent_child_nano_review_queue_v2_2.md`

Full candidate universe:

- total candidate rows: `155,519`
- child concepts with at least one candidate: `82,189`
- child concepts with at least one ontology-resolved parent candidate: `80,000`

By channel:

- `lexical_ngram_parent`: `94,248`
- `semantic_broader_neighbor`: `43,459`
- `existing_parent_label`: `9,182`
- `jel_code_hierarchy`: `4,868`
- `openalex_topic_field`: `1,881`
- `openalex_topic_subfield`: `1,881`

## What Looks Good

- The pass is broad enough to cover most of the ontology without becoming all-pairs.
- Structured hierarchy signals are now explicit:
  - JEL code-hierarchy candidates: `4,868`
  - OpenAlex topic field/subfield candidates: `3,762`
- The lexical pass is especially strong for flat sources:
  - `64,084` children get at least one lexical parent candidate
- The semantic pass is useful for the flatter sources:
  - overall semantic cosine median: `0.723`
  - JEL semantic median: `0.750`
  - OpenAlex keyword semantic median: `0.743`
  - Wikipedia semantic median: `0.764`

## What Still Looks Risky

- Existing inherited parent labels are noisy:
  - `7,085` `existing_parent_label` rows are unresolved or cross-domain suspicious
- JEL hierarchy is present, but only `27.1%` of JEL code-parent labels resolve cleanly to an ontology concept id in the current merged ontology.
- OpenAlex topics carry structured field/subfield strings, but many of those strings are not themselves ontology concepts.
- Semantic candidates for our reviewed-family nodes are weak because those appended nodes do not have native embedding vectors from the original ontology build:
  - `frontiergraph_v2_1_reviewed_family` semantic median: `0.408`

## Suggested Nano Staging

Use the smaller queue, not the full candidate universe.

Recommended review queue:

- `37,208` rows covering `29,870` child concepts

Tier counts:

- `inferred_lexical`: `19,330`
- `inferred_semantic`: `8,531`
- `existing_parent_cleanup`: `6,304`
- `structured_validation`: `3,043`

Interpretation:

- `structured_validation` should help calibrate whether the relation-classifier behaves sensibly on easier hierarchy-like cases.
- `existing_parent_cleanup` is probably the highest-leverage ontology-cleanup bucket.
- `inferred_lexical` is the best source of likely missing parent links.
- `inferred_semantic` should be treated more cautiously and likely reviewed after lexical.

## Recommendation

The next pass should not be “review all 155k candidates.”

It should be:

1. run `gpt-5.4-nano` on `structured_validation` and `existing_parent_cleanup`
2. run it next on `inferred_lexical`
3. treat `inferred_semantic` as the last tier, or raise the semantic threshold further before spending

That keeps the review:

- broad
- source-aware
- defensible
- and targeted toward the highest-value hierarchy cleanup first
