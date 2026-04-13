# Method v2 Schema and Model Choices Note

Date: 2026-04-09

## Purpose

This note resolves or narrows the remaining method-v2 design choices that were still open after the anchor redesign:

- exact layer names
- candidate row schema
- whether some motif families should be first-class or remain evidence tags
- transparent-model redesign
- options for reranker, concentration control, and human validation

The note is meant to be academically defensible and implementation-ready.

## Guiding principles

Three principles govern the choices below.

### 1. Keep the empirical object simple enough to benchmark

The historical object should remain a dated event with a clear realization rule. This follows the same general discipline as the literature on link prediction and learning to rank in information retrieval: training and evaluation are much easier to interpret when the target object is fixed and the retrieval model is layered on top of it rather than redefining the object midstream. This is one reason the current paper already leans on preferential attachment, co-occurrence, and learning-to-rank comparisons rather than an unconstrained generation task.

Relevant background already cited in the manuscript:

- Price (1976)
- Barabasi and Albert (1999)
- Liben-Nowell and Kleinberg (2007)
- Martinez et al. (2016)
- Liu (2009)
- Krenn and Zeilinger (2020)
- Gu and Krenn (2025)

### 2. Keep the surfaced object close to how researchers actually read ideas

A reader rarely wants to inspect a raw graph motif. They want a bounded question. That is why endpoint-centered or endpoint-plus-mediator formulations remain the paper-facing unit, with richer motifs treated as evidence.

### 3. Keep the method modular

Candidate family, evidence motif, transparent score, reranker, diversification, and human evaluation should be separate layers. When these get mixed together, the method becomes hard to defend and harder to improve.

## 1. Recommended layer names

I recommend making four graph layers explicit, even if only three are central in the paper text.

### `contextual_pair`

Definition:

- undirected contextual relation

Why this name:

- `contextual` says clearly that this is support rather than a benchmark-causal claim
- `pair` reflects that the stored object is undirected
- it avoids the misleading phrase `undirected_noncausal`, which sounds more substantive than intended

### `ordered_claim`

Definition:

- relation stated directionally in the paper-local graph

Why this name:

- it names ordering directly without implying identification strength
- it preserves the distinction between textual directionality and causal credibility

This is useful as an internal layer even if it is not the main benchmark layer.

### `causal_claim`

Definition:

- ordered claim with `causal_presentation in {explicit_causal, implicit_causal}`

Why this name:

- this is the cleanest name for the new main benchmark object
- it is broader than identified-causal edges but still reads like an economist-facing substantive claim
- it avoids using `directed` as a proxy for causal credibility

### `identified_causal_claim`

Definition:

- method-based strict subset of causal claims

Why this name:

- it tells the truth about what this layer is doing
- it is a credibility-oriented subset rather than the generic meaning of direction
- it is the right name for the nested strict benchmark

### Summary

For code and notes, I would therefore use:

- `contextual_pair`
- `ordered_claim`
- `causal_claim`
- `identified_causal_claim`

For the main paper, we probably only need to foreground:

- `contextual_pair`
- `causal_claim`
- `identified_causal_claim`

with `ordered_claim` described as an internal bridge layer.

## 2. Recommended candidate row schema

The schema should be lean enough to remain inspectable, but rich enough to support:

- deterministic scoring
- reranking
- human-facing rendering
- LLM audit
- layered evaluation

### Design recommendation

Split the candidate row into six blocks.

### A. Identity block

- `candidate_id`
  - stable candidate identifier
- `cutoff_year_t`
  - historical cutoff
- `candidate_family`
  - `path_to_direct`, `direct_to_path`, `mediator_expansion`
- `candidate_status_at_t`
  - concise description of the current state at the cutoff

Why:

- these fields identify the object without yet committing to how it will be rendered or evaluated

### B. Focal relation block

- `source_id`
- `target_id`
- `source_label`
- `target_label`
- `pair_key`

Why:

- these remain the stable focal handles across scoring, reranking, and rendering

### C. Anchor and evaluation block

- `main_anchor_layer`
  - default `causal_claim`
- `strict_anchor_layer`
  - default `identified_causal_claim`
- `main_anchor_event`
  - for example `appearance`
- `strict_anchor_event`
  - for example `appearance`
- `evaluation_target_main`
  - exact dated outcome definition for the main benchmark
- `evaluation_target_strict`
  - exact dated outcome definition for the nested strict benchmark

Why:

- this keeps the historical event explicit and prevents later code from inferring the target implicitly

### D. Local evidence block

- `focal_mediator_id`
  - nullable
- `focal_mediator_label`
  - nullable
- `top_mediators_json`
- `top_paths_json`
- `evidence_motif_tags_json`
- `local_topology_class`
- `closure_state`

Why:

- these are the fields most useful for human reading and later LLM interpretation
- the combination is still compact enough to inspect row by row

### E. Support provenance block

