# Family-Aware Phrasing Review

## Scope

This note reviews the upgraded `family_aware` prototype after adding:

- sibling-comparator phrasing
- two new reviewed split families
- concept-type overlays in the ontology-vNext artifacts

Current prototype coverage:

- `25` family-aware rows
- `14` unique family-aware pairs in the review markdown
- `6` reviewed families
- `25` active seed rows

## Main result

The phrasing upgrade was worth doing.

Family-aware objects now read as explicit comparative questions rather than generic family diagnostics.

The best new template behavior is:

- name the broader family
- name the focal pair
- name one or two sibling comparators
- tell the reader what comparison to make next

That is a real upgrade over the older wording.

## What improved

### 1. Comparator phrasing is now explicit

Examples that now read much better:

- `Within the macro cycle and price concepts family, is the state of the business cycle -> house prices link more specific than sibling links involving price changes and rate of growth?`
- `Within the innovation and technology concepts family, is the technological innovation -> digital economy link more specific than sibling links involving innovation level and digital economy development?`
- `Within the trade flow and openness concepts family, is the imports -> exports link more specific than sibling links involving trade openness?`
- `Within the structural transformation and urbanization concepts family, is the urbanization -> industrial structure link more specific than sibling links involving industrial structure upgrading?`

These are more comparative and more actionable than the earlier “what is specific to X -> Y?” style.

### 2. The split trade families are already producing plausible objects

The split away from the old broad trade/urban candidate looks justified.

The new reviewed families already surface coherent family-aware examples:

- `trade flow and openness concepts`
- `structural transformation and urbanization concepts`

That is a good sign that the family split improved the object instead of just increasing ontology complexity.

### 3. The object still works best as a secondary frontier object

The best family-aware rows are now real and useful.

But they still work best as:

- ontology-vNext review objects
- internal comparative frontier objects
- possible paper-extension objects

They are not yet stronger than:

- path/mechanism objects
- context-transfer objects
- evidence-type-expansion objects

### 4. The review pack is now easier to judge

The human-readable prototype markdown now collapses horizon duplicates.

That matters because the earlier review view made the same pair appear twice at `h=5` and `h=10`, which inflated the apparent variety of family-aware objects.

The new review pack makes it easier to judge:

- how many genuinely distinct family-aware objects we have
- which families are doing real work
- and whether the best rows are strong enough to promote later

## Where the object is strongest

Strongest family-aware regions right now:

- `macro cycle and price concepts`
- `innovation and technology concepts`
- `trade flow and openness concepts`

The environmental family remains useful, but it still often doubles as an ontology-boundary diagnostic.

## Remaining limitations

### 1. Comparators are sometimes right but still coarse

Examples like:

- `environmental pollution and environmental quality`
- `price changes and rate of growth`

are much better than before, but the comparison dimension is still implicit.

The next phrasing improvement should sometimes say whether we are comparing:

- effect specificity
- context concentration
- evidence concentration
- or family blur versus pair specificity

### 2. Horizon duplicates are still duplicated in the prototype table

This is fine for review, but if family-aware objects move closer to paper-facing use, we should collapse duplicate `h=5` / `h=10` prototype rows in the human review pack.

## Decision

Keep family-aware objects active as a secondary ontology-vNext object.

Do not route them into the main surfaced shortlist yet.

## Next improvement

The next gain is likely not more raw family breadth by itself.

It is:

1. slightly sharper comparator selection
2. a little more explicit comparison wording
3. then a re-review of whether the best family-aware rows are paper-worthy
