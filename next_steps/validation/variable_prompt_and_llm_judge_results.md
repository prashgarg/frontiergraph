# Variable Prompt and LLM Judge: Results

Date: 2026-04-01

## What was tested

We added two new validation components:

1. a **variable-level extraction prompt**
2. a **structured LLM overlap judge**

The goal was to test whether a substantial part of the validation gap comes from graph-object choice and ontology, rather than from obviously bad extraction.

## Prompt families

### Semantic extraction prompt

File:
- `next_steps/validation/prompt_pack/system_prompt_validation.md`

Target:
- paper-local semantic graph
- can include methods, datasets, institutions, and framing nodes if they are salient in the abstract

### Variable-level extraction prompt

File:
- `next_steps/validation/prompt_pack/system_prompt_variable_validation.md`

Target:
- compact variable-level or figure-level causal graph
- prefers treatments, outcomes, mediators, confounders, and covariates
- discourages high-level paper-summary nodes

### Overlap judge prompt

Files:
- `next_steps/validation/prompt_pack/system_prompt_overlap_judge.md`
- `next_steps/validation/prompt_pack/user_prompt_overlap_judge_template.md`
- `next_steps/validation/prompt_pack/overlap_judge_schema.json`

Target:
- judge semantic overlap between gold graph and predicted graph
- separate:
  - label mismatch
  - broader/narrower concept mismatch
  - paper-summary vs variable-graph mismatch
  - unrecoverable-from-abstract cases

## Models used

Extraction:
- `gpt-5-mini`
- reasoning effort: `low`

Overlap judge:
- `gpt-5-nano`
- reasoning effort: `low`

## What was run

### Semantic runs already available

