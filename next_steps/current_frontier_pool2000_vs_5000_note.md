# Pool 2000 vs Pool 5000 Current Frontier Compare

Date: 2026-04-10

## Question

After the retrieval-budget and reranker-depth studies suggested that `pool=2000`
is a strong challenger to the current `pool=5000` default for the global
historical top-100 objective, does a `pool=2000` current frontier also look
better than the current `pool=5000` frontier on paper-facing shortlist quality?

This note compares:

- existing current frontier:
  - `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface`
- new matched `pool=2000` rebuild:
  - `outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000`

The comparison keeps the following fixed:

- effective corpus / paper metadata
- horizon-specific reranker family and alpha
- horizon-specific concentration configs
- horizon-specific paper-facing surface-layer configs

The only intended change is the retrieval/reranking pool size:

- old: `5000`
- new: `2000`

## Build Notes

The new build required one code fix in
`scripts/build_current_reranked_frontier.py`.
After recent upstream changes, surfaced diagnostics could collide with
pre-existing columns and produce `_x` / `_y` suffixes. I added a coalescing step
so fields such as `endpoint_broadness_pct` survive the surfaced merge path
cleanly.

I also derived a lightweight `pool=2000` panel cache from the existing historical
panel by adding:

- `in_pool_2000 = (transparent_rank <= 2000)`

This avoids a full historical rebuild and keeps the comparison focused.

## Main Result

`pool=2000` does **not** dominate `pool=5000` on the current surfaced shortlist.

It produces a shortlist that is:

- shallower in transparent-rank origin
- less concentrated on the single most repeated target
- somewhat less WTP-heavy
- but also less diverse in theme pairs
- and slightly more green/climate-heavy

So the honest conclusion is:

- `2000` is the better budget for the current **global top-100 historical**
  objective
- but `5000` still buys broader current-frontier exploration
- therefore we should **not** switch the paper-facing current frontier default to
  `2000` yet

## Side-by-Side Diagnostics

Source:

- `outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/pool_compare_summary.csv`

### Horizon 5

- top target share:
  - `5000: 0.07`
  - `2000: 0.06`
- WTP share:
  - `5000: 0.07`
  - `2000: 0.06`
- green share:
  - `5000: 0.38`
  - `2000: 0.42`
- unique theme pairs:
  - `5000: 32`
  - `2000: 28`
- unique sources:
  - `5000: 76`
  - `2000: 79`
- unique targets:
  - `5000: 67`
  - `2000: 74`
- broad-endpoint share:
  - `5000: 0.55`
  - `2000: 0.49`
- textbook-like share:
  - `5000: 0.50`
  - `2000: 0.43`

### Horizon 10

- top target share:
  - `5000: 0.11`
  - `2000: 0.06`
- WTP share:
  - `5000: 0.11`
  - `2000: 0.07`
- green share:
  - `5000: 0.35`
  - `2000: 0.39`
- unique theme pairs:
  - `5000: 35`
  - `2000: 33`
- unique sources:
  - `5000: 75`
  - `2000: 81`
- unique targets:
  - `5000: 61`
  - `2000: 77`
- broad-endpoint share:
  - `5000: 0.45`
  - `2000: 0.46`
- textbook-like share:
  - `5000: 0.41`
  - `2000: 0.41`

### Horizon 15

- top target share:
  - `5000: 0.09`
  - `2000: 0.06`
- WTP share:
  - `5000: 0.08`
  - `2000: 0.06`
- green share:
  - `5000: 0.37`
  - `2000: 0.40`
- unique theme pairs:
  - `5000: 32`
  - `2000: 28`
- unique sources:
  - `5000: 75`
  - `2000: 79`
- unique targets:
  - `5000: 66`
  - `2000: 70`
- broad-endpoint share:
  - `5000: 0.38`
  - `2000: 0.34`
- textbook-like share:
  - `5000: 0.43`
  - `2000: 0.40`

## Overlap / Depth Read

Source:

- `outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/pool_compare_top100_overlap.csv`

The surfaced top-100 changes a lot when the pool is reduced:

- overlap counts:
  - `h=5: 9`
  - `h=10: 11`
  - `h=15: 13`
- Jaccard overlap:
  - `h=5: 0.047`
  - `h=10: 0.058`
  - `h=15: 0.070`

So pool size is not a cosmetic choice. It changes the surfaced shortlist
substantially.

The `pool=2000` shortlist is much shallower in transparent-rank origin:

- mean transparent rank in surfaced top-100
  - `h=5: 2736 -> 1018`
  - `h=10: 2681 -> 1020`
  - `h=15: 2598 -> 1033`
- share from transparent rank `>2000`
  - `5000: 0.63-0.68`
  - `2000: 0.00`

This is exactly what we should expect. A smaller pool forces the surfaced
shortlist to live closer to the transparent retrieval layer.

## Interpretation

Why `2000` helps:

- it trims the very deep rescues
- this reduces repeated-target concentration
- it also lowers WTP exposure modestly
- and it improves some broad/textbook-like diagnostics

Why `2000` hurts:

- it removes a large part of the reranker’s exploratory reach
- this lowers theme-pair diversity
- it increases reliance on already-visible retrieval neighborhoods
- in the current run, that tends to tilt the shortlist somewhat back toward
  green/climate clusters

So there is a real objective split:

- for the current **global top-100 benchmark**, `2000` looks strong
- for the current **current-frontier exploratory shortlist**, `5000` still has a
  case because it brings in deeper candidates

## Readability

Snapshot file:

- `outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/pool_compare_shortlist_snapshots.md`

My qualitative read is:

- `2000` looks a bit cleaner on concentration
- but not clearly better on paper-likeness
- several top `2000` items are still broad anchored pairs such as
  `Digitization -> Economic Development`,
  `Capital Account -> Economic Growth`,
  `Renewable Energy -> Environmental, social, and governance`
- so switching to `2000` alone does not solve the remaining shortlist-quality
  problem

## Recommendation

Do **not** replace the current `5000` current-frontier default with `2000` yet.

Instead:

1. Keep `2000` as the strongest challenger for the global top-100 retrieval
   objective.
2. Keep `5000` as the working current-frontier default for now.
3. Add the next evaluation layer that the user flagged explicitly:
   - within-field top-`K`
   - larger budget ladders like `100`, `250`, `1000`
4. Revisit pool size after we know whether exploratory depth matters more once
   the user-facing object is “top candidates within field” rather than one
   global top-100.
