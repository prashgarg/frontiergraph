# Project State

## What FrontierGraph Is
FrontierGraph is a deterministic metascience system for economics. It:
- extracts paper-local concept graphs from paper title/abstract text,
- merges those into a large concept graph,
- applies ontology regimes and mapping modes,
- ranks missing or underexplored concept links as research opportunities,
- surfaces those rankings through a public site and an interactive app.

## Public Default
- Ontology regime: `Baseline`
- Mapping mode: `Exploratory`
- Ranking surface: suppressed baseline top-100k
- Public framing: concept graph, not legacy JEL browse

## Live State
- Site: [frontiergraph.com](https://frontiergraph.com)
- App: [economics-opportunity-ranker-beta-1058669339361.us-central1.run.app](https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app)
- Cloudflare Pages is live on the rewritten concept-graph site.
- Cloud Run is live on the new concept DB:
  - `concept_exploratory_suppressed_top100k_app_20260309.sqlite`

## Core Production Counts
From the merged extraction corpus:
- papers: `242,595`
- extracted node instances: `1,762,898`
- extracted edges: `1,443,407`
- mean nodes per paper: `7.267`
- mean edges per paper: `5.95`

From ontology compare:
- Broad heads: `16,505`
- Baseline heads: `6,752`
- Conservative heads: `4,025`
- Baseline hard mapped instances: `242,086`
- Baseline soft mapped instances: `471,149`

From baseline suppression:
- candidate slice scored: `100,000`
- visible after suppression: `99,627`
- hard same-family suppressed rows: `373`
- top-100 rows removed: `11`

## Canonical Artifacts
- Extraction corpus:
  - [fwci_core150_adj150_extractions.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite)
- Enriched paper metadata:
  - [openalex_published_enriched.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/openalex/published_enriched/openalex_published_enriched.sqlite)
- Ontology compare:
  - [frontiergraph_ontology_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_ontology_compare_v1)
- Concept compare:
  - [frontiergraph_concept_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1)
- Baseline suppressed app DB:
  - [concept_exploratory_suppressed_top100k_app.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite)

## Current Product Judgment
- The backend is largely in place.
- The current main work is product/UX simplification and polish.
- The app/site should not foreground legacy JEL.
- Broad / Conservative exist for comparison, not as the main public narrative.

## Decision Log
- Product default is `Baseline exploratory`.
- `Broad strict` is the best strict comparison mode, but advanced.
- Suppression is a ranking cleanup layer on top of baseline exploratory.
