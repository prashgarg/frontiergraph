# Ranker v3 Quality Layer Micro Results

## Scope

This is a first calibration pass for the new quality-layer features on a small historical slice, using the sampled corpus:

- corpus: `outputs/paper/73_method_v2_sampled_reranker_grid/hybrid_corpus_sample_5pct_seed42.parquet`
- anchor: `candidate_kind = causal_claim`
- family: `path_to_direct`
- scope: `broad`

This is not yet the full paper-grade rerun. It is a fast historical check on whether the new quality features look directionally useful.

## 1. Transparent-model tuning result

The transparent model was tuned on a micro historical slice:

- cutoff years: `2010`
- horizons: `5, 10`
- random weight trials: `6`

Saved outputs:

- `outputs/paper/80_quality_layer_path_to_direct/transparent_tuning_micro/best_config.yaml`
- `outputs/paper/80_quality_layer_path_to_direct/transparent_tuning_micro/ablation_grid.csv`
- `outputs/paper/80_quality_layer_path_to_direct/transparent_tuning_micro/win_loss_summary.md`

### Tuned transparent weights

- `transparent_weight_support_strength = 0.276348`
- `transparent_weight_opportunity = 0.189756`
- `transparent_weight_specificity = 0.177306`
- `transparent_weight_resolution = 0.149557`
- `transparent_weight_mediator_specificity = 0.051948`
- `transparent_weight_provenance = 0.049208`
- `transparent_weight_topology = 0.105878`

### Tuned subfamily bonuses

- `transparent_bonus_fully_open_frontier = -0.018908`
- `transparent_bonus_contextual_to_ordered = +0.064961`
- `transparent_bonus_ordered_to_causal = -0.017813`
- `transparent_bonus_causal_to_identified = +0.036876`
- `transparent_bonus_ordered_direct_to_path = -0.046681`
- `transparent_bonus_causal_direct_to_path = -0.010272`
- `transparent_bonus_identified_direct_to_path = -0.047501`

### Interpretation

The tuned transparent model puts most mass on:

- support strength
- opportunity
- specificity
- endpoint resolution

It gives a smaller but non-zero role to mediator specificity, and relatively little to provenance and topology.

The most notable subfamily result is that the tuning prefers:

- positive bonuses for anchored progression:
  - `contextual_to_ordered`
  - `causal_to_identified`
- mild negative bonuses for the other categories, especially direct-to-path buckets in this path-to-direct run

### Performance result

Despite that reasonable shape, the tuned transparent model did **not** beat preferential attachment on this tiny sampled micro slice.

That is an important result. It suggests:

- the new quality-layer features are probably not enough as a standalone transparent fix
- but they may still be valuable as inputs to the learned reranker

## 2. Learned-reranker comparison result

I then ran a micro reranker comparison using the tuned transparent config above.

Run:

- cutoff years: `2005, 2010`
- horizons: `5, 10`
- pool size: `5000`
- feature families:
  - `family_aware_composition`
  - `family_aware_boundary_gap`
  - `quality`
  - `family_aware_quality`

Saved outputs:

- `outputs/paper/80_quality_layer_path_to_direct/reranker_tuning_sample5pct_2005_2010/tuning_best_configs.csv`
- `outputs/paper/80_quality_layer_path_to_direct/reranker_tuning_sample5pct_2005_2010/tuning_summary.csv`
- `outputs/paper/80_quality_layer_path_to_direct/reranker_tuning_sample5pct_2005_2010/tuning_summary.md`

Important interpretation note:

- `family_aware_quality` is the explicit new quality-family challenger
- `family_aware_boundary_gap` now also contains the quality-layer features, because the boundary-gap family was extended on top of the new quality block

So the clean comparison is not “old versus new.” It is:

- composition baseline
- explicit quality family
- quality-plus-boundary family

## 3. Best reranker by horizon on this micro run

### `h = 5`

Best:

- `glm_logit + family_aware_composition`
- `alpha = 0.05`

Metrics:

- `MRR = 0.014218`
- `Recall@100 = 0.148148`

Close alternatives:

- `glm_logit + family_aware_quality`
- `glm_logit + family_aware_boundary_gap`

These were extremely close.

### `h = 10`

Best under the tuning script’s selection rule:

- `glm_logit + family_aware_composition`
- `alpha = 0.20`

Metrics:

- `MRR = 0.014176`
- `Recall@100 = 0.084746`

But the top table shows an important nuance:

- `glm_logit + family_aware_quality` has higher `MRR` at some settings
- it loses on `Recall@100`
- the current selection rule still prefers the composition family

## 4. What this means

The first-pass conclusion is:

1. The new quality features look sensible.
2. They are not enough to rescue the transparent model on their own.
3. They are more promising inside the learned reranker.
4. But on this micro sampled run they do **not yet clearly displace** `family_aware_composition` as the default feature family.

The strongest interpretation is:

- quality-layer features should stay in the stack
- they should probably be treated as additional reranker inputs
- but we should not yet replace the current default reranker family on the basis of this micro run alone

## 5. Centrality and novelty takeaway

The current implementation used:

- degree-like support centrality
- incident counts
- node age

It did **not** use PageRank or eigenvector centrality in the first pass.

That still looks like the right order.

These simple historical features already give us:

- endpoint broadness
- mediator genericness
- concept age / novelty

without making the model much harder to explain.

## Bottom line

The new quality layer is directionally useful, especially for reranking, but the current evidence says:

- keep `family_aware_composition` as the default until a larger rerun says otherwise
- keep `family_aware_quality` as the main challenger
- keep the tuned transparent weights as a starting point, not as a finished paper-grade replacement
