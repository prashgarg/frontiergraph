# Superseded `path_to_direct` Refresh Status

Date: 2026-04-09

This note records an earlier pre-effective-corpus refresh pass. It is kept only as
workflow memory and should not be quoted for current paper winners or benchmark levels.

Current references:

- `next_steps/current_locked_vs_open_decisions.md`
- `next_steps/method_v2_design.md`
- `next_steps/full_paper_refresh_audit_2026_04_11.md`

Current paper-consistent winners:

- `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`, pool `5000`
- `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`, pool `5000`
- `h=15`: `glm_logit + quality`, `alpha=0.05`, pool `5000`

Current paper-consistent benchmark levels:

- `h=5`: `P@100 = 0.1050`, `Recall@100 = 0.1376`, `MRR = 0.0133`
- `h=10`: `P@100 = 0.2067`, `Recall@100 = 0.1391`, `MRR = 0.0103`
- `h=15`: `P@100 = 0.2640`, `Recall@100 = 0.1541`, `MRR = 0.0116`

## Earlier scope completed

This note records the completed paper-grade method-v2 refresh on the frozen ontology
baseline for the headline family:

- ontology baseline: frozen `v2.3`
- family: `path_to_direct`
- main anchor: `causal_claim`
- horizons: `5, 10, 15`
- reranker retune: completed
- concentration comparison: completed
- current frontier build: completed

The parallel `direct_to_path` family remains conceptually in scope but is not yet
refreshed to the same paper-grade standard.

## Earlier winners and benchmark summary

The remaining details below refer to that earlier pass and are superseded by the current
effective-corpus benchmark.

## Concentration winners by horizon

- `h=5`: `sink_plus_diversification`
- `h=10`: `diversification_only`
- `h=15`: `sink_plus_diversification`

Selected using the explicit paper-facing rule:

1. keep only variants with non-negative mean `Recall@100` and `MRR` relative to the
   unregularized reranker winner
2. among those, minimize mean `top_target_share@100`
3. tie-break by highest mean `unique_theme_pair_keys@100`
4. final tie-break prefers `diversification_only`

Source: `outputs/paper/77_method_v2_concentration_path_to_direct/selected_concentration/recommended_concentration_configs.csv`

## Shortlist inspection

The refreshed current frontier is readable and no longer obviously broken by internal
placeholder states, but the surfaced shortlist is not a pure “fully open missing edge”
object.

Observed top-shortlist pattern:

- top surfaced rows are almost entirely `candidate_subfamily = causal_to_identified`
- `candidate_scope_bucket` is almost entirely `anchored_progression`
- `candidate_family` is almost entirely `mediator_expansion`

So the current strongest surfaced `path_to_direct` shortlist is best described as:

- a headline `path_to_direct` benchmark family
- whose strongest surfaced examples are mostly anchored mechanism-deepening questions

That is a useful empirical result. It means the method’s best current outputs are not
generic fully open gaps. They are questions where the literature already has meaningful
ordered or causal structure and the next useful step is to deepen or tighten it.

## Remaining concentration issue

Concentration improved, but it is not solved.

Repeated targets still appear often in the surfaced top-100, especially:

- `Willingness to Pay.`
- `Renewable Energy`
- `R&D`

This should be described in the paper as a real improvement with residual crowding, not
as a full fix.

## Paper-facing curated examples worth using

Examples that remain readable without leaning on repeated WTP-style targets:

- `Digital economy -> Environmental Regulation`
- `Trade Liberalization -> R&D`
- `Environmental quality -> Green innovation`
- `Green innovation -> Technological Innovation.`
- `R&D -> Carbon emission trading`
- `Renewable Energy -> Urbanization`

These are better main-text examples than repeatedly foregrounding the most crowded
targets.

## Still pending

- full non-sampled `direct_to_path` reranker retune and concentration comparison
- human-usefulness pack
- supply-vs-demand ranking extension
