# Revised Paper Outline

Date: 2026-04-05

This is the recommended outline for the next paper pass under the frozen-ontology strategy.

## 1. Question and setting

- why question choice is the bottleneck
- why economics is a useful test bed
- what the paper does in one sentence:
  - use missing directed links as retrieval anchors
  - surface path-rich or mechanism-rich next questions

## 2. Corpus, paper-local extraction, and normalization

- corpus and sample
- paper-local extraction
- normalization
- enough detail to make the benchmark object interpretable

## 3. Retrieval anchors, surfaced questions, and evaluation design

- direct-edge anchor as benchmark object
- path-rich and mechanism-rich surfaced questions
- gap vs boundary anchors
- score ingredients
- prospective rolling-cutoff benchmark

## 4. Main benchmark results

- strict shortlist result
- attention-allocation frontier
- value-weighted rerun
- keep this section symmetric and simple

## 5. Where structure helps more

- heterogeneity by journal tier, method family, and major topic groups
- keep the main text on robust patterns only

## 6. Path development and richer question objects

- `path_to_direct`
- `direct_to_path`
- why many surfaced objects are better read as path-rich or mechanism-rich
- current path-rich examples

## 7. Discussion and limits

- future appearance is not truth or welfare
- benchmark is on direct-link anchors
- surfaced research object is richer than the benchmark event
- what the current paper does and does not claim

## 8. Deferred next iteration

This stays brief in the main paper.

- learned reranking within the current graph
- richer ripeness objects
- later ontology redesign

## Main drafting rule

The paper should move in this order:

1. explain the benchmark object clearly
2. explain the surfaced object clearly
3. show the main comparison simply
4. only then add richer path-development evidence

The path/mechanism language should not appear as an appendix-style afterthought. It should be integrated into the object definition early, while keeping the benchmark target itself clean.
