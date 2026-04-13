# LLM Within-Field V3 Findings

## Scope

This pass moved from abstract prompt design into a concrete within-field screening object:

- candidate universe: endpoint-first within-field shelves from `pool=2000`
- scalar prompt: construction-aware record prompt `G`
- veto prompt: coarse pass/review/fail prompt `E`
- pairwise prompt: construction-aware within-field pairwise prompt `H`

Runs:

- baseline `none` reasoning
- `low` reasoning comparison on `G` and `H`
- two additional `none`-reasoning repeats for stability

Outputs:

- prompt pack: `outputs/paper/105_llm_screening_within_field_v3_prompt_pack`
- runs: `106`, `107`, `108`, `109`
- analysis: `outputs/paper/110_llm_screening_within_field_v3_analysis`

## Main findings

### 1. Weak veto is usable, but only as a weak veto

The right operational object is not a hard LLM filter.

Current weak-veto rule:

- `E = fail`
- `E confidence >= 4`
- `primary_failure_mode` in a substantive failure set
- `G overall_screening_value <= 2`

On the within-field candidate universe, this drops about `16.2%` of candidates.
Those dropped candidates have mean scalar score about `1.78`, which is consistent with
“clear local failures” rather than borderline items.

So:

- `E` should be used as a conservative prune of obvious junk
- `E` should not be used as a hard all-purpose screening model

### 2. Construction-aware scalar prompt is stable enough, but should remain secondary

Prompt `G` uses explicit construction context plus score anchors.

Across three repeated `none`-reasoning runs:

- exact score agreement: about `0.83`
- within-one agreement: `1.00`
- mean score standard deviation: about `0.10`

That is good enough for a secondary scalar signal.
It is not strong enough to make the scalar prompt the only decision rule.

### 3. Construction-aware pairwise prompt is the strongest LLM object so far

Prompt `H` is much more stable than the scalar prompt.

Across three repeated `none`-reasoning runs:

- exact pairwise agreement: about `0.978`
- stable preference share after three-run consensus: about `0.950`
- stable tie share: about `0.051`

So the pairwise within-field task continues to look like the best LLM role:

- local shelf cleanup
- local promotion/demotion inside a field shelf
- not global importance scoring

### 4. `low` reasoning is not a clean drop-in for pairwise screening

Judgment differences from `none` were modest in the overlapping subset, but parse
reliability degraded sharply:

- prompt `G`: usable low-reasoning rows `1734 / 1791`
- prompt `H`: usable low-reasoning rows `817 / 2000`

So the current recommendation is:

- keep `none` for structured within-field screening
- do not switch `H` to `low` without a prompt/schema redesign

### 5. The combined weak-veto plus pairwise rerank improves what users see first

Using:

- weak veto from `E`
- stable pairwise consensus from three `H` runs

the top-`20` slice inside each shelf improves materially:

- mean top-target share: `0.128 -> 0.106`
- mean broad-endpoint share: `0.489 -> 0.094`
- mean low-compression share: `0.533 -> 0.169`
- mean scalar screening value: `1.756 -> 2.075`

This is the first LLM pass that looks operationally useful without trying to become the
main benchmark.

## Interpretation

The strongest current LLM design is:

1. weak veto for obvious failures
2. pairwise within-field reranking on survivors
3. optional scalar score as a secondary diagnostic, not the main arbiter

That matches the broader method logic:

- use the graph stack for retrieval and initial ranking
- use the LLM only for local semantic cleanup where graph signals are weakest

## What this says about prompt design

### What helped

- explicit construction context
- explicit score anchors
- explicit tie permission in the pairwise prompt
- structured outputs with short reasons
- repeated-run stability checks

### What still needs work

- scalar prompt calibration against a stronger reference set
- pairwise prompt behavior under `low` reasoning
- a clean ablation testing whether construction context itself improves quality or only stability
- whether an experimental “journal bar” prompt adds value or only imports prestige/taste

## Current recommendation

For the next LLM-facing implementation pass:

1. keep `E` only as a weak veto
2. use repeated `H` pairwise runs to build stable within-field reranks
3. keep `G` as a secondary scalar diagnostic
4. do not use `low` reasoning for pairwise structured screening in its current form
5. keep the LLM layer as a current-frontier cleanup tool, not as the historical benchmark
