# Closest Comparables, Positioning, and Borrowable Ideas

## Purpose

This note maps the papers closest to ours, where we add value, where they add value, what we could borrow, and what tradeoffs we're making. It is a working strategic document for positioning the manuscript and identifying concrete next analyses.

---

## TIER 1: The three papers a referee will reach for first

### 1A. Gu & Krenn (2025) "Forecasting High-Impact Research Topics via Machine Learning on Evolving Knowledge Graphs"

**Venue:** Machine Learning: Science and Technology, vol. 6
**Also known as:** Impact4Cast
**arXiv:** 2402.08640

#### What they do

Build an evolving concept graph from 2.4M papers across four preprint servers. Nodes are NLP-extracted concepts (RAKE extraction from titles/abstracts). Edges are co-occurrence within a single paper, weighted by aggregated annual citations. They train a feedforward neural network on 141 engineered features to predict which never-before-connected concept pairs will become highly cited research topics.

Temporal split: train on 2016 vintage, predict 2019 links; then evaluate out-of-sample on 2019 vintage predicting 2022 links. AUC > 0.9 on link prediction; AUC > 0.67 on genuine impact prediction (high-citation thresholds).

#### Their 141 features in 4 categories

1. **Node features (20)**: neighbor count at different time points, neighbor count growth, rank-based measures, PageRank centrality over rolling 3-year windows
2. **Node citation features (58)**: yearly and cumulative citation counts, paper-mention frequencies, citation growth rankings
3. **Pair/edge features (21)**: cosine similarity, geometric similarity, Simpson similarity, Jaccard similarity, Sorensen-Dice similarity, preferential attachment, shared neighbor counts -- computed over different yearly snapshots
4. **Pair citation features (42)**: aggregate citation metrics comparing concept pairs, citation ratios, min/max citation values, interaction-based citation patterns

Key finding: Simpson similarity (across yearly windows) and cosine similarity are the strongest individual predictors (AUC 0.868-0.888 alone). All 141 features together reach AUC 0.948.

#### Where they overlap with us

- Evolving concept graph with temporal vintages
- Missing links as candidate future research topics
- Temporal/prospective evaluation (freeze graph, predict forward)
- ML on topological and node-level features
- The fundamental framing: what questions will science ask next?

#### Where we add value beyond them

- **Directed causal edges**: they use undirected co-occurrence; we have directed causal claims with typed edges (method, stability, role, status). This is a richer graph object.
- **Economics-specific**: they cover all sciences; we have domain-specific interpretability and the preferential-attachment framing as an economic null.
- **Preferential attachment as a named benchmark**: they don't compare against PA as a named hypothesis about how science works. They use it as one feature among 141. We make it the main null.
- **Anchor/surfaced-object separation**: they predict links and stop. We separate the benchmarkable event from the readable question a researcher would actually inspect. No one else does this.
- **Two-layer benchmark**: transparent score (inspectable) + learned reranker (strongest). They have only the neural network.
- **Gap vs boundary distinction**: they don't distinguish gap questions (rich local support, missing direct link) from boundary questions (sparse bridges). We do, and it's substantively interpretable.

#### Where they add value beyond us

- **Citation impact as outcome**: they predict not just link appearance but whether the link becomes highly cited (Impact Ratio thresholds from 1 to 200). We use binary appearance plus a value-weighted extension, but not the same granularity.
- **Much larger scale**: 2.4M papers, 368K concepts vs our 242K papers, 6,752 concepts. (Though our concepts are semantically richer.)
- **Neural network model**: 6-layer feedforward NN with 600 neurons per hidden layer. Our reranker is logistic regression with 34 features. Their model is more flexible.
- **141 engineered features**: their feature set is much larger. Many of their features (Simpson similarity, cosine similarity across time windows) are informative and we don't currently use them.
- **No baseline gap**: they don't compare against PA or other named baselines (a weakness of theirs, actually).

#### What we could borrow from Impact4Cast

