# Path-Length Axis: Sequential Execution

Date: 12 April 2026

## Goal

Run the path-length axis in an auditable sequence rather than all at once.

Order:

1. `max_path_len = 2`
2. `max_path_len = 3`
3. `max_path_len = 4`
4. `max_path_len = 5`

## Why sequential

- lets us inspect results after each completed length
- avoids unnecessary CPU contention
- keeps failures localized
- makes it easier to compare whether longer support paths are helping before committing to the full axis

## Output root

- `outputs/paper/166_path_length_axis_sequential`

Each run writes into:

- `len_2`
- `len_3`
- `len_4`
- `len_5`

## Current run

First run:

- family: `path_to_direct`
- scope: `broad`
- max path length: `2`
- includes:
  - initial widened benchmark
  - reranker tuning
  - tuned widened benchmark

## Reporting rule

After each completed length:

1. read the benchmark summary
2. read the best tuning configs
3. refresh the axis summary artifacts
4. decide whether to proceed to the next length
