---
title: "What Frontier Graph Finds"
description: "A web-first overview of the Frontier Graph paper and public release."
eyebrow: "Web overview"
author: "Prashant Garg"
date: "12 April 2026"
---

# What Frontier Graph Finds

Frontier Graph is a research-allocation project about a simple question: how should economists decide what to work on next?

The paper starts from a large published-journal corpus, extracts paper-local research graphs from titles and abstracts, normalizes repeated concept labels into a shared concept space, and then treats missing links as candidate next papers. The point is not to automate taste or replace reading. It is to make one difficult part of academic work a bit more inspectable: deciding which questions are open enough to matter, grounded enough to investigate, and concrete enough to become a paper.

## The basic object

The working object is a missing relation in a concept graph. If one paper connects public debt to public investment, and another connects public investment to CO2 emissions, then the missing direct relation between public debt and CO2 emissions becomes a candidate question.

![From paper text to candidate questions](/paper-assets/outputs/paper/figures/method_build_step1_candidates.png)

That candidate can look like a **gap** if the local support is already dense, or like a **boundary** if it bridges two regions that still have relatively little direct traffic.

## What the benchmark says

The hardest benchmark in the paper is a very tight shortlist problem: suppose a researcher has time to inspect only 100 candidate questions. At that margin, a simple popularity rule based on preferential attachment remains difficult to beat.

![Strict shortlist benchmark](/paper-assets/outputs/paper/slides_figures/mainline_full_rolling_vs_pref.png)

That is a useful result, not a disappointing one. It says cumulative advantage is a serious force in realized scientific development. Questions that connect already-central concepts are more likely to appear later in the literature, and any structural score has to clear that bar.

## Where the story changes

The pooled top-100 result is too narrow to be the whole story. Once the shortlist broadens, and once the data are split by method, journal tier, and topic region, the graph-based ranking becomes more competitive.

![Broader screening frontier](/paper-assets/outputs/paper/13_heterogeneity_atlas/figures/pooled_frontier_main.png)

The clearest patterns are:

- the graph-based score looks relatively better outside the most central core
- design-based causal slices are more favorable than panel- or time-series-heavy slices
- pooled averages hide meaningful heterogeneity across the literature

## A second result: how research evolves

The paper also asks whether research more often closes a missing direct link, or instead adds mediating structure around an existing direct claim. The second pattern is more common.

![Path evolution comparison](/paper-assets/outputs/paper/13_heterogeneity_atlas/figures/path_evolution_comparison.png)

That matters because it changes how the graph should be interpreted. A missing direct link is not the only interesting research move. Sometimes the literature deepens a mechanism before it closes the missing direct edge that local paths already suggest.

## How to use the public release

The public release has three layers:

1. the main site, which introduces the project and curates questions worth checking
2. the deeper exploration app, which lets you inspect questions, concepts, paths, and nearby evidence
3. the downloadable release files, which range from lightweight CSVs to a richer public graph bundle

If you just want to browse, start with the site. If a question looks promising, move into the deeper app. If you want to take the material away, use the downloads page.

## Read more

- [Open the HTML manuscript](/paper/)
- [Download the working paper PDF](/downloads/frontiergraph-working-paper.pdf)
- [Browse questions](/questions/)
- [Open the literature map](/graph/)
