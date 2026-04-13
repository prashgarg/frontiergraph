# Prompt Diagnosis and Example Outputs

Date: 2026-04-03

## Main question

Are the prompts already being told that mismatch may be ontology or graph-object mismatch?

Short answer:
- **the extraction prompts are not told that**
- **the overlap judge is told that explicitly**

So we have two different layers:

1. **Extraction**
   - told what kind of graph to produce
   - not told how to excuse mismatch against a benchmark

2. **Judge**
   - explicitly told to distinguish:
     - label mismatch
     - broader vs narrower concepts
     - graph-resolution mismatch
     - method/context drift
     - gold not recoverable from title + abstract

## Prompt excerpts

### Variable-level extraction prompt

File:
- `next_steps/validation/prompt_pack/system_prompt_variable_validation.md`

Key instructions:
- `Prefer variable-like nodes over high-level paper-summary nodes.`
- `Avoid adding method, dataset, benchmark, system, interface, or paper-purpose nodes unless they are themselves central causal variables in the paper.`
- `If the abstract gives both a high-level policy or system framing and lower-level causal variables, prefer the lower-level causal variables.`

Interpretation:
- this prompt is **quite specific on nodes**
- it is actively trying to suppress broad summary nodes
- it is pushing the model toward a compact causal-variable graph

### Semantic extraction prompt

File:
- `next_steps/validation/prompt_pack/system_prompt_validation.md`

Key instruction:
- `Nodes should be concepts, variables, interventions, outcomes, mechanisms, constraints, institutions, populations, methods, or other paper-salient entities.`

Interpretation:
- this prompt is much broader
- it allows methods, institutions, and other paper-salient objects
- it tends to produce a more paper-summary-like graph

### Overlap judge prompt

File:
- `next_steps/validation/prompt_pack/system_prompt_overlap_judge.md`

Key instructions:
- `If a gold node or edge is not really recoverable from title + abstract alone, say so.`
- `Distinguish graph-object mismatch from extraction failure.`

Interpretation:
- yes, the judge is already being told to treat ontology and graph-object mismatch as real possibilities
- so the semantic scores are **not** pretending that every mismatch is a bad extraction

## Diagnosis

### Is the variable prompt too specific on nodes?

Probably **somewhat yes**.

It is doing two things at once:
- fixing the graph object
- trying to improve benchmark alignment

That helps, but it can also overshoot by:
- discarding useful high-level causal framing
- forcing a compact variable graph even when the abstract is actually broader and more narrative

This is consistent with the full ReCITE result:
- variable prompt is better than semantic prompt
- but only modestly better on semantic judge overlap

So prompt specificity helps, but it does not solve the main mismatch.

## What may improve matches

### 1. Soften the variable-node constraint

Instead of:
- `Prefer variable-like nodes over high-level paper-summary nodes`

Try:
- prefer variable-like nodes **when they are explicit and central**
- keep one or two higher-level causal framing nodes **if they organize the abstract’s logic**

That would reduce cases where the prompt over-compresses the paper into an unnatural benchmark-oriented object.

### 2. Add an explicit “preserve benchmark-friendly abstract terms” instruction

Something like:
- if the abstract uses compact factor or domain-variable labels, preserve them as written
- do not rewrite them into more interpretive narrative labels unless needed

This should help on rows like WASH / FIETS-style papers.

### 3. Separate extraction from alignment

Best structure:
- extract the paper’s own best abstract-level graph first
- then do a second optional alignment pass for benchmark comparison

Right now the variable prompt partly blends those two goals.

### 4. Add a dual-mode output for validation

Potential future validation setup:
- `paper_graph`: your natural semantic paper-local graph
- `compact_variable_graph`: a second benchmark-facing graph if recoverable

That would be cleaner than forcing one graph to do both jobs.

## Concrete examples from ReCITE variable prompt

### Low overlap example

Benchmark id:
- `8`

Judge result:
- comparability: `fair_abstract_level_comparison`
- recoverable: `partly`
- node overlap: `0.0`
- edge overlap: `0.0`

