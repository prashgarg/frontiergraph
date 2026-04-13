# Objective Underlying Paper Pass

## What this note is

This is an internal reviewer-style pass on the paper's underlying logic after the recent benchmark, ontology, shortlist, and manuscript revisions.

It is not a presentation pass.
It is not a friendly project-status memo.
It is a blunt assessment of:

- what is now genuinely stronger
- what is still exposed
- what concrete empirical work would most improve the paper from here

## Short answer

The paper is much better than it was a few days ago because it now has one coherent object hierarchy and it is substantially more honest about what the benchmark does and does not show.

But the core empirical claim is still not fully secure.

The project now looks strongest as a paper about:

- screening candidate economics questions under attention constraints
- using a graph-based candidate universe plus a learned reranker
- surfacing readable path/mechanism questions around that screened set

The project does **not** currently look strongest as a paper claiming that a transparent graph score beats popularity-based alternatives.

That distinction matters. Once the benchmark family was widened, the transparent graph score lost. The paper survived because the learned reranker won. That is a real rescue, but it changes what the paper is.

## What materially improved in the last 2--3 days

### 1. The paper now has a stable empirical hierarchy

The draft now consistently separates:

- benchmark target: later appearance of a missing directed link
- surfaced object: a path-rich or mechanism-rich question built around that anchor
- routed overlays: context transfer and evidence-type expansion
- internal support layers: family-aware comparison and ontology-vNext

This is a real improvement. Earlier versions risked feeling like several different papers stitched together. The current version is much more coherent.

### 2. The ontology work is no longer the main uncertainty

The recent ontology-vNext passes were worth doing because they answered a genuine question:

- was the unresolved substantive tail evidence for a new frontier-object family, or mostly an internal typing problem?

The answer appears to be:

- mostly an internal typing problem

That is useful because it lets the paper stop pretending the ontology layer is the central result. It now behaves like support infrastructure, which is where it belongs.

### 3. The paper is much more honest about the benchmark

The stronger transparent benchmark expansion was important.

It showed that the transparent graph score does **not** beat:

- preferential attachment
- degree plus recency
- directed closure

That could have been a paper-breaking result if the paper had insisted on the transparent score as the flagship screen. Instead, the reranker review showed that the best learned reranker does beat those baselines on the main top-\(K\) metrics. That is a more defensible position.

### 4. The surfaced object story is now better grounded

The object-ablation work clarified something important:

- the main interpretive gain comes from path/mechanism rendering
- routed overlays are useful but selective

That is exactly the kind of evidence the paper needed. It helps justify why the human-facing object is richer than the benchmark anchor without claiming that every extension layer is equally important.

### 5. The redundancy problem is now identified correctly

The shortlist problem is no longer wording.
It is semantic crowding.

That is progress. Wording problems are cosmetic. Redundancy is substantive because the paper is about screening under limited attention. If the shortlist keeps surfacing too many nearby variants of the same idea, that is a real problem for the claimed use case.

## What is now genuinely strong

### A. The benchmark anchor is clean

The missing directed link is a good empirical object because it is:

- dated
- prospectively testable
- interpretable
- stable under historical backtesting

This remains one of the paper's strongest design decisions.

### B. The anchor/object distinction is now credible

The paper no longer confuses:

- what is evaluated historically
- what a human researcher should actually read

That distinction is conceptually important and now mostly well handled.

### C. The paper is more disciplined about extensions

The routed overlays and family-aware comparison now look like extension layers rather than the main benchmark object. That is the right architecture.

### D. The benchmark story is still alive

The paper did not survive the harder baselines because the original graph score was stronger than expected.
It survived because the project was flexible enough to test the stronger benchmark family honestly and then move the comparative claim to the learned reranker.

That is not a weakness in itself.
It is a sign that the project is now being evaluated more seriously.

## Main remaining weaknesses

These are ordered by importance.

### 1. The paper's benchmark win now depends on the learned reranker

This is the main exposed point.

Right now the paper says, in effect:

- the transparent score is the interpretable retrieval layer
- the learned reranker is the strongest graph-based benchmark

That is plausible.
But it creates a new burden of proof.

A skeptical economist or referee can now ask:

- what exactly is the reranker learning?
- how much of the win is real graph structure versus flexible reweighting?
- how insulated is the reranker from overfitting to the historical panel?
- why should I think this is still a graph-screening paper rather than a lightly supervised ranking paper?

The paper does not fully answer those questions yet.

#### Why this matters

If the reranker is the actual winner, then the reader needs a cleaner explanation of:

- feature set
- training design
- vintage split discipline
- model family choice
- why this does not collapse into an opaque benchmark arms race

#### Concrete steps

1. Add one compact benchmark-design table in the appendix with one row each for:
   - preferential attachment
   - degree plus recency
   - directed closure
   - transparent graph score
   - best learned reranker
2. Add one short paragraph in the main text explaining:
   - what the reranker sees
   - what it does not see
   - how historical split discipline is preserved
3. Add one compact ablation or feature-family decomposition if feasible:
   - transparent graph features only
   - graph features plus credibility/support features
   - final chosen reranker
4. Keep the benchmark family small.
   Do not add more models unless they answer a specific critique.

### 2. The paper still lacks direct human-usefulness evidence

This is the second-biggest weakness.

