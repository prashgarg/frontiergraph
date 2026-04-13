# Method v2 Execution Queue

Date: 2026-04-09

## Purpose

This note translates the method-v2 design into an implementation queue.

It is intentionally narrower than `next_steps/method_v2_design.md`. The design note
locks the concepts. This queue names the implementation order and the main code areas.

## Queue order

### 1. Candidate-generation v2

Goal:

- emit family-tagged candidates rather than one undifferentiated pair pool

Main code areas:

- `src/analysis/common.py`
- `src/research_allocation_v2.py`
- `src/analysis/path_evolution.py`

Required changes:

- emit `candidate_family`
- emit `anchor_type`
- emit `evaluation_target`
- preserve enough local evidence to render surfaced questions later

### 2. Transparent retrieval/scoring v2

Goal:

- keep the transparent model as the interpretable first-stage screen
- require score decomposition outputs

Main code areas:

- `src/analysis/model_search.py`
- `src/analysis/ranking_utils.py`

Required changes:

- make transparent score decomposition a first-class output
- keep the benchmark family compact
- ensure tuning stays historically disciplined

### 3. Learned reranker v2

Goal:

- choose one main reranker and one appendix reranker over the fixed candidate universe

Main code areas:

- `src/analysis/learned_reranker.py`
- any training/eval runner already used by current reranker searches

Required changes:

- compare the existing feature families on the fixed candidate universe
- document what the reranker does and does not see
- keep model comparison readable and compact

### 4. Concentration-control layer

Goal:

- evaluate concentration control as a separate layer after reranking

Main code areas:

- `src/analysis/ranking_utils.py`
- reranker output post-processing path

Required changes:

- compare no control, soft sink penalty, and diversification/quota control
- report concentration diagnostics alongside main retrieval metrics

### 5. Evaluation runner and benchmark tables

Goal:

- support layered evaluation rather than one single-task benchmark only

Main code areas:

- current benchmark/eval runners
- path-evolution utilities
- paper-output generation scripts

Required changes:

- keep the direct-link continuity anchor
- add family-aware extension tasks where defined
- emit shortlist diversity and concentration summaries

### 6. Human-usefulness execution

Goal:

- run the prepared validation pack rather than leaving human validation as a placeholder

Main note:

- `next_steps/human_validation_plan.md`

Required changes:

- execute the prepared pack
- summarize ratings cleanly for paper use

## Guardrails

- do not change ontology policy inside this queue
- do not rerun the full paper-facing stack until candidate generation, reranking, and concentration handling are all in place
- keep historical continuity anchor and surfaced question distinct in code and outputs
- keep benchmark-family growth disciplined
