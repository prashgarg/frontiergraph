# Path-length axis constraints

This note records what the current code supports as of the current parity pass,
before we run the second design axis.

## Current state

The paper configuration exposes `max_path_len`, but the implementation is not
fully general.

- In [src/analysis/common.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src/analysis/common.py), `CandidateBuildConfig` defaults to `max_path_len = 2`.
- In [src/features_paths.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src/features_paths.py), explicit support is now implemented for:
  - length-2 paths
  - bounded length-3 paths
  - bounded length-4 paths
  - bounded length-5 paths
- The longer lengths use a tighter bounded DFS on top-weighted outgoing
  neighbors. So `max_len = 4` and `5` are now real ranking-layer settings, but
  they are more heavily pruned than the length-2 construction.

So for the transparent support features, the code currently means:

- `max_path_len = 2` -> length-2 only
- `max_path_len = 3` -> length-2 plus length-3
- `max_path_len = 4` -> length-2, length-3, and bounded length-4
- `max_path_len = 5` -> length-2, length-3, bounded length-4, and bounded
  length-5

## Direct-to-path event definition

The direct-to-path historical event is also not fully general yet.

- In [src/research_allocation_v2.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src/research_allocation_v2.py), `first_path_appearance_map_v2` and `first_path_appearance_map_for_pairs_v2`
  detect first path emergence by updating `(u, b)` and `(a, v)` when a new edge
  `(a, b)` arrives.
- That is a clean incremental construction for the first appearance of a
  length-2 path.
- It is not a general first-appearance map for arbitrary path lengths.

This matters because a path-length experiment has two layers:

1. support used by the ranking rule
2. historical event used for validation

At the moment, the ranking layer can be extended more easily than the direct-to-path
historical event layer.

## Implication for the second design axis

There are now two honest ways to proceed.

### Option 1. Immediate descriptive axis

Run the path-length comparison first for `path-to-direct`, where the historical
event is still direct closure and the changed object is the support structure.

That lets us compare:

- length-2 support only
- length-2 plus length-3 support
- bounded length-4 support
- bounded length-5 support

without simultaneously changing the historical event definition.

### Option 2. Full two-family path-length axis

Extend both:

- `compute_path_features` to length 4 and 5
- direct-to-path path-emergence maps to longer-path first appearance

Then rerun both families.

This is the conceptually clean full version, but it is materially more work.

## Recommendation

Use a staged path-length design:

1. run the path-length axis first on `path-to-direct`
2. decide whether the direct-to-path historical event should stay length-2 for a
   clean benchmark, or whether we want a second-wave extension with longer path
   emergence

That keeps the next experiment interpretable while still letting us study what
happens when the ranking layer looks beyond the obvious two-step channel.
