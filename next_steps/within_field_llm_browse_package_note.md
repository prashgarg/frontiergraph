# Within-Field LLM Browse Package

Date: 2026-04-11

The first packaged within-field LLM browse object now exists at:

- `outputs/paper/111_within_field_llm_browse_package`

Inputs:

- endpoint-first within-field package:
  - `outputs/paper/98_objective_specific_frontier_packages_endpoint_first/within_field_top100_pool2000/package.csv`
- LLM rerank analysis package:
  - `outputs/paper/110_llm_screening_within_field_v3_analysis/within_field_llm_reranked_package.csv`

Workflow:

1. start from the endpoint-first within-field shelves
2. apply weak veto from prompt `E`
3. rerank survivors using repeated pairwise within-field consensus from prompt `H`
4. use prompt `G` only as a secondary diagnostic and tie-breaker

Package outputs:

- `package.csv`
- `package.parquet`
- `top20.csv`
- `summary.csv`
- `top20_compare.csv`
- `summary.md`
- `manifest.json`

This is the first browse-ready LLM product.

Important interpretation:

- it is a current-frontier cleanup layer
- it is not a historical benchmark object
- it is a within-field browse object, not a single global shortlist
