# Project State — Updated 2026-04-08

## What FrontierGraph Is
FrontierGraph is a deterministic metascience system for economics. It:
- extracts paper-local concept graphs from paper title/abstract text,
- merges those into a large concept graph,
- applies ontology regimes and mapping modes,
- computes deterministic ranking signals over missing or underexplored concept links,
- cleans the visible recommendation surface with a duplicate-suppression layer,
- and surfaces research opportunities through a public site and an interactive app.

## Current Branch
`paper-incubation-v2ontology` — all work uncommitted in working tree.

## Public Default (FG3C era — still live)
- Ontology regime: `Baseline` (FG3C, 6,752 heads)
- Mapping mode: `Exploratory`
- Ranking surface: suppressed baseline top-100k
- Public framing: concept graph, not legacy JEL browse

## Live State
- Site: frontiergraph.com (Cloudflare Pages)
- App: economics-opportunity-ranker-beta-1058669339361.us-central1.run.app (Cloud Run)
- Live runtime DB: `concept_exploratory_suppressed_top100k_app_20260309.sqlite`

## Core Production Counts (from extraction corpus)
- Papers: 242,595
- Extracted node instances: 1,762,898 (= 1,762,899 occurrences in label table)
- Extracted edges: 1,443,407
- Mean nodes per paper: 7.267
- Mean edges per paper: 5.95

## V2 Ontology Counts (NEW — not yet in live product)
- Ontology concepts: 153,800
- Unique normalized labels in mapping: 1,389,907
- Linked (≥0.85): 92,249 labels / 241,435 occurrences
- Soft (0.75–0.85): 224,043 labels / 311,580 occurrences
- Unmatched (<0.75): 1,073,615 labels / 1,209,884 occurrences

## FG3C Counts (live product, being replaced)
From ontology compare:
- Broad heads: 16,505
- Baseline heads: 6,752
- Conservative heads: 4,025
- Baseline hard mapped instances: 242,086
- Baseline soft mapped instances: 471,149

From baseline suppression:
- Candidate slice scored: 100,000
- Visible after suppression: 99,627
- Hard same-family suppressed rows: 373
- Top-100 rows removed: 11

## Canonical Artifacts

### Active V2 (current work)
- `data/ontology_v2/ontology_v2_final.json` — 153,800 concepts
- `data/ontology_v2/ontology_v2_label_only_embeddings.npy` — matching embeddings
- `data/ontology_v2/extraction_labels_v2.parquet` — 1.4M label table
- `data/ontology_v2/extraction_label_mapping_v2.parquet` — mapping results
- `data/ontology_v2/ontology_design_decisions.md` — methodology log

### Extraction (unchanged)
- `data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite`
- `data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.jsonl.gz`

### Enriched paper metadata (unchanged)
- `data/processed/openalex/published_enriched/openalex_published_enriched.sqlite`

### FG3C era (live product, being replaced)
- `data/production/frontiergraph_ontology_compare_v1/`
- `data/production/frontiergraph_concept_compare_v1/`
- `data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite`

### FG3C artifacts (archived)
- `data/ontology_v2/_v1_artifacts/` — FG3C-era ontology files
- `scripts/_v1_archive/` — FG3C-era scripts

## Current Work Priority
1. Unmatched threshold decision → paper ontology rewrite → commit v2 work
2. Paper pending plan files (see NEXT_STEPS.md)
3. Rebuild concept graph with v2 mapping (after paper section finalized)
4. Refresh live product with v2 data

## Decision Log
- FG3C archived 2026-04; v2 ontology is the new canonical substrate.
- Paper-incubation SHAP/reranker work fully implemented.
- Paper's ontology appendix still FG3C-era — pending v2 rewrite.
