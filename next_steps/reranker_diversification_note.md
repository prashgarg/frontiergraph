# Reranker Diversification Note

## Question

Can a light diversification layer widen idea coverage on the historical reranker benchmark without giving back the rescued benchmark performance?

## Horizon 5
- diversified reranker precision@100: `0.218`
- diversified reranker recall@100: `0.067098`
- diversified reranker MRR: `0.006583`
- delta precision@100 vs undiversified reranker: `+0.014`
- delta recall@100 vs undiversified reranker: `+0.003264`
- delta MRR vs undiversified reranker: `+0.000040`
- still beats strong transparent baselines on precision@100: degree_recency, pref_attach, directed_closure
- still beats strong transparent baselines on recall@100: degree_recency, pref_attach, directed_closure
- still beats strong transparent baselines on MRR: none
- mean top-50 theme-pair gain: `4.20`
- mean top-100 top-target share delta: `-0.006`

## Horizon 10
- diversified reranker precision@100: `0.372`
- diversified reranker recall@100: `0.057587`
- diversified reranker MRR: `0.006366`
- delta precision@100 vs undiversified reranker: `-0.020`
- delta recall@100 vs undiversified reranker: `-0.002969`
- delta MRR vs undiversified reranker: `-0.000091`
- still beats strong transparent baselines on precision@100: degree_recency, pref_attach, directed_closure
- still beats strong transparent baselines on recall@100: degree_recency, pref_attach, directed_closure
- still beats strong transparent baselines on MRR: degree_recency, pref_attach, directed_closure
- mean top-50 theme-pair gain: `4.60`
- mean top-100 top-target share delta: `-0.038`

## Interpretation

This is a post-ranking screening layer, not a new benchmark model. The right question is whether it widens idea coverage at an acceptable cost once the reranker has already done the hard ranking work.

## Recommendation

If the performance losses remain modest while theme coverage improves, present diversification as a light screening extension rather than as part of the benchmark winner itself.
