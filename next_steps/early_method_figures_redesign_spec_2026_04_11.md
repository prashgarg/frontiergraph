# Early Method Figures Redesign Spec

## Goal

Redesign the early method figures from scratch so a skeptical new reader can understand the method without reverse-engineering the text.

The figures should explain:

1. what is extracted from one paper
2. how a benchmark candidate first appears
3. what is benchmarked versus what is shown to the reader
4. optionally, why the transparent score favors some candidates

They should not try to teach the full schema, full workflow, or all benchmark details.

## Reader Confusions To Solve

The early visual sequence has to resolve four concrete questions:

1. What exactly is the extraction unit?
2. What does "paper-local" mean?
3. When does a missing-link candidate first exist?
4. Why is the surfaced question richer than the benchmark anchor?

If a reader can answer those four questions, the early method section is doing its job.

## Recommended Figure Set

Use three main-text figures, plus one optional appendix or later main-text figure.

### Main-text Figure A

**Title**
Text excerpt to paper-local graph

**Question answered**
What exactly is extracted from one paper?

**Purpose**
Make the extraction unit concrete and legible. This figure should show that the language model is not constructing a global graph directly. It is recovering one paper's local claim structure.

**Minimum content**
- one lightly cleaned title/abstract excerpt
- 3 to 5 highlighted concepts
- one paper-local graph
- at least one directed claim edge
- at least one contextual support edge

**Visual structure**
- left panel: excerpt with highlighted concepts
- right panel: small graph with 3 to 5 nodes
- short label under graph: "one paper -> one local graph"

**What the caption should say**
- this is the extraction unit
- it is stylized but adapted from a live economics-facing example
- no cross-paper matching has happened yet

**What must not appear**
- ontology matching
- shared graph neighborhood
- red missing-link candidate
- score logic
- walk-forward timeline

### Main-text Figure B

**Title**
Paper-local graphs become a shared candidate neighborhood

**Question answered**
When does the benchmark candidate first appear?

**Purpose**
Show the conceptual move from local graphs to a shared normalized graph. This is the central bottleneck. Readers should see clearly that extraction and matching are separate operations.

**Minimum content**
- two paper-local graphs from different papers
- repeated label or concept visibly shared across them
- one merged shared neighborhood
- one red dashed missing directed link

**Visual structure**
- left: local graph from paper A
- middle: local graph from paper B
- right: merged neighborhood after matching
- arrows between stages
- repeated concept visually emphasized

**What the caption should say**
- the left two panels are separate local graphs
- the right panel exists only after across-paper matching
- the red dashed link is the benchmark candidate anchor

**What must not appear**
- long text excerpts
- full ontology machinery
- surfaced prose question
- feature callouts

### Main-text Figure C

**Title**
Benchmark anchor versus surfaced question

**Question answered**
What is benchmarked, and what is the human-facing object?

**Purpose**
Make the paper's main conceptual distinction explicit. The reader must see that the benchmark event is a missing directed link, while the surfaced question is a richer human-facing object built around that anchor.

**Minimum content**
- narrow benchmark anchor: `u -> v`
- local supporting neighborhood around that anchor
- surfaced research-question rendering
- small timeline or inset for walk-forward timing

**Visual structure**
- left: benchmark anchor only
- center: local neighborhood that supports it
- right: surfaced question object
- small bottom strip or corner inset:
  - freeze at `t-1`
  - check appearance in `[t, t+h]`

**What the caption should say**
- the benchmark object is the dated missing directed link
- the surfaced question is what the reader inspects
- the surfaced question is richer than the benchmark event and should not be treated as identical to it

**What must not appear**
- long score formulas
- many nodes
- dense live-graph picture

### Optional Figure D

**Title**
Why the transparent score likes this candidate

**Question answered**
Why does this candidate rank highly or lowly?

**Purpose**
Explain the transparent score with one graph object, not with abstract feature names alone.

**Minimum content**
- same shared neighborhood used in Figures B and C
- 3 or 4 feature callouts only:
  - path support
  - underexploration gap
  - motif support
  - hub penalty

