# Candidate Generation v3 Specification

Date: 2026-04-10

## Purpose

This note specifies the next upstream pass on the frozen ontology baseline.

The immediate problem is no longer just reranking. The current `85` surfaced frontier is
less crowded than before, but many top items are still broad, anchored, and only weakly
paper-like. That failure begins upstream:

- some candidate questions are too weakly framed before the reranker ever sees them
- some broad anchored `path_to_direct` objects enter the candidate universe too easily
- some endpoint pairs are surfaced without a strong enough endpoint-plus-mediator
  compression

So the next pass should focus on candidate generation rather than another marginal
reranker tweak.

## 1. Empirical object

The empirical object remains:

- an endpoint-centered research question
- optionally with a focal mediator or short path
- supported by a local graph evidence bundle

The generator is not trying to recover every graph motif as a separate prediction task.
It is trying to produce readable, benchmarkable question objects.

That means the generator should prefer:

- endpoint question
  - “does `A` affect `C`?”
- endpoint-plus-mediator question
  - “does `B` mediate `A -> C`?”

over raw motif objects such as:

- arbitrary four-node motifs
- branch-heavy local neighborhoods without a clear focal relation
- generic broad endpoint pairs with no clear substantive route

## 2. Why candidate generation deserves first-class attention now

The current stack uses a standard retrieval-then-rerank design:

1. candidate generation
2. transparent retrieval score
3. learned reranker
4. concentration control
5. surface-layer reshaping

This architecture is sensible and is consistent with the retrieval/ranking logic used in
search and recommender systems. The important implication is:

- reranking can only improve the candidates it is given

So if the candidate object is weak, later ranking layers can only partially rescue it.

This motivates moving candidate generation upstream in the design conversation.

Useful literatures for motivation:

- two-stage candidate-generation and ranking systems
  - e.g. Covington, Adams, and Sargin (2016)
- learning-to-rank
  - because the reranker should not be asked to solve bad retrieval
- literature-based discovery
  - e.g. Swanson (1986) and follow-on work
- scientific knowledge-graph discovery
  - where candidate generation and pruning are central

Important companion note:

- `next_steps/candidate_generation_historical_vs_screening_note.md`

That note should be read together with this one. The current broad-anchored gate is
promising as a current-frontier screening rule, but it is not yet established as a
historically validated generator improvement.

## 3. Current diagnosis

The main current weaknesses are:

Using the current rebuilt frontier in:

- `outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv`

and the audit in:

- `outputs/paper/86_candidate_generation_v3_audit_from_85/candidate_generation_v3_audit.md`

the current top-100 by horizon is:

- `100%` anchored progression
- `100%` `candidate_subfamily = causal_to_identified`
- about `73–79%` weak-compression cases
- about `81–85%` serial single-mediator cases
- about `16–19%` broad anchored low-signal cases even after the current surface layer

So the failure is now quite clear: the stack is not mainly surfacing fully open questions.
It is surfacing broad anchored progression objects that remain too weakly compressed.

### A. Broad anchored progression is still overrepresented

Many surfaced top items are in:

- `candidate_scope_bucket = anchored_progression`
- especially `candidate_subfamily = causal_to_identified`

This is historically meaningful, but often too broad to read as a good paper question.

### B. Endpoint compression is still too weak

Some candidates surface as:

- broad endpoint pair
- with a weak or generic mediator
- or with no paper-like mechanism compression

This creates items that are graph-plausible but not especially sharp.

### C. Family assignment is still semantically coarse

The current family system is much better than before, but some items still enter the same
headline family even though they differ sharply in how open, anchored, or mechanism-like
they really are.

### D. The local evidence object is still underused at generation time

We now carry a richer evidence bundle, but the generator still does not make enough use of
it to suppress weakly framed or overly generic candidates early.

## 4. Design principles for v3

### Principle 1: Candidate generation should optimize for question quality, not raw motif coverage