The paper is framed as a screening tool under attention constraints.
That means human usefulness is not decorative evidence.
It is central evidence.

Right now the human-validation pack is ready, but the ratings do not exist yet.

#### Why this matters

Later link appearance is a useful benchmark target, but it is not the same as:

- usefulness to a reader
- plausibility as a paper idea
- attention-worthiness under scarce time

Without human validation, the paper still depends heavily on a proxy target whose connection to research usefulness is plausible but not directly shown.

#### Concrete steps

1. Run the blinded rating exercise with at least 3 raters.
   Better:
   - 5 to 8 economics-trained raters
2. Score at least:
   - novelty
   - plausibility
   - usefulness
   - readability
   - attention-worthiness
3. Pre-commit to the comparison:
   - graph-selected rows versus preferential-attachment-selected rows
4. Report:
   - mean difference by criterion
   - standard errors or simple confidence intervals
   - whether any criterion is clearly driving differences
5. Be honest about who the raters are.
   If they are economics PhD students, say that.

### 3. The paper shows that path/mechanism renderings are better, but not yet that humans prefer them

The internal ablation shows that the path/mechanism layer is the main interpretive gain.
That is useful, but it is still an internal diagnostic rather than external validation.

The missing evidence is:

- do humans actually find the rendered questions more useful than the raw endpoint pair?

#### Why this matters

The paper's main conceptual move is that:

- the benchmark anchor should stay narrow
- the surfaced object should be richer

That claim would become much stronger if supported directly by a small human comparison.

#### Concrete steps

1. Build a tiny within-item comparison pack:
   - raw anchor wording
   - path/mechanism wording
   - routed overlay wording when available
2. Use 12 to 20 items, not the full pack.
3. Ask raters to judge:
   - which version is more understandable
   - which version is more actionable as a research prompt
   - which version they would rather inspect under time pressure
4. Report this as validation of the surfaced object, not as the main benchmark.

### 4. Redundancy is now a real methodological issue

This paper is about screening.
So diversity of surfaced questions is not just a UX consideration.
It affects the economic interpretation of the shortlist.

The diversification backtest is encouraging, especially at \(h=5\), but it has not yet been fully integrated into the argument.

#### Why this matters

If the model's best top-50 set contains many close variants of one theme, then:

- the benchmark may still look good historically
- but the practical screening value is lower than the paper implies

This is especially relevant for economist readers who care about research-allocation breadth rather than only predictive concentration.

#### Concrete steps

1. Decide on one clear role for diversification:
   - either a screening-only extension
   - or not in the main workflow at all
2. If kept, make the claim narrow:
   - diversification improves idea coverage
   - the quality-coverage tradeoff is more favorable at \(h=5\) than at \(h=10\)
3. Add one compact table or paragraph reporting:
   - quality change
   - coverage change
   - concentration change
4. Avoid overselling diversification as part of the core benchmark winner.

### 5. The paper's target proxy is still narrower than its practical claim

This is not fatal, but it should stay visible.

The main benchmark target is later link appearance.
The main practical claim is better screening of candidate questions.

Those are related, but not identical.

The paper now handles this better than before, but the limitation still exists.

#### Why this matters

A skeptical reader can still say:

- maybe the model is finding questions that later appear
- but that does not mean it is finding the most important, interesting, or welfare-relevant questions

#### Concrete steps

1. Keep the practical claim modest everywhere.
2. Lean on:
   - value-weighted results
   - human validation
   - heterogeneity where structure helps more
3. Do not let the paper imply that later link appearance is equivalent to scientific value.

## What I would do next if this were my paper

### Priority 1: Run the human validation

This is the highest-value move now.

If the graph-selected questions score better than preferential-attachment questions on usefulness and attention-worthiness, the paper becomes much more convincing in its own stated terms.

### Priority 2: Tighten the reranker benchmark discipline

The reranker is now doing essential work in the paper.
That means its role must be clearer and more defensible.

The paper does not need a benchmark zoo.
It needs a clean explanation of why the reranker is still part of the same graph-screening exercise.

### Priority 3: Add a small surfaced-object validation

This is the cleanest way to justify the path/mechanism rendering layer.

If the paper can show that humans prefer the richer surfaced question to the raw anchor, that becomes one of the most intuitive results in the whole project.

### Priority 4: Decide the status of diversification

My current view is:

- keep diversification as a light extension
- do not make it part of the core benchmark win
- do mention it because it answers a real screening concern

### Priority 5: Only then revisit paper emphasis

After the above, the manuscript can be revised again with much firmer foundations.
Until then, more prose polishing will help less than direct validation work.

## Bottom line

The paper is now in a much stronger position than it was a few days ago.

That is not because the main benchmark became simpler or prettier.
It is because the project now knows what its strongest and weakest claims actually are.

The strongest current version of the paper is:

- a paper about screening candidate economics questions under attention constraints
- using a graph-defined candidate universe
- evaluated on later link appearance
- with a learned reranker as the strongest graph-based benchmark
- and a richer path/mechanism rendering layer for the human-facing object

The weakest remaining point is not ontology, wording, or extension sprawl.
It is the gap between:

- historical benchmark success
- and direct evidence that the surfaced questions are genuinely better for human research attention

That is why the next best work is validation, not more pipeline expansion.
