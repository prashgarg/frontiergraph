# Frozen-Ontology Execution Plan

Date: 2026-04-05

This note is the working implementation plan for the next paper pass.

The key decision is:

- **freeze the current ontology and extraction layer through the next paper pass**
- use that fixed graph to learn what the stronger paper actually looks like
- redesign ontology only after we know which downstream failures are still binding

Public integration is deferred. See:

- [eventual_public_release_path_mediator_note.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/eventual_public_release_path_mediator_note.md)

## Order of work

### 1. Rewrite the paper's object and language

Goal:

- stop writing as if the main substantive object is literally "a missing directed edge"
- keep the missing directed edge as the **retrieval anchor**
- treat the surfaced object as usually a **path-rich** or **mechanism-rich** question

What to do:

- revise abstract, introduction, object-definition sections, examples, and conclusion
- add side-by-side examples:
  - direct-edge anchor
  - path-rich reading
  - mechanism-rich reading
- keep the historical benchmark language clean:
  - the backtest is still about future appearance of direct-link anchors

Variants:

- **Variant A (main):** direct-edge anchor, path/mechanism surfaced object
- **Variant B (reserve):** research-program / path-thickening object with less anchor language

Decision rule:

- keep Variant A unless Variant B is clearly better without weakening the benchmark story

Outputs:

- revised paper draft
- rewrite note
- revised outline
- canonical phrasing bank

### 2. Build the learned reranker on the frozen graph

Goal:

- improve ranking quality without changing ontology

Core design:

- current transparent score remains **retrieval stage**
- learned model reranks only the retrieved pool
- historical target remains:
  - first direct appearance of the missing directed edge within horizon `h`

What to build:

- pair-year training dataset builder
- reranker training/evaluation runner
- model-comparison outputs
- cutoff-stability summary

Candidate pools to try:

- top `10,000`
- top `20,000`

Feature families to try:

- base score only
- structural
- structural + dynamic
- structural + dynamic + composition
- structural + dynamic + composition + boundary/gap

Model variants to try:

- logistic hazard / classifier
- gradient-boosted trees
- learning-to-rank

Evaluation:

- rolling cutoffs spaced every 5 years
- main horizons: `5`, `10`
- appendix horizons: `3`, `15`, `20`
- metrics: `MRR`, `Recall@50/100/500/1000`, frontier summaries
- compare against:
  - transparent score
  - preferential attachment

Decision rule:

- pick one main model and one appendix model
- main model must improve on the transparent score and preferably on preferential attachment at the main horizons
- if no model wins cleanly, keep the transparent score and move on

### 3. Formalize candidate families and build the ripeness panel

Goal:

- turn the new object into something analyzable rather than only better phrasing

Candidate families:

- `path_to_direct`
- `direct_to_path`
- `mediator_expansion`

Path/mechanism phrasing variants to try:

- top-1 mediator path
- top-3 diverse mediator set
- explicit mechanism-choice framing

Ripeness panel units:

- unresolved pair-year for `path_to_direct`
- direct-edge-year for `direct_to_path`

Measures:

- supporting path count
- mediator count
- mediator diversity
- journal spread
- method/evidence spread
- citation/FWCI-weighted local support where available
- support growth
- support age
- local saturation / nearby closure density

Outcomes:

- direct closure within `3/5/10`
- path thickening within `3/5/10`
- remains unresolved

Analyses:

- hazard / survival by ripeness quintile
- monotonicity plots
- transition tables
- pre-closure support growth plots
- reranker vs ripeness agreement analysis

Decision rule:

- keep the phrasing variant that reads best under manual review and nano audit
- only make strong dynamic claims if the ripeness relationship is clear and stable

### 4. Keep the LLM audit as a diagnostic sidecar

Goal:

- use the LLM to explain failure modes, not to become the paper's main validation device

Operational role:

- audit current-era top candidates with `nano`
- use `mini` only on disagreement or hard cases

Use the audit for:

- prune-reason cross-tabs by candidate family
- identifying hub-driven or generic false positives
- spotting ontology-merge problems
- finding candidates that should be rerouted from direct-edge to path or mediator objects
- translating repeated audit reasons into deterministic reranker features or filters

Decision rule:

- only promote an audit-derived signal if it can be approximated deterministically

### 5. Redesign ontology after the stronger paper exists

Goal:

- fix only the ontology problems that still matter after the better object and better reranker are in place

Evidence that can trigger redesign:

- repeated high-cost reranker failures
- repeated path/mechanism review failures
- repeated `ontology_merge_problem` labels from audit
- repeated benchmark mismatch cases that are clearly ontology, not graph-object mismatch

Redesign variants:

- minimal patch
- layered frontier ontology
- full redesign

Decision rule:

- start with the smallest redesign that fixes repeated high-cost errors
- do not redesign the entire graph unless the downstream stack still looks bottlenecked by ontology

## Trial matrix

| Workstream | Main variants | Keep criterion |
|---|---|---|
| Paper object | Variant A vs Variant B | clearer reading without weakening benchmark logic |
| Reranker pool | top `10k` vs top `20k` | better pooled MRR / Recall@K with stable cutoffs |
| Reranker model | logistic / GBT / ranking | better main-horizon performance plus interpretability |
| Feature sets | additive families | improvement over transparent score without obvious instability |
| Path phrasing | top-1 / top-3 / mechanism framing | least generic and most readable under review |
| Ripeness score | simple vs richer support bundle | clearer monotonic relationship with later realization |

## Decision gates

### Gate 1. Paper object

- does the paper now clearly separate retrieval anchor from surfaced question?
- if yes, lock the framing and stop iterating on language except for normal editing

### Gate 2. Reranker

- does at least one reranker beat the transparent score?
- if yes, promote it into the next paper pass
- if no, keep the transparent score and still proceed to ripeness

### Gate 3. Path/mechanism object and ripeness

- do path/mechanism questions read materially better than direct-edge questions?
- does ripeness produce usable structure?
- if yes, make this the paper's main surfaced object

### Gate 4. Ontology redesign

- only open if repeated failures cluster as ontology failures rather than ranking or graph-object failures

## What stays deferred

- public export/UI integration
- broader external benchmark work
- full ontology redesign
- node-birth layer
- large neural temporal graph models

These remain valuable, but not before the current paper object and current graph have been pushed as far as they can go.
