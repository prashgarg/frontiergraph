# Family Seed Review and Evidence Cleanup Findings

## What we changed

This pass did two things on top of the active `v1 + representation fixes + context normalization` baseline:

- promoted a small second set of reviewed families into active membership
- cleaned up high-support canonical-edge evidence summaries when the pair-level dominant design signal was already strong enough to justify resolution

No ranking changed. Public outputs still did not change.

## Reviewed family seeds now active

The active reviewed family layer now contains `4` families and `19` seed rows:

- `environmental outcomes`
- `uncertainty and risk concepts`
- `innovation and technology concepts`
- `macro cycle and price concepts`

This is the first point where the family layer is broad enough to tell us whether family-aware frontier objects are genuinely useful rather than merely possible.

## What happened to the candidate-family queue

The candidate queue is now cleaner because active reviewed members are excluded from the reusable review queue.

That reduced the candidate table from the previous broader queue to:

- `15` candidate rows
- `74` relation rows overall

The remaining top candidate families are now more informative:

1. `environment climate concepts`
2. `trade urban structure concepts`
3. `labor income demand concepts`

That is the right result. The queue is now focused on unresolved family decisions rather than re-proposing families we already reviewed and promoted.

## What happened to family-aware frontier objects

Family-aware objects materially expanded.

Before the second reviewed seeding pass:

- `family_aware = 8`

After the second reviewed seeding pass:

- `family_aware = 24`

The new objects are materially better than before because they now include coherent non-environment examples such as:

- `state of the business cycle -> house prices`
- `state of the business cycle -> price changes`
- `technological innovation -> digital economy`
- `digital economy development -> digital economy`

So the family-aware object is no longer underpowered only because the seed layer was too thin.

## What happened to the evidence taxonomy

The targeted cleanup worked, but in a conservative way.

It resolved summary-layer ambiguity for high-support pairs when:

- the dominant pair-level design was already clean
- support was strong enough
- the edge could be treated as resolved at the canonical summary layer without inventing a new classifier

This reduced the unknown-evidence audit from:

- `325250` rows

to:

- `324342` rows

That is not a dramatic numerical drop, but it is still useful because the resolved cases were exactly the high-support pairs where the leftover unknown flag was least informative.

The remaining unknown mass is now more honest:

- unresolved `unknown` / `do_not_know` / `other` cases no longer keep a misleading `0.75+` confidence bucket
- unresolved rows are capped at `0.5` or below

## What happened to the routed layer

The routed shortlist stayed stable:

- `14` `context_transfer` rows
- `7` `evidence_type_expansion` rows
- `21` changed rows total
- `2` low-support evidence-expansion rows still correctly suppressed

That stability is good. It means the new family/evidence pass did not destabilize the best routed objects.

## Main takeaway

This pass taught us two useful things.

1. The family system is now strong enough to evaluate seriously.
   Family-aware objects became much more substantial once the seed layer moved beyond the environmental family.

2. The next evidence-taxonomy gains are now less about routing rules and more about the unresolved tail.
   The remaining unknown-evidence mass is concentrated in genuinely unresolved method-heavy or metadata-heavy regions, not just in leftover summary-layer ambiguity.

## Best next moves

### Sequential

1. review the new family-aware objects directly and decide whether any belong in the paper as secondary frontier types
2. do a targeted unknown-evidence audit on the highest-support unresolved method-heavy edges
3. decide whether `trade urban structure concepts` should become one reviewed family or be split into narrower reviewed families

### Parallel

- improve family-aware phrasing so it compares a pair against sibling concepts more explicitly
- improve evidence-taxonomy coverage for the unresolved method-heavy tail
- decide whether the family layer should eventually route its own frontier object, not just feed prototypes

## Bottom line

This was a productive pass.

- the active family layer is now materially stronger
- the candidate queue is cleaner
- the evidence layer is more honest
- the routed layer stayed conservative

The project is now in a good place to decide whether family-aware frontier questions deserve promotion from prototype status into the paper-facing object set.
