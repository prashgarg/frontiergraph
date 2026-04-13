# Why Environmental Nodes Dominate

## Short answer

Environmental and climate-adjacent concepts dominate the current surfaced shortlist for **several different reasons at once**.

It is **not** just an ontology artifact.
It is also **not** just a corpus-composition fact.

The stage-by-stage decomposition suggests:

1. environmental/climate topics are genuinely more common in the recent corpus than in the full corpus
2. the current retrieval and reranker already amplify them
3. the biggest additional amplification happens in the **surfaced cleanup layer**, because environmental/climate families are unusually readable and substantive after methods, metadata, opaque codes, and broad container labels are filtered away

So the current dominance is a **compound effect**, not a single bug.

## What we measured

We compared theme and family shares across:
- the full corpus
- the recent corpus (`2016+`)
- the current transparent top 100
- the current reranked top 100
- the current surfaced top 100
- the current cleaned shortlist top 100

Relevant files:
- `next_steps/concentration_diagnostics/theme_shares.csv`
- `next_steps/concentration_diagnostics/tracked_family_stage_shares.csv`
- `next_steps/concentration_diagnostics/shortlist_family_metrics.csv`

## Main decomposition

### Environment/climate share by stage

- full corpus: `3.1%`
- recent corpus (`2016+`): `5.7%`
- transparent top 100: `8.0%`
- reranked top 100: `17.0%` to `17.5%`
- surfaced top 100: `58.0%` to `61.0%`
- cleaned shortlist top 100: `48.5%` to `50.5%`

This is the clearest result in the whole diagnostic.

The interpretation is:

### 1. There is a real recent-corpus shift
Environment/climate share rises from:
- `3.1%` in the full corpus
to
- `5.7%` in the recent corpus

So part of the story is simply that these topics are more important in recent social-science publishing than in the full 50-year window.

### 2. The graph-based ranking amplifies that shift
The transparent current top 100 already raises environment/climate share to `8.0%`.
The reranker roughly doubles that again to `17%+`.

So the graph and reranker are not neutral with respect to those topics.

### 3. The biggest amplifier is the surfaced-shortlist layer
The jump from reranked top 100 to surfaced top 100 is much larger than the jump from corpus to reranker.

That means the final shortlist is not dominated by environment/climate only because the reranker likes those topics.

It is also dominated by them because, once we remove:
- method artifacts
- metadata nodes
- opaque code labels
- a few generic container endpoints

environment/climate candidates remain especially:
- readable
- policy-salient
- conceptually concrete
- path-rich

The semantic-dedup shortlist reduces this concentration somewhat:
- from `58-61%`
to
- `48.5-50.5%`

but does not remove it.

So the concentration survives even after a deliberate cleanup pass.

## Which environmental families are carrying the weight

The main overweight environmental/climate-adjacent families in the cleaned shortlist are:

- `carbon emissions`
- `green innovation`
- `environmental pollution`
- `environmental quality`
- `energy consumption`
- `renewable energy consumption`

These are all tiny in corpus-share terms, but much larger in shortlist-share terms.

Examples:

- `carbon emissions`
  - recent corpus share: `0.84%`
  - cleaned shortlist share: `14.5%`

- `green innovation`
  - recent corpus share: `0.10%`
  - cleaned shortlist share: `7.0%` to `8.0%`

- `environmental pollution`
  - recent corpus share: `0.06%`
  - cleaned shortlist share: `3.5%`

So these families are not just common. They are **heavily amplified**.

## Why these families are amplified

The evidence points to four reasons.

### 1. Recent growth
Several of these families are more common in the recent corpus than in the full corpus:
- `green innovation`
- `renewable energy consumption`
- `environmental quality`
- `financial development` in green-adjacent settings

So part of the shortlist is tracking a real recent shift in topic mix.

### 2. High local combinatorial richness
The family metrics show that several of these families sit in very path-rich local neighborhoods.

