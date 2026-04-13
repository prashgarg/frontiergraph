# Full Seminar Outline

Working title: `What Should Science Ask Next?`

Audience:
- economics seminar
- mixed social-science methods audience
- patient audience willing to see more design detail

Target length:
- `45–60` minutes
- `20–24` main slides
- `8–12` appendix slides

Design principles:
- same visual language as the short talk
- more time for empirical object definition and interpretation
- still avoid letting the talk become a benchmark horse race
- the seminar should feel like a substantive paper talk with a credible historical design, not a ranking-system demo

## Main arc

### 1. Title
- same as short talk

### 2. Motivation
Purpose:
- frame question choice as a science-wide problem

Content:
- question choice is under-formalized
- knowledge burden is rising
- conservative search dominates
- AI may shift scarcity upstream toward question choice

### 3. Why this matters in economics and science
Purpose:
- bridge broad motivation to this paper’s setting

Content:
- economics as a tractable testbed
- published literature gives dated realized structure
- the object is useful beyond economics

### 4. This paper
Purpose:
- paper in one slide

Sections:
- build
- test
- find
- contribution

### 5. Setting and corpus
Purpose:
- define the literature and the sample before method jargon

Content:
- economics-facing published-journal corpus
- what is in, what is out, and why

Visual:
- small corpus waterfall or compact data summary panel

### 6. Paper-local extraction
Purpose:
- show what gets extracted from one paper

Visual:
- Figure 2

### 7. Cross-paper matching
Purpose:
- show why shared candidate structure is a graph problem rather than only a text problem

Visual:
- Figure 3

### 8. Node normalization
Purpose:
- explain the central technical challenge without drowning in detail

Content:
- why concept identity matters
- conservative matching logic
- what is deterministic versus reviewed / softer

Visual:
- one compact ontology / normalization schematic or a small process panel

### 9. Overall pipeline
Purpose:
- put the pieces together

Visual:
- Figure 1

### 10. Two graph-grounded next-question objects
Purpose:
- define direct-to-path and path-to-direct clearly

Visual:
- dedicated two-object slide

### 11. Benchmark event versus surfaced question
Purpose:
- explain why the benchmark is narrower than the reader-facing object

Visual:
- Figure 5

### 12. Gap versus boundary questions
Purpose:
- explain the type of variation the score is trying to read

Visual:
- Figure 6 style gap/boundary slide

### 13. Historical evaluation design
Purpose:
- explain the walk-forward benchmark cleanly

Content:
- freeze at `t-1`
- rank top `K`
- check what appears in `[t, t+h]`

Visual:
- simple dated evaluation schematic

### 14. Main paired historical result
Purpose:
- first result slide

Visual:
- paired-family main benchmark figure

### 15. Benchmark interpretation
Purpose:
- explain what differs across the two families

Content:
- recall versus later realizations per shortlist
- why the two objects are not mirror images

Visual:
- compact paired table or annotated benchmark figure

### 16. Reading-budget interpretation
Purpose:
- if the paired budget result is ready and clean, this is where it goes

If not ready:
- hold this slide as optional

Key message:
- the graph matters most when reading time is scarce

### 17. Main substantive takeaway
Purpose:
- center the science-of-science interpretation

Visual:
- family transition / path-development result

Key message:
- the literature more often adds mechanisms around existing claims than it later states locally implied direct links

### 18. Where the graph helps
Purpose:
- one interpretable heterogeneity or composition slide

Requirement:
- only include if the result is substantively clean

### 19. Surfaced questions now
Purpose:
- make the current frontier concrete

Visual:
- curated examples by family

### 20. What this says about question choice
Purpose:
- interpretation slide

Talking points:
- question choice can be partially disciplined
- graph structure is useful but not dispositive
- mechanism discovery deserves more emphasis than direct closure alone

### 21. Limits
Purpose:
- serious limits slide

Content:
- published-literature core
- benchmarkable historical object differs from richer research imagination
- normalization and extraction remain imperfect

### 22. What comes next
Purpose:
- make the agenda look like research, not marketing

Possible items:
- path length
- context extension
- workflow layer with LLM screening
- node activation as a separate frontier object

### 23. Conclusion
Purpose:
- close the seminar

Content:
- what we built
- what we learned
- why it matters

## Appendix outline

### A1. Corpus and sample construction
- detailed attrition and journal selection

### A2. Extraction protocol
- schema and prompt logic

### A3. Node normalization
- full algorithm and retention counts

### A4. Extra benchmark detail
- paired table
- additional horizons

### A5. Budget frontier
- only if the paired result is finished

### A6. Usefulness / interpretability screen
- appendix only

### A7. Extensions
- path length
- graph evolution

## Main versus appendix rules

Keep in main:
- empirical object
- dated benchmark logic
- paired historical result
- main substantive takeaway
- surfaced examples

Keep in appendix unless unusually strong:
- reranker engineering
- benchmark grids
- model-family comparisons
- LLM usefulness screening
- broad robustness atlases
- graph-evolution descriptives

## Shared deck conventions

- small text, high information density, but only where needed
- figures first, text second
- no decorative transitions
- no full-sentence paragraphs on slides
- appendix buttons in a fixed top-right or bottom-right location
- `Back to main` button on every appendix slide
