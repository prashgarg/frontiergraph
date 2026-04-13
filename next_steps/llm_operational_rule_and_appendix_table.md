# LLM Operational Rule and Appendix Table

Date: 2026-04-11

## Purpose

This note freezes the current paper-facing description of the LLM layer.

It does three things:

1. states the operational decision rule in plain language
2. states what role manual inspection does and does not play
3. provides an appendix-style prompt summary table

The LLM layer is a current-frontier cleanup layer. It is not the historical benchmark.

## Main-text operational rule

The LLM layer is applied only to the within-field browse object.

The current workflow is:

1. Construct endpoint-first within-field shelves from the graph-ranked current frontier.
2. Run a coarse veto screen (`E`) on each candidate.
3. Drop a candidate only when all of the following hold:
   - the veto prompt returns `fail`
   - veto confidence is at least `4`
   - the reported failure mode is substantive rather than stylistic:
     - `broad_endpoint`
     - `generic_mediator`
     - `method_not_mechanism`
     - `canonical_pairing`
     - `placeholder_like`
     - `unclear_question_object`
   - the scalar screening prompt (`G`) gives an overall screening score of at most `2`
4. For the surviving candidates, run repeated within-field pairwise comparisons (`H`).
5. Convert the repeated pairwise outcomes into a stable local ranking within each field shelf.
6. Use the scalar screening score from `G` only as a secondary diagnostic and tie-breaker, not as the main decision rule.

In short:

- `E` is a weak veto only
- `H` is the main ordering rule
- `G` is secondary

## What the LLM is being asked to judge

The LLM is not asked to judge:

- importance
- truth
- policy value
- publishability
- citation potential
- topic prestige

It is asked to judge only local screening quality:

- are the endpoints specific
- is there a plausible focal mechanism
- does the object read like a coherent research question
- is the wording generic, canonical, or semantically mismatched

That narrower role is the main reason the current design is defensible.

## What manual inspection does

Manual inspection remains part of the workflow, but not as the main ranking rule.

Its role is:

- prompt development
- sanity-checking disagreement cases
- inspecting obvious false positives and false negatives
- selecting illustrative examples for the paper

Its role is not:

- hand-ranking the full candidate set
- overriding the main automated within-field ordering item by item
- replacing the stated veto and pairwise rules with ad hoc editorial judgment

So the paper should not say “we manually inspected and kept the good ones” as if that were the main method.

The correct statement is closer to:

“We used manual inspection to develop and audit the LLM screening layer, while the operational within-field ordering followed a fixed weak-veto plus repeated pairwise rule.”

## Why this design was chosen

The current evidence favors pairwise within-field comparisons over one-row scalar scoring.

Reasons:

- pairwise judgments are more stable than scalar scores
- within-field comparisons are easier than global judgments
- pairwise prompts are less likely to over-credit locally plausible but semantically odd candidates
- the weak-veto rule removes obvious local failures without letting the veto prompt dominate the full ranking

The scalar prompt remains useful, but mainly as:

- a tie-breaker
- a sanity check
- an auxiliary audit signal

## Cost for the current operating design

Using `gpt-5.4-mini` at current list pricing:

- input: `$0.75 / 1M`
- output: `$4.50 / 1M`

Observed costs on the current within-field package were approximately:

- `E` once on `1791` candidates: `$2.04`
- `G` once on `1791` candidates: `$3.11`
- `H` once on `2000` pairs: `$3.42`

So:

- lean run:
  - `E` once + `G` once + `H` once
  - about `$8.57`
- stability-focused run:
  - `E` once + `G` once + `H` three times
  - about `$15.41`

These are observed token-based estimates from the current logs, not rough priors.

## Appendix-style prompt table

| Prompt | What it sees | What it outputs | Why we tried it | What we learned | Operational status |
|---|---|---|---|---|---|
| `A` semantic-blind scalar | labels, family tags, no graph diagnostics | scalar screening scores plus flags | test whether semantics alone catches malformed objects | good at catching semantic nonsense, but relatively harsh and context-poor | retired as main prompt; useful as a comparison baseline |
| `B` record-aware scalar | labels plus graph-local diagnostics | scalar screening scores plus flags | test whether numeric graph diagnostics improve one-row screening | original version was too forgiving on semantically odd candidates | retired |
| `B v2` stricter record-aware scalar | same as `B`, with explicit skepticism about semantically weak objects | scalar screening scores plus flags | repair the over-generosity of `B` | directionally better than `B`, but still not the best main operational object | retained only as a design step on the way to `G` |
| `C` pairwise within-field | two candidates from same field and horizon | preferred candidate or tie | test whether local comparisons work better than one-row scoring | pairwise within-field is substantially more useful than global scalar screening | superseded by construction-aware `H` |
| `E` veto screen | one candidate, skeptical first-pass screen | `pass`, `review`, or `fail`, with failure mode and confidence | identify obvious local failures | useful as a weak veto, too strict as a hard filter | kept as weak veto only |
| `F` swapped-order pairwise | same as `C`, but candidate order reversed | preferred candidate or tie | test order sensitivity in pairwise judgments | pairwise judgments were fairly stable under order swap | diagnostic only |
| `G` construction-aware scalar | one candidate plus explanation of graph-derived fields and score anchors | scalar screening scores plus flags | make scalar scoring more natural and auditable | reasonably stable and interpretable, but weaker than pairwise as the main ordering device | kept as secondary diagnostic and tie-breaker |
| `H` construction-aware pairwise | two candidates plus explanation of graph-derived fields and tie guidance | preferred candidate or tie, with confidence | pairwise within-field reranking with explicit construction context | strongest current prompt family; stable enough to support local ordering | main operational prompt |
| `J` journal-bar prompt | one candidate framed in publication-tier terms | journal-bar style classification | explore a strong-pruning editorial screen | imports prestige and taste too early; harder to defend as a method object | experimental only, not operational |

## Paper wording suggestion

Main text:

“On the within-field browse object, we use the LLM only for local semantic cleanup. We first apply a conservative veto to obvious local failures, and then rerank the surviving candidates using repeated pairwise comparisons within field and horizon. A scalar LLM screening score is retained only as a secondary diagnostic.”

Appendix:

- list the prompts
- state which fields were hidden
- state the schema for each prompt
- report repeatability and agreement
- state that the LLM screens local question sharpness rather than impact or importance

## Current recommendation

For the next implementation pass:

1. keep the operational rule fixed
2. apply it to the actual within-field browse package
3. audit the resulting shelves manually
4. only then decide whether a global-scan LLM layer is worth adding
