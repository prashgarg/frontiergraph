# Paper Next Steps After Full Refresh

This note records the next steps after the full analytical refresh, literature-positioning pass, and reference audit. The point is to separate true paper decisions from optional polish and from later website/product work.

## A. Immediate manuscript decisions

These are the highest-priority paper decisions because they affect how the manuscript reads to a referee.

### 1. Lock the bibliography policy

Recommendation:

- Keep standard scholarly references in the bibliography.
- Move website/system references out of the main bibliography unless they are themselves the object of study.
- If we want to mention current AI tools or systems as examples, cite them in a short footnote or a short inline note, not as ordinary academic references.

Reason:

- In an economics paper, bibliography entries should mostly be stable scholarly objects: journal articles, books, working papers, conference papers, or clearly identifiable benchmarks.
- System pages such as product websites, reviewer guides, and tool overviews are real, but they are not the same kind of evidence.
- Keeping them in the bibliography weakens the reference list by mixing archival research claims with informal system examples.

Current paper implication:

- Strong keep in bibliography:
  - `zhang2025scientificmethod`
  - `shao2025sciscigpt`
  - `si2024llmideas`
  - `agrawal2024ai`
  - `daquin2025kgdiscovery`
  - the rest of the core scholarly references

- Move to footnote or cut:
  - `refine2026`
  - `iclr2026reviewer`
  - `jiangng2026agenticreviewer`
  - `projectape2026`

Best paper version:

- Keep the sentence about the fast-moving AI-assisted-science space.
- Support it with the scholarly references above.
- If examples of deployed systems are still useful, add one short footnote saying that contemporary deployed systems now include manuscript-review and research-assistance tools, with URLs if needed.

### 2. Decide how much of the AI-tools sentence belongs in the main text

Recommendation:

- Keep one compact main-text sentence about AI-assisted scientific work.
- Avoid a long list of named products or websites in the body.
- Use the main text for the scholarly positioning, not for a catalog of tools.

Reason:

- The paper's comparative contribution is not that many AI systems exist.
- The main text should establish the research question, not advertise the current tool landscape.

### 3. Decide whether the human/LLM usefulness appendix stays at current scale or expands

Current state:

- The small human usefulness exercise is useful and honest, but not large enough to carry major argumentative weight.
- The appendix LLM usefulness sweep is larger and informative, but supplementary.

Recommendation:

- Keep both in the appendix in the current draft.
- If there is time before circulation, expand the human usefulness pack from `24` to the larger prepared `48`-item pack.
- Do not hold the current paper draft hostage to that expansion.

## B. Manuscript improvements that add depth

These are good next moves if the goal is a stronger paper, not just a cleaner one.

### 4. Strengthen the literature comparisons around the main results

The recent pass improved this, but three places could still be sharpened further.

#### 4a. Attention frontier

Potential addition:

- Make clearer that the figure is not just about predictive performance by `K`.
- It is about when graph structure helps relative to popularity under scarce attention.

Use:

- Kleinberg et al. on prediction-policy problems
- Agrawal et al. on prioritized search
- Bloom/Jones on frontier navigation and knowledge burden

#### 4b. Path development

Potential addition:

- Make clearer that the path-development result speaks to a substantive science-of-science question:
  - how often literatures deepen existing claims versus close implied structural gaps

Use:

- Foster et al. / Kedrick et al. on gap opening
- Uzzi et al. on structured recombination
- Park et al. and Petersen et al. on disruption and its measurement

#### 4c. Regime split / heterogeneity

Potential addition:

- Say more explicitly that the method is best understood as a screening device for partially prepared literatures, not for maximally thin discovery spaces.

Use:

- Sourati et al. on human-aware AI and sparse spaces
- Tong et al. on graph-plus-LLM hypothesis generation
- Swanson as the contrasting open-world discovery ideal

### 5. Add one small “what the paper is not” paragraph to the discussion

Recommendation:

- Add one short paragraph that says the paper is not:
  - a theory of scientific creativity
  - a topic-trend detector
  - an LLM-only idea-generation benchmark
  - an open-world discovery engine

Reason:

- This will help referees classify the contribution more precisely.
- The current paper is strongest when read as benchmarked screening under scarce attention.

## C. Appendix tasks worth doing

### 6. Create an appendix subsection on relationship to adjacent benchmark objects

This would be a short synthetic appendix subsection, not a literature review.

Suggested structure:

- missing-link prediction versus surfaced-question screening
- topic surveillance versus budgeted screening
- open-world discovery versus partially prepared literatures
- historical benchmark versus current-usefulness validation

Reason:

- The paper now contains all of these distinctions, but they are spread out.
- One appendix subsection could make the conceptual architecture explicit.

### 7. Turn the comparison-paper audit into an appendix drafting aid

Existing note:

- `next_steps/comparison_papers_figure_results_robustness_audit_2026_04_11.md`

Recommendation:

- Use that note to improve:
  - figure captions
  - subsection opening sentences
  - appendix robustness framing

The useful rule is:

- every retained figure should answer one paper question
- every appendix robustness subsection should justify why it exists

## D. Technical and editorial cleanup

### 8. Clean the bibliography format

After the reference audit, there are still two cleanup tasks even if the metadata is now correct.

- Standardize types for preprints and working papers:
  - avoid `journal = {arXiv preprint ...}` if the rest of the bibliography uses `@misc` or `@techreport`
- Standardize URLs and DOIs:
  - if a DOI exists, prefer keeping the DOI and using a stable URL only where useful

This is not conceptually important, but it improves paper professionalism.

### 9. Resolve the remaining manuscript-level overfull boxes selectively

Recommendation:

- Fix only the worst overflow points in the final draft stage.
- Do not rewrite good prose solely to silence every LaTeX warning.

Reason:

- The remaining issues are now mostly presentation and appendix layout, not analytical clarity.

## E. Post-paper work

These are real next steps, but they should not distract from the paper.

### 10. Website/product layer

Once the paper draft is stable:

- return to the LLM browse objects
- continue richer current-frontier question rendering
- expand within-field and global browse workflows
- test LLM-assisted rewriting and mechanism suggestions on current frontier candidates only

### 11. Substantive extension: hot versus enduring ideas

This remains promising as either:

- an appendix interpretation
- or a next paper / follow-on method extension

Candidate taxonomy:

- recent-surge
- enduring-structural
- revived / rediscovered
- event-driven transient

This should stay downstream of the core benchmark rather than altering the main ranking pipeline.

## F. Recommended order

If the goal is to keep momentum and improve the paper without reopening the pipeline, the recommended order is:

1. Move website/system references to footnotes or cut them from the bibliography.
2. Make one more manuscript pass on the discussion and subsection openers using the new literature-positioning logic.
3. Decide whether to expand the human usefulness appendix from `24` to `48`.
4. Standardize bibliography entry types and formatting.
5. Do only selective layout cleanup.
6. Freeze the paper draft and move later work to the website/product stream.

## Bottom line

The paper is now analytically refreshed and conceptually much cleaner than before. The next steps should therefore be disciplined:

- do not reopen core benchmark design
- make a few explicit manuscript decisions
- clean the bibliography logic
- deepen interpretation where it strengthens the paper's identity
- then freeze and move on