**Visual structure**
- one shared neighborhood in center
- small annotated callouts around it
- each callout tied to a visible graph property

**What the caption should say**
- this is a stylized logic figure, not a result figure
- the figure exists to make the transparent score readable
- the example is reused so features feel like properties of one object rather than arbitrary covariates

**What must not appear**
- reranker coefficients
- many unrelated examples
- full model comparison

## Recommended Narrative Order

Use the figures in this order:

1. Figure A: extraction unit
2. Figure B: candidate formation
3. Figure C: benchmark anchor versus surfaced question
4. Figure D only if the text still needs score intuition

This sequence teaches:

- one paper
- many papers
- benchmark event
- ranking logic

That is the right pedagogic order for this paper.

## What To Cut From The Current Draft

The redesign implies the following:

- cut the generic workflow figure as a main teaching device
- stop using one figure to show both extraction and cross-paper merging
- stop asking the early sequence to also summarize screening, reranking, and evaluation in a generic pipeline box
- move any dense live-graph "object picture" later, after the extraction and candidate logic are clear

The paper does not need an orientation figure unless it is very small and clearly secondary. The core early figures should teach the empirical object, not the administrative workflow.

## Visual System

Keep one consistent visual language across all early figures.

### Color roles

- blue: directed claim edge
- gray: contextual support edge
- orange or sand fill: shared graph neighborhood
- red dashed: benchmark missing-link anchor
- green accent only if needed for realized future link in a timeline or later figure

### Node treatment

- 3 to 5 nodes per graph in teaching figures
- lightly cleaned labels only
- no unlabeled decorative nodes unless absolutely necessary

### Arrows

- solid arrows between panels for stage transitions
- dashed red only for the missing benchmark link

### Text

- short labels
- no code-like field names
- no schema variable names in the figure body

### Icons

If built in Figma, use simple vector icons for:
- paper/document
- graph/network
- magnifying glass or shortlist only if needed
- clock/calendar for the walk-forward timing inset

Do not use icons decoratively. Each icon should represent an object or action that actually matters.

## Medium Recommendation

### Best option

Build these figures as external vector figures in Figma or PowerPoint/Keynote, then export to PDF or SVG for inclusion in LaTeX.

### Why

- easier layout control
- better icon handling
- cleaner typography and alignment
- faster iteration than TikZ for conceptual figures

### What should still stay in code

- result charts
- benchmark ladders
- regression or heterogeneity visuals
- any figure where the main object is numerical rather than conceptual

## Caption Discipline

Each caption should do four things:

1. say what the figure is for
2. say whether it is stylized or adapted from live examples
3. tell the reader what to look at
4. tell the reader what not to overread

### Example caption patterns

**Figure A**
"This figure shows the extraction unit. One paper becomes one paper-local graph. The example is lightly cleaned from a live economics-facing case, but the layout is stylized. No cross-paper matching has happened yet."

**Figure B**
"This figure shows when the benchmark candidate first appears. The two left panels are separate paper-local graphs. The right panel exists only after repeated labels are matched into shared concepts. The red dashed edge is the benchmark anchor."

**Figure C**
"This figure separates the dated benchmark event from the richer object shown to readers. The benchmark remains the missing directed link; the surfaced question is a human-facing compression built around that anchor."

## Validation Checklist

Before finalizing the redesigned figures, check whether a new reader could answer:

1. What is extracted from one paper?
2. What makes a graph paper-local?
3. When does the missing-link candidate first appear?
4. What is benchmarked prospectively?
5. Why is the surfaced object richer than the benchmark event?

If any answer is unclear, the figures are not done.

## Implementation Order

1. Freeze the figure logic in this note.
2. Build rough wireframes for Figures A, B, and C outside LaTeX.
3. Review the wireframes before polishing style.
4. Only after the visual logic is approved, replace the early method figures in the paper.
5. Then port the same figure family into the seminar deck.

## Bottom-Line Recommendation

The paper should not open with a generic pipeline figure.

It should open with:

1. what one paper contributes
2. how multiple papers generate a benchmark candidate
3. what is benchmarked versus what is read

That is the minimum visual logic required to make the methodology legible.
