# DAGverse and Related Papers: Reading Notes

Date: 2026-03-31

Primary paper:
- Shu Wan, Saketh Vishnubhatla, Iskander Kushbay, Tom Heffernan, Aaron Belikoff, Raha Moraffah, and Huan Liu. 2026. "DAGverse: Building Document-Grounded Semantic DAGs from Scientific Papers." arXiv:2603.25293.
- Abstract page: <https://arxiv.org/abs/2603.25293>
- HTML paper: <https://arxiv.org/html/2603.25293v1>

## What DAGverse is doing

My read is that DAGverse is not mainly a "causal claim extraction from papers" paper. It is a **document-grounded semantic DAG benchmark** paper.

Their central move is:
- use scientific papers that already contain explicit DAG figures
- treat those figures as the target structure
- then ground that structure back to the document text
- produce examples with graph-level, node-level, and edge-level evidence

So the paper is trying to solve a different problem from the one FrontierGraph is solving.

Their core object is:
- given a document, recover the semantic DAG that a domain expert would draw from it

That is closer to:
- graph reconstruction
- benchmark construction
- multimodal grounding

than to:
- large-scale literature mapping
- question generation
- prospective evaluation of missing or path-rich questions

## What they improve over my earlier "Causal Claims in Economics" paper

Relative to *Causal Claims in Economics*, DAGverse improves on a few dimensions.

### 1. They have a much stronger supervised target

This is the biggest difference.

They are not trying to infer a graph only from prose. They exploit papers that already contain DAG figures. That gives them:
- an author-provided graph target
- a more coherent graph object
- a more defensible graph-level benchmark

This is much stronger than pure extraction when the goal is:
- reconstruct the intended DAG
- evaluate graph grounding
- benchmark graph-text reasoning

### 2. They are graph-first, not edge-first

Your earlier paper is much closer to:
- extracting paper-local causal links
- then using those links downstream

DAGverse is much more explicitly about:
- recovering a whole document-level semantic DAG
- with coherent node and edge grounding

That means they care a lot about:
- abstraction level
- graph coherence
- evidence grounding
- reconstruction quality

### 3. They have graph-, node-, and edge-level evidence

That is a useful design choice.

It means the dataset is not just:
- a graph object

but:
- a graph plus evidence spans and contextual grounding

This is attractive for:
- benchmarking
- interpretability
- text-to-graph and graph-to-text tasks

### 4. They are multi-domain

They position DAGverse as broader than economics:
- multiple domains
- real-world scientific papers
- causal DAGs as a case study

That makes the benchmark easier to pitch to the ML / AI community.

### 5. They are benchmark-oriented in a way our current paper is not

Their contribution is very benchmark-shaped:
- high-precision pipeline
- expert-validated examples
- comparison to VLM / LLM baselines
- intended downstream reasoning tasks

That is a major difference in style and audience.

## Where DAGverse still differs from FrontierGraph

This is important, because the overlap is real but the papers are still doing different things.

### 1. FrontierGraph is not only about causal DAG reconstruction

Our current pipeline is broader than the way they summarize *Causal Claims in Economics*.

They write in Related Work that Garg and Fetzer's pipeline "extract[s] causal claims from econometric equations, producing large numbers of pairwise links."

That is too narrow for where the pipeline now stands.

The current FrontierGraph paper and codebase explicitly include:
- paper-level research graphs extracted from titles and abstracts
- directed causal links
- undirected contextual support
- separation of causal presentation from evidence method
- contextual qualifiers outside the node label
- concept normalization across papers
- theoretical or conceptual evidence types in the schema

So the current object is not just:
- econometric-equation retrieval

It is much closer to:
- a reusable paper-level graph extraction layer for literature mapping and question generation

### 2. FrontierGraph is temporal and prospective

This may be the biggest substantive difference in research aim.

DAGverse asks:
- can we recover document-grounded semantic DAGs?

FrontierGraph asks:
- can local literature structure help screen plausible next questions?
- which unresolved questions later realize?
- when do direct links close versus mediator structures deepen?

So FrontierGraph is much more about:
- research allocation
- dynamics
- screening
- path development over time

### 3. FrontierGraph cares about path-rich unresolved questions

DAGverse is about reconstructing a graph that already exists in a document.

FrontierGraph is moving toward a richer object:
- unresolved but increasingly supported research programs
- not just recovering the graph that an author already drew

That is conceptually quite different.

### 4. FrontierGraph is built for literature-scale aggregation

DAGverse has:
- 108 expert-validated semantic DAGs

That is a strong benchmark size.

But FrontierGraph is trying to work at a very different scale:
- roughly 240k economics and adjacent-journal papers
- concept normalization across papers
- aggregated literature map
- candidate-question panel over time

So the papers differ not only by discipline, but by:
- unit of analysis
- scale
- downstream use

### 5. FrontierGraph is not limited to author-provided DAGs

This is both a weakness and a strength.

Weakness:
- we do not get the clean supervision signal that DAGverse gets from explicit DAG figures

