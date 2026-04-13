# Co-occurrence Ablation Note

## Question

Does the directed causal claim graph add screening value over simple undirected co-occurrence?

## Baselines

- `cooc_count`: raw paper co-mention count (undirected, ignores direction and edge type)
- `cooc_jaccard`: neighbourhood overlap proxy (cooc / (src_degree + tgt_degree - cooc))
- `cooc_pref_attach`: co-occurrence weighted by log popularity (cooc * log1p(degree product))

## Results

### Horizon 5

| Model | Precision@100 | Recall@100 | MRR | Hits@100 |
|-------|--------------|-----------|-----|----------|
| degree_recency | 0.141667 | 0.055915 | 0.009307 | 14.2 |
| cooc_pref_attach * | 0.136667 | 0.054552 | 0.008462 | 13.7 |
| pref_attach | 0.135000 | 0.053823 | 0.009234 | 13.5 |
| cooc_count * | 0.133333 | 0.053926 | 0.008410 | 13.3 |
| directed_closure | 0.121667 | 0.049147 | 0.008444 | 12.2 |
| graph_score | 0.090000 | 0.039821 | 0.006853 | 9.0 |
| cooc_jaccard * | 0.066667 | 0.025549 | 0.001885 | 6.7 |
| lexical_similarity | 0.033333 | 0.007059 | 0.002274 | 3.3 |

Best co-occurrence baseline (`cooc_pref_attach`) beats graph score on precision@100 by 51.9%.

### Horizon 10

| Model | Precision@100 | Recall@100 | MRR | Hits@100 |
|-------|--------------|-----------|-----|----------|
| degree_recency | 0.270000 | 0.051550 | 0.006845 | 27.0 |
| cooc_pref_attach * | 0.268333 | 0.050875 | 0.006456 | 26.8 |
| cooc_count * | 0.261667 | 0.049904 | 0.006411 | 26.2 |
| pref_attach | 0.260000 | 0.049272 | 0.006751 | 26.0 |
| directed_closure | 0.235000 | 0.045369 | 0.006177 | 23.5 |
| graph_score | 0.183333 | 0.035032 | 0.005010 | 18.3 |
| cooc_jaccard * | 0.126667 | 0.023852 | 0.001483 | 12.7 |
| lexical_similarity | 0.073333 | 0.008244 | 0.001973 | 7.3 |

Best co-occurrence baseline (`cooc_pref_attach`) beats graph score on precision@100 by 46.4%.

## Interpretation

If the co-occurrence baselines perform similarly to the graph score, the directed causal
structure is not buying much beyond what raw paper co-mentions deliver. If the graph score
substantially outperforms co-occurrence, the directed claim structure justifies the harder
extraction. If co-occurrence baselines are even weaker than preferential attachment, that
confirms co-occurrence alone is a poor screen for future link appearance.

## Connection to Impact4Cast (Gu and Krenn 2025)

Gu and Krenn use undirected co-occurrence edges in a concept graph across all sciences.
This ablation tests the co-occurrence approach on our economics-specific directed claim
graph. If directed claims outperform co-occurrence here, it provides direct evidence that
the richer extraction is worthwhile in this domain.
