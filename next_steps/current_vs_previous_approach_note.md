# Current vs Previous Approach Note

Date: 2026-04-09

## Purpose

This note is a separate project-history record, not part of the main paper.

Its job is to document how the project has changed from the earlier public version to
the current frozen-ontology and method-v2 direction. That is useful for:

- internal memory
- future polishing into a public technical note
- readers who have seen earlier public materials and want to understand what changed

The main paper should remain self-contained and should not depend on this comparison note
to define its empirical object or justify its claims.

## Why this note must stay separate

The current paper should read as one coherent object on its own terms. Pulling legacy
ontology choices, legacy benchmark framing, or older results into the main text would
make the paper harder to read and easier to attack.

So the rule is:

- main paper: state the current object, current benchmark, current ontology baseline
- separate note: explain project evolution and what improved

## High-level comparison

| Dimension | Previous approach | Current approach |
|---|---|---|
| Ontology inventory | Narrower and more endogenous; earlier public materials still leaned on the small FG3C-style concept inventory or pre-freeze v2 language | Frozen `v2.3` baseline with `154,359` rows, broad structured-source coverage, reviewed family rows, and explicit provenance rules |
| Grounding story | Easier to read as binary or thresholded matching, with more risk that ontology weakness mechanically changed what counted downstream | Open-world and tiered; raw labels remain visible, broader grounding is explicit, unresolved states are explicit, and freeze policy is conservative |
| Label cleanup | Less explicit distinction between source truth and paper-facing cleanup | Raw source fields remain immutable; `display_label` is a separate paper-facing cleanup layer |
| Hierarchy | More implicit reliance on inherited or source-native structure | Reviewed `effective_parent_*` / `effective_root_*` overlay, with flatness preserved where hierarchy would be forced |
| Benchmark framing | Easier to read as “transparent graph score versus preferential attachment” | More honest separation: transparent retrieval layer, learned reranker as strongest benchmark comparator, compact benchmark family |
| Surfaced object | Missing-link anchor and human-facing question could blur together | Explicit anchor versus surfaced object split, with path/mechanism rendering treated as interpretation on top of the anchor |
| Ontology role in paper | Risked looking like part of the main empirical claim | Treated as support infrastructure for grounding and interpretation |
| Shortlist pathology handling | Redundancy and sink concentration were observed but not yet separated cleanly from ontology | Concentration control is now a separate method-design problem, not an ontology patch |
| Validation path | Historical backtest did most of the work | Historical anchor remains, but human-usefulness validation is now an explicit next layer |

## What genuinely improved

### 1. The ontology is now more defensible

The most important ontology gain is not just that the inventory is larger. It is that the
current baseline is better disciplined:

- raw provenance is preserved
- paper-facing cleanup is explicit
- hierarchy overlays are reviewed rather than assumed
- broad roots are allowed instead of being forced upward
- ambiguous containers are explicit rather than silently prettified
- unresolved backlog is parked instead of hidden

That makes the ontology easier to defend academically, even when it stays flat in some places.

### 2. The benchmark story is more honest

The earlier project could be read too easily as if the transparent graph score itself were
the headline winner. The current view is more disciplined:

- the transparent score is the readable first-stage screen
- once the benchmark family is widened, the transparent score does not remain the strongest comparator
- the learned reranker is the main graph-screening winner in the current results

That is a more credible paper, even if it is a less flattering headline.

### 3. The paper’s empirical hierarchy is cleaner

The current project separates:

- ontology support layer
- benchmark anchor
- surfaced research question
- reranking layer
- concentration-control layer

That is a major conceptual improvement over earlier drafts where those pieces were easier to conflate.

### 4. The surfaced object is better motivated

The project now has a clearer reason for presenting path-rich or mechanism-rich questions.
They are not replacing the benchmark anchor. They are the human-facing reading of a narrow
historical object. That distinction is much cleaner than before.

## What is not yet a fair “before versus after” comparison

Some comparisons would be misleading if presented casually.

### Do not compare raw counts without labeling the object

Examples:

- frozen ontology rows versus active benchmark-graph concepts
- pre-freeze ontology rows versus frozen ontology rows
- old shortlist outputs versus new candidate families

Those are different objects and must be labeled as such.

### Do not present legacy and current ranking numbers as one clean horse race

If the candidate universe, ontology baseline, target family, or benchmark family changes,
the ranking outputs are not directly comparable without saying so.

The right comparison language is:

- “earlier benchmark under earlier object definition”
- “current benchmark under current object definition”

not:

- “the model improved from X to Y” unless the evaluation object is genuinely held fixed

### Do not use the comparison note to backfill the main paper’s claims

This note can explain how the project matured. It should not become a second hidden source
of evidence for the main paper.

## Public-release considerations

If this note becomes public later, it should follow five rules.

### 1. Timestamp everything

Readers need to know which note reflects:

- archived public versions
- frozen ontology `v2.3`
- pre-method-v2 results
- post-method-v2 results, when those exist

### 2. Separate project evolution from empirical evidence

This note should say how the project changed and why. It should not pretend to be the
paper’s main validation document.

### 3. Be candid about what changed because the objective changed

Some improvements reflect better engineering or better ontology discipline.
Others reflect a sharper statement of what the paper is actually about.
Those are both real improvements, but they are not the same thing.

### 4. Keep old work visible but archived

Older materials should not be erased. They should be labeled clearly as:

- archived
- superseded
- historically useful but not current

### 5. Avoid triumphalist language

The right tone is:

- this is how the project evolved
- this is what became more defensible
- this is what remains unfinished

not:

- the old project was wrong and the new one solved everything

## Recommended public framing later

If this note is polished into a public companion note, its safest framing is:

“Project evolution and design clarification note”

rather than:

“new results versus old results”

because the biggest change is conceptual clarification and pipeline discipline, not just a
single metric improvement.

## Current status

As of this note:

- ontology baseline is frozen at `v2.3`
- main paper has been rewritten to use that frozen ontology story only
- method-v2 redesign is specified but not yet implemented
- human-validation plan exists but ratings do not yet exist

So this note should currently be read as:

- a comparison of project architecture and empirical framing
- not yet a final before/after results report
