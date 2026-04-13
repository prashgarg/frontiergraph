# Regime-Split Analyses

## Analysis 1: Sparse vs Dense (by co-occurrence density)

**Question:** Does the graph score's advantage over PA vary with local neighborhood density?

Candidates split at within-cell median co-occurrence count. Sparse = below median, Dense = above.

### h=5

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| dense | direct_degree_product | 0.098333 | 0.196626 | 0.020614 | 9.8 |
| dense | cooc_pref_attach | 0.063333 | 0.175695 | 0.015518 | 6.3 |
| dense | cooc_count | 0.056667 | 0.154231 | 0.012309 | 5.7 |
| dense | graph_score | 0.055000 | 0.139591 | 0.012839 | 5.5 |
| dense | degree_recency | 0.028333 | 0.078106 | 0.003383 | 2.8 |
| dense | pref_attach | 0.028333 | 0.078106 | 0.003060 | 2.8 |
| sparse | direct_degree_product | 0.055000 | 0.261670 | 0.014230 | 5.5 |
| sparse | graph_score | 0.025000 | 0.072059 | 0.008139 | 2.5 |
| sparse | cooc_pref_attach | 0.020000 | 0.151833 | 0.010856 | 2.0 |
| sparse | degree_recency | 0.020000 | 0.158322 | 0.013574 | 2.0 |
| sparse | pref_attach | 0.018333 | 0.156039 | 0.009566 | 1.8 |
| sparse | cooc_count | 0.015000 | 0.052752 | 0.004682 | 1.5 |

### h=10

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| dense | direct_degree_product | 0.185000 | 0.192700 | 0.016988 | 18.5 |
| dense | cooc_pref_attach | 0.115000 | 0.154509 | 0.013439 | 11.5 |
| dense | cooc_count | 0.113333 | 0.159232 | 0.012121 | 11.3 |
| dense | graph_score | 0.110000 | 0.142240 | 0.012736 | 11.0 |
| dense | degree_recency | 0.066667 | 0.098701 | 0.003612 | 6.7 |
| dense | pref_attach | 0.058333 | 0.094768 | 0.003188 | 5.8 |
| sparse | direct_degree_product | 0.115000 | 0.254211 | 0.013249 | 11.5 |
| sparse | cooc_pref_attach | 0.043333 | 0.098609 | 0.006848 | 4.3 |
| sparse | degree_recency | 0.043333 | 0.099770 | 0.008178 | 4.3 |
| sparse | pref_attach | 0.043333 | 0.107247 | 0.006182 | 4.3 |
| sparse | graph_score | 0.036667 | 0.050071 | 0.004818 | 3.7 |
| sparse | cooc_count | 0.028333 | 0.048266 | 0.003678 | 2.8 |

### h=15

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| dense | direct_degree_product | 0.240000 | 0.181581 | 0.015970 | 24.0 |
| dense | cooc_pref_attach | 0.163333 | 0.158813 | 0.012920 | 16.3 |
| dense | cooc_count | 0.161667 | 0.161603 | 0.012244 | 16.2 |
| dense | graph_score | 0.148333 | 0.130957 | 0.010870 | 14.8 |
| dense | degree_recency | 0.085000 | 0.072762 | 0.003263 | 8.5 |
| dense | pref_attach | 0.073333 | 0.066650 | 0.002895 | 7.3 |
| sparse | direct_degree_product | 0.143333 | 0.199494 | 0.013275 | 14.3 |
| sparse | cooc_pref_attach | 0.065000 | 0.109516 | 0.007132 | 6.5 |
| sparse | degree_recency | 0.065000 | 0.108682 | 0.008051 | 6.5 |
| sparse | pref_attach | 0.065000 | 0.112485 | 0.006428 | 6.5 |
| sparse | graph_score | 0.041667 | 0.038370 | 0.003661 | 4.2 |
| sparse | cooc_count | 0.038333 | 0.042981 | 0.004162 | 3.8 |

### Graph score minus PA (delta by regime)

| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |
|--------|---------|----------|----------|-------|---------|
| dense | 5 | 0.055000 | 0.028333 | +0.026667 | 94.1% |
| dense | 10 | 0.110000 | 0.058333 | +0.051667 | 88.6% |
| dense | 15 | 0.148333 | 0.073333 | +0.075000 | 102.3% |
| sparse | 5 | 0.025000 | 0.018333 | +0.006667 | 36.4% |
| sparse | 10 | 0.036667 | 0.043333 | -0.006667 | -15.4% |
| sparse | 15 | 0.041667 | 0.065000 | -0.023333 | -35.9% |

## Analysis 2: High vs Low Impact Endpoints (by pair FWCI)

**Question:** Do the models screen differently in high-impact vs low-impact neighborhoods?

