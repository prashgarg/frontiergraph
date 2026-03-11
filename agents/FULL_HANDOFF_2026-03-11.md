# Full Handoff 2026-03-11

## Purpose
This is the fastest complete handoff for a fresh Codex thread. It is meant to be read before diving into the more detailed files in `agents/`.

Use this file when:
- a new thread starts after context compaction,
- a new agent needs the current project state quickly,
- you want one place that summarizes what FrontierGraph is, what is live, what decisions have already been made, and what work remains.

This file does not replace the topic files in `agents/`. It tells you what matters and where to look next.

## What FrontierGraph Is
FrontierGraph is a deterministic metascience product for economics. It:
- collects a curated literature corpus,
- extracts paper-local concept graphs from titles and abstracts,
- builds concept-level ontology layers,
- computes deterministic ranking signals over missing links in the concept graph,
- cleans the visible recommendation surface with a duplicate-suppression layer,
- and surfaces underexplored concept links as research opportunities.

The product story is:
- AI extracts graph structure from text.
- ranking and cleanup are deterministic and inspectable.
- ontology sensitivity is visible rather than hidden.

The product is no longer framed as a JEL browser. The old JEL-era site/app was only an earlier beta stage and should not be treated as the main public system.

## Current Live State
- Site: [frontiergraph.com](https://frontiergraph.com)
- App: [economics-opportunity-ranker-beta-1058669339361.us-central1.run.app](https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app)
- Public default ontology: `Baseline`
- Public default mapping: `Exploratory`
- Public default ranking surface: suppressed top-100k baseline exploratory concept ranking
- Live runtime DB: `concept_exploratory_suppressed_top100k_app_20260309.sqlite`
- Legacy JEL should not be public-facing

## Canonical Product Defaults
- main ontology regime: `Baseline`
- main mapping mode: `Exploratory`
- best strict comparison reference: `Broad strict`
- duplicate suppression is part of the product-facing ranking cleanup layer
- compare regimes remain available as advanced options, not the main narrative

## Corpus And Data Pipeline
### Main published sample
The current main extraction sample is:
- `core top 150 + adjacent top 150` journals by mean FWCI

This was chosen because:
- full-history full-retained extraction was too expensive,
- source-quality filtering was needed,
- FWCI gave a workable compromise between quality and breadth.

### Corpus counts
- papers: `242,595`
- extracted node instances: `1,762,898`
- extracted edges: `1,443,407`

### Canonical data artifacts
- extraction corpus:
  - [fwci_core150_adj150_extractions.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite)
- extraction JSONL:
  - [fwci_core150_adj150_extractions.jsonl.gz](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.jsonl.gz)
- enriched OpenAlex metadata:
  - [openalex_published_enriched.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/openalex/published_enriched/openalex_published_enriched.sqlite)

### Topic file
For full details, read:
- [CORPUS_AND_RETRIEVAL.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/CORPUS_AND_RETRIEVAL.md)

## Extraction Prompt And Model Design
### Production extraction choice
- model: `gpt-5-mini`
- reasoning: `low`
- schema: nodes + edges only
- no paper-level metadata blob
- no transitive closure

### Important extraction decisions
- use `source` and `target`
- keep paper-local nodes reusable within a paper
- use context fields separately from concept labels
- keep edge attributes like:
  - directionality
  - relationship type
  - causal presentation
  - claim status
  - evidence method
  - sign
  - explicitness

### Evidence method design
The production enum retains common economics abstract-level designs and includes:
- `experiment`
- `DiD`
- `IV`
- `RDD`
- `event_study`
- `panel_FE_or_TWFE`
- `time_series_econometrics`
- `structural_model`
- `simulation`
- `theory_or_model`
- `qualitative_or_case_study`
- `descriptive_observational`
- `prediction_or_forecasting`
- `other`
- `do_not_know`

### Topic file
For full details, read:
- [PROMPT_AND_EXTRACTION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/PROMPT_AND_EXTRACTION.md)

## Ontology History
### v1
- deterministic seed ontology
- useful infrastructure
- low coverage

### v2
- added manual adjudication and embeddings
- produced a reviewed seed ontology
- still conservative

### v3
- tested a coverage-based head rule
- failed because too many labels became heads
- retained only as a diagnostic lesson

### compare_v1
This is the current production comparison basis.

Frozen support-gated regimes:
- Broad: `distinct_papers >= 5` and `distinct_journals >= 3`
- Baseline: `distinct_papers >= 10` and `distinct_journals >= 3`
- Conservative: `distinct_papers >= 15` and `distinct_journals >= 3`

### Current regime counts
Broad:
- heads: `16,505`
- hard mapped instances: `308,222`
- soft mapped instances: `470,225`

Baseline:
- heads: `6,752`
- hard mapped instances: `242,086`
- soft mapped instances: `471,149`

Conservative:
- heads: `4,025`
- hard mapped instances: `207,430`
- soft mapped instances: `475,564`

### Current ontology judgment
- default product ontology: `Baseline`
- default product mapping: `Exploratory`
- best strict comparison view: `Broad strict`

### Canonical compare artifacts
- ontology compare:
  - [frontiergraph_ontology_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_ontology_compare_v1)
- concept compare:
  - [frontiergraph_concept_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1)

### Topic file
For full details, read:
- [ONTOLOGY_AND_CONCEPTS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/ONTOLOGY_AND_CONCEPTS.md)

## Ranking And Recommendation Surface
### Core ranking idea
The concept graph is used to surface missing links worth investigating. The visible recommendation surface is not just the raw candidate score; it also includes a duplicate-cleanup layer.

### Suppressed default surface
Canonical product DB:
- [concept_exploratory_suppressed_top100k_app.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite)

### Suppression summary
- candidate slice scored: `100,000`
- hard same-family suppressed: `373`
- visible after suppression: `99,627`
- top-100 removed: `11`

### Why suppression exists
Ontology and concept comparison still left visible near-synonym loops in the recommendation surface, for example:
- acronym/restatement loops
- concept-variant loops
- subset/superset phrasing that wasted top ranks

The suppression layer cleans the visible ranking without changing the underlying extraction measurement model.

### Topic file
For full details, read:
- [RANKING_AND_SUPPRESSION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/RANKING_AND_SUPPRESSION.md)

## Product And Website State
### Public architecture
- public site: Astro
- deeper explorer: Streamlit

### Public routes
- `/`
- `/graph/`
- `/opportunities/`
- `/method/`
- `/compare/`
- `/downloads/`

### Product narrative
FrontierGraph should be presented as:
- a concept graph of economics and adjacent literature
- a deterministic system that ranks what to study next
- a product where AI extracts graph structure from text, but ranking and cleanup are deterministic and inspectable

### Current UX judgment
What works:
- dark graph-native theme is directionally right
- serious framing is right
- compare functionality is useful as advanced depth

What still matters:
- reduce density
- show one main thing at a time
- hide complexity until asked
- make the graph page graph-first, not dashboard-first
- keep methods/comparison deeper and less mandatory

### Current most likely product direction
- `Baseline exploratory` is the default product
- Broad / Conservative remain advanced comparison modes
- future work should focus more on UX/content than backend infrastructure

### Topic file
For full details, read:
- [WEBSITE_AND_PRODUCT.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/WEBSITE_AND_PRODUCT.md)

## Deployment And Storage
### Live deployment
- Cloudflare Pages for the site
- Google Cloud Run for the app

### Current live runtime DB
- `concept_exploratory_suppressed_top100k_app_20260309.sqlite`

### Buckets
Private runtime bucket:
- `frontiergraph-ranker-data-1058669339361`

Important objects:
- `concept_exploratory_suppressed_top100k_app_20260309.sqlite` (current live runtime DB)
- `app_causalclaims.db` (old rollback DB only)

Public downloads bucket:
- `frontiergraph-public-downloads-1058669339361`

### Storage decisions already made
Deleted safely:
- failed ontology runs
- wrong BigQuery shard
- duplicate fast review-pack folder
- extraction sample staging folder
- failed diagnostic ontology `v3`

### Topic file
For full details, read:
- [DEPLOYMENT_AND_STORAGE.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/DEPLOYMENT_AND_STORAGE.md)

## Measurement And Evaluation
The current stack already includes:
- corpus
- extraction
- ontology comparison
- concept graph
- ranking
- suppression
- site
- live app

The immediate blocker is no longer core measurement infrastructure. The immediate blocker is how to surface the product clearly and convincingly.

### Topic file
For full details, read:
- [MEASUREMENT_AND_EVALUATION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/MEASUREMENT_AND_EVALUATION.md)

## Immediate Next Work
The main priority is product and UX polish, not new backend infrastructure.

Highest-priority tasks:
- simplify homepage density
- make the graph page more elegant and graph-first
- keep opportunities page more curated
- keep methods/comparison deeper and less mandatory
- preserve the top-slice suppression approach rather than attempting huge full-table cleanup jobs

Keep:
- `Baseline exploratory` as the public default
- Broad / Conservative available as advanced comparison views

### Topic file
For full details, read:
- [NEXT_STEPS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/NEXT_STEPS.md)

## Recommended Read Order For A New Thread
If you only have a few minutes:
1. [LATEST.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/LATEST.md)
2. this file
3. [NEXT_STEPS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/NEXT_STEPS.md)

If the next task is product/UX:
1. this file
2. [WEBSITE_AND_PRODUCT.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/WEBSITE_AND_PRODUCT.md)
3. [RANKING_AND_SUPPRESSION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/RANKING_AND_SUPPRESSION.md)
4. [NEXT_STEPS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/NEXT_STEPS.md)

If the next task is data/method:
1. this file
2. [CORPUS_AND_RETRIEVAL.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/CORPUS_AND_RETRIEVAL.md)
3. [PROMPT_AND_EXTRACTION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/PROMPT_AND_EXTRACTION.md)
4. [ONTOLOGY_AND_CONCEPTS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/ONTOLOGY_AND_CONCEPTS.md)
5. [DECISION_LOG.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/DECISION_LOG.md)

If the next task is deployment:
1. this file
2. [DEPLOYMENT_AND_STORAGE.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/DEPLOYMENT_AND_STORAGE.md)
3. [LATEST.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/LATEST.md)

## Decision Log
- This file exists to reduce the amount a new thread must load before becoming useful.
- Topic files remain the source of detail.
- `LATEST.md` plus this file should be enough to bootstrap a new thread quickly.
