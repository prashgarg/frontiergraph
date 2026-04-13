# Hot vs Enduring Idea Taxonomy

## Status

This is not part of the upstream pipeline yet.

For now it should be treated as either:

- an appendix interpretation of the current results, or
- a next method extension after the widened historical benchmark is stable.

## Motivation

The current system already distinguishes candidates by graph structure, provenance,
boundary signals, and horizon-specific realized closure.

A natural substantive extension is to ask whether surfaced ideas look more like:

- recent-surge ideas that are short-horizon and topic-cycle sensitive,
- enduring-structural ideas that persist across longer periods,
- revived ideas that reappear after an older base of support, or
- event-driven transient ideas tied to shocks or temporary attention spikes.

This is potentially interesting to economists and metascience readers because it is
not only a method question. It is also a question about what kinds of research
frontiers the graph is finding.

## Proposed taxonomy

### 1. Recent-surge

Interpretation:

- strong recent activity
- likely to realize in shorter horizons if the literature is currently hot

Likely empirical signature:

- high `source_recent_share`
- high `target_recent_share`
- low `recent_support_age_years`
- positive `cooc_trend_norm`
- lower average support age

### 2. Enduring-structural

Interpretation:

- supported over longer periods
- less tied to short-lived topic cycles
- more likely to reflect persistent structural questions

Likely empirical signature:

- older `support_age_years`
- lower recent-share measures
- higher `pair_mean_stability`
- broader evidence / venue / source diversity

### 3. Revived / rediscovered

Interpretation:

- older support exists, but recent activity has returned
- not simply hot, and not simply timeless

Likely empirical signature:

- high `support_age_years`
- nontrivial recent-share measures
- possibly positive trend after a long dormant period

### 4. Event-driven transient

Interpretation:

- candidate looks tied to shocks, crises, policy moments, or temporary attention
- may be useful for short horizons but weak as a persistent frontier

Likely empirical signature:

- high recent-share measures
- low long-run diversity and stability
- topic wording that clusters around shock-like or episodic terms

## Current proxy variables already available

The current effective-corpus stack already contains most of the raw ingredients:

- `support_age_years`
- `recent_support_age_years`
- `source_recent_share`
- `target_recent_share`
- `cooc_trend_norm`
- `pair_mean_stability`
- `pair_evidence_diversity_mean`
- `pair_venue_diversity_mean`
- `pair_source_diversity_mean`
- `pair_mean_fwci`

So this extension would not require new extraction logic up front.

## Near-term empirical questions

Once the widened benchmark is refreshed, inspect:

1. whether short-horizon winners load more on recent-surge signals
2. whether longer-horizon winners load more on enduring-structural signals
3. whether early eras and late eras differ in the mix of recent-surge versus enduring candidates
4. whether current-frontier shortlisted objects are disproportionately hot, structural, revived, or transient

## Why this should stay separate for now

This is promising, but it should not be pushed into the main ranking pipeline until:

- the widened historical benchmark is refreshed,
- early-versus-late era behavior is understood,
- and the interpretation is stable enough not to look like post hoc storytelling.

For now, keep it as a formal next-step interpretation layer.
