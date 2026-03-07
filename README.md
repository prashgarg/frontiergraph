# Missing Claims

Domain-agnostic missing-claim recommender and Streamlit webtool built from claim graphs.

## What It Does

- Builds a normalized claim corpus from adapters (`demo`, `causalclaims`, `generic`).
- Computes three transparent signals for missing claims:
  - underexplored concept-pair gaps,
  - path-implied missing direct edges,
  - motif completion (open triads).
- Scores and ranks candidates with score decomposition.
- Backtests retrospectively for horizons 1/3/5 years.
- Stores outputs in SQLite for a lightweight Streamlit UI.

## Quickstart

Install dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run the default $0 pipeline with demo data:

```bash
python -m src.build_corpus --adapter demo --out data/processed/corpus.parquet --config config/config.yaml
python -m src.features_pairs --in data/processed/corpus.parquet --out data/processed/pairs.parquet --tau 2
python -m src.features_paths --in data/processed/corpus.parquet --out data/processed/missing_edges.parquet --max_len 2
python -m src.features_motifs --in data/processed/corpus.parquet --out data/processed/motif_gaps.parquet
python -m src.scoring --pairs data/processed/pairs.parquet --paths data/processed/missing_edges.parquet --motifs data/processed/motif_gaps.parquet --out data/processed/candidates.parquet
python -m src.backtest --corpus data/processed/corpus.parquet --out outputs/tables/backtest.parquet --figdir outputs/figures
python -m src.store_sqlite --corpus data/processed/corpus.parquet --candidates data/processed/candidates.parquet --out data/processed/app.db
streamlit run app/streamlit_app.py
```

Cleaner launcher after `pip install -e '.[dev]'`:

```bash
economics-ranker
```

Useful options:

```bash
economics-ranker --db data/processed/app_causalclaims.db
economics-ranker --port 8502
economics-ranker --headless
```

No-terminal launcher on macOS:

- Double-click `launchers/Economics Opportunity Ranker.app`
- If Python 3.9+ is not installed yet, the launcher opens the Python download page.

## Public Beta Deployment

Stage 1 deployment assets now live in:

- `Dockerfile`
- `cloudbuild.yaml`
- `scripts/deploy_cloud_run.sh`
- `scripts/upload_ranker_db_to_gcs.sh`
- `deploy/public_beta.env.example`
- `site/`

Recommended public beta architecture:

- static landing page on Cloudflare Pages
- interactive app on Google Cloud Run
- economics SQLite database mounted read-only from Google Cloud Storage

See `deploy/PUBLIC_BETA.md` for the exact setup flow.

## Optional CausalClaims Adapter

```bash
python -m src.build_corpus --adapter causalclaims --out data/processed/corpus.parquet --config config/config.yaml
```

The adapter tries to clone:

`https://github.com/prashgarg/CausalClaimsInEconomics`

If unavailable/materialization fails, it falls back to the demo dataset.

Then run the same feature/scoring/backtest/storage commands against that corpus.

For larger corpora, tune `features.max_neighbors_per_mediator` in `config/config.yaml` to control runtime in path/motif computations and backtests.

Production CausalClaims run (recommended file names):

```bash
python -m src.build_corpus --adapter causalclaims --out data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml
python -m src.features_pairs --in data/processed/corpus_causalclaims.parquet --out data/processed/pairs_causalclaims.parquet --tau 2
python -m src.features_paths --in data/processed/corpus_causalclaims.parquet --out data/processed/missing_edges_causalclaims.parquet --max_len 2 --max_neighbors_per_mediator 120
python -m src.features_motifs --in data/processed/corpus_causalclaims.parquet --out data/processed/motif_gaps_causalclaims.parquet --max_neighbors_per_mediator 120
python -m src.scoring --pairs data/processed/pairs_causalclaims.parquet --paths data/processed/missing_edges_causalclaims.parquet --motifs data/processed/motif_gaps_causalclaims.parquet --out data/processed/candidates_causalclaims.parquet --config config/config_causalclaims.yaml
python -m src.backtest --corpus data/processed/corpus_causalclaims.parquet --out outputs/tables/backtest_causalclaims.parquet --figdir outputs/figures --resume --verbose --config config/config_causalclaims.yaml
python -m src.store_sqlite --corpus data/processed/corpus_causalclaims.parquet --candidates data/processed/candidates_causalclaims.parquet --out data/processed/app_causalclaims.db --config config/config_causalclaims.yaml
```

