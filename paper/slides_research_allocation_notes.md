# FrontierGraph Research-Allocation Deck Notes

## Mainline

### 1. Title
- Frame this as a paper about research allocation, not product design.
- The question is prospective: what should economics work on next?
- The core object is a transparent tool built from claim-graph structure.

### 2. Why this problem matters
- Topic choice is a scarce-attention problem, especially for early-stage researchers.
- The hard part is finding questions between crowded and too-vague.
- Motivate this as a practical economics problem, not a generic ML task.

### 3. What the paper does
- We rank candidate research questions from missing links in literature structure.
- Then we test prospectively whether those links appear later.
- The paper contribution is transparency, prospective evaluation, and interpretation.

### 4. From corpus stock to candidate questions
- Freeze the literature at `t-1`.
- Missing links implied by local structure become candidate next papers.
- Emphasize that this is candidate generation, not the final claim.

### 5. How the score works
- Give the intuition only: plausibility, underexploration, and anti-popularity discipline.
- Avoid equations here; point to the appendix if asked.
- Stress that the score is decomposable and inspectable.

### 6. How we test it prospectively
- Every vintage uses only information available at that time.
- We score first appearance in future horizons, not in-sample fit.
- Preferential attachment is the natural benchmark because popularity is hard to beat.

### 7. Main result: honest benchmark
- Say this plainly: the full rolling result favors preferential attachment.
- This is a credibility slide, not bad news to hide.
- The question becomes where a transparent model still adds value.

### 8. Why the project is still scientifically interesting
- Held-out tuning shows the gap can close or reverse under a stricter decision-use setting.
- Broader top-K slices matter because researchers browse more than one suggestion.
- This keeps the tool scientifically interesting even with mixed headline results.

### 9. What kind of questions it surfaces
- The model surfaces gap-type questions more than popularity closures.
- That is substantively different from a pure popularity baseline.
- This is where the research-allocation interpretation starts to matter.

### 10. Concrete examples
- Treat these as current illustrative outputs, not validation proof.
- Use them to show what the object looks like in economics terms.
- Keep the tone speculative and paper-oriented.

### 11. What this tool is and is not
- It is a screening aid, not a truth machine.
- It does not replace reading papers or judging importance.
- The claim is auditable prioritization, not authority over the agenda.

### 12. FrontierGraph as research artifact
- The site and workbench are downstream interfaces built on the scientific core.
- They matter because they make the outputs inspectable.
- But they are not the evidence for the paper.

### 13. Takeaways / next paper agenda
- Re-state the honest position: mixed benchmark, still promising as a transparent research-allocation tool.
- The next paper needs stronger external and prospective validation.
- End on the lockbox / expert-validation agenda rather than on the product.

## Appendix

### A1. Literature anchors
- Use only if someone asks for the literature positioning.
- Keep it short: burden of knowledge, undiscovered public knowledge, link prediction, motifs.

### A2. Relation to the Causal Claims extraction foundation
- Distinguish clearly between the extraction paper and FrontierGraph as downstream ranking/interface.
- Cite `Causal Claims in Economics` and `causal.claims`.

### A3. Data construction
- Explain why the evaluation corpus is smaller than the current public build.
- This is the cleanest place to justify the hybrid scientific story.

### A4. Candidate generation details
- Walk through the missing-link enumeration step.
- Stress provenance retention through mediators.

### A5. Full score equation and component definitions
- Use when asked how the score is actually formed.
- Clarify that hub penalty is there to resist popularity collapse.

### A6. Metric definitions and why the numbers are small
- Explain the enormous candidate space.
- Re-anchor interpretation around benchmarks, not absolute magnitudes.

### A7. Leakage audit, CIs, significance
- Use if someone pushes on vintage integrity or statistical discipline.
- Emphasize frozen cutoffs and paired comparison logic.

### A8. Full rolling result table
- This is the full, blunt benchmark summary.
- Useful if someone wants the exact values instead of the simplified chart.

### A9. Held-out tuning / ablation path
- Explain what changes under tuning and why it matters.
- Be careful not to oversell it as the definitive result.

### A10. Attention-allocation frontier
- This is the bridge from prediction to workflow relevance.
- The key point is that researchers browse lists, not only rank-1 outputs.

### A11. Impact-weighted evaluation
- Use this if the room cares about “important” future links, not just realized ones.
- Keep the interpretation cautious.

### A12. Gap vs boundary decomposition
- This is the substantive anatomy slide.
- It helps answer “what kind of questions does the model want?”

### A13. Field heterogeneity
- Useful if someone asks whether the aggregate story hides discipline differences.
- Reinforce that one global score is not the whole story.

### A14. More examples / case diagnostics
- Use this when the room wants more concrete economics examples.
- Keep reminding them these are illustrative current outputs.

### A15. External transfer design
- This is the forward-looking scientific roadmap for broader validation.
- Emphasize external corpora and pre-registered discipline.

### A16. Expert validation + prospective lockbox
- This is the strongest “next step” slide for turning the prototype into a paper.
- End here in a skeptical room if needed.
