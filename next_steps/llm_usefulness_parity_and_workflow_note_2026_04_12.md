## Purpose

This note fixes the role of the LLM screener in the paired-family paper.

The LLM layer is not a substitute for the historical benchmark. It is a secondary workflow layer that asks whether the screened shortlist reads like a usable research-question set to a present-day reader.

That means the right question is not "did the LLM validate the paper?" The right question is:

- can an LLM help post-screen the graph shortlist for readability, interpretability, and artifact risk?
- does that help equally for `path-to-direct` and `direct-to-path`?
- after the path-length axis is run, does looking farther out in the graph improve historical performance at the cost of intelligibility?

## Current State

Existing historical usefulness pipeline:

- pack builder:
  - `scripts/prepare_historical_appendix_usefulness_pack.py`
- response analysis:
  - `scripts/analyze_historical_appendix_usefulness.py`
- prior pack:
  - `outputs/paper/124_historical_appendix_usefulness_pack`
- prior analysis:
  - `outputs/paper/128_historical_appendix_usefulness_analysis`

Existing full run size and cost:

- rows: `12,750`
- input tokens: `6,020,714`
- output tokens: `881,637`
- estimated cost: `$8.48`

Pricing hard-coded in the analysis script:

- input: `$0.75 / 1M`
- output: `$4.50 / 1M`

## What The Current Pack Actually Judges

The current prompt says it is judging a "raw triplet from a literature graph" and that the middle term is an intervening concept.

But the actual selected records are often not rich triplets. In the existing historical pack, many requests are effectively plain direct pairs, for example:

- `Prospective payment system -> hospital charges`
- `Cost sharing -> Length of stay`

The relevant issue is that the current selected historical panel often has:

- `focal_mediator_label = ""`
- `top_mediators_json = []`
- `top_paths_json = []`

So the current LLM screener is often rating a stripped-down relation object, not a rich mechanism object.

That is acceptable as a first-pass appendix check. It is not good enough for a serious paired-family workflow experiment.

## What Must Be Rerun For Direct-To-Path

These pieces must be rerun if the LLM screener survives in the paired-family paper:

1. Historical selection pack for `direct-to-path`
- same arm structure as the existing pack:
  - adopted
  - transparent
  - pref_attach
- same horizons unless we deliberately narrow them
- same shortlist sampling logic

2. LLM response batch for that pack
- same model unless we deliberately change the price/quality point

3. Analysis summary
- summary by arm
- summary by arm x horizon
- artifact-risk breakdown
- examples high/low score

4. Paired comparison output
- `path-to-direct` vs `direct-to-path`
- same rubric
- same item-count logic

## What Is Likely Reusable

The following infrastructure can be reused with limited changes:

- JSON-schema response format
- scoring dimensions:
  - readability
  - interpretability
  - usefulness
  - artifact_risk
- response analysis script
- cost accounting logic
- arm/horizon comparison structure

The main thing that should **not** be reused blindly is the prompt payload shape.

## Prompt Problem

The current prompt is not family-specific enough.

It assumes a generic "triplet" object. That is too vague for the paired-family paper.

### Current framing

- graph triplet
- possible bridge term
- construction note

This hides the fact that the two families represent different research-question objects.

### What `path-to-direct` should show

For `path-to-direct`, the readable object is:

- an implied direct relation
- supported by a short observed path

Suggested payload fields:

- `item_id`
- `family = "path_to_direct"`
- `proposed_direct_relation`
- `supporting_path`
- `question_render`
- `construction_note`

Example logic:

- proposed direct relation:
  - `Broadband access -> business formation`
- supporting path:
  - `Broadband access -> search frictions -> business formation`

### What `direct-to-path` should show

For `direct-to-path`, the readable object is different:

- an existing direct relation
- a proposed missing channel or bridge around it

Suggested payload fields:

- `item_id`
- `family = "direct_to_path"`
- `existing_direct_relation`
- `proposed_path`
- `question_render`
- `construction_note`

Example logic:

- existing direct relation:
  - `Broadband access -> business formation`
- proposed path:
  - `Broadband access -> search frictions -> business formation`

That is not a cosmetic change. The LLM should be told explicitly whether it is seeing:

- a path-supported missing direct relation
or
- a direct relation with a missing mechanism

Otherwise it will grade both against the same vague template.

## Recommended Prompt Redesign

The system prompt should keep the same constraints:

- no outside knowledge
- no judging truth, novelty, prestige, or later success
- judge only present-day readability and usefulness

But the user payload should be family-specific and should include a plain-language rendered question object.

Recommended rendered object:

- `question_render`

Examples:

- `Could broadband access increase business formation by reducing search frictions?`
- `Could transit investment raise employment by reducing commute time?`

This is better than exposing only a raw triplet because it judges the object the reader will actually see.

The raw graph fields can still be included for auditability, but the main judged object should be the rendered question.

## Cost Estimate

### Direct-To-Path family parity

If we rerun the historical usefulness sweep at the same scale as the existing pack, the cost should be roughly the same order:

- about `$8` to `$10`

Reason:

- same number of requests
- similar prompt size
- similar response schema

It could be slightly lower or higher depending on how verbose the rendered question payload becomes, but not by an order of magnitude.

### Path-length later

Do **not** multiply the cost by all path-length settings.

Recommended design:

1. paired-family rerun at the default path setting
2. after the path-length axis is run, rerun only:
   - baseline `len=2`
   - best longer-path contender, likely `len=3` or `len=4`

That means the likely total LLM screener cost is:

- one full paired-family rerun now
- plus one narrower path-length comparison later

Practical envelope:

- paired-family rerun now: about `$8` to `$10`
- later path-length comparison: likely another `$4` to `$10`, depending on whether we rerun the full item count or a reduced comparison pack

So the sensible total planning number is:

- about `$12` to `$20`

not

- `$35+` from naively crossing every family with every path length

## How To Turn This Into A Workflow Experiment

The LLM layer is most useful if it is reframed from "appendix check" to "post-screening workflow layer."

The empirical questions then become:

1. Descriptive
- among historically selected items, does the graph shortlist read better than popularity baselines?

2. Operational
- if an LLM score is used as a post-filter or reranking layer on the graph shortlist, does the final shortlist improve?

This can be tested without making the paper depend on the LLM.

Suggested workflow experiment:

- take the top graph shortlist from each family
- collect LLM usefulness scores
- compare:
  - raw graph shortlist
  - graph shortlist after LLM post-filter
- evaluate:
  - historical hit metrics
  - LLM readability / interpretability / artifact risk

That is a cleaner contribution than treating the LLM as a replacement validator.

## Recommended Execution Order

1. Build a family-aware usefulness pack builder
- `path-to-direct` and `direct-to-path`
- family-specific rendered question object

2. Rerun the historical usefulness sweep for both families at the default path setting

3. Analyze paired-family usefulness results

4. Decide whether the LLM layer stays in the appendix or becomes a small workflow-improvement subsection

5. After the path-length axis is complete, run usefulness only for:
- `len=2`
- best longer-path contender

## Recommendation

Proceed, but do not launch the expensive rerun until the prompt is fixed.

The current pack is cheap enough to repeat. It is not clean enough to treat as the final paired-family version.

The next concrete task should be:

- patch `scripts/prepare_historical_appendix_usefulness_pack.py` to be family-aware and render a readable question object
- then build the new direct-to-path pack and rerun the paired-family usefulness sweep