## Optional LLM Extractor (OFF By Default)

Estimate-only mode (no spend):

```bash
python -m src.adapters.llm_extractor_adapter --in data/raw/custom_docs.jsonl --out data/processed/corpus_llm.parquet --estimate_cost
```

Execution mode (requires explicit spend permission via flag):

```bash
python -m src.adapters.llm_extractor_adapter --in data/raw/custom_docs.jsonl --out data/processed/corpus_llm.parquet --estimate_cost --execute
```

## Tests

```bash
python -m pytest -q
```

## Paper Analysis CLIs

```bash
python -m src.analysis.eval_stats --backtest outputs/tables/backtest_causalclaims.parquet --out outputs/paper/02_eval
python -m src.analysis.model_search --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --out outputs/paper/03_model_search
python -m src.analysis.vintage_exercise --corpus data/processed/corpus_causalclaims.parquet --years 1990 2000 2010 2015 --h 5 --out outputs/paper/04_vintage_exercise
python -m src.analysis.benchmark_enrichment --benchdir data/external/CausalClaimsInEconomics/analysis_data/core/benchmarks --corpus data/processed/corpus_causalclaims.parquet --candidates data/processed/candidates_causalclaims.parquet --out outputs/paper/05_benchmarks
python -m src.analysis.field_heterogeneity --corpus data/processed/corpus_causalclaims.parquet --candidates data/processed/candidates_causalclaims.parquet --out outputs/paper/06_findings
```

## Substantive Analysis CLIs (Workstreams 07-12)

```bash
python -m src.analysis.attention_allocation --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --years 1980 1985 1990 1995 2000 2005 2008 --horizons 3,5,10,15 --k_values 50 100 500 1000 --out outputs/paper/07_attention_allocation
python -m src.analysis.impact_weighted_eval --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --years 1980 1985 1990 1995 2000 2005 2008 --horizons 3,5,10,15 --k_values 50 100 500 1000 --out outputs/paper/08_impact_weighted
python -m src.analysis.gap_boundary --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --years 1980 1985 1990 1995 2000 2005 2008 --horizons 3,5,10,15 --max_k 1000 --k_values 100 500 1000 --out outputs/paper/09_gap_boundary
python -m src.analysis.external_transfer_design --backtest outputs/tables/backtest_causalclaims.parquet --out outputs/paper/10_external_transfer_design
python -m src.analysis.expert_validation_pack --corpus data/processed/corpus_causalclaims.parquet --candidates data/processed/candidates_causalclaims.parquet --n_per_arm 40 --seed 42 --out outputs/paper/11_expert_validation
python -m src.analysis.prospective_challenge --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --horizons 5,10 --k_values 100 500 --out outputs/paper/12_prospective_challenge
```

Targeted long-horizon/boundary retune (overwrites `best_config.yaml` if `--overwrite_best` is passed):

```bash
python -m src.analysis.targeted_model_search --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --years 1980 1985 1990 1995 2000 2005 2008 --horizons 5,10,15 --n_trials 90 --seed 42 --out outputs/paper/03_model_search_targeted --overwrite_best
```

Constrained boundary-aware reranker search (quota + score bonus for boundary candidates):

```bash
python -m src.analysis.constrained_reranker_search --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --targeted_trials outputs/paper/03_model_search_targeted/targeted_trials.csv --top_weight_trials 4 --years 1985 1995 2000 2005 2008 --horizons 5,10,15 --k_ref 100 --boundary_bonus_grid 0 0.05 --boundary_quota_grid 0 0.1 --quota_max_rank 1000 --min_overall_pass_horizons 2 --min_boundary_pass_horizons 1 --out outputs/paper/03_model_search_constrained_fast
```
