# ReCITE Full Scale (`292`) Variable-Prompt Validation

Date: 2026-04-02

## What was run

### Extraction run

- Benchmark:
  - `next_steps/validation/data/reCITE/frontiergraph_abstract_benchmark.jsonl`
- Prompt family:
  - variable-level extraction
- Prompt files:
  - `next_steps/validation/prompt_pack/system_prompt_variable_validation.md`
  - `next_steps/validation/prompt_pack/user_prompt_template.md`
- Model:
  - `gpt-5-mini`
- Reasoning:
  - `low`
- Run directory:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1`

### Judge run

- Judge inputs:
  - `next_steps/validation/judge_inputs/recite_full292_variable.jsonl`
- Prompt files:
  - `next_steps/validation/prompt_pack/system_prompt_overlap_judge.md`
  - `next_steps/validation/prompt_pack/user_prompt_overlap_judge_template.md`
  - `next_steps/validation/prompt_pack/overlap_judge_schema.json`
- Model:
  - `gpt-5-nano`
- Reasoning:
  - `low`
- Run directory:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_gpt5nano_low_v1`

## Run completeness

- Main extraction run initially had one timeout on benchmark row `167`.
- That row was rerun successfully and the final parsed result set contains all `292` rows.
- The stale timeout remains recorded in:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/errors.jsonl`
- The actual usable output is:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/parsed_results.jsonl`

## Exact-match comparison

Files:
- `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/recite_review/aggregate.json`
- `data/pilots/frontiergraph_extraction_v2/runs/recite_full292_gpt5mini_low_variable_v1/recite_review/summary.csv`

Aggregate exact metrics:
- rows: `292`
- mean node precision: `0.056`
- mean node recall: `0.027`
- mean node jaccard: `0.020`
- mean directed edge recall: `0.001`
- mean relaxed edge recall: `0.001`

Interpretation:
- strict string-based overlap is still very harsh at full scale
- the variable prompt improves node-level exact overlap relative to the earlier semantic prompt family and pilot runs
- but exact edge recovery remains close to zero on ReCITE

This is consistent with the pilot lesson:
- ReCITE often uses denser and more decomposed internal mechanism graphs than our abstract-level extraction target

## Semantic judge comparison

Files:
- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_gpt5nano_low_v1/judge_summary/aggregate.json`
- `data/pilots/frontiergraph_extraction_v2/judge_runs/recite_full292_variable_gpt5nano_low_v1/judge_summary/summary.csv`

Aggregate judge metrics:
- rows: `292`
- mean node overlap score: `0.235`
- mean edge overlap score: `0.135`

Comparability classes:
- `fair_abstract_level_comparison`: `43`
- `partly_fair_but_resolution_mismatch`: `220`
- `mostly_unfair_for_abstract_extraction`: `29`

Gold recoverability from title + abstract:
- `yes`: `19`
- `partly`: `232`
- `no`: `41`

Mean overlap by recoverability:
- `yes`:
  - mean node overlap: `0.351`
  - mean edge overlap: `0.187`
- `partly`:
  - mean node overlap: `0.246`
  - mean edge overlap: `0.147`
- `no`:
  - mean node overlap: `0.118`
  - mean edge overlap: `0.043`

Most common mismatch modes:
- `method_or_dataset_nodes_added`: `243`
- `gold_not_recoverable_from_abstract`: `191`
- `broader_vs_narrower_concepts`: `188`
- `label_wording_only`: `155`
- `paper_summary_vs_variable_graph`: `127`
- `direction_mismatch`: `63`
- `symbolic_or_state_variable_gold_graph`: `20`
- `little_meaningful_overlap`: `5`

Interpretation:
- the full-scale semantic picture is much better than the exact-match picture
- the dominant case is not “our graph is nonsense”
- the dominant case is “there is some overlap, but the benchmark and our graph operate at different resolutions”

## Best-overlap examples

Top rows by node overlap score from the judge summary:

- benchmark `178`
  - comparability: `fair_abstract_level_comparison`
  - recoverable: `yes`
  - node overlap: `0.83`
  - edge overlap: `0.25`

- benchmark `264`
  - comparability: `partly_fair_but_resolution_mismatch`
  - recoverable: `yes`
  - node overlap: `0.75`
  - edge overlap: `0.15`

- benchmark `7`
  - comparability: `fair_abstract_level_comparison`
  - recoverable: `partly`
  - node overlap: `0.64`
  - edge overlap: `0.78`

- benchmark `91`
  - comparability: `partly_fair_but_resolution_mismatch`
  - recoverable: `partly`
  - node overlap: `0.55`
  - edge overlap: `0.45`

These are useful candidates for a paper appendix table because they show that the benchmark is not uniformly unfair. There are rows where abstract-level recovery is genuinely possible.

## Spend

Estimated from actual response payload token usage and current GPT-5 pricing assumptions used in this project:

### Extraction (`gpt-5-mini`)
- rows: `292`
- input tokens: `694,681`
- cached input tokens: `514,816`
- uncached input tokens: `179,865`
- output tokens: `893,407`
- estimated cost: **`$1.8447`**

### Judge (`gpt-5-nano`)
- rows: `292`
- input tokens: `801,807`
- cached input tokens: `0`
- output tokens: `687,749`
- estimated cost: **`$0.3152`**

### Total for this full-scale step
- **`$2.1599`**

### Total validation-track spend so far
Combining this step with the earlier pilot and DAGverse work:
- previous tracked spend: `$0.4106`
- new full-scale spend: `$2.1599`
- cumulative validation-track spend: **`$2.5705`**

This remains comfortably below the current `$10` no-ask ceiling.

## Bottom line

The strongest honest claim from this full-scale ReCITE run is:

> Exact string overlap makes FrontierGraph look much worse than it really is. At full scale, the better description is that FrontierGraph often recovers a partially overlapping abstract-level graph from title + abstract, but usually at a different level of abstraction than the ReCITE gold graph.

More concretely:
- exact metrics are too harsh to stand alone
- semantic overlap is real
- most cases are partly fair comparisons with resolution mismatch
- only a minority of rows look genuinely well-posed for direct abstract-level recovery

## Recommended next moves

1. Run the **semantic prompt** on full ReCITE as a matched full-scale baseline.
2. Use the judge labels to carve out a **fairer evaluation subset**:
   - `fair_abstract_level_comparison`
   - optionally plus `recoverable = yes`
3. Build a short appendix table with:
   - 3 to 5 good matches
   - 3 to 5 resolution-mismatch cases
   - 2 to 3 clearly unfair benchmark rows
4. Treat ReCITE as evidence on:
   - ontology mismatch
   - abstraction mismatch
   - abstract recoverability limits
   rather than as a pure “did we recover the gold graph exactly?” benchmark
