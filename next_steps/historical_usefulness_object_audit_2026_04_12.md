# Historical usefulness object audit

## Main finding

The historical LLM usefulness pack was much thinner than it appeared. It did not
contain rendered path or mediator detail. In practice, the model was usually
judging endpoint pairs plus a short generic note rather than a fully readable
path-supported or mechanism-thickening question object.

## What the data show

- Selected historical LLM pack: `12,750` rows
- Rows with non-empty `focal_mediator_label`: `0`
- Rows with non-empty `top_mediators_json`: `0`
- Rows with non-empty `top_paths_json`: `0`
- Rows with non-empty `compressed_triplet_json` carrying a real mediator/path object: effectively `0`

The same all-zero pattern also holds in the saved historical feature panels used
to construct the pack.

## Why this happened

### Path-to-direct

The widened historical benchmark panel was built with `include_details=False`.
That preserves the score-bearing historical object, but suppresses the
human-readable detail fields needed for a usefulness screen.

### Direct-to-path

The direct-to-path historical object is endpoint-centered by construction in the
benchmark layer. The saved historical panel therefore does not itself carry a
readable proposed path object, even when the surrounding support neighborhood can
often supply one.

## What is stale in the paper

The appendix LLM usefulness prose was stronger than the underlying object
deserved. The manuscript has therefore been softened so the LLM screen is now
described as a coarse screening check rather than a precise ranking result.

The small human exercise is not the same problem. It was built from the richer
current frontier and already includes a readable triplet-style object.

## Fix

1. Rebuild the path-to-direct widened historical panel with `include_details=True`.
2. Verify that the ranking metrics do not materially change.
3. Regenerate the path-to-direct historical usefulness pack from that detail-on panel.
4. Build a family-aware readable question-object layer for direct-to-path:
   - existing direct relation
   - proposed support path or bridge
   - rendered question
5. Regenerate the direct-to-path historical usefulness pack from that readable layer.

## Expected interpretation after the fix

After the rerun, the LLM screen should be read as a workflow layer:

- graph and reranker ask whether a question is historically grounded
- the usefulness screen asks whether the rendered question looks interpretable and non-artifactual

It should remain secondary to the historical benchmark.
