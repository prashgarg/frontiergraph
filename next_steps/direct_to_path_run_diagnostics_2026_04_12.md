# Direct-to-Path Run Diagnostics

Date: 2026-04-12

This note records why the first `direct-to-path` parity runs failed to produce usable
outputs, and what was changed before rerunning them.

## 1. What actually went wrong

Two different problems were present.

### A. Synced-file instability

The original runs read core inputs directly from the Dropbox-backed working tree:

- `data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet`
- `data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet`
- `outputs/paper/69_v2_2_effective_model_search/best_config.yaml`
- `outputs/paper/83_quality_confirm_path_to_direct_effective/adopted_surface_backtest_configs.csv`

Those reads were not stable. Small config files sometimes hung. The parquet sometimes
raised a footer error on one read and worked on the next. The file itself appears valid.
The problem looks like hydration or sync-path instability rather than a permanently bad
artifact.

### B. Direct-to-path event-map waste

The direct-to-path pipeline used to build a global historical path-emergence map for the
entire graph before it knew which candidate pairs would ever be evaluated.

That is much more expensive for `direct-to-path` than for `path-to-direct` because the
candidate event is path emergence, not direct-edge appearance. In the old probe, the
global map already exceeded `19 million` realized pairs by `1995`. That was the main
memory pressure.

## 2. What was changed

### A. Local staging for inputs

The reruns now read from local staged copies in `/tmp`:

- `/tmp/direct_to_path_hybrid_corpus.parquet`
- `/tmp/direct_to_path_hybrid_papers_funding.parquet`
- `/tmp/direct_to_path_best_config.yaml`
- `/tmp/direct_to_path_adopted_surface_backtest_configs.csv`

This leaves the underlying artifacts unchanged. It only removes sync-path instability.

### B. Progress logging

The main scripts now log:

- corpus and metadata loading
- candidate-family configuration
- feature-panel build start and row counts
- per-horizon and per-cutoff progress
- final output writes

The heavy internal builders now also log timing when `FG_TIMING=1`.

Files patched:

- `scripts/run_effective_benchmark_widened.py`
- `scripts/run_learned_reranker_tuning.py`
- `src/analysis/learned_reranker.py`
- `src/research_allocation_v2.py`

### C. Candidate-targeted direct-to-path event years

For `direct-to-path`, the feature-panel build now:

1. builds the cutoff-specific candidate tables first
2. collects the union of candidate pairs actually kept for evaluation
3. computes path-emergence years only for those candidate pairs

This preserves the target labels for evaluated pairs. It does not change the scoring
logic or the historical event definition.

## 3. Why this should not affect quality

The substantive object is unchanged.

- The graph is the same.
- Candidate generation is the same.
- Feature construction is the same.
- The realized event for each evaluated pair is the same.

The only change is that the code no longer computes realized path years for millions of
pairs that never enter the evaluation pool.

## 4. Probe evidence

Under the old global direct-to-path map:

- the realized-pair map had already reached about `19.2 million` pairs by `1995`
- memory use crossed roughly `2.7 GB` in a narrow probe

Under the candidate-targeted map in the same probe:

- target pairs: `2,026`
- realized target pairs found: `1,655`
- path-emergence map stage: about `49 seconds`
- total narrow panel build: about `65 seconds`
- memory use was materially lower

That is the relevant efficiency improvement.

## 5. Rerun protocol

Stage 1:

- run the widened `direct-to-path` benchmark from local staged inputs
- save `historical_feature_panel.parquet`
- keep `run.log`

Stage 2:

- run reranker tuning on the same staged inputs
- reuse Stage 1's `historical_feature_panel.parquet` through `--feature-panel`
- keep `run.log`

This is now the default protocol for the parity run.
