# Strong Substantive Review Note

## Scope

This note reviews:

- `outputs/paper/32_strong_substantive_regime_review/strong_substantive_candidates.csv`
- `next_steps/reviewed_relation_semantics_overrides.csv`

The goal is to reassess the strong-substantive queue after the final residual relation-semantics pass.

## Main result

The queue is now empty.

Current counts are:

- `strong_substantive_rows`: `0`
- `direct_substantive_review`: `0`
- `paper_candidate_count`: `0`

## What changed

The last surviving row was:

- `inflation -> unemployment`

That pair is no longer being treated as a residual strong-substantive unresolved case.
It now lives in:

- `next_steps/reviewed_relation_semantics_overrides.csv`

with reviewed residual semantics:

- `macro_tradeoff_relation`

So the old strong-substantive queue has now been fully absorbed by reviewed internal edge typing.

## Interpretation

This settles the question more cleanly than before.

The earlier strong-substantive cluster was not a missing surfaced object family waiting to be promoted.
It was a small queue of substantively important pairs that still lacked reviewed internal edge typing.

Now that:

- the `13` reviewed design-family overrides are integrated, and
- the last residual semantics case is reviewed,

the queue no longer survives on the unresolved review surface.

## Current judgment

The project should **not** create a dedicated substantive frontier-object family from the current state.

The remaining work should stay in:

- reviewed override maintenance
- shortlist curation
- paper consolidation

not new ontology-vNext family growth.

## Recommendation

Do:

1. treat ontology-vNext as frozen except for future reviewed override tables
2. keep the reviewed design-family, policy-semantic, and relation-semantic tables as the stable internal source of truth
3. move the center of gravity back to surfaced shortlist quality and paper framing

Do not:

- reopen substantive frontier-family creation now

## Stability

This pass did **not** change:

- reviewed family count, which remains `6`
- family seed rows, which remain `25`
- routed shortlist counts, which remain `14` `context_transfer` and `7` `evidence_type_expansion`
