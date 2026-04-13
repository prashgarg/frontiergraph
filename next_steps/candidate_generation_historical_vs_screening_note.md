# Candidate Generation vs Current-Frontier Screening

Date: 2026-04-10

## Purpose

This note records an important distinction that became clear in the first
candidate-generation v3 threshold sweep.

The current broad-anchored gate looks promising as a **current-frontier screening**
rule, but it is not yet established as a **historically validated
candidate-generation improvement**.

That distinction matters for both method design and paper claims.

## 1. The two objects are different

### A. Historical candidate-generation improvement

This is the stronger claim.

It means that changing the generator itself improves the historically evaluated
candidate universe. A successful historical generator change should:

- change the candidate pool in vintage-respecting backtests
- improve candidate positive rate or retrieval quality at fixed budgets
- preserve or improve downstream ranking performance
- do so using generic rules rather than concept-specific exceptions

This is the right standard for claims about the **method**.

### B. Current-frontier screening

This is a weaker but still useful object.

It means that, given the current surfaced frontier, we apply a generic screening
rule to remove candidates that are too broad, weakly compressed, or too generic to
read well as research questions.

A successful screening rule should:

- improve the current surfaced shortlist
- reduce broad or weakly compressed items
- reduce concentration or repetition
- remain generic and interpretable

This is the right standard for claims about the **current surfaced shortlist**.

## 2. What the narrow threshold sweep found

Using:

- `outputs/paper/84_surface_layer_backtest_path_to_direct/historical_feature_panel.parquet`
- `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv`
- `outputs/paper/87_candidate_generation_v3_threshold_sweep`

the narrow sweep found:

- on the cached historical panel, the broad-anchored gate had effectively no bite
- on the current frontier, the same gate did have bite and meaningfully improved
  top-100 concentration and compression diagnostics

So the present evidence is asymmetric:

- **historical candidate-generation claim:** not established
- **current-frontier screening claim:** supported

This is a useful result because it tells us not to overclaim.

## 3. How to interpret the current thresholds

Current defaults such as:

- `anchored_broad_start_pct = 0.80`
- `anchored_min_resolution_score = 0.18`
- `anchored_min_mediator_specificity_score = 0.25`
- `anchored_min_path_support_raw = 2.0`

should therefore be treated as:

- generic provisional screening thresholds
- motivated by observed current-frontier distributions
- useful for current-shortlist cleanup

They should **not** yet be presented as:

- historically calibrated structural thresholds
- final paper-grade generator settings
- evidence that candidate generation itself has been improved

## 4. What we can safely say now

We can safely say:

- the current surfaced shortlist has a recurring failure mode:
  - broad anchored progression objects
  - weak compression
  - overly generic mediator framing
- generic rule-based screening can reduce that failure mode on the current frontier
- the compression fields are programmable and reproducible, not hand-coded concept
  exceptions and not LLM judgment

We should not yet say:

- the candidate generator has been historically improved
- the new thresholds are tuned and validated as stable method parameters

## 5. Operational policy going forward

Until stronger evidence exists, we should keep the following distinction:

### Historical method layer

Allowed claims:

- reranker improvements validated on vintage-respecting backtests
- concentration and surface-layer effects validated on historical panels
- candidate-generation changes only when they move the historical panel in a
  measurable way

### Current-frontier layer

Allowed claims:

- generic screening for readability and question sharpness
- post-frontier compression and cleanup
- shortlist shaping for paper-facing examples

This keeps the paper honest while still letting us improve the live shortlist.

## 6. Promotion rule: when can a screening rule become a generator rule?

A current-frontier screening rule can be promoted into the historical
candidate-generation layer only if it passes all three tests:

1. **historical bite**
   - materially changes the historical candidate pool
2. **historical discipline**
   - does not reduce retrieval recall too much at fixed budgets
   - ideally improves candidate positive rate or downstream ranking
3. **robustness**
   - nearby thresholds show similar behavior
   - no need for named-concept exceptions

Until then, it remains a screening rule.

## 7. Next pass implied by this distinction

The next pass should therefore be split cleanly:

1. **current-frontier screening track**
   - keep the compression fields
   - improve current-shortlist screening and paper-worthiness logic
   - evaluate on current top-100, top-250, and current human judgments

2. **historical candidate-generation track**
   - redesign generator-time rules that are more likely to move the historical pool
   - test retrieval budgets `500, 2000, 5000, 10000`
   - test candidate positive rate and multi-`K` retrieval metrics

This avoids forcing one piece of evidence to do both jobs.

## 8. Paper implication

For the paper, the safe position is:

- keep the current threshold logic out of the main historical method claim
- if used at all in the paper package, describe it as a current-frontier screening
  or shortlist-shaping rule
- do not write as though candidate generation has already been historically
  recalibrated

That is the defensible line.
