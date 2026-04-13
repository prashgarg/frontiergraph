# Widened Effective Benchmark (1990-2015)

## What was run

Current effective-corpus stack, current adopted reranker choices, widened five-year
cutoffs.

- panel cutoffs: `1985, 1990, 1995, 2000, 2005, 2010, 2015`
- reported cutoffs: `1990, 1995, 2000, 2005, 2010, 2015`
- warm-up only: `1985`
- horizons:
  - `h=5`: `1990, 1995, 2000, 2005, 2010, 2015`
  - `h=10`: `1990, 1995, 2000, 2005, 2010, 2015`
  - `h=15`: `1990, 1995, 2000, 2005, 2010`
- pool size: `5000`
- candidate family: `path_to_direct`
- scope: `broad`

Outputs:

- `outputs/paper/123_effective_benchmark_widened_1990_2015`

## Headline read

The widened benchmark supports keeping the current graph story, but it also makes the
era split clearer.

1. The adopted reranker still beats transparent retrieval and preferential attachment
   on the widened benchmark.
2. Early cutoffs are not only thinner. They are also structurally different.
3. The early era looks younger, more recent-share-heavy, and less diverse/stable than
   the later era.

So the right interpretation is:

- early eras are noisier **and**
- early eras are structurally different

not just “same object with fewer positives.”

## Overall benchmark

Mean `Recall@100`:

- `h=5`
  - adopted: `0.1376`
  - transparent: `0.0852`
  - pref-attach: `0.0377`
- `h=10`
  - adopted: `0.1391`
  - transparent: `0.0890`
  - pref-attach: `0.0450`
- `h=15`
  - adopted: `0.1541`
  - transparent: `0.0839`
  - pref-attach: `0.0362`

## Early vs late

Define:

- early = `1990, 1995`
- late = `2000, 2005, 2010, 2015` where horizon-valid

### Noise / thinness

Early cutoffs have far fewer realized positives.

- adopted, `h=5`: mean eval positives `12.5` early vs `103.0` late
- adopted, `h=10`: `32.5` early vs `214.5` late
- adopted, `h=15`: `55.5` early vs `268.0` late

This alone explains part of the instability.

### Structural difference

The surfaced top-100 also changes meaningfully across eras.

Relative to early cutoffs, late cutoffs have:

- older support ages
- lower recent-share measures
- higher stability
- higher evidence diversity
- slightly broader endpoints on average

Examples from the adopted model:

- `h=5`
  - top100 support age: `11.11` early vs `20.63` late
  - mean recent-share: about `0.413` early vs `0.314` late
  - pair evidence diversity: `8.75` early vs `10.58` late
- `h=10`
  - top100 support age: `11.68` early vs `20.36` late
  - mean recent-share: about `0.430` early vs `0.320` late
  - pair evidence diversity: `8.53` early vs `10.54` late
- `h=15`
  - top100 support age: `11.54` early vs `18.54` late
  - mean recent-share: about `0.435` early vs `0.323` late
  - pair evidence diversity: `8.14` early vs `9.94` late

So the later era looks more established and structurally supported, not merely larger.

## Horizon-specific interpretation

- `h=5`: later-era adopted performance improves a lot and variance falls. This looks
  like genuine stabilization plus a richer realized set.
- `h=10`: later-era adopted performance is better on average, but variance is still
  nontrivial. The object is more mature than early years, but still mixed.
- `h=15`: early cutoffs can look strong on average, but they are far more volatile.
  This is exactly the sort of pattern that can tempt over-interpretation if only a
  couple of early cutoffs are shown.

## Paper implication

This widening should be kept in the paper workflow.

- Main headline benchmark can still emphasize the later era if needed.
- But the paper should be able to show that earlier cutoffs were checked.
- If someone asks whether early years were simply dropped, the answer is now no.
- If someone asks whether the early years behave differently, the answer is yes:
  they are both thinner and more recent-surge-like.

## Next move

Use this widened benchmark as the exercise grid for the appendix LLM usefulness sweep.

- main paper exercises:
  - `6` cutoffs at `h=5`
  - `6` cutoffs at `h=10`
  - `5` cutoffs at `h=15`
  - total `17`
