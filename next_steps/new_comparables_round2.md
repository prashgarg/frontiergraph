# New Comparable Papers: Round 2

## Papers we should cite (high priority)

### Already have data objects similar to ours

**Lee et al. (2024) "EconCausal"** — arXiv 2510.07231
- Constructs 10,490 context-annotated causal triplets from 2,595 economics papers
- Tests LLM causal reasoning; finds 88% accuracy but 32.6pp drop under context shifts
- **Relevance:** Most similar data object to ours in economics. They build causal triplets from econ papers; we build a directed claim graph. Key difference: they benchmark LLM reasoning *about* claims; we benchmark whether the graph structure can *screen* for future claims.
- **Cite in:** Related Literature (economics KG) or footnote in extraction section

**Leng, Wang & Yuan (2024)** — SSRN 4948029
- Uses LLMs to generate social science hypotheses, graph-based metrics to evaluate them
- Graph centrality, shortest-path distances used to score novelty, plausibility
- **Relevance:** Closest to our approach of using graph structure to evaluate research questions. They evaluate LLM-generated hypotheses; we evaluate graph-surfaced candidates. Both use graph metrics for scoring.
- **Cite in:** Related Literature or Discussion

**Marwitz et al. (2026) Nature Machine Intelligence**
- Already in our comparables. Concept graph + ML for materials science.

### Broader framing papers

**Dell (2025) "Deep Learning for Economists"** — JEL
- Standard reference for NLP/deep learning in economics
- **Cite in:** Footnote in extraction section — our LLM extraction builds on the methods surveyed here

**Bergeaud, Jaffe & Papanikolaou (2025)** — NBER WP 33821
- NLP methods for measuring innovation from text (patents, papers)
- **Cite in:** Related Literature (economics + NLP) or footnote

**Korinek (2025) "AI Agents for Economic Research"** — NBER WP 34202
- Autonomous AI agents for economics research workflows
- **Cite in:** Discussion closing — our screening tool as a component of future research workflows

### Methodological comparables

**Cohrs et al. (2025) "LLMs for Causal Hypothesis Generation"** — MLST
- LLMs infer causal graphs from text, automate hypothesis generation
- **Cite in:** Related Literature (AI-assisted work) — complements our extraction approach

**Si et al. (2024/2025) ICLR** — Already cited

**Survey (2025) "Hypothesis Generation in the Era of LLMs"** — arXiv 2504.05496
- Comprehensive taxonomy of LLM-driven hypothesis generation methods
- **Cite in:** Footnote — positions our work in the broader taxonomy

## Papers that are interesting but we probably don't need to cite

- Khosrowi (2025) philosophical critique — interesting but tangential
- Eren & Perez (2025) workflow survey — too broad
- Besiroglu et al. (2024) AI-augmented R&D — economic growth framing, already covered by Bloom/Jones
- AceMap (Wang et al. 2024) — infrastructure platform, not directly comparable
- BAGELS (2025) — limitations extraction, tangential
- GoAI (2025) — graph of AI ideas, domain-specific

## What to add to the manuscript

### Priority additions (3 new citations):

1. **Lee et al. "EconCausal"** — cite alongside Tong et al. as the other economics-specific causal extraction project. One sentence in Related Literature.

2. **Leng, Wang & Yuan** — cite in Discussion as the closest graph-based hypothesis evaluation approach. One footnote.

3. **Dell (2025) or Bergeaud et al. (2025)** — footnote in extraction section grounding our approach in the economics NLP literature.

### The author-awareness finding (convert Discussion acknowledgment to tested result):

Current text says: "the system operates on the content structure of the claim graph without modeling which researchers are positioned to produce which results"

Replace with: "I tested whether incorporating researcher positioning improves screening. In economics at this concept granularity (6,752 concepts), author expertise is fully saturated: every candidate pair in the top-10K pool has author overlap (median 69 authors), and author features add no incremental signal after controlling for endpoint degree (partial r = 0.05). The Sourati et al. finding does not replicate here, likely because economics has fewer, broader concepts with more overlap in researcher portfolios than the specific material-property combinations studied in biomedicine."

This is stronger than acknowledging the gap — it says we tested and found a domain-specific explanation for why the gap doesn't matter.
