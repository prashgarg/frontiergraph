# Paper Underlying Improvement Roadmap

## Purpose

This note records what materially improved in the paper over the last `2-3` days at the **underlying-method** level and what the next serious paper-improvement moves should be.

This is **not** a presentation roadmap.
It is a roadmap for improving the empirical object, the benchmark comparison, the screening interpretation, and the supporting validation.

## What materially improved in the last `2-3` days

### 1. The paper now has a stable empirical hierarchy

The paper is no longer trying to lead with several competing objects at once.

The current hierarchy is:

1. benchmark anchor = later appearance of a missing directed link
2. surfaced object = a path-rich or mechanism-rich research question built around that anchor
3. routed overlays = context-transfer and evidence-type expansion
4. internal support = family-aware comparison and ontology-vNext

That is a real underlying improvement because it changed what the paper is claiming to evaluate.

### 2. The core benchmark comparison is now much cleaner

The main comparison is now intentionally simple:

- graph-based score
- versus preferential-attachment-style benchmark

This is a substantial improvement because the paper now has one interpretable historical comparison instead of several half-competing baselines.

### 3. The ontology-vNext layer became stable internal support rather than a drifting side project

Recent internal work added and then froze:

- reviewed design-family overrides
- reviewed policy semantics and regime guardrails
- reviewed residual relation semantics
- concept-type and context-type overlays
- family-aware comparison as an extension object

This matters because the paper no longer depends on a moving unresolved semantic layer.

### 4. The earlier strong-substantive unresolved queue was resolved rather than promoted

This is one of the most important findings from the recent passes.

The earlier queue looked like possible evidence for a new substantive frontier-object family.
After reviewed edge typing landed, that queue disappeared.

That means the old queue was mostly:

- an internal edge-typing problem

not:

- a missing paper object waiting to be promoted

That is a genuine methodological clarification, not just cleanup.

### 5. The routed overlays now have clearer roles

The project now has stable examples of:

- context-transfer
- evidence-type expansion

These now read as disciplined extensions to the main surfaced object, not as replacement benchmark objects.

### 6. The shortlist is cleaner underneath the paper

Recent work improved:

- family-aware phrasing
- sibling-comparator selection
- context/entity typing
- concept-type tagging
- unresolved-evidence bucketing
- residual regime filtering

This reduces the amount of semantic noise that the paper has to carry.

## What these improvements imply

The paper is no longer bottlenecked by:

- ontology growth
- new family promotion
- more internal semantic categories
- another large paper rewrite

The next gains now have to come from **stronger empirical validation and sharper screening interpretation**.

## Highest-value underlying improvements available now

## 1. Add harder but still transparent benchmark baselines

### Why this matters

Right now the main comparison is clean, but it is still vulnerable to the question:

- is the graph score beating preferential attachment only because preferential attachment is too weak?

The next step is not to add a huge benchmark zoo.
It is to add `2-3` stronger but still transparent baseline families that a skeptical economist can understand.

### Recommended baseline additions

#### A. Degree + recency baseline

Purpose:

- test whether the graph score is just rediscovering endpoint popularity plus recent attention

Concrete construction:

- source out-degree or source prominence
- target in-degree or target prominence
- recent growth in endpoint mentions or endpoint-edge incidence
- simple additive or rank-combined score

Required outputs:

- ranked candidate list
- top-`K` later-link hit rate
- value-weighted comparison if that metric already exists in the paper
- overlap with the graph shortlist

#### B. Directed common-neighbors / triadic-closure baseline

Purpose:

- test whether the graph score is just a directed closure heuristic

Concrete construction:

- number of intermediate nodes bridging source to target
- weighted version using mediator prominence
- possibly normalized by endpoint degree to avoid raw popularity domination

Required outputs:

- same historical evaluation as the current benchmark
- direct comparison against the current graph score
- where each method wins in top-`K`

#### C. Endpoint lexical similarity baseline

Purpose:

- test whether the system is just surfacing semantically nearby endpoint pairs

Concrete construction options:

- token overlap on canonical labels and aliases
- simple TF-IDF similarity on endpoint labels or supporting local text

Keep this simple.
Do not introduce a heavyweight embedding benchmark unless the transparent lexical version proves obviously too weak.

Required outputs:

- top-`K` later-link hit rate
- shortlist composition
- overlap with graph score shortlist

### Decision rule

After these baselines are run, the key question is:

- does the graph score still beat them in the regions of the shortlist that matter for the paper?

If yes, the core empirical claim becomes substantially stronger.
If no, then the paper needs a more modest claim about what the graph score adds.

## 2. Run object-level ablations on the surfaced question layer

### Why this matters

The paper now says:

- the benchmark anchor is a missing link
- the human-facing object is a path/mechanism question

That distinction is conceptually cleaner now, but it is not yet empirically decomposed.

The next step is to show what is gained by moving from a raw endpoint pair to a richer surfaced question object.

### Recommended ablation ladder

#### A. Endpoint-only object

Form:

- just the source-target pair

Question:

- how far can we get with endpoint quality alone?

#### B. Endpoint + path structure

Form:

- source-target pair plus nearby pathways and mediators

Question:

- does path structure improve the shortlist in a way that is historically validated or visibly more interpretable?

#### C. Endpoint + path structure + routed overlays

Form:

- the current surfaced stack with context-transfer and evidence-type-expansion when supported

Question:

- do overlays add value beyond the path/mechanism object, or do they mainly rephrase existing high-quality rows?

### What to measure

At minimum:

- historical hit rate or later-link validation
- overlap between top-`K` sets
- composition of the shortlisted set
- manual quality judgments on a small sample

Useful manual criteria:

- readability
- specificity
- plausibility
- actionability

### Decision rule

