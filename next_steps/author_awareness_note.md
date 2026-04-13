# Author-Awareness Analysis: Results

## The Sourati & Evans question

Sourati et al. (2023, Nature Human Behaviour) show that incorporating researcher expertise into a knowledge network improves discovery prediction by up to 400% in biomedicine, especially in sparse literatures. We tested whether the same effect holds in economics.

## Data

- 229,023 papers with author data (99.4% of corpus)
- 233,538 unique authors
- 17,475 unique institutions
- Mean 2.5 authors per paper

## Key finding: author expertise is fully saturated in economics

At the concept granularity used in this paper (6,752 concepts), **every candidate pair in the top-10K pool has author overlap** — at least 2 authors (and a median of 69) who have published on both endpoint concepts. There are zero "alien" candidates: no pair where the graph suggests a connection but no researcher is positioned to make it.

| Statistic | Value |
|-----------|-------|
| Pairs with author overlap | 60,000 / 60,000 (100%) |
| Median overlap | 69 authors |
| Min overlap | 2 authors |
| "Alien" candidates (top-500, no author positioned) | 0 |

## Does author awareness add screening value?

| Model | P@100 | vs PA |
|-------|-------|-------|
| Author composite | 0.262 | +0.8% |
| Pref. attachment | 0.260 | — |
| Author overlap (raw) | 0.253 | -2.7% |
| Author Jaccard | 0.092 | -64.6% |

Author overlap performs at parity with preferential attachment. After controlling for endpoint degree (partial correlation), overlap adds only r=0.051 — essentially no incremental signal.

## Why this differs from Sourati & Evans

In biomedicine, Sourati & Evans work with specific material-property combinations where many have zero or very few researchers positioned to discover them. In economics at this concept granularity:

1. **Fewer, broader concepts** — 6,752 concepts vs millions of specific materials
2. **More portfolio overlap** — economists publish across related concepts far more than materials scientists specialize in specific substances
3. **Popularity-concentrated pool** — the top 10K candidates involve well-studied concepts that many researchers work on

The "alien" phenomenon requires sparse researcher positioning. Economics at this granularity doesn't have that sparsity.

## For the paper

This is an interesting negative finding: the Sourati & Evans human-awareness effect doesn't replicate in economics at concept-level granularity, because author expertise is saturated. This sharpens the earlier acknowledgment in the Discussion and explains why the graph-content approach (directed causal features) is the right primary signal in this domain.

## Possible extensions

1. **Finer-grained concepts** — more specific concept nodes would create sparser author positioning
2. **Method-specific expertise** — does the pair have an author with the right identification strategy?
3. **Junior vs senior distinction** — are early-career researchers positioned, not just established ones?
