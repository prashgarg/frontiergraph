# ReCITE Full Scale (`292`) Matched Prompt Comparison

Date: 2026-04-03

## Goal

Compare the two FrontierGraph extraction prompt families on the full ReCITE benchmark:

- **semantic prompt**
- **variable-level prompt**

using the same:
- benchmark rows (`292`)
- extraction model (`gpt-5-mini`, low reasoning)
- semantic overlap judge (`gpt-5-nano`, low reasoning)

## Runs used

### Variable prompt

- extraction summary:
  - `next_steps/validation/recite_full292_variable_scaled_results.md`
- extraction run:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1`
- judge run:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_gpt5nano_low_v1`

### Semantic prompt

- extraction run:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_semantic_v1`
- cleanup rerun for failed rows:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_semantic_failed3_gpt5mini_low_v1`
- exact-match review:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_semantic_v1/recite_review_complete/aggregate.json`
- judge run:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_semantic_gpt5nano_low_v1`
- single-row judge cleanup:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_semantic_failed1_gpt5nano_low_v1`
- combined judge aggregate:
  - `/tmp/recite_full292_semantic_judge_summary/aggregate.json`

## Exact-match comparison

### Semantic prompt

- mean node precision: `0.027`
- mean node recall: `0.017`
- mean node jaccard: `0.011`
- mean directed edge recall: `0.001`
- mean relaxed edge recall: `0.000`

### Variable prompt

- mean node precision: `0.056`
- mean node recall: `0.027`
- mean node jaccard: `0.020`
- mean directed edge recall: `0.001`
- mean relaxed edge recall: `0.001`

### Exact-match takeaway

At full scale, the variable prompt is clearly better on strict node overlap:
- roughly **2x** semantic prompt precision
- noticeably higher recall and jaccard

But neither prompt makes strict edge matching look good on ReCITE.

## Semantic-judge comparison

### Semantic prompt

- rows: `292`
- mean node overlap score: `0.220`
- mean edge overlap score: `0.128`

Comparability classes:
- `fair_abstract_level_comparison`: `39`
- `partly_fair_but_resolution_mismatch`: `212`
- `mostly_unfair_for_abstract_extraction`: `41`

Recoverability from title + abstract:
- `yes`: `13`
- `partly`: `229`
- `no`: `50`

Main mismatch modes:
- `method_or_dataset_nodes_added`: `268`
- `gold_not_recoverable_from_abstract`: `211`
- `label_wording_only`: `158`
- `broader_vs_narrower_concepts`: `129`
- `paper_summary_vs_variable_graph`: `123`
- `direction_mismatch`: `66`

### Variable prompt

- rows: `292`
- mean node overlap score: `0.235`
- mean edge overlap score: `0.135`

Comparability classes:
- `fair_abstract_level_comparison`: `43`
- `partly_fair_but_resolution_mismatch`: `220`
- `mostly_unfair_for_abstract_extraction`: `29`

Recoverability from title + abstract:
- `yes`: `19`
- `partly`: `232`
- `no`: `41`

Main mismatch modes:
- `method_or_dataset_nodes_added`: `243`
- `gold_not_recoverable_from_abstract`: `191`
- `broader_vs_narrower_concepts`: `188`
- `label_wording_only`: `155`
- `paper_summary_vs_variable_graph`: `127`
- `direction_mismatch`: `63`

### Semantic-judge takeaway

The variable prompt still wins at full scale, but by a **modest** margin:

- node overlap:
  - semantic `0.220`
  - variable `0.235`
  - delta `+0.015`

- edge overlap:
  - semantic `0.128`
  - variable `0.135`
  - delta `+0.007`

So the variable prompt helps, but not enough to say that prompt choice alone solves the validation gap.

## What changed substantively

The variable prompt appears to help mainly by:
- reducing high-level framing and summary nodes
- pulling the graph closer to compact variable-like objects
- making more benchmark rows look at least partly fair for abstract-level comparison

But the core validation problem remains:
- many ReCITE gold graphs are only partly recoverable from abstract text
- many benchmark graphs live at a more decomposed internal mechanism level than FrontierGraph’s natural paper-summary object

## Best interpretation

The strongest honest conclusion is:

> Prompt choice matters, but benchmark comparability matters more.

More concretely:
- switching from semantic to variable extraction improves overlap
- but most full-sample rows are still resolution-mismatched
- exact string overlap remains too harsh to stand alone as a validation metric
- the semantic judge is the right primary validation layer for this benchmark family

## Spend

### Variable full-scale step

From `next_steps/validation/recite_full292_variable_scaled_results.md`:
- extraction: `$1.8447`
- judge: `$0.3152`
- total: `$2.1599`

### Semantic full-scale step

Computed from actual response payload usage across the main semantic run, the 3-row extraction rerun, the main semantic judge run, and the 1-row judge rerun:

- semantic extraction: `$2.1975`
- semantic judge: `$0.3246`
- total: `$2.5221`

### Validation-track cumulative spend

Previous cumulative after the variable full-scale step:
- `$2.5705`

Add semantic full-scale matched comparison:
- `+$2.5221`

Current cumulative validation-track spend:
- **`$5.0926`**

This remains below the current `$10` no-ask ceiling.

## Recommended next move

The next highest-value step is not another full benchmark run.

It is to define a **reportable fair subset** using the semantic judge labels, for example:
- `fair_abstract_level_comparison`
- or `fair_abstract_level_comparison` plus `recoverable = yes`

Then report:
1. full-sample results
2. fair-subset results
3. a small appendix table of:
   - strong matches
   - resolution mismatches
   - clearly unfair rows

That would make the validation story much more persuasive for the paper.
