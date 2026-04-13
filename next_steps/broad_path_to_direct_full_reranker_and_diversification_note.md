# Broad `path_to_direct` Full Reranker And Diversification Note

Date: 2026-04-09

## Purpose

This note records the first full-corpus follow-up to the sampled method-v2
reranker grid for broad `path_to_direct`.

It answers two questions:

1. Which learned-reranker family survives on the full non-sampled corpus?
2. What happens if we put a light diversification layer on top of the winner?

## Artifacts

Full reranker grid:

- `outputs/paper/74_method_v2_full_reranker_grid/broad_path_to_direct/reranker_summary.csv`
- `outputs/paper/74_method_v2_full_reranker_grid/broad_path_to_direct/reranker_best_configs.csv`
- `outputs/paper/74_method_v2_full_reranker_grid/broad_path_to_direct/learned_reranker_summary.md`

Diversification follow-up:

- `outputs/paper/74_method_v2_full_reranker_grid/diversification_pool10000/reranker_diversification_summary.csv`
- `outputs/paper/74_method_v2_full_reranker_grid/diversification_pool10000/reranker_diversification_by_cutoff.csv`
- `next_steps/method_v2_diversification_note.md`

## Full-Corpus Reranker Result

Unlike the sampled run, the full-corpus comparison does not show a strong
pairwise advantage.

Average over all tested cutoffs, horizons, and pool sizes:

| Model | Feature family | Mean MRR | Mean Recall@100 | Mean delta Recall@100 vs pref |
|---|---|---:|---:|---:|
| `glm_logit` | `family_aware_composition` | `0.009217` | `0.096426` | `+0.093980` |
| `glm_logit` | `family_aware_boundary_gap` | `0.009211` | `0.097617` | `+0.095171` |
| `pairwise_logit` | `family_aware_composition` | `0.009081` | `0.096058` | `+0.093612` |
| `pairwise_logit` | `family_aware_boundary_gap` | `0.009030` | `0.096534` | `+0.094088` |
| `glm_logit` | `family_aware` | `0.008997` | `0.096200` | `+0.093755` |
| `pairwise_logit` | `family_aware` | `0.008977` | `0.092546` | `+0.090101` |

## Main Read

Three things matter.

1. The full run compresses the differences a lot.

All six candidates are now fairly close. The sampled story was directionally
useful, but it overstated how much pairwise reranking was pulling away.

2. The best overall mean MRR is now `glm_logit + family_aware_composition`.

That edge is small, but it is real in the full aggregation.

3. The whole family-aware frontier is healthy.

All six candidates are strongly positive relative to preferential attachment on
both mean MRR and mean Recall@100. So the important win is not just one tiny
family-vs-family race. It is that the redesigned candidate object and richer
family-aware features are working on the full corpus.

## Recommendation

My recommendation after the full run is:

- main broad `path_to_direct` reranker default:
  - `glm_logit + family_aware_composition`
- closest robustness alternative:
  - `glm_logit + family_aware_boundary_gap`
- appendix alternative if we still want a pairwise comparator:
  - `pairwise_logit + family_aware_composition`

Why this is my recommendation:

1. It has the best mean MRR in the full aggregate.
2. It is the simpler model class.
3. The difference versus the nearest alternatives is small enough that
   simplicity and interpretability should count.

## Important Nuance

The cell winners still vary.

By best mean MRR within each `(pool_size, horizon)` cell:

- `pool=5000`, `h=5`:
  - `pairwise_logit + family_aware`
- `pool=5000`, `h=10`:
  - `pairwise_logit + family_aware_composition`
- `pool=10000`, `h=5`:
  - `pairwise_logit + family_aware_composition`
- `pool=10000`, `h=10`:
  - `glm_logit + family_aware_composition`

So the right conclusion is not “one model crushes the others.” The right
conclusion is:

- the family-aware redesign is robust
- the full corpus pushes us back toward a simpler main default

## Diversification Follow-Up

For concentration control, I ran a light reranker diversification pass at
`pool_size = 10000` using the horizon-specific full-run winners:

- `h = 5`:
  - `glm_logit + family_aware`
- `h = 10`:
  - `pairwise_logit + family_aware_boundary_gap`

This is a post-ranking screening layer, not a new benchmark winner.

## Diversification Result

Average over the evaluated cutoff years:

### Horizon 5

- precision@100:
  - `0.153333 -> 0.160000`
- recall@100:
  - `0.090062 -> 0.092469`
- MRR:
  - `0.007157 -> 0.007565`
- mean top-100 top-target share delta:
  - `-0.160`
- mean top-100 theme-pair gain:
  - `+6.33`

### Horizon 10

- precision@100:
  - `0.260000 -> 0.313333`
- recall@100:
  - `0.074455 -> 0.089655`
- MRR:
  - `0.006699 -> 0.007196`
- mean top-100 top-target share delta:
  - `-0.250`
- mean top-100 theme-pair gain:
  - `+7.00`

## Interpretation

This is better than the cautious prior.

The light diversification layer does not merely trade concentration for quality.
On this pass, it improves both:

- shortlist diversity
- and the standard ranking metrics

That is especially clear at `h = 10`, where the gains are not tiny.

## Recommendation On Concentration

My recommendation now is:

- keep concentration control as a post-ranking layer
- make light diversification the leading concentration candidate for the next
  paper-grade comparison

I would not call it fully frozen yet, because this pass is tied to:

- `pool_size = 10000`
- a small number of cutoff years
- the current broad `path_to_direct` setup

But it is now the best-supported concentration direction we have.

## Bottom Line

The full-corpus result is encouraging in two different ways.

1. The reranker race is no longer fragile.

The full run says the redesigned family-aware candidate object is doing the
important work. The best model is now a simple `glm_logit +
family_aware_composition`, not a more elaborate pairwise winner.

2. The concentration layer looks genuinely useful.

The diversification pass improved both ranking metrics and shortlist breadth.
That means the current next step should be:

- treat `glm_logit + family_aware_composition` as the main broad
  `path_to_direct` reranker default
- carry light diversification as the first concentration-control method into the
  next paper-grade comparison
