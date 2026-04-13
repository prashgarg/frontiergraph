# LLM Audit of Candidate Questions

Date: 2026-04-04

## Purpose

This audit is not meant to replace the graph-based ranking or to serve as a historical benchmark.

Its main use is diagnostic:

- understand which candidates the current deterministic system surfaces
- see which ones an LLM would keep, downrank, or drop
- inspect the stated reasons
- translate those reasons back into methodology improvements

The most important output is not just a keep/drop label. It is the combination of:

- main reason
- better formulation
- deterministic implication

Those fields let us ask:

- is the candidate bad as is?
- is the direct-edge object too simple?
- is the ontology merging too aggressively?
- is the system missing path-level or node-birth objects?

## Recommended first use

Use this on **current 2026 outstanding candidates**, not as the main historical backtest.

Why:

- leakage is much less problematic for present-day diagnostic use
- the audit is most useful as a precision and methodology-improvement layer
- the questions are directly relevant to the current website and paper narrative

## Best first sample sizes

I would run this in stages.

### Stage 1: diagnostic pilot

- top `100` current candidates

This is enough to see:

- what share are kept, downranked, or dropped
- what reasons dominate
- whether path-to-direct objects are being pruned systematically

### Stage 2: more stable analysis

- top `300` current candidates

This is enough to:

- break results down by candidate type
- compare `gap` versus `boundary`
- compare `path_to_direct` versus richer path-like candidates if available

### Stage 3: broader current shortlist

- top `500` current candidates

This is useful if we want:

- a production-facing filter layer
- a more stable distribution of prune reasons

## What to analyze

### 1. Decision rates

Report:

- `% keep`
- `% downrank`
- `% drop`

### 2. Reason distribution

Report counts and shares for:

- `already_saturated`
- `too_generic_or_hub_driven`
- `weak_mechanism_support`
- `ontology_merge_problem`
- `should_be_path_level_not_direct_edge`
- `should_be_mediator_expansion`
- `requires_new_node_or_new_concept`
- `not_paper_shaped`
- `unclear_directionality`
- `insufficient_local_support`

### 3. Better-formulation distribution

This is especially important.

If many candidates are marked:

- `reframe_as_path_question`
- `reframe_as_mediator_question`
- `split_endpoint_concepts`
- `introduce_new_node`

then the current object is revealing where the methodology needs to expand.

### 4. Cross-tabs by candidate family

For each candidate family, compare:

- keep/downrank/drop rates
- dominant reasons

Suggested rows:

- `path_to_direct`
- `direct_to_path`
- `gap`
- `boundary`

This is exactly where we may learn whether the current direct-edge simplification is too narrow.

### 5. Cross-tabs by current score decile

Check whether the LLM mostly prunes:

- lower-score candidates only
- or also high-score candidates

If many high-score candidates are pruned for the same reason, that points to a systematic deterministic issue.

## How this helps methodology

The audit can be translated into concrete next moves.

- `too_generic_or_hub_driven`
  - strengthen hub penalty
- `weak_mechanism_support`
  - require more path support or mediator diversity
- `ontology_merge_problem`
  - split or parent-child nodes in ontology
- `should_be_path_level_not_direct_edge`
  - add a path-level candidate object
- `should_be_mediator_expansion`
  - add a direct-to-path or mediator-expansion object
- `requires_new_node_or_new_concept`
  - add a node-birth layer

So this is best thought of as a structured failure-labelling tool for the current pipeline.

## Cost estimates

Source for current official pricing:

- [OpenAI API Pricing](https://openai.com/api/pricing/)

Relevant current prices on 2026-04-04:

- `GPT-5.4 nano`
  - input: `$0.20 / 1M`
  - output: `$1.25 / 1M`
- `GPT-5.4 mini`
  - input: `$0.75 / 1M`
  - output: `$4.50 / 1M`

### Practical token estimate per candidate

If we keep the prompt compact, a typical candidate audit should be roughly:

- input: `1,800` to `3,000` tokens
- output: `180` to `350` tokens

### Estimated cost with GPT-5.4 nano

Per candidate:

- lower end: about `$0.00059`
- upper end: about `$0.00104`

Batch sizes:

- `100` candidates: about `$0.06` to `$0.10`
- `300` candidates: about `$0.18` to `$0.31`
- `500` candidates: about `$0.29` to `$0.52`

### Estimated cost with GPT-5.4 mini

Per candidate:

- lower end: about `$0.00216`
- upper end: about `$0.00383`

Batch sizes:

- `100` candidates: about `$0.22` to `$0.38`
- `300` candidates: about `$0.65` to `$1.15`
- `500` candidates: about `$1.08` to `$1.91`

## Recommendation

Start with:

- `GPT-5.4 nano`
- `100` current 2026 candidates

That is enough to learn whether the audit is informative at all, and the cost is negligible.

If the reasons look useful and stable, scale to:

- `300` current candidates

That is likely the best cost-to-insight point.
