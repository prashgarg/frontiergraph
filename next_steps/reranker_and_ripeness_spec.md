# Reranker and Ripeness Spec

Status: historical design note from 2026-04-05. It remains useful as an implementation
reference for existing reranker feature families and ripeness-panel ideas, but it is now
superseded as the governing redesign document by `next_steps/method_v2_design.md`,
which is anchored on the frozen ontology `v2.3` baseline.

Date: 2026-04-05

This note gives the concrete implementation spec for Phases 2 to 4 of the frozen-ontology plan.

## 1. Learned reranker

### Goal

Improve shortlist quality on the current graph without changing ontology.

### Unit of observation

- one row per candidate ordered pair `(u,v)` at cutoff year `t`
- only candidates returned by the current retrieval stage

### Label

Primary label:

- `appears_within_h`
  - equals 1 if direct edge `u -> v` first appears between `t` and `t+h`

Horizons:

- main: `5`, `10`
- appendix: `3`, `15`, `20`

### Candidate pools

Try both:

- top `10,000`
- top `20,000`

### Feature sets

#### Set A. Base

- current total score only

#### Set B. Structural

- score components
- path count by length
- path support norm
- mediator count
- motif count
- co-occurrence count
- hub penalty terms
- endpoint in/out degree

#### Set C. Structural + dynamic

- endpoint degree growth
- recency-weighted support
- mediator growth
- local support acceleration
- closure density nearby

#### Set D. Structural + dynamic + composition

- journal spread
- method/evidence spread
- stability-weighted support
- citation/FWCI-weighted support where available

#### Set E. Structural + dynamic + composition + boundary/gap

- novelty type
- cross-field indicator
- boundary/gap flags
- local saturation

### Model variants

- logistic classifier / hazard-style model
- gradient-boosted trees
- learning-to-rank model

### Training protocol

- evaluate at 5-year spaced cutoffs
- for cutoff `t`, train only on earlier cutoffs `< t`
- earliest cutoffs without enough history keep the transparent baseline only

### Evaluation

Metrics:

- `MRR`
- `Recall@50`
- `Recall@100`
- `Recall@500`
- `Recall@1000`
- frontier summaries

Baselines:

- current transparent score
- preferential attachment

Selection rule:

- choose one main model and one appendix model
- main model should improve on:
  - transparent score
  - preferably preferential attachment
- also require:
  - stable cutoffs
  - readable feature importance or coefficients

### Deliverables

- candidate-pool builder
- reranker training/eval runner
- model-comparison table
- frontier plots
- cutoff-stability note

## 2. Candidate-family formalization

### Families

#### A. `path_to_direct`

- unresolved direct edge
- nearby supporting path already exists
- direct edge later may appear

#### B. `direct_to_path`

- direct edge already exists
- later papers add mediator structure around it

#### C. `mediator_expansion`

- unresolved endpoint pair
- main open question is which mediator carries the link

### Surfaced phrasing variants to compare

- top-1 mediator path
- top-3 diverse mediator set
- explicit mechanism-choice framing

### Selection rule

- use manual review plus nano audit
- keep the version that is:
  - most readable
  - least generic
  - closest to the local evidence

## 3. Ripeness panel

### Units

- unresolved pair-year for `path_to_direct`
- direct-edge-year for `direct_to_path`

### Annual measures

- supporting path count
- mediator count
- mediator diversity
- journal spread
- method/evidence spread
- stability-weighted support
- citation/FWCI-weighted support where available
- support growth
- support age
- nearby closure density

### Outcomes

- direct closure within `3/5/10`
- path thickening within `3/5/10`
- remains unresolved

### Analyses

- hazard / survival by ripeness quintile
- monotonicity plots
- transition tables
- pre-closure support growth
- compare reranker top sets to ripeness top sets

### Main question

Does the graph become more useful when the object is interpreted as:

- a direct closure candidate
- a mechanism-thickening candidate
- or a broader path-rich question?

## 4. LLM audit sidecar

### Role

- current-era diagnostic tool only
- not the main historical validation device

### Default model

- `nano` for bulk audit
- `mini` only for disagreement subsets or hard cases

### Output fields to use

- keep / downrank / drop
- main reason
- better formulation
- deterministic implication

### Main uses

- cross-tab prune reasons by candidate family
- identify generic/hub-driven false positives
- identify weak-mechanism candidates
- identify path or mediator rerouting cases
- turn repeated reasons into deterministic reranker features or filters

### Promotion rule

- only add an audit-derived signal to the reranker if it can be approximated deterministically

## 5. Recommended immediate sequence

1. build reranker dataset
2. run model grid on the current retrieval pool
3. formalize candidate families and phrasing variants
4. build ripeness panel
5. use the audit as a diagnostic overlay on the resulting shortlists
