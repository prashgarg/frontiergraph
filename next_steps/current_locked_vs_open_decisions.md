# Current Locked vs Open Decisions

Date: 2026-04-09

## Locked

- ontology baseline is frozen at `v2.3`
- ontology quality and ranking quality must remain separated
- the recommendation object stays endpoint-centered or endpoint-plus-mediator centered
- richer motifs are evidence, not the main paper-facing object
- candidate families remain compact:
  - `path_to_direct`
  - `direct_to_path`
  - `mediator_expansion`
- evidence motifs may be richer and multi-valued
- the main historical anchor is:
  - later appearance of a missing `causal_claim`
  - operationally: `directionality_raw = directed` and `causal_presentation in {explicit_causal, implicit_causal}`
- the nested stricter benchmark is:
  - later appearance of a missing `identified_causal_claim`
- explicit-only causal language is a planned robustness cut on the main anchor
- undirected contextual structure remains support, not noise
- candidate generation v2 must emit a structured local evidence object, not just a pair and a score
- candidate rows now carry explicit within-family structure:
  - `candidate_family`
  - `candidate_subfamily`
  - `candidate_scope_bucket`
- the paper should keep benchmark anchor and surfaced question clearly separate

## Paper refresh locked now

- the following manuscript components are now treated as current enough to keep while the remaining sections are refreshed:
  - main `1990–2015` benchmark framing
  - strict shortlist benchmark text
  - refreshed main benchmark figure
  - main benchmark summary table
  - appendix placement and cautious wording for the human usefulness check
  - appendix placement and cautious wording for the LLM usefulness sweep
  - corpus / extraction / ontology description
  - credibility audit tables
  - corpus growth figure
- these items should not be reopened unless a later upstream method change directly invalidates them
- paper refresh execution list:
  - `next_steps/paper_refresh_checklist_2026_04_11.md`

## Recommended and likely to freeze next

- layer names:
  - `contextual_pair`
  - `ordered_claim`
  - `causal_claim`
  - `identified_causal_claim`
- transparent model redesign:
  - family-specific eligibility
  - then a decomposable additive transparent score
- broad `path_to_direct` should remain the default continuity family
- the anchored `path_to_direct` slice should be treated as a robustness or shortlist slice, not as a replacement benchmark
- objective-specific working pool defaults:
  - single global exploratory top-`100`: `5000`
  - top-`100` within field: `2000`
  - larger global scan budgets such as top-`250` / top-`1000`: `2000`
- current within-field shelves are useful browse objects, but not yet clean enough to treat as final subfield shelves:
  - the first cleanup audit shows non-trivial mediator-only shelf assignment
  - future field-shelf cleanup should move toward endpoint-first matching
- working within-field shelf rule is now endpoint-first with mediator fallback:
  - endpoints decide field shelf when they provide signal
  - mediator-only placement is allowed only when endpoints give no field signal

## Newly locked from the paper-grade `path_to_direct` refresh

- headline family remains broad `path_to_direct`
- main benchmark object is the `causal_claim` anchor on that family
- the paper-grade reranker winner is horizon-specific rather than global:
  - `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`, pool `5000`
  - `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`, pool `5000`
  - `h=15`: `glm_logit + quality`, `alpha=0.05`, pool `5000`
- on the refreshed `path_to_direct` benchmark, the learned reranker clearly beats both the transparent score and preferential attachment:
  - `h=5`: `P@100 = 0.1050`, `Recall@100 = 0.1376`, `MRR = 0.0133`
  - `h=10`: `P@100 = 0.2067`, `Recall@100 = 0.1391`, `MRR = 0.0103`
  - `h=15`: `P@100 = 0.2640`, `Recall@100 = 0.1541`, `MRR = 0.0116`
- the transparent score remains useful as a readable retrieval layer but is materially weaker than the reranker on the refreshed main family
- concentration should remain a post-ranking layer, not part of the benchmark winner definition
- the paper-facing concentration winner is also horizon-specific:
  - `h=5`: `sink_plus_diversification`
  - `h=10`: `diversification_only`
  - `h=15`: `sink_plus_diversification`