**Concrete analysis 1: Co-occurrence baseline within our data**

We could construct a co-occurrence version of our graph (ignore direction, just check if two concepts appear in the same paper) and run the same benchmark we already run for directed causal links. This would directly test: does the directed claim structure buy us anything over co-occurrence?

If co-occurrence performs similarly to our directed graph on the same benchmark, that weakens the case for the richer extraction. If co-occurrence performs worse -- especially at shorter horizons or in design-based slices -- that's strong evidence that the directed claim graph adds value.

This is a clean ablation we could do with existing data. The co-occurrence graph already exists implicitly in our data (the undirected contextual subgraph is close to this).

**Concrete analysis 2: Simpson/Jaccard similarity features**

Their strongest single features are neighborhood similarity measures (Simpson similarity between the neighbor sets of two concepts). We could compute these for our graph and add them to the reranker feature set, or test them as standalone baselines. If Simpson similarity on our directed graph is a strong predictor, it would confirm the Krenn finding and strengthen the case that topological features carry real signal.

**Concrete analysis 3: Link-vs-impact prediction**

We could split our evaluation into: (a) does the link appear at all? (our current benchmark) and (b) conditional on appearing, does it appear in a high-FWCI paper? This is the analog of their Impact Ratio thresholds. We already have FWCI data in the composition features. The analysis would ask whether our reranker predicts not just appearance but importance.

**Concrete analysis 4: Single-feature ablation**

They train 141 separate single-feature models and rank by AUC. We could do the same with our 34 features. This would produce a clean feature-importance ranking and answer directly: which graph features drive screening value in economics?

#### What we should acknowledge about them

They established the "evolving knowledge graph + link prediction + temporal holdout" methodology in a recent, well-cited paper. We should cite them as a methodological reference and note that our contribution is to bring this approach to a directed claim graph in economics with the preferential-attachment comparison and the anchor/object separation.

---

### 1B. Sourati, Evans et al. (2023) "Accelerating Science with Human-Aware AI"

**Venue:** Nature Human Behaviour, 7, 1682-1696

#### What they do

Build a heterogeneous hypergraph with three node types: properties (scientific targets), materials (candidate substances), and authors. Hyperedges are papers. They simulate random walks on this hypergraph, with a parameter alpha controlling how much the walk traverses through author nodes vs content nodes. Train skip-gram embeddings (DeepWalk-style) on the walk sequences. Predict future material-property discoveries via cosine similarity in the embedding space.

Key innovation: "human-aware" predictions (high alpha = walks follow author networks) dramatically outperform "content-only" predictions (alpha = 0), especially when relevant literature is sparse. They also define "alien" hypotheses: scientifically plausible connections that no current expert is positioned to discover.

Tested in materials science, drug repurposing, and COVID therapeutics. Up to 400% precision improvement from human-awareness.

#### Where they overlap with us

- Knowledge graph + link prediction + temporal evaluation
- Freeze-graph-then-predict methodology
- The fundamental question: what will science discover next?

#### Where we add value beyond them

- **Directed causal claim graph**: they use co-occurrence in a materials-property bipartite graph. We have directed claims with typed edges, methods, stability.
- **Economics domain**: they work in biomedicine/materials science. We bring the approach to economics where cumulative advantage has a specific economic interpretation.
- **Preferential attachment as named null**: they compare content-only vs human-aware. We compare structure vs popularity, which is a different and economically meaningful question.
- **Anchor/surfaced-object separation**: they predict links; we separate what's benchmarkable from what's readable.
- **Transparent retrieval layer**: they have only the embedding model. We maintain a separate inspectable score.
- **Multi-horizon rolling evaluation**: they predict forward by year. We evaluate across 3, 5, 10, 15-year horizons with rolling cutoffs, which is more thorough for the economics setting.

#### Where they add value beyond us

