# Economics-facing restructure plan

## Objective

Tilt the paper toward economists without losing rigor.

The benchmark remains necessary, but it is no longer the product. The product is
an empirically disciplined claim about where economics leaves open questions and
how the literature more often develops.

## Main-text order

### 1. Introduction

Keep:
- broad question
- two historical objects
- one mechanism-thickening example
- one direct-closure example
- one plain statement of the empirical comparison

Cut or downweight:
- long benchmarking rhetoric
- excessive language about screening pipelines

### 2. Related literature and positioning

Keep:
- economics of ideas / science-of-science / cumulative-advantage null
- short positioning against closest graph papers

Downweight:
- long CS framing
- tool-landscape discussion that is not needed for an economist reader

### 3. Data, graph object, and evaluation design

Keep:
- corpus
- extraction and normalization in plain language
- two graph-grounded objects
- prospective evaluation logic

Demote in tone:
- detailed feature-language
- reranker mechanics as if they are themselves a main contribution

### 4. Main results

Recommended order:
1. Paired historical validation on the strict shortlist
2. How the literature more often develops: mechanism thickening versus direct closure
3. Richer ranking rule as confirmation, not the centerpiece
4. Current frontier and examples, once paired-family runs are ready
5. One substantive heterogeneity result only if it survives as cleanly economist-interpretable

Principle:
- the first benchmark subsection establishes credibility
- the second subsection gives the substantive finding
- the third subsection says the richer ranking rule confirms and sharpens the baseline

### 5. Discussion and conclusion

Lead with:
- what the paper says about how economics moves
- what the graph is useful for under scarce attention

Compress:
- engineering details
- long comparisons with other ML systems

## Appendix order

Recommended order:
1. Guide to the appendix
2. Paired family extensions
3. Paired budget comparison
4. Path-length axis
5. Direct-closure-only extensions
6. Extraction prompts and schema
7. Ontology construction
8. Graph evolution over time
9. Benchmark construction and significance
10. Reranker design and grouped diagnostics
11. Heterogeneity atlas
12. Credibility audits
13. Supplementary current-usefulness validation

Reason:
- paired-family material should stay near the front because it extends the main argument
- family-specific and engineering-heavy material should come later

## What to cut from main immediately

Move or keep in appendix:
- reading-budget frontier if it is still family-specific
- value-weighted outcomes
- grouped SHAP and grouped feature decomposition
- VIF and multicollinearity diagnostics
- failure-mode profiles
- temporal generalization
- broad heterogeneity atlas
- LLM usefulness
- path-length comparison
- graph-evolution descriptives

## What to promote once paired-family runs finish

Promote candidate:
- paired budget comparison, if both families show a clean and interpretable difference
- paired current-frontier examples
- one paired heterogeneity result if it says something economists can use

Do not promote by default:
- path-length axis
- LLM usefulness
- graph-evolution descriptives

## Results still worth keeping but not foregrounding

These are not wasted:
- reranker diagnostics
- temporal holdout
- grouped coefficients and grouped SHAP
- value-weighted and broader-budget checks
- current-usefulness validation

They remain useful as:
- audit material
- referee insurance
- appendix evidence that the main pattern survives harder probes

## Material that may be low-return

Potentially low-return for the main paper:
- long model inventories
- several closely related heterogeneity figures that do not change interpretation
- any figure that mainly says the reranker is well behaved rather than saying something about economics

These should remain available, but they do not need to shape the main narrative.

## Open slots for live runs

### Main text

- after paired strict-shortlist subsection:
  - keep paired benchmark figure and table
- after path-development subsection:
  - insert paired current-frontier examples subsection when ready
- after richer-ranking subsection:
  - optionally insert one paired budget or heterogeneity subsection if clean enough

### Appendix

- `appendix_paired_budget_extensions.tex`
  - waiting for direct-to-path budget pairing
- `appendix_path_length_axis.tex`
  - waiting for `max_len = 2,3,4,5`
- `appendix_paired_family_extensions.tex`
  - already live, can absorb more paired current-frontier material

## Editorial rule for the next pass

Whenever a result is mentioned in the main text but not shown there:
- add one sentence saying what it checks
- add one sentence saying whether it confirms the main pattern, weakens it, or changes interpretation
- cite the appendix section, figure, or table directly

That keeps rigor visible without making the main paper read like a diagnostics dump.
