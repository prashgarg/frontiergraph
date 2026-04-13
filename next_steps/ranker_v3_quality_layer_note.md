# Ranker v3 Quality Layer Note

## Motivation

The refreshed method-v2 retrieval stack is now good at finding plausible local graph neighborhoods. It is not yet good enough at separating:

- plausible but broad or crowded mechanism neighborhoods
- plausible and genuinely sharp paper candidates

The current shortlist failure mode is clear in the surfaced frontier:

- broad endpoint concepts recur too often
- generic mediators such as `Income`, `Productivity`, or `Policy uncertainty` are overused as catch-all bridges
- active semantic families such as green/climate/energy dominate the top of the ranking

This is not mainly an ontology problem. It is a ranking-quality problem.

## What is implemented in this pass

This pass adds graph-native quality features rather than lexical blacklists.

### Transparent-layer additions

The transparent score now has two new bounded components:

- `transparent_resolution_component`
- `transparent_mediator_specificity_component`

These are built from historical graph structure at `t-1`.

`transparent_resolution_component` is higher when the focal endpoints are less broad in the support graph. It is computed from historical support-degree broadness rather than from manually curated stoplists.

`transparent_mediator_specificity_component` is higher when the focal mediator is less generic in the historical graph. It uses mediator broadness in the support graph rather than keyword heuristics.

The transparent model still keeps:

- support strength
- opportunity
- hub-style specificity
- provenance
- topology

So the quality layer acts as a soft correction, not a full rewrite of the retrieval logic.

### Learned-reranker additions

The learned reranker feature panel now includes:

- `source_support_total_degree`
- `target_support_total_degree`
- `source_node_age_years`
- `target_node_age_years`
- `focal_mediator_support_total_degree`
- `focal_mediator_incident_count`
- `focal_mediator_age_years`
- `endpoint_broadness_raw`
- `endpoint_resolution_score`
- `focal_mediator_broadness_raw`
- `focal_mediator_specificity_score`
- `endpoint_age_mean_years`

These are historical `t-1` features. They are intended to help the reranker learn when a candidate is:

- broad but important
- broad and generic
- fresh but weakly grounded
- mature enough to be a plausible next paper

## How penalty magnitude should be chosen

We should not hand-pick penalty magnitudes from examples.

Instead:

1. Keep the transparent quality components bounded in `[0,1]`.
2. Tune their weights on historical cutoff-year validation.
3. For learned rerankers, let the coefficients be estimated from the candidate panel with regularization.
4. Choose post-ranking concentration controls by an explicit Pareto rule rather than aesthetics.

This means:

- transparent penalties are calibrated
- reranker penalties are learned
- diversification penalties are selected from a documented comparison rule

That is much more defensible than saying “we penalized broad concepts because the examples looked too broad.”

## Why degree-style centrality is included first

The simplest historically grounded centrality information is already very useful:

- support degree
- direct degree
- incident count
- node age

These are transparent and easy to explain.

They also map directly onto the current failure mode:

- high-degree endpoints are often broad containers
- high-degree mediators are often generic bridges

## Why PageRank and eigenvector centrality are not the first default

They may still be useful, but they are not the best first pass.

Concerns:

- they are less transparent to readers
- they are often highly correlated with degree in these sparse graphs
- they can reward “globally central” nodes that are important but also generic

So the right order is:

1. degree-like centrality and node age first
2. evaluate whether they help
3. only then add PageRank/eigenvector as robustness or appendix features if they add signal

## How novelty should be used

Novelty is not one-directional.

Very old nodes can be too broad or saturated. Very new nodes can be too weakly grounded. So novelty should enter first as raw features such as:

- `source_node_age_years`
- `target_node_age_years`
- `focal_mediator_age_years`

The reranker can then learn whether very old or very young objects are less promising in practice.

This is better than hard-coding “newer is better.”

## Anticipated reviewer/editor objections

### “You are penalizing important broad questions.”

Response:

The model does not hard-ban broad concepts. It introduces soft historical features that distinguish broad-but-sharp candidates from broad-and-generic candidates. Broadness is one signal, not the decision rule.

### “These penalties look ad hoc.”

Response:

The features are defined ex ante from historical graph structure, bounded transparently, and tuned on held-out historical cutoffs rather than selected from anecdotal examples.

### “Centrality may reflect importance, not genericness.”

Response:

Exactly. That is why centrality is used as a feature, not as a one-way exclusion rule. In the learned reranker, the sign and magnitude are estimated from data rather than assumed.

### “Novelty is subjective.”

Response:

We do not impose a novelty bonus by fiat. We expose node age as a historical feature and let the model learn whether novelty helps or hurts.

## Recommended next experiment

Run a focused historical comparison for `path_to_direct`:

- current family-aware composition / boundary-gap winners
- new quality-layer transparent screen
- new quality-aware reranker families

Main outputs:

- `MRR`
- `Recall@100`
- top-target share
- semantic-family concentration
- human-usefulness pack quality

The test should ask whether the new quality layer:

- reduces broad/generic shortlist clutter
- preserves or improves historical ranking performance
- produces better paper-facing examples

## Bottom line

The right way to move beyond “plausible graph gap” is not to invent taste-based rules. It is to add historically grounded quality features that measure:

- how broad the endpoints are
- how generic the mediator is
- how old or saturated the underlying concepts are

and then calibrate those features historically.
