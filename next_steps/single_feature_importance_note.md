# Single-Feature Importance Ranking

## Question

Which individual graph features carry the most screening signal when used alone?

## Method

For each of the reranker's features, rank candidates by that feature in isolation
and evaluate on the same walk-forward benchmark. This is directly comparable to the
141-feature ablation in Gu and Krenn (2025, Impact4Cast).

## Top 15 features at h=5

| Rank | Feature | Family | P@100 | R@100 | MRR | Hits@100 |
|------|---------|--------|-------|-------|-----|----------|
| 1 | direct_degree_product | structural | 0.183333 | 0.066334 | 0.007335 | 18.3 |
| 2 | support_degree_product | structural | 0.135000 | 0.053823 | 0.009234 | 13.5 |
| 3 | cooc_trend_norm | structural | 0.135000 | 0.054172 | 0.008359 | 13.5 |
| 4 | cooc_count | structural | 0.133333 | 0.053926 | 0.008410 | 13.3 |
| 5 | motif_count | structural | 0.121667 | 0.049147 | 0.008438 | 12.2 |
| 6 | nearby_closure_density | boundary_gap | 0.121667 | 0.049147 | 0.008438 | 12.2 |
| 7 | motif_bonus_norm | structural | 0.095000 | 0.041957 | 0.007896 | 9.5 |
| 8 | score | base | 0.090000 | 0.039821 | 0.006853 | 9.0 |
| 9 | pair_evidence_diversity_mean | composition | 0.086667 | 0.042809 | 0.002224 | 8.7 |
| 10 | path_support_norm | structural | 0.078333 | 0.035170 | 0.005809 | 7.8 |
| 11 | hub_penalty | structural | 0.076667 | 0.034790 | 0.004673 | 7.7 |
| 12 | source_direct_out_degree | structural | 0.076667 | 0.028279 | 0.002919 | 7.7 |
| 13 | source_recent_incident_count | dynamic | 0.076667 | 0.028279 | 0.002894 | 7.7 |
| 14 | source_recent_support_out_degree | dynamic | 0.076667 | 0.028279 | 0.002892 | 7.7 |
| 15 | source_support_out_degree | structural | 0.076667 | 0.028279 | 0.002887 | 7.7 |

### Family summary at h=5

| Family | Best P@100 | Mean P@100 | # Features |
|--------|-----------|-----------|------------|
| structural | 0.183333 | 0.085444 | 15 |
| boundary_gap | 0.121667 | 0.058333 | 3 |
| base | 0.090000 | 0.090000 | 1 |
| composition | 0.086667 | 0.041296 | 9 |
| dynamic | 0.076667 | 0.046944 | 6 |

## Top 15 features at h=10

| Rank | Feature | Family | P@100 | R@100 | MRR | Hits@100 |
|------|---------|--------|-------|-------|-----|----------|
| 1 | direct_degree_product | structural | 0.331667 | 0.058185 | 0.005289 | 33.2 |
| 2 | cooc_trend_norm | structural | 0.263333 | 0.050033 | 0.006360 | 26.3 |
| 3 | cooc_count | structural | 0.261667 | 0.049904 | 0.006411 | 26.2 |
| 4 | support_degree_product | structural | 0.260000 | 0.049272 | 0.006751 | 26.0 |
| 5 | motif_count | structural | 0.245000 | 0.048467 | 0.006192 | 24.5 |
| 6 | nearby_closure_density | boundary_gap | 0.245000 | 0.048467 | 0.006192 | 24.5 |
| 7 | pair_evidence_diversity_mean | composition | 0.195000 | 0.042679 | 0.002624 | 19.5 |
| 8 | motif_bonus_norm | structural | 0.186667 | 0.036615 | 0.005653 | 18.7 |
| 9 | score | base | 0.183333 | 0.035032 | 0.005010 | 18.3 |
| 10 | path_support_norm | structural | 0.166667 | 0.031280 | 0.004062 | 16.7 |
| 11 | hub_penalty | structural | 0.166667 | 0.031280 | 0.003369 | 16.7 |
| 12 | source_direct_out_degree | structural | 0.165000 | 0.028559 | 0.003084 | 16.5 |
| 13 | source_recent_incident_count | dynamic | 0.165000 | 0.028559 | 0.003060 | 16.5 |
| 14 | source_recent_support_out_degree | dynamic | 0.165000 | 0.028559 | 0.003058 | 16.5 |
| 15 | source_support_out_degree | structural | 0.165000 | 0.028559 | 0.003054 | 16.5 |

### Family summary at h=10

| Family | Best P@100 | Mean P@100 | # Features |
|--------|-----------|-----------|------------|
| structural | 0.331667 | 0.170889 | 15 |
| boundary_gap | 0.245000 | 0.120556 | 3 |
| composition | 0.195000 | 0.082222 | 9 |
| base | 0.183333 | 0.183333 | 1 |
| dynamic | 0.165000 | 0.098611 | 6 |

## Interpretation

Features that rank highly as standalone predictors are doing real screening work.
If directed-graph-specific features (path_support, mediator_count, gap_bonus,
boundary_flag, nearby_closure_density) appear in the top ranks, that directly
strengthens the case that the directed causal extraction adds value beyond
what co-occurrence or degree-based signals deliver.

If popularity-adjacent features (support_degree_product, cooc_count) dominate,
that confirms the co-occurrence ablation result: cumulative advantage is the
strongest single signal, and the reranker's advantage comes from combining
directed features rather than from any one feature alone.