- `contextual_support_count`
- `ordered_support_count`
- `causal_claim_support_count`
- `identified_causal_support_count`
- `support_paper_count`
- `support_year_min`
- `support_year_max`
- `support_source_mix_json`
- `support_method_mix_json`

Why:

- the anchor redesign makes support provenance by layer essential
- this is where we stop hiding which layer is doing the work

### F. Scoring-ready feature block

- `path_support_raw`
- `mediator_count`
- `mediator_diversity`
- `motif_count`
- `contextual_gap_raw`
- `causal_gap_raw`
- `hub_penalty_raw`
- `boundary_flag`
- `cross_field_flag`
- `same_field_flag`
- `direct_literature_status_main`
- `direct_literature_status_strict`

Why:

- these are the transparent ingredients
- the row can later add normalized variants in scoring outputs, but the core row should preserve the interpretable raw quantities

## 3. Recommended field names

The naming rule should be:

- use `source_` / `target_` for focal endpoints
- use `main_` / `strict_` for the two benchmark layers
- use `_count`, `_raw`, `_json`, and `_flag` suffixes consistently

This keeps the schema readable and reduces later confusion about whether a field is:

- a concept label
- a benchmark definition
- a support summary
- a score ingredient

## 4. Prompt contract for any LLM consumer of candidate rows

If we later use an LLM to render or audit candidate rows, the prompt should be explicit that the model is reading a structured local object, not inventing the object.

Recommended system prompt:

```text
You are given a structured candidate research-question object from a literature graph.

Your job is to interpret or audit the candidate using only the provided fields.
Do not use external knowledge about what happened later in the literature.
Do not invent missing graph structure.
Treat the focal endpoints as the candidate's main research object and the local paths, mediators, and motif tags as supporting evidence.

Distinguish carefully between:
- the historical benchmark anchor
- the local evidence bundle
- the human-facing formulation of the question

Return only the fields requested by the supplied schema.
```

Why this prompt is defensible:

- it explicitly limits the model to within-row evidence
- it prevents free-form hindsight ranking
- it reinforces the anchor-versus-surfaced-object distinction

## 5. Why `parallel_mediator_expansion` should come later

I still recommend keeping this out of the first top-level family set.

### Reason 1. It is nested inside mediator expansion conceptually

A parallel-mediator case is a special case of the broader mechanism question:

- "through which mechanism does `A` affect `C`?"

So the main methodological gain can already be captured by `mediator_expansion`.

### Reason 2. It is empirically real but relatively rare

In the motif read:

- directed parallel mediator patterns are only about `0.4%` of all papers
- and about `4.4%` of the directed subset

That is not negligible, but it is not strong enough to justify another headline family immediately.

### Reason 3. Its historical event is harder to define cleanly

For `path_to_direct`, the main event is clear:

- direct closure

For `direct_to_path`, the event is also clear:

- mechanism thickening

For `parallel_mediator_expansion`, the benchmark event is much less clean:

- one additional mediator?
- two competing mediators?
- stable multi-route support?

That ambiguity is exactly the sort of thing that can make a family feel handcrafted.

### Recommendation

Keep:

- `parallel_mediators` as an evidence motif tag now

Promote later only if:

- it shows distinct behavior in the data
- it materially improves rendering or validation quality
- and its realization event can be defined clearly

## 6. Why common-driver and common-consequence should remain evidence tags for now

This is not because they are unimportant. In the directed subset, they are common:

- common-driver / fork-like: about `52.8%`
- common-consequence / collider-like: about `53.3%`

The issue is not prevalence. The issue is whether they define a clean top-level historical task.

### Common-driver

Pattern:

- `A -> B` and `A -> C`

Potential research readings:

- broader downstream consequence map
- omitted target discovery
- shared-source expansion

Problem:

- there is no single obvious dated event analogous to direct closure

### Common-consequence

Pattern:

- `A -> B` and `C -> B`

Potential research readings:

- convergence on a shared outcome
- competing mechanisms
- omitted common antecedent

Problem:

- the natural next move is often not one missing pair
- it may be a richer explanatory or comparative question instead

### Why evidence-tag status is better

As evidence tags, they are very useful:

- they describe why a candidate is structurally interesting
- they help rendering and LLM auditing
- they can affect reranking or concentration control

But as top-level historical families, they would require a more complex event definition and would likely muddy the paper.

## 7. Transparent-model redesign

The transparent model should stay simple, readable, and decomposable.

It should not try to be the benchmark winner.

### What is wrong with the current version

The current transparent score is:

- path support
- plus gap bonus
- plus motif bonus
- minus hub penalty

This was a reasonable first design, but it has three problems now:

1. it hides support provenance by layer
2. it is not family-aware
3. it is too close to one scalar heuristic when the object has become richer

### Recommended redesign

Make the transparent model a two-stage interpretable screen.

### Stage 1. Family-specific eligibility

Examples:

- `path_to_direct`
  - require at least one supporting path
  - require focal relation missing in the main anchor layer
