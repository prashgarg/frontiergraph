# LLM Screening Prompt Pack

This note defines the appendix-ready LLM screening pack for a future pilot. The pack is prepared now, but not yet run.

## Goal

Use an LLM only to score local question sharpness, not topic importance, publication probability, citation potential, or policy relevance.

That distinction matters for paper defensibility.

The LLM is screening:

- endpoint specificity
- mediator specificity
- question-object clarity
- mechanism clarity
- canonicality risk
- local crowding risk

It is not forecasting impact.

## Variants

### Prompt A: semantic-blind

Single-candidate scoring using only labels and family tags.

Purpose:
- test whether the model is reacting mainly to wording and semantic broadness

Hidden from the model:
- all rank fields
- field shelf
- theme and semantic-family keys
- graph-local diagnostics
- derived penalties

### Prompt B: record-aware

Single-candidate scoring using labels plus graph-local diagnostics.

Purpose:
- likely production variant if we later use an LLM screening layer

Hidden from the model:
- all rank fields
- field shelf
- theme and semantic-family keys
- derived penalties

### Prompt C: pairwise within-field

Two-candidate comparison within the same field shelf and horizon.

Purpose:
- improve within-field browse ordering without forcing a single global score

Hidden from the model:
- all rank fields
- theme and semantic-family keys
- derived penalties

### Prompt D: scoring-only then rewrite

Second-stage rewrite prompt for survivors only.

Purpose:
- keep screening separate from cosmetic question rewriting

## Paper-facing requirements

When this appears in the paper or appendix, we should explicitly state:

- the LLM screens local question sharpness, not impact or importance
- at least two prompt variants were tested
- agreement across variants is reported
- hidden fields are listed
- structured outputs were used with a strict JSON schema

## API choice

Use the Responses API with Structured Outputs via `text.format`, not function calling.

Reason:
- we want the model's response itself to follow a schema
- we are not asking the model to call tools

Official references:
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/batch#1-prepare-your-batch-file
- https://developers.openai.com/api/docs/guides/prompt-guidance#keep-outputs-compact-and-structured

## Pilot design

Single-candidate pilot:
- `2000` deterministic rows from the `pool=2000` current frontier
- stratified by horizon and rank band

Pairwise pilot:
- `2000` within-field comparisons
- adjacent pairs plus balanced wider-gap pairs
- use the endpoint-first within-field package rather than the older combined-match shelves

## Recommended first live pilot

- model: `gpt-5.4-mini`
- reasoning effort: leave unset or very low for the first pass
- structured outputs: strict schema
- one request per candidate or pair
- batch submission for cost and rate-limit efficiency

Current prepared packs:

- original pack: `outputs/paper/97_llm_screening_prompt_pack`
- endpoint-first pack for the within-field pairwise pilot: `outputs/paper/99_llm_screening_prompt_pack_endpoint_first`

Async execution helper:

- `scripts/run_llm_screening_async.py`

This runner submits the prepared `/v1/responses` requests directly with high concurrency, writes append-only `responses.jsonl` and `errors.jsonl`, and supports resuming interrupted runs.