Not every real motif should become a candidate.

The generator should produce candidates that are:

- benchmarkable
- readable
- compressible into a paper-like question

### Principle 2: Family assignment should be deterministic and stricter

The same local graph should not drift across families depending on downstream handling.

Once the frozen graph and cutoff are fixed, family assignment should be deterministic.

### Principle 3: Compression should happen at generation time, not only in presentation

If a candidate needs a focal mediator or route to make sense, that should be reflected in
the candidate object itself, not only in later wording cleanup.

### Principle 4: The generator should reject some plausible neighborhoods

This is important.

A neighborhood can be:

- graph-plausible
- historically common
- and still not sharp enough to deserve entry into the candidate pool

So candidate generation should not maximize recall alone. It should also screen out weakly
framed objects.

### Principle 5: Generic rules only

Do not solve repeated `Willingness to Pay` or repeated `Innovation` by hard-coding those
concepts.

Use generic graph- and ontology-based rules:

- broadness
- resolution
- specificity
- family repetition
- evidence strength

### Principle 6: Distinguish generator improvement from current-frontier screening

Some generic rules may improve the surfaced current shortlist without yet showing a
clear historical effect on the candidate universe. Those should be treated as
current-frontier screening rules, not as historically validated generator changes.

Generator-time rules should only be promoted into the historical method layer after:

- showing bite on historical panels
- preserving or improving retrieval quality at fixed budgets
- showing robustness across nearby thresholds

## 5. Recommended v3 changes

## 5.1 Stronger family assignment

### Current problem

The current family/subfamily tags are informative, but still too permissive for broad
anchored progression.

### Change

Introduce a deterministic assignment sequence:

1. direct-path thickening check
   - if direct edge exists and path is missing, evaluate `direct_to_path`
2. anchored endpoint progression check
   - if direct relation already exists in contextual or ordered form, route to the relevant
     anchored `path_to_direct` subfamily
3. mediator-expansion check
   - if the main open object is mediator differentiation rather than direct closure, emit
     `mediator_expansion`
4. fully open `path_to_direct` only as fallback

### Goal

This should reduce the number of broad cases entering as undifferentiated headline
`path_to_direct`.

## 5.2 Better gating of broad anchored `path_to_direct`

### Current problem

Some broad anchored cases are historically plausible but too textbook-like.

### Change

For anchored progression candidates, require at least one of:

- strong path support
- high mediator specificity
- nontrivial topology evidence
- sufficiently high endpoint resolution

Candidates that are:

- broad on both endpoints
- weakly resolved
- and weakly mediated

should fail candidate generation rather than merely being pushed down later.

### Goal

Move some of the current surface-layer work upstream.

### Current status

The first narrow threshold sweep suggests that the current broad-anchored gate has
more support as a current-frontier cleanup rule than as a historical generator
change. So this item remains open in the historical-generator track even though the
same logic may still be useful in a surfaced-shortlist track.

## 5.3 Better endpoint-plus-mediator compression

### Current problem

The current system still carries some candidates that only become interpretable after
manual rewriting.

### Change

Add generator-time fields such as:

- `focal_question_type`
  - `endpoint`
  - `endpoint_plus_mediator`
  - `direct_path_thickening`
- `compression_confidence`
- `compressed_triplet_json`
  - focal `A -> M -> C` object if available
- `compression_failure_reason`
  - if the neighborhood is real but too diffuse to compress cleanly

Compression rule:

- if one mediator dominates on specificity and support, emit endpoint-plus-mediator
- if several parallel mediators remain close, emit endpoint question plus mediator set
- if no mediator is informative, either suppress the candidate or keep it as an endpoint
  question only if the endpoints are sharp enough on their own

### Goal

Reduce graph-plausible but semantically weak candidates.

## 5.4 Richer local evidence object at generation time

### Current problem

We already store evidence tags, but generation still does not use enough of that
information to decide whether a candidate deserves entry.

