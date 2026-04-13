# Edge Evidence Schema v1

## Goal

Extend the frontier beyond node space by recording what kind of evidence supports an edge.

Right now the graph mostly knows:

- source concept
- target concept
- broad causal/noncausal status
- some stability/evidence fields

That is not enough for many useful frontier questions.

## Core edge-evidence fields

### Evidence mode

- `evidence_mode`
  - theory
  - empirics
  - mixed

### Empirical design family

- `design_family`
  - experiment
  - IV
  - DiD
  - panel_FE
  - descriptive
  - survey_valuation
  - simulation_calibration
  - structural_estimation
  - review_or_synthesis

### Causal explicitness

- `causal_explicitness`
  - explicit_causal
  - causal_language_ambiguous
  - associative_only

### Directionality confidence

- `directionality_confidence`
- `directionality_source`

### Context coverage

- `context_coverage_json`
  - geographies
  - populations
  - sectors
  - units

### Evidence strength

Map the existing graph-side support into the new schema:

- `stability`
- `edge_instance_count`
- `weight`
- `supporting_paper_count`
- `supporting_design_diversity`

## Why this matters

A frontier system should be able to surface not only:

- missing direct relation

but also:

- missing mechanism
- missing empirical confirmation
- missing theory for an empirical regularity
- missing transport to a new context
- missing evidence-type expansion

## Example frontier types enabled

1. **Missing empirical confirmation**
- theory-heavy edge, weak empirical support

2. **Missing mechanism**
- strong direct association, low mediator support

3. **Missing context transfer**
- strong support in one geography or population, weak elsewhere

4. **Missing evidence-type expansion**
- descriptive relation with no quasi-experimental follow-up

## Design rule

Edge-evidence attributes should attach to canonical edges and to supporting mention-level edge instances.

That lets us keep:

- a clean graph for ranking
- richer evidence summaries for surfacing

without turning every evidence distinction into a separate concept node.
