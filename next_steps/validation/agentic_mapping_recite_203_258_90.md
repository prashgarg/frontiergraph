# Agentic Mapping Review: ReCITE Papers 203, 258, 90

Date: 2026-03-31

This note records a manual/agentic semantic mapping pass over three ReCITE pilot papers.

Inputs used:
- raw pilot outputs from `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/parsed_results.jsonl`
- ReCITE gold graphs from `next_steps/validation/data/reCITE/test.parquet`
- embedding suggestions from `data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/recite_review/embedding_matches_203_258_90.json`

Mapping labels:
- `exact_match`
- `broader_than_gold`
- `narrower_than_gold`
- `partial_overlap`
- `context_only`
- `no_match`
- `not_comparable_at_abstract_level`

## High-level conclusion

These three papers support the same broad point:

**the current validation problem is mostly semantic-level mismatch, not obviously bad extraction.**

More specifically:
- paper `203` looks semantically alignable with modest manual effort
- paper `258` looks strongly alignable at the node level, but not at the edge-structure level
- paper `90` is not fairly comparable at title+abstract level because the ReCITE gold graph appears to come from a specific lower-level archetype loop that is not recoverable from the abstract

## Paper 203

Title:
- `A Review of Agricultural Technology Transfer in Africa: Lessons from Japan and China Case Projects in Tanzania and Kenya`

### Overall judgment

This is the best semantic-fit paper among the three.

The extracted graph is not identical to the gold graph, but a substantial part of the predicted node set is clearly talking about the same underlying objects:
- agricultural technology transfer
- agricultural productivity
- stakeholder coordination / participation
- sustainability
- beneficiary autonomy

The main mismatch is that:
- ReCITE gold nodes are more compact, CLD-style, and loop-oriented
- FrontierGraph extracted nodes are more paper-summary and mechanism-description oriented

### Predicted-node judgments

- `Agricultural technology transfer`
  - `exact_match` to gold `Agricultural technology transfer`

- `Agricultural productivity / farm production`
  - `exact_match` or very close `partial_overlap` with gold `Agricultural productivity`
  - I would count this as effectively the same concept

- `Stakeholder linkages, commitment, and participation`
  - `exact_match` to gold `Stakeholders linkages, supports and commitment`

- `Project sustainability in recipient countries`
  - `partial_overlap` / mild `broader_than_gold` relative to gold `Sustainability of agricultural technical cooperation projects`
  - same core concept, slightly different wording and scope

- `Beneficiary autonomy (knowledge and capacity of production)`
  - `partial_overlap` with gold `Autonomy, self-reliance and utilization of local resources`
  - narrower on some dimensions, broader on others

- `Local government policy and institutional frameworks`
  - `partial_overlap` at best with gold `Operating project environment`
  - plausible environmental/institutional subcomponent, but not a clean match

- `Effectiveness and sustainability challenges`
  - `partial_overlap` with the broader sustainability part of the gold graph
  - but not a node that clearly exists as such in the gold graph

- `Responsiveness to local demand`
  - `no_match`
  - important abstract-level problem framing, but not clearly present as a gold node

- `Japanese agricultural technical cooperation (SHEP, RIDS)`
  - `context_only`
  - these are case/project examples, not gold CLD variables

- `Chinese agricultural technical cooperation (ATDC)`
  - `context_only`

- `Study methods: system dynamics and literature review`
  - `context_only`

### Bottom line for 203

If judged semantically rather than by exact string:
- roughly `5` of the `11` predicted nodes are clearly useful matches or near-matches
- another `2` are arguable partial overlaps
- the main failure is not nonsense extraction
- it is graph-object mismatch between a summary graph and a tighter causal-loop graph

## Paper 258

Title:
- `The Sustainable Development of the Economic-Energy-Environment (3E) System under the Carbon Trading (CT) Mechanism: A Chinese Case`

### Overall judgment

This paper is the strongest case for the claim that exact-match metrics are too harsh.

The embedding suggestions are very good here, and the semantic overlap is obvious:
- `Energy consumption`
- `CO2 emissions`
- `GDP`
- `Total quota`
- `Free quota amount`
- `CT price`

These are all either exact or near-exact concept matches.

### Predicted-node judgments

