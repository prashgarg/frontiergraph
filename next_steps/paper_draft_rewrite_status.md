# Paper Draft Rewrite Status

## Current state

The full draft rewrite is now complete in:

- `paper/research_allocation_paper.md`
- `paper/research_allocation_paper.tex`

The TeX manuscript is now the hardened source-of-truth draft and compiles successfully.

Both drafts now follow the locked hierarchy consistently:

1. measurement anchor = missing directed link
2. surfaced object = path-rich or mechanism-rich question
3. routed overlays = context-transfer and evidence-type expansion
4. internal support layer = family-aware comparison and ontology-vNext

## What changed in the rewrite

### 1. Abstract and introduction

The front of the paper now:

- defines the benchmark target immediately as later missing-link appearance
- defines the surfaced object immediately after as a richer path/mechanism question
- states the simple main comparison early:
  graph-based score versus preferential-attachment-style benchmark
- frames the contribution as a screening tool under attention constraints

### 2. Main-text ordering

The body now introduces material in a cleaner sequence:

- corpus and graph construction
- direct-edge retrieval anchors
- benchmark and frontier results
- path development
- curated current examples
- internal semantic support as a late interpretive layer

This keeps routed overlays and ontology-vNext out of the core pitch.

### 3. Example discipline

The main text now uses the curated four-example set consistently:

- baseline surfaced object
- context-transfer overlay
- evidence-type-expansion overlay
- family-aware extension

The older crowded example presentation is gone.

### 4. TeX hardening and appendix framing

- the TeX abstract and introduction now match the locked hierarchy
- main-text figures and tables now sit in the revised argument order
- the main-text example table is locked to the curated four-example set
- the appendix now carries a short reserve-example table rather than another crowded headline example cluster
- the credibility appendix is self-contained inside the manuscript rather than depending on a missing generated include
- figure asset paths now point to the live paper-asset directories used by the manuscript build

## What this means

The paper now reads much more like:

- a benchmarked screening paper

and much less like:

- a pipeline changelog
- an ontology paper in disguise
- a collection of extensions introduced before the baseline is clear

## What changed after the rewrite

The manuscript is no longer only structurally cleaner. It now reflects the newer underlying benchmark results too.

- the benchmark language now distinguishes:
  - transparent graph score as the readable retrieval layer
  - learned reranker as the strongest graph-based benchmark
- the appendix now includes the expanded benchmark table against:
  - preferential attachment
  - degree plus recency
  - directed closure
- the text now treats diversification as a light screening extension rather than as part of the benchmark winner

## What still remains after the rewrite

The next draft-facing work is now much narrower:

- actual human ratings using the prepared blinded pack
- deciding how prominently to feature diversification in the circulation draft
- circulation-specific polish for title, abstract, and appendix balance
- a referee-facing positioning pass once the target circulation format is chosen
- optional layout cleanup only where it improves readability

The paper no longer needs another large structural rewrite before those steps. The manuscript is now in benchmark-validation and circulation-hardening mode, and the ontology-vNext layer remains frozen except for future reviewed override tables.
