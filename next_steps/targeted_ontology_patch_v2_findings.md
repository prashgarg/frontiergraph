# Targeted Ontology Patch v2 Findings

## Decision

Reject patch `v2` as the new active baseline.

Keep:

- patch `v1`
- mediator-label propagation
- generic container endpoint rule
- explanation-layer alias cleanup

as the active internal baseline.

Patch `v2` was still worth running, because it taught us something real about the current bottleneck.

## What patch v2 was trying to do

Patch `v2` was intentionally conservative:

- no new risky merges across the environmental outcome family
- explicit boundary rule for:
  - `environmental quality`
  - `environmental pollution`
  - `environmental degradation`
  - `CO2 emissions`
  - `ecological footprint`
- low-risk label overrides only
- explanation-layer GDP alias cleanup

Artifacts:

- [patch_note.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/research_allocation_v2_patch_v2/patch_note.md)
- [boundary_family_report.csv](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/research_allocation_v2_patch_v2/boundary_family_report.csv)
- [environmental_boundary_audit_v2.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/environmental_boundary_audit_v2.md)

## What improved

### 1. The boundary is clearer

The shortlist now preserves distinctions like:

- `environmental pollution`
- `environmental quality`
- `ecological footprint`

instead of trying to clean the family by further collapse.

That is conceptually the right direction.

### 2. Historical performance stayed close

At `h=10`, `Recall@100` moved:

- `0.0634 -> 0.0630`

So the patch did **not** break the historical reranker.

### 3. Environment/climate share in the cleaned shortlist stayed moderate

Compared with the current active baseline:

- `h=5`: `34.0% -> 33.5%`
- `h=10`: `35.0% -> 35.5%`

So the patch did not create a new theme-concentration blow-up at the shortlist level.

## Why we reject it anyway

### 1. Target-endpoint concentration got worse

Top target share in the surfaced frontier top 100 moved:

- `h=5`: `0.210 -> 0.360`
- `h=10`: `0.200 -> 0.230`

That is too large an increase for a conservative patch.

The main driver is obvious:

- `CO2 emissions` appeared `21 -> 36` times in the surfaced top 100 at `h=5`
- `CO2 emissions` appeared `20 -> 23` times at `h=10`

So even without risky merges, the label cleanup and boundary clarifications pushed too much mass onto the already central emissions endpoint.

### 2. Poorly labeled fallback rows did not improve enough

Poorly labeled rows in the cleaned shortlist moved:

- `h=5`: `2 -> 3`
- `h=10`: `2 -> 2`

That is a small change, but it fails the acceptance rule we set for ourselves.

### 3. The patch does not buy enough to justify the concentration cost

The main gain from `v2` is semantic clarity around the environmental family.
That is useful, but not enough to justify worsening endpoint concentration in the live surfaced frontier.

## Acceptance gate outcome

From the formal comparison note:

- PASS: no new container endpoints in top-20 current shortlist
- FAIL: poorly labeled fallback rows stay `<= 2` per horizon
- PASS: noisy targeted label hits stay at `0`
- PASS: `Recall@100` at `h=10` does not fall by more than `0.002`
- FAIL: top-endpoint share does not increase by more than `0.02` at `h=5`
- FAIL: top-endpoint share does not increase by more than `0.02` at `h=10`

Reference:

- [targeted_ontology_patch_comparison.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/targeted_ontology_patch_v2_compare/targeted_ontology_patch_comparison.md)

## Main learning

This is the important part:

The next bottleneck is **not** just “do one more conservative label patch.”

We now have evidence that:

- some semantic clarity gains are real
- but even clean, conservative boundary fixes can still amplify already-dominant endpoints

That means the next meaningful ontology work should be broader than another label-only patch.

## Recommended next move

Keep the current active baseline at:

- `v1` patch
- representation fixes
- current shortlist cleanup rules

Then move the ontology program up one level:

1. layered ontology design
2. node-context signatures
3. edge-evidence attributes

Those are more promising now than another narrow patch in the same style.
