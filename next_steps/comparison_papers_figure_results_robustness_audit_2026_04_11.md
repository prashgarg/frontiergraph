# Comparison Papers: Figures, Results, and Robustness

This note audits the papers closest to the current paper's object and asks a narrow question: how do they present figures, report results, and handle robustness, and what should this paper learn from them?

The comparison set here is:

- Gu and Krenn (2025), *Forecasting High-Impact Research Topics via Machine Learning on Evolving Knowledge Graphs* (`Impact4Cast`)
- Sourati and Evans (2023), *Accelerating Science with Human-Aware Artificial Intelligence*
- Tong et al. (2024), *Automating Psychological Hypothesis Generation with AI: when Large Language Models Meet Causal Graph*
- Krenn and Zeilinger (2020), *Predicting Research Trends with Semantic and Neural Networks with an Application in Quantum Physics*

## 1. Impact4Cast

### What it does well

- The paper makes the engineering benchmark visually legible. It leans on simple performance figures that compare models directly rather than asking the reader to infer the hierarchy from text.
- The results are stated as forecasting gains over clear baselines. The headline is not a vague claim about discovery; it is a predictive claim about future high-impact topic emergence.
- The paper uses a broad feature stack and backs that up with ablations. This is useful because it turns "the model works" into "which signals matter and how much."

### Limits relative to our paper

- The object is topic impact, not an economics-facing candidate question.
- The graph is not built from directed claim-like edges.
- The evaluation is strong on machine-learning benchmarking but weaker on human interpretability and question-level inspection.

### What we should learn

- Keep one or two benchmark figures that are visually plain and comparative.
- Keep appendix diagnostics that explain what the model is loading on.
- Do not imitate the paper's engineering breadth if it makes our object less interpretable.

## 2. Sourati and Evans (2023)

### What it does well

- The paper has a very clear conceptual move: content-only prediction misses the fact that discoveries are made by people with specific expertise. That makes the empirical object easy to remember.
- Robustness is not just "more baselines." It comes from testing the same logic across sparse settings and showing where the gain is larger.
- The paper's comparative claim is crisp: human-aware models help especially where the literature is sparse.

### Limits relative to our paper

- The object is future discovery under expertise constraints, not shortlist screening under scarce reading budgets.
- The model is less directly inspectable question by question than ours.

### What we should learn

- Our heterogeneity sections should keep asking: where should this method help more, and why?
- Regime-split evidence is strongest when it has a conceptual prediction behind it, not when it is just a long appendix table.
- When we discuss sparse versus dense neighborhoods, the comparison to Sourati should stay explicit: graph structure alone is not enough in very thin spaces; expertise-aware layers are a natural next step.

## 3. Tong et al. (2024)

### What it does well

- The paper is very strong on workflow presentation. It uses a simple pipeline figure that makes the object and steps obvious.
- The evaluation uses blinded human ratings rather than only model-side metrics.
- The results section is easy to parse because the comparison groups are concrete: graph+LLM, LLM-only, PhD students, and expert-refined outputs.
- There is a second layer of validation beyond the human scores, using semantic-space analysis to understand why the groups differ.

### Limits relative to our paper

- The evaluation is expert judgment on a small generated set rather than a prospective historical benchmark.
- The setting is one focal domain in psychology ("well-being"), not a broad field-wide backtest.
- The statistical evidence is narrower than our historical benchmark evidence.

### What we should learn

- Human evaluation is useful when the rating object is narrow and clearly defined.
- The human-facing object should be easy to inspect. Their paper benefits from showing generated hypotheses as objects a reader can react to.
- We should keep our appendix human and LLM usefulness exercises secondary to the historical benchmark, not let them drift into the headline empirical claim.

## 4. Krenn and Zeilinger (2020)

### What it does well

- The paper presents a clean "semantic network -> future trend prediction" story with a strong motivating example from one scientific field.
- The temporal holdout logic is straightforward and easy to understand.
- The figures are used to show the network object first, then the predictive benchmark.

### Limits relative to our paper

- The object is future concept association in quantum physics, not candidate questions in economics.
- The paper does not need to separate a benchmark anchor from a surfaced question object, because the semantic concept network itself is the displayed object.

### What we should learn

- There is value in keeping one very clear graph-object figure near the front of the paper.
- Temporal discipline is a major source of credibility and should stay visually obvious.

## 5. What the closest papers do not do, and why that matters

None of the closest papers combine all four of the things this paper is trying to do:

- a directed claim-like graph in economics
- a prospective walk-forward historical benchmark
- explicit comparison with cumulative advantage as the main null
- a surfaced question object that is richer than the benchmark anchor

That means we should not expect to borrow one full presentation template from any single comparison paper. The useful move is to borrow locally:

- from Impact4Cast: clean benchmark comparison figures and ablations
- from Sourati and Evans: conceptually motivated heterogeneity and regime splits
- from Tong et al.: human-facing workflow figure and small-scale blind evaluation
- from Krenn and Zeilinger: temporal holdout clarity and graph-object legibility

## 6. Concrete lessons for our current manuscript

### Figures

- Keep figure titles declarative and plain. The strongest comparison papers rarely title figures in jargon.
- Every main figure should answer one question only.
- The paper should continue to distinguish:
  - benchmark figures
  - screening-budget figures
  - heterogeneity figures
  - surfaced-object figures

### Results writing

- Headline results should always compare to one named null or one named baseline family.
- Heterogeneity should be framed as "where the method should help more" rather than "here are many subgroups."
- Path-development results should be interpreted against recombination/disruption work, not left as a purely internal graph pattern.

### Appendix robustness

- The appendix is strongest when it does one of three things:
  - checks temporal discipline
  - explains what the model is using
  - tests whether the surfaced object is legible to humans or a parallel evaluator

- The appendix is weakest when it becomes a holding area for old diagnostics that no longer map cleanly to the current benchmark object.

## 7. Bottom line

The closest papers suggest a simple standard:

- the main text should show one clean benchmark object, one clean budgeted-screening interpretation, and one clean set of conceptually motivated heterogeneity results
- the appendix should support credibility through temporal robustness, feature/diagnostic interpretation, and small-scale human-facing validation

That is already close to where the current paper has moved. The main thing to preserve is discipline: every figure and every robustness section should answer a specific paper question, not just display one more output from the pipeline.
