## Purpose

This note checks whether the new readable-object heuristic for `direct-to-path` is substantive or merely cosmetic.

The historical `direct-to-path` panel is endpoint-only by design: it excludes pairs that already have a short support path. So the usefulness layer needs a separate readable question object if it is going to judge mechanism thickening rather than bare endpoint labels.

## Probe design

Sample:

- balanced sample from `outputs/paper/145_effective_benchmark_direct_to_path/historical_feature_panel.parquet`
- `40` rows per `(cutoff_year_t, horizon)` cell
- total rows: `840`

Heuristic:

- build cutoff-specific support neighborhoods from the training corpus
- first try to recover a short support path from source to target with up to `4` edges
- if no short path is found, fall back to the strongest one-sided bridge candidate
- render a readable question object from that path or bridge

## Result

Overall:

- any readable proposed path: `100.0%`
- full multi-step support path found: `73.6%`
- empty fallback (`What missing channel ... ?`): `0.0%`

By cutoff:

- `1985`: full-path share `67.5%`
- `1990`: full-path share `82.5%`
- `1995`: full-path share `82.5%`
- `2000`: full-path share `82.5%`
- `2005`: full-path share `77.5%`
- `2010`: full-path share `65.0%`
- `2015`: full-path share `57.5%`

The later cutoffs are harder, but even there the heuristic still produces a readable proposed path object for all sampled rows.

## Interpretation

This is a useful result.

It means the direct-to-path historical object is not doomed to stay endpoint-only in the usefulness layer. Even though the benchmark event excludes already-observed short support paths, the broader local support neighborhood often still yields a readable longer pathway object.

So the right design is:

- keep the historical benchmark event as is
- but present the LLM with a readable mechanism-thickening object built from the local support neighborhood

## Examples

- `Permanent Income Hypothesis -> Housing Demand`
  - rendered as:
  - `Could Permanent Income Hypothesis affect Housing Demand through Housing tenure?`

- `Inflationary Expectations -> Union Wage`
  - rendered as:
  - `Could Inflationary Expectations affect Union Wage through Inflation rate?`

- `Wage growth -> Net output`
  - rendered as:
  - `Could Wage growth affect Net output through the pathway Incomes Policy, Natural rate of unemployment?`

## Recommendation

Use the new readable-object layer for the `direct-to-path` usefulness rerun.

Do not reuse the old endpoint-only prompt payload.
