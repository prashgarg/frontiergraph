# Method v2 Concentration Selection

Family: `path_to_direct`

Selection rule:
1. keep only variants with non-negative mean Recall@100 and mean MRR relative to the unregularized reranker
2. among those, choose the lowest mean top-target share@100
3. tie-break with highest mean unique theme-pair keys@100
4. final tie-break prefers diversification only

## Horizon 5
- chosen variant: `sink_plus_diversification`
- config id: `s0.9950_ls0.0000_w300_rl0.0045_rn0.0015`
- mean precision@100: `0.150000`
- mean recall@100: `0.096269`
- mean MRR: `0.008248`
- mean unique theme-pair keys@100: `22.00`
- mean unique semantic-family keys@100: `100.00`
- mean top-target share@100: `0.113333`
- delta recall@100 vs base: `+0.010508`
- delta MRR vs base: `+0.000375`

## Horizon 10
- chosen variant: `diversification_only`
- config id: `diversification_only_w300`
- mean precision@100: `0.320000`
- mean recall@100: `0.092718`
- mean MRR: `0.007958`
- mean unique theme-pair keys@100: `27.67`
- mean unique semantic-family keys@100: `100.00`
- mean top-target share@100: `0.226667`
- delta recall@100 vs base: `+0.018295`
- delta MRR vs base: `+0.000444`

## Horizon 15
- chosen variant: `sink_plus_diversification`
- config id: `s0.9975_ls0.0040_w300_rl0.0045_rn0.0015`
- mean precision@100: `0.376667`
- mean recall@100: `0.079090`
- mean MRR: `0.007173`
- mean unique theme-pair keys@100: `22.00`
- mean unique semantic-family keys@100: `100.00`
- mean top-target share@100: `0.126667`
- delta recall@100 vs base: `+0.005555`
- delta MRR vs base: `+0.000125`

