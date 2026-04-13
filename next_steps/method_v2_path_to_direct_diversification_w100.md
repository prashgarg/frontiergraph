# Reranker Diversification Note

## Question

Can a light diversification layer widen idea coverage on the historical reranker benchmark without giving back the rescued benchmark performance?

## Horizon 5
- diversified reranker precision@100: `0.147`
- diversified reranker recall@100: `0.085761`
- diversified reranker MRR: `0.008350`
- delta precision@100 vs undiversified reranker: `+0.000`
- delta recall@100 vs undiversified reranker: `+0.000000`
- delta MRR vs undiversified reranker: `+0.000478`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `5.67`
- mean top-100 top-target share delta: `+0.000`

## Horizon 10
- diversified reranker precision@100: `0.267`
- diversified reranker recall@100: `0.074423`
- diversified reranker MRR: `0.007819`
- delta precision@100 vs undiversified reranker: `+0.000`
- delta recall@100 vs undiversified reranker: `+0.000000`
- delta MRR vs undiversified reranker: `+0.000305`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `5.67`
- mean top-100 top-target share delta: `+0.000`

## Horizon 15
- diversified reranker precision@100: `0.343`
- diversified reranker recall@100: `0.073535`
- diversified reranker MRR: `0.007280`
- delta precision@100 vs undiversified reranker: `+0.000`
- delta recall@100 vs undiversified reranker: `+0.000000`
- delta MRR vs undiversified reranker: `+0.000233`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `5.00`
- mean top-100 top-target share delta: `+0.000`

## Interpretation

This is a post-ranking screening layer, not a new benchmark model. The right question is whether it widens idea coverage at an acceptable cost once the reranker has already done the hard ranking work.

## Recommendation

If the performance losses remain modest while theme coverage improves, present diversification as a light screening extension rather than as part of the benchmark winner itself.