### Change

Make the generator consume:

- motif count and motif type
- closure density
- branch structure
- mediator concentration
- support provenance mix
- broadness and resolution

to form eligibility rules, not just downstream diagnostics.

### Goal

Upgrade the candidate object from “pair plus support” to “screened local question object.”

## 5.5 Leave node activation as a separate extension

Dormant-node and node-activation problems remain important, but they should stay out of
this v3 pass. This pass is still about better question generation among currently grounded
nodes.

## 6. Candidate-generation success criteria

Candidate generation should be judged on more than final shortlist aesthetics.

### Historical criteria

- higher positive rate inside the candidate universe
- better recall of future positives at fixed retrieval budgets
- higher reranker headroom at fixed pool size
- better family consistency across cutoffs

### Semantic criteria

- fewer broad or textbook-like surfaced top items
- fewer unresolved or weakly compressed candidates
- more readable endpoint or endpoint-plus-mediator objects

### Coverage criteria

- good performance not just overall, but within broad fields
- candidate universe should not collapse into one or two overactive literatures

## 7. What improvements should we realistically expect?

Do not expect candidate generation v3 to deliver a miraculous jump in headline MRR by
itself.

The likely gains are:

- cleaner candidate pool
- better retrieval purity
- fewer semantically weak top candidates
- better use of reranker capacity
- a more defensible current frontier

That is exactly the kind of gain we need right now.

## 8. Alternatives and why not choose them now

### Alternative 1: Keep current candidate generation and rely on the LLM later

Why not:

- that would use the LLM to patch over an upstream design problem
- it would make it harder to say what the graph method itself is doing well or badly

### Alternative 2: Expand top-level candidate families aggressively

Why not:

- too many family types become hard to benchmark and explain
- richer motif vocabulary should mostly stay in the evidence layer

### Alternative 3: Generate all broad pairs and let ranking sort them out

Why not:

- this is exactly what is currently creating broad, textbook-like surfaced items
- weak retrieval objects waste downstream ranking capacity

### Alternative 4: Move directly to embeddings or fully semantic generation

Why not:

- harder to interpret
- easier to overfit semantically
- weakens the paper’s graph-based historical design before we have exhausted the graph-native fixes

## 9. Proposed implementation order

### Step 1. Audit the current candidate pool by failure mode

Create a structured audit on the current `85` frontier and the historical panel:

- broad anchored progression
- weak endpoint compression
- generic mediator
- diffuse local evidence
- family-assignment ambiguity

### Step 2. Implement stricter generator-time gates

Add generation rules for:

- broad anchored progression eligibility
- compression failure
- stronger mediator specificity thresholding

### Step 3. Add compression fields to the candidate row

Add:

- `focal_question_type`
- `compression_confidence`
- `compressed_triplet_json`
- `compression_failure_reason`

### Step 4. Rebuild the candidate feature panel

Re-run the historical panel and compare:

- positive rate
- retrieval recall by pool size
- reranker performance at fixed pool size

### Step 5. Rebuild the current frontier and inspect manually

Only after the candidate object improves should we revisit:

- the paper-facing shortlist
- and any eventual LLM paper-worthiness pass

## 10. Recommended companion work right after v3

The next two notes and evaluations should follow immediately after this:

- `retrieval_budget_eval_note.md`
  - pool sizes `500, 2000, 5000, 10000`
  - multi-`K` recall and positive-rate curves
- `field_overlay_eval_note.md`
  - broad field-conditioned top-`K`
  - macro coverage across `10–20` broad fields

This is the right way to make the upstream design paper-defensible before adding an LLM layer.

## Bottom line

Candidate generation v3 should not try to invent a new frontier objective. It should do a
more disciplined version of the same job:

- decide more carefully which question objects exist
- compress them more sharply
- reject more weakly framed broad anchored cases
- and hand a better pool to retrieval and reranking

That is the highest-leverage next upstream move.
