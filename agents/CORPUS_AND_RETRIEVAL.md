# Corpus And Retrieval

## Corpus Definition
The main current corpus is a published-journal corpus, not NBER/CEPR working papers.

Source:
- OpenAlex journal-hosted English article universe
- publication window: `1976-2026`
- then source selection into `core` and `adjacent`

## Retrieval Logic
### Stage 1. Broad metadata pull
- OpenAlex metadata-only journal slice
- no abstracts at first
- built a source-level universe

### Stage 2. Source selection
Source-first, not paper-first.

Source buckets:
- `core`
- `adjacent`
- `exclude`
- `review`

Published retained corpus was then selected using:
- `core top 150 + adjacent top 150` by mean FWCI

## Why This Corpus
- Full-history coverage matters more than a short recent window.
- Source quality was chosen instead of crude year truncation.
- `core` and `adjacent` were kept separate because product value comes partly from cross-field frontier links.

## Main Corpus Artifacts
- raw OpenAlex journal metadata:
  - [data/raw/openalex/journal_field20_metadata](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/raw/openalex/journal_field20_metadata)
- source registry:
  - [source_registry.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/raw/openalex/journal_field20_metadata/source_registry.csv)
- enriched metadata DB:
  - [openalex_published_enriched.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/openalex/published_enriched/openalex_published_enriched.sqlite)

## Key Counts
- total selected papers used downstream: `242,595`
- extraction buckets:
  - `core`: `143,136`
  - `adjacent`: `99,459`

## Important Protocol Notes
- [openalex_published_corpus_methods.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/openalex_published_corpus_methods.md)
- [openalex_source_selection_protocol.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/openalex_source_selection_protocol.md)
- [openalex_source_review_log.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/openalex_source_review_log.md)
- [openalex_full_work_enrichment_protocol.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/openalex_full_work_enrichment_protocol.md)

## Decision Log
- Published-only is the main current substrate.
- Working papers are deferred, not abandoned.
- The corpus is source-selected and quality-filtered, not “all economics-tagged OpenAlex.”
