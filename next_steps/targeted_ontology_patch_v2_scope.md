# Targeted Ontology Patch v2 Scope

## Why this note exists

After the first narrow ontology patch and the mediator-label propagation fix, the remaining failures are easier to interpret.

That matters because we no longer need to guess whether a bad current question comes from:
- unresolved mediator codes
- duplicate label noise
- or a real ontology boundary problem

The mediator-label propagation step reduced shortlist rows with generic fallback wording from:
- `21 -> 2` at `h=5`
- `21 -> 2` at `h=10`

So the next ontology patch should target the failures that remain **after** that representation fix.

## What now looks like a real v2 ontology target

### 1. Environmental-quality boundary

The main family is now cleaner, but the boundary is still muddy:
- `environmental quality`
- `environmental pollution`
- `environmental degradation`
- `pollution abatement`
- nearby EKC-style constructs

Evidence from the patched shortlist:
- `environmental pollution -> environmental quality`
- `environmental quality -> environmental pollution`
- `income tax rate -> environmental quality`
- mediators such as `pollution abatement`, `environmental taxes`, and `Environmental Kuznets Curve (EKC) hypothesis`

Interpretation:
- this is no longer just a parenthetical-label issue
- it now looks like a real **family-boundary problem**
- some of these are outcomes
- some are mechanisms or channels
- some are umbrella constructs

Recommended v2 action:
- inspect this family as a **boundary audit**, not just a synonym merge
- likely separate:
  - pollution / emissions outcomes
  - environmental-quality umbrella constructs
  - degradation / damage constructs
  - mechanism-like mediators such as abatement or taxes

### 2. Weak container endpoints

Examples now visible in the patched shortlist:
- `policy variables -> CO2 emissions`
- `models -> CO2 emissions`

These are not really unresolved-code problems anymore.
They are weak semantic containers.

Interpretation:
- this is partly ontology, partly endpoint typing
- these labels are too broad to be helpful surfaced objects

Recommended v2 action:
- create a **generic container endpoint list** for ontology-side review
- likely either:
  - demote them at the surfaced layer with a general rule
  - or split / remap them if they collapse heterogeneous things

### 3. High-level development / innovation umbrella mediators

These are now readable, but still broad:
- `high-quality economic development`
- `innovation efficiency`
- `green innovation efficiency`
- `technological innovation level`

Interpretation:
- not obviously wrong
- but often too umbrella-like to serve as strong mechanism objects

Recommended v2 action:
- do **not** merge these blindly
- first tag them as a candidate ontology/type issue:
  - broad mechanism umbrella
  - likely useful as a parent/family concept later

### 4. Local duplicative economic-growth aliases inside explanations

Examples:
- `GDP`
- `gross domestic product (GDP)`
- `economic growth (GDP)`

These are now mostly explanation-layer redundancies, not top-level endpoint failures.

Recommended v2 action:
- low-risk explanation-layer alias cleanup
- this is a smaller target than the environmental-quality boundary

## What no longer looks like a primary ontology target

### 1. Recurrent unresolved mediator codes

This looked important before, but the patched frontier now resolves most of them.

So this is no longer a main ontology redesign reason.
It was largely a missing label propagation issue.

### 2. `willingness to pay (WTP)` versus `willingness to pay`

This was a clear first patch target and it worked.
The acronym clutter is gone from the shortlist.

### 3. Emissions-family parenthetical duplicates

These were a clear first patch target and they also improved materially.

The remaining emissions problem is no longer duplicate labels.
It is now:
- canonical-node concentration
- and the broader environmental-outcome boundary around that family

## Proposed v2 patch order

1. environmental-quality / pollution / degradation boundary audit
2. generic container endpoint review:
   - `policy variables`
   - `models`
3. low-risk explanation-layer alias cleanup for recurring GDP/growth duplicates

## Decision rule

We should keep using the same standard:

- patch only if the intervention is general and defensible
- rerun the same current frontier -> shortlist -> concentration stack
- compare:
  - label cleanliness
  - remaining weak container endpoints
  - thematic concentration
  - canonical-node concentration

If a candidate patch only improves readability by collapsing too much semantic structure, we should reject it.
