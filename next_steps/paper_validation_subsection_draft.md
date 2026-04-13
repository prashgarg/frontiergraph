# Draft: Validation Section Replacement

Date: 2026-04-03

This note gives a concrete replacement for a benchmark-heavy validation section. The aim is to keep the paper's validation aligned with the paper's actual object.

## 1. What "prospective validation" means here

In this paper, the main empirical object is a ranked shortlist of candidate questions generated from the literature observed through year `t-1`. Prospective validation means that the graph is frozen at that date, candidates are ranked using only information available then, and the evaluation asks whether those suggested links later appear in the literature. This is the paper's main validation exercise because it tests the thing the paper is actually trying to do: surface plausible next questions before they become explicit in later papers.

That is a different exercise from asking whether the extraction layer reproduces an external benchmark graph exactly. External graph benchmarks can still be informative, but they are not the paper's main target. The paper's main target is whether the surfaced questions are prospectively useful.

## 2. Main-text version

### 4.X Validation and interpretation

The paper's main validation is prospective rather than reconstructive. At each cutoff year, I freeze the literature map using only papers observed through `t-1`, rank candidate directed links using information available at that date, and then ask whether those links later appear in the literature over horizons of 3, 5, 10, and 15 years. This design is the most relevant validation exercise for the object studied here. The question is not whether the extraction layer can reproduce every graph representation used in other benchmark datasets. The question is whether the resulting shortlist helps surface plausible next questions before they become explicit in later work.

This distinction matters because the graph object in this paper is a paper-local semantic claim graph built from titles and abstracts. Existing external graph benchmarks often encode different objects: lower-level variable graphs, figure-specific causal diagrams, or structure that is only fully recoverable from the complete paper rather than from titles and abstracts alone. For that reason, I do not treat pooled overlap with external benchmark graphs as the paper's primary validation evidence. Instead, the main paper relies on the prospective backtest and uses a small number of qualitative extraction examples to show what the extracted graph captures well and where the remaining differences are mostly about abstraction level rather than simple extraction failure.

## 3. Shorter version if space is tight

### 4.X Validation

The main validation exercise in this paper is prospective. At each cutoff year, I freeze the graph using only information available through `t-1`, rank candidate links, and test whether those links later appear in the literature. That is the central validation object because the paper is about screening plausible next questions, not about reproducing an external graph benchmark.

External graph benchmarks are only partially aligned with this object. Many benchmark graphs encode lower-level variables, figure-specific structures, or content not fully recoverable from titles and abstracts alone. I therefore treat those comparisons as supplementary diagnostics rather than as the paper's main validation evidence.

## 4. Qualitative extraction-validity subsection

### 4.X Extraction validity: qualitative examples

The extraction layer is not meant to recover every possible graph representation of a paper. Its purpose is to produce a paper-local semantic graph that is consistent enough to support candidate generation and prospective ranking. A useful validity check is therefore qualitative rather than purely benchmark-based: does the extracted graph capture the main conceptual relations in the abstract, and are the remaining differences mainly about wording, abstraction, or graph resolution?

In hand-reviewed examples, the extraction works best when the abstract itself states a compact set of factors, mechanisms, or outcomes in plain language. In those cases, the extracted graph is often close to a benchmark graph up to minor wording differences. The extraction works less well when the benchmark graph represents figure-internal state transitions, highly specific variables, or relations that are only fully visible in the complete paper. In those cases, the extracted graph often preserves the paper's higher-level semantic structure while differing from the benchmark in abstraction level. That pattern suggests a limit of benchmark comparability more than a pure extraction failure.

These examples are enough to establish the right interpretation for the rest of the paper. The graph used here should be read as a paper-local semantic representation designed for screening candidate questions, not as an attempt to reproduce every lower-level causal diagram that may appear elsewhere.

## 5. Concrete examples

If we want 2--3 examples in the paper or appendix, I would now use actual cases from the exploratory benchmark work.

### Example 1. Close semantic match

Paper: *Interaction of Factors Influencing the Sustainability of Water, Sanitation, and Hygiene (WASH) Services in Rural Indonesia* (`ReCITE 178`)

- Benchmark graph: a compact factor graph linking `social`, `technical`, `environmental`, `institutional`, and `financial` factors to the sustainability of WASH services
- Extracted graph: `institutional factor`, `financial factor`, `environmental factor`, `technical factor`, `social factor`, and `sustainability of WASH services`
- What matches: the main factors and the central outcome line up closely
- What differs: the benchmark includes more of the full inter-factor structure than the extracted graph
- Interpretation: this is a close semantic match. The main issue is incomplete recovery of the fuller benchmark interconnections rather than a disagreement about the paper's core object.

