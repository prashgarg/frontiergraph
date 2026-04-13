# Current 2026 Candidate Audit: `gpt-5-nano` vs `gpt-5-mini`

## What we ran

We audited the current top 100 public FrontierGraph candidates from:

- `site/src/generated/site-data.json`

using the structured candidate-audit prompt and schema in:

- `next_steps/llm_audit/system_prompt_candidate_audit.md`
- `next_steps/llm_audit/user_prompt_candidate_audit_template.md`
- `next_steps/llm_audit/candidate_audit_schema.json`

The two judge runs are:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_audit_gpt5nano_low_v1`
- `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_audit_gpt5mini_low_v1`

The direct model comparison is in:

- `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_audit_model_comparison_v1/aggregate.json`

## Main result

`gpt-5-mini` does **not** look like it is buying enough to justify using it as the default audit model.

The striking pattern is not that mini is more nuanced. It is that mini is much more willing to collapse candidates into the same diagnosis:

- `nano`: `72 keep`, `28 downrank`
- `mini`: `2 keep`, `98 downrank`

Both models still point toward the same broad methodological lesson:

- most current candidates probably want to be reframed as path-level objects rather than direct-edge objects

But mini appears to be doing this in a much more one-note way.

## Agreement rates

Across the 100 overlapping rows:

- decision agreement: `0.30`
- main-reason agreement: `0.68`
- better-formulation agreement: `0.84`
- shortlist agreement: `0.38`

So the two models often agree on the broad *type* of reformulation, but not on whether the candidate should still be kept on the shortlist as currently useful.

## How mini differs from nano

The most important pattern is:

- `70` rows are `keep` under nano but `downrank` under mini

This means mini is not mostly finding a different class of errors. It is mostly applying a stricter threshold to the same underlying interpretation.

Main reasons:

- `nano`:
  - `should_be_path_level_not_direct_edge`: `70`
  - `promising_as_is`: `18`
  - `already_saturated`: `5`
  - `not_paper_shaped`: `5`

- `mini`:
  - `should_be_path_level_not_direct_edge`: `96`
  - `should_be_mediator_expansion`: `4`

This suggests mini is collapsing several qualitatively different cases into the same diagnosis:

- promising direct-edge candidates
- saturated candidates
- weakly paper-shaped candidates

That makes it less useful as a diagnostic critic.

## Score comparison

Average scores, mini minus nano:

- candidate quality: `-0.20`
- paper-shapedness: `+0.11`
- mechanism support: `-0.29`
- genericity: `-0.26`

This is consistent with mini reading the same candidates as somewhat less compelling overall, while not actually surfacing much more structural differentiation.

## Cost

Estimated costs from actual token usage:

- `nano`: about `$0.127`
- `mini`: about `$0.356`

So mini cost about `2.8x` as much as nano on the same 100 rows.

Given the result pattern above, that extra cost does not currently look worth paying for bulk audit use.

## Recommendation

Use `gpt-5-nano` as the default current-candidate audit model.

Use mini only in one of two roles:

1. spot-checking a small disagreement set where we want a second opinion
2. later prompt-development work, if we want to make the audit schema less binary about direct-edge versus path-level reframing

## Methodological takeaway

This audit was useful. The main signal is not "mini is better." The main signal is:

- a large share of current candidates are being interpreted as interesting but better posed as path-level questions

That strengthens the case for moving path-level objects higher in the roadmap.

It also suggests a next deterministic improvement:

- classify current candidates by whether they should remain direct-edge objects or be lifted into path-level / mediator-expansion objects before final ranking

## Small implementation note

The mini run had one initial parse failure on:

- `FG3C000215__FG3C001052`

We reran that row successfully, so the final comparison is complete at 100 rows.
