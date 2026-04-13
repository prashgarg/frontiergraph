# Shortlist Cleanup Method

## Purpose

This note records the **general, reusable method** for cleaning and reviewing the surfaced current frontier shortlist.

The goal is not perfect reproducibility in every implementation detail. The goal is a process that is:
- **stable enough** to run again after methodology changes
- **defensible enough** to compare before and after ontology redesign
- **modular enough** that we can improve one layer without changing the whole interpretation

This note applies to the **surfaced current shortlist**, not the historical backtest itself.

## What this method is for

The cleanup layer exists because the historical ranking model and the surfaced human-facing question object are not the same thing.

The ranking layer may be historically useful while the surfaced shortlist still contains:
- method artifacts
- metadata/container nodes
- unresolved code labels
- very broad container concepts
- near-duplicate question families
- awkward semantic redundancies

So the cleanup stage is the standard bridge between:
- **historical discovery model**
and
- **human-inspectable frontier question**

## What must stay fixed during a cleanup pass

To keep the cleanup exercise interpretable, the following should be treated as fixed for one pass:
- ontology version
- extraction pipeline
- retrieval score
- learned reranker

The cleanup pass is allowed to modify only the **surfaced presentation/routing layer**.

If one of the above core layers changes, record that as a new run context and rerun the cleanup procedure from the top.

## Standard inputs

A cleanup pass should start from these inputs:

1. **Current reranked frontier table**
- candidate pairs
- reranker ranks/scores
- transparent ranks/scores
- endpoint labels
- top mediators
- top paths

2. **Concept label index**
- current best label mapping for surfaced concepts

3. **Current path/mechanism renderer**
- the current logic used to convert surfaced pairs into path or mechanism questions

4. **Review note from previous pass**, if any
- to track recurring failure modes and compare whether a new pass is better

## Standard cleanup sequence

### Step 1. Surface-endpoint quality filtering

Apply deterministic penalties to endpoints that are poor surfaced objects.

These penalties should be:
- rule-based
- documented
- interpretable
- limited to the surfaced shortlist only

Typical categories:
- `method_like`
- `metadata_like`
- `unresolved_code` when the displayed label is still opaque
- `generic_like` for a small, documented set of broad container terms

What this step is trying to fix:
- obvious artifacts
- non-substantive endpoints
- broad labels that crowd the top of the human-facing shortlist

What this step is **not** trying to do:
- improve the historical benchmark score
- redefine ontology
- semantically deduplicate the shortlist

### Step 2. Path/mechanism rendering

Render surfaced pairs into:
- `path_question`
- `mediator_question`
- rare `direct_edge_question`

This should use a fixed and documented routing rule for the pass.

The important point is not that the exact path/mediator split is permanent. The important point is that the surfaced object should usually be:
- path-rich, or
- mechanism-rich

This is the standard place where the paper’s substantive object becomes visible.

### Step 3. Manual review of the top surfaced shortlist

Do a human review on the top slice, typically:
- top `25`
- top `50`
- top `100`

Each surfaced question should be assigned one of the following labels:
- `strong`
- `readable_but_redundant`
- `readable_but_weak`
- `label_problem`
- `ontology_problem`

Definitions:

- `strong`
  The question reads naturally, looks substantive, and feels like a plausible research frontier object.

- `readable_but_redundant`
  The question is understandable, but it is too similar to another surfaced question or family already present.

- `readable_but_weak`
  The question is readable, but it still feels too broad, thin, or unconvincing.

- `label_problem`
  The underlying object may be fine, but unresolved or awkward labels make the surfaced question poor.

- `ontology_problem`
  The weakness appears to come from concept granularity, bad merging, broader/narrower confusion, or another structural ontology issue.

This review is the main bridge between cleanup and later ontology redesign.

### Step 4. Semantic redundancy review

After the first manual pass, review whether the surfaced shortlist suffers from:
- repeated endpoint families
- near-duplicate targets
- semantically equivalent question variants
- repetitive path/mechanism framing for essentially the same object

If yes, record the redundancy pattern in one of three ways:
- repeated source family
- repeated target family
- near-equivalent semantic object

This step exists to distinguish:
- ranking failure
from
- semantic crowding in the surfaced shortlist

### Step 5. Mediator label review

Inspect the `why` and mechanism text for unresolved or poor mediator labels.

Classify problems as:
- `acceptable_mediator_noise`
- `mediator_label_problem`
- `mediator_ontology_problem`

This matters because a surfaced question can be good overall while its explanation layer is still poor.

### Step 6. Decide what kind of fix is warranted

At the end of the pass, assign each major failure mode to one of these buckets:
- `cleanup_layer_fix`
- `presentation/routing_fix`
- `label_mapping_fix`
- `ontology_fix`

This is the most important discipline in the process.

The point is to avoid jumping to ontology redesign when the real issue is just:
- bad surfaced wording
- poor semantic deduplication
- weak mediator display labels

## Standard outputs

Every cleanup pass should produce:

1. **Updated surfaced frontier table**
- with the active penalties and surfaced ranks

2. **Rendered path/mechanism shortlist**
- CSV or JSONL
- reviewable markdown note

3. **Review summary**
- counts by review label:
  - `strong`
  - `readable_but_redundant`
  - `readable_but_weak`
  - `label_problem`
  - `ontology_problem`

4. **Failure-mode note**
- what improved
- what still looks off
- whether the next fix belongs to cleanup or ontology

## What we compare across passes

The right comparison is not just numeric.

We should compare:

### Quantitative
- share of surfaced top `K` with obvious artifacts
- share of surfaced top `K` with unresolved labels
- route-family counts (`path`, `mediator`, `direct`)
- concentration by repeated endpoint family

### Qualitative
- how many top questions look genuinely `strong`
- how many are merely readable
- how many are redundant
- how many reveal ontology problems directly

### Structural
- whether the same weak concept families keep recurring
- whether failure modes move from:
  - artifact problems
  to
  - semantic redundancy
  to
  - ontology limitations

## How to use this after ontology redesign

After any ontology revamp, rerun the same broad procedure:

1. build current reranked frontier
2. apply surfaced-endpoint quality filtering
3. render path/mechanism shortlist
4. manually review the top slice
5. classify failure modes
6. compare against the prior ontology version

The comparison question should be:

**Did the ontology redesign reduce the share of problems that are truly ontological, rather than merely shifting wording?**

That is the defensible standard.

## Decision rule for ontology redesign

The cleanup process should trigger ontology redesign only if repeated failures are mainly:
- `ontology_problem`
- unresolved important labels that are not fixable by label mapping
- broader/narrower confusion that keeps generating weak questions
- repeated merged concepts that survive cleanup and deduplication

If most failures are instead:
- `readable_but_redundant`
- `readable_but_weak`
- `label_problem`

then the next step should stay in the cleanup/presentation layer, not ontology.

## Current working interpretation

At the current stage of the project, the method suggests:
- the historical reranker is useful
- the surfaced question object should usually be path/mechanism based
- endpoint-quality filtering is necessary
- the next remaining problem is increasingly semantic redundancy and label quality
- ontology redesign is approaching, but should still be evidence-led

## Bottom line

This cleanup method is meant to be rerunnable and defensible.

It gives us a standard way to say:
- what the surfaced shortlist looked like
- what kind of fixes we applied
- what improved
- what still appears to be a genuine ontology limitation

That is the level of stability we need before and after ontology redesign.
