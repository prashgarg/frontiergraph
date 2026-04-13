# Initial Download and Scope Decision

Date: 2026-03-31

This note records what has already been downloaded, what the files contain, how well they match FrontierGraph's current extraction prompt, and what subset we should run first.

## Files downloaded locally

Downloaded into:
- `next_steps/validation/data/reCITE/test.parquet`
- `next_steps/validation/data/dagverse/train.parquet`

## 1. ReCITE: what we now know

Local file:
- `next_steps/validation/data/reCITE/test.parquet`

### Schema
Columns:
- `id`
- `title`
- `source`
- `url`
- `domains`
- `num_nodes`
- `num_edges`
- `explicitness`
- `nodes`
- `edges`
- `node_explicitness`
- `input_text`
- `abstract`
- `publication_date`

### Scale
- 292 examples
- mean node count: **24.99**
- mean edge count: **37.37**

### Text size
`input_text`:
- mean length: **40,541 chars**
- mean rough token count: **10,135**
- p90 rough token count: **14,585**
- max rough token count: **42,785**
- total rough input tokens across all examples: **2,959,504**

`abstract`:
- mean length: **1,493 chars**
- mean rough token count: **373**
- max rough token count: **734**
- total rough input tokens across all examples: **109,011**

### Interpretation
This is very important:
- ReCITE gives us **both** a full-text-ish field (`input_text`) **and** an abstract
- our current FrontierGraph extraction prompt is explicitly written for **title + abstract**

So ReCITE is an unusually good fit.

### Prompt fit
**Very good fit for abstract-only.**

We can run our current prompt on:
- `title`
- `abstract`

with almost no adaptation.

We can also later test:
- `title`
- `input_text`

but that would be a modified experiment, not a clean first benchmark, because the prompt was not designed for long document text.

### Cost proxy
If we run the current prompt on all 292 ReCITE abstracts:
- input token budget is only about **109k**
- likely output budget is roughly **146k to 234k**, assuming **500 to 800 output tokens** per paper-local graph

So total token budget is roughly:
- **255k to 343k tokens**

That is small and very manageable.

If we run on the full `input_text` instead:
- input alone is about **2.96M tokens**
- total likely budget becomes roughly **3.1M to 3.2M tokens**

That is much more expensive and also a worse match to the current prompt.

### Conclusion for ReCITE
Run **all 292 abstracts** first.

This is the cleanest, cheapest, and most informative first benchmark.

## 2. DAGverse example: what we now know

Local file:
- `next_steps/validation/data/dagverse/train.parquet`

### Schema
Columns:
- `dag_id`
- `source`
- `abstract`
- `technical`
- `domain`
- `semantic_dag`
- `dag`
- `paper_id`
- `paper_uri`
- `image_id`
- `image`

Important:
- `dag` and `semantic_dag` are serialized JSON strings
- `image` is embedded PNG bytes
- there is **no obvious full text field**

### Scale
- 108 examples
- mean node count from `dag`: **5.45**
- mean edge count from `dag`: **6.22**

This is a much smaller graph object than ReCITE.

### Source composition
By source:
- `arxiv`: **58**
- `cladder`: **37**
- `biorxiv`: **13**

By `abstract` flag:
- `False`: **80**
- `True`: **28**

Cross-tab:
- `arxiv` with `abstract=True`: **25**
- `biorxiv` with `abstract=True`: **3**
- `cladder` with `abstract=True`: **0**

### Interpretation of the `abstract` flag
My working assumption is:
- `abstract=True` means the released DAG can be grounded at abstract level
- `abstract=False` likely means full paper / fuller document context is needed

This is not fully documented in the release, but it is the most plausible operational reading.

### Prompt fit
The match to our current prompt is:

#### Best match
- `arxiv` rows with `abstract=True`

Reason:
- we can fetch title + abstract from ArXiv pages
- our prompt already expects title + abstract

#### Second-best match
- `biorxiv` rows with `abstract=True`

Reason:
- likely also abstract-groundable
- but text retrieval is a little less straightforward

#### Not recommended first
- `cladder` rows
- all rows with `abstract=False`

Reason:
- those are not the cleanest "real paper title + abstract" benchmark for our current prompt

### Text retrieval feasibility

#### ArXiv
Feasible.

For example:
- converting `https://arxiv.org/pdf/2006.02482` to `https://arxiv.org/abs/2006.02482`
lets us recover title and abstract from the abstract page.

#### bioRxiv
Probably feasible, but less clean.

The `paper_uri` values point to `*.full.pdf`.
We would likely need a bioRxiv-specific retrieval step for abstract text.

#### CLadder
Not relevant to this specific prompt-validation step.

### Cost proxy
If we only use the **25 ArXiv + abstract=True** rows first, token cost should be tiny.

Even at a rough **300 to 700 input tokens** per abstract plus moderate JSON output, this is a very small pilot.

### Conclusion for DAGverse
Do **not** try to use all 108 examples first.

Use:
- **25 ArXiv rows with `abstract=True`** first

Potentially add:
- **3 bioRxiv rows with `abstract=True`** later

Skip for now:
- all `abstract=False` rows
- all `cladder` rows

## What our current prompt can and cannot do

From `paper/research_allocation_paper.md`, the current prompt explicitly says:
- "You extract a paper-local research graph from a paper title and abstract."
- "Read the paper title and abstract."
- "Use only the information in the title and abstract."

So:

### It can directly handle
- ReCITE title + abstract
- DAGverse rows where we can fetch title + abstract

### It cannot cleanly handle, without modification
- full-document ReCITE `input_text`
- DAGverse full-paper grounding examples

Those are second-stage experiments.

## Recommended first benchmark run

### Run now
1. **ReCITE abstract-only benchmark**
   - all 292 examples

2. **DAGverse abstract-compatible benchmark**
   - 25 ArXiv examples with `abstract=True`

### Do later
3. ReCITE full-text benchmark on a small subset
4. DAGverse `abstract=False` examples on a small subset with adapted prompts
5. bioRxiv subset if retrieval is easy

## Why this staged approach is right

It gives us:
- a clean validation pass against a prompt that matches its intended input format
- a cheap first run
- enough examples to learn about ontology and graph differences

without:
- paying to process millions of unnecessary tokens
- mixing prompt-format mismatch with model-quality issues
- overcomplicating the first comparison

