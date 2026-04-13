# Regime-Split Analyses

## Analysis 1: Sparse vs Dense (by co-occurrence density)

**Question:** Does the graph score's advantage over PA vary with local neighborhood density?

Candidates split at within-cell median co-occurrence count. Sparse = below median, Dense = above.

### h=5

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| dense | direct_degree_product | 0.191667 | 0.100293 | 0.011088 | 19.2 |
| dense | degree_recency | 0.141667 | 0.081727 | 0.013390 | 14.2 |
| dense | cooc_pref_attach | 0.136667 | 0.079726 | 0.012094 | 13.7 |
| dense | pref_attach | 0.135000 | 0.078560 | 0.013286 | 13.5 |
| dense | cooc_count | 0.133333 | 0.078732 | 0.012017 | 13.3 |
| dense | graph_score | 0.090000 | 0.057685 | 0.009745 | 9.0 |
| sparse | direct_degree_product | 0.076667 | 0.077161 | 0.004429 | 7.7 |
| sparse | degree_recency | 0.030000 | 0.027905 | 0.001684 | 3.0 |
| sparse | cooc_pref_attach | 0.028333 | 0.028144 | 0.002627 | 2.8 |
| sparse | pref_attach | 0.028333 | 0.025716 | 0.001730 | 2.8 |
| sparse | graph_score | 0.023333 | 0.015074 | 0.001558 | 2.3 |
| sparse | cooc_count | 0.021667 | 0.026336 | 0.001509 | 2.2 |

### h=10

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| dense | direct_degree_product | 0.348333 | 0.089460 | 0.008500 | 34.8 |
| dense | degree_recency | 0.270000 | 0.076345 | 0.009986 | 27.0 |
| dense | cooc_pref_attach | 0.268333 | 0.075456 | 0.009377 | 26.8 |
| dense | cooc_count | 0.261667 | 0.073960 | 0.009307 | 26.2 |
| dense | pref_attach | 0.260000 | 0.073032 | 0.009849 | 26.0 |
| dense | graph_score | 0.185000 | 0.052115 | 0.007272 | 18.5 |
| sparse | direct_degree_product | 0.153333 | 0.071462 | 0.004059 | 15.3 |
| sparse | degree_recency | 0.063333 | 0.028336 | 0.001680 | 6.3 |
| sparse | pref_attach | 0.060000 | 0.028246 | 0.001677 | 6.0 |
| sparse | cooc_pref_attach | 0.055000 | 0.022878 | 0.001985 | 5.5 |
| sparse | graph_score | 0.055000 | 0.016109 | 0.001446 | 5.5 |
| sparse | cooc_count | 0.046667 | 0.018618 | 0.001355 | 4.7 |

### Graph score minus PA (delta by regime)

| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |
|--------|---------|----------|----------|-------|---------|
| dense | 5 | 0.090000 | 0.135000 | -0.045000 | -33.3% |
| dense | 10 | 0.185000 | 0.260000 | -0.075000 | -28.8% |
| sparse | 5 | 0.023333 | 0.028333 | -0.005000 | -17.6% |
| sparse | 10 | 0.055000 | 0.060000 | -0.005000 | -8.3% |

## Analysis 2: High vs Low Impact Endpoints (by pair FWCI)

**Question:** Do the models screen differently in high-impact vs low-impact neighborhoods?

Candidates split at within-cell median pair_mean_fwci.

### h=5

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| high_fwci | direct_degree_product | 0.161667 | 0.108162 | 0.010841 | 16.2 |
| high_fwci | degree_recency | 0.115000 | 0.068455 | 0.005378 | 11.5 |
| high_fwci | pref_attach | 0.105000 | 0.062697 | 0.005140 | 10.5 |
| high_fwci | cooc_pref_attach | 0.085000 | 0.056446 | 0.003955 | 8.5 |
| high_fwci | cooc_count | 0.080000 | 0.049368 | 0.003873 | 8.0 |
| high_fwci | graph_score | 0.051667 | 0.037792 | 0.002447 | 5.2 |
| low_fwci | direct_degree_product | 0.153333 | 0.124335 | 0.011931 | 15.3 |
| low_fwci | cooc_pref_attach | 0.138333 | 0.120605 | 0.017408 | 13.8 |
| low_fwci | cooc_count | 0.136667 | 0.119419 | 0.017267 | 13.7 |
| low_fwci | degree_recency | 0.126667 | 0.104743 | 0.018914 | 12.7 |
| low_fwci | pref_attach | 0.111667 | 0.099752 | 0.018790 | 11.2 |
| low_fwci | graph_score | 0.108333 | 0.100104 | 0.014472 | 10.8 |

### h=10

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| high_fwci | direct_degree_product | 0.290000 | 0.093502 | 0.008031 | 29.0 |
| high_fwci | degree_recency | 0.213333 | 0.070363 | 0.006400 | 21.3 |
| high_fwci | pref_attach | 0.196667 | 0.066095 | 0.006184 | 19.7 |
| high_fwci | cooc_pref_attach | 0.180000 | 0.062326 | 0.007322 | 18.0 |
| high_fwci | cooc_count | 0.173333 | 0.059262 | 0.006220 | 17.3 |
| high_fwci | graph_score | 0.103333 | 0.036734 | 0.003948 | 10.3 |
| low_fwci | direct_degree_product | 0.290000 | 0.108427 | 0.009074 | 29.0 |
| low_fwci | cooc_count | 0.266667 | 0.105681 | 0.012695 | 26.7 |
| low_fwci | cooc_pref_attach | 0.266667 | 0.105868 | 0.012780 | 26.7 |
| low_fwci | degree_recency | 0.246667 | 0.092343 | 0.013299 | 24.7 |
| low_fwci | pref_attach | 0.230000 | 0.090852 | 0.013173 | 23.0 |
| low_fwci | graph_score | 0.201667 | 0.080712 | 0.010377 | 20.2 |

### Graph score minus PA (delta by impact regime)

| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |
|--------|---------|----------|----------|-------|---------|
| high_fwci | 5 | 0.051667 | 0.105000 | -0.053333 | -50.8% |
| high_fwci | 10 | 0.103333 | 0.196667 | -0.093333 | -47.5% |
| low_fwci | 5 | 0.108333 | 0.111667 | -0.003333 | -3.0% |
| low_fwci | 10 | 0.201667 | 0.230000 | -0.028333 | -12.3% |

## Interpretation

**Sparse-dense:** If the graph score's deficit relative to PA is smaller in sparse regimes,
that aligns with Sourati et al. (2023): graph structure is most useful where the literature
is thinnest, i.e., where popularity signals are weakest and local topology carries more
incremental information.

**Impact split:** If models screen differently in high-FWCI vs low-FWCI neighborhoods,
that reveals whether the reranker and graph score are better at predicting the appearance
of connections involving high-impact topics or low-impact topics. This connects to the
Impact4Cast finding that predicting *impactful* connections is harder than predicting any
connection.
