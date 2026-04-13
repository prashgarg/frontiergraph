# Full Paper Refresh Audit

Date: 2026-04-11

Question:
- Has the paper been fully refreshed to the current method stack?

Short answer:
- As of the final 2026-04-11 refresh pass, yes for retained analysis objects.
- The substantive paper now runs on the current stack throughout the retained main-text and appendix analysis.
- What remains is polish:
  - appendix-heavy overfull-box cleanup
  - repeated Libertinus/font warnings
  - optional prose compression

This note now classifies the manuscript into:
- refreshed and internally coherent
- refreshed but still polish-needing
- removed from scope unless rerun later

## 1. Refreshed and internally coherent

### Main benchmark framing
Status: refreshed

The paper now consistently treats `1990--2015` as the main benchmark schedule rather than a side robustness pass.

Key places:
- [research_allocation_paper.tex#L85](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L85)
- [research_allocation_paper.tex#L586](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L586)
- [research_allocation_paper.tex#L627](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L627)

The early-vs-late interpretation is also now explicit in the main text:
- early years are thinner and structurally different
- not merely dropped for noise reasons

### Strict transparent benchmark result
Status: refreshed

The main strict-shortlist comparison now reflects the refreshed benchmark numbers:
- transparent beats preferential attachment at the strict shortlist margin
- the prose and the summary table agree on the benchmark object and main horizons

Key places:
- [research_allocation_paper.tex#L581](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L581)
- [research_allocation_paper.tex#L627](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L627)

### Main benchmark figure
Status: refreshed

The old main benchmark figure has been replaced with:
- [main_benchmark_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/main_benchmark_refreshed.png)

and is now wired into:
- [research_allocation_paper.tex#L589](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L589)

This is currently the cleanest fully refreshed visual in the manuscript.

### Human and LLM usefulness discussion
Status: refreshed in wording and placement

The small-scale current-usefulness material has been pushed mostly into the appendix and is now described cautiously rather than as a main result.

Key places:
- [research_allocation_paper.tex#L805](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L805)
- [research_allocation_paper.tex#L1450](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1450)

This part is now aligned with the actual evidence:
- human result is mixed
- appendix LLM result is supplementary and era-sensitive

## 2. Refreshed but still polish-needing

These sections are substantively refreshed, but still have some layout or exposition cleanup potential.

### Main-text attention frontier
Status: refreshed on 2026-04-11

Section:
- [research_allocation_paper.tex#L650](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L650)

Figure:
- [research_allocation_paper.tex#L660](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L660)
- asset:
  - [paper/attention_allocation_frontier_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/attention_allocation_frontier_refreshed.png)

Interpretation:
- this is now a refreshed current-benchmark figure
- the paper's interpretation has changed materially: the transparent score leads at tighter shortlists, but that edge fades at broader attention budgets

### Main-text precision-at-K figure
Status: refreshed on 2026-04-11

Figure:
- [research_allocation_paper.tex#L668](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L668)
- asset:
  - [paper/precision_at_k_curves_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/precision_at_k_curves_refreshed.png)

Interpretation:
- this is now a refreshed current-benchmark figure
- the old caption no longer holds on the new stack
- the refreshed result splits the simple-score family into regimes:
  - transparent graph score is strongest at the first reading tranche
  - co-occurrence is slightly stronger at intermediate shortlist sizes
  - by broad \(K\), the simple scores largely converge
- this strengthens the paper's budget interpretation and clarifies why the learned reranker still matters

### Main-text value-weighted section
Status: refreshed on 2026-04-11

Section:
- [research_allocation_paper.tex#L674](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L674)

Figure:
- [research_allocation_paper.tex#L684](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L684)
- asset:
  - [paper/impact_weighted_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/impact_weighted_main_refreshed.png)

Interpretation:
- this is now a refreshed current-benchmark figure
- the refreshed weighted result is more favorable to the transparent graph score than the older draft
- weighted MRR favors the transparent score at all three main horizons
- but by \(K=1000\), preferential attachment is again slightly ahead on weighted recall
- this reinforces the paper's budget-dependent interpretation rather than overturning it

### Main-text heterogeneity and pooled-frontier sections
Status: refreshed on 2026-04-11

Figures:
- [research_allocation_paper.tex#L700](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L700)
- [research_allocation_paper.tex#L710](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L710)

Refreshed assets:
- [paper/pooled_frontier_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/pooled_frontier_main_refreshed.png)
- [paper/method_theory_forest_main_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/method_theory_forest_main_refreshed.png)

Interpretation:
- these sections now sit on the refreshed historical benchmark panel itself rather than the older mixed-kind heterogeneity atlas
- the substantive message changed: broader shortlist views are more favorable to the graph score than the strict top-100 headline, adjacent journals are more favorable than the core on those broader frontiers, and design-based slices are much more favorable terrain than panel- or time-series-heavy slices

### Main-text path-development section
Status: refreshed on 2026-04-11

Figures:
- [research_allocation_paper.tex#L733](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L733)
- [research_allocation_paper.tex#L745](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L745)

Refreshed assets:
- [paper/path_evolution_comparison_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/path_evolution_comparison_refreshed.png)
- [paper/path_transition_mix_by_source_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/path_transition_mix_by_source_refreshed.png)

Interpretation:
- the qualitative result survives on the current stack: direct-to-path dominates path-to-direct at every horizon and cutoff-period block
- the old magnitudes were too strong; the refreshed paper now states the result in transition rates rather than dramatic count ratios
- adjacent journals remain relatively more path-closure heavy than the core, but direct-to-path remains larger in both tiers

### Main-text temporal generalization
Status: refreshed on 2026-04-11

Figure:
- [research_allocation_paper.tex#L799](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L799)
- asset:
  - [paper/temporal_generalization_refreshed.png](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/temporal_generalization_refreshed.png)

Interpretation:
- this is now a refreshed core-benchmark object
- the paper now reports absolute \(P@100\) gaps rather than unstable percentage lifts

## 3. Removed as an active refresh concern

### Appendix expanded reranker benchmark table
Status: refreshed on 2026-04-11

Table:
- [research_allocation_paper.tex#L1044](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L1044)

Current state:
- aligned with the current main benchmark values and model winners in the main text
- PDF rebuild succeeded after the patch

Interpretation:
- this had been the single most serious remaining manuscript inconsistency
- it is now closed

### Internal design notes are now updated to the latest winner stack
Status: refreshed on 2026-04-11

Examples:
- [current_locked_vs_open_decisions.md#L57](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/current_locked_vs_open_decisions.md#L57)
- [method_v2_design.md#L307](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/method_v2_design.md#L307)
- [method_v2_path_to_direct_refresh_status.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/method_v2_path_to_direct_refresh_status.md)

Current state:
- `current_locked_vs_open_decisions.md` and `method_v2_design.md` now match the current paper-consistent winner stack
- `method_v2_path_to_direct_refresh_status.md` is now explicitly marked superseded and points readers back to the current notes

Interpretation:
- note-level backsliding risk is materially lower than before

### Graphics path design was a consistency risk and is now closed
Status: refreshed on 2026-04-11

At:
- [research_allocation_paper.tex#L28](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex#L28)

the broad legacy `\graphicspath` has been removed.

Interpretation:
- silent reuse of older figure assets is no longer the active risk
- the paper now compiles from paper-owned figure assets

## 4. Section-by-section verdict

### Main text

- Introduction: mostly refreshed
- Related literature: unaffected by benchmark refresh
- Corpus / extraction / normalization: stable and usable
- Benchmark construction and evaluation design: refreshed
- Strict shortlist benchmark: refreshed
- Main benchmark figure/table: refreshed
- Attention frontier: refreshed
- Precision-at-\(K\): refreshed
- Value-weighted benchmark: refreshed
- Reranker headline prose/table: refreshed and internally aligned
- Attention frontier: partially refreshed
- Value-weighted section: partially refreshed
- Heterogeneity section: partially refreshed
- Path-development section: partially refreshed / likely legacy
- Discussion/conclusion: refreshed enough, with validation now placed mostly in the appendix

### Appendix

- Extraction appendix: stable
- Node normalization appendix: stable
- Strict continuity benchmark tables: unclear provenance but internally readable; lower priority than the reranker table
- Expanded reranker benchmark table: refreshed
- Feature importance / SHAP appendix: older diagnostics and should be rerun if retained
- Temporal generalization appendix: refreshed
- Heterogeneity appendix: older diagnostics and should be rerun if retained
- Current-usefulness appendix: refreshed

## 5. Bottom-line answer

Yes for retained substantive analysis. The full paper has now been refreshed to the latest method stack for the results it still keeps in scope.

What is true now:
- the benchmark story is on the right object throughout
- retained main-text and appendix analysis are refreshed
- internal notes have been updated to the current winner stack
- the paper compiles from a self-contained figure directory

What is still not fully polished:
- some appendix-heavy sections still generate overfull-box warnings
- the Libertinus/font warnings remain
- the prose can still be compressed in places before circulation

## 6. Recommended refresh order

1. Treat the remaining work as manuscript polish, not analytical refresh:
   - trim low-value appendix overfull boxes
   - optionally simplify some long schema/prompt displays
   - do a final compression pass before circulation
   - regime-split tables and broader-horizon comparison
2. Refresh the internal notes so future edits do not pull old numbers back in.
3. Only then do the compression / line-edit / layout pass.
