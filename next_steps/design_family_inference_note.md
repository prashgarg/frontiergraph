# Design Family Inference Note

## Scope

This note reviews:

- `outputs/paper/34_design_family_inference_review/summary.json`
- `next_steps/reviewed_design_family_overrides.csv`

The goal is to record the stable post-integration state of the design-family layer after the residual semantics freeze pass.

## Main result

The design-family inference queue remains fully absorbed.

Current counts are:

- `reviewed_design_family_override_rows`: `13`
- `design_family_inference_rows`: `0`
- `design_family_manual_review_needed`: `0`

And the key acceptance check still holds:

- the `13` reviewed design-family pairs are absent from `data/processed/ontology_vnext_proto_v1/evidence_unknown_audit.parquet`

## What this means

The design-family recovery work is now complete for the reviewed queue.

At this point the right interpretation is:

- reviewed design-family overrides are part of the stable internal evidence layer
- future changes should come through new reviewed overrides
- not through reopening the old provisional inference pass

## Current judgment

Treat ontology-vNext as **frozen except for future reviewed override tables**.

That means:

- keep the `13` reviewed design-family overrides in place
- do not reopen them unless new evidence changes the preferred classification
- do not expand heuristic design-family growth just to create new queue activity

## Recommendation

Use this layer as settled internal support for:

- routed evidence-type expansion
- shortlist interpretation
- paper-facing methods description
