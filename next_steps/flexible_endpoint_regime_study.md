# Flexible Endpoint Regime Study

This study is intended to learn reusable endpoint regimes rather than hand-patch individual ontology nodes.

## Coverage

- broad screen endpoints (`mapped_total_freq >= 300`): `989`
- study-universe endpoints: `426`

## Regime counts within study universe

- `monitor`: `347`
- `study_subfamily_candidate`: `52`
- `regularize_only`: `21`
- `canonicalize_only`: `4`
- `canonicalize_and_regularize`: `2`

## Representative examples

### canonicalize_and_regularize
- `Willingness to Pay.` | sink_pct=0.999, tuned_top100=14, canonical_members=1, significant_clusters=1, dominant_cluster_share=0.462
- `Technological Innovation.` | sink_pct=0.988, tuned_top100=6, canonical_members=1, significant_clusters=1, dominant_cluster_share=0.554

### canonicalize_only
- `Uncertainty.` | sink_pct=0.983, tuned_top100=0, canonical_members=1, significant_clusters=1, dominant_cluster_share=0.584
- `Decision Making` | sink_pct=0.853, tuned_top100=0, canonical_members=1, significant_clusters=0, dominant_cluster_share=0.070
- `Exchange Rate Regime` | sink_pct=0.809, tuned_top100=0, canonical_members=1, significant_clusters=1, dominant_cluster_share=0.496
- `Incomplete Markets.` | sink_pct=0.000, tuned_top100=0, canonical_members=1, significant_clusters=1, dominant_cluster_share=0.269

### regularize_only
- `R&D` | sink_pct=1.000, tuned_top100=8, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.678
- `Firms` | sink_pct=0.997, tuned_top100=4, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.407
- `Spillover Effect` | sink_pct=0.996, tuned_top100=4, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.623
- `Human Capital` | sink_pct=0.993, tuned_top100=4, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.621
- `GDP` | sink_pct=0.991, tuned_top100=6, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.730
- `Housing Prices` | sink_pct=0.991, tuned_top100=5, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.584
- `Stock Returns` | sink_pct=0.991, tuned_top100=6, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.776
- `Environmental quality` | sink_pct=0.985, tuned_top100=6, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.772

### study_subfamily_candidate
- `Consumption` | sink_pct=0.996, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.351
- `Efficiency` | sink_pct=0.988, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.099
- `Inflation` | sink_pct=0.986, tuned_top100=2, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.547
- `Resource allocation` | sink_pct=0.982, tuned_top100=0, canonical_members=0, significant_clusters=3, dominant_cluster_share=0.106
- `Production efficiency` | sink_pct=0.981, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.257
- `economic behavior` | sink_pct=0.976, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.273
- `Technical progress` | sink_pct=0.975, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.399
- `Interest Rates` | sink_pct=0.969, tuned_top100=0, canonical_members=0, significant_clusters=2, dominant_cluster_share=0.220

### monitor
- `Economic Growth` | sink_pct=1.000, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.773
- `Innovation` | sink_pct=0.999, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.621
- `Productivity` | sink_pct=0.998, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.613
- `Spillovers` | sink_pct=0.998, tuned_top100=2, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.649
- `Employment` | sink_pct=0.997, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.491
- `Investment` | sink_pct=0.995, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.287
- `Wage` | sink_pct=0.995, tuned_top100=2, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.560
- `Diversification` | sink_pct=0.994, tuned_top100=0, canonical_members=0, significant_clusters=1, dominant_cluster_share=0.601

## Interpretation

- `canonicalize_and_regularize` captures duplicate-identity endpoints that remain flexible sinks after tuning.
- `regularize_only` captures broad valid endpoints that are concentration-prone but not clearly multi-family.
- `study_subfamily_candidate` is a learning label, not an automatic promotion instruction.
- endpoints stay in `monitor` when they are broad but do not yet show a structural reason for stronger intervention.

## What Generalizes

- duplicate identity and sink behavior are separable problems, and the regime table distinguishes them cleanly
- not all broad sink endpoints are split candidates
- not all split candidates are good ontology-child candidates

The last point matters. The `study_subfamily_candidate` regime includes:

- substantive families such as `Consumption`, `Energy Consumption`, `Financial Stability`, and `Bilateral trade`
- but also generic or method-heavy containers such as `Estimation`, `Time Series`, `Forecasting Returns`, and `Optimal decision`

So the general lesson is:

- multi-cluster modifier structure is a necessary clue for possible splitting
- but it is not sufficient on its own to justify ontology promotion

## Guardrail We Should Add Next

Before promoting any child families from the `study_subfamily_candidate` regime, we should add a second-stage guardrail that distinguishes:

- substantive concept families
- method containers
- generic decision / behavior containers
- contextual buckets

That keeps this workflow generalizable beyond economics and avoids turning structural heterogeneity into indiscriminate ontology growth.

## Caution

This table is intended to guide generalized ontology policy, not to justify endpoint-specific patches.
Any later promotion of child families should require a separate rule-based review over the `study_subfamily_candidate` regime.