- the current surfaced `path_to_direct` frontier is not mostly a fully open pool in practice
  - the surfaced top-100 is almost entirely `candidate_subfamily = causal_to_identified`
  - so the paper-facing shortlist is best read as anchored progression / mechanism-deepening questions inside the headline family
- concentration is improved but not solved
  - repeated endpoints such as `Willingness to Pay.`, `Renewable Energy`, and `R&D` still recur in the surfaced shortlist
  - this should be acknowledged directly in the paper rather than described as fully fixed
- the human-validation protocol is now prepared:
- the aligned human-usefulness pack is now filled and analyzed:
  - a balanced 24-item graph-vs-preferential-attachment blinded pack
  - an aligned v2 usefulness pack now also exists using the same rating object as the
    appendix LLM usefulness pass:
    - raw triplet `A -> B -> C`
    - short construction note
    - readability
    - interpretability
    - usefulness
    - artifact risk
  - current read:
    - no overall mean-score advantage for graph-selected items
    - modest graph-selected edge on interpretability, usefulness, and artifact risk
    - slight preferential-attachment edge on readability
  - use this as cautious external validation, not as a large human-rated win

- the refreshed appendix reruns change two older paper-facing stories:
  - the transparent graph score helps most at tight reading budgets, with its edge fading as the shortlist becomes very broad
  - the transparent score helps more in dense than sparse local neighborhoods, and its relative edge is larger in lower-FWCI than in high-FWCI slices

## Newly locked from the quality / surface-layer pass

- a narrow full-sample confirmation on a different corpus showed `quality` winning all three horizons, so the quality-layer features are real rather than a sampling artifact
- on the paper-consistent effective corpus, the adopted reranker stack remains horizon-specific:
  - `h=5`: `glm_logit + family_aware_boundary_gap`, `alpha=0.20`, pool `5000`
  - `h=10`: `pairwise_logit + family_aware_composition`, `alpha=0.10`, pool `5000`
  - `h=15`: `glm_logit + quality`, `alpha=0.05`, pool `5000`
- the first calibrated paper-worthiness / de-crowding layer should be treated as a post-frontier surfacing layer, not as a new historical benchmark
- the tuned surface-layer backtest is historically positive at all three horizons:
  - it lowers top-target concentration
  - it raises unique theme-pair coverage
  - and it slightly improves `Recall@100` and `MRR`
- the selected paper-facing surface layer is also horizon-specific:
  - `h=5`: `top_window=300`, `broad_lambda=6.0`, `source_repeat=2.0`, `target_repeat=4.0`, `family_repeat=6.0`, `theme_pair_repeat=4.0`, `broad_repeat_lambda=4.0`
  - `h=10`: `top_window=200`, `broad_lambda=9.0`, `source_repeat=1.0`, `target_repeat=4.0`, `family_repeat=6.0`, `theme_pair_repeat=2.0`, `broad_repeat_start_pct=0.90`, `broad_repeat_lambda=4.0`
  - `h=15`: `top_window=200`, `broad_start_pct=0.90`, `broad_lambda=6.0`, `source_repeat=1.0`, `target_repeat=4.0`, `family_repeat=6.0`, `theme_repeat=2.0`, `theme_pair_repeat=4.0`, `broad_repeat_lambda=4.0`
- the rebuilt current frontier now exists at:
  - `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface`
- the rebuilt current frontier is less crowded, but still not paper-stable:
  - WTP share is lower
  - target concentration is lower
  - theme diversity is higher
  - but the surfaced top ranks are still dominated by broad `causal_to_identified` anchored progression questions
  - so this should be treated as an improved shortlist, not the final paper-facing examples set
- the retrieval-versus-reranking distinction now needs to be made explicit in the paper
  methods:
  - transparent score = retrieval layer
  - learned reranker = reordering within the retrieved pool
  - pool size = tuned design parameter rather than fixed scientific object