- **Author/expertise modeling**: their alpha parameter incorporates who is positioned to make discoveries. We don't model researcher expertise at all. This is their biggest advantage.
- **"Alien" hypothesis generation**: they can identify scientifically plausible connections that no current expert is positioned to find. We don't have this dimension.
- **Sparse-vs-dense analysis**: they show human-aware models help most in sparse literature regimes. We have gap-vs-boundary but haven't tested whether our model's advantage varies by literature density.
- **Discoverer prediction**: they predict WHO will make discoveries. We don't.
- **Top venue (Nature Human Behaviour)**: published in a very high-impact generalist venue.

#### What we could borrow from Sourati & Evans

**Concrete analysis 1: Sparse-vs-dense regime comparison**

Their core finding is that structure helps most in sparse regimes. We could test the analog: does our graph score's advantage over preferential attachment vary by the density of the local neighborhood? Specifically: for missing links where the two endpoints have thin local support (few mediators, low co-occurrence), does the graph score add more screening value than for links in dense neighborhoods?

This maps to our gap-vs-boundary distinction but makes it quantitative and directly comparable to their finding. We could split our benchmark by local support density and report the graph-score-minus-PA delta in each bin.

**Concrete analysis 2: Content-only vs structure comparison**

They compare content-only embeddings vs structure-aware embeddings. We could do the analogous comparison: how does a text-similarity baseline (e.g., embedding similarity between concept labels) compare to our graph-structural features? We already have lexical_similarity as a baseline. But we could also compute embedding similarity between concept label embeddings and test it as a standalone baseline, then ask whether the graph-structural features add value beyond text similarity.

**Concrete analysis 3: The "alien" hypothesis framing**

Their alien hypotheses are predictions that are scientifically plausible but that no current expert is positioned to make. In our setting, this could be operationalized as: missing links where our graph score is high but co-occurrence/degree measures are low (i.e., the endpoints are not popular but the graph structure points toward a connection). These are the boundary questions in our framing. We could explicitly identify these and report whether they are more or less likely to be realized at longer horizons, which would test whether our graph surface genuinely novel connections or just predict the obvious.

**Concrete analysis 4: Where the graph helps more, revisited**

They show human-awareness helps most in sparse literature. Our heterogeneity atlas already shows where structure helps more (adjacent journals, design-based slices). We could sharpen this by testing whether the pattern is driven by local sparsity: are adjacent-journal, design-based results the places where the literature is thinnest and therefore where structural features carry the most signal?

#### What we should acknowledge about them

The human-awareness insight is genuinely novel and important. We should cite them as showing that incorporating researcher positioning improves scientific prediction, and note that our paper focuses on a complementary dimension: the content structure of claims rather than the social structure of researchers. The two dimensions are not substitutes -- a future extension could combine both.

---

### 1C. Tong, Mao et al. (2024) "Automating Psychological Hypothesis Generation with AI: When Large Language Models Meet Causal Graph"

**Venue:** Humanities and Social Sciences Communications (Nature)

#### What they do

Extract causal relations from 43,312 psychology papers using GPT-4. Build a directed causal knowledge graph. Apply link prediction (TransE, TransR, DistMult) to generate 130 hypotheses about "well-being." Compare KG-generated hypotheses with doctoral scholars' ideas and LLM-only hypotheses. Find that the KG+LLM approach matches expert novelty.

#### Where they overlap with us

- Directed causal claim graph from social science papers via LLM extraction
- Link prediction as hypothesis generation
- Social science domain (psychology, close to economics)

#### Where we add value beyond them

- **Much larger scale**: 242K papers vs 43K. 6,752 concepts vs their smaller graph.
- **Walk-forward temporal evaluation**: they don't do prospective benchmarking. They generate hypotheses and evaluate them by expert judgment, not by whether the link later appeared. Our evaluation is prospective and reproducible.
- **Preferential attachment comparison**: they compare against TransE/TransR/DistMult and LLM-only baselines. They don't test whether popularity alone predicts future work.
- **Anchor/surfaced-object separation**: they treat the predicted link as the output. We separate the benchmark target from the readable question.
- **Richer edge typing**: our extraction schema is more detailed (method, stability, role, status, sign, significance, tentativeness).
- **Transparent + learned two-layer design**: they use only KG embedding models.