Title:
- `The Value of In Vitro Diagnostic Testing in Medical Practice: A Status Report`

Gold nodes (sample):
- `Low sensitivity and specificity`
- `False negative results`
- `Fear of missed diagnosis`
- `Legal consequences`
- `Overutilization of IVD`

Predicted nodes:
- `in vitro diagnostic testing (IVD)`
- `IVD healthcare expenditure (IVD HCE)`
- `total healthcare expenditure (total HCE)`
- `physician perception of IVD HCE`
- `clinical decision-making based on IVD`
- `new diagnostic markers delivering actionable, medically relevant information`

Predicted edges (sample):
- `IVD healthcare expenditure (IVD HCE) -> total healthcare expenditure (total HCE)`
- `in vitro diagnostic testing (IVD) -> clinical decision-making based on IVD`
- `new diagnostic markers delivering actionable, medically relevant information -> improved patient outcomes`

Interpretation:
- the abstract mentions broad expenditure and decision-making themes
- the gold graph is about diagnostic sensitivity, false negatives, legal fear, and over/under-use
- this is a case where the prediction drifts toward high-level framing and misses the gold’s internal risk structure

### Medium overlap example

Benchmark id:
- `160`

Judge result:
- comparability: `partly_fair_but_resolution_mismatch`
- recoverable: `partly`
- node overlap: `0.25`
- edge overlap: `0.10`

Title:
- `Modelling the European Union Sustainability Transition: A Soft-Linking Approach`

Gold nodes (sample):
- `clean energy`
- `employment`
- `energy efficiency`
- `consumption`
- `production`
- `food quality`
- `societal costs`

Predicted nodes:
- `EGD policy instruments`
- `revenue recycling mechanism`
- `development and diffusion of clean energy technologies`
- `EU market benefits`
- `trade-based technology transfer`
- `global emissions reduction`
- `non-EU country benefits`

Predicted edges (sample):
- `EGD policy instruments -> revenue recycling mechanism`
- `revenue recycling mechanism -> development and diffusion of clean energy technologies`
- `development and diffusion of clean energy technologies -> EU market benefits`
- `trade-based technology transfer -> global emissions reduction`

Interpretation:
- the prediction captures a coherent causal narrative
- but it is much more compressed and policy-level than the benchmark graph
- this is exactly a graph-resolution mismatch rather than pure extraction failure

### High overlap example

Benchmark id:
- `178`

Judge result:
- comparability: `fair_abstract_level_comparison`
- recoverable: `yes`
- node overlap: `0.83`
- edge overlap: `0.25`

Title:
- `Interaction of Factors Influencing the Sustainability of Water, Sanitation, and Hygiene (WASH) Services in Rural Indonesia`

Gold nodes:
- `WASH services`
- `Social`
- `Technical`
- `Environmental`
- `Institutional`
- `Financial`

Predicted nodes:
- `institutional factor`
- `financial factor`
- `environmental factor`
- `technical factor`
- `social factor`
- `sustainability of WASH services`

Predicted edges (sample):
- `institutional factor -> financial factor`
- `institutional factor -> environmental factor`
- `institutional factor -> technical factor`
- `institutional factor -> social factor`
- `institutional factor -> sustainability of WASH services`
- `social factor -> sustainability of WASH services`
- `sustainability of WASH services -> social factor`

Interpretation:
- this is a good example of the prompt doing the right thing
- node labels are close to the gold object
- the remaining problem is not node recovery but missing many of the benchmark’s fuller interconnections

## Takeaway

The current setup already gives the judge permission to treat ontology and graph-object mismatch as the main issue.

So if we want better matches, the most promising next change is **not** to make the judge more forgiving.

It is to make extraction slightly more flexible by:
- preserving compact abstract terms more faithfully
- avoiding over-compression into a narrative causal chain
- and possibly separating:
  - natural paper-local graph extraction
  - benchmark-facing compact variable alignment