- the first broad-anchored candidate-generation v3 gate should currently be treated as
  a **current-frontier screening rule**, not as a historically validated generator
  improvement:
  - the narrow sweep in `outputs/paper/87_candidate_generation_v3_threshold_sweep`
    shows current-frontier bite
  - but not clear bite on the cached historical panel
- frontier output smoke coverage now exists for the active current-frontier artifacts:
  - `tests/test_frontier_output_smoke.py`
  - this guards against silent `_x` / `_y` merge suffix drift and missing surfaced
    columns in the active `85` and `93` frontier outputs
- appendix-ready LLM screening prompt materials are now prepared, but not yet run:
  - prompt variants `A` semantic-blind, `B` record-aware, `C` pairwise within-field, plus survivor rewrite prompt `D`
  - strict JSON schemas and batch-ready `2000`-request JSONL files now exist in `outputs/paper/97_llm_screening_prompt_pack`
  - the refreshed endpoint-first pairwise pack now exists in `outputs/paper/99_llm_screening_prompt_pack_endpoint_first`
  - the intended LLM role remains local question-sharpness screening, not impact or importance prediction
- async execution path now exists for the prepared LLM screens:
  - `scripts/run_llm_screening_async.py`
  - this uses direct high-concurrency `/v1/responses` calls rather than the Batch API
- first within-field LLM v3 screening evidence now exists:
  - note: `next_steps/llm_within_field_v3_findings.md`
  - working operational shape is:
    - `E` as a weak veto only
    - repeated `H` pairwise within-field reranking on survivors
    - `G` as a secondary scalar diagnostic
  - repeated `none`-reasoning pairwise screening is highly stable
  - `low` reasoning is not currently acceptable for the pairwise structured-output prompt because parse reliability drops too much
- paper-facing LLM rule note now exists:
  - `next_steps/llm_operational_rule_and_appendix_table.md`
  - manual inspection should be described as prompt-development and audit support, not as the main ranking rule
- first browse-ready within-field LLM package now exists:
  - `outputs/paper/111_within_field_llm_browse_package`
  - this is the current working within-field product
  - it should be treated as a browse object, not as the historical benchmark
- first global top-250 LLM screening pass now exists:
  - note: `next_steps/global_top250_llm_screening_note.md`
  - `E/G/H` transfers to the global candidate universe
  - but the clean current output is still bucket-local cleanup, not yet a final
    single global LLM-ranked product

## Still open

- whether the current `candidate_subfamily` and `candidate_scope_bucket` names are final paper-facing names or only code-facing names
- whether `parallel_mediator_expansion` should ever become a first-class family
- whether common-driver and common-consequence patterns should remain evidence tags permanently or later become separate tasks
- exact transparent score formula and preset definitions
- whether `quality` should be renamed paper-facing to `candidate_sharpness` or a similar narrower label
- exact paper-worthiness layer objective and whether it should stay a purely surfaced layer or later receive a historical evaluation design
- how to move from the improved but still broad `85` shortlist to a defensible final paper-facing shortlist
- whether and when to run the prepared LLM screening pilot:
  - initial within-field pilot has now been run
  - next open question is not whether to use LLMs at all, but how far to extend the current within-field weak-veto plus pairwise design
- improved candidate generation upstream of the reranker:
  - stronger family assignment
  - better gating of broad anchored `path_to_direct` cases in a way that moves the
    historical candidate pool, not only the current surfaced shortlist
  - richer endpoint-plus-mediator compression
- whether the current broad-anchored gate should remain a shortlist-screening rule or
  later be promoted into the historical candidate-generation layer
- retrieval-budget and evaluation-budget design:
  - pool-size sweep such as `500, 2000, 5000, 10000`
  - multi-`K` evaluation such as `20, 50, 100, 250, 500`
  - field-conditioned top-`K` evaluation
  - reranker depth-usage versus transparent rank, so pool size can be justified by
    what the surfaced top-`100` actually draws from
