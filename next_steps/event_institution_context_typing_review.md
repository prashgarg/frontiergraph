# Event Institution Context Typing Review

## Scope

This note reviews the latest additive node-typing overlay for:

- `event`
- `institution_actor`
- `geography_context`
- `none`

The point of this pass was not to create new surfaced objects.
It was to separate context-bearing concepts from the ordinary substantive queue so the unresolved-evidence audit becomes easier to interpret.

## Current counts

Current canonical-concept counts are:

- `none`: `6233`
- `institution_actor`: `281`
- `geography_context`: `190`
- `event`: `48`

That distribution is sensible for a conservative overlay.

Relative to the earlier purely pattern-based pass:

- `geography_context` rose from `131 -> 190`
- `none` fell from `6292 -> 6233`
- `event` and `institution_actor` stayed stable

That is the right shape of change.
The dictionary-backed layer improved recall without changing the basic character of the overlay.

## Representative examples

### `event`

- `COVID-19 pandemic`
- `global financial crisis`
- `financial crisis`
- `COVID-19 outbreak`
- `Russia-Ukraine conflict`

### `institution_actor`

- `firm size`
- `firm productivity`
- `government subsidies`
- `banks`
- `government intervention`
- `institutions`

### `geography_context`

- `China`
- `Japan`
- `United States`
- `developing countries`
- `developed countries`
- `rural areas`
- `urban population`
- `low-income countries`
- `eastern region`

## What improved

The main improvement is not recall.
It is precision.

The earlier broader heuristic was too loose.
It created noisy matches by using the full alias cloud and overly broad tokens.

The current version is intentionally more conservative than the first dictionary attempt:

- it relies mainly on preferred-label patterns
- it uses a narrower geography / institution / event vocabulary
- it consults the existing context alias table for known geographies and blocs
- and it avoids broad fallback behavior that was creating false positives

That was the right tradeoff for this pass.

## What this now does well

### 1. It peels off a distinct event-context region

Rows like:

- `COVID-19 outbreak -> World Health Organization (WHO)`
- `COVID-19 pandemic -> COVID-19 outbreak`

now live in a more intelligible part of the unresolved audit.

### 2. It helps keep the top policy queue cleaner

The current top `policy_outcome_or_boundary` rows are now mostly `none -> none`.
That is exactly what we wanted from this overlay.

The important practical checks now pass:

- `Japan` -> `geography_context`
- `China` -> `geography_context`
- `United States` -> `geography_context`
- `policy` -> `none`
- `energy efficiency` -> `none`
- `environmental regulations` -> `none`

### 3. It gives us a real diagnosis layer without changing ranking

This is a useful pattern:

- keep the overlay additive
- use it to separate review queues
- do not force it into ranking prematurely

## What it still misses

This pass is conservative enough that some obvious named contexts are still missed.

Examples of likely misses or partial misses include:

- named institutions that do not carry an obvious institution token
- named geography blocs when the label does not expose a context token directly

That is acceptable for now.
It is better than the earlier false-positive-heavy version.

Known bloc strings like `OECD` and `EU-15` are now present in the alias table and will classify as `geography_context` when they appear as surfaced concept labels.

## Current judgment

Keep this as an internal diagnosis overlay.

Do not use it in ranking or routed-layer selection yet.

Its current role should be:

- unresolved-tail separation
- audit prioritization
- later design input for richer context/entity typing

## Recommendation for the next typing pass

The next useful refinement would not be a broader pattern list.
It would be a more structured named-entity pass on top of the current alias-table approach, for example:

- explicit country dictionary support beyond currently observed context strings
- explicit institution dictionary support
- optional bloc/region dictionary support

That would improve recall without reopening the earlier false-positive problem.

Until then, the current overlay is good enough to keep:

- it is conservative
- it is interpretable
- and it already improves the unresolved audit in a meaningful way
