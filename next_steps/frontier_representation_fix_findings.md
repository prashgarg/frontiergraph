# Frontier Representation Fix Findings

## What changed

After the first narrow ontology patch, I made two internal representation fixes:

1. **Mediator label propagation**
   - the current frontier builder now carries resolved mediator labels into `top_mediators_json`
   - the shortlist renderer uses those labels directly

2. **Generic container endpoint penalty**
   - a general surfaced-endpoint rule now demotes broad containers such as:
     - `policy variables`
     - `models`
     - `model parameters`

These are general, rule-based fixes.
They do not hand-target any topic family.

## Why this matters

Before these changes, some apparent ontology failures were really:
- missing label propagation
- or generic container endpoints surviving too high in the surfaced shortlist

That distinction matters because we should not treat every ugly current question as evidence for deeper ontology redesign.

## Results

### 1. Mediator explanation quality improved sharply

On the patched shortlist:
- rows with fallback wording like “the nearest mediators are still poorly labeled” fell from `21 -> 2` at `h=5`
- and from `21 -> 2` at `h=10`

This means many previous explanation-layer failures were **not** ontology problems.

### 2. Generic container endpoints dropped out of the top current shortlist

In the top 20 current shortlist:
- `policy variables -> CO2 emissions` was present before the generic-container rule
- after the rule, container hits in the top 20 fell:
  - `1 -> 0` at `h=5`
  - `1 -> 0` at `h=10`

### 3. The top shortlist now reads more cleanly

Examples now look like:
- `income tax rate -> CO2 emissions`
- `financial development -> green innovation`
- `state of the business cycle -> willingness to pay`
- `CO2 emissions -> ecological footprint`

with mechanism/path text that is much more informative than before.

## What still remains

These changes did **not** solve everything.

Remaining issues include:
- environmental-quality / pollution / degradation boundary questions
- broad but readable mechanism umbrellas such as:
  - `high-quality economic development`
  - `innovation efficiency`
- a few explanation-layer alias redundancies such as:
  - `imports, GDP, and GDP`

So the remaining hard problems are now more likely to be:
- real ontology boundary problems
- or explanation-layer alias cleanup

not unresolved mediator codes.

## Decision

This confirms a useful sequencing rule:

1. fix representation first
2. then interpret the remaining failures as ontology evidence

That makes the next ontology step much more defensible.
