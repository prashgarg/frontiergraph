# Objective-Specific Pool Defaults Note

Date: 2026-04-10

## Why we are not freezing one universal pool size

The recent retrieval-budget, reranker-depth, current-frontier, and
field-conditioned budget evaluations all point to the same conclusion:

- pool size is not a scientific constant
- it is a design choice tied to the user-facing shortlist object

That is why the current working defaults are split by objective rather than forced
into one universal number.

## Current working defaults

- single global exploratory top-`100`
  - `pool=5000`
- within-field top-`100`
  - `pool=2000`
- larger global scan budgets such as top-`250` / top-`1000`
  - `pool=2000`

These defaults are recorded in:

- `outputs/paper/94_field_conditioned_budget_eval_path_to_direct/recommended_objective_pool_defaults.csv`

## Why these are not arbitrary

The choices are anchored in a sequence of increasingly specific checks:

1. retrieval-budget evaluation
   - larger pools do not improve transparent top-`K` by themselves
   - they only raise the reranker’s opportunity set

2. reranker pool-depth evaluation
   - `500` is too small
   - `10000` is too large for the current global top-`100` objective
   - `2000` is the strongest challenger to `5000`

3. current-frontier direct comparison
   - `2000` reduces repeated-target and WTP concentration
   - but `5000` preserves deeper exploratory rescue for one global shortlist

4. field-conditioned and multi-budget evaluation
   - `2000` looks better for within-field browsing and larger scan budgets
   - `5000` still has a case for the single global exploratory top-`100`

So the logic is:

- use `5000` where exploratory depth is the main object
- use `2000` where concentration control and practical browsing are the main object

## How to explain this in the paper

The paper should say plainly that:

- the system follows a retrieval-then-rerank architecture
- pool size is tuned as part of the ranking design
- the appropriate pool depends on the evaluation or use-case budget
- the main text focuses on one headline object, but appendix robustness should show
  that this is not the only sensible operating point

## Robustness we should not forget

For the paper write-up, the current minimum robustness set should include:

1. pool-size robustness
   - compare at least `2000` and `5000`

2. budget robustness
   - report more than one `K`
   - at minimum: `100`, `250`, `1000`

3. field-conditioned robustness
   - show that conclusions are not an artifact of one global mixed shortlist

4. horizon robustness
   - keep the current `5, 10, 15` headline set
   - note that `3` and `20` were informative diagnostic extensions, even if they
     stay out of the main text

## Current stance

These are **working defaults**, not final immutable choices.

They are strong enough to guide the next frontier outputs and paper drafting, but
they should still be presented as design choices supported by historical and
current-frontier evidence, not as uniquely correct constants.
