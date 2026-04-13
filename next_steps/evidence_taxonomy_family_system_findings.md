# Evidence Taxonomy + Family System Findings

## What changed

This pass added three new internal layers on top of the active `v1 + representation fixes + context normalization` baseline:

- a corpus-wide edge evidence taxonomy
- a reviewed-seed family system plus a reusable candidate-family queue
- routed-layer quality filters that use taxonomy confidence and support strength

No ranking or public outputs changed.

## New internal artifacts

Under `data/processed/ontology_vnext_proto_v1/`:

- `edge_instance_taxonomy.parquet`
- `canonical_edge_evidence_summary.parquet`
- `evidence_unknown_audit.parquet`
- `family_seed_table.parquet`
- `family_candidate_table.parquet`
- `family_relation_table.parquet`

The enriched shortlist review pack and routed outputs were rebuilt on top of those new layers.

## Validation

All planned schema checks now pass:

- canonical joins complete
- family joins complete
- endpoint context coverage >= 90%
- edge evidence coverage >= 90%
- one active family per concept
- environmental boundary members remain separate
- mapping kinds remain exact-only in the proxy layer
- edge evidence modes stay within the allowed set
- identification strengths stay within the allowed set
- taxonomy confidence stays on the fixed ladder
- family relation types stay within the allowed set

## Evidence taxonomy: what improved

The evidence layer now classifies canonical edges with:

- `evidence_mode`
- `design_family`
- `identification_strength`
- `taxonomy_confidence`
- `unknown_reason`

This immediately sharpened the routed evidence-expansion object.

### Before taxonomy + route-quality filters

The routed shortlist had:

- `23` changed rows
- `14` context-transfer rows
- `9` evidence-type-expansion rows

### After taxonomy + route-quality filters

The routed shortlist now has:

- `21` changed rows
- `14` context-transfer rows
- `7` evidence-type-expansion rows

Two evidence-expansion rows were suppressed, both for low support:

- `price changes -> CO2 emissions` at `h=5`
- `price changes -> CO2 emissions` at `h=10`

That is the right behavior. The taxonomy kept the stronger evidence-expansion objects and dropped the weaker one that did not meet the support floor.

### Kept evidence-expansion examples

- `willingness to pay -> CO2 emissions`
- `imports -> exports`
- `willingness to pay -> environmental pollution`
- `CO2 emissions -> imports` at `h=10`

These all read more actionable than the baseline path/mechanism wording because they say what kind of evidence should come next, not just that the pair is interesting.

## Family system: what we learned

The family system now has:

- `5` reviewed seed rows
- `29` candidate family rows
- `74` family relation rows

The candidate families are plausible enough to justify a second pass of reviewed seeding.

Top candidate families:

- `uncertainty risk concepts`
- `innovation technology concepts`
- `macro cycle prices concepts`
- `environment climate concepts`
- `trade urban structure concepts`
- `labor income demand concepts`

This is exactly the kind of output we wanted:

- not live ontology membership
- not random lexical cousins
- a review queue of related-but-not-identical concept groups

## Best next family seeds

Based on current candidate quality, the most promising next reviewed seeds are:

1. `innovation technology concepts`
   - `digital economy`
   - `digital economy development`
   - `digital transformation`
   - `innovation level`
   - `technological innovation`
   - `technological progress`

2. `macro cycle prices concepts`
   - `house prices`
   - `inflation`
   - `output growth`
   - `price changes`
   - `rate of growth`
   - `state of the business cycle`

3. `trade urban structure concepts`
   - `exports`
   - `imports`
   - `industrial structure`
   - `industrial structure upgrading`
   - `trade openness`
   - `urbanization`

I would review these before touching `environment climate concepts`, because the environmental area already has one active reviewed seed and is more likely to need boundary care than simple family promotion.

## Main takeaway

This pass worked.

- evidence-expansion is now cleaner and more defensible
- family expansion is no longer ad hoc
- routed objects are still conservative and topic-agnostic

The next useful move is to review and promote a small number of family candidates, then rerun the same routed-object pipeline and see whether family-aware frontier objects become strong enough to matter.
