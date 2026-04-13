# Layered Ontology v1 Spec

## Goal

Define the first next-generation ontology design that keeps the graph usable for ranking while preserving more semantic structure than the current single-layer setup.

The core design choice is:

- keep a graph-ready canonical layer
- but stop forcing every semantic relation into full equivalence

## Layers

### 1. Mention layer

This is the paper-local extracted item.

Required fields:

- `mention_id`
- `paper_id`
- `edge_local_id`
- `raw_string`
- `normalized_string`
- `extraction_role`
  - source
  - target
  - mediator
- `extraction_provenance`
- `sentence_or_span_id` if available
- `context_signature_id` if available

Purpose:

- preserve what the paper actually said
- keep provenance for later audits or re-mapping

### 2. Canonical concept layer

This is the graph-ready concept used for ranking and retrieval.

Required fields:

- `concept_id`
- `preferred_label`
- `status`
  - active
  - deprecated
  - merged_forward
- `type_tags_json`
- `parent_family_id` nullable

Purpose:

- preserve the tractable frontier graph
- remain the main retrieval/ranking layer

### 3. Family / parent layer

This is the broader grouping for concepts that are linked but should not be fully merged.

Required fields:

- `family_id`
- `family_label`
- `family_notes`
- `family_type`
  - outcome_family
  - mechanism_family
  - institution_family
  - method_family
  - context_family

Purpose:

- support grouping, deduplication, and family-aware surfacing without destroying concept distinctions

### 4. Type-tag layer

This is a typed annotation layer that can attach to concepts and mentions.

Initial tag set:

- outcome
- mechanism
- policy_intervention
- institution
- population
- geography
- method
- data_artifact
- broad_theoretical_construct

Purpose:

- support better surfacing
- support better filtering
- support richer frontier types later

## Mapping table

The key redesign rule is that vNext must store the **kind of sameness**.

Required mapping fields:

- `mention_id`
- `concept_id`
- `mapping_kind`
  - exact
  - synonym
  - broader
  - narrower
  - related
  - do_not_merge
- `mapping_confidence`
- `mapping_source`
  - manual
  - hard_embedding
  - soft_embedding
  - lexical
  - inherited
- `review_status`

This is the main structural difference from the current flattened downstream graph.

## Operational rules

1. Ranking uses the canonical concept graph by default.
2. Surfacing may use:
   - canonical concept
   - family
   - type tags
3. Mention-level provenance is never discarded.
4. `do_not_merge` is a first-class state, not an ad hoc note.
5. Family membership is not equivalence.

## Why this is the right first redesign

This design is intentionally conservative.

It preserves what already works:

- a graph-ready canonical layer
- tractable ranking
- interpretable concept IDs

And adds only the structure we repeatedly needed during the current work:

- family grouping
- mapping-kind distinction
- type tags
- preserved provenance