If endpoint + path structure beats endpoint-only clearly, the paper can defend the surfaced object more directly.
If overlays add value only on a small subset, the paper should present them as narrow extensions rather than as general gains.

## 3. Make redundancy a methodological object

### Why this matters

The current main shortlist weakness is not awkward phrasing anymore.
It is semantic crowding and repeated neighborhoods.

That is no longer a paper-presentation issue only.
It is a substantive screening issue.

If a screening tool repeatedly surfaces close variants of the same neighborhood, it may be good at ranking but bad at allocating attention across distinct ideas.

### Concrete next steps

#### A. Quantify redundancy in the current top slice

Build a paper-facing redundancy audit for the top `20`, `50`, and `100` surfaced rows:

- repeated source families
- repeated target families
- repeated theme neighborhoods
- repeated endpoint hubs such as CO2-centered rows
- repeated mediator neighborhoods

#### B. Define simple diversity metrics

Candidate metrics:

- unique source-target family neighborhoods in top `K`
- unique theme-pair coverage
- share of rows coming from the top repeated hub neighborhoods
- entropy-style dispersion measures if easy to interpret

#### C. Test a light diversification rule

Do not redesign ranking from scratch.
Test a simple post-ranking diversification rule such as:

- one row per repeated neighborhood until a quota is filled
- marginal penalty for already-seen family or theme neighborhoods
- max-marginal-relevance style reranking using semantic overlap

### Decision rule

If a light diversification rule preserves historical quality while materially widening coverage, that becomes a real underlying paper improvement.
If it damages historical performance, keep diversification as a curation layer only.

## 4. Validate the routed overlays more explicitly

### Why this matters

The routed overlays are promising, but the paper still mostly argues for them by example.

The next step is to show, with a small structured validation pass, that the overlays actually improve the surfaced question in ways a reader cares about.

### Recommended evaluation design

Take a small balanced set of routed rows:

- `10-15` context-transfer rows
- `10-15` evidence-type-expansion rows
- matched baseline phrasing for each

For each pair, compare:

- baseline surfaced question
- routed overlay question

Judge on:

- specificity
- actionability
- interpretability
- likely usefulness for a researcher deciding what to look at next

### Evaluation modes

Possible modes:

- self-audit with deterministic rubric
- blinded internal review
- lightweight economist judgment if available

### Decision rule

If routed overlays improve specificity and actionability on most rows, they deserve a stronger place in the paper.
If gains are uneven, the paper should explicitly frame them as selective overlays rather than broad improvements.

## 5. Add a small human or expert-judgment validation layer

### Why this matters

The paper is framed as a screening tool under attention constraints.
That framing invites a very natural validation question:

- do humans find the shortlisted questions more useful?

Even a small evaluation would help because it connects the historical benchmark to the practical screening interpretation.

### Recommended minimal design

Sample:

- `20-30` surfaced questions
- mix of graph-selected rows and baseline-selected rows
- include baseline object and overlay examples

Ratings:

- novelty
- plausibility
- usefulness
- readability
- whether the row seems worth a researcher’s attention

Raters:

- even one informed economist reader is useful
- two raters is substantially better

### Decision rule

This does not need to become the core paper result.
It is valuable if it supports the practical interpretation:

- the graph screen does not just predict later links
- it also tends to surface questions a reader considers worth attention

## 6. Expand robustness without reopening scope

### Why this matters

Once the main object and main benchmark are stable, the next risk is fragility.

The paper will be stronger if the main result is shown to hold in a few interpretable slices without opening a huge new analysis tree.

### Recommended robustness slices

- shorter vs longer horizon
- top journals vs adjacent journals
- subfield families
- earlier vs later periods

### Required discipline

These robustness checks should remain subordinate to the core comparison.
They should not become a new paper inside the paper.

### Decision rule

If the result is directionally stable across these slices, the screening story becomes more credible.
If not, then the paper should say more clearly where the approach helps and where it does not.

## 7. Small bookkeeping check: relation-semantics propagation

### Why this matters

A recent summary artifact still reports only `none` for `edge_relation_semantic_type` in the enriched shortlist summary, even though the reviewed residual relation-semantics table exists and is wired into the builder.

This is probably a surface-accounting issue rather than a major methodological gap, because the relevant pair may simply not be in the current enriched shortlist.

### Recommended action

- verify whether the reviewed relation semantics land in the full edge-evidence artifact
- confirm whether the missing summary variety is just because the affected pair is absent from the shortlist
- document the answer once so it does not keep resurfacing as a false alarm

This is housekeeping, not a main paper bottleneck.

## Recommended priority order

If we want the biggest underlying gains, the order should be:

1. stronger transparent baselines
2. object-level ablations
3. redundancy/diversification as a screening improvement
4. routed-overlay validation
5. human/expert judgment layer
6. compact robustness slices

## What not to do now

Do not spend the next pass on:

- new ontology growth
- new family promotion
- ranking redesign from scratch
- another broad extraction or prompt retuning pass
- new surfaced object families without fresh evidence

## Concrete outputs to produce in the next serious method pass

At minimum, the next underlying-method pass should leave behind:

- one benchmark-expansion note
- one object-ablation note
- one redundancy audit note
- one routed-overlay validation note
- one updated checkpoint note saying what actually changed the paper’s empirical claim

If time is limited, prioritize the first two.

## Bottom line

The last `2-3` days solved the paper’s internal object-definition problem.

The next real gains will come from answering:

1. does the graph screen still beat stronger simple baselines?
2. what exactly is gained by surfacing path/mechanism questions rather than endpoint pairs alone?
3. can the screen allocate attention across distinct ideas rather than repeatedly surfacing the same neighborhood?

Those are the next underlying questions that can materially improve the paper.
