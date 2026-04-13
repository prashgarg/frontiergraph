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

---

## V2 Ontology Build (2026-04-07/08)

### Retire FG3C, build fresh from structured sources

Decision:

- FG3C (6,752 v1 canonical concepts) is archived, not used in v2
- v2 ontology built from 5 structured vocabulary sources only:
  JEL, Wikidata, OpenAlex topics, OpenAlex keywords, Wikipedia
- Result: 153,800 concepts in `data/ontology_v2/ontology_v2_final.json`

Why:

- FG3C had only ~15% match rate against 1.4M extraction labels — too narrow
- FG3C was a derived artifact (support-gated heads from extraction), not a
  structured vocabulary source — circular for ontology purposes
- Structured sources give stable concept identities independent of extraction

Archive locations:
- `data/ontology_v2/_v1_artifacts/` — FG3C-era ontology files
- `scripts/_v1_archive/` — FG3C-era scripts

### Wikipedia BFS crawl as fifth source

Decision:

- crawl Wikipedia depth-5 BFS from `Category:Economics`
- classify with gpt-4.1-nano (title + short_desc + category)
- include at 72.3% acceptance rate → 129,162 concepts

Why:

- JEL + Wikidata + OpenAlex alone gave ~24K concepts — still missed most
  real economics terminology (named phenomena, historical episodes, composite
  indicators, named effects)
- Wikipedia at depth-5 provides the broad named-concept coverage
- gpt-4.1-nano at $3.69 for 184K articles is cheap enough

### Label-only embedding symmetry for extraction matching

Decision:

- embed ontology labels WITHOUT descriptions for the extraction matching index
- embed raw labels without descriptions (they have none)
- store as `ontology_v2_label_only_embeddings.npy` separate from
  `ontology_v2_embeddings.npy`

Why:

- descriptions shift embeddings by mean cosine 0.77–0.82 (self-similarity
  label-only vs label+desc is 0.77–0.82, not 1.0)
- mixing description-enriched ontology against label-only queries biases
  distance measurements
- symmetric label-only vs label-only is the correct comparison

### Surface-form length guard (≥3 words for exact SF matching)

Decision:

- skip surface-form exact matching when SF is < 3 words
- let embedding handle short SFs instead

Why:

- 123,116 rows were wrong-matched because 1-2 word SFs ("ces", "trade",
  "insurance") exactly matched JEL abbreviations or short JEL entries
- examples: "carbon emissions" → JEL "CES" via SF "ces";
  "green finance" → JEL "Insurance" via SF "insurance"
- post-hoc patch script fixed all 123K rows via re-embedding

### Streaming FAISS (10K chunks) for 1.4M label mapping

Decision:

- embed and search in 10K-label streaming chunks rather than all at once
- discard embeddings after each chunk

Why:

- 1.4M × 1536 × 4 bytes ≈ 8.6GB if held in RAM simultaneously
- first run OOM-killed (exit code 137)
- streaming chunks of 10K keep peak RAM under 2GB

### Accept high unmatched rate as structural, not a bug

Decision (provisional — threshold strategy TBD):

- 77.2% of labels fall below 0.75 soft threshold
- this is expected: ontology = formal concept names, extraction = compound phrases
- rank-1 FAISS match stored for all unmatched rows for future threshold changes

Why:

- "renewable energy consumption" ↔ "Renewable Energy" cosine 0.732 (just below 0.75)
- these are genuine vocabulary register differences, not matching failures
- lowering to 0.65 or adding a "candidate" tier covers most high-freq compounds
- user decision pending before paper rewrite proceeds

## Paper Reranker / SHAP (2026-04)

### Grouped feature decomposition resolves multicollinearity

Decision:

- group 34 individual reranker features into 9 interpretable families
- compute within-group PC1 as summary score
- use group-level Shapley values, not individual-feature Shapley values

Why:

- individual-feature VIF exceeds 200 for recency and degree measures
- individual-feature SHAP allocations were unstable across model families
  (logistic, GBM, random forest showed near-zero rank correlation)
- group-level VIF drops below 3.5; cross-model rank correlation exceeds 0.8

Finding: directed causal degree is the dominant group (importance 0.65);
support degree carries a *negative* coefficient once directed degree is
controlled for. "Rising attention" interpretation is stable across model families.

This analysis is in the paper appendix (line 1135, `research_allocation_paper.tex`).

