# Option C Dual-Family Parity Map

Date: 2026-04-12

This note maps the next method phase under the design choice to support both headline
family objects side by side:

- `path-to-direct`
- `direct-to-path`

The immediate goal is not to decide which family is rhetorically primary. The immediate
goal is to bring `direct-to-path` to the same empirical standard as the current
paper-grade `path-to-direct` stack, then compare the two cleanly.

This note also separates a third, more speculative object:

- `something-from-nothing`

That third object is intellectually real, but it should not be folded into the first
dual-family parity pass.

## 1. The three objects

### A. `path-to-direct`

- support path exists at `t-1`
- direct relation is missing at `t-1`
- later direct relation appears

This is the current paper-grade historical object.

### B. `direct-to-path`

- direct relation exists at `t-1`
- supporting path is missing at `t-1`
- later supporting path appears

This is already implemented in the code, but not refreshed to paper-grade parity.

### C. `something-from-nothing`

This is the wild but serious third object. It covers cases where the later question is
not just a missing direct leg or a later mechanism around an existing direct claim.
Instead, the later question may involve:

- a new mediator concept not previously present in the local graph
- a bridge across graph regions that were previously far apart
- a later relation around a node that had little or no prior local support

This object matters substantively because some of the most creative or interdisciplinary
research questions look like this. But it is much harder to benchmark cleanly.

Why it should not enter the first parity pass:

- if a node is genuinely absent at `t-1`, it cannot be ranked as a candidate endpoint in
  the same way
- if the event is a broad cross-region bridge rather than a path closure or path
  thickening event, the historical target changes again
- it would confound family choice with a different graph object

So the right sequence is:

1. dual-family parity for `path-to-direct` and `direct-to-path`
2. only then a separate extension for more open-ended or distant graph emergence

## 2. What is already implemented versus what is not

Implemented in code:

- both family modes exist in `src/research_allocation_v2.py`
- side-by-side family comparison scaffold exists in
  `scripts/compare_method_v2_families.py`

Not yet at paper-grade parity:

- full non-sampled reranker retune for `direct-to-path`
- concentration comparison for `direct-to-path`
- current frontier build for `direct-to-path`
- paper-facing figure/table packages on the effective corpus for `direct-to-path`

So the parity job is real method work, not a wording pass.

## 3. Must rerun

These are the outputs that genuinely need a fresh `direct-to-path` run if the paper is
going to support both families side by side.

### A. Historical candidate panel and benchmark summary

Purpose:

- establish the candidate universe, realized-positive set, and strict shortlist
  comparison for `direct-to-path`

Required outputs:

- candidate counts by cutoff and horizon
- realized-positive counts in-universe
- strict shortlist metrics against:
  - preferential attachment
  - transparent graph score
  - co-occurrence, if retained in the comparison set

Relevant scripts / logic:

- `src/backtest.py`
- `scripts/run_effective_benchmark_widened.py`
- `scripts/compare_method_v2_families.py`

### B. Learned reranker tuning and winner selection

Purpose:

- bring `direct-to-path` to the same reranker standard as the current
  `path-to-direct` stack

Required outputs:

- sampled tuning pass if needed for narrowing the grid
- full non-sampled reranker retune
- horizon-specific winner selection
- benchmark table in paper-facing form

Relevant scripts / logic:

- `scripts/run_learned_reranker_tuning.py`
- `src/analysis/learned_reranker.py`
- `src/analysis/constrained_reranker_search.py`
- `src/analysis/targeted_model_search.py`

### C. Concentration and surfacing layer

Purpose:

- determine whether the `direct-to-path` surfaced shortlist is readable and diverse
  enough for paper-facing examples

Required outputs:

- diversification-only vs sink-plus-diversification comparison
- adopted concentration layer by horizon
- current frontier build

Relevant scripts / logic:

- current `path-to-direct` notes and scripts around the `77/78/83/84/85` output chain
- `scripts/build_current_reranked_frontier.py`

### D. Reading-budget / frontier evaluation

Purpose:

- compare how both families behave as the shortlist expands

Required outputs:

- `K`-frontier comparison
- pooled-frontier or shortlist-share comparison
- possibly the simple-score-at-`K` figure if kept in the main text

Relevant scripts / logic:

- `scripts/run_attention_allocation_refresh.py`
- `scripts/run_retrieval_budget_eval.py`
- `scripts/run_reranker_pool_depth_eval.py`

### E. Heterogeneity

Purpose:

- see whether the same subgroup story holds in both families

Required outputs:

- method / journal-tier heterogeneity
- regime split if retained
- funding interaction if retained

Relevant scripts / logic:

- `src/analysis/field_heterogeneity.py`
- `scripts/run_field_conditioned_budget_eval.py`

### F. Current surfaced examples

Purpose:

- assemble readable examples for both objects

Required outputs:

