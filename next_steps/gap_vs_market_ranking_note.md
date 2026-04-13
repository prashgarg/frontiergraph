# Gap Vs Market Ranking Note

Date: 2026-04-09

## Purpose

This note records a ranking direction that is important but should remain an
extension to the current method build rather than silently redefining it.

The short version is:

- a literature gap is not enough
- we also care about the size and value of the opportunity inside that gap

Put differently:

- `gap in the market` asks whether a relation or mechanism is missing
- `market in the gap` asks whether enough researchers, subfields, or downstream
  agendas would care if that gap were filled

The current method-v2 build is still mainly about the first object. This note
sketches how to extend it toward the second.

## Why This Matters

Two candidate gaps can be equally plausible in graph terms and still be very
different as research opportunities.

One gap may be:

- technically real
- historically plausible
- but narrow, low-reuse, and of interest to only a tiny neighborhood

Another may be:

- equally plausible
- but relevant to many neighboring literatures
- useful for clarifying many downstream claims
- likely to matter to more researchers, funders, or policy readers

If the ranker only learns “is this gap plausible?”, it will miss that difference.

## A Useful Decomposition

The cleanest way to think about the ranking objective is:

`opportunity value = plausibility + importance + tractability - congestion`

Not necessarily literally as that algebra in code, but conceptually.

### 1. Plausibility

Is this a real, nearby, graph-supported next-step object?

This is the main thing the current retrieval and historical benchmark already try
to capture.

### 2. Importance

If the question were answered, how much conceptual work would it do?

This is the part the graph may already help with, even before we move into more
explicit demand-side ranking.

### 3. Tractability or Ripeness

Is this a reasonable next project rather than a vague long-run aspiration?

This is already close to some of the current graph logic and could remain in the
core method.

### 4. Congestion or Saturation

Is the candidate overly generic, overly crowded, or dominated by flexible
high-support endpoints?

This is where our concentration-control work fits.

## Current Build: What It Is And Is Not

The current method-v2 stack is mostly a supply-side screen.

It asks:

- is the candidate supported by the observed literature graph?
- is it still open at the cutoff?
- does it look like a plausible next-step research object?

That is a good first benchmark. It is historically testable and academically
defensible.

But it is not yet a full “market in the gap” ranker.

## Important Distinction: Pure Supply Side Vs Richer Supply Side

There are really two versions of “supply side”.

### A. Narrow supply side

This is the current minimum object:

- missingness
- local support
- historical realization

### B. Richer supply side

This still stays inside the graph, but asks a stronger question:

- among plausible gaps, which ones appear more conceptually important?

This second object is probably relevant right now.

It does not require us to jump to demand-side modeling yet. It only requires us
to stop treating all plausible gaps as equally valuable.

## How The Graph Might Already Predict Conceptual Importance

Even before adding external demand signals, the graph may already tell us that
some candidates are more important than others.

Promising graph-based importance signals include:

### 1. Multi-neighborhood convergence

The same missing question is implied by many different local neighborhoods, not
just one path.

Why it matters:

- this suggests the candidate is not a local accident
- it may be a bottleneck or common unresolved bridge

### 2. Bridge breadth

The candidate connects distinct but substantively active parts of the graph.

Why it matters:

- a bridge that matters to several neighborhoods may have broader conceptual
  payoff than one that only tidies up one tiny corner

### 3. Downstream unlock potential

Resolving the candidate would likely clarify many adjacent claims, mediator
questions, or unresolved paths.

Why it matters:

- some questions are “leaf gaps”
- others are “unlocking gaps”

### 4. Endpoint reuse after genericity correction

An endpoint appearing in many serious, heterogeneous, well-supported contexts is
different from an endpoint appearing often only because it is vague or flexible.

Why it matters:

- raw popularity is not enough
- corrected reuse may still be a useful signal of conceptual importance

### 5. Evidence diversity

Support coming from several fields, methods, venues, or evidence types may mark
the candidate as more broadly consequential.

### 6. Centrality with anti-hub correction

Network centrality can matter, but only if corrected for generic hub behavior.

This is exactly why WTP-type pathologies showed up earlier:

- raw support can over-reward flexible sink endpoints
- conceptual importance is not the same thing as being an easy attachment point

## Recommendation-System Analogy

The analogy to recommender systems is helpful, but only up to a point.

### What Seems Portable

#### 1. Two-stage architecture

Modern recommendation systems often separate:

- candidate generation
- ranking

That maps well here.

Relevant examples:

- Covington, Adams, and Sargin (2016), *Deep Neural Networks for YouTube Recommendations*
- Liu (2009), *Learning to Rank for Information Retrieval*

Our analogue is:

