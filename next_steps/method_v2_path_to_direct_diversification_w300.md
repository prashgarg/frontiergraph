# Reranker Diversification Note

## Question

Can a light diversification layer widen idea coverage on the historical reranker benchmark without giving back the rescued benchmark performance?

## Horizon 5
- diversified reranker precision@100: `0.180`
- diversified reranker recall@100: `0.109859`
- diversified reranker MRR: `0.008540`
- delta precision@100 vs undiversified reranker: `+0.033`
- delta recall@100 vs undiversified reranker: `+0.024098`
- delta MRR vs undiversified reranker: `+0.000667`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `6.00`
- mean top-100 top-target share delta: `-0.137`

## Horizon 10
- diversified reranker precision@100: `0.320`
- diversified reranker recall@100: `0.092718`
- diversified reranker MRR: `0.007958`
- delta precision@100 vs undiversified reranker: `+0.053`
- delta recall@100 vs undiversified reranker: `+0.018295`
- delta MRR vs undiversified reranker: `+0.000444`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `6.33`
- mean top-100 top-target share delta: `-0.217`

## Horizon 15
- diversified reranker precision@100: `0.410`
- diversified reranker recall@100: `0.087139`
- diversified reranker MRR: `0.007419`
- delta precision@100 vs undiversified reranker: `+0.067`
- delta recall@100 vs undiversified reranker: `+0.013604`
- delta MRR vs undiversified reranker: `+0.000371`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `5.67`
- mean top-100 top-target share delta: `-0.233`

## Interpretation

This is a post-ranking screening layer, not a new benchmark model. The right question is whether it widens idea coverage at an acceptable cost once the reranker has already done the hard ranking work.

## Recommendation

If the performance losses remain modest while theme coverage improves, present diversification as a light screening extension rather than as part of the benchmark winner itself.
