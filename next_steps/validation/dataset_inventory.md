# External Validation Targets: Inventory

Date: 2026-03-31

This note records what is currently available for download from the most relevant adjacent datasets, how large those assets are, and whether they are useful for FrontierGraph-style validation.

## What we need from an external dataset

The most useful external validation target would provide:
- real paper or document text
- a gold or near-gold graph
- named nodes and directed edges
- enough metadata to let us compare our extraction to the target

The two main bottlenecks on our side are:
- **ontology**
- **validation**

So the most valuable datasets are the ones that help us answer:
- if we run our own prompt on the source text, how different is our graph?
- if nodes are not exactly the same, how do we evaluate broader/narrower or synonymous concepts?

## 1. DAGverse example release

Paper:
- Shu Wan et al. 2026. "DAGverse: Building Document-Grounded Semantic DAGs from Scientific Papers."
- <https://arxiv.org/abs/2603.25293>

Current downloadable dataset I found:
- Hugging Face dataset: `textual-causal-reasoning/dagverse-example`
- README: <https://huggingface.co/datasets/textual-causal-reasoning/dagverse-example/raw/main/README.md>

### What appears to be available
- 108 examples
- one parquet file
- download size: **1,846,997 bytes** (~1.8 MB)
- dataset size: **3,358,786 bytes** (~3.4 MB)

### Fields exposed in the release
- `dag_id`
- `source`
- `abstract` (field exists, though the README schema suggests it may be a flag rather than full text)
- `technical`
- `domain`
- `semantic_dag`
- `dag`
- `paper_id`
- `paper_uri`
- `image_id`
- `image`

### Validation usefulness
This is very promising, but with one caveat.

Strengths:
- graph object is present
- figure/image is present
- source paper URI is present
- examples are backed by papers with explicit DAG figures

Weakness:
- the release does **not obviously include full paper text inline**

Practical implication:
- we can still use it
- but for prompting we may need to fetch the actual paper text ourselves from `paper_uri`

### Why it is useful for us
- strong graph-level supervision
- good for evaluating graph recovery
- useful for checking whether our graph is more fragmented, broader, narrower, or misdirected relative to an author-provided DAG

### First-pass recommendation
Yes, download this.
It is tiny and should be the first thing we test.

## 2. ReCITE

Paper:
- Ryan Saklad et al. 2026. "Can Large Language Models Infer Causal Relationships from Real-World Text?"
- arXiv:2505.18931

Current downloadable dataset:
- Hugging Face dataset: `RyanSaklad/ReCITE`
- README: <https://huggingface.co/datasets/RyanSaklad/ReCITE/raw/main/README.md>
- GitHub: <https://github.com/Ryan-Saklad/ReCITE>

Note:
- the paper was referred to in our earlier discussion as "ReCAST"
- the actual released dataset name appears to be **ReCITE**

### What is available
Three configurations:
- `default` = core benchmark
- `responses` = model outputs
- `evaluations` = evaluation scores

### Sizes
Core benchmark:
- `test.parquet`
- **3,496,972 bytes** (~3.5 MB)

Model responses:
- `responses.parquet`
- **58,946,694 bytes** (~58.9 MB)

Evaluations:
- `evaluations.parquet`
- **144,415,944 bytes** (~144.4 MB)

Total stored size reported by Hugging Face API:
- **254,683,854 bytes** (~255 MB)

### Core benchmark contents
- 292 annotated causal graphs
- real-world scientific text from open-access MDPI and PLOS articles
- fields include:
  - `title`
  - `source`
  - `url`
  - `domains`
  - `num_nodes`
  - `num_edges`
  - `nodes`
  - `edges`
  - `node_explicitness`
  - `input_text`
  - `abstract`
  - `publication_date`

### Validation usefulness
This is probably the **best immediate external validation set** for us.

Reasons:
- real scientific text is included directly
- nodes and edges are already present
- moderate size
- causal graph extraction is exactly the task
- response and evaluation files provide a benchmark context we can compare against

### First-pass recommendation
Definitely download the core benchmark now.
Likely also download the response and evaluation files later, but only after we have our own extraction loop working.

## 3. CLadder

Paper:
- Zhijing Jin et al. 2023. "CLadder: Assessing Causal Reasoning in Language Models."
- <https://arxiv.org/abs/2312.04350>

Download links:
- GitHub README: <https://raw.githubusercontent.com/causalNLP/cladder/main/README.md>
- zip file: <https://raw.githubusercontent.com/causalNLP/cladder/main/data/cladder-v1.zip>
- Hugging Face: `tasksource/cladder`

### Sizes
- zip file size from README: **6.5 MB**
- raw ZIP content-length: **7,168,720 bytes** (~7.2 MB)
- Hugging Face used storage: **53,273,398 bytes** (~53.3 MB)

### What it contains
- 10,112 questions
- natural-language prompts
- answers
- reasoning traces
- metadata including:
  - `graph_id`
  - `model_id`
  - query type
  - rung of the ladder of causation

Important:
- the graph is generally reconstructable from metadata/background
- but this is **not a real paper-text to gold-graph benchmark**

### Validation usefulness
Useful for:
- reasoning evaluation
- checking whether a model can answer causal questions over known structures

Not useful for:
- validating our paper-text graph extraction pipeline
- evaluating ontology decisions on real research papers

### First-pass recommendation
Do not prioritize for extraction validation.
Keep in reserve for later reasoning tests.

## 4. CLEAR

Paper:
- Sirui Chen et al. 2024. "CLEAR: Can Language Models Really Understand Causal Graphs?"
- <https://arxiv.org/abs/2406.16605>

Data/code:
- GitHub README: <https://raw.githubusercontent.com/opencausalab/clear/main/README.md>
- Hugging Face dataset: `OpenCausaLab/CLEAR`

### Sizes
- total questions: **2,808**
- Hugging Face used storage: **26,650,181 bytes** (~26.7 MB)

### What it contains
- 20 causal tasks
- graph images
- JSON and JSON-single files
- human-readable versions
- evaluation tooling

Important:
- this is a **causal-graph understanding benchmark**
- it is not a paper-text paired extraction benchmark

### Validation usefulness
Useful for:
- testing graph understanding and causal reasoning

Not useful for:
- testing whether our prompt recovers a graph from real paper text

### First-pass recommendation
Do not prioritize for current validation.

## 5. LAGRANGE / paired graph-text dataset paper

Paper:
- Ali Mousavi et al. 2024. "Construction of Paired Knowledge Graph-Text Datasets Informed by Cyclic Evaluation."

### What it is useful for
Mostly conceptual.

It matters for FrontierGraph because it is directly about:
- graph-text equivalence
- noise in automatically paired graph-text datasets
- why ontology and semantic alignment matter

### Validation usefulness
Useful as:
- a warning about alignment problems
- an ontology-design reference

Not useful as:
- a direct causal-paper extraction benchmark for us

## Practical ranking for FrontierGraph

### Most useful right now
1. **ReCITE**
2. **DAGverse example**

### Useful later
3. **CLadder**
4. **CLEAR**

### Conceptual / methodology reference
5. **LAGRANGE**

## Recommended immediate download strategy

### Download now
- DAGverse example parquet (~1.8 MB)
- ReCITE `test.parquet` (~3.5 MB)

### Probably download later
- ReCITE `responses.parquet` (~58.9 MB)
- ReCITE `evaluations.parquet` (~144.4 MB)

### Do not prioritize yet
- CLadder
- CLEAR

