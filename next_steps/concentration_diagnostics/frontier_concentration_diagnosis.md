# Frontier Concentration Diagnosis

This note compares family and theme concentration across pipeline stages:
- underlying corpus
- recent corpus (`year >= 2016`)
- current transparent top 100
- current reranked top 100
- current surfaced top 100
- current cleaned shortlist top 100

## Environment/climate share across stages

- `corpus_all`: 3.1%
- `corpus_recent_2016`: 5.7%
- `h5_transparent_top100`: 8.0%
- `h5_reranker_top100`: 17.0%
- `h5_surface_top100`: 61.0%
- `h5_shortlist_top100`: 50.5%
- `h10_transparent_top100`: 8.0%
- `h10_reranker_top100`: 17.5%
- `h10_surface_top100`: 58.0%
- `h10_shortlist_top100`: 48.5%

## Top tracked families from the cleaned shortlist

- `carbon emissions` | corpus=0.41%, recent=0.84%, h5_short=14.50%, h10_short=14.50%
- `digital economy` | corpus=0.04%, recent=0.10%, h5_short=2.50%, h10_short=1.00%
- `energy consumption` | corpus=0.08%, recent=0.13%, h5_short=4.50%, h10_short=4.50%
- `environmental pollution` | corpus=0.03%, recent=0.06%, h5_short=3.50%, h10_short=3.50%
- `environmental quality` | corpus=0.07%, recent=0.11%, h5_short=4.00%, h10_short=4.00%
- `financial development` | corpus=0.08%, recent=0.15%, h5_short=4.00%, h10_short=4.00%
- `green innovation` | corpus=0.05%, recent=0.10%, h5_short=8.00%, h10_short=7.00%
- `income tax rate` | corpus=0.02%, recent=0.02%, h5_short=2.50%, h10_short=3.50%
- `price changes` | corpus=0.03%, recent=0.02%, h5_short=2.00%, h10_short=3.00%
- `renewable energy consumption` | corpus=0.09%, recent=0.20%, h5_short=3.00%, h10_short=3.00%
- `state of the business cycle` | corpus=0.03%, recent=0.03%, h5_short=6.50%, h10_short=8.50%
- `technological innovation` | corpus=0.06%, recent=0.12%, h5_short=4.50%, h10_short=3.00%
- `willingness to pay` | corpus=0.08%, recent=0.09%, h5_short=5.50%, h10_short=5.50%

## Initial read

The key question is whether environment/climate families are already large in the corpus, become larger in the recent corpus, and then receive further amplification from reranking and shortlist cleanup.
The same decomposition can be used for other repeated families such as business-cycle, willingness-to-pay, green-innovation, and emissions-related objects.
