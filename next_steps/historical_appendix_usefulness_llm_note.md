# Historical Appendix LLM Usefulness Sweep

## Purpose

This is an appendix-style usefulness evaluation on the historical benchmark objects.

It is not a historical forecasting test.

The LLM is asked only whether a surfaced object looks like:

- a readable research-question object
- an interpretable relationship
- a usable candidate question
- or a graph artifact

## Prompt object

Lean raw-triplet prompt with construction note.

Displayed record:

- raw triplet: `A -> B -> C`
- short construction note explaining that the middle term is an intervening concept
  from the literature graph and may represent a mechanism, channel, condition,
  policy lever, or other bridge

This is more defensible than forcing mechanism wording.

## Exercise grid

Built from the widened benchmark in `123`.

- horizons:
  - `h=5`: `6` cutoffs
  - `h=10`: `6` cutoffs
  - `h=15`: `5` cutoffs
- total exercises: `17`
- shortlist size per exercise: `250`
- arms:
  - adopted reranker
  - transparent retrieval
  - preferential attachment

Total requests:

- `17 × 250 × 3 = 12,750`

Prompt pack:

- `outputs/paper/124_historical_appendix_usefulness_pack`

Run:

- `outputs/paper/127_historical_appendix_usefulness_full`

Analysis:

- `outputs/paper/128_historical_appendix_usefulness_analysis`

## Cost

Observed full-run usage on `gpt-5.4-mini`, `reasoning.effort = none`:

- requests: `12,750`
- input tokens: `6,020,714`
- output tokens: `881,637`
- reasoning tokens: `0`
- actual estimated cost: `$8.48`

Observed prompt size:

- input tokens per request: `472.2`
- output tokens per request: `69.1`

So the appendix sweep is cheap enough to keep.

## Main result

Pooled over the full widened historical grid, the ranking is:

- adopted > transparent > preferential attachment

Mean usefulness score:

- `h=5`
  - adopted: `2.292`
  - transparent: `2.212`
  - pref-attach: `1.898`
- `h=10`
  - adopted: `2.345`
  - transparent: `2.178`
  - pref-attach: `1.862`
- `h=15`
  - adopted: `2.372`
  - transparent: `2.203`
  - pref-attach: `1.855`

So the graph-selected historical shortlist looks better than both baselines under the
same current-usefulness rubric.

## Important nuance

The raw-triplet prompt is harsh in absolute terms.

Across all `12,750` items:

- mean readability: `2.81`
- mean interpretability: `1.88`
- mean usefulness: `1.71`
- artifact risk:
  - `high`: `10,696`
  - `medium`: `2,019`
  - `low`: `35`

This means the appendix result should be read as a **relative** comparison, not as a
claim that the historical shortlists are already clean natural-language questions.

## Early vs late nuance

The pooled result hides a meaningful era interaction.

### Early era (`1990, 1995`)

Transparent can look slightly cleaner than adopted.

Examples:

- `h=5`
  - adopted: `2.015`
  - transparent: `2.324`
- `h=10`
  - adopted: `2.118`
  - transparent: `2.245`
- `h=15`
  - adopted: `2.257`
  - transparent: `2.259`

Interpretation:

- in the early era, the adopted reranker is surfacing harder, more predictive, but
  linguistically rougher graph objects
- transparent rankings in that era are often semantically cleaner but historically
  weaker

### Late era (`2000+`)

Adopted clearly beats transparent.

Examples:

- `h=5`
  - adopted: `2.431`
  - transparent: `2.156`
- `h=10`
  - adopted: `2.458`
  - transparent: `2.144`
- `h=15`
  - adopted: `2.449`
  - transparent: `2.166`

Interpretation:

- once the literature is richer, the adopted reranker improves both historical
  prediction and current-usefulness appearance

## What this is good for in the paper

Good use:

- appendix robustness evidence that graph-selected objects are better than baseline
  objects on a current-usefulness rubric
- especially credible in the later era

Bad use:

- do not present this as the main historical benchmark
- do not treat the absolute score levels as a statement that the shortlist is already
  polished human-facing language

## Practical implication

For the paper:

- keep this as appendix evidence
- emphasize relative separation across arms
- explicitly note the early-versus-late interaction

For the website later:

- this reinforces the case for a later rewrite / rendering layer, because many raw
  historical triplets are useful comparatively but still look graph-like in absolute
  terms
