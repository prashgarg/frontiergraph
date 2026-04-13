# Benchmark Strategy Decision

## Question

Can the paper's benchmark claim be rescued by moving from the transparent graph score to the best learned reranker?

## Horizon 5
- best reranker: precision@100=0.222000, recall@100=0.071850, MRR=0.006739
- beats on precision@100: degree_recency, pref_attach, directed_closure, graph_score, lexical_similarity, cooc_gap
- beats on recall@100: degree_recency, pref_attach, directed_closure, graph_score, lexical_similarity, cooc_gap
- beats on MRR: graph_score, lexical_similarity, cooc_gap

## Horizon 10
- best reranker: precision@100=0.402000, recall@100=0.062955, MRR=0.006245
- beats on precision@100: degree_recency, pref_attach, directed_closure, graph_score, lexical_similarity, cooc_gap
- beats on recall@100: degree_recency, pref_attach, directed_closure, graph_score, lexical_similarity, cooc_gap
- beats on MRR: degree_recency, pref_attach, directed_closure, graph_score, lexical_similarity, cooc_gap

## Decision

`partial rescue`

The learned reranker is strong enough to keep the paper's benchmark claim alive, but the paper should be explicit that the winning graph-based benchmark is the learned reranker rather than the transparent graph score.

## Recommendation

1. move the comparative benchmark claim to the learned reranker
2. present the transparent graph score as the interpretable retrieval layer rather than the benchmark winner
3. keep the stronger transparent baselines in the paper as real comparison points

## Best reranker configs used

- h=5: `glm_logit + boundary_gap` with alpha `0.01`
- h=10: `pairwise_logit + composition` with alpha `0.10`