Strength:
- we are not limited to the tiny slice of papers that already include DAG diagrams
- we can build a much broader literature object

## Fair reading of their characterization of my earlier work

My charitable interpretation is:
- they are trying to place *Causal Claims in Economics* inside a causal-DAG-dataset literature review
- so they compress it into the aspect most legible to that audience

Still, the summary undersells what the extraction layer can do.

More accurate wording would have been something like:
- economics-focused paper-level causal and relation extraction from titles, abstracts, and equation-centered evidence
- producing large numbers of pairwise links that can support larger graph construction, though not coherent author-provided DAGs

So I do not think the citation is hostile.
I do think it is narrower than the current reality of the pipeline.

## What we can learn from DAGverse

### 1. Strong supervision matters

Their use of explicit DAG figures is smart.

Lesson:
- if FrontierGraph wants a benchmark paper for graph recovery or graph grounding, we should look for places where the literature itself provides stronger supervision
- figures, diagrams, conceptual schematics, path diagrams, mediation diagrams, DAG images

### 2. Graph-level coherence is valuable

One recurring weakness of pairwise extraction is that it can look fragmented.

DAGverse leans hard into:
- coherent graph object
- semantic grounding
- abstraction level

Lesson:
- our paper should be explicit that we are not only collecting pairwise links
- we are building paper-local graph objects and then aggregating them

### 3. Evidence grounding is a real differentiator

Their graph-level, node-level, and edge-level evidence is a strong design choice.

Lesson:
- when we present FrontierGraph, we should foreground paper-level, edge-level, and route-level evidence much more clearly
- this helps with credibility and inspectability

### 4. The benchmark audience likes clear task definitions

DAGverse is very good at saying:
- here is the task
- here is the supervision source
- here is the dataset
- here is the benchmark

Lesson:
- FrontierGraph should be equally crisp about its core task
- especially if we move from "missing edge" to "path-rich question" as the richer object

### 5. Multi-domain generality is attractive, but not necessary for the economics paper

DAGverse gains a lot from being broader than one field.

Lesson:
- for the economics paper, do not chase generality too early
- but note clearly what would and would not transfer outside economics

## Important ways our current paper can still stand apart

The strongest differentiators for FrontierGraph are not:
- "we also have graphs"

They are:

### 1. Prospective validation

We ask whether surfaced objects later realize in the literature.

That is a major difference.

### 2. Research-allocation use case

We are not primarily building a graph benchmark.
We are building a system for:
- screening questions
- identifying path-rich opportunities
- eventually ranking replication priorities and disagreement structures

### 3. Hybrid graph object

We already have:
- directed causal edges
- undirected contextual support
- method metadata
- causal-presentation metadata
- theoretical/conceptual evidence types

That should be emphasized more strongly in the paper.

### 4. Dynamic unresolved-question objects

The next draft can push much harder on:
- unresolved questions becoming more supported over time
- direct closure versus mechanism-deepening
- "ripeness" or "researchability"

That is not what DAGverse is doing.

## Specific papers from their references worth reading next

These look most relevant.

### 1. ReCAST
- R. Saklad, A. Chadha, O. Pavlov, and R. Moraffah. 2025. "Can Large Language Models Infer Causal Relationships from Real-World Text?"
- arXiv:2505.18931

Why it matters:
- real-world text
- economics domain
- causal relation extraction and validation
- probably the closest cited paper to our extraction problem

### 2. CLadder
- Z. Jin et al. 2023. "CLadder: Assessing Causal Reasoning in Language Models."

Why it matters:
- benchmark framing
- causal reasoning task design

### 3. Corr2Cause
- Z. Jin et al. 2023. "Can Large Language Models Infer Causation from Correlation?"

Why it matters:
- causal reasoning benchmark
- useful contrast with document-grounded work

### 4. CLEAR
- S. Chen et al. 2024. "CLEAR: Can Language Models Really Understand Causal Graphs?"

Why it matters:
- graph understanding benchmark
- likely useful for thinking about evaluation design

### 5. Can Large Language Models Build Causal Graphs?
- S. Long, T. Schuster, and A. Piché. 2023.

Why it matters:
- likely close to graph-construction framing

### 6. LAGRANGE / graph-text paired datasets
- A. Mousavi et al. 2024. "Construction of Paired Knowledge Graph-Text Datasets Informed by Cyclic Evaluation."

Why it matters:
- graph-text pairing at scale
- quality problems in automatic graph-text alignment

## Concrete next steps from this reading

1. In the FrontierGraph paper, describe the extraction layer more explicitly as:
   - paper-local graph extraction
   - not just pairwise causal-claim extraction

2. In the paper and website, foreground:
   - edge-level evidence
   - route-level evidence
   - method and credibility metadata

3. Consider a side project or future paper on:
   - stronger supervision from diagrams, path figures, mediation schematics, or DAG-like figures in economics and adjacent fields

4. Read ReCAST carefully next.

5. Revisit the wording around the richer object in the paper:
   - unresolved but increasingly supported question
   - path-rich research program
   - direct closure versus mechanism-deepening