Candidates split at within-cell median pair_mean_fwci.

### h=5

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| high_fwci | direct_degree_product | 0.086667 | 0.212831 | 0.017425 | 8.7 |
| high_fwci | degree_recency | 0.063333 | 0.162698 | 0.006590 | 6.3 |
| high_fwci | graph_score | 0.058333 | 0.107804 | 0.009439 | 5.8 |
| high_fwci | pref_attach | 0.051667 | 0.146164 | 0.005601 | 5.2 |
| high_fwci | cooc_count | 0.048333 | 0.106614 | 0.009529 | 4.8 |
| high_fwci | cooc_pref_attach | 0.045000 | 0.094709 | 0.012051 | 4.5 |
| low_fwci | direct_degree_product | 0.055000 | 0.204546 | 0.017375 | 5.5 |
| low_fwci | cooc_count | 0.040000 | 0.223090 | 0.018844 | 4.0 |
| low_fwci | cooc_pref_attach | 0.040000 | 0.239261 | 0.018697 | 4.0 |
| low_fwci | graph_score | 0.031667 | 0.187595 | 0.023928 | 3.2 |
| low_fwci | degree_recency | 0.020000 | 0.126080 | 0.003374 | 2.0 |
| low_fwci | pref_attach | 0.018333 | 0.107561 | 0.003259 | 1.8 |

### h=10

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| high_fwci | direct_degree_product | 0.161667 | 0.210447 | 0.014788 | 16.2 |
| high_fwci | degree_recency | 0.118333 | 0.127237 | 0.005421 | 11.8 |
| high_fwci | graph_score | 0.106667 | 0.116227 | 0.011069 | 10.7 |
| high_fwci | pref_attach | 0.098333 | 0.107866 | 0.004677 | 9.8 |
| high_fwci | cooc_count | 0.095000 | 0.109248 | 0.009866 | 9.5 |
| high_fwci | cooc_pref_attach | 0.095000 | 0.105501 | 0.011158 | 9.5 |
| low_fwci | direct_degree_product | 0.118333 | 0.208543 | 0.019219 | 11.8 |
| low_fwci | cooc_pref_attach | 0.093333 | 0.203619 | 0.017474 | 9.3 |
| low_fwci | cooc_count | 0.090000 | 0.192399 | 0.016765 | 9.0 |
| low_fwci | graph_score | 0.058333 | 0.161160 | 0.016703 | 5.8 |
| low_fwci | degree_recency | 0.041667 | 0.130213 | 0.004066 | 4.2 |
| low_fwci | pref_attach | 0.036667 | 0.118485 | 0.003805 | 3.7 |

### h=15

| Regime | Model | P@100 | R@100 | MRR | Hits@100 |
|--------|-------|-------|-------|-----|----------|
| high_fwci | direct_degree_product | 0.203333 | 0.188132 | 0.015309 | 20.3 |
| high_fwci | degree_recency | 0.155000 | 0.118416 | 0.005041 | 15.5 |
| high_fwci | graph_score | 0.138333 | 0.111637 | 0.010924 | 13.8 |
| high_fwci | cooc_pref_attach | 0.136667 | 0.140209 | 0.011852 | 13.7 |
| high_fwci | cooc_count | 0.135000 | 0.140975 | 0.011193 | 13.5 |
| high_fwci | pref_attach | 0.128333 | 0.090483 | 0.004473 | 12.8 |
| low_fwci | direct_degree_product | 0.163333 | 0.195605 | 0.017441 | 16.3 |
| low_fwci | cooc_pref_attach | 0.133333 | 0.182045 | 0.015338 | 13.3 |
| low_fwci | cooc_count | 0.131667 | 0.183091 | 0.014928 | 13.2 |
| low_fwci | graph_score | 0.076667 | 0.120523 | 0.012683 | 7.7 |
| low_fwci | degree_recency | 0.060000 | 0.111023 | 0.003605 | 6.0 |
| low_fwci | pref_attach | 0.050000 | 0.088291 | 0.003378 | 5.0 |

### Graph score minus PA (delta by impact regime)

| Regime | Horizon | GS P@100 | PA P@100 | Delta | Delta % |
|--------|---------|----------|----------|-------|---------|
| high_fwci | 5 | 0.058333 | 0.051667 | +0.006667 | 12.9% |
| high_fwci | 10 | 0.106667 | 0.098333 | +0.008333 | 8.5% |
| high_fwci | 15 | 0.138333 | 0.128333 | +0.010000 | 7.8% |
| low_fwci | 5 | 0.031667 | 0.018333 | +0.013333 | 72.7% |
| low_fwci | 10 | 0.058333 | 0.036667 | +0.021667 | 59.1% |
| low_fwci | 15 | 0.076667 | 0.050000 | +0.026667 | 53.3% |

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
