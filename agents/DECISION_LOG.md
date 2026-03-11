# Decision Log

This file records the major project decisions that are likely to matter in future threads.

## Corpus And Retrieval

### OpenAlex source-first filtering

Decision:

- classify sources first into `core`, `adjacent`, `exclude`, `review`

Why:

- raw field-based OpenAlex pulls were too noisy
- source identity is more stable than paper-level guessing

### Selected main published sample

Decision:

- use `core top 150 + adjacent top 150` journals by mean FWCI

Why:

- full-history, full-retained extraction was too expensive
- source-quality cut was needed
- FWCI gave a workable compromise

## Prompt And Extraction

### Production model

Decision:

- `gpt-5-mini` low

Why:

- best quality/cost tradeoff in the pilot
- nano models were less reliable
- medium reasoning added more cost and more over-splitting

### Extraction schema

Decision:

- nodes + edges only
- no paper-level metadata blob
- no transitive closure

Why:

- cleaner downstream graph build
- less schema contradiction
- easier deterministic use later

### Evidence method enum

Decision:

- keep `event_study` and `panel_FE_or_TWFE`
- drop `synthetic_control` and `matching`
- replace `RCT` with `experiment`
- add `time_series_econometrics`

Why:

- better fit to abstract-level economics extraction

## Ontology

### v1

Decision:

- build deterministic seed ontology

Outcome:

- machinery worked
- coverage too conservative

### v2

Decision:

- add manual review and embeddings

Outcome:

- useful seed, but still not final product ontology

### v3

Decision:

- test coverage-based head rule

Outcome:

- too many labels became heads
- not production viable

### Compare build

Decision:

- freeze 3 support-gated regimes:
  - Broad `5/3`
  - Baseline `10/3`
  - Conservative `15/3`

Why:

- support gates produced a cleaner, interpretable ontology comparison than the failed coverage-based rule

### Default ontology view

Decision:

- `Baseline exploratory`

Why:

- best compromise between concept compactness and usable coverage

### Best strict comparison view

Decision:

- `Broad strict`

Why:

- most useful strict comparison surface among the current regimes

## Ranking And Cleanup

### Suppression layer

Decision:

- product-facing duplicate cleanup layer on top of baseline exploratory

Why:

- ontology alone did not prevent near-synonym recommendation waste

### Suppression scope

Decision:

- top `100,000` candidate rows only

Why:

- full-table rescoring was too slow
- product value is concentrated in the surfaced ranking slice

## Product And Website

### Public narrative

Decision:

- concept graph + deterministic ranking

Avoid:

- centering the old JEL-first beta

### Product default

Decision:

- baseline exploratory should be the public default
- compare modes stay advanced

### Theme

Decision:

- keep the dark graph-native serious visual identity

Adjustment:

- simplify density and disclosure rather than changing the theme family

## Deployment

### Live runtime DB

Decision:

- switch Cloud Run runtime DB to `concept_exploratory_suppressed_top100k_app_20260309.sqlite`

Why:

- product surface should match the new baseline exploratory default

### Buckets

Decision:

- private bucket = runtime DBs
- public bucket = downloads only

## Cleanups

Deleted:

- failed ontology runs
- wrong BigQuery shard
- duplicate fast review pack
- extraction sample staging folder
- failed ontology `v3` artifacts

Why:

- all were superseded, diagnostic only, or known-bad

