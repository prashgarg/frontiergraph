# Ontology And Concepts

## Version History

### Era 1 — FG3C (v1 canonical concepts) — ARCHIVED
- 6,752 canonical concepts, IDs like `FG3C000001`
- Built by `build_frontiergraph_concept_v3.py` using support-gated head rules
- Produced `frontiergraph_concept_compare_v1` and `frontiergraph_ontology_compare_v1`
- Used for: live product DB (`concept_exploratory_suppressed_top100k_app_20260309.sqlite`)
  and old paper ontology appendix (lines 881–947 of current .tex — needs rewrite)
- Status: **ARCHIVED**. All FG3C artifacts moved to `data/ontology_v2/_v1_artifacts/`
  and `scripts/_v1_archive/`. Must not appear in v2 analysis.

Why FG3C was retired: narrow (6,752 concepts), JEL-biased, misses most domain concepts
from economics literature. The 1.4M raw extraction labels had only ~15% match rate.

### Era 2 — Ontology V2.3 (frozen baseline, 2026-04-09) — FROZEN FOR METHOD V2
154,359 concepts from 5 structured source families plus reviewed family rows, frozen for
the next method pass. Governing artifacts:
- `data/ontology_v2/ontology_v2_3_candidate.json`
- `data/ontology_v2/extraction_label_mapping_v2_3_candidate.parquet`
- `data/production/frontiergraph_ontology_v2_3_candidate/ontology_v2_3_candidate.sqlite`
- `data/ontology_v2/ontology_v2_3_freeze_note.md`
- `data/ontology_v2/ontology_v2_3_baseline_manifest.json`
- `next_steps/v2_3_ontology_policy.md`

## Current Frozen Ontology Summary
- File: `data/ontology_v2/ontology_v2_3_candidate.json`
- 154,359 rows:
  - Wikipedia `129,032`
  - OpenAlex keywords `9,271`
  - Wikidata `8,383`
  - JEL `5,001`
  - OpenAlex topics `1,876`
  - reviewed family rows `796`
- Extra paper-facing layer:
  - `display_label` for conservative cleanup
  - reviewed `effective_parent_*` / `effective_root_*` hierarchy overlay
- Pause 1 freeze metrics:
  - display-label changes `602`
  - allowed roots `22`
  - ambiguous containers `4`
  - duplicate merges applied `2`
  - promoted intermediate groups `0`
  - effective-parent coverage `13,820`

## Current Mapping State
**`data/ontology_v2/extraction_label_mapping_v2_3_candidate.parquet`:**
- 1,389,907 unique normalized extracted labels
- score bands:
  - linked `92,249`
  - soft `224,043`
  - candidate `524,551`
  - rescue `539,120`
  - unresolved `9,944`
- direct grounding at `0.75`:
  - labels `316,292`
  - occurrences `553,015`

The ontology baseline is frozen. Ranking and benchmark refresh work now happens
downstream of that baseline rather than by continuing to move ontology policy.

## Old Compare Regimes (FG3C era — still live in product)
These still power the live site and app but will be superseded when v2 is used:

Frozen support-gated regimes (papers/journals thresholds):
- Broad: `≥5 papers, ≥3 journals` → 16,505 heads
- Baseline: `≥10 papers, ≥3 journals` → 6,752 heads  ← current live default
- Conservative: `≥15 papers, ≥3 journals` → 4,025 heads

Canonical compare artifacts (FG3C era):
- `data/production/frontiergraph_ontology_compare_v1/`
- `data/production/frontiergraph_concept_compare_v1/`

These remain the production data for now. They will be rebuilt against v2 once
the paper's ontology section is finalized and the mapping threshold is decided.

## Important Distinction (applies to v2 too)
### Strict mapping
Conservative identity mapping only — high precision.

### Exploratory / soft mapping
Includes strict + soft nearest-match assignment — better coverage for product.

## Decision Log
- FG3C retired 2026-04 in favor of v2 (153,800 concept) ontology.
- FG3C artifacts archived (not deleted) — needed to reproduce old results.
- Ontology v2.3 frozen on 2026-04-09 for the next method-v2 pass.
- Raw source provenance remains immutable; `display_label` is cleanup only.
- Reviewed hierarchy now lives in `effective_parent_*` / `effective_root_*`.
- Broad roots and ambiguous containers are explicit policy states.
- Paper-facing ontology appendix rewritten around the v2.3 freeze baseline.
