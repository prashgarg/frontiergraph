# Method-v2 Human Usefulness Analysis

## Status

This note analyzes the filled human usefulness pack. The filled sheet is treated as read-only user input.

## Main read

- total rated rows: `24`
- graph-selected mean overall score: `3.222`
- preferential-attachment mean overall score: `3.222`
- overall-score gap (graph minus preferential attachment): `0.000`
- readability gap: `-0.333`
- usefulness gap: `0.083`
- interpretability gap: `0.250`
- artifact-risk advantage (preferential attachment minus graph): `0.084`

The current human ratings are mixed rather than one-sided.

- There is no overall mean-score gap.
- Graph-selected items do modestly better on interpretability, usefulness, and artifact risk.
- Preferential-attachment items do slightly better on readability.
- The graph-selected set also has a larger share of high-usefulness ratings (`>=4`).

## Dimension definitions

- readability:
  - narrow surface fluency
  - are the displayed labels easy to read, or do they contain obvious malformed tokens,
    stray abbreviations, or awkward string artifacts such as `12 as`
- interpretability:
  - can the reader tell what relationship or bridge is being proposed?
- usefulness:
  - does the object look like a usable research question, even if it would still need
    rewriting or refinement?
- artifact risk:
  - does the object read like a graph artifact rather than a genuine question object?

## Horizon read

- `h=5`
  - graph overall mean: `3.333`
  - pref-attach overall mean: `3.083`
  - graph readability mean: `3.750`
  - pref-attach readability mean: `3.750`
  - graph interpretability mean: `3.000`
  - pref-attach interpretability mean: `2.750`
  - graph usefulness mean: `3.250`
  - pref-attach usefulness mean: `2.750`
- `h=10`
  - graph overall mean: `3.000`
  - pref-attach overall mean: `3.333`
  - graph readability mean: `3.500`
  - pref-attach readability mean: `4.000`
  - graph interpretability mean: `3.000`
  - pref-attach interpretability mean: `3.000`
  - graph usefulness mean: `2.500`
  - pref-attach usefulness mean: `3.000`
- `h=15`
  - graph overall mean: `3.333`
  - pref-attach overall mean: `3.250`
  - graph readability mean: `3.250`
  - pref-attach readability mean: `3.750`
  - graph interpretability mean: `3.500`
  - pref-attach interpretability mean: `3.000`
  - graph usefulness mean: `3.250`
  - pref-attach usefulness mean: `3.000`

## Threshold view

- graph usefulness `>=4` share: `0.500`
- pref-attach usefulness `>=4` share: `0.333`
- graph artifact-high share: `0.250`
- pref-attach artifact-high share: `0.167`

## Paper use

This is the external human usefulness check aligned to the appendix LLM usefulness object. The current result supports a cautious paper claim: graph-selected current-frontier objects look somewhat more interpretable and somewhat less artifact-like than preferential-attachment-selected objects, but the small pack does not support a blanket claim of a large overall human-rated advantage.
