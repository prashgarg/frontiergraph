# Retrieval Budget Evaluation Note

Date: 2026-04-10

## Purpose

This note evaluates the retrieval-budget question more directly:

- how much does pool size matter?
- how informative is `Recall@100` on its own?
- are the top scores a plateau?
- why might a pool like `5000` still matter?

Outputs:

- earlier draft:
  - `outputs/paper/89_retrieval_budget_eval_path_to_direct`
  - this used a too-strict global cutoff filter tied to the maximum horizon
- corrected canonical run:
  - `outputs/paper/90_retrieval_budget_eval_path_to_direct_h3_h20`
  - this uses horizon-specific valid cutoffs

## Setup

The corrected pass uses:

- effective corpus:
  - `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`
- family:
  - broad `path_to_direct`
- cutoffs:
  - requested: `2000, 2005, 2010, 2015`
  - used horizon-specifically:
    - `h=3,5,10`: `2000, 2005, 2010, 2015`
    - `h=15`: `2000, 2005, 2010`
    - `h=20`: `2000, 2005`
- horizons:
  - `3, 5, 10, 15, 20`
- pool sizes:
  - `500, 2000, 5000, 10000`
- evaluation budgets:
  - `20, 50, 100, 250, 500`

The script builds the **full transparent candidate table** at each cutoff and then
evaluates retrieval budgets off that ranking.

## 1. Candidate universe is very large

Mean candidate counts are large even before any reranking:

- about `300k` candidates per cutoff on average

Mean future-positive counts are also large and rise with horizon:

- `h=3`: about `5.7k`
- `h=5`: about `10.0k`
- `h=10`: about `26.9k`
- `h=15`: about `38.2k`
- `h=20`: about `52.0k`

This matters because a top-`100` or top-`500` budget is tiny relative to the full
candidate universe.

## 2. Transparent recall at small K is flat across pool size

The main empirical result is simple:

- increasing pool size from `500` to `10000` does **not** change transparent
  `Recall@20`, `Recall@50`, `Recall@100`, `Recall@250`, or `Recall@500`

That is not a bug. It follows mechanically from the setup:

- the transparent top-`500` is the same regardless of whether we keep only the top
  `500` or allow a larger downstream pool

So, for example at `h=3`:

- `Recall@100` stays about `0.0010`
- `Recall@500` stays about `0.0032`

At `h=5`:

- `Recall@100` stays about `0.0008`
- `Recall@500` stays about `0.0027`

At `h=10`:

- `Recall@100` stays about `0.0006`
- `Recall@500` stays about `0.0019`

At `h=15`:

- `Recall@100` stays about `0.0005`
- `Recall@500` stays about `0.0016`

At `h=20`:

- `Recall@100` stays about `0.0004`
- `Recall@500` stays about `0.0013`

This tells us that **transparent retrieval alone is not enough** if we care about
improving the visible top-`K` shortlist.

## 3. Larger pools still matter through their recall ceiling

While top-`500` transparent recall is flat, larger pools do raise the **pool recall
ceiling**:

At `h=3`:

- pool `500`: ceiling about `0.0032`
- pool `2000`: ceiling about `0.0078`
- pool `5000`: ceiling about `0.0129`
- pool `10000`: ceiling about `0.0173`

At `h=5`:

- pool `500`: ceiling about `0.0027`
- pool `2000`: ceiling about `0.0069`
- pool `5000`: ceiling about `0.0112`
- pool `10000`: ceiling about `0.0156`

At `h=10`:

- pool `500`: ceiling about `0.0019`
- pool `10000`: ceiling about `0.0126`

At `h=15`:

- pool `500`: ceiling about `0.0016`
- pool `10000`: ceiling about `0.0106`

At `h=20`:

- pool `500`: ceiling about `0.0013`
- pool `10000`: ceiling about `0.0084`

So a larger pool does buy something real:

- it increases how many future positives are available to the reranker

What it does **not** do by itself is improve the transparent top-`K`.

## 4. Why `5000` can still matter

The current surfaced frontier gives the practical answer.

In:

- `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv`

the surfaced top-100 draws very heavily from deep transparent ranks:

### h=5

- mean transparent rank of surfaced top-100: about `2736`
- share with transparent rank > `500`: `0.92`
- share with transparent rank > `1000`: `0.84`
- share with transparent rank > `2000`: `0.68`

### h=10

- mean transparent rank of surfaced top-100: about `2681`
- share with transparent rank > `500`: `0.92`
- share with transparent rank > `1000`: `0.86`

### h=15

- mean transparent rank of surfaced top-100: about `2598`
- share with transparent rank > `500`: `0.90`
- share with transparent rank > `1000`: `0.82`

This is the key point.

`5000` matters **not** because the transparent top-100 itself improves when we enlarge
the pool, but because:

- the learned reranker is successfully rescuing many candidates from deep in the
  transparent ranking

That is the strongest current justification for having a larger retrieval pool.

## 5. What the score-plateau diagnostics say

The transparent score is somewhat compressed at the top, but not fully flat.

Across cutoffs:

- top-100 score span is about `0.049-0.066`
- gap between ranks `1` and `10` is about `0.021-0.031`
- gap between ranks `10` and `100` is about `0.022-0.035`
- gap between ranks `100` and `500` is smaller, about `0.012-0.015`

In the corrected run, `2015` is also included in the plateau diagnostics for the
shorter horizons, with:

- top-100 span about `0.0576`
- gap `1 -> 10` about `0.0353`
- gap `10 -> 100` about `0.0224`
- gap `100 -> 500` about `0.0115`

So the top is compressed, but not degenerate.

Interpretation:

- rank differences near the top are meaningful but modest
- `Recall@100` is therefore useful as one checkpoint, but it should not be treated as
  the only budget that matters

## 6. Practical implications

### A. `Recall@100` should not stand alone

We should report multi-`K` curves or at least a small budget ladder such as:

- `20, 50, 100, 250, 500`

### B. Pool size is a design parameter, not a scientific constant

The right interpretation is:

- a larger pool increases the reranker's opportunity set
- it does not automatically improve the transparent shortlist

### C. The next retrieval question is not just “bigger or smaller pool?”

It is:

- how deep into the transparent pool does the final surfaced shortlist actually draw?
- and does that justify `5000` over `2000` or `10000`?

## 7. Recommended next step from this note

The next clean diagnostic is:

- **reranker depth-usage vs pool size**

That means:

- rerun or audit the reranker with pools `500, 2000, 5000, 10000`
- report where surfaced top-`100` items came from in transparent rank
- ask whether `5000` is still needed once we measure that directly

That is the right next step if we want to justify pool size carefully.
