# Paper Refresh Checklist

Date: 2026-04-11

Rule:
- no legacy result stays in the paper just because it is already there
- each item must be one of:
  - `LOCKED`: already current enough, keep as is
  - `RERUN`: keep in paper, but recompute on the current method stack
  - `REMOVE`: cut from the paper if we do not rerun it

This checklist is the execution list for the full-paper refresh.

## Locked now

- [x] Main benchmark framing in [research_allocation_paper.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex)
  - main schedule is `1990--2015`
  - early-vs-late regime point is explicit

- [x] Strict shortlist benchmark text
  - transparent beats preferential attachment at the strict shortlist margin

- [x] Main benchmark figure
  - [main_benchmark_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/main_benchmark_refreshed.png)

- [x] Main benchmark summary table
  - current main-text values are aligned with the refreshed benchmark

- [x] Human usefulness appendix framing
  - cautious wording
  - appendix placement

- [x] Appendix LLM usefulness framing
  - supplementary only
  - current-usefulness rather than historical forecasting

- [x] Corpus / extraction / ontology description
  - stable under the current method refresh

- [x] Credibility audit tables
  - keep as is unless later corpus definitions change

- [x] Corpus growth figure
  - [corpus_growth.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/50_extra_figures/corpus_growth.png)
  - built directly from the current corpus file
  - keep as is

## Rerun if kept in paper

### Highest priority

