# Ontology And Concepts

## Why Ontology Was Needed
Raw extracted labels were too local and too messy to use directly for the product.
We needed reusable concept layers.

## Ontology History
### v1
- deterministic seed ontology
- conservative
- good infrastructure, low coverage

### v2
- reviewed ontology with manual adjudication and embeddings
- produced a working reviewed seed
- still conservative and low-coverage

### v3
- coverage-based head-rule experiment
- failed because it effectively promoted too many labels into heads
- kept only as a lesson, not as production basis

### compare_v1
The current production comparison basis.

Frozen support-gated regimes:
- Broad: `distinct_papers >= 5` and `distinct_journals >= 3`
- Baseline: `distinct_papers >= 10` and `distinct_journals >= 3`
- Conservative: `distinct_papers >= 15` and `distinct_journals >= 3`

## Current Regime Summary
From:
- [regime_summary.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_ontology_compare_v1/analysis/regime_summary.csv)

### Broad
- heads: `16,505`
- hard mapped instances: `308,222`
- soft mapped instances: `470,225`

### Baseline
- heads: `6,752`
- hard mapped instances: `242,086`
- soft mapped instances: `471,149`

### Conservative
- heads: `4,025`
- hard mapped instances: `207,430`
- soft mapped instances: `475,564`

## Current Product Judgment
- Default product ontology: `Baseline`
- Default product mapping: `Exploratory`
- Best strict comparison view: `Broad strict`

## Important Distinction
### Strict
- conservative identity mapping only
- high precision

### Exploratory
- includes strict mapping and soft nearest-head assignment
- better for product exploration

## Main Artifacts
- ontology compare:
  - [frontiergraph_ontology_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_ontology_compare_v1)
- concept compare:
  - [frontiergraph_concept_compare_v1](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_concept_compare_v1)

## Important Protocol Notes
- [frontiergraph_ontology_protocol_v1.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/frontiergraph_ontology_protocol_v1.md)
- [frontiergraph_head_gate_deliberation.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/frontiergraph_head_gate_deliberation.md)
- [frontiergraph_ontology_compare_protocol_v1.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/frontiergraph_ontology_compare_protocol_v1.md)

## Decision Log
- The product should not present ontology choice as mandatory.
- Baseline exploratory is the main public concept substrate.
- Broad and Conservative remain useful sensitivity and comparison views.
