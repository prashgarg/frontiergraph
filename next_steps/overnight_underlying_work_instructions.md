# Overnight Underlying Work Instructions

## Mission

Work overnight on **underlying paper improvements**, not on presentation polish.

The target is to strengthen the paper’s empirical claim and screening interpretation using the already stabilized stack:

- missing-link benchmark anchor
- surfaced path/mechanism question
- routed overlays as extensions
- frozen ontology-vNext support layer

Do not treat this as an invitation to reopen the ontology or rewrite the paper again.

## Core rule

If a task improves:

- benchmark credibility
- surfaced-object interpretation
- screening quality
- validation strength

it is in scope.

If it mainly improves:

- visual presentation
- wording only
- ontology expansion
- new family growth

it is out of scope for the overnight pass.

## Fixed constraints

Keep all of these fixed unless a pass explicitly proves they need revision:

- reviewed family count remains `6`
- family seed rows remain `25`
- routed shortlist logic remains unchanged
- no new family promotion
- no ranking redesign from scratch
- ontology-vNext stays frozen except for reviewed override maintenance
- the paper’s main example roles stay fixed

## Primary overnight sequence

## Phase 1. Stronger transparent baselines

### Goal

Answer whether the current graph score beats more than just preferential attachment.

### Tasks

1. Inspect the existing benchmark and historical evaluation scripts.
2. Add `2-3` transparent comparator scores:
   - degree + recency baseline
   - directed common-neighbors or directed triadic-closure baseline
   - simple endpoint lexical similarity baseline
3. Run them on the same historical evaluation setup already used by the paper.
4. Produce:
   - top-`K` comparison table
   - hit-rate comparison
   - overlap comparison with the graph shortlist
   - one note describing where the graph score wins and where it does not

### Deliverables

Suggested outputs:

- `outputs/paper/37_benchmark_expansion/`
- `next_steps/benchmark_expansion_note.md`

### Stop condition

Do not add more baselines after these three unless one clearly fails for a trivial reason.
The goal is a stronger transparent comparison, not benchmark sprawl.

## Phase 2. Surfaced-object ablation

### Goal

Show what is gained by moving from raw endpoint pairs to path/mechanism questions and then to routed overlays.

### Tasks

1. Define three comparison layers:
   - endpoint-only
   - endpoint + path structure
   - endpoint + path structure + routed overlays
2. Use the same evaluation sample where possible.
3. Compare:
   - historical performance
   - shortlist composition
   - qualitative readability and specificity on a small review sample
4. Write a short conclusion:
   - what the path/mechanism layer adds
   - what overlays add beyond that

### Deliverables

Suggested outputs:

- `outputs/paper/38_object_ablation_review/`
- `next_steps/object_ablation_note.md`

### Stop condition

If the overlays do not add much on average, do not force the result.
Record that they are selective improvements and move on.

## Phase 3. Redundancy audit and light diversification test

### Goal

Treat semantic crowding as a screening-quality issue rather than a purely editorial problem.

### Tasks

1. Audit the top `20`, `50`, and `100` surfaced rows for:
   - repeated source families
   - repeated target families
   - repeated theme neighborhoods
   - repeated hubs such as CO2-centered neighborhoods
2. Build a compact redundancy summary.
3. Test one light diversification rule only:
   - neighborhood penalty
   - or one-row-per-neighborhood before repeats
   - or simple max-marginal-relevance style rerank
4. Compare:
   - historical quality
   - coverage across distinct neighborhoods
   - whether the top slice looks more useful for attention allocation

### Deliverables

Suggested outputs:

- `outputs/paper/39_redundancy_audit/`
- `next_steps/redundancy_audit_note.md`

### Stop condition

If diversification worsens historical quality substantially, keep it as a paper-facing curation idea rather than a system change.

## Phase 4. Routed-overlay validation

### Goal

Demonstrate whether context-transfer and evidence-type-expansion actually improve question usefulness.

### Tasks

1. Sample a balanced routed set:
   - `10-15` context-transfer rows
   - `10-15` evidence-type-expansion rows
2. Pair each routed row with its unrouted baseline version.
3. Review each pair on:
   - specificity
   - actionability
   - interpretability
   - likely usefulness to a researcher
4. Summarize:
   - where overlays help clearly
   - where overlays merely restate the base question

### Deliverables

Suggested outputs:

- `outputs/paper/40_overlay_validation/`
- `next_steps/overlay_validation_note.md`

### Stop condition

Do not turn this into a new ranking pass.
This is a validation pass.

## Phase 5. Human or expert-judgment pilot if time remains

### Goal

Add direct support for the “screening under attention constraints” interpretation.

### Tasks

1. Build a small rating pack of `20-30` rows.
2. Compare graph-selected and baseline-selected rows.
3. Include ratings for:
   - novelty
   - plausibility
   - usefulness
   - readability
4. If no external rater is available overnight, prepare the pack and rubric so it can be run the next day.

### Deliverables

Suggested outputs:

- `outputs/paper/41_human_validation_pack/`
- `next_steps/human_validation_plan.md`

## Overnight priorities if time is limited

If the overnight window is shorter than expected, do this order and stop once quality starts to fall:

1. stronger baselines
2. surfaced-object ablation
3. redundancy audit
4. overlay validation

The first two are the most likely to materially change the paper’s underlying claim.

## How to decide whether a pass changed the paper

At the end of each phase, write one sentence answering:

- did this pass materially change what the paper can credibly claim?

Use these thresholds:

- **yes** if it strengthens or weakens the main benchmark story
- **yes** if it clarifies what the surfaced object adds
- **yes** if it changes the interpretation of screening quality
- **no** if it only improves examples or phrasing

## Required notes to leave behind

Even if a pass is incomplete, leave:

1. a short methods note
2. a summary of outputs created
3. a list of unresolved questions
4. a direct recommendation for the next pass

Do not leave behind an unfinished folder with no interpretation.

## Do-not-do list

Do not spend the night on:

- new ontology families
- new policy-semantic expansion
- prompt retuning
- more display-phrasing cleanup
- new paper rewrite cycles
- open-ended robustness trees before the first three phases are done

## Validation requirements

For every overnight phase:

- use local artifacts only unless there is a clear reason not to
- keep comparison samples aligned with the current paper benchmark
- do not silently change the routed shortlist or ranking behavior
- document any assumption that could affect interpretation
- verify outputs are reproducible from scripts, not just ad hoc inspection

## Morning handoff format

By the end of the overnight pass, produce one handoff note with:

1. what was completed
2. what materially changed the paper
3. what failed or stayed inconclusive
4. what the next best move is

If nothing materially changes the paper, say that plainly.

## Bottom line

The overnight job is to answer the next real empirical questions:

1. does the graph screen still beat stronger simple baselines?
2. what does the surfaced path/mechanism object add over raw endpoints?
3. can the shortlist allocate attention across distinct ideas instead of crowding the same neighborhoods?

If those questions get better answers, the paper gets better at its core, not just in how it looks.
