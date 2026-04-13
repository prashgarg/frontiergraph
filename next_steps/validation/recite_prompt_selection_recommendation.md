# Prompt selection recommendation after the ReCITE 100-paper scale-up

Date: 2026-04-03

## Recommendation

Use this policy for now:

1. **Default to `variable_v1`.**
2. **Do not replace it globally with `variable_v2`.**
3. Use `variable_v2` only as a **targeted fallback** when the initial `variable_v1` extraction looks unusually sparse.

## Why

The `100`-paper node-alignment comparison shows:

- `variable_v1` mean node F1: `0.634`
- `variable_v2` mean node F1: `0.611`

So `variable_v2` is not the better default overall.

But the scale-up also shows a useful fallback pattern.

## Best simple fallback rule

The strongest practical rule from the `100`-paper analysis is:

Run `variable_v2` **only if** all three conditions hold:

1. the `variable_v1` extraction has `<= 6` predicted nodes
2. the abstract has `<= 210` words
3. the title + abstract do **not** contain strong sustainability markers:
   - `sustainab*`
   - `circular economy`

On the `100`-paper comparison, that subset had:

- `11` papers
- mean `delta_f1 = +0.216` for `v2 - v1`
- `72.7%` of those papers improved under `v2`

That is the first routing rule that looks good enough to use as a **fallback**.

## Weaker but still useful fallback rule

If we want a less restrictive version:

- `variable_v1` predicted nodes `<= 6`
- abstract length `<= 210` words

That subset had:

- `15` papers
- mean `delta_f1 = +0.165`
- `66.7%` improved under `v2`

So this is also defensible if we prefer a simpler rule.

## Interpretation

This means:

- `variable_v2` helps most when `variable_v1` appears to have under-produced a compact graph
- that is easier to diagnose **after** a first `variable_v1` pass than before
- so the right design is sequential:
  - run `v1`
  - inspect a small set of lightweight signals
  - rerun `v2` only when those signals say it is worth trying

## What not to do

Do **not** use rules like:

- "if the paper mentions system dynamics, use `v2`"
- "if the paper is about sustainability, use `v2`"
- "if the paper is policy-facing, use `v2`"

The scale-up does not support those broad switches. They are too noisy.

## Operational policy

The practical policy should therefore be:

### Default production path
- run `variable_v1`

### Fallback path
- if the extracted graph has `<= 6` nodes
- and the abstract is short (`<= 210` words)
- and the paper is not obviously in the sustainability / circular-economy phrase family
- then run `variable_v2` as a second pass

### Selection
- keep whichever output looks better under the downstream validation or review workflow
- in benchmark mode, compare both to the semantic alignment metric
- in production mode, flag the `v2` rerun as an alternate candidate graph rather than silently replacing `v1`

## Supporting files

- scale-up result note:
  - `next_steps/validation/recite_alignment_pilot100_scaled_results.md`
- prompt-selection analysis table:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/prompt_selection_analysis.csv`
- prompt-selection analysis summary:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/prompt_selection_analysis.json`
