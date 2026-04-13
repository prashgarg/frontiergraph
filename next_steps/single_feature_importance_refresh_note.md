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
| 1 | direct_degree_product | structural | 0.100000 | 0.120802 | 0.012452 | 10.0 |
| 2 | target_recent_incident_count | dynamic | 0.083333 | 0.108096 | 0.005552 | 8.3 |
| 3 | target_direct_in_degree | structural | 0.081667 | 0.094724 | 0.004792 | 8.2 |
| 4 | path_support_norm | structural | 0.075000 | 0.114860 | 0.008830 | 7.5 |
| 5 | hub_penalty | structural | 0.075000 | 0.114257 | 0.009109 | 7.5 |
| 6 | cooc_count | structural | 0.056667 | 0.091801 | 0.007577 | 5.7 |
| 7 | score | base | 0.056667 | 0.085177 | 0.007808 | 5.7 |
| 8 | motif_bonus_norm | structural | 0.048333 | 0.078762 | 0.005976 | 4.8 |
| 9 | motif_count | structural | 0.041667 | 0.062368 | 0.006214 | 4.2 |
| 10 | nearby_closure_density | boundary_gap | 0.041667 | 0.062368 | 0.006214 | 4.2 |
| 11 | source_direct_out_degree | structural | 0.041667 | 0.039592 | 0.002499 | 4.2 |
| 12 | source_recent_incident_count | dynamic | 0.035000 | 0.022593 | 0.001581 | 3.5 |
| 13 | source_recent_support_out_degree | dynamic | 0.031667 | 0.020900 | 0.001888 | 3.2 |
| 14 | source_support_out_degree | structural | 0.026667 | 0.018737 | 0.001665 | 2.7 |
| 15 | pair_evidence_diversity_mean | composition | 0.025000 | 0.022704 | 0.001962 | 2.5 |

### Family summary at h=5

| Family | Best P@100 | Mean P@100 | # Features |
|--------|-----------|-----------|------------|
| structural | 0.100000 | 0.042333 | 15 |
| dynamic | 0.083333 | 0.030278 | 6 |
| base | 0.056667 | 0.056667 | 1 |
| boundary_gap | 0.041667 | 0.021111 | 3 |
| composition | 0.025000 | 0.013519 | 9 |

## Top 15 features at h=10

| Rank | Feature | Family | P@100 | R@100 | MRR | Hits@100 |
|------|---------|--------|-------|-------|-----|----------|
| 1 | target_direct_in_degree | structural | 0.196667 | 0.146969 | 0.005991 | 19.7 |
| 2 | direct_degree_product | structural | 0.183333 | 0.119002 | 0.009726 | 18.3 |
| 3 | target_recent_incident_count | dynamic | 0.173333 | 0.091563 | 0.004925 | 17.3 |
| 4 | path_support_norm | structural | 0.143333 | 0.118219 | 0.008629 | 14.3 |
| 5 | hub_penalty | structural | 0.141667 | 0.115621 | 0.009016 | 14.2 |
| 6 | cooc_count | structural | 0.113333 | 0.096458 | 0.007459 | 11.3 |
| 7 | score | base | 0.111667 | 0.088961 | 0.007821 | 11.2 |
| 8 | motif_bonus_norm | structural | 0.093333 | 0.077142 | 0.005540 | 9.3 |
| 9 | motif_count | structural | 0.088333 | 0.079077 | 0.006059 | 8.8 |
| 10 | nearby_closure_density | boundary_gap | 0.088333 | 0.079077 | 0.006059 | 8.8 |
| 11 | source_direct_out_degree | structural | 0.076667 | 0.042012 | 0.002652 | 7.7 |
| 12 | source_recent_incident_count | dynamic | 0.068333 | 0.024983 | 0.002519 | 6.8 |
| 13 | source_recent_support_out_degree | dynamic | 0.065000 | 0.024065 | 0.002083 | 6.5 |
| 14 | source_support_out_degree | structural | 0.065000 | 0.026087 | 0.001667 | 6.5 |
| 15 | pair_evidence_diversity_mean | composition | 0.048333 | 0.028551 | 0.001885 | 4.8 |

### Family summary at h=10

| Family | Best P@100 | Mean P@100 | # Features |
|--------|-----------|-----------|------------|
| structural | 0.196667 | 0.085222 | 15 |
| dynamic | 0.173333 | 0.064167 | 6 |
| base | 0.111667 | 0.111667 | 1 |
| boundary_gap | 0.088333 | 0.043889 | 3 |
| composition | 0.048333 | 0.026852 | 9 |

## Top 15 features at h=15

| Rank | Feature | Family | P@100 | R@100 | MRR | Hits@100 |
|------|---------|--------|-------|-------|-----|----------|
| 1 | target_direct_in_degree | structural | 0.255000 | 0.130111 | 0.005768 | 25.5 |
| 2 | direct_degree_product | structural | 0.236667 | 0.111824 | 0.009661 | 23.7 |
| 3 | target_recent_incident_count | dynamic | 0.216667 | 0.078597 | 0.005155 | 21.7 |
| 4 | hub_penalty | structural | 0.183333 | 0.096704 | 0.007229 | 18.3 |
| 5 | path_support_norm | structural | 0.183333 | 0.097317 | 0.007116 | 18.3 |
| 6 | cooc_count | structural | 0.161667 | 0.100312 | 0.007704 | 16.2 |
| 7 | score | base | 0.145000 | 0.079926 | 0.006754 | 14.5 |
| 8 | motif_count | structural | 0.121667 | 0.065981 | 0.005171 | 12.2 |
| 9 | nearby_closure_density | boundary_gap | 0.121667 | 0.065981 | 0.005171 | 12.2 |
| 10 | motif_bonus_norm | structural | 0.121667 | 0.062391 | 0.004464 | 12.2 |
| 11 | source_direct_out_degree | structural | 0.103333 | 0.052828 | 0.002883 | 10.3 |
| 12 | source_recent_incident_count | dynamic | 0.096667 | 0.031859 | 0.003072 | 9.7 |
| 13 | source_recent_support_out_degree | dynamic | 0.095000 | 0.031374 | 0.002411 | 9.5 |
| 14 | source_support_out_degree | structural | 0.095000 | 0.032263 | 0.002110 | 9.5 |
| 15 | pair_evidence_diversity_mean | composition | 0.066667 | 0.025647 | 0.001960 | 6.7 |

### Family summary at h=15

| Family | Best P@100 | Mean P@100 | # Features |
|--------|-----------|-----------|------------|
| structural | 0.255000 | 0.113111 | 15 |
| dynamic | 0.216667 | 0.085278 | 6 |
| base | 0.145000 | 0.145000 | 1 |
| boundary_gap | 0.121667 | 0.058333 | 3 |
| composition | 0.066667 | 0.035370 | 9 |

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