- [x] Appendix expanded reranker benchmark table
  - location: [research_allocation_paper.tex#L1044](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1044)
  - resolved on 2026-04-11
  - appendix table now matches the current `1990--2015` benchmark winners:
    - `h=5`: `glm_logit + family_aware_boundary_gap`
    - `h=10`: `pairwise_logit + family_aware_composition`
    - `h=15`: `glm_logit + quality`
  - PDF rebuild succeeded after the patch

- [x] Early-vs-late appendix regime table or figure
  - reason: make the regime difference numerically visible rather than only verbal
  - resolved on 2026-04-11
  - added appendix Table~`early-late-regime` in the live manuscript
  - uses the current `1990--2015` benchmark and the horizon-specific adopted winner at each main horizon
  - paper bundle created at [132_early_late_appendix_display](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/132_early_late_appendix_display)

### Main-text figures currently on legacy runs

- [x] Attention-allocation frontier
  - figure used: [research_allocation_paper.tex#L660](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L660)
  - resolved on 2026-04-11
  - refreshed on the current stack using [134_attention_allocation_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/134_attention_allocation_refresh)
  - paper figure now uses [attention_allocation_frontier_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/attention_allocation_frontier_refreshed.png)
  - refreshed interpretation: the transparent score leads at \(K=50\) and \(K=100\), but its edge fades by \(K=500\) and largely disappears by \(K=1000\)

- [x] Precision-at-\(K\)
  - figure used: [research_allocation_paper.tex#L668](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L668)
  - resolved on 2026-04-11
  - refreshed on the current stack using [135_precision_at_k_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/135_precision_at_k_refresh)
  - paper figure now uses [precision_at_k_curves_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/precision_at_k_curves_refreshed.png)
  - refreshed interpretation: among simple scores, the transparent graph score is strongest at the very tight shortlist margin, co-occurrence leads at intermediate shortlist sizes, and the simple-score family largely converges at broad \(K\)

- [x] Value-weighted benchmark
  - figure used: [research_allocation_paper.tex#L684](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L684)
  - resolved on 2026-04-11
  - refreshed on the current stack using [136_value_weighted_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/136_value_weighted_refresh)
  - paper figure now uses [impact_weighted_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/impact_weighted_main_refreshed.png)
  - refreshed interpretation: weighting by later reuse strengthens the strict-shortlist case for the transparent score, but popularity reasserts itself once the shortlist becomes very broad

- [x] Pooled frontier
  - figure used: [research_allocation_paper.tex#L700](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L700)
  - resolved on 2026-04-11
  - refreshed on the current benchmark panel using [137_benchmark_panel_heterogeneity_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/137_benchmark_panel_heterogeneity_refresh)
  - paper figure now uses [pooled_frontier_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/pooled_frontier_main_refreshed.png)
  - refreshed interpretation: the transparent score looks materially stronger once the benchmark is evaluated over broader reading budgets, but its edge still fades as the shortlist becomes very broad

- [x] Method heterogeneity
  - figure used: [research_allocation_paper.tex#L710](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L710)
  - resolved on 2026-04-11
  - refreshed on the current benchmark panel using [137_benchmark_panel_heterogeneity_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/137_benchmark_panel_heterogeneity_refresh)
  - paper figure now uses [method_theory_forest_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/method_theory_forest_main_refreshed.png)
  - refreshed interpretation: adjacent journals are more favorable than the core on the broader frontier view, and design-based causal slices are much more favorable terrain than panel- or time-series-heavy slices, which sit near zero at the longer horizons

- [x] Path development
  - figures used:
    - [research_allocation_paper.tex#L733](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L733)
    - [research_allocation_paper.tex#L745](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L745)
  - resolved on 2026-04-11
  - refreshed on the current stack using [138_path_evolution_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/138_path_evolution_refresh)
  - paper figures now use:
    - [path_evolution_comparison_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/path_evolution_comparison_refreshed.png)
    - [path_transition_mix_by_source_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/path_transition_mix_by_source_refreshed.png)
  - refreshed interpretation: direct-to-path still dominates path-to-direct at every horizon and period, but the magnitudes should be stated as transition rates rather than exaggerated count ratios; adjacent journals are relatively more path-closure heavy than the core, but direct-to-path remains larger in both tiers

- [x] Temporal generalization
  - figure used: [research_allocation_paper.tex#L799](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L799)
  - appendix table used: [research_allocation_paper.tex#L1257](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1257)
  - resolved on 2026-04-11
  - refreshed on the current stack using [133_temporal_generalization_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/133_temporal_generalization_refresh)
  - main-text figure now uses [temporal_generalization_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/temporal_generalization_refreshed.png)
  - appendix table now reports absolute \(P@100\) gaps rather than unstable percentage lifts

### Appendix diagnostics we will also refresh if retained

- [x] Grouped SHAP appendix diagnostics
  - figures:
    - [research_allocation_paper.tex#L1182](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1182)
    - [research_allocation_paper.tex#L1192](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1192)
    - [research_allocation_paper.tex#L1204](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1204)
    - [research_allocation_paper.tex#L1212](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1212)
    - [research_allocation_paper.tex#L1220](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1220)
  - refreshed on 2026-04-11 using:
    - [140_grouped_shap_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/140_grouped_shap_refresh)
    - [141_shap_robustness_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/141_shap_robustness_refresh)
  - paper now uses refreshed figure assets in [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper)

- [x] Single-feature importance appendix diagnostics
  - figure/table:
    - [research_allocation_paper.tex#L1138](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1138)
    - [research_allocation_paper.tex#L1168](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1168)
  - refreshed on 2026-04-11 using:
    - [139_single_feature_importance_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/139_single_feature_importance_refresh)
  - paper now uses refreshed figure assets in [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper)

- [x] Sparse/dense regime split appendix diagnostics
  - resolved on 2026-04-11
  - refreshed using [142_regime_split_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/142_regime_split_refresh)
  - paper now uses [regime_split_delta_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/142_regime_split_refresh/regime_split_delta_refreshed.png)
  - refreshed interpretation: the transparent score helps more in dense than sparse local neighborhoods, and its relative edge is larger in lower-FWCI than in high-FWCI slices

- [x] All-horizons auxiliary benchmark figure
  - resolved on 2026-04-11
  - refreshed using [143_auxiliary_horizon_appendix_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/143_auxiliary_horizon_appendix_refresh)
  - paper now uses [auxiliary_horizon_comparison_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/143_auxiliary_horizon_appendix_refresh/auxiliary_horizon_comparison_refreshed.png)
  - refreshed interpretation: as the horizon lengthens, the transparent score's top-100 hit rate rises, but top-100 recall remains tiny and the pool recall ceiling remains much larger than the visible shortlist yield

- [x] Time heatmap / funding interaction appendix figures
  - resolved on 2026-04-11
  - refreshed using [137_benchmark_panel_heterogeneity_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/137_benchmark_panel_heterogeneity_refresh)
  - paper now uses refreshed appendix assets rather than the old heterogeneity atlas

## Internal-note cleanup

- [x] Refresh [current_locked_vs_open_decisions.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/current_locked_vs_open_decisions.md) so it no longer carries superseded reranker winners and metric values

- [x] Refresh [method_v2_design.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/method_v2_design.md) so it no longer mixes earlier and later paper-grade refresh states

- [x] Refresh [method_v2_path_to_direct_refresh_status.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/method_v2_path_to_direct_refresh_status.md) or stop using it

## Process hardening

- [x] Replace the broad `\\graphicspath` search over legacy bundles in [research_allocation_paper.tex#L28](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L28)
  - resolved on 2026-04-11
  - the manuscript now resolves figures from the paper directory itself
  - the two remaining carryover assets needed for compilation, `real_neighborhood.png` and `corpus_growth.png`, were copied into [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper)

## Working order

1. Substantive refresh complete for all retained analysis objects.
2. Remaining work is manuscript polish only:
   - line edits and prose compression where useful
   - low-value overfull-box cleanup, mostly in appendix prompt/schema material
   - optional font-package cleanup if the draft is prepared for circulation outside the current toolchain
