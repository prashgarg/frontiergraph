# Appendix LLM Usefulness Prompt v1

Date: 2026-04-11

## Purpose

This is a lean appendix-only LLM rubric for current usefulness evaluation.

It is meant to parallel the human usefulness task, not the historical benchmark.

The model is asked to judge only:

- readability
- interpretability
- usefulness as a research-question object
- whether the item reads like a graph artifact

It is explicitly **not** asked to judge:

- novelty at the historical cutoff
- importance
- truth
- likely future closure
- journal placement

## Why this version is lean

Compared with the earlier screening prompts, this version:

- hides graph diagnostics
- uses one short system prompt
- uses a very small schema
- caps output with a short reason only
- uses `reasoning.effort = none`
- uses `text.verbosity = low`

That makes it closer to the human rating task and much cheaper to scale.

## Files

- prompt pack: `outputs/paper/117_appendix_usefulness_prompt_v1`
- builder: `scripts/prepare_appendix_usefulness_prompt_v1.py`
- analyzer: `scripts/analyze_appendix_usefulness_prompt_v1.py`

## Intended paper role

If retained, this belongs in the appendix as supplementary current-usefulness evaluation.

It should not replace:

- the graph-only historical benchmark
- the human usefulness validation

## Pilot

The first `10`-item pilot used `gpt-5.4-mini`, `reasoning.effort = none`, and `text.verbosity = low`.

Observed usage:

- input tokens per request: about `401`
- output tokens per request: about `61`
- reasoning tokens: `0`
- estimated cost: about `$0.0058` for `10` items, or about `$0.58` per `1000` items

## No-reason ablation

A second `10`-item pilot removed the free-text `reason` field while keeping the same items and scoring dimensions.

Observed usage:

- input tokens per request: about `390`
- output tokens per request: about `48`
- reasoning tokens: `0`
- estimated cost: about `$0.0051` for `10` items, or about `$0.51` per `1000` items

Compared with the version that includes `reason`:

- output tokens fell by about `21%`
- total cost fell by about `12%`
- mean readability, interpretability, and usefulness scores changed by only about `+0.1`
- artifact-risk labels matched on `80%` of the `10` pilot items

The sample is too small to treat this as definitive, but the no-reason variant looks viable if cost pressure matters.
