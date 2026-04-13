# FrontierGraph Paper: Improvement Notes

Date: 2026-03-31

This note collects the main discussion so far on how to make the paper much stronger in the next draft.

## 1. Core reframing

The current paper is cleanest when the reader can answer:
- what is the empirical object?
- what is being compared?
- what is the main benchmark?

The original draft's clean backbone is:
- object: a missing directed link
- comparison: graph-based score versus preferential attachment
- outcome: whether the link later appears

That backbone is valuable and should not be thrown away.

But for the next draft, the substantive object should be richer.

### Recommended reframing

- **Substantive object:** a path-rich research-program candidate, or unresolved question that is increasingly supported by nearby structure
- **Measurement anchor:** a missing directed link between endpoints
- **Supporting structure:** nearby mediators, repeated local motifs, contextual support, and path development

Short version:
- the missing edge is not the whole research question
- it is the simplest observable trace of a broader emerging research program

## 2. Keep the clean benchmark, but downgrade its ambition

The direct-edge prospective benchmark should stay.

But it should be presented as:
- a disciplined benchmark
- a measurement anchor
- not the full theory of how research progresses

That means the paper can say:
- we start with the missing direct link because it is clean and prospectively testable
- but many important research moves are richer than direct-link closure

## 3. Make path development a central contribution

One of the strongest ideas already in the draft is:
- research often develops by adding mediator structure around existing direct relations
- not only by closing missing direct edges

This should move from:
- interesting side result

to:
- central contribution

The paper should explicitly distinguish two development margins:
- **path-to-direct**
- **direct-to-path**

and interpret them substantively.

## 4. Add a dynamic unresolved-question panel

This is one of the most promising upgrades.

For each unresolved pair-year, build a panel of signals such as:
- number of supporting paths
- number of distinct mediators
- mediator diversity
- support across journals
- support across methods
- citation-weighted support
- recent growth in local support
- credibility or stability of surrounding edges

Then ask:
- does the question later close directly?
- does it deepen through new mediator structure?
- does it remain unresolved despite accumulating support?

This would let the paper talk about:
- **question heat**
- **ripeness**
- **researchability**

instead of only top-K edge prediction.

## 5. Shift the interpretation from "prediction" toward "screening"

This is essential.

The paper should not read mainly as:
- can we predict the future literature better than a simple baseline?

It should read more as:
- can we help researchers screen plausible next questions under realistic attention constraints?

That is the stronger and more believable contribution.

## 6. Human or LLM evaluation of current unresolved questions

This is a useful extension, but should remain supplementary.

Possible exercise:
- take current unresolved high-ranked questions
- compare graph-based ranking to preferential attachment or other baselines
- ask human readers and/or LLMs to rate:
  - plausibility
  - paper-shapedness
  - specificity
  - mechanism clarity
  - novelty

This is useful because the real use case is:
- screening today

not only:
- checking what later realized historically

## 7. Main analyses to keep and strengthen

The current paper already has several strong pieces. The next draft should preserve them but sharpen interpretation.

### A. Main strict shortlist benchmark

Keep:
- top-100 or tight-shortlist benchmark
- preferential attachment comparison

Interpret honestly:
- the popularity benchmark is hard to beat at the very top

### B. Attention-allocation frontier

This is one of the best parts of the paper.

Keep:
- performance over larger shortlists
- realistic attention-allocation interpretation

This is where the graph-based approach becomes more compelling.

### C. Value-weighted outcomes

Keep:
- later realized links weighted by downstream reuse or impact

Potentially strengthen with:
- year-normalized citation measures
- better external importance measures

### D. Heterogeneity atlas

Keep:
- journal splits
- method-family splits
- topic-region splits
- funding-related heterogeneity

This moves the paper away from a single pooled horse race.

### E. Path-development analysis

Promote this section.

It should not feel like:
- one extra fact at the end

It should feel like:
- one of the main reasons the direct-edge benchmark is incomplete

## 8. Better external importance measures

OpenAlex is already useful, but the next draft could use more of what is already available there:
- cited_by_count
- cited_by_percentile_year
- citation-normalized percentile
- FWCI-like relative impact measures if available
- counts_by_year
- funders

Additional datasets worth considering:

### A. Semantic Scholar

Most useful additional source if matched carefully.

Potentially helpful:
- citation counts
- influentialCitationCount
- broader graph metadata

### B. RePEc / EconPapers / CitEc

Potentially very useful for economics-specific validation:
- working paper appearance
- economics citation infrastructure
- idea emergence before journal publication

### C. OpenCitations / Crossref

Useful mainly for robustness and metadata enrichment.

## 9. Suggested paper structure for the next draft

Recommended high-level order:

1. Question and setting
2. Corpus and graph construction
3. Baseline empirical object: missing direct link
4. Ranking design and benchmark
5. Main top-K result
6. Attention-allocation frontier
7. Heterogeneity
8. Path development and richer question objects
9. Dynamic ripeness / unresolved-question panel
10. Discussion

This keeps the paper disciplined while making room for the richer object.

## 10. What to move online versus keep in the paper

Keep in the paper:
- core benchmark design
- main top-K result
- frontier result
- one compact heterogeneity section
- one compact path-development section
- credibility summary

Move online:
- full candidate-question catalog
- full heterogeneity atlas
- full robustness sweeps
- full extraction and normalization audit
- large example library

## 11. Important language choices

Terms to use carefully:
- "missing directed link" is fine as a measurement object, but not enough as the substantive object
- "path-rich question" is useful, but define it plainly
- "research-program candidate" may be a stronger economist-facing phrase in prose

Recommended language:
- the missing edge is an observable trace of a broader emerging research program
- some important questions do not close directly; they thicken through mediators
- the aim is screening, not replacing judgment

## 12. Concrete near-term writing tasks

1. Rewrite the introduction around the richer object.
2. Rewrite the empirical-object section so the missing edge is clearly the anchor, not the whole theory.
3. Promote path-development results.
4. Design the dynamic unresolved-question panel.
5. Decide whether to add a small LLM or human evaluation exercise.
6. Decide which external importance measure to prioritize first.

