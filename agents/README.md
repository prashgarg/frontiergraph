# Agents Handoff Pack

This folder is the canonical handoff pack for FrontierGraph. A new thread should
start here rather than trying to reconstruct the project from chat history.

## Start Here
- **[LATEST.md](LATEST.md)** — current live state, uncommitted work, immediate next steps
- **[FULL_HANDOFF_2026-04-08.md](FULL_HANDOFF_2026-04-08.md)** — complete compact handoff for a fresh thread
- [NEW_THREAD_BRIEF.md](NEW_THREAD_BRIEF.md) — quick bootstrap for a new thread
- [THREAD_START_TEMPLATE.md](THREAD_START_TEMPLATE.md) — ready-made first message template

## Core State
- [PROJECT_STATE.md](PROJECT_STATE.md) — system state, live product, canonical artifacts
- [NEXT_STEPS.md](NEXT_STEPS.md) — ordered work queue
- [DECISION_LOG.md](DECISION_LOG.md) — major decisions and rationale

## Paper Work
- [PAPER_INCUBATION.md](PAPER_INCUBATION.md) — branch `paper-incubation`, what was done,
  pending plan files, how to resume
- [PAPER_INCUBATION_V2ONTOLOGY.md](PAPER_INCUBATION_V2ONTOLOGY.md) — branch
  `paper-incubation-v2ontology`, v2 ontology build state, open threshold decision,
  paper rewrite plan

## V2 Ontology
- [ONTOLOGY_V2_BUILD.md](ONTOLOGY_V2_BUILD.md) — 153,800-concept ontology, sources,
  build decisions, canonical artifacts
- [LABEL_MAPPING_V2.md](LABEL_MAPPING_V2.md) — 1.4M label mapping, FAISS pipeline,
  thresholds, unmatched rate interpretation
- [ONTOLOGY_AND_CONCEPTS.md](ONTOLOGY_AND_CONCEPTS.md) — full history (FG3C era → v2)

## Data And Corpus
- [CORPUS_AND_RETRIEVAL.md](CORPUS_AND_RETRIEVAL.md) — OpenAlex retrieval, source
  selection, counts, retained corpora

## Extraction And Measurement
- [PROMPT_AND_EXTRACTION.md](PROMPT_AND_EXTRACTION.md) — extraction prompt design,
  schema, model choices, batch strategy
- [MEASUREMENT_AND_EVALUATION.md](MEASUREMENT_AND_EVALUATION.md) — graph build,
  ranking signals, evaluation

## Ranking And Cleanup
- [RANKING_AND_SUPPRESSION.md](RANKING_AND_SUPPRESSION.md) — baseline exploratory,
  duplicate suppression, recommendation surface

## Product And Deployment
- [WEBSITE_AND_PRODUCT.md](WEBSITE_AND_PRODUCT.md) — site/app narrative, live UX,
  product defaults
- [DEPLOYMENT_AND_STORAGE.md](DEPLOYMENT_AND_STORAGE.md) — Cloudflare, Cloud Run,
  buckets, runtime DBs

## Archival
- [FULL_HANDOFF_2026-03-11_ARCHIVED.md](FULL_HANDOFF_2026-03-11_ARCHIVED.md) — old
  handoff, FG3C era (pre-v2 ontology)
- [SESSION_HANDOFF_2026-03-01.md](SESSION_HANDOFF_2026-03-01.md) — older session
  handoff, historical only

## Rules For Future Threads
- Treat files in this folder as the current memory of the project.
- Prefer current production artifacts over chat recollection.
- **FG3C must not appear in v2 analysis.** `FG3C` concept IDs or
  `frontiergraph_concept_compare_v1` in a v2 context = contamination error.
- The correct v2 ontology is always `data/ontology_v2/ontology_v2_final.json`.
- All current work is uncommitted on branch `paper-incubation-v2ontology`. Check
  LATEST.md for the full list before starting new work.
- Update these files whenever a major decision, deployment, or measurement change happens.
