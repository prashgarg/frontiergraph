# Hypothesis Generation Strategy: Connecting to Ludwig/Mullainathan

## The opportunity

Ludwig & Mullainathan (2024, QJE) propose a three-step procedure for using ML as a hypothesis generation tool:
1. **Explore**: Train ML on high-dimensional data to discover predictive patterns
2. **Communicate**: Translate those patterns into interpretable hypotheses humans can evaluate
3. **Verify**: Test the hypotheses on held-out data to confirm novelty and generalizability

Our paper currently does step 1 (the reranker discovers which graph features predict link appearance) and step 3 (walk-forward evaluation). But it skips step 2 almost entirely: the reranker produces a ranking, not interpretable hypotheses about *what makes certain research connections more likely to materialize*.

Adding a genuine hypothesis-generation layer would:
- Directly connect to the Ludwig/Mullainathan program (QJE audience)
- Produce novel, testable claims about how economics research evolves
- Move the paper from "screening benchmark" to "screening benchmark + discovery tool"
- Address the referee concern about what the reranker is actually learning

---

## Tool 1: HypotheSAEs (Movva, Peng, Garg, Kleinberg, Pierson 2025)

**What it does:** Takes text + a binary/continuous target → trains sparse autoencoders on text embeddings → identifies interpretable "neurons" that predict the target → uses LLMs to generate natural-language descriptions of what each neuron captures → validates on held-out data.

**How it fits our paper:**

### Application: "What textual features of concept neighborhoods predict whether a missing link later appears?"

**Input:**
- For each candidate pair (u, v) in the feature panel, construct a text description:
  - Concept labels: "public debt → CO2 emissions"
  - Top paper titles mentioning u (last 5 years before cutoff)
  - Top paper titles mentioning v (last 5 years before cutoff)
  - Evidence types present for edges involving u and v
  - Method families used in papers about u and v
- Target: `appears_within_h` (binary)

**What we'd learn:**
- HypotheSAEs would discover interpretable features like:
  - "Pairs where source-concept papers mention 'identification strategy' or 'natural experiment' are more likely to realize"
  - "Pairs involving concepts with recent growth in experimental evidence are predictive"
  - "Pairs where both concepts appear in health economics papers are more likely to close"
- These are *interpretable, testable hypotheses about how the economics literature grows*

**Why it's powerful for the QJE pitch:**
- It directly implements Ludwig/Mullainathan Step 2 on our data
- The hypotheses would be about economics research itself — not just about graph topology
- They would be field-specific and readable by any economist
- They could be verified on held-out time periods (Step 3)

### Practical implementation:

```python
from hypothesaes import HypotheSAEPipeline

# Build text descriptions for each candidate pair
texts = []  # list of strings describing each (u, v) pair
labels = panel_df["appears_within_h"].values

pipeline = HypotheSAEPipeline(
    M=256,  # number of learnable concepts
    K=8,    # active features per example
    selection_method="lasso",
)
pipeline.fit(texts, labels)
hypotheses = pipeline.get_hypotheses(top_k=20)
# Returns: ranked list of natural-language hypotheses with statistical validation
```

**Estimated cost:** ~$1-5 for embeddings + interpretation on our panel (~120K text descriptions).

**What we'd report:**
- Table: "Top 10 text-derived hypotheses about link appearance" with each hypothesis, its predictive strength, and validation on held-out data
- This would be a new subsection: "What does the text tell us about which connections materialize?"

---

## Tool 2: DeepLatent (Gauthier, Widmer, Ash 2025)

**What it does:** Latent variable models (topic models, ideal point models) for multimodal data using variational autoencoders. Can combine text embeddings, bag-of-words, metadata, and structured features.

**How it fits our paper:**

### Application: "What latent research directions are captured by the graph?"

**Input:**
- Document = one concept node
- Text = concatenated titles of papers mentioning that concept
- Metadata = concept degree, evidence types, method families, FWCI
- Target (optional) = does this concept participate in many future realized links?

**What we'd learn:**
- Latent "research direction" topics that cluster concepts by their research neighborhood structure
- Whether certain latent dimensions predict link appearance better than others
- A map of the economics concept space organized by latent research themes rather than by JEL codes or ad-hoc topic clusters

**Why it's useful:**
- It would give us a *different* way to visualize the concept space (replacing or supplementing the t-SNE)
- It could reveal latent dimensions that the current graph features miss
- The ideal-point model variant could position concepts along interpretable axes (e.g., "theoretical vs empirical," "micro vs macro," "established vs frontier")

### Practical implementation:

```python
from deeplatent import DeepLatentModel

model = DeepLatentModel(
    model_type="topic",  # or "ideal_point"
    n_topics=20,
    modalities=["embedding", "metadata"],
)
model.fit(concept_embeddings, concept_metadata)
topics = model.get_topics()  # top words/concepts per topic
positions = model.get_positions()  # latent coordinates per concept
```

**What we'd report:**
- Figure: concepts positioned in latent space, colored by whether they participate in high-realization pairs
- Table: top 5 latent research directions with their characteristic concepts

---

## How the two tools complement each other

| Dimension | HypotheSAEs | DeepLatent |
|-----------|-------------|------------|
| Unit of analysis | Candidate pair (u, v) | Individual concept |
| Target | Binary link appearance | Latent structure |
| Output | Interpretable hypotheses | Latent dimensions/topics |
| Connection to Ludwig/Mullainathan | Direct (Steps 1-2-3) | Indirect (latent structure) |
| QJE relevance | High | Medium |
| Implementation effort | Low (API-based) | Medium (training required) |
| Novel finding potential | High (new hypotheses about economics research) | Medium (new visualization) |

---

## Recommended priority

### Must-do: HypotheSAEs
This is the highest-value addition for the QJE pitch. It:
1. Directly implements Ludwig/Mullainathan Step 2
2. Produces genuinely novel, interpretable claims about economics research
3. Is cheap to run (~$5)
4. Can be validated on held-out data (Step 3)
5. Would be a new subsection or short section in the paper

### Nice-to-have: DeepLatent
This would improve the visualization and concept-space understanding but doesn't connect as directly to hypothesis generation. It's a good appendix addition if time permits.

---

## What the QJE pitch looks like with HypotheSAEs

**Current pitch:** "We build a graph and show it can screen candidate questions better than popularity."

**Enhanced pitch:** "We build a graph, show it can screen candidate questions better than popularity, and then use sparse autoencoders to discover *what textual features of the economics literature predict which research connections will materialize*. The resulting hypotheses are interpretable, testable, and novel — for example, [specific hypothesis about how economics research evolves]. This implements the Ludwig and Mullainathan (2024) three-step procedure on the structure of past research itself."

That second sentence is what turns a screening benchmark into a discovery paper.

---

## Connection to what we already have

The HypotheSAEs analysis would sit naturally after the current Section 5.2 (reranker rescue) and before Section 5.3 (attention frontier). It answers the question: "OK, the reranker predicts link appearance. But *what* is it learning about the economics literature?"

The graph features tell us it's learning topology, recency, evidence composition. HypotheSAEs would tell us what *textual* patterns in the surrounding papers predict link appearance — a complementary dimension that the graph features don't capture.

This also addresses the "LLM-only baseline" concern from the Discussion: if HypotheSAEs discovers that text features alone are highly predictive, that would suggest an LLM-only baseline might work. If graph features dominate even after controlling for text, that further validates the directed extraction.
