# Current Shortlist Cleanup: Findings

## What this pass changed

This pass added two things on top of the already filtered current frontier:

1. **A light semantic-dedup / repeated-family layer**
- candidate pool per horizon: top `250` by surfaced rank
- final shortlist per horizon: top `100`
- greedy shortlist penalty:
  - `12` for an exact repeated source-target semantic family
  - `4` for each prior appearance of the same source family
  - `4` for each prior appearance of the same target family

2. **A stricter mediator display rule**
- explanation text now prefers only resolved mediator labels
- if the leading mediators are still poorly labeled, the surfaced question keeps its path/mechanism form, but the explanation switches to a generic fallback rather than printing opaque codes

So this pass is not an ontology redesign. It is a more disciplined surfaced-shortlist cleanup.

## What improved

### 1. The shortlist is still readable after diversification
The top questions now include:
- `Through which nearby pathways might income tax rate shape CO2 emissions?`
- `Through which nearby pathways might financial development shape green innovation?`
- `Through which nearby pathways might technological innovation shape green innovation?`
- `Through which nearby pathways might environmental pollution shape carbon emissions?`
- `Which nearby mechanisms most plausibly link environmental regulation to sustainable development?`

These are much closer to paper-usable frontier objects than the earlier raw surfaced list.

### 2. The question object remains path/mechanism based
After the cleanup pass, the top-100 route mix is:
- `h=5`: `79` path, `21` mediator
- `h=10`: `77` path, `23` mediator

That is directionally reassuring. The surfaced object is still mostly richer than a direct edge.

### 3. Explanation quality improved
The `why` text no longer forces unresolved `FG3C...` mediator labels into the explanation just because they scored highly.

That makes the rendered questions meaningfully easier to read, even when the underlying mediator layer is still imperfect.

## What still looks good

These question families now look genuinely strong:
- `financial development -> green innovation`
- `technological innovation -> green innovation`
- `income tax rate -> CO2 emissions`
- `environmental pollution -> carbon emissions`

These look like real current frontier objects rather than graph artifacts.

## What still looks weak

The remaining weakness is no longer “bad surfaced endpoints.”

It is mainly:
- repeated families
- broad targets
- ontology-adjacent semantic awkwardness
- mediator explanation quality for some families

Examples:
- repeated `state of the business cycle -> ...` variants
- repeated `green innovation -> ...` variants
- `carbon emissions` / `CO2 emissions` / `environmental quality (CO2 emissions)` type overlaps
- broad targets such as `innovation outcomes`

## Manual review of the top 15 per horizon

This is a human-style review, not an automated score.

### Horizon 5

| Rank | Question | Review label | Why |
|---:|---|---|---|
| 1 | income tax rate -> CO2 emissions | strong | concrete endpoints, plausible mediators, good paper shape |
| 2 | financial development -> green innovation | strong | coherent and well-supported current frontier object |
| 3 | state of the business cycle -> willingness to pay (WTP) | label_problem | object may be valid, but explanation layer is still too poorly labeled |
| 4 | technological innovation -> green innovation | strong | strong and readable path question |
| 5 | environmental regulation -> innovation outcomes | readable_but_weak | readable, but target is broad |
| 6 | state of the business cycle -> carbon emissions | label_problem | plausible family, weak explanation layer |
| 7 | price changes -> willingness to pay | label_problem | thin and under-explained |
| 8 | environmental pollution -> carbon emissions | strong | strong mechanism-rich candidate |
| 9 | environmental regulation -> sustainable development | readable_but_weak | readable, but target remains broad |
|10 | green innovation -> renewable energy consumption | readable_but_redundant | good but crowded green-innovation family |
|11 | state of the business cycle -> green innovation | readable_but_redundant | same source family already appears repeatedly |
|12 | carbon emissions -> environmental quality | ontology_problem | emissions / environmental-quality family still semantically awkward |
|13 | green innovation -> environmental pollution | readable_but_redundant | same source family crowding the shortlist |
|14 | natural resources -> green innovation | readable_but_redundant | understandable, but another green-innovation family variant |
|15 | renewable energy consumption -> green innovation | readable_but_redundant | understandable, but still crowded |

### Horizon 10

| Rank | Question | Review label | Why |
|---:|---|---|---|
| 1 | financial development -> green innovation | strong | strong and stable across horizons |
| 2 | state of the business cycle -> willingness to pay (WTP) | label_problem | explanation layer still too weak |
| 3 | technological innovation -> green innovation | strong | strong and stable across horizons |
| 4 | income tax rate -> CO2 emissions | strong | strong and stable across horizons |
| 5 | environmental regulation -> innovation outcomes | readable_but_weak | target remains broad |
| 6 | environmental pollution -> carbon emissions | strong | still one of the best examples |
| 7 | price changes -> willingness to pay | label_problem | still thin and poorly explained |
| 8 | state of the business cycle -> green innovation | readable_but_redundant | repeated source-family issue |
| 9 | carbon emissions -> environmental quality | ontology_problem | emissions family still unclear |
|10 | environmental regulation -> sustainable development | readable_but_weak | readable, but still broad |
|11 | green innovation -> environmental pollution | readable_but_redundant | another repeated green-innovation family object |
|12 | state of the business cycle -> carbon emissions | label_problem | plausible family, weak explanation layer |
|13 | natural resources -> green innovation | readable_but_redundant | understandable, but still crowded |
|14 | environmental quality -> willingness to pay (WTP) | ontology_problem | awkward label family plus semantic ambiguity |
|15 | income tax rate -> state of the business cycle | readable_but_weak | readable but still not among the strongest objects |

## Review counts from the top 15 per horizon

Across the `30` manually reviewed top rows:
- `strong`: `8`
- `readable_but_redundant`: `8`
- `readable_but_weak`: `5`
- `label_problem`: `6`
- `ontology_problem`: `3`

## What this implies

The biggest current problem is **not** raw endpoint junk anymore.

The current shortlist now fails mostly in three ways:

1. **repeated-family redundancy**
2. **explanation-layer label problems**
3. **a smaller but real ontology problem in a few semantic families**

That is progress. It means the project has moved from:
- artifact cleanup

to:
- semantic crowding and ontology diagnosis

## Recommendation

Use the cleaned shortlist for:
- paper examples
- paper wording
- ontology target selection

Do **not** treat the current shortlist as fully finished yet.

The next fix should be:
- a narrow ontology pass on the repeated semantic families
- plus, if needed later, a light repeated-family or semantic-dedup regularization layer on the surfaced shortlist