#### Where they add value beyond us

- **Human evaluation of outputs**: they got doctoral scholars to rate the generated hypotheses for novelty, feasibility, and interestingness. We have the materials ready but haven't collected ratings. This is our single biggest gap relative to them.
- **LLM-generated natural language hypotheses**: they use GPT-4 to generate readable hypothesis text from the KG. Our surfaced object rendering is rule-based (path/mechanism questions from graph structure), not LLM-generated.
- **Comparison with LLM-only hypotheses**: they test whether the KG adds value over LLM prompting alone. We don't test an LLM-only baseline.

#### What we should acknowledge about them

They are the closest social-science comparison. We should cite them and note: we go beyond them in scale, prospective evaluation, and the PA comparison, but they go beyond us in human validation. The prepared blinded pack is our planned response to that gap.

---

## TIER 2: Methodological ancestors and important context

### Krenn & Zeilinger (2020) "Predicting Research Trends with Semantic and Neural Networks" -- PNAS

Established the concept-graph + link-prediction + temporal-holdout methodology. 750K quantum physics papers, 6,500 concept nodes, 5-year prediction horizon. This is the paper that proved the approach works. We should cite as a methodological ancestor and note we bring it to a directed claim graph in economics.

### Rzhetsky, Foster, Foster & Evans (2015) "Choosing Experiments to Accelerate Collective Discovery" -- PNAS

The theoretical justification for the whole exercise. Shows scientists are 6x more likely to pursue conservative strategies, and that more exploration would accelerate collective discovery. Our paper is an empirical implementation of the kind of screening tool their simulations suggest would help.

### Foster, Ziegelmeier et al. (2025) "Opening Knowledge Gaps Drives Scientific Progress" -- arXiv

Uses persistent homology (topology) on the Microsoft Academic Graph. Finds that gap-opening papers are more cited and more disruptive. This is independent topological evidence for our gap/boundary distinction: structural gaps in the knowledge graph drive progress, not just novel combinations.

### Borrego et al. (2025) "ResearchLink" -- Knowledge-Based Systems

Formalizes hypothesis generation as link prediction on a knowledge graph with path-based features. Closest to our path-support scoring. Key difference: static expert-label evaluation, not prospective.

---

## The Ludwig-Mullainathan connection

### Ludwig & Mullainathan (2024) "Machine Learning as a Tool for Hypothesis Generation" -- QJE

This is the philosophical anchor for why our approach is legitimate in economics.

**Their core argument:** Hypothesis generation has remained "largely informal" and at a "prescientific" stage. ML can systematize it by exploiting algorithms' capacity to notice patterns people might not. They propose a three-step procedure: (1) train ML on high-dimensional data, (2) use human-algorithm interaction to make patterns interpretable, (3) verify novelty against existing theory and expert knowledge.

**How our paper connects:** Our paper is a specific instance of their general program, applied to the structure of past research rather than to behavioral data. They use ML to find patterns in individual-level data (mugshots, behavioral features) that generate hypotheses about human behavior. We use ML (the learned reranker) to find patterns in the literature graph that generate candidate questions about which connections deserve further study.

**The key difference:** Ludwig-Mullainathan focus on prediction within a fixed dataset to generate behavioral hypotheses. Our paper uses the evolving structure of the literature itself as the object, and the missing-link benchmark provides a prospective test of whether the generated candidates are actually good.

**What to cite:** Ludwig and Mullainathan (2024) should be cited in the Introduction or Related Literature as establishing the intellectual case for ML-assisted hypothesis generation in economics. The connection to our paper is natural: if ML can generate novel hypotheses from behavioral data, it can also generate candidate research questions from the structure of past research.

### Earlier Mullainathan framing

