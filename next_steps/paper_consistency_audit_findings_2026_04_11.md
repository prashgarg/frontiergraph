# Paper Consistency Audit Findings

Date: 2026-04-11

Scope:
- live manuscript: [research_allocation_paper.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex)
- refreshed main benchmark figure: [main_benchmark_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/main_benchmark_refreshed.png)
- refreshed benchmark output bundle: [123_effective_benchmark_widened_1990_2015](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/123_effective_benchmark_widened_1990_2015)

## Findings

### 1. Resolved on 2026-04-11: appendix reranker table now matches the refreshed main benchmark
Severity: closed

The main text and main summary table use the refreshed benchmark numbers:
- [research_allocation_paper.tex#L604](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L604)
- [research_allocation_paper.tex#L627](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L627)

The appendix table at:
- [research_allocation_paper.tex#L1044](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1044)

now reports the same horizon-specific winners and headline metrics as the refreshed main benchmark:
- `h=5`: `0.105 / 0.1376 / 0.0133`
- `h=10`: `0.207 / 0.1391 / 0.0103`
- `h=15`: `0.264 / 0.1541 / 0.0116`

Winning model families are now aligned across main text and appendix:
- `h=5`: `glm_logit + family_aware_boundary_gap`
- `h=10`: `pairwise_logit + family_aware_composition`
- `h=15`: `glm_logit + quality`

Interpretation:
- this had been the strongest remaining internal inconsistency in the draft
- it is now closed

Recommendation:
- keep the table
- move to the next open consistency task: refresh the remaining legacy-sourced result sections

### 2. Resolved on 2026-04-11: early-vs-late regime difference is now numerically visible in the appendix
Severity: closed

The main text now points directly to:
- [research_allocation_paper.tex#L579](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L579)

and the appendix table itself is at:
- [research_allocation_paper.tex#L1070](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1070)

The display is also written out to:
- [132_early_late_appendix_display](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/132_early_late_appendix_display)

It reports, by horizon and era:
- number of valid cutoff cells
- mean realized positives in the evaluation cell
- Recall@100 for the horizon-specific adopted winner
- mean support age
- mean endpoint recent share

Interpretation:
- the regime distinction is no longer only verbal
- readers can now see directly that early cells are much thinner and much younger than late cells
- at `h=15`, the later era is structurally thicker even though winner Recall@100 is slightly lower, which is exactly why this needed to be shown rather than implied

### 3. Resolved on 2026-04-11: the manuscript no longer relies on broad legacy `\\graphicspath` resolution
Severity: closed

The broad legacy asset search has been removed from:
- [research_allocation_paper.tex#L28](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L28)

The manuscript now resolves figures from the paper directory itself. The two remaining older-but-still-valid assets needed for compilation:
- [real_neighborhood.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/real_neighborhood.png)
- [corpus_growth.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/corpus_growth.png)

were copied into [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper), so the draft is now self-contained.

Interpretation:
- silent reuse of old figure bundles is no longer the active risk
- the remaining issues are layout warnings, not stale figure sourcing

### 4. Resolved on 2026-04-11: retained appendix diagnostics are now refreshed
Severity: closed

Refreshed on the current benchmark stack:
- single-feature importance:
  - [139_single_feature_importance_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/139_single_feature_importance_refresh)
- grouped family decomposition and grouped SHAP robustness:
  - [140_grouped_shap_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/140_grouped_shap_refresh)
  - [141_shap_robustness_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/141_shap_robustness_refresh)

Also refreshed on the current stack:
- regime split:
  - [142_regime_split_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/142_regime_split_refresh)
- auxiliary horizon appendix comparison:
  - [143_auxiliary_horizon_appendix_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/143_auxiliary_horizon_appendix_refresh)

Interpretation:
- the retained appendix diagnostics are now on the same refreshed benchmark stack as the main text

### 5. Resolved on 2026-04-11: temporal generalization is now refreshed on the current stack
Severity: closed

The main-text temporal-generalization figure:
- [research_allocation_paper.tex#L796](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L796)

now uses:
- [temporal_generalization_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/temporal_generalization_refreshed.png)

and the appendix table:
- [research_allocation_paper.tex#L1257](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1257)

now reports refreshed values from:
- [133_temporal_generalization_refresh](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/133_temporal_generalization_refresh)

Interpretation:
- the section is now on the same benchmark footing as the rest of the refreshed paper
- the wording has been corrected from unstable percentage-lift language to absolute \(P@100\) gap language
- the main conclusion survives: the reranker generalizes forward to the fully held-out 2010--2015 era

### 6. Resolved on 2026-04-11: appendix horizon language and supporting display now match the current setup
Severity: closed

The appendix now uses the refreshed auxiliary-horizon display rather than the older extension bundle:
- [research_allocation_paper.tex#L1328](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1328)
- [auxiliary_horizon_comparison_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/auxiliary_horizon_comparison_refreshed.png)

### 7. The paper now compiles from a self-contained figure directory, but the draft still has layout noise
Severity: low

Current build:
- [research_allocation_paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.pdf)

Compile succeeds, but there are many overfull boxes and repeated Libertinus warnings. These are not benchmark-consistency errors, but they make the draft feel less controlled than it now is substantively.

Recommendation:
- substantive consistency is now in place
- remaining cleanup is manuscript polish only: overfull-box trimming in appendix-heavy material and optional font-package cleanup

## Recommendations

### Refresh status
1. The retained substantive figures and appendix diagnostics have now been refreshed on the current stack:
   - attention-allocation frontier
   - precision-at-\(K\)
   - impact-weighted frontier
   - pooled frontier
   - method heterogeneity
   - path-evolution figures
   - grouped SHAP
   - single-feature importance
   - sparse/dense regime split
   - auxiliary-horizon appendix benchmark
   - time heatmap / funding heterogeneity figures

### Safe to postpone
2. Overfull-box cleanup and prose compression can now be treated as the remaining polish step.