- `direct_to_path`
  - require focal relation already present in the main anchor layer
  - require no substantial mechanism support yet, but some local mechanism precursor
- `mediator_expansion`
  - require focal endpoints plus at least one plausible mediator

This keeps the score from comparing fundamentally different objects before the family assignment has done any work.

### Stage 2. Family-aware additive transparent score

Recommended component families:

- support strength
  - path support, mediator count, motif support
- openness
  - missingness or underdevelopment in the main and strict layers
- support provenance
  - how much evidence comes from contextual, causal-claim, and identified-causal layers
- specificity
  - penalties for hubness and overgeneric endpoints
- topology shape
  - branch or closure descriptors where useful

### Recommended score form

For transparency, keep it additive and decomposable:

```text
transparent_score
  = family_fit
  + support_strength
  + openness
  + provenance_balance
  - genericity_penalty
```

with each term itself a short weighted sum of interpretable normalized pieces.

### Recommendation on tuning

Do not freely tune all weights to maximize historical performance.

Instead:

- fix a small number of transparent presets by design
- compare them honestly
- let the reranker absorb the heavier optimization burden

This is more defensible than turning the transparent layer into a disguised trained model.

## 8. Learned-reranker options

The current code already supports two sensible model families:

- `glm_logit`
- `pairwise_logit`

and five feature families:

- `base`
- `structural`
- `dynamic`
- `composition`
- `boundary_gap`

### Options

#### Option A. Main = `glm_logit`, appendix = `pairwise_logit`

Pros:

- easiest to interpret
- easiest to summarize in the paper
- coefficient-level stories are cleaner

Cons:

- may give up some ranking performance if pairwise learning materially helps

#### Option B. Main = `pairwise_logit`, appendix = `glm_logit`

Pros:

- closer to the actual ranking objective
- often stronger when the shortlist order matters

Cons:

- harder to explain
- harder to relate coefficients back to feature meaning

### Current recommendation

Use:

- main paper reranker: `glm_logit`
- appendix robustness reranker: `pairwise_logit`

unless the pairwise model wins by a clearly material margin on the redesigned anchor.

That follows Liu (2009) in spirit:

- ranking models should be compared on ranking metrics
- but the paper-facing choice need not be the least interpretable model if gains are small

## 9. Concentration-control options

Three options remain sensible.

### Option A. No control

Use as the benchmark baseline only.

Why:

- we need to know what the raw ranking does

### Option B. Soft sink penalty

Apply a post-ranking penalty to endpoints with extreme repetition or sink behavior.

Pros:

- easy to calibrate
- preserves the underlying score ordering locally

Cons:

- still somewhat heuristic

### Option C. Diversification rerank

Use a light max-marginal-relevance or quota-style rerank at shortlist time.

Pros:

- directly targets crowding
- more interpretable as an attention-allocation layer

Cons:

- can reduce historical metrics if overused

The repo already has encouraging evidence that light diversification can improve top-100 coverage with modest cost, especially at shorter horizons.

### Current recommendation

Compare:

- no control
- calibrated soft sink penalty
- light MMR-style or quota-style diversification

Then choose the default by Pareto comparison, not by aesthetic preference.

This is also where the IR diversification literature is useful background:

- Carbonell and Goldstein (1998) on maximal marginal relevance
- Agrawal et al. (2009) on diversified search
- Clarke et al. (2008) on novelty and diversity evaluation

The paper should present this as a post-ranking screening layer, not as the benchmark winner itself.

## 10. Human-validation options

The current plan is directionally right but still thin.

### What the protocol should answer

Not:

- "is this true?"

But:

- is this a plausible and useful research question object to show a researcher?

### Recommended pack structure

Use a balanced randomized pack with three comparisons:

1. graph-selected versus preferential-attachment-selected
2. raw anchor wording versus path/mechanism wording
3. main-anchor winner versus stricter identified-causal winner on a small overlap sample

### Recommended rating dimensions

- plausibility
- specificity
- mechanism clarity
- actionability
- reading effort / readability
- attention-worthiness

Keep novelty optional or secondary, because raters often interpret novelty inconsistently.

### Recommended design

- `24` to `40` items total for a first serious pilot
- blind the source method
- randomize order
- keep wording style neutral where possible
- analyze both mean ratings and pairwise win rates

### Current recommendation

Build the first proper protocol around:

- `12-20` graph-selected items
- `12-20` baseline-selected items
- a smaller within-item wording comparison subset

That is enough to support a paper claim about screening usefulness without pretending to have solved expert forecasting.

## Bottom line

The most important choices are now fairly clear:

- use explicit layer names that separate ordering, causal language, and identification strength
- keep a compact candidate-family set
- let richer motifs live in the evidence object
- redesign the transparent model as a family-aware interpretable screen
- keep the main reranker readable unless a more complex model wins clearly
- treat concentration as a separate post-ranking layer
- make human validation about usefulness of research-question objects, not about truth or hindsight
