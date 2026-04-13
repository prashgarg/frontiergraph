# Ontology v2.3 Frozen Baseline

Date: 2026-04-09

This note freezes the current ontology baseline for the next paper-method phase.

## Status

- Baseline name: `ontology_v2_3_frozen_baseline`
- Freeze policy: factual errata only
- Intended use: paper-facing ontology baseline for the method-v2 redesign

## Frozen artifacts

- ontology JSON: `data/ontology_v2/ontology_v2_3_candidate.json`
- mapping parquet: `data/ontology_v2/extraction_label_mapping_v2_3_candidate.parquet`
- inspection sqlite: `data/production/frontiergraph_ontology_v2_3_candidate/ontology_v2_3_candidate.sqlite`
- policy note: `next_steps/v2_3_ontology_policy.md`
- evaluation note: `data/ontology_v2/ontology_v2_3_evaluation.md`
- baseline manifest: `data/ontology_v2/ontology_v2_3_baseline_manifest.json`

## What is frozen

- raw source provenance remains immutable
- `display_label` is a paper-facing cleanup layer, not rewritten source truth
- `effective_parent_*` and `effective_root_*` are the reviewed hierarchy overlay
- broad roots are allowed where forcing an extra parent would be artificial
- ambiguous containers are explicit rather than silently over-cleaned
- no conservative intermediate-parent promotions cleared the Pause 1 bar

## Freeze metrics

- ontology rows: `154,359`
- display-label changes: `602`
- allowed roots: `22`
- ambiguous containers: `4`
- duplicate merges applied in the Pause 1 pass: `2`
- promoted intermediate groups: `0`
- effective-parent coverage: `13,820`
- direct grounding at `0.75`: `316,292` labels and `553,015` occurrences

## Interpretation

This is a conservative ontology freeze, not a claim that the ontology is complete.
The main gain is stability and provenance discipline:

- the ontology is broad and source-aggregated rather than hand-built end to end
- the hierarchy layer is reviewed where supported and left flat where forcing structure would be arbitrary
- unresolved and ambiguous cases are parked explicitly instead of being hidden by aggressive normalization

The next phase should treat this ontology as fixed support infrastructure while candidate generation, ranking, concentration control, and evaluation are redesigned separately.
