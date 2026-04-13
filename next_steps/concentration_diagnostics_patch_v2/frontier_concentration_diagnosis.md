# Frontier Concentration Diagnosis

This note compares family and theme concentration across pipeline stages:
- underlying corpus
- recent corpus (`year >= 2016`)
- current transparent top 100
- current reranked top 100
- current surfaced top 100
- current cleaned shortlist top 100

## Environment/climate share across stages

- `corpus_all`: 3.5%
- `corpus_recent_2016`: 6.4%
- `h5_transparent_top100`: 5.0%
- `h5_reranker_top100`: 22.0%
- `h5_surface_top100`: 60.0%
- `h5_shortlist_top100`: 33.5%
- `h10_transparent_top100`: 5.0%
- `h10_reranker_top100`: 21.0%
- `h10_surface_top100`: 56.0%
- `h10_shortlist_top100`: 35.5%

## Top tracked families from the cleaned shortlist

- `carbon emissions` | corpus=0.65%, recent=1.22%, h5_short=12.50%, h10_short=12.50%
- `digital economy` | corpus=0.04%, recent=0.10%, h5_short=2.50%, h10_short=2.50%
- `energy consumption` | corpus=0.08%, recent=0.13%, h5_short=2.00%, h10_short=2.50%
- `environmental quality` | corpus=0.18%, recent=0.28%, h5_short=3.50%, h10_short=3.00%
- `financial development` | corpus=0.08%, recent=0.15%, h5_short=4.50%, h10_short=4.50%
- `green innovation` | corpus=0.05%, recent=0.10%, h5_short=5.00%, h10_short=6.00%
- `income tax rate` | corpus=0.02%, recent=0.02%, h5_short=3.50%, h10_short=3.50%
- `price changes` | corpus=0.03%, recent=0.02%, h5_short=2.50%, h10_short=3.00%
- `state of the business cycle` | corpus=0.03%, recent=0.03%, h5_short=6.50%, h10_short=6.00%
- `technological innovation` | corpus=0.06%, recent=0.12%, h5_short=3.00%, h10_short=4.00%
- `urbanization` | corpus=0.06%, recent=0.11%, h5_short=3.00%, h10_short=3.00%
- `willingness to pay` | corpus=0.28%, recent=0.33%, h5_short=6.50%, h10_short=5.50%

## Initial read

The key question is whether environment/climate families are already large in the corpus, become larger in the recent corpus, and then receive further amplification from reranking and shortlist cleanup.
The same decomposition can be used for other repeated families such as business-cycle, willingness-to-pay, green-innovation, and emissions-related objects.
