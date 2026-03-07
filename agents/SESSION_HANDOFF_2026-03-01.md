# Session Handoff (2026-03-01)

## Project Context
- Repo: `frontiergraph` pipeline + analysis stack for the FrontierGraph metascience paper and beta product.
- Core data in use: `data/processed/corpus_causalclaims.parquet` and related outputs.
- Objective in this phase: move from generic tuning to substantive, decision-gated analysis against strong baseline (`pref_attach`).

## What Was Completed

### 1) New substantive analysis modules (implemented + run)
- Added:
  - `src/analysis/attention_allocation.py`
  - `src/analysis/impact_weighted_eval.py`
  - `src/analysis/gap_boundary.py`
  - `src/analysis/external_transfer_design.py`
  - `src/analysis/expert_validation_pack.py`
  - `src/analysis/prospective_challenge.py`
  - `src/analysis/ranking_utils.py` (shared utilities)
- Outputs generated:
  - `outputs/paper/07_attention_allocation/*`
  - `outputs/paper/08_impact_weighted/*`
  - `outputs/paper/09_gap_boundary/*`
  - `outputs/paper/10_external_transfer_design/*`
  - `outputs/paper/11_expert_validation/*`
  - `outputs/paper/12_prospective_challenge/*`

### 2) Targeted retune (long-horizon + boundary objective)
- Added:
  - `src/analysis/targeted_model_search.py`
- Ran targeted search and produced:
  - `outputs/paper/03_model_search_targeted/*`
- `outputs/paper/03_model_search/best_config.yaml` was overwritten during targeted run.
- Reran evaluations with targeted config:
  - `outputs/paper/07_attention_allocation_targeted/*`
  - `outputs/paper/08_impact_weighted_targeted/*`
  - `outputs/paper/09_gap_boundary_targeted/*`
- Comparison artifacts:
  - `outputs/paper/03_model_search_targeted/retune_comparison.md`

### 3) Constrained reranker implementation
- Added boundary-aware reranker support:
  - `src/analysis/constrained_reranker_search.py`
  - `CandidateBuildConfig` extended in `src/analysis/common.py` with:
    - `boundary_bonus`
    - `boundary_quota`
    - `boundary_quota_max_rank`
  - boundary quota reranking logic in `src/analysis/ranking_utils.py` via `apply_boundary_rerank(...)`
- Fast constrained search completed:
  - `outputs/paper/03_model_search_constrained_fast/*`
- Fast constrained result: no feasible trial under constraints in that small grid.

### 4) Tests and docs
- Added substantive tests:
  - `tests/test_substantive_analysis_modules.py`
- Current test status:
  - `python -m pytest -q` -> `13 passed`
- README updated with new CLI commands, including targeted and constrained searches.

## Key Results So Far (Intuition)
- Generic/targeted weight tuning improved some overall deltas but did not reliably clear the `pref_attach` bar at top-100.
- Boundary-aware fast constrained run improved boundary deltas in evaluation summary but still had slightly negative overall deltas, so constraints were not met.
- Conclusion: need medium search before deciding whether no feasible operating point exists.

## Condensed Chat History / Decision Trail
- User requested "think big" substantive roadmap and asked to execute all priorities.
- We implemented and ran workstreams `07`-`12`.
- User approved deeper optimization.
- We implemented targeted retune and reran evaluations.
- User asked what next; recommendation: constrained reranker with decision gates.
- User asked for smaller/faster run and intuitive explanation; we executed fast constrained run.
- User asked to store handoff in `agents/` for later resume.

## Where To Pick Up Next (Exact)

### Immediate next step
Run a medium constrained grid (do not overwrite default config yet):

```bash
python -m src.analysis.constrained_reranker_search --corpus data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml --best_config outputs/paper/03_model_search/best_config.yaml --targeted_trials outputs/paper/03_model_search_targeted/targeted_trials.csv --top_weight_trials 8 --years 1980 1985 1990 1995 2000 2005 2008 --horizons 5,10,15 --k_ref 100 --boundary_bonus_grid 0 0.02 0.05 0.1 0.15 --boundary_quota_grid 0 0.05 0.1 0.15 0.2 --quota_max_rank 1000 --min_overall_pass_horizons 2 --min_boundary_pass_horizons 1 --out outputs/paper/03_model_search_constrained_medium
```

### If feasible trial exists
1. Re-run:
   - `07_attention_allocation` (to `_constrained_medium`)
   - `08_impact_weighted_eval` (to `_constrained_medium`)
   - `09_gap_boundary` (to `_constrained_medium`)
2. Produce before/after comparison table vs:
   - baseline run (`07/08/09`)
   - targeted run (`07/08/09_targeted`)
3. Apply paper decision gate:
   - If constraints pass -> "predictive + boundary-aware" narrative.
   - Else -> "transparent diagnostic frontier" narrative.

## Notes for Resume
- `best_config.yaml` currently reflects targeted retune, not original baseline defaults.
- Fast constrained run outputs are available for quick sanity check before medium run.
- Machine time estimate:
  - medium grid likely much longer than fast run on this laptop.
