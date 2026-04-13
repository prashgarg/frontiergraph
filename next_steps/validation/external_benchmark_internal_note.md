# Internal Note: Why the External Benchmark Runs Are Not Paper-Ready Evidence

Date: 2026-04-03

## Purpose of this note

This note records exploratory work on external graph benchmarks that was done to understand transferability and validation strategy. The goal was diagnostic, not to generate a pre-committed headline result for the paper.

The key question was:

- if FrontierGraph paper-local semantic graphs are compared to existing external graph benchmarks, do those benchmarks provide a fair and informative validation target?

The short answer is:

- only partly
- and often not enough to justify pooled benchmark metrics as paper evidence

## What we tried

We ran a substantial external-benchmark validation exercise on:

- ReCITE
- DAGverse

We also built:

- semantic node-alignment scoring
- recoverability adjustments for title-plus-abstract extraction
- edge-alignment scoring
- prompt-family comparisons (`semantic`, `variable_v1`, `variable_v2`)

This was useful methodological work. It helped clarify where mismatch comes from and what can and cannot be learned from benchmark transfer.

## What we learned

The main issue is not simple extraction failure. The main issue is target mismatch.

In practice, the benchmark graphs often differ from FrontierGraph on at least one of these dimensions:

1. **abstraction level**
   - benchmark graphs may use low-level variables, factor labels, or figure-specific states
   - FrontierGraph often extracts a semantic abstract-level paper graph

2. **graph object**
   - some benchmark graphs represent figure-internal mechanisms
   - FrontierGraph aims to represent a paper-local research graph from title and abstract

3. **recoverability**
   - some benchmark nodes or edges are not really recoverable from title + abstract alone
   - especially when the benchmark was built from fuller paper content or author-provided figures

4. **ontology choice**
   - some disagreements are best described as broader/narrower or partial-overlap concept choices rather than clear errors

## Why we should not use the pooled benchmark numbers in the paper

Even after semantic alignment and recoverability adjustments, the pooled benchmark metrics remain too mixed to serve as clean headline evidence.

That does **not** mean the exercise failed. It means the benchmark is not well aligned enough to the paper's main empirical object.

The risk of reporting pooled benchmark numbers is that a reader may take them as a direct score on graph quality, when in fact they also reflect:

- benchmark-object mismatch
- abstraction mismatch
- title-plus-abstract recoverability limits
- ontology compression choices

So the problem is not only that the numbers are not especially high. It is that they are not cleanly interpretable as a test of the object the paper actually studies.

## What this benchmark work is still good for

This work is still useful internally because it established:

1. exact-match evaluation is too harsh for our object
2. semantic node alignment is more informative than strict label overlap
3. recoverability from title + abstract matters materially
4. prompt tuning can help somewhat, but does not solve graph-object mismatch
5. the paper should rely primarily on **prospective validation**, not external benchmark transfer, for its main validation claim

## Recommended paper use

The recommended use is:

- do **not** report pooled ReCITE or DAGverse benchmark scores as headline paper evidence
- if needed, include only a brief qualitative note that existing external graph benchmarks often encode different graph objects than ours
- if an extraction-validity section is desired, make it small and qualitative:
  - a few hand-reviewed examples
  - explanation of abstraction mismatch
  - explanation of recoverability limits

## Safer phrasing if this work is referenced at all

If we need one sentence for the paper or appendix, it should say something like:

> Existing external graph benchmarks are only partially aligned with our paper-local semantic graph object. In exploratory comparisons, benchmark overlap was limited and heavily shaped by differences in abstraction level, graph target, and what can be recovered from titles and abstracts alone. We therefore do not treat pooled benchmark scores as our primary validation evidence.

That is the defensible interpretation.

## Bottom line

This benchmark work was worth doing because it clarified what external validation can and cannot tell us.

But it should be treated as **exploratory internal diagnostics**, not as omitted strong evidence or as a hidden negative result that the paper ought to foreground.
