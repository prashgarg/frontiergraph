# Measurement And Evaluation

## High-Level Pipeline
The pipeline is:
1. collect papers
2. extract paper-local graphs
3. merge them
4. build ontology / concept views
5. compute deterministic ranking signals
6. surface opportunities
7. clean the visible ranking with duplicate suppression

## What The Ranker Measures
The recommendation layer is trying to identify promising missing or underexplored links between concepts.

Main signals include:
- path support
- mediator / motif support
- gap / underexploration signal
- hub penalties
- co-occurrence and neighborhood structure

These produce a base candidate score.

## Important Clarification
Duplicate suppression is **not** a new scientific measurement model.
It is a post-measurement ranking cleanup layer for the visible product surface.

So:
- base score = measurement
- suppression = product-facing cleanup on top of measurement

## Current Canonical Summary
From:
- [fwci_core150_adj150_corpus_summary.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/analysis/fwci_core150_adj150_corpus_summary.json)

Main numbers:
- papers: `242,595`
- node instances: `1,762,898`
- edges: `1,443,407`
- mean nodes/paper: `7.267`
- mean edges/paper: `5.95`

## Evaluation Direction
The current compare/evaluation emphasis is:
- ontology sensitivity
- ranking surface quality
- whether top recommendations are meaningful rather than duplicate-heavy

The immediate product benchmark is:
- does the recommendation list look more actionable and less redundant?

## Important Related Files
- [RANKING_AND_SUPPRESSION.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/RANKING_AND_SUPPRESSION.md)
- [ONTOLOGY_AND_CONCEPTS.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/ONTOLOGY_AND_CONCEPTS.md)

## Decision Log
- The scientific substrate is the concept graph and deterministic ranking signals.
- Product cleanup should not be mistaken for ontology or measurement redesign.