Examples:
- `carbon emissions` source-family mean supporting-path count: about `1935`
- `energy consumption` source-family mean supporting-path count: about `5577`
- `financial development` source-family mean supporting-path count: about `3174`

That matters because the current retrieval and reranker reward nearby structure.

So these families are naturally favored by a method that looks for:
- many plausible mediators
- many nearby paths
- rich local support

### 3. Strong recency and citation-weighted profiles
Some of these families also have strong recency and FWCI-like profiles in the current frontier metrics.

Examples:
- `green innovation`
  - mean recent share about `0.83`
  - mean FWCI about `12.3`
- `financial development`
  - mean recent share about `0.52`
  - mean FWCI about `15.0`
- `renewable energy consumption`
  - target-family mean recent share about `0.63`
  - mean FWCI about `18.1`

So the reranker is not just picking these because they are numerous. It is also seeing them in active, high-visibility local subgraphs.

### 4. They survive human-facing cleanup unusually well
This is the part that matters most for interpretation.

Environmental/climate families often have labels that are:
- specific
- readable
- substantive
- easy to translate into a path or mechanism question

That makes them survive cleanup better than many other families.

So even if the reranker also likes other families, the final surfaced shortlist will still tilt further toward environment/climate if those other families are:
- more generic
- more awkwardly labeled
- less interpretable to a human reviewer

## It is not only environmental topics

Other families are also heavily amplified.

### State of the business cycle
- recent corpus share: `0.03%`
- cleaned shortlist share: `6.5%` to `8.5%`
- amplification vs recent corpus: roughly `255x` to `333x`

This is not an environmental story.
It suggests that some generic macro bridge concepts also get strongly amplified.

### Willingness to pay
- recent corpus share: `0.09%`
- cleaned shortlist share: `5.5%`
- amplification vs recent corpus: about `58x`

Again, not environmental.
This looks more like a bridge-variable / readable-endpoint effect.

### Income tax rate
- recent corpus share: `0.02%`
- cleaned shortlist share: `2.5%` to `3.5%`

### Price changes
- recent corpus share: `0.02%`
- cleaned shortlist share: `2.0%` to `3.0%`

These are strong reminders that the general phenomenon is:
- not just climate dominance
- but broader **amplification of concept families that are locally bridge-rich and human-readable**

## What this means conceptually

This is useful beyond ontology design.

It suggests a more general metascience point:

### Graph-based frontier tools do not only surface "important" topics
They also systematically reward topics that combine:
- recent growth
- dense local pathways
- multiple plausible mediators
- readable, specific endpoint labels

That means the surfaced frontier can overrepresent literatures that are:
- conceptually modular
- policy-salient
- combinatorially rich

even if those literatures are not uniquely important in a broader normative sense.

So the current shortlist should be interpreted as:
- a map of **tractable, richly connected frontier opportunities**

not:
- a neutral welfare ranking of what social science should study

That is a real insight for the paper.

## What this implies for the method

### 1. Ontology still matters
There are still genuine ontology issues, especially in the emissions/environmental-quality family.

Those should be patched.

But ontology alone will not eliminate the environmental tilt.

### 2. The surfaced-shortlist layer matters a lot
Because the biggest jump happens between reranked candidates and surfaced shortlisted questions, the presentation/cleanup layer is not just cosmetic.

It is a major driver of what humans actually see.

### 3. We may eventually want a concentration-control layer
Not in the historical benchmark.
But possibly in the surfaced current shortlist.

Candidate ideas:
- repeated-family penalties
- semantic deduplication
- light theme/family caps

That would not be because environment/climate is "wrong."
It would be because any readable, mediator-rich family can otherwise crowd the surfaced frontier.

## Bottom line

Why are there so many environmental/climate nodes?

Because those families:
- are genuinely more common in the recent corpus
- have unusually rich local graph structure
- score well under the current reranker
- and survive human-facing cleanup unusually well

And the general lesson is broader:

the pipeline tends to amplify **recent, richly connected, human-readable research families**, not just environmental ones.

That is a useful methodological and metascience fact, not just an ontology bug.
