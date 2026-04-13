# Field-Conditioned Budget Evaluation Note

Date: 2026-04-10

## Purpose

Earlier runs suggested that `pool=2000` is a strong challenger to `pool=5000`
for the **global top-100 historical** objective. The user correctly flagged that
this may not transfer to other user-facing objectives:

- top-100 within field
- larger budget ladders such as top-250 or top-1000

This note evaluates that question directly on the current frontiers.

Outputs:

- `outputs/paper/94_field_conditioned_budget_eval_path_to_direct/field_budget_metrics.csv`
- `outputs/paper/94_field_conditioned_budget_eval_path_to_direct/field_budget_compare.csv`
- `outputs/paper/94_field_conditioned_budget_eval_path_to_direct/field_budget_overlap.csv`
- `outputs/paper/94_field_conditioned_budget_eval_path_to_direct/field_budget_summary.md`

Compared frontiers:

- `pool5000`
  - `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv`
- `pool2000`
  - `outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv`

## Overlay

The field overlay is intentionally lightweight and aligned to the existing public
field shelves:

- `macro-finance`
- `development-urban`
- `trade-globalization`
- `climate-energy`
- `innovation-productivity`
- `other`

This is a **provisional browse overlay**, not a new ontology layer. Membership is
non-exclusive.

## Main Result

The “best pool” depends strongly on the user-facing objective.

### 1. Global top-100 still favors `2000` on concentration

At `K=100`, `pool2000` continues to reduce:

- top-target share
- WTP share

relative to `pool5000`.

But it also:

- increases green/climate share
- reduces global unique theme-pair diversity

So the global top-100 result remains mixed, just as in the direct current-frontier
comparison.

### 2. At larger global budgets, `2000` looks stronger

At `K=250` and especially `K=1000`, the case for `2000` strengthens:

- top-target share falls sharply
- WTP share falls sharply
- by `K=1000`, green/climate share is actually **lower** under `2000`
- global unique theme-pair counts are roughly comparable by `K=1000`

So the earlier “`2000` vs `5000`” conclusion was not wrong, but it was too tied to
the single global top-100 view.

### 3. Within-field top-100 often looks better under `2000`

For many fields at `K=100`, `pool2000` improves:

- top-target concentration
- number of unique targets

This is especially visible in:

- `development-urban`
- `innovation-productivity`
- `trade-globalization`
- `other`

The clearest pattern is that `2000` produces **cleaner within-field concentration**
while `5000` produces **deeper global exploration**.

### 4. The overlap remains low

Even within field, the top slices change a lot between `2000` and `5000`.

Global overlap is still small:

- `K=100`: about `9-13` shared items by horizon
- `K=250`: about `37-40`
- `K=1000`: about `181-192`

Field overlaps are somewhat higher than global overlap, especially for
`macro-finance` and `climate-energy`, but still far from trivial.

So pool size remains a substantive choice, not a cosmetic one.

## Interpretation

The current evidence supports a split conclusion:

- if the objective is a **single global exploratory shortlist**, `5000` still has a
  real case because it reaches deeper into the transparent ranking
- if the objective is **cleaner concentration at fixed budgets**, especially
  within-field or larger budget ladders, `2000` often looks better

That means we should stop talking as if there is one universally best pool size.

The right framing is:

- `2000` is strong for concentration-focused retrieval
- `5000` is strong for exploratory rescue depth

## Recommendation

Do not freeze a new single default yet.

Instead:

1. Keep `5000` as the working exploratory current-frontier default.
2. Treat `2000` as the leading alternative for:
   - within-field browsing
   - larger shortlist budgets
   - concentration-sensitive public or analyst-facing views
3. Next, add a user-facing evaluation layer that explicitly asks which object we
   are optimizing:
   - global exploratory top-100
   - top-100 within field
   - top-250 or top-1000 research scan

That is a better next decision point than trying to force one pool size to serve
all three objects.
