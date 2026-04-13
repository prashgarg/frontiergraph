# ReCITE Pilot 10: First Findings

Date: 2026-03-31

## What we ran

We ran a first real FrontierGraph validation pilot on a 10-paper ReCITE subset.

Run:
- `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2`

Settings:
- model: `gpt-5-mini`
- reasoning: `low`
- timeout: `180s`
- max output tokens: `8000`
- concurrency: `2`

Prompt pack used:
- `next_steps/validation/prompt_pack/system_prompt_validation.md`
- `next_steps/validation/prompt_pack/user_prompt_template.md`

Important note:
- the original production `system_prompt.md` in `prompts/frontiergraph_extraction_v2/` is currently hanging on local file read because of a Dropbox-managed file issue
- so this pilot used a close local fallback prompt rather than the exact production prompt file

## What succeeded

- all `10/10` papers completed successfully
- parsed outputs were written
- comparison outputs were written

Comparison outputs:
- `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/recite_review/aggregate.json`
- `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/recite_review/summary.csv`
- `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/recite_review/manual_review.jsonl`

## Surface metrics

Naive exact-match metrics are extremely poor:
- mean node precision: `0.029`
- mean node recall: `0.022`
- mean node jaccard: `0.013`
- mean edge recall (directed): `0.000`
- mean edge recall (relaxed): `0.000`

At first glance this looks like failure.

## Why the exact-match metrics are misleading

The pilot strongly suggests that the main issue is **not** simply extraction failure.
It is a mismatch in **ontology level and graph object**.

### ReCITE gold graphs
Many ReCITE gold graphs appear to be closer to:
- paper-specific causal-loop or system-dynamics variables
- figure-grounded variables
- lower-level operational nodes

Examples of gold labels:
- `the us's water based development`
- `charging station number`
- `availability of time for improvements implementation`
- `ct price`

### FrontierGraph abstract extraction
Our prompt often returns:
- higher-level semantic concepts
- summary-level objects named in the abstract
- broader research-program or paper-summary nodes

Examples of extracted labels:
- `hydropolitical system archetypes (five)`
- `optimization of energy and material flows`
- `new corporate sustainability assessment csa method`
- `fuel price increase policy`

So the extraction is often plausible, but it is operating at a different level of abstraction from the gold graph.

## Concrete interpretation

This first pilot suggests:

1. **ReCITE is still useful**, but not as a raw exact-string benchmark.
2. The main problem is **ontology and graph-level mismatch**, exactly as expected.
3. Exact node overlap is too strict for this benchmark.
4. Edge overlap built on exact node identity is therefore also too strict.

## Best examples from the pilot

### Benchmark 203
Title:
- `A Review of Agricultural Technology Transfer in Africa: Lessons from Japan and China Case Projects in Tanzania and Kenya`

This was one of the closest cases in the pilot.

Why it is useful:
- extracted nodes and gold nodes are at least in the same thematic region
- overlap is still low by exact string, but this looks like a **semantic mapping** problem rather than a nonsense extraction problem

### Benchmark 258
Title:
- `The Sustainable Development of the Economic-Energy-Environment (3E) System under the Carbon Trading (CT) Mechanism: A Chinese Case`

Again, exact overlap is low, but we can already see partial semantic alignment:
- gold: `ct price`, `ct amounts`, `energy intensity`
- extracted: `carbon trading price ct price`, `free quota ct`, `gross domestic product gdp`

This is a good candidate for embedding or agentic mapping.

## Most important lesson

The validation bottleneck is now much clearer:

**We do not yet have the right matching layer between our semantic abstract-level graph and the benchmark's often more operational graph.**

That means the next validation step should not be:
- "run more exact-match metrics"

It should be:
- "build a smarter semantic/agentic mapping layer"

## Recommended next steps

### 1. Manual review three papers carefully
Best first candidates:
- `203`
- `258`
- `90`

Goal:
- label each extracted node against the gold graph as:
  - `exact_match`
  - `broader_than_gold`
  - `narrower_than_gold`
  - `partial_overlap`
  - `no_match`

### 2. Add embedding-based node matching
Use embeddings to propose top candidate gold-node matches for each extracted node.

This will not solve ontology problems by itself, but it will make manual review much faster.

### 3. Try ReCITE `input_text` on a very small subset
Reason:
- many gold graph variables may be present in the body text or figure descriptions, not the abstract
- our title+abstract prompt may therefore be under-informed relative to the benchmark target

Best scope:
- only `3` papers first

### 4. Use DAGverse next
Reason:
- DAGverse semantic DAGs may be closer to our semantic-level extraction target
- this may produce a fairer first external benchmark than ReCITE exact overlap

## Bottom line

This pilot was successful because it told us something important very quickly:

**the first external validation problem is not mainly model reliability; it is how to compare two graphs that live at different semantic levels.**