### Example 2. Abstraction mismatch

Paper: *The Sustainable Development of the Economic-Energy-Environment (3E) System under the Carbon Trading (CT) Mechanism: A Chinese Case* (`ReCITE 258`)

- Benchmark graph: a variable-level system graph linking `GDP`, `energy consumption`, `energy gap`, `energy policies`, `CO2 emissions`, and environmental governance costs
- Extracted graph: a more policy-centered graph linking the `carbon trading mechanism`, quotas, `CT price`, `GDP`, `CO2 emissions`, and the sustainable development of the `3E` system
- What matches: several central concepts overlap, especially `GDP`, `energy consumption`, and `CO2 emissions`
- What differs: the extracted graph summarizes the paper around the policy mechanism and system-level outcomes, while the benchmark preserves a more decomposed internal mechanism graph
- Interpretation: the extracted graph captures the paper's higher-level semantic structure, while the benchmark encodes a more variable-level object

### Example 3. Recoverability limit

Paper: *Hydropolitical System Archetypes: Feedback Structures, Physical Environments, Unintended Behaviors, and a Diagnostic Checklist* (`ReCITE 90`)

- Benchmark graph: a specific low-level causal loop among five archetype variables such as unilateral water capture and downstream development
- Extracted graph: a semantic graph around `system archetypes`, `feedback loop structures`, `unintended behaviors`, a `diagnostic checklist`, and `transboundary water basins`
- What matches: the extracted graph captures the abstract's stated framing around archetypes, feedback structures, and diagnostic use
- What differs: the benchmark graph uses a much more specific loop that is not stated directly in the title and abstract
- Interpretation: this is only partly fair as an abstract-level comparison. The benchmark depends on structure that is not fully recoverable from title and abstract alone.

## 6. One-sentence appendix note if needed

If we want a restrained appendix sentence on the external benchmark runs, I would use something like:

> In exploratory comparisons to existing graph benchmarks, overlap was limited and strongly shaped by differences in abstraction level, graph target, and what can be recovered from titles and abstracts alone, so we do not treat pooled benchmark overlap as the paper's primary validation evidence.

## 7. What I would not write

I would avoid saying:

- `the extraction layer was externally validated on benchmark X`
- `the method performs well on external graph benchmarks`
- `benchmark overlap confirms graph quality`

Those claims would overstate what the exploratory benchmark work can support.

## 8. My recommendation

For the paper, I would do:

1. keep prospective validation as the main validation object
2. add one short extraction-validity subsection in the style above
3. include at most 2--3 hand-reviewed examples
4. keep the external benchmark runs in internal notes unless we need a very restrained appendix sentence

## 9. How failures should feed back into methodology

These failures are still useful. They tell us what kind of improvement is worth trying.

The useful split is:

1. **close semantic match but incomplete recovery**
   - this points toward prompt or extraction improvements
   - for example, recovering more of the benchmark's inter-factor edges when the abstract already names the factors clearly

2. **abstraction mismatch**
   - this points toward graph-object choice rather than a simple error
   - the right response is usually not to force the main extractor to mimic the benchmark, but to decide whether a second benchmark-facing extraction mode is worth maintaining

3. **recoverability limit**
   - this is not a prompt problem
   - the right response is to mark these cases as unfair targets for title-plus-abstract extraction

So the benchmark exercise is still useful if we use it to separate:

- errors we can fix
- graph-object choices we should acknowledge
- comparisons we should simply stop treating as fair

## 10. On an LLM-based false-positive filter

There is a plausible future use for LLMs as a precision filter on surfaced candidate questions, but it should be framed carefully.

The safest use is **contemporary filtering**, not historical backtesting. For example, in 2026 we could ask an LLM to score current outstanding candidate questions on dimensions such as:

- is the question concrete enough to become a paper?
- is the endpoint relation already too obvious or already saturated?
- does the nearby support actually point toward a coherent question rather than a noisy graph coincidence?

That could help reduce false positives in the current recommendation layer.

The risky use is to ask an LLM to simulate ex ante judgments at older cutoffs such as 2005. That is much harder to interpret because model knowledge may leak later scientific developments into the score even if the prompt only shows the 2005 graph snapshot.

So if we use an LLM filter, I would recommend:

1. use it for **current 2026-facing shortlist refinement**
2. present it as a **supplementary precision layer**, not as the core ranking object
3. avoid using it as the main historical backtest unless we have a very clear leakage-control strategy
