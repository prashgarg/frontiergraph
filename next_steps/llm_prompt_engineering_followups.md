# LLM Prompt Engineering Follow-Ups

## What the latest pass improved

Relative to the first LLM screening pass, the current prompt pack now follows the
official GPT-5.4 guidance more closely in four ways:

1. **Compact structured outputs**
   - strict schemas
   - short reasons
   - low verbosity
   - clear output contracts

2. **Pinned reasoning settings**
   - `none` is now treated as the baseline setting
   - `low` is tested as an explicit variant, not mixed in accidentally

3. **Small-change eval discipline**
   - one prompt family change at a time
   - rerun evals after each change
   - compare against previous prompt variants rather than eyeballing examples only

4. **Task decomposition**
   - weak veto
   - scalar diagnostic
   - pairwise within-field reranking
   - rewrite only after screening, not during screening

That is closer to the official pattern:

- keep outputs compact and structured
- keep prompts stable and use API controls where possible
- pin reasoning settings rather than letting defaults drift
- rerun evals after each small change

## What we still were not doing well enough

### 1. We had not defined the score ladder sharply enough

Earlier scalar prompts asked for `1-5` scores without a sufficiently explicit meaning for
each level. The v3 prompt fixed this with score anchors, but this should be treated as a
real methodological change, not a cosmetic wording tweak.

### 2. We had not separated record context from judgment context

The user concern was correct: the graph-derived candidate object is not intuitive if the
prompt sees only a naked JSON row.

The construction-aware prompts now explain:

- what nodes and edges mean
- what the `source -> mediator -> target` compression means
- what support, broadness, resolution, and compression diagnostics mean

But we still do **not** have a clean same-set ablation proving that the construction
context itself improves quality rather than only improving stability.

### 3. We had not tested low-reasoning parse reliability early enough

We were treating `low` as if it were just a cheaper/faster version of `none`.
The v3 pass shows that this is not safe for the current pairwise structured-output prompt.

So for current within-field screening:

- `none` is the baseline
- `low` should be treated as an experimental condition, not a deployment default

### 4. We had not made tie behavior strong enough early enough

For pairwise prompts, “allow ties” is not enough.
The prompt must actively instruct the model not to force a choice when evidence is mixed.

The current pairwise prompt is better, but tie behavior is still something to monitor in
future variants.

## Prompt variants still worth testing

### A. Construction-context ablation

Compare:

- current construction-aware prompt
- otherwise identical prompt with the construction block removed

Purpose:

- isolate whether graph-process explanation actually helps

### B. Journal-bar experimental prompt

This should remain an **experimental downstream prompt only**.
It is not a good main screening prompt because it imports taste and publication-status
judgments too early.

But it may be useful later as a strong-prune layer on already-clean survivors.

Recommended labels:

- `top_journal_bar`
- `solid_field_journal_bar`
- `not_journal_ready`

### C. Pairwise-with-rubric prompt

Instead of only asking for `A/B/tie`, ask the model to fill a short rubric first:

- endpoint specificity winner
- mechanism clarity winner
- question-object clarity winner
- overall winner

This could improve auditability and make reversals easier to diagnose.

### D. Survivor rewrite prompt

Keep this as a second-stage prompt only.

Use case:

- rewrite already-screened survivors into cleaner economist-facing wording

Do **not** use it to invent new mechanisms, nodes, or edges.

### E. Mechanism-suggestion prompt

This should stay open but parked.

It may later make sense for future-looking frontier exploration to ask the model for:

- a sharper mechanism phrasing
- a narrower question rewrite
- or a suggested mediator interpretation

But it should not be mixed into the historical benchmark or into the first-pass screen.

## Paper-facing recommendations

When this goes into the paper or appendix:

1. show at least two prompt variants, not one
2. state what fields were hidden from the model
3. state that the LLM screens local question sharpness, not importance or impact
4. report repeatability / agreement, not just one-shot examples
5. report the reasoning setting explicitly
6. report that `low` reasoning under the current pairwise schema degraded parse reliability

## Official guidance this aligns with

- Prompt guidance for GPT-5.4:
  - https://developers.openai.com/api/docs/guides/prompt-guidance#keep-outputs-compact-and-structured
- Structured Outputs:
  - https://developers.openai.com/api/docs/guides/structured-outputs#structured-outputs-vs-json-mode
- GPT-5 series new params and tools:
  - https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools
- GPT-5.4 reasoning-effort support:
  - https://developers.openai.com/api/docs/guides/latest-model#faq
