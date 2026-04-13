# Targeted Ontology Patch Comparison

This note compares the baseline current-frontier artifacts against the narrow local ontology patch.

## Readability / label cleanup
- Noisy targeted label hits in shortlist text: `0` -> `0`
- Flagged share in h=5 surfaced frontier top 100: `0.000` -> `0.000`
- Flagged share in h=10 surfaced frontier top 100: `0.000` -> `0.000`

## Concentration
- Environment/climate share in h=5 cleaned shortlist top 100: `0.340` -> `0.335`
- Environment/climate share in h=10 cleaned shortlist top 100: `0.350` -> `0.355`

## Acceptance gate
- PASS | no new container endpoints in top-20 current shortlist
- FAIL | poorly labeled fallback rows stay <= 2 per horizon
- PASS | noisy targeted label hits stay at 0
- PASS | Recall@100 at h=10 does not fall by more than 0.002 absolute
- FAIL | top-endpoint share does not increase by more than 0.02 absolute at h=5
- FAIL | top-endpoint share does not increase by more than 0.02 absolute at h=10

## Additional diagnostics
- Poorly labeled rows h=5: `2` -> `3`
- Poorly labeled rows h=10: `2` -> `2`
- Container hits in top-20 h=5: `0` -> `0`
- Container hits in top-20 h=10: `0` -> `0`
- Top target share in surfaced frontier top 100 h=5: `0.210` -> `0.360`
- Top target share in surfaced frontier top 100 h=10: `0.200` -> `0.230`
- Recall@100 at h=10: `0.0634` -> `0.0630`

## Top h=5 shortlist titles after patch
- Through which nearby pathways might willingness to pay shape CO2 emissions?
- Which nearby mechanisms most plausibly link state of the business cycle to willingness to pay?
- Through which nearby pathways might price changes shape CO2 emissions?
- Through which nearby pathways might financial development shape green innovation?
- Through which nearby pathways might regional heterogeneity shape CO2 emissions?
- Through which nearby pathways might digital economy shape energy intensity?
- Through which nearby pathways might energy consumption shape willingness to pay?
- Through which nearby pathways might CO2 emissions shape ecological footprint?
- Through which nearby pathways might technological innovation shape green innovation?
- Which nearby mechanisms most plausibly link renewable energy to willingness to pay?

## Top h=10 shortlist titles after patch
- Through which nearby pathways might income tax rate shape CO2 emissions?
- Which nearby mechanisms most plausibly link state of the business cycle to willingness to pay?
- Through which nearby pathways might price changes shape CO2 emissions?
- Through which nearby pathways might financial development shape green innovation?
- Through which nearby pathways might digital economy shape energy intensity?
- Through which nearby pathways might willingness to pay shape CO2 emissions?
- Through which nearby pathways might CO2 emissions shape ecological footprint?
- Through which nearby pathways might energy consumption shape willingness to pay?
- Through which nearby pathways might technological innovation shape green innovation?
- Which nearby mechanisms most plausibly link renewable energy to willingness to pay?
