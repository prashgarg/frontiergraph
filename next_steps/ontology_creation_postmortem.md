# Ontology Creation Postmortem

## Why this note exists

We now have enough evidence from reranking, shortlist cleanup, and targeted ontology patches to describe what the ontology actually is today, rather than what we hoped it was.

That matters because the downstream research-allocation graph behaves like a **single canonical concept graph**, even though the upstream ontology builders already contain richer structure.

## What the current ontology pipeline is today

### Upstream `v2`

The `v2` builder combines:

- manual pair decisions
- manual negative overrides
- embedding-based tail-to-head mapping
- context-fingerprint tables

Relevant files:

- [scripts/build_frontiergraph_ontology_v2.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_frontiergraph_ontology_v2.py)
- [src/ontology_v2.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src/ontology_v2.py)

The important point is that `v2` is already **not** just raw embedding clustering. It includes:

- explicit blocked auto-merge pairs
- isolate-label logic
- manual adjudication of same vs different concept
- context-fingerprint population
- embedding review queues

So `v2` already knows that not all lexical similarity should become sameness.

### Upstream `v3`

The `v3` builder goes further. It adds:

- coverage-based head selection
- hard mappings
- soft mappings
- tail soft-candidate tables
- soft pending queues
- context fingerprint tables for hard and soft mappings separately

Relevant file:

- [scripts/build_frontiergraph_ontology_v3.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_frontiergraph_ontology_v3.py)

Key design signals visible in code:

- `coverage_target` default `0.90`
- hard embedding thresholds:
  - auto `0.93`
  - review `0.88`
  - margin `0.03`
  - graph threshold `0.45`
- separate tables for:
  - `instance_mappings_hard`
  - `instance_mappings_soft`
  - `tail_soft_candidates`
  - `soft_map_pending`
  - `context_fingerprints_hard`
  - `context_fingerprints_soft`

So upstream `v3` is already trying to preserve uncertainty and mapping type.

## What gets flattened downstream

The downstream research-allocation pipeline mostly consumes a graph where each endpoint is effectively a single canonical concept:

- `source_concept_id`
- `target_concept_id`
- one preferred label

That means several distinctions are mostly lost by the time we rank or surface questions:

- synonym vs broader/narrower relation
- mapping confidence
- hard vs soft assignment
- mention-level provenance
- family / parent structure
- context fingerprint detail
- evidence-type differences beyond a few coarse fields

## What the current ontology is good at

The current ontology is good at:

- collapsing a very large string space into a tractable concept graph
- removing obvious duplicates
- making graph ranking feasible
- supporting a first-generation frontier system

Without that flattening, most of the current paper would not exist.

## What the current ontology is weak at

The current ontology is weak at preserving the **kind of sameness** involved.

Examples:

- `CO2 emissions` vs `environmental quality`
- `willingness to pay` vs narrower valuation constructs
- `environmental pollution` vs `environmental degradation`
- context-specific variants that are related but not identical

In practice, that creates three downstream problems:

1. over-merged families
2. underrepresented hierarchy
3. inability to ask frontier questions in context or evidence space

## Main conclusion

The current ontology is best described as:

- **multi-step upstream**
- **flattened single-layer downstream**

That is why narrow patches help, but also why they eventually hit a ceiling.

The next ontology should preserve more of what the upstream builders already know, instead of compressing everything into one concept layer before frontier ranking.
