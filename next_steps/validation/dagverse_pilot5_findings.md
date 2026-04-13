# DAGverse Pilot 5: First Findings

Date: 2026-04-01

## What we ran

We ran a 5-paper DAGverse pilot on the ArXiv `abstract=true` slice.

Run:
- `data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1`

Settings:
- model: `gpt-5-mini`
- reasoning: `low`
- timeout: `180s`
- max output tokens: `8000`
- concurrency: `2`

Prompt pack:
- `next_steps/validation/prompt_pack/system_prompt_validation.md`
- `next_steps/validation/prompt_pack/user_prompt_template.md`

Comparison outputs:
- `data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1/dagverse_review_explicit/aggregate.json`
- `data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1/dagverse_review_explicit/summary.csv`
- `data/pilots/frontiergraph_extraction_v2/runs/dagverse_pilot5_gpt5mini_low_v1/dagverse_review_explicit/manual_review.jsonl`

## Surface result

The alias-exact metrics are again zero:
- mean node precision alias: `0.000`
- mean node recall alias: `0.000`
- mean edge recall directed alias: `0.000`
- mean edge recall relaxed alias: `0.000`

At first sight this is disappointing.

But it is still informative.

## Why this is different from ReCITE

On ReCITE, the main mismatch was:
- operational / system-dynamics gold variables
vs.
- higher-level semantic paper-summary extraction

On this DAGverse pilot, the mismatch is slightly different:
- many gold semantic DAG nodes are still encoded as symbolic variables or very technical latent objects
vs.
- FrontierGraph extracts higher-level semantic concepts from the abstract

Examples from the pilot:
- gold node IDs like `X1`, `X2`, `W1`, `W2`, `A=a1`, `B=b2`
- extracted nodes like:
  - `Bayesian causal discovery`
  - `Structural causal model`
  - `Business necessity`
  - `Representation learning for reinforcement learning`

So even though DAGverse is semantically richer than raw DAG node letters, this particular ArXiv subset still contains many graph objects that are:
- symbolic
- instantiation-level
- auxiliary-variable-centered
- or more formal than the abstract’s prose summary

## What this means

This pilot suggests that:

1. DAGverse is not automatically a clean exact-match benchmark for FrontierGraph.
2. The selected ArXiv subset is skewed toward technical causal/ML papers where graph objects are often latent variables or symbolic assignments.
3. FrontierGraph is still extracting plausible abstract-level semantic graphs, but the benchmark nodes often live at a different representational layer.

## Representative examples

### `Interventions, Where and How?`
Gold nodes:
- `X1`
- `X2`

Predicted nodes:
- `Bayesian causal discovery`
- `BOED framework`
- `experiment intervention selection`
- `structural causal model`

Interpretation:
- the model extracted the paper's conceptual object
- the gold graph records internal formal variables

### `Learning the Finer Things`
Gold nodes:
- `A=a1`
- `A=a2`
- `B=b1`
- `C=c3`

Predicted nodes:
- `Bayesian networks`
- `Bayesian knowledge bases`
- `MDL score`
- `gene regulatory networks`

Interpretation:
- these are not the same graph object
- this is not a failure of reading the abstract
- it is a mismatch between symbolic instantiation-level graph targets and semantic abstract summaries

### `Causal Discovery on the Effect of Antipsychotic Drugs on Delirium Patients`
This is the most promising case in the pilot because the gold graph uses more natural variables:
- `age`
- `alzheimers`
- `delirium`
- `death_timeline`

Predicted nodes still compress at a higher level:
- `antipsychotic drugs`
- `delirium in ICU patients`
- `covariates correlated with delirium`
- `one-year mortality rate`

So even here, the mismatch is more about compression and abstraction than about nonsense extraction.

## Best current interpretation

The DAGverse pilot does **not** show that FrontierGraph fails on semantic DAGs.
It shows that the selected benchmark slice still often expects a graph that is:
- more formal
- more variable-level
- and more tightly tied to paper-specific DAG notation
than what a title+abstract semantic extraction prompt is naturally built to produce.

## Practical lesson

If we want DAGverse to be maximally informative for FrontierGraph, we should do one of two things:

### Option 1: curate a more natural-language subset
Prefer rows where:
- aliases are natural concepts rather than symbols
- the DAG is closer to a prose-summary graph
- the abstract itself names the relevant variables directly

### Option 2: change the extraction target
Ask FrontierGraph to extract:
- paper-specific variable-level DAGs
- including symbolic or instantiation-level variables

That would be a different prompt and a different paper-local graph object from what FrontierGraph is currently optimized for.

## Bottom line

This pilot still helps.

It tells us that:
- ReCITE stresses operational-vs-semantic mismatch
- DAGverse ArXiv stresses symbolic/formal-vs-semantic mismatch

So the common lesson is:

**the main external-validation problem remains representational mismatch, not simple model failure.**
