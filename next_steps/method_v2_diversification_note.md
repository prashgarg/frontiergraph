# Reranker Diversification Note

## Question

Can a light diversification layer widen idea coverage on the historical reranker benchmark without giving back the rescued benchmark performance?

## Horizon 5
- diversified reranker precision@100: `0.160`
- diversified reranker recall@100: `0.092469`
- diversified reranker MRR: `0.007565`
- delta precision@100 vs undiversified reranker: `+0.007`
- delta recall@100 vs undiversified reranker: `+0.002407`
- delta MRR vs undiversified reranker: `+0.000408`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `6.33`
- mean top-100 top-target share delta: `-0.160`

## Horizon 10
- diversified reranker precision@100: `0.313`
- diversified reranker recall@100: `0.089655`
- diversified reranker MRR: `0.007196`
- delta precision@100 vs undiversified reranker: `+0.053`
- delta recall@100 vs undiversified reranker: `+0.015200`
- delta MRR vs undiversified reranker: `+0.000498`
- still beats strong transparent baselines on precision@100: not evaluated in this pass
- still beats strong transparent baselines on recall@100: not evaluated in this pass
- still beats strong transparent baselines on MRR: not evaluated in this pass
- mean top-50 theme-pair gain: `6.00`
- mean top-100 top-target share delta: `-0.250`

## Interpretation

This is a post-ranking screening layer, not a new benchmark model. The right question is whether it widens idea coverage at an acceptable cost once the reranker has already done the hard ranking work.

## Recommendation

If the performance losses remain modest while theme coverage improves, present diversification as a light screening extension rather than as part of the benchmark winner itself.