- graph retrieval generates plausible research candidates
- ranking decides which of those are worth limited attention

#### 2. Link-likelihood style retrieval

Classic link prediction provides the right retrieval intuition:

- identify plausible missing links from graph structure

Relevant examples:

- Liben-Nowell and Kleinberg (2007), *The Link-Prediction Problem for Social Networks*
- Backstrom and Leskovec (2011), *Supervised Random Walks: Predicting and Recommending Links in Social Networks*

This is close to what our supply-side stage already does.

#### 3. Beyond-accuracy ranking

Recommender-system work has long emphasized that pure prediction accuracy is not
the whole objective.

Relevant example:

- McNee, Riedl, and Konstan (2006), *Being Accurate Is Not Enough: How Accuracy Metrics Have Hurt Recommender Systems*

That maps well onto our concern that:

- a plausible graph gap is not automatically a good research recommendation

#### 4. Diversification and de-crowding

Recommendation and information-retrieval systems often use post-ranking
diversification to avoid repetitive slates.

Relevant example:

- Carbonell and Goldstein (1998), *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*

That maps directly onto our concentration-control layer.

### What Does Not Port Cleanly

#### 1. We do not have clicks or engagement labels

A recommender system often has immediate user feedback.

We do not.

Our outcomes are slower, noisier, and endogenous to the evolution of science.

#### 2. Popularity can be a bad objective in science

A movie recommender can often accept popularity as part of the objective.
Scientific ranking cannot do that naively.

Why:

- crowded, fashionable, or generic topics may be over-rewarded
- the project’s goal is not just attention capture

#### 3. Scientific opportunity is not consumer preference

The question is not only:

- “what will many people choose?”

It is also:

- “what is worth scarce research attention?”

That is a harder and more normative object.

## A Clean Staged Extension Path

I would not jump straight from the current build to a full demand-side system.

A cleaner path is:

### Stage 1. Finish the current build

Keep the current paper’s core ranking objective close to:

- plausibility
- tractability
- anti-congestion

This is where we are now.

### Stage 2. Add richer supply-side importance

This is the most relevant next extension for the current codebase.

Candidate additions:

- neighborhood convergence count
- downstream unlock count
- bridge breadth
- corrected endpoint reuse
- support diversity
- genericity-adjusted centrality

This would still be historically disciplined and graph-native.

### Stage 3. Add explicit demand-side signals

Later, we can ask:

- how many active literatures are growing toward this object?
- how many downstream agendas would use the answer?
- is the candidate salient to policy, funding, or public-interest audiences?

Possible future inputs:

- neighborhood growth rates
- field activity trends
- citation or uptake patterns around related questions
- funding or grant metadata
- LLM or human usefulness judgments on shortlists

### Stage 4. Forward-looking ranking beyond the historical benchmark

At the end-of-sample frontier, where leakage is no longer a concern in the same
way, we can be more ambitious:

- use richer LLM critique and interpretation
- combine graph plausibility with usefulness and audience-demand signals
- surface multiple types of opportunities, not just historically benchmarkable
  link events

## Immediate Ideas Unlockable With The Current Setup

Without redesigning the whole system, we can already test some “market in the
gap” ideas as extensions or ablations.

### 1. Add a supply-side importance overlay

Do not change retrieval yet.

Instead, compute a second-stage score from current graph features such as:

- number of independent supporting neighborhoods
- number of distinct mediator families
- field spread of the supporting evidence
- local bridge breadth
- anti-generic corrected endpoint support

### 2. Compare plausibility-only vs plausibility-plus-importance

This would answer:

- does adding graph-based importance improve shortlist usefulness without
  materially breaking historical retrieval quality?

### 3. Evaluate whether concentration control is partly an importance problem

Some concentration issues may reflect:

- too much raw support weight
- too little correction for genericity
- too little reward for multi-neighborhood conceptual breadth

## Potential Applications Later

If this extension works, it opens up several downstream uses.

### For researchers

- better shortlists of paper ideas
- better triage among many plausible open directions

### For funders or program managers

- identifying under-served but broadly consequential research areas
- spotting questions with large downstream reuse value

### For literature mapping

- distinguishing:
  - plausible but niche gaps
  - plausible and broadly important gaps

### For LLM-assisted frontier systems

- giving the model a richer prior than “missing link”
- helping it render not only plausible ideas, but high-value ones

## Recommendation

My recommendation is:

1. keep the current paper’s core method on the present supply-side benchmark
2. add graph-based conceptual-importance signals as the first extension
3. treat full demand-side ranking as a later workstream

That sequencing is the most defensible one.

It keeps the current paper clean while still moving toward the larger goal you
actually care about:

- not only finding gaps
- but finding opportunities that have a real market inside the gap
