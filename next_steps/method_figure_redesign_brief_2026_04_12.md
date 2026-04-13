# Method Figure Redesign Brief

Date: 2026-04-12

## Bottom line

The current Mermaid-based figures are now clear enough to function in a draft, but they are not yet beautiful in the paper-design sense. The right next move is not to keep tuning all three equally. They should be split into:

- Figure 2: keep, with minor polish only
- Figure 3: keep, with minor polish only
- Figure 5: redraw from scratch

The reason is simple. Figures 2 and 3 have good logic and acceptable composition. Figure 5 has good logic but weak composition. More micro-edits to Figure 5 in Mermaid are unlikely to make it elegant.

## General diagnosis

The current figures succeed on:

- one question per figure
- worked-example consistency
- benchmark-anchor versus surfaced-question distinction
- avoiding generic workflow art

They are weaker on:

- visual hierarchy
- panel proportion
- annotation economy
- compositional elegance

In all three figures, labels still carry too much of the explanatory burden. The best redesigns will let geometry and color do more of the work and reserve text labels for only the indispensable distinctions.

## Figure 2

Current role:
- one paper becomes one paper-local graph

Current judgment:
- conceptually correct
- visually clean enough
- not especially elegant, but already serviceable

Recommendation:
- keep as is, with minor polish only

Why not redraw:
- the figure already answers its question clearly
- there is no compositional confusion
- the main weaknesses are small and local, not structural

What to improve:

1. Soften the excerpt box
- It is slightly too block-like.
- The excerpt should feel like a lightly quoted paper fragment, not like a heavy content card.

2. Quiet the connector further
- The `extract graph` label is better than before, but it still sits on the connector rather than being integrated with it.
- Best fix: shrink or remove the label and let the caption carry the operation.

3. Tighten node spacing slightly
- The vertical graph chain still has a bit more air than it needs.
- The graph can be compacted without losing readability.

4. Make the graph panel slightly more dominant
- The right panel is the actual extracted object.
- It should visually outrank the excerpt by a small margin.

Suggested end state:
- excerpt quieter
- graph panel slightly more prominent
- connector less label-heavy

Acceptance standard:
- a reader should understand the extraction unit in under three seconds
- no part of the figure should feel decorative

## Figure 3

Current role:
- two paper-local graphs become a shared candidate neighborhood

Current judgment:
- strongest of the three
- good logic
- reasonably good composition
- close to draft-final quality

Recommendation:
- keep as is, with minor polish only

Why not redraw:
- the current Mermaid layout is already doing the essential comparative job
- the three-panel structure is conceptually clean
- this figure benefits from its schematic directness

What to improve:

1. Make the shared graph panel more dominant
- This is the whole point of the figure.
- The right panel should win the visual hierarchy more decisively.
- The left two panels should look like inputs; the right panel should look like the object of interest.

2. Reduce repeated connector labels
- `match concepts` appears twice and is still visually louder than needed.
- Better options:
  - keep only one label
  - or replace both with a simpler visual cue and explain matching in the caption

3. Strengthen edge semantics
- The blue observed edge and dashed rust missing edge are now present, but they should read faster.
- Best fix: slightly stronger stroke contrast and slightly quieter neutral edges.

4. Tighten empty space inside the shared graph panel
- The panel is good, but the right-side object still has a bit more internal air than needed.

Suggested end state:
- left inputs visually quieter
- right panel visually central
- observed versus missing relation more obvious without relying on text

Acceptance standard:
- a reader should immediately grasp that the candidate only exists after cross-paper matching
- the shared graph should be the first thing the eye lands on

## Figure 5

Current role:
- benchmark anchor is narrower than the surfaced question

Current judgment:
- conceptually correct
- compositionally weak
- still the least beautiful figure

Recommendation:
- redraw from scratch

Why redraw:
- the current composition remains unbalanced
- the left support graph is too tall and visually heavy
- the right surfaced-question panel is too generic by comparison
- the connector text still functions like a label sticker
- the benchmark anchor is correct but not elegantly integrated

Why more Mermaid tuning is a bad bet:
- the logic is already settled
- the remaining problem is composition, not syntax
- Mermaid is now close to its ceiling for this figure

Best redesign direction:

### New Figure 5 concept

Use a two-part composition:

1. Left: one compact support graph
- same four nodes
- same observed direct edge
- same dashed benchmark edge
- benchmark edge highlighted with color and one very light label or callout

2. Right: surfaced question
- not a generic box floating separately
- should feel derived from the left object, not just placed beside it

This means the separate mini-panel for the benchmark anchor should be removed.

### Why this is better

- the benchmark anchor already exists inside the support graph
- pulling it into a separate inset duplicates the object
- the figure should show:
  - one graph object
  - one richer reader-facing question
- not:
  - support graph
  - separate benchmark box
  - surfaced question box

### What the new figure should communicate

- the dashed edge is the benchmarkable event
- the reader does not inspect only that edge
- the reader inspects the richer support graph, which is then surfaced as a question

### Concrete redesign spec

- one horizontal support graph on the left
- nodes arranged more compactly than in the current tall panel
- dashed benchmark edge highlighted in rust
- observed direct edge shown in blue
- no separate anchor inset
- no long connector text between panels
- surfaced question box on the right, vertically aligned with the support graph's center

### Label policy

Keep at most:
- `benchmark anchor`
- `surfaced question`

The rest should be conveyed by:
- solid blue versus dashed rust
- graph geometry
- caption text

Acceptance standard:
- the reader should understand the distinction in one glance
- the figure should feel lighter than the current version
- the benchmark edge should read as embedded in the support graph, not detached from it

## Medium recommendation

For the next iteration:

- Figure 2: Mermaid is acceptable
- Figure 3: Mermaid is acceptable
- Figure 5: use Mermaid only as logic scaffolding, then redraw manually in a vector tool or very controlled TikZ/SVG

If the objective is genuine visual beauty rather than merely clear logic, Figure 5 should not stay in raw Mermaid form.

## Practical next step

1. Freeze Figures 2 and 3 except for very small polish.
2. Redesign Figure 5 as:
   - one compact support graph
   - one surfaced-question panel
   - no separate benchmark-anchor inset
3. Only after that, re-evaluate whether Figures 2 and 3 need matching stylistic adjustment.
