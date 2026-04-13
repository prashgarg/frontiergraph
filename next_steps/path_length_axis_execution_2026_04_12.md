# Path-length axis execution order

This note freezes the second design axis now that the paired-family paper has
mostly been set up.

## Scope

The first honest path-length axis is:

- family: `path-to-direct`
- `max_path_len`: `2`, `3`, `4`, `5`

That is deliberate. The ranking layer now supports bounded path lengths up to 5,
but the `direct-to-path` historical event is still defined as the first
appearance of a length-2 path. So if we ran both families immediately, the
experiment would mix a changed support structure with an unchanged direct-to-path
event definition.

## What to run

For each `max_path_len`:

1. widened benchmark with the current family-specific adopted configs
2. reranker tuning on the same saved feature panel
3. widened benchmark rerun using the tuned configs

The orchestration script for this is:

- [scripts/run_path_length_axis.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/run_path_length_axis.py)

## What to compare

The main summary should compare, by horizon:

- transparent Recall@100
- transparent MRR
- tuned reranker Recall@100
- tuned reranker MRR
- delta versus preferential attachment
- delta versus the transparent score

The first read should ask:

1. does longer support help at all?
2. if it helps, does it help the transparent score or mostly the reranker?
3. does improvement come with weaker interpretability or noisier surfaced
   examples?

## Interpretation rule

Do not interpret a longer path as automatically “more creative.”

If `max_path_len = 4` or `5` helps, that can mean at least three different
things:

- the graph is providing useful bridge support
- the graph is becoming dense enough that longer paths still carry signal
- the reranker is learning to separate useful longer support from generic graph
  proximity

That is why the graph-evolution appendix figure matters. It gives the descriptive
background for whether longer paths are plausible candidates or mostly dense-graph
artifacts.

## What belongs in the paper

If the path-length axis is weak or ambiguous:

- appendix only

If one intermediate length, likely `3` or `4`, clearly dominates:

- appendix figure with one sentence in the discussion

Only if the gains are large, stable, and interpretable should the path-length
axis become a visible main-text result.