- `Energy consumption`
  - `exact_match`

- `CO2 emissions`
  - `exact_match`

- `Gross domestic product (GDP)`
  - `exact_match`

- `Total quota (CT)`
  - `exact_match` to gold `Total quota`

- `Free quota (CT)`
  - `exact_match` or near-exact `partial_overlap` with gold `Free quota amount`

- `Carbon trading price (CT price)`
  - `exact_match` or near-exact `partial_overlap` with gold `CT price`

- `Carbon trading (CT) mechanism`
  - `broader_than_gold`
  - this compresses several gold-side policy/market components into one higher-level node

- `Sustainable development of the 3E system`
  - `broader_than_gold`
  - this is a higher-level outcome node not represented cleanly as one gold node

- `3E system simulation model (system dynamics)`
  - `context_only`

- `Beijing-Tianjin-Hebei region`
  - `context_only`

### Why edges still score zero

This is important.

The gold graph is a more internal mechanism graph:
- GDP -> energy investment
- energy gap -> energy policies
- energy intensity -> energy consumption
- CO2 emissions -> environmental governance costs

The extracted graph is a more paper-summary graph:
- CT mechanism -> energy consumption
- CT mechanism -> CO2 emissions
- CT mechanism -> GDP
- CT price -> CO2 emissions

So the node overlap is much better than the edge overlap.

### Bottom line for 258

This is a strong example where:
- node-level semantic recovery is actually fairly good
- exact graph-edge recovery is poor because the benchmark gold graph lives at a more decomposed internal-mechanism level than the abstract

## Paper 90

Title:
- `Hydropolitical System Archetypes: Feedback Structures, Physical Environments, Unintended Behaviors, and a Diagnostic Checklist`

### Overall judgment

This paper is **not fairly comparable at abstract level**.

The ReCITE gold graph is a specific five-node loop:
- upstream water-based development
- upstream unilateral water capture
- water flow asymmetry
- downstream water-based development
- downstream unilateral water capture

But the abstract does not state those five nodes directly.
Instead, the abstract talks at a much higher level about:
- hydropolitics
- system archetypes
- feedback loop structures
- physical environments
- unintended behaviors
- a diagnostic checklist

That is exactly what FrontierGraph extracted.

### Predicted-node judgments

The predicted nodes are mostly:
- `exact_match` to the abstract's own semantic content
- but `not_comparable_at_abstract_level` relative to the gold graph

This is the key distinction.

Examples:
- `Hydropolitics (study of conflict and cooperation)`
  - `not_comparable_at_abstract_level`

- `System archetypes (hydropolitical)`
  - `not_comparable_at_abstract_level`

- `Feedback loop structures`
  - `not_comparable_at_abstract_level`

- `Diagnostic checklist`
  - `not_comparable_at_abstract_level`

The model is doing a reasonable abstract extraction job.
The benchmark target is simply not the same object.

### Bottom line for 90

This paper should be flagged as:
- `abstract-insufficient for gold graph recovery`

It is still useful as a benchmark, but only if:
- we use full text or figure context
- or we treat it as a benchmark for higher-level paper-summary extraction rather than exact loop recovery

## Cross-paper lessons

### 1. We need semantic categories, not just exact-match metrics

At least on these three papers, the right evaluation object is something like:
- semantic node recovery
- abstraction level mismatch
- context-only nodes
- mechanism compression

### 2. We should split benchmark rows into fair and unfair abstract-level cases

Some rows, like `90`, should not count as failures of abstract extraction.
They should be tagged as:
- `not recoverable from abstract alone`

### 3. Node comparison and edge comparison must be separated

Paper `258` shows the pattern clearly:
- node-level semantic overlap can be decent
- edge-level exact recovery can still be poor

This is because the abstract often states top-line policy effects while the benchmark graph records internal mechanism structure.

### 4. The next validation layer should combine embeddings with human judgment

Embeddings help surface good candidate matches quickly.
But the final label still needs human/agentic judgment, because:
- broader vs narrower matters
- paper-summary vs mechanism-node matters
- context-only nodes should not be treated as simple errors

## Recommended next move

For the next pass, the evaluation should shift from:
- exact overlap only

to:
- semantic match categories
- abstract-level fairness flags
- separate node and edge judgments
