# Extended Analyses Note

## Analysis 1: Reranker at all horizons (h=3,5,10,15)

### h=3
| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| direct_degree_product | 0.133333 | 0.069918 | 0.006450 | 13.3 |
| reranker | 0.123333 | 0.056618 | 0.006734 | 12.3 |
| cooc_count | 0.096667 | 0.060231 | 0.010727 | 9.7 |
| pref_attach | 0.096667 | 0.058383 | 0.011528 | 9.7 |
| graph_score | 0.055000 | 0.040590 | 0.009047 | 5.5 |

### h=5
| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| direct_degree_product | 0.183333 | 0.066334 | 0.007335 | 18.3 |
| reranker | 0.171667 | 0.053366 | 0.006808 | 17.2 |
| pref_attach | 0.135000 | 0.053823 | 0.009234 | 13.5 |
| cooc_count | 0.133333 | 0.053926 | 0.008410 | 13.3 |
| graph_score | 0.090000 | 0.039821 | 0.006853 | 9.0 |

### h=10
| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| direct_degree_product | 0.331667 | 0.058185 | 0.005289 | 33.2 |
| reranker | 0.320000 | 0.048946 | 0.005283 | 32.0 |
| cooc_count | 0.261667 | 0.049904 | 0.006411 | 26.2 |
| pref_attach | 0.260000 | 0.049272 | 0.006751 | 26.0 |
| graph_score | 0.183333 | 0.035032 | 0.005010 | 18.3 |

### h=15
| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| direct_degree_product | 0.450000 | 0.053591 | 0.004017 | 45.0 |
| reranker | 0.435000 | 0.045781 | 0.004053 | 43.5 |
| cooc_count | 0.368333 | 0.045553 | 0.005199 | 36.8 |
| pref_attach | 0.366667 | 0.045476 | 0.005374 | 36.7 |
| graph_score | 0.263333 | 0.032357 | 0.004188 | 26.3 |

## Analysis 2: Failure mode profiles

| Type | Horizon | Count | CoOc | DirectDegProd | FWCI | Boundary | Gap |
|------|---------|-------|------|---------------|------|----------|-----|
| hit | 3 | 13 | 207.2 | 3466 | 5.41 | 0.000 | 1.000 |
| hit | 5 | 18 | 208.8 | 3413 | 5.35 | 0.000 | 1.000 |
| hit | 10 | 32 | 185.8 | 3240 | 5.36 | 0.000 | 1.000 |
| hit | 15 | 44 | 174.0 | 3156 | 5.30 | 0.000 | 1.000 |
| miss | 3 | 87 | 108.0 | 3260 | 5.51 | 0.000 | 0.998 |
| miss | 5 | 82 | 103.3 | 3288 | 5.55 | 0.000 | 0.998 |
| miss | 10 | 68 | 87.7 | 3400 | 5.58 | 0.000 | 0.998 |
| miss | 15 | 56 | 75.3 | 3433 | 5.65 | 0.000 | 0.998 |
| missed_realized | 3 | 152 | 26.4 | 293 | 5.69 | 0.000 | 0.994 |
| missed_realized | 5 | 241 | 26.0 | 290 | 5.71 | 0.000 | 0.994 |
| missed_realized | 10 | 514 | 25.9 | 283 | 5.68 | 0.000 | 0.996 |
| missed_realized | 15 | 754 | 25.3 | 280 | 5.62 | 0.000 | 0.997 |

## Analysis 3: Journal-quality realization split

## Analysis 4: Temporal generalization

### h=3
| Era | Model | P@100 | Hits@100 | Cutoffs |
|-----|-------|-------|----------|---------|
| held_out_era | reranker_restricted | 0.245000 | 24.5 | 2 |
| held_out_era | pref_attach | 0.160000 | 16.0 | 2 |
| train_era | pref_attach | 0.065000 | 6.5 | 4 |
| train_era | reranker_restricted | 0.062500 | 6.2 | 4 |

### h=5
| Era | Model | P@100 | Hits@100 | Cutoffs |
|-----|-------|-------|----------|---------|
| held_out_era | reranker_restricted | 0.325000 | 32.5 | 2 |
| held_out_era | pref_attach | 0.210000 | 21.0 | 2 |
| train_era | pref_attach | 0.097500 | 9.8 | 4 |
| train_era | reranker_restricted | 0.097500 | 9.8 | 4 |

### h=10
| Era | Model | P@100 | Hits@100 | Cutoffs |
|-----|-------|-------|----------|---------|
| held_out_era | reranker_restricted | 0.550000 | 55.0 | 2 |
| held_out_era | pref_attach | 0.375000 | 37.5 | 2 |
| train_era | reranker_restricted | 0.207500 | 20.8 | 4 |
| train_era | pref_attach | 0.202500 | 20.2 | 4 |

### h=15
| Era | Model | P@100 | Hits@100 | Cutoffs |
|-----|-------|-------|----------|---------|
| held_out_era | reranker_restricted | 0.645000 | 64.5 | 2 |
| held_out_era | pref_attach | 0.460000 | 46.0 | 2 |
| train_era | reranker_restricted | 0.332500 | 33.2 | 4 |
| train_era | pref_attach | 0.320000 | 32.0 | 4 |

