# Method v2 Benchmark Target Note

Date: 2026-04-09

## Purpose

This note makes the benchmark target explicit for method v2.

It exists because the project now distinguishes three different objects that were easier
to blur together in earlier drafts:

- the historical continuity anchor
- the substantive target family
- the surfaced research question shown to a human reader

The paper and the implementation should keep those objects separate.

## 1. Main historical anchor and nested strict anchor

Method v2 should now distinguish two nested anchors.

### Main historical anchor

Use:

- later appearance of a missing ordered causal-language claim

Operationally:

- `directionality_raw = directed`
- `causal_presentation in {explicit_causal, implicit_causal}`

Why this becomes primary:

- it matches the plain-language meaning of an ordered claim better than the old benchmark-causal layer
- it is much less sparse
- it remains economics-facing and claim-shaped
- it avoids using the word "directed" to mean "identified causal by method class"

Recommended robustness cut:

- rerun the same main benchmark using `explicit_causal` only

Why:

- it shows that the broader main anchor is not being driven only by more weakly phrased implicit-causal language
- it keeps the main object broad while still offering a stricter language-based robustness check

### Nested strict anchor

Retain:

- later appearance of a missing identified-causal claim

Operationally:

- the current strict method-based causal layer

Why it stays:

- dated
- prospectively testable
- historically benchmarkable
- valuable as a stricter secondary check

This keeps continuity with the current paper without forcing the strict layer to remain the only headline object.

## 2. Reopened substantive target family

Method v2 is allowed to reopen what sits above the anchor.

The project should now treat three candidate families as first-class:

### `path_to_direct`

- candidate object: unresolved ordered pair with nearby path support already present
- historical event: later ordered-claim closure in the main anchor, with stricter closure checked in the nested identified-causal anchor
- interpretation: the literature had local mechanism or path support before the direct claim became explicit

### `direct_to_path`

- candidate object: direct edge already exists, but later work thickens the mediator structure around it
- historical event: later path thickening
- interpretation: scientific development can deepen around an existing direct relation rather than only closing a missing direct edge

### `mediator_expansion`

- candidate object: unresolved endpoint pair where the substantive open question is which mediator carries the relation
- historical event: later mediator emergence or mechanism thickening where the family definition makes that meaningful
- interpretation: the useful question is not only whether the endpoints connect, but how they connect

## 3. Surfaced research question

This is the human-facing object shown in the paper or UI.

It is not identical to the benchmark anchor.

Typical surfaced forms:

- raw anchor wording
- path-rich wording
- mechanism-rich wording

The rule is:

- evaluate one clean historical object
- surface a richer research question when that improves readability and actionability

## 4. What the implementation must emit

Every candidate row in method v2 should carry:

- `candidate_family`
- `anchor_type`
- `evaluation_target`
- anchor endpoint IDs and labels
- surfaced wording inputs
- local evidence provenance

That prevents family assignment from being inferred ad hoc later in reporting code.

## 5. What the paper should and should not claim

### The paper can claim

- the historical backtest uses a clean continuity anchor
- richer surfaced questions are built around that anchor
- different candidate families correspond to different kinds of research development

### The paper should not claim

- that every surfaced question is validated by the same historical event
- that path thickening and direct-link appearance are interchangeable outcomes
- that one scalar ranking metric fully captures every family’s value

## 6. Evaluation ladder

Method v2 should use a layered evaluation design.

### Layer A. Main anchor task

- later appearance of a missing ordered causal-language claim

### Layer A2. Nested strict anchor task

- later appearance of a missing identified-causal claim

### Layer B. Family-aware extensions

- later path thickening for `direct_to_path`
- mediator growth or mechanism thickening for `mediator_expansion`

### Layer C. Screening-quality outputs

- family mix
- concentration
- diversity
- duplicate/crowding diagnostics

### Layer D. Human-usefulness validation

- graph-selected versus baseline-selected items
- raw anchor wording versus path/mechanism wording

## 7. Why this note matters

Without this separation, the project can drift into two bad habits:

1. using the narrow anchor as if it were the full research question
2. using the richer surfaced question as if it had already been historically validated on identical terms

Method v2 should do neither.

The anchor stays for continuity.
The target family reopens the substantive object.
The surfaced question remains the human-facing interpretation layer.
