# Ranking And Suppression

## Current Default Ranking Surface
Use:
- `Baseline`
- `Exploratory`
- suppressed top-100k candidate surface

Canonical DB:
- [concept_exploratory_suppressed_top100k_app.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite)

## Why Suppression Exists
The ontology compare build showed that the top recommendation lists could still waste rank on near-duplicate pairs such as:
- concept variants
- acronym/restatement loops
- subset/superset concept phrasing

The suppression layer cleans the visible recommendation surface without changing the underlying measurement model.

## What Suppression Does
### Hard same-family block
High-precision removal for clearly same-family pairs.

### Soft duplicate penalty
Down-ranks semantically too-close pairs instead of always deleting them.

## Current Suppression Summary
From:
- [suppression_summary.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/analysis/suppression_summary.json)

Main numbers:
- candidate slice scored: `100,000`
- hard same-family suppressed: `373`
- visible after suppression: `99,627`
- top-100 removed: `11`

## Important Artifacts
- protocol:
  - [frontiergraph_duplicate_suppression_protocol_v1.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/frontiergraph_duplicate_suppression_protocol_v1.md)
- before/after review files:
  - [top100_before.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/analysis/top100_before.csv)
  - [top100_after.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/analysis/top100_after.csv)
  - [removed_by_hard_block.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1/baseline/suppression/analysis/removed_by_hard_block.csv)

## Current Product Judgment
- This suppression layer is part of the product-facing ranking surface.
- It should remain baseline-only until there is a clear reason to extend it to Broad/Conservative.
- The next product work is UX simplification, not more ranking-engine expansion.

## Decision Log
- `Baseline exploratory` plus suppression is the main product recommendation surface.
- The suppression layer is a ranking cleanup layer, not a new ontology version.