- curated top examples for `path-to-direct`
- curated top examples for `direct-to-path`
- ideally paired examples showing how the two objects differ substantively

### G. Temporal generalization

Purpose:

- confirm that the `direct-to-path` reranker generalizes forward rather than only
  reflecting in-sample tuning

Relevant scripts / logic:

- `scripts/run_temporal_generalization_refresh.py`

### H. Human/usefulness packs

Purpose:

- if the paper later wants to compare the surfaced question quality of the two families,
  the validation pack should be run on both

This should not be first. It should wait until the `direct-to-path` surfaced shortlist is
paper-stable.

## 4. Likely reusable

These parts of the current paper can probably survive with light rewriting rather than a
new empirical run.

### A. Corpus, extraction, and ontology sections

These are family-agnostic:

- corpus and sample
- paper-local extraction
- normalization pipeline
- credibility audit tables

They may need wording changes, but not new computation.

### B. Early method figures

The early figures can still work if we describe both family objects explicitly:

- one paper to one local graph
- local graphs to shared graph candidate
- benchmark anchor versus surfaced question

What needs changing is the family explanation around them, not the extraction logic.

### C. Graph-evolution appendix

The proposed appendix figure on graph evolution is reusable across families because it
describes the corpus graph itself, not one benchmark family.

Recommended panels:

- number of concepts over time
- number of support edges over time
- mean degree and 90th percentile degree over time
- giant connected-component share over time
- sampled shortest-path distribution over time
- clustering / transitivity over time

If path-length exercises are later added, one more panel should show the share of
candidates supported at path lengths 2, 3, 4, and 5.

### D. Literature-positioning sections

These can be reused but will need reframing:

- the paper is about question choice under scarce attention
- one historical object is direct closure
- another is mechanism thickening
- the graph is doing screening, not open-world idea generation

## 5. Main-text figures and tables that become paired

These are the objects that should eventually be shown side by side, not just described
twice in text.

### Core paired objects

1. Main benchmark figure
   - current: `fig:main-benchmark`
   - future: side-by-side or faceted by family

2. Main benchmark summary table
   - current: `tab:benchmark-summary-main`
   - future: rows or panels for both families

3. Attention-budget frontier
   - current: `fig:attention-frontier-main`
   - future: family comparison

4. Simple-score dependence on shortlist size
   - current: `fig:precision-at-k`
   - future: either paired or family-conditioned appendix if too crowded

5. Value-weighted rerun
   - current: `fig:impact-weighted-main`
   - future: paired only if substantively different; otherwise likely appendix

6. Broader-shortlist frontier
   - current: `fig:pooled-frontier`
   - future: family comparison

7. Main heterogeneity figure
   - current: `fig:method-forest`
   - future: family comparison

8. Path-development section
   - current: `fig:path-evolution` and `fig:path-source-mix`
   - future: this section becomes central rather than supplemental because it will now
     compare the two headline objects directly

9. Curated examples table
   - current: `tab:curated-examples-main`
   - future: paired examples by family

### Likely main-text structure under Option C

The cleanest main-text order is probably:

1. strict shortlist comparison for both families
2. reranker comparison for both families
3. attention-budget comparison for both families
4. where each family helps more
5. paired surfaced examples
6. path development as the section that interprets why the two objects differ

## 6. Appendix pieces that should wait until after family comparison

These should not be expanded now, because their interpretation depends on what the
dual-family comparison actually shows.

### A. Path-length appendix exercise

Wait until after family parity.

Reason:

- if we vary family and path length at the same time, the result will be hard to read
- first establish dual-family results at the current path setting
- then test `max_len = 2, 3, 4, maybe 5`

### B. Deep reranker interpretation diagnostics

Items like:

- grouped SHAP
- grouped coefficients
- VIF comparisons
- single-feature importance

should wait until we know whether:

- both families merit full reranker interpretation
- one family is clearly main-text and the other appendix

These diagnostics are expensive in paper space and should follow the substantive family
decision, not lead it.

### C. Expanded usefulness packs

Human and LLM usefulness packs should wait until:

- `direct-to-path` has a paper-stable surfaced shortlist
- we know whether usefulness is being compared within family, across family, or both

### D. Large current-frontier browse expansions

Do not build large browse products yet. The paper needs the historical family comparison
first.

## 7. Practical sequencing

Recommended order:

1. bring `direct-to-path` to paper-grade parity at the current path setting
2. compare the two families side by side on the main empirical objects
3. decide what moves to the main text versus appendix
4. only then run the path-length appendix exercise
5. only after that revisit the more open-ended `something-from-nothing` object

## 8. Current recommendation

The correct next phase is:

- dual-family paper under Option C
- current path setting held fixed
- family comparison first
- path-length variation second
- more open-ended graph-emergence objects third

That sequence keeps the paper disciplined while still moving it toward the economist-facing
object that motivated the project in the first place.