- ReCITE pilot:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2`
- DAGverse broad 5:
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1`
- DAGverse curated 5:
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse_curated5_gpt5mini_low_v1`

### New variable-level runs

- ReCITE pilot 10:
  - `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_variable_v1`
- DAGverse full 25:
  - `data/pilots/frontiergraph_extraction_v2/runs/dagverse25_gpt5mini_low_variable_v1`

### Judge run

- Combined semantic vs variable comparison on `40` rows:
  - ReCITE `10` semantic
  - ReCITE `10` variable
  - DAGverse broad `5` semantic
  - DAGverse broad `5` variable
  - DAGverse curated `5` semantic
  - DAGverse curated `5` variable

Files:
- judge inputs:
  - `next_steps/validation/judge_inputs/combined_semantic_vs_variable_40.jsonl`
- judge run:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/semantic_vs_variable_40_gpt5nano_low_v2`
- judge summary:
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/semantic_vs_variable_40_gpt5nano_low_v2/judge_summary/aggregate.json`
  - `data/pilots/frontiergraph_extraction_v2/judge_runs/semantic_vs_variable_40_gpt5nano_low_v2/judge_summary/summary.csv`

## Exact-match results

### ReCITE pilot 10

Semantic prompt:
- mean node precision: `0.029`
- mean node recall: `0.022`
- mean edge recall directed: `0.000`

Variable prompt:
- mean node precision: `0.109`
- mean node recall: `0.073`
- mean edge recall directed: `0.000`

Interpretation:
- the variable prompt helps **node alignment materially**
- it does **not** fix edge overlap on ReCITE
- this is consistent with ReCITE often using denser and more decomposed internal mechanism graphs

### DAGverse broad 5

Semantic prompt:
- node precision: `0.000`
- node recall: `0.000`
- edge recall: `0.000`

Variable prompt:
- node precision: `0.000`
- node recall: `0.000`
- edge recall: `0.000`

Interpretation:
- on the broad symbolic/formal slice, exact alias matching still fails completely
- changing the prompt is not enough when the benchmark graph is dominated by symbolic state variables

### DAGverse curated 5

Semantic prompt:
- mean node precision: `0.053`
- mean node recall: `0.089`
- mean edge recall directed: `0.046`

Variable prompt:
- mean node precision: `0.170`
- mean node recall: `0.107`
- mean edge recall directed: `0.031`

Interpretation:
- variable prompt improves **node precision** and slightly improves **node recall**
- edge exact recall falls slightly
- so the variable prompt gives a tighter node set, but does not automatically improve exact edge recovery

## Judge results

### Overall

Across all `40` judged rows:
- mean node overlap score: `0.196`
- mean edge overlap score: `0.117`

Comparability classes:
- `partly_fair_but_resolution_mismatch`: `19`
- `mostly_unfair_for_abstract_extraction`: `13`
- `fair_abstract_level_comparison`: `8`

Most common mismatch modes:
- `method_or_dataset_nodes_added`: `30`
- `gold_not_recoverable_from_abstract`: `25`
- `label_wording_only`: `22`
- `paper_summary_vs_variable_graph`: `20`
- `broader_vs_narrower_concepts`: `16`

This strongly supports the claim that the main issue is not just "wrong extraction."
It is mostly:
- graph-object mismatch
- abstraction-level mismatch
- unrecoverable gold content

### By prompt family

Semantic prompt:
- mean node overlap score: `0.171`
- mean edge overlap score: `0.082`

Variable prompt:
- mean node overlap score: `0.222`
- mean edge overlap score: `0.151`

So the variable prompt improves both semantic node overlap and semantic edge overlap on average, even though exact edge metrics remain weak.

### By dataset

#### ReCITE

Semantic:
- mean node overlap: `0.170`
- mean edge overlap: `0.083`

Variable:
- mean node overlap: `0.225`
- mean edge overlap: `0.142`

Interpretation:
- variable prompt helps meaningfully on ReCITE
- especially on cases where the semantic content is there but the original prompt over-summarizes

#### DAGverse

Semantic:
- mean node overlap: `0.172`
- mean edge overlap: `0.080`

Variable:
- mean node overlap: `0.219`
- mean edge overlap: `0.161`

Interpretation:
- variable prompt helps even more clearly on DAGverse at the semantic-judge level
- this matters because exact alias matching alone understated the gain

## Biggest wins from the variable prompt

Examples with the largest semantic-judge gains:

- DAGverse `arxiv_2306_05066_0`
  - semantic total: `0.60`
  - variable total: `1.08`
  - delta: `+0.48`

- DAGverse `arxiv_2112_05695_0`
  - semantic total: `0.20`
  - variable total: `0.65`
  - delta: `+0.45`

- ReCITE `258`
  - semantic total: `0.33`
  - variable total: `0.70`
  - delta: `+0.37`

These are all papers where a compact variable-style target is closer to the benchmark object than the original semantic summary graph.

## Spend

Using actual API usage from response payloads and official per-token pricing used in this session:

- ReCITE semantic 10: `$0.0748`
- DAGverse broad 5 semantic: `$0.0361`
- DAGverse curated 5 semantic: `$0.0406`
- ReCITE variable 10: `$0.0682`
- DAGverse variable 25: `$0.1519`
- overlap judge 40: `$0.0389`

Total validation-track spend so far:
- **`$0.4106`**

This is well below the current no-ask ceiling of `$10`.

## Bottom line

The new evidence supports four claims:

1. **Ontology is a major part of the validation problem**
- but ontology here includes abstraction level and graph-object choice, not just label wording

2. **A variable-level prompt is worth keeping**
- it materially improves exact node alignment on ReCITE
- it materially improves semantic overlap on both ReCITE and DAGverse

3. **Exact-match metrics alone are too harsh**
- they miss real gains that appear in the semantic judge scores

4. **Some benchmark rows are simply not fair title+abstract targets**
- especially symbolic DAGverse rows and some ReCITE rows whose gold structure is not recoverable from the abstract

## Recommended next step

Use a two-track validation story:

1. **semantic prompt** for FrontierGraph's core paper-summary graph object
2. **variable prompt** for compact causal-variable or figure-like benchmarks

And report:
- strict exact metrics
- semantic judge metrics
- comparability / fairness labels

That gives a much more defensible validation story than exact string overlap alone.
