# Sink Regularizer Calibration Note

We calibrated a small family of target-sink regularizers on held-out cutoff years rather than choosing one penalty by hand.

Selection rule:
- compute walk-forward held-out performance for each regularizer setting
- treat baseline performance variation across cutoffs as the tolerance band
- keep only settings within roughly one baseline SEM on MRR, Recall@100, and Precision@100
- among those, choose the configuration with the lowest top-100 endpoint concentration

Practical note:
- there are only `4` held-out cutoff cells per horizon in this sweep, so the SEM bands are informative but not razor-tight
- the rule should be read as "stay within normal held-out variation, then minimize concentration", not as a proof that one exact constant is uniquely correct

## Horizon 5
- recommended config: `s0.9950_ls0.0060_w300_rl0.0045_rn0.0015`
- sink start percentile: `0.9950`
- sink lambda: `0.0060`
- diversify window: `300`
- repeat log lambda: `0.0045`
- repeat linear lambda: `0.0015`
- baseline mean MRR: `0.009567`
- baseline mean Recall@100: `0.089134`
- baseline mean Precision@100: `0.155000`
- tuned mean MRR: `0.008118`
- tuned mean Recall@100: `0.081779`
- tuned mean Precision@100: `0.162500`
- tuned mean HHI@100: `0.037100`
- tuned mean top-target share@100: `0.097500`
- tuned mean unique targets@100: `52.50`

Current-frontier effect with the recommended config:
- top-20 unique endpoints: `4 -> 19`
- top-100 unique endpoints: `34 -> 56`
- top-20 top-target share: `0.45 -> 0.10`
- top-100 top-target share: `0.24 -> 0.05`
- WTP top-20 / top-100: `9 / 15 -> 1 / 5`
- Economic Growth top-20 / top-100: `9 / 24 -> 1 / 4`

## Horizon 10
- recommended config: `s0.9950_ls0.0060_w300_rl0.0045_rn0.0015`
- sink start percentile: `0.9950`
- sink lambda: `0.0060`
- diversify window: `300`
- repeat log lambda: `0.0045`
- repeat linear lambda: `0.0015`
- baseline mean MRR: `0.006223`
- baseline mean Recall@100: `0.079931`
- baseline mean Precision@100: `0.295000`
- tuned mean MRR: `0.005997`
- tuned mean Recall@100: `0.068461`
- tuned mean Precision@100: `0.285000`
- tuned mean HHI@100: `0.035000`
- tuned mean top-target share@100: `0.090000`
- tuned mean unique targets@100: `51.50`

Current-frontier effect with the recommended config:
- top-20 unique endpoints: `9 -> 16`
- top-100 unique endpoints: `25 -> 47`
- top-20 top-target share: `0.35 -> 0.10`
- top-100 top-target share: `0.24 -> 0.06`
- WTP top-20 / top-100: `3 / 17 -> 1 / 6`
- Economic Growth top-20 / top-100: `7 / 24 -> 1 / 6`
