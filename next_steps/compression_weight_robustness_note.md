# Compression Weight Robustness Note

Date: 2026-04-10

## Purpose

This note records a narrow robustness check for the compression-confidence weights in:

- `src/analysis/common.py`

Current formula:

- `0.55 * endpoint_resolution`
- `+ 0.30 * mediator_specificity`
- `+ 0.15 * tanh(path_support_raw / 4.0)`

The main question was whether these weights are brittle or whether nearby choices
produce essentially the same weak-compression diagnosis.

## What was tested

Using the current surfaced frontier:

- `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv`

the script:

- `scripts/run_compression_weight_robustness.py`

recomputed compression confidence for five nearby weight sets:

- `baseline = (0.55, 0.30, 0.15)`
- `resolution_heavier = (0.60, 0.25, 0.15)`
- `support_heavier = (0.50, 0.30, 0.20)`
- `mediator_heavier = (0.45, 0.35, 0.20)`
- `balanced = (0.50, 0.25, 0.25)`

and compared them on windows:

- top `100`
- top `250`
- top `500`

for each horizon:

- `h=5`
- `h=10`
- `h=15`

Outputs are in:

- `outputs/paper/88_compression_weight_robustness`

## Main result

The current weights look **reasonably robust**.

Across horizons:

- rank correlation with baseline remains high:
  - about `0.989-0.995` for `resolution_heavier` and `support_heavier`
  - about `0.985-0.986` for `mediator_heavier`
  - about `0.969-0.971` even for the more shifted `balanced` variant
- the low-confidence set overlap with baseline is also strong:
  - about `0.90-0.93` Jaccard for `resolution_heavier`
  - about `0.92-0.94` Jaccard for `support_heavier`
  - about `0.85-0.88` Jaccard for `mediator_heavier`
  - about `0.78-0.80` Jaccard for `balanced`

So the diagnosis is not hanging on one knife-edge parameter choice.

## Interpretation

This supports the following reading of the current formula:

- endpoint resolution should matter most
- mediator specificity should matter second
- path support should matter, but in a bounded way and not dominate

That is exactly what the current baseline weights encode.

The robustness check therefore supports keeping the baseline formula as a
transparent prior rather than aggressively tuning it.

## What this does not show

This sweep does **not** show that the current weights are optimal in any deeper sense.

It also does not show a historical benchmark improvement, because:

- compression confidence is currently an annotation field rather than an active ranking
  term
- this sweep used the current surfaced frontier, not a vintage-respecting historical
  candidate-generation experiment

So the right claim is:

- the current weights are a stable and defensible heuristic

not:

- the current weights have been historically optimized

## Practical implication

For now, the baseline compression weights are good enough to keep.

If compression confidence later becomes:

- an active screening score
- or a learned feature with direct paper-facing consequences

then it would be worth doing a stronger calibration pass against:

- human paper-likeness ratings
- or a more explicit screening objective

Until then, the current formula is best treated as a transparent, robust prior.
