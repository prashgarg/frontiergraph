# Prompt And Extraction

## Current Extraction Design
Extraction is paper-local.

For each paper title/abstract, the model returns:
- `nodes`
- `edges`

Nodes are paper-local concepts with optional local context.
Edges are paper-local relations with relation and evidence attributes.

## Important Design Decisions
- No transitive closure.
- Reuse the same paper-local node when the same concept genuinely recurs in the same paper.
- Keep concept identity and study context separate.
- Context fields can later be ignored for abstract concept graphs or preserved for context-specific views.

## Current Prompt Pack
Located in:
- [prompts/frontiergraph_extraction_v2](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2)

Important files:
- [schema.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2/schema.json)
- [system_prompt.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2/system_prompt.md)
- [user_prompt_template.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2/user_prompt_template.md)
- [pilot_conditions.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2/pilot_conditions.json)

## Model Choice
Production choice:
- `gpt-5-mini`
- low reasoning
- batch mode for production

Dropped:
- `gpt-5-nano`
- medium-reasoning variants as the production default

## Key Edge Fields
- directionality
- relationship_type
- causal_presentation
- edge_role
- claim_status
- explicitness
- condition_or_scope_text
- sign
- evidence_method
- nature_of_evidence
- uses_data
- sources_of_exogenous_variation
- tentativeness

## Key Evidence Method Enum
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

## Production Extraction Outputs
- merged extraction DB:
  - [fwci_core150_adj150_extractions.sqlite](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite)
- batch and pilot artifacts:
  - [data/pilots/frontiergraph_extraction_v2](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/pilots/frontiergraph_extraction_v2)

## Decision Log
- Extraction is concept-first, not JEL-first.
- Nano models were rejected after pilot behavior and reliability checks.
- `gpt-5-mini` low reasoning is the current extraction standard.
