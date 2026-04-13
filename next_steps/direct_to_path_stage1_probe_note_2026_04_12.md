# Direct-to-Path Stage 1 Probe Note

Date: 2026-04-12

This note records the first quick Stage 1 family comparison before the full widened
`direct-to-path` benchmark finishes.

Source:

- `outputs/paper/144_family_compare_fixed_pathlen_probe`

Probe design:

- corpus: `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`
- candidate kind: `causal_claim`
- family modes:
  - `path_to_direct`
  - `direct_to_path`
- cutoffs: `1990, 2000, 2010, 2015`
- horizons: `5, 10`
- current path setting held fixed
- 10% paper-sampled probe for speed

## 1. Immediate read

`direct-to-path` is not a trivial mirror of `path-to-direct`.

It is:

- smaller
- denser
- much higher base-rate
- far more anchored

So a side-by-side paper will not be comparing the same candidate geometry under two
labels. It will be comparing two genuinely different research-progress objects.

## 2. Candidate-universe contrast

Mean candidate counts in the probe:

- `path_to_direct`: about `55.6k`
- `direct_to_path`: about `16.8k`

So `direct-to-path` is roughly one-third the size of the `path-to-direct` universe in
this probe.

Status mix:

- `path_to_direct` is mostly `fully_open`
- `direct_to_path` is almost entirely `direct_present__path_missing`

This is substantively useful. It confirms that `direct-to-path` is inherently a much
more anchored object.

## 3. Positive-rate contrast

Mean positive rates in the probe:

- `path_to_direct`
  - `h=5`: about `0.21%`
  - `h=10`: about `0.39%`
- `direct_to_path`
  - `h=5`: about `5.3%`
  - `h=10`: about `9.8%`

This is the biggest structural difference.

Interpretation:

- later mechanism thickening around an existing direct claim is far more common than
  later direct closure of a path-supported missing edge
- this already points toward economist relevance
- but it also means the two families will not be directly comparable without careful
  notes, because the outcome frequencies are on very different scales

## 4. First ranking read

In this probe:

- `path_to_direct`
  - transparent `main` beats preferential attachment at `h=5`
  - at `h=10`, preferential attachment is still competitive and even stronger on the
    broad fully-open slice
- `direct_to_path`
  - transparent `main` is meaningful
  - but preferential attachment is still slightly stronger than `main` in the broad
    `causal_direct_to_path` slice in this quick probe

So the immediate read is mixed:

- `direct-to-path` is clearly a real object
- but the current transparent score is not obviously already the right transparent rule
  for it

That is exactly why reranker parity matters. We should not judge the family only on the
current transparent score.

## 5. Strict slice versus broad slice

The `identified_direct_to_path` slice is tiny but very strong:

- `h=5` recall@100 is above `0.5`
- `h=10` recall@100 is also above `0.5`

So when the direct claim is already in the strict identified-causal layer, later path
emergence is very predictable.

That is useful, but it is too small to be the whole paper. The broad
`causal_direct_to_path` slice is the real object we need to understand.

## 6. What this implies for Option C

The probe strengthens the case for the dual-family paper.

Why:

- `direct-to-path` is not redundant with `path-to-direct`
- it is clearly more mechanism-anchored
- it has much higher base rates
- it likely aligns more naturally with economist intuition

But the probe also says something cautionary:

- the two families are not symmetric benchmark objects
- the direct-to-path family may need its own transparent scoring logic or at least a
  family-specific reranker to look as strong as it deserves

## 7. Next decision

Do not decide from the probe alone.

The next real checkpoint is the full widened `direct-to-path` benchmark on the effective
corpus. If that run confirms the probe's basic picture, then we should proceed directly to
reranker parity and current-frontier parity under Option C.
