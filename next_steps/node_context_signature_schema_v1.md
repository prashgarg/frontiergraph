# Node Context Signature Schema v1

## Goal

Attach context to canonical concepts without exploding the ontology into thousands of overly narrow context-specific nodes.

The rule is:

- node context is metadata on concepts by default
- not a reason to create a new concept automatically

## Context signature object

Each canonical concept can have one or more context-signature summaries built from its supporting mentions and edges.

Required fields:

- `concept_id`
- `context_signature_id`
- `support_count`
- `paper_count`
- `weight_sum`

## Signature dimensions

### Geography

- `top_geographies_json`
- `geography_entropy`
- `geography_confidence`

Examples:

- China
- United States
- OECD
- cross-country

### Population

- `top_populations_json`
- `population_entropy`
- `population_confidence`

Examples:

- households
- firms
- students
- workers

### Sector

- `top_sectors_json`
- `sector_entropy`
- `sector_confidence`

Examples:

- agriculture
- manufacturing
- energy
- banking

### Unit of analysis

- `top_units_json`
- `unit_confidence`

Examples:

- individual
- household
- firm
- city
- province
- country

### Method footprint

- `top_methods_json`
- `method_entropy`
- `method_confidence`

### Domain / journal footprint

- `top_domains_json`
- `top_journals_json`
- `domain_entropy`

## Design rules

1. Context signatures summarize usage; they do not redefine concept identity by default.
2. New concept creation from context should require repeated evidence and a review decision.
3. Surfaced frontier questions may use context signatures to make questions more precise.
4. Context signatures can later support:
   - context-transfer frontier
   - geography gaps
   - population gaps
   - sector-transfer questions

## Why this matters

Many concepts in economics are interpretable only with setting.

Examples:

- employment in a labor-market paper vs macro panel
- willingness to pay in environmental valuation vs other stated-preference settings
- innovation in green-development work vs industrial policy

The current graph mostly discards that setting information. This schema preserves it without fragmenting the graph too early.