- current pool-size read from the corrected reranker depth study:
  - `500` is too small
  - `10000` is too large for the current top-100 objective
  - `2000` is now the strongest single challenger to the current `5000` default
  - `5000` still has some support as a medium-run or robustness setting, especially at `h=10`
- current field-conditioned and multi-budget read:
  - the “best pool” depends on the user-facing objective
  - `2000` looks stronger for concentration-sensitive within-field browsing and
    for larger budget ladders such as top-`250` / top-`1000`
  - `5000` still has a real case for the single global exploratory shortlist
  - so no single pool should be frozen as universally best yet
- whether to rename or compress `candidate_family = mediator_expansion` inside the `path_to_direct` surfaced shortlist for paper-facing presentation
- full paper-grade reranker and concentration refresh for `direct_to_path`
  - sampled diagnostics remain encouraging
  - a full non-sampled tuning run is still computationally unresolved and should not be backfilled with old results

## Next implementation order

1. finish the paper/docs sync around the new `path_to_direct` refresh
2. decide whether the surfaced `mediator_expansion` label should stay explicit in the paper or be compressed into a plainer “anchored mechanism question” description
3. either complete or explicitly park the full `direct_to_path` paper-grade reranker refresh
4. run the first proper human-usefulness pack on the refreshed `path_to_direct` shortlist
5. sharpen the paper-worthiness / de-crowding layer again, now focusing on broad anchored progression items rather than only raw theme concentration
6. implement `next_steps/candidate_generation_v3_spec.md`
7. improve transparent retrieval and run the retrieval-budget study
8. decide whether to keep separate pool defaults for:
   - global exploratory shortlist
   - within-field browsing
   - larger budget ladders such as `250` / `1000`
9. decide whether the `85` current frontier is good enough for paper-facing examples or whether a second paper-worthiness pass is required first
10. reopen supply-vs-demand ranking as the next method extension

## Main caution

Do not let the project drift back into:

- ontology changes during method work
- turning every motif into a new top-level family
- letting the transparent model become a disguised trained model
- using LLMs as the main historical benchmark

## Historical benchmark scope

- The current effective-corpus paper passes often use cutoff years `2000, 2005, 2010, 2015`.
- This is a design choice for later-era, compute-heavy passes, not a hard feasibility limit.
- The effective corpus spans `1976–2026`, so earlier five-year cutoffs such as `1990` and `1995` are feasible for the main paper horizons, and `1985` is also feasible as a robustness extension.
- Planned paper move:
  - widen the main historical benchmark schedule from `2000–2015` to at least `1990–2015`
  - treat `1985` as a secondary robustness extension unless early-era noise is too high
- Planned paper wording:
  - the graph at cutoff `t` uses the full literature through `t-1`
  - there is no hard rolling pre-window cutoff in the main stack
  - older observations are downweighted via recency decay rather than discarded
- Current status:
  - widened current-stack benchmark now run with reported cutoffs `1990–2015` and `1985` warm-up only
  - early cutoffs are both thinner and structurally different
  - later cutoffs surface older, less recent-share-heavy, more stable, and more diverse candidate objects
  - keep the widened benchmark in the paper workflow even if the headline figures still emphasize the later era

## Timing-taxonomy follow-up

- Keep a formal follow-up note on a timing taxonomy for surfaced ideas:
  - recent-surge
  - enduring-structural
  - revived / rediscovered
  - event-driven transient
- This should stay out of the main pipeline for now.
- Use it later either as:
  - an appendix interpretation of the widened benchmark, or
  - a next method extension once the widened benchmark is stable.
- Relevant note:
  - `next_steps/hot_vs_enduring_idea_taxonomy_note.md`

## Appendix LLM usefulness sweep

- A full widened historical appendix usefulness sweep has now been run on:
  - `17` historical exercises
  - top `250`
  - `3` arms: adopted, transparent, pref-attach
- Current read:
  - pooled over the full grid, adopted > transparent > pref-attach
  - but in the early era alone, transparent can look slightly cleaner than adopted
  - in the later era, adopted clearly beats transparent
- Keep this as appendix robustness evidence, not the main historical benchmark.