- Mullainathan & Spiess (2017, JEP): the y-hat vs beta-hat distinction. Our benchmark is a y-hat problem (does the link appear?), not a beta-hat problem (what is the causal effect?). That distinction helps position our paper.
- Kleinberg, Ludwig, Mullainathan & Obermeyer (2015, AER P&P): "prediction policy problems." Our screening problem is a prediction policy problem -- the binding constraint is which questions to inspect, and improving that prediction improves research allocation.
- Athey (2018, NBER): ML changes not just methods but the questions economics can ask. Our paper is an example of that.

---

## The honest tradeoff matrix

### What we gain from our choices

| Choice | What it buys us |
|--------|-----------------|
| Directed causal edges | Richer graph object; can separate causal from contextual; enables the gap/boundary distinction |
| Economics-only | Domain-specific interpretability; PA has economic meaning; heterogeneity by method family is substantive |
| PA as named null | Economically meaningful comparison; not just "our model beats TransE" |
| Transparent + reranker layers | Inspectable score for browsing + stronger benchmark for evaluation |
| Anchor/object separation | More honest about what's being evaluated vs what's useful |
| Walk-forward rolling design | Multiple cutoffs, multiple horizons; not one lucky vintage |

### What we pay for those choices

| Choice | What it costs us |
|--------|-----------------|
| Directed causal edges | Harder extraction; smaller concept inventory (6,752 vs 368K); harder to scale |
| Economics-only | No external validity; can't claim the approach works in other fields |
| PA as named null | Simpler baseline family; a referee could ask for more ML baselines |
| Logistic reranker (34 features) | Less flexible than neural networks; may underfit complex interactions |
| No author modeling | Missing the Sourati/Evans insight that researcher positioning matters |
| No human evaluation (yet) | The biggest credibility gap vs Tong et al. and SciMuse |
| No LLM-generated hypotheses | Missing the Tong et al. and SciMuse approach of natural language generation |
| Binary appearance target | Missing the Impact4Cast insight about impact thresholds |

### What we should probably do next (ordered by value)

1. **Collect human ratings** -- this closes the biggest gap vs Tong et al. and SciMuse. Materials are ready.
2. **Co-occurrence ablation** -- test whether directed claims buy anything over undirected co-occurrence. Cheap to do, directly addresses the Impact4Cast comparison.
3. **Single-feature importance ranking** -- 34 separate single-feature models, ranked by precision@100 or recall@100. Directly comparable to Impact4Cast's ablation.
4. **Sparse-vs-dense regime split** -- test whether our model's advantage over PA varies with local neighborhood density. Directly comparable to Sourati & Evans's core finding.
5. **Link-vs-impact split** -- split evaluation into appearance-only vs high-FWCI appearance. Comparable to Impact4Cast's IR thresholds.

---

## Suggested citation additions to the manuscript

### Introduction

- Ludwig & Mullainathan (2024): cite as establishing the case for ML-assisted hypothesis generation in economics. Footnote connecting their program (ML on behavioral data) to ours (ML on literature structure).
- Kleinberg, Ludwig, Mullainathan & Obermeyer (2015): cite in passing as naming the "prediction policy problem" -- our screening problem is an instance.

### Related Literature

- Krenn & Zeilinger (2020): cite in the network-growth / link-prediction paragraph as the methodological ancestor.
- Sourati & Evans (2023): cite in the science-of-science paragraph. Note the human-awareness dimension they add and the directed-claim dimension we add.
- Tong et al. (2024): cite as the closest social-science comparison. Note scale and evaluation differences.
- Foster et al. (2025): cite in connection to the gap/boundary distinction. Independent topological evidence.

### Discussion

- Footnote acknowledging the neural-network tradeoff vs Impact4Cast's 141-feature NN. Frame as a deliberate choice: we keep the benchmark family small and interpretable rather than chasing maximum AUC.
- Footnote acknowledging the missing author-awareness dimension from Sourati & Evans. Frame as a complementary direction rather than a limitation.
