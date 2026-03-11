# Latest

## Live Product
- Site: [frontiergraph.com](https://frontiergraph.com)
- App: [economics-opportunity-ranker-beta-1058669339361.us-central1.run.app](https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app)
- Public default: `Baseline exploratory`
- Live app DB: `concept_exploratory_suppressed_top100k_app_20260309.sqlite`
- Legacy JEL should not be public-facing.

## Current Canonical Position
- FrontierGraph is a concept-graph product, not a JEL-browser product.
- AI is used to extract graph structure from paper text.
- Ontology comparison exists, but `Baseline exploratory` is the default product view.
- Duplicate suppression is part of the recommendation-cleanup layer, not a new scientific measurement model.

## Current Main Artifacts
- Extraction corpus:
  - [fwci_core150_adj150_extractions.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite)
- Enriched paper metadata:
  - [openalex_published_enriched.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/openalex/published_enriched/openalex_published_enriched.sqlite)
- Ontology compare outputs:
  - [frontiergraph_ontology_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_ontology_compare_v1)
- Concept compare outputs:
  - [frontiergraph_concept_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1)
- Suppressed baseline app DB:
  - [concept_exploratory_suppressed_top100k_app.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite)

## Current Counts
- Papers: `242,595`
- Extracted node instances: `1,762,898`
- Extracted edges: `1,443,407`
- Baseline head concepts: `6,752`
- Baseline soft-mapped instances: `471,149`
- Baseline suppressed candidate slice: `100,000`
- Hard-suppressed duplicate-family rows in the top slice: `373`

## Most Important Decisions
- Source-selected published corpus: `core top 150 + adjacent top 150` by mean FWCI.
- Extraction model: `gpt-5-mini`, low reasoning.
- Ontology regimes:
  - Broad: `5 papers / 3 journals`
  - Baseline: `10 papers / 3 journals`
  - Conservative: `15 papers / 3 journals`
- Product default: `Baseline exploratory`
- Best strict comparison view: `Broad strict`
- Public graph/product should not foreground JEL.

## Immediate Next Work
- Simplify and improve the public UX, not the backend.
- Focus on:
  - homepage density
  - graph page aesthetics and usability
  - opportunities page simplification
  - method page progressive disclosure
  - compare page as advanced, not mandatory
- Keep Broad/Conservative available, but secondary.

## Decision Log
- Last major deployment state:
  - Site live on simplified concept-graph framing with the page-by-page polish pass on homepage, graph, opportunities, method, and compare
  - App live on suppressed baseline DB
- Last major product decision:
  - baseline exploratory is the product
  - compare regimes are advanced options
