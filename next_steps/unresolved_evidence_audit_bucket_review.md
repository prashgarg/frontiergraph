# Unresolved Evidence Audit Bucket Review

## Scope

This note reviews the new `audit_bucket` split added to `evidence_unknown_audit.parquet`.

Allowed buckets:

- `method_artifact`
- `metadata_container`
- `substantive_unresolved`
- `mixed_or_other`

In the current rebuilt artifacts, the observed buckets are:

- `substantive_unresolved`
- `metadata_container`
- `method_artifact`

## Current split

Counts:

- `substantive_unresolved`: `276038`
- `metadata_container`: `24201`
- `method_artifact`: `24103`

This is the main gain from the typed audit pass:

the unresolved tail is no longer one undifferentiated pool.

## What the split tells us

### 1. Most unresolved edges are still substantive

The unknown-evidence tail is mostly not a method-label bookkeeping problem.

It is still mostly a substantive unresolved pool.

Representative high-support examples:

- `COVID-19 outbreak -> World Health Organization (WHO)`
- `default -> bank-specific characteristics`
- `CO2 emissions -> environmental quality`
- `country income level -> countries`
- `COVID-19 outbreak -> country income level`

So there is still a real substantive review problem here, not only ontology noise.

### 2. The method-heavy tail is now cleanly separable

Representative high-support `method_artifact` examples:

- `simulation -> Method of Moments Quantile Regression (MMQR)`
- `estimation accuracy -> Method of Moments Quantile Regression (MMQR)`
- `place of residence -> Method of Moments Quantile Regression (MMQR)`
- `spatial autoregressive model -> Method of Moments Quantile Regression (MMQR)`
- `estimation -> Method of Moments Quantile Regression (MMQR)`
- `OECD countries -> Method of Moments Quantile Regression (MMQR)`
- `CO2 emissions -> Method of Moments Quantile Regression (MMQR)`

This is exactly the sort of method-heavy region we wanted to separate from substantive unresolved edges.

## Interpretation

The audit bucket is doing useful prioritization work.

It tells us:

- the method-heavy MMQR region is now easy to quarantine as a type/ontology issue
- the metadata/container bucket is separate from both method noise and substantive unresolved edges
- the largest remaining unresolved pool is substantive enough to deserve focused review rather than being dismissed as a labeling artifact

## What this should change operationally

### Near-term

Use the buckets to prioritize audits in this order:

1. `substantive_unresolved`
2. `method_artifact`
3. `metadata_container`

### Why

- `substantive_unresolved` is where we are most likely to find genuinely interesting missing evidence or weak ontology boundaries
- `method_artifact` is where concept-type cleanup and node-typing policy can remove noise efficiently
- `metadata_container` is mostly cleanup work, not frontier opportunity work

## Recommendation

Keep the audit buckets.

Do not use them to suppress routed objects yet.

Use them first as:

- an ontology diagnosis aid
- a review prioritization tool
- and a guide for the next concept-type cleanup pass
