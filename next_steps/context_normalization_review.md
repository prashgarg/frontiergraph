# Context Normalization Review

## What we changed

We added a deterministic context normalization layer for geography-like context values and wired it into the ontology-vNext direct scorer.

Main pieces:

- alias table: `data/processed/ontology_vnext_proto_v1/context_alias_table.csv`
- normalization policy note: `next_steps/context_normalization_working_note.md`
- scorer integration: `scripts/build_vnext_object_scored_frontier.py`

The normalization layer:

- collapses obvious aliases such as `CHN -> China`, `USA -> United States`, `GBR -> United Kingdom`
- keeps blocs and regions distinct from countries
- treats `NA` as ambiguous / unknown for now
- computes matched-level geography comparisons where possible

## Design choice on blocs and groups

We should keep blocs and groups as blocs and groups in the primary normalized field.

Examples:

- `OECD` -> `OECD countries`
- `EU-15` -> `EU-15 countries`
- `BRICS` -> `BRICS countries`

We should **not** automatically explode bloc-level evidence into constituent countries in the main normalization layer.

Reason:

- bloc-level evidence is not the same thing as direct country-level evidence
- exploding blocs into countries would overstate context coverage and blur provenance
- if we later want bloc-membership reasoning, it should be added as separate metadata, not by replacing the observed label

## What improved

The routed shortlist became cleaner and slightly more conservative.

Before normalization:

- changed rows: `25`
- changed unique pairs: `13`

After normalization:

- changed rows: `23`
- changed unique pairs: `12`

This is a good change, not a regression. A couple of weaker mixed-level context-transfer routes dropped out rather than being forced through.

Examples that now read much better:

- `CO2 emissions -> exports`
  - now reads: pair evidence concentrated in `EU-15 countries`, endpoint concepts broader across `OECD countries`
- `financial development -> green innovation`
  - now reads: pair evidence concentrated in `South Africa`, endpoints broader across `China`, `India`, and `Pakistan`
- `willingness to pay -> CO2 emissions`
  - still works well as evidence-type expansion and is unaffected by messy context aliases

## What we learned

1. Context normalization is worth keeping.
2. Matched-level geography comparison improves quality.
3. The best policy is conservative:
   - normalize aliases
   - keep context types separate
   - do not silently convert bloc evidence into country evidence

## Remaining edge cases

There are still a small number of direct-scored context-transfer rows with no matched geography granularity.

At this stage they do not cross the routed shortlist threshold, which is fine.

That means the current routing layer is already behaving conservatively enough, even before any further refinement.

## Best next improvements

1. Evidence taxonomy cleanup
   - reduce `unknown` / `other`
   - sharpen evidence-type expansion

2. Context membership metadata
   - keep blocs as blocs in the main field
   - optionally add `member_country_ids_json` later for membership-aware reasoning

3. Family expansion
   - seed a few more high-value related-but-not-merged families

4. Optional route-quality refinement
   - if needed later, add a requirement that routed context-transfer objects have matched geography or matched unit evidence above a minimum threshold
