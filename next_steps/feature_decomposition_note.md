# Feature-Set Decomposition

## Question

How much screening value does each feature group contribute?
- `directed_only`: 18 features requiring directed causal extraction
- `cooc_only`: 23 features computable from undirected co-occurrence + metadata
- `all_features`: all 41 features combined

All three use the same GLM logit reranker with L2 regularization (alpha=0.05)
and the same walk-forward temporal split.

## Results

### h=5

| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| reranker_all_features | 0.206000 | 0.064039 | 0.008095 | 20.6 |
| reranker_directed_only | 0.204000 | 0.064567 | 0.008820 | 20.4 |
| reranker_cooc_only | 0.168000 | 0.057083 | 0.006252 | 16.8 |
| pref_attach | 0.135000 | 0.053823 | 0.009234 | 13.5 |
| cooc_count | 0.133333 | 0.053926 | 0.008410 | 13.3 |

### h=10

| Model | P@100 | R@100 | MRR | Hits@100 |
|-------|-------|-------|-----|----------|
| reranker_all_features | 0.384000 | 0.058736 | 0.006268 | 38.4 |
| reranker_directed_only | 0.372000 | 0.057041 | 0.006233 | 37.2 |
| reranker_cooc_only | 0.316000 | 0.049635 | 0.005518 | 31.6 |
| cooc_count | 0.261667 | 0.049904 | 0.006411 | 26.2 |
| pref_attach | 0.260000 | 0.049272 | 0.006751 | 26.0 |

## Interpretation

The decomposition answers three questions:
1. Do directed-only features beat co-occurrence baselines on their own?
2. Do co-occurrence features beat directed-only features on their own?
3. Does combining both add value over either alone?

If the combined reranker substantially outperforms both subsets,
the directed extraction adds value ON TOP OF co-occurrence (additive claim).
If directed-only features alone already beat co-occurrence baselines,
that is an even stronger result (substitutive claim).
