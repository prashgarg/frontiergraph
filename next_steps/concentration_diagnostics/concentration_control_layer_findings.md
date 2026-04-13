# Concentration-Control Layer: Findings

## What we tried

We added a **general repeated-theme penalty** to the surfaced shortlist builder.

This was intentionally not domain-specific.
It did **not** penalize environmental topics directly.

Instead, it added a light shortlist penalty when the same:
- source theme
- target theme
- source-target theme pair

had already appeared repeatedly in the selected shortlist.

The purpose was to test whether a mild concentration-control layer could reduce thematic crowding without damaging the quality of the top surfaced questions.

## What changed qualitatively

The top `25` questions do shift somewhat.

Examples of items that moved upward under the theme-control layer:
- `imports -> exports`
- `COVID-19 pandemic -> state of the business cycle`
- `price changes -> stock prices`

So the layer does produce somewhat broader local coverage.

## What did **not** change much

The important result is that the overall thematic mix barely changed.

### Environment/climate share in the cleaned shortlist

Before theme control:
- `h=5`: `50.5%`
- `h=10`: `48.5%`

After theme control:
- `h=5`: `50.5%`
- `h=10`: `48.5%`

So at the stage-share level, the environmental/climate concentration is effectively unchanged.

### Top repeated families also remain very similar

After the layer, the dominant families are still:
- `carbon emissions`
- `green innovation`
- `state of the business cycle`
- `willingness to pay`
- `energy consumption`

That means the layer mostly reshuffles the top of the shortlist rather than changing the shortlist's broader thematic structure.

## Interpretation

This is a useful negative result.

It suggests that the current thematic concentration is **not mainly caused by a weak local diversification policy**.

Instead, the concentration seems to come from deeper forces:
- recent-corpus composition
- rich local graph structure
- reranker amplification
- readable, human-surviving topic families

In other words:

**a light shortlist-level concentration-control rule is not enough to materially rebalance the surfaced frontier.**

## What this means for the project

### 1. The environmental tilt is structurally real in the current pipeline
The layer was general and defensible.
If it had materially reduced concentration, we could have said the shortlist itself was the main issue.

But it did not.

So the environmental tilt looks more structural than cosmetic.

### 2. A concentration-control layer may still be useful for presentation
Even though it does not change the big shares much, it can still:
- prevent a few theme families from occupying the very top ranks too repetitively
- make a review shortlist a bit more varied

So this is still a possible **presentation layer**, but not a real solution to the broader concentration pattern.

### 3. Bigger changes would need to happen earlier in the stack
If we eventually want materially less concentration, the likely levers are:
- ontology redesign
- reranker feature choices
- objective design
- stronger family/theme caps in the surfaced layer

The first two are scientifically more interesting than the last one.

## Recommendation

Do **not** treat the current theme-control layer as a major methodological fix.

Best use:
- keep it as an optional surfaced-shortlist variant for internal review

Do **not** rely on it to solve thematic concentration.

The main learning is the opposite:

**the concentration pattern survives a reasonable general diversification layer, so it reflects something more structural in the graph, corpus, and reranker.**
