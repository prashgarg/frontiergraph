# Sink Regularizer Calibration Note

We calibrated a small family of target-sink regularizers on held-out cutoff years rather than choosing one penalty by hand.

Selection rule:
- compute walk-forward held-out performance for each regularizer setting
- treat baseline performance variation across cutoffs as the tolerance band
- keep only settings within roughly one baseline SEM on MRR, Recall@100, and Precision@100
- among those, choose the configuration with the lowest top-100 endpoint concentration

## Horizon 5
- recommended config: `s0.9950_ls0.0060_w300_rl0.0045_rn0.0015`
- sink start percentile: `0.9950`
- sink lambda: `0.0060`
- diversify window: `300`
- repeat log lambda: `0.0045`
- repeat linear lambda: `0.0015`
- baseline mean MRR: `0.007872`
- baseline mean Recall@100: `0.085761`
- baseline mean Precision@100: `0.146667`
- tuned mean MRR: `0.006642`
- tuned mean Recall@100: `0.098392`
- tuned mean Precision@100: `0.153333`
- tuned mean HHI@100: `0.049600`
- tuned mean top-target share@100: `0.113333`
- tuned mean unique targets@100: `43.00`

## Horizon 10
- recommended config: `s0.9975_ls0.0060_w300_rl0.0045_rn0.0015`
- sink start percentile: `0.9975`
- sink lambda: `0.0060`
- diversify window: `300`
- repeat log lambda: `0.0045`
- repeat linear lambda: `0.0015`
- baseline mean MRR: `0.007514`
- baseline mean Recall@100: `0.074423`
- baseline mean Precision@100: `0.266667`
- tuned mean MRR: `0.006805`
- tuned mean Recall@100: `0.070595`
- tuned mean Precision@100: `0.253333`
- tuned mean HHI@100: `0.046000`
- tuned mean top-target share@100: `0.110000`
- tuned mean unique targets@100: `45.33`

## Horizon 15
- recommended config: `s0.9950_ls0.0060_w300_rl0.0045_rn0.0015`
- sink start percentile: `0.9950`
- sink lambda: `0.0060`
- diversify window: `300`
- repeat log lambda: `0.0045`
- repeat linear lambda: `0.0015`
- baseline mean MRR: `0.007048`
- baseline mean Recall@100: `0.073535`
- baseline mean Precision@100: `0.343333`
- tuned mean MRR: `0.007330`
- tuned mean Recall@100: `0.078474`
- tuned mean Precision@100: `0.373333`
- tuned mean HHI@100: `0.058533`
- tuned mean top-target share@100: `0.130000`
- tuned mean unique targets@100: `40.33`

