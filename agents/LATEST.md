# Latest — Updated 2026-04-08

## Current Branch
`paper-incubation-v2ontology` (all four local branches — main, paper-incubation,
paper-incubation-v2ontology — share the same HEAD commit `f40d87a`; all work is
uncommitted in the working tree)

## What Is Currently Uncommitted (working tree)
Two distinct work streams are both uncommitted:

### Stream 1 — paper-incubation work (tracked modified files)
These were edited as part of the paper-incubation agent work:
- `paper/research_allocation_paper.tex` — heavily revised (see PAPER_INCUBATION.md)
- `paper/slides_research_allocation.tex`
- `paper/slides_research_allocation_notes.md`
- Several `src/analysis/*.py` files (learned_reranker, gap_boundary, etc.)
- Several new scripts for paper analyses (SHAP, hypothesis discovery, etc.)

### Stream 2 — v2 ontology build (untracked `??` files)
- `data/ontology_v2/` — entire directory (ontology_v2_final.json, extraction_label_mapping_v2.parquet, embeddings, etc.)
- `next_steps/` — all working notes
- `scripts/build_ontology_v2.py`, `scripts/map_extraction_labels_to_ontology_v2.py`,
  `scripts/patch_sf_exact_matches.py`, `scripts/crawl_wikipedia_economics.py`,
  and ~40 other new scripts

## Current V2 Ontology State
Built and mapped — see ONTOLOGY_V2_BUILD.md and LABEL_MAPPING_V2.md for full detail.

Key artifacts:
- `data/ontology_v2/ontology_v2_final.json` — 153,800 concepts (JEL, Wikidata,
  OpenAlex topics, OpenAlex keywords, Wikipedia)
- `data/ontology_v2/extraction_label_mapping_v2.parquet` — 1,389,907 labels mapped
- `data/ontology_v2/ontology_design_decisions.md` — full methodology log

## Open Decision (immediate next work)
The label mapping has a 77.2% unmatched rate by label count (68.6% by occurrence).
This is a structural gap (ontology = formal concept names; extraction = compound
operationalisation phrases). Three options:
1. Lower soft threshold to ~0.65 (more recall, less precision)
2. Accept gap, use 31.4% matched occurrences as-is
3. Targeted enrichment of top-N unmatched compound terms into ontology

This decision gates the paper's Section on node normalization/ontology rewrite.

## Paper State
`research_allocation_paper.tex` is 1,405 lines. The paper-incubation agent:
- Added full "What the reranker learns" section (line 1135, appendix)
- Added SHAP grouped feature decomposition paragraph to Section 5.2 (line 607)
- Added SHAP robustness figures (graphicspath updated)
- Did many other rewrites throughout

Still uses FG3C-era ontology description in Appendix (lines 881–947):
- References `FG3C...` concept IDs
- Describes old head-pool / force-map / pending-label pipeline
- This is the main paper section that needs to be rewritten for v2 ontology

## Immediate Next Steps
1. Decide unmatched threshold treatment (owner: user decision)
2. Rewrite paper Appendix "Node normalization and ontology construction" (lines 881–947)
   to describe the v2 ontology pipeline instead of the FG3C pipeline
3. Update paper Section 3.3 "Node normalization and concept identity" (line 267)
   to reference v2 ontology counts rather than FG3C counts
4. Commit v2 ontology work on paper-incubation-v2ontology

## Site and App
Still live on FG3C-era data (unchanged since March 2026):
- Site: frontiergraph.com (Cloudflare Pages)
- App: economics-opportunity-ranker-beta-1058669339361.us-central1.run.app (Cloud Run)
- Live DB: `concept_exploratory_suppressed_top100k_app_20260309.sqlite`
Refreshing the live product with v2 ontology data is downstream of resolving the paper.
