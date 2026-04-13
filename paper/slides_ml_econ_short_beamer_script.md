# What Should Economics Ask Next?

Detailed speaker script for:
[slides_ml_econ_short_beamer.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer.tex)

This note is written as a talk script, not as slide copy. It is meant to help you speak through each slide in detail, while also anticipating likely questions and giving concise answers.

## Opening

### Slide 1: Title

#### What this slide is doing
- Establish the topic quickly.
- Tell the room this is about question choice, not just prediction.
- Signal that the paper is economics-facing, but that the motivation is broader.

#### Suggested script

“This paper asks a simple question: what should economics ask next?

The motivation is that question choice is one of the least formalized parts of research. We have well-developed tools for estimation, causal identification, and model comparison, but much less structure for deciding which open questions are worth inspecting in the first place.

What I do here is build a dated claim graph from published economics-facing papers, use that graph to surface still-open questions, and then validate those screens historically by checking which kinds of candidates later became part of the published literature.

So the paper is partly methodological, but the point is not just to build another ranking system. The deeper goal is to learn something about how economics actually moves, and to ask whether graph structure can help with upstream research choice.”

#### If you want a shorter opening

“The paper is about question choice. I build a dated claim graph from published economics-facing papers, use it to surface still-open questions, and test those screens against later publication.”

#### Likely questions

- Why economics rather than all science?
  - “Economics is the first empirical domain here because the literature is coherent enough to validate carefully, and because the field-level interpretation matters in its own right.”

- Is this meant as a product or as a paper?
  - “The paper comes first. The product-like layer is useful because it forces the surfaced questions to be readable, but the historical validation is the core scientific object.”


## Motivation and method setup

### Slide 2: Why this problem?

#### What this slide is doing
- Explain why question choice matters now.
- Make the AI motivation concrete without sounding speculative.
- Set up the graph as a practical answer to a real bottleneck.

#### Suggested script

“The motivation is that question choice is still the weakly formalized part of research.

We have much better tools for analyzing a paper than for deciding what to work on next. And this becomes more pressing as the literature grows, because local reading becomes harder. A researcher can read a neighborhood of papers, but it is much harder to see what claims are missing, what mechanism structure is only partial, or which nearby questions are repeatedly supported without yet being stated directly.

That is where the graph helps. A graph gives you a structured local object. It lets you look at repeated concepts, repeated paths, and missing links in a way that ordinary literature review usually does only informally.

And the timing matters because if downstream tasks get cheaper with AI, then the bottleneck shifts upstream. If summarizing and coding and drafting get easier, then deciding what is worth asking becomes relatively more important.”

#### Likely questions

- Are you saying economists do question choice badly?
  - “Not badly in an absolute sense. The point is that it is weakly formalized relative to other parts of the workflow.”

- Why is a graph the right object?
  - “Because the object I want is local scientific structure: repeated concepts, observed paths, and missing direct links. A graph is a natural way to represent that.”


### Slide 3: Each paper first becomes a local graph

#### What this slide is doing
- Make the extraction object concrete.
- State sample, model, and source in one place.
- Show that the first step is local and inspectable.

#### Suggested script

“The first step is local. Each paper becomes one small graph.

Operationally, I use GPT-5.4-mini to extract paper-local graphs from roughly 242,000 economics-facing papers from 1976 to 2026. The paper set comes from the top 150 economics journals and economics papers in the top 150 adjacent journals, with metadata from OpenAlex. This extraction setup follows the earlier Causal Claims in Economics project.

The important thing to notice in the figure is that I am not trying to summarize a whole paper into one sentence. I am extracting a very small structured object. In this example, transit investment reduces commute time, which expands reachable jobs. That gives you a local causal neighborhood.

This is useful because later steps do not need the full paper text again. They operate on this extracted local structure.”

#### Likely questions

- Why GPT-5.4-mini here?
  - “Because this is a large extraction task and the object is relatively constrained. The main requirement is consistency and scale.”

- Are you extracting from full text?
  - “No. This pipeline uses titles and abstracts, which is a limitation, but also gives a consistent and scalable source across the corpus.”


### Slide 4: A frozen ontology makes cross-paper matching usable

#### What this slide is doing
- Explain why extraction alone is not enough.
- Show that concept identity is disciplined rather than ad hoc.
- Make the ontology scale and sources legible.

#### Suggested script

“Local extraction is not enough by itself, because the cross-paper problem is really a concept identity problem.

If one paper says ‘commute time’ and another says ‘travel time’, or one says ‘employment’ and another says ‘jobs’, candidate generation only works if those mappings are disciplined. So I freeze an ontology using JEL, Wikidata, OpenAlex topics, OpenAlex keywords, and an economics-filtered Wikipedia layer.

The scale matters. The ontology has about 154,000 rows, and the benchmark graph has more than 230,000 papers and about 1.27 million normalized links.

The key design principle is conservative grounding. Easy cases are resolved by exact or near-exact matching. Harder cases go through semantic embedding retrieval, with multiple ranked candidates stored for audit. So embeddings are being used as retrieval after simpler cases are solved, not as an unconstrained merge rule.

That matters because candidate generation and path counts are only meaningful if concept identity is reasonably stable.”

#### Likely questions

- Why freeze the ontology rather than let the model improvise?
  - “Because otherwise the graph becomes unstable over time and impossible to audit.”

- Is ontology quality a bottleneck?
  - “Yes. This is one of the main engineering bottlenecks, which is why I expose it explicitly.”


### Slide 5: Cross-paper matching creates the shared candidate neighborhood

#### What this slide is doing
- Move from one paper to many papers.
- Show how separate local graphs become a common neighborhood.
- Make the missing-edge idea intuitive.

#### Suggested script

“Once concepts are normalized across papers, local graphs stop being isolated.

Here, Paper A contains a direct claim from transit investment to employment. Paper B contains a mechanism path from transit investment to commute time to reachable jobs. Once those repeated concepts are matched across papers, you can place these edges in one shared neighborhood.

That shared neighborhood is where candidates come from. The missing mechanism edge here is not invented from nowhere. It is a structurally local missing link inside a neighborhood that already has partial support.

This is the step where the graph begins to generate economically interpretable open questions, rather than simply storing extracted claims.”

#### Likely questions

- Is this just transitive closure?
  - “No. The graph helps generate candidates, but later stages decide which candidates are plausible and worth ranking.”

- Why should a missing edge be interesting?
  - “Because it may be the direct claim or mechanism step that the surrounding literature already points toward without having fully stated.”


### Slide 6: The benchmark event is narrower than the surfaced question

#### What this slide is doing
- Clarify the difference between the backtestable object and the readable question.
- Prevent confusion about what exactly is being scored.

#### Suggested script

“This distinction is important: the benchmark event is narrower than the surfaced question.

On the left is a dated event the historical record can actually test. There is a specific missing edge in a local support neighborhood. That edge either appears later in the literature or it does not.

But that is not how a researcher wants to read the object. A researcher wants a readable question, like: could transit investment raise employment through faster commutes and wider job access?

So the benchmark object and the surfaced question are not the same thing. The benchmark uses a narrow, dateable anchor. The surfaced question is a readable compression of the local evidence around that anchor.”

#### Likely questions

- Why not benchmark the full surfaced question?
  - “Because you need a narrow historical event to backtest consistently.”

- Does that make the surfaced question looser than the benchmark object?
  - “Yes, deliberately. The narrow event is for validation. The richer question is for use.”


### Slide 7: Two historical question objects

#### What this slide is doing
- Define the two main empirical families.
- Separate mechanism thickening from direct closure.
- Prepare the audience for the benchmark and interpretation.

#### Suggested script

“At that point the graph can move in two historically different ways, and I keep them separate.

The first is direct-to-path. A direct relation is already in the literature, and later work adds a clearer mechanism around it. I think of that as mechanism thickening.

The second is path-to-direct. Nearby support already exists, but the direct relation itself is still missing. Later work states that direct link explicitly. I think of that as direct closure.

These are not two labels for the same event. They are different kinds of scientific progress, and the rest of the paper treats them symmetrically so we can compare them cleanly.”

#### Likely questions

- Why are both needed?
  - “Because they capture different ways a literature matures. One deepens an existing claim; the other closes a gap.”

- Are these equally common?
  - “No, and that asymmetry becomes one of the substantive findings.”


### Slide 8: Three ranking rules

#### What this slide is doing
- Establish the three orderings before showing results.
- Make the benchmark comparison legible.

#### Suggested script

“Now hold the candidate universe fixed. The question is how to order that same set of still-open questions.

The first rule is preferential attachment. This is the popularity baseline. It favors candidates whose endpoints are already well connected and visible. In practical terms, it asks whether the literature just keeps flowing toward already central concepts.

The second is the transparent graph score. This is a hand-set linear score on the local graph. It rewards motif support, undercompletion, and repeated local confirmation, and it penalizes generic hubs. So it is deliberately interpretable rather than tuned for maximum prediction.

The third is a learned reranker. This is a supervised second-stage model on the same candidates, trained in walk-forward windows, using richer features to estimate later realization.

So the comparison is not between different candidate sets. It is between three statistical ordering rules on the same candidate set.”

#### Likely questions

- Why keep the transparent rule if you have a learned model?
  - “Because interpretability matters. I want to know whether simple graph structure already carries signal.”

- What exactly is preferential attachment here?
  - “A degree-style popularity ordering. It is the right rival if you think attention mostly follows what is already central.”


## Results

### Slide 9: Graph screening beats popularity in historical shortlists

#### What this slide is doing
- Show the core benchmark result.
- Make the difference between the two families intuitive.

#### Suggested script

“This is the main historical benchmark result.

The comparison is simple: in shortlists a researcher could actually inspect, how often do these ordering rules surface candidates that later become realized in the literature?

The main result is that graph-based screening beats the popularity baseline. And the two families help in different ways.

Direct-to-path gives denser shortlists. That means if your goal is to inspect a shortlist and see a higher share of later realizations, the mechanism-thickening family is strong.

Path-to-direct does something different. It captures a larger share of all later-realized links. So it is broader coverage rather than denser hit rates.

The learned reranker improves further, but the important point here is that even the transparent graph rule already beats popularity.”

#### Likely questions

- Are these economically large differences or just statistically detectable differences?
  - “They are economically meaningful at shortlist sizes a researcher might actually inspect.”

- Why does direct-to-path look denser?
  - “Because mechanism thickening is often a more local continuation of already established direct claims.”


### Slide 10: Economics more often deepens mechanisms than closes missing direct links

#### What this slide is doing
- Turn the benchmark into a substantive statement about the field.

#### Suggested script

“This is the paper’s main substantive result.

Once you compare the two historical families directly, the pattern is clear: economics more often deepens mechanisms around existing claims than later closes missing direct links that are locally implied by the graph.

That matters because it says something about how the field moves. The dominant mode of progress is not just that the literature suddenly states a missing direct relation. More often, the literature takes a claim it already believes and then adds more mechanism detail, more decomposition, or more channel structure around it.

So the graph is not only useful as a screen. It also reveals something about the field’s path dependence.”

#### Likely questions

- Could this be an artifact of titles and abstracts rather than a real feature of economics?
  - “It could matter at the margin, but the asymmetry is strong enough that I read it as a real field-level pattern.”

- Is this specific to economics?
  - “Possibly not. But the paper establishes it here first rather than assuming it generalizes.”


### Slide 11: What to do with that result

#### What this slide is doing
- Bridge from historical validation to present-facing use.
- Prevent the next slide from looking like an unrelated product demo.

#### Suggested script

“This result changes how we should use the graph.

The historical exercise does two jobs. First, it tells us the screen is not arbitrary: some graph-based shortlists do outperform popularity. Second, it tells us what kind of open question the graph tends to surface well.

That means the next step is not another benchmark. It is to move from historical validation to current candidate inspection. In other words: if the screen has some real historical discipline behind it, what does it surface at the current frontier?

But I would read those surfaced questions as prompts for reading and judgment, not as final recommendations.”

#### Likely questions

- Why not stop at the backtest?
  - “Because the practical value comes from using the historically validated screen on current open questions.”

- Is this a recommendation engine?
  - “Only in a weak sense. It is better thought of as a disciplined reading aid.”


### Slide 12: The current frontier looks like a set of readable mechanism questions

#### What this slide is doing
- Show what the output looks like in practice.
- Make the questions feel usable rather than abstract.

#### Suggested script

“This is what the current-facing layer looks like.

The key thing to notice is that the surfaced objects are readable mechanism questions. They are not raw graph edges, and they are not generic prompts like ‘does X affect Y?’ They are meant to be the kind of question a researcher could actually inspect, assess, and potentially build from.

I would interpret them as aids for what to inspect first. They are a disciplined way to surface candidates from the literature’s local graph structure. They are not substitutes for judgment, and they are not a claim that the top-ranked question is automatically the best project.”

#### Likely questions

- How much editorial rewriting is happening at this stage?
  - “There is a real presentation layer here. The readable question is a rendering of the underlying benchmark anchor and support graph.”

- Are these all mechanism questions?
  - “The present-facing layer emphasizes mechanism questions because they are richer and usually more useful to inspect.”


### Slide 13: Who takes these up later?

#### What this slide is doing
- Add economist-friendly heterogeneity.
- Show that uptake is not just a generic diffuse process.

#### Suggested script

“This slide gives two additional facts that economists usually find interesting.

On the left is bundle uptake. About 95 percent of realizing papers take up exactly one historically predicted edge. Mixed-family bundles are extremely rare, and when papers do take up more than one prediction, the bundle is usually very local in graph space.

So the historical uptake process is not mainly a story of papers absorbing lots of graph suggestions at once. Realization is usually narrow and local.

On the right is adopter profile. Path-to-direct questions are more often taken up by larger, more funded, and more cross-country teams. Direct-to-path looks broader and more diffuse across later papers.

That is useful because it suggests the two families differ not only in what they surface, but also in what kind of scientific organization seems to move toward them.”

#### Likely questions

- Should I read this as causal?
  - “No. These are descriptive adopter-profile differences, not causal claims about team structure.”

- Why do larger teams show up more in path-to-direct?
  - “My reading is that direct-closure projects may require more coordinated accumulation and synthesis, but I would keep that as interpretation rather than a firm claim.”


## Closing

### Slide 14: Conclusion

#### What this slide is doing
- End with three claims:
  - what was built
  - what was found
  - what this prototype is for

#### Suggested script

“To conclude, the paper builds a dated claim graph from published economics-facing papers, defines two historical question objects, and validates graph-based screening in a walk-forward setting.

The main empirical result is that graph screening improves on popularity, and that economics more often deepens mechanisms around existing claims than later closes missing direct links.

And the larger takeaway is that this is a prototype for AI-assisted question choice. I do not think of it as an autopilot for research. I think of it as a disciplined way to surface what might be worth reading and asking next.

So the contribution is partly a method, partly a result about how economics moves, and partly a proof of concept that upstream research choice can be made more inspectable.”

#### Strong final line

“Not a machine for choosing papers for us, but a way to make question choice less opaque.”

#### Likely questions

- What is the main limitation?
  - “Titles and abstracts, ontology quality, and the gap between benchmark anchors and readable surfaced questions.”

- What would the next version do?
  - “Use richer text sources, better mechanism curation, and tighter field-specific screening.”


## Likely audience questions after the talk

### 1. Is this forecasting science, or just organizing it?

Suggested answer:

“Both, but in an asymmetric way. The historical benchmark uses forecasting-like validation, but the practical use is better thought of as structured screening rather than prediction for its own sake.”

### 2. Why should we trust LLM extraction for a scientific graph?

Suggested answer:

“Not because the model is infallible, but because the object is constrained, the ontology is frozen, and the validation is historical rather than purely anecdotal.”

### 3. Why not use citation graphs instead?

Suggested answer:

“Citation graphs tell you about influence and traffic. This graph is trying to represent claim structure and missingness.”

### 4. Why is popularity the main baseline?

Suggested answer:

“Because if research mostly follows visibility and centrality, then a degree-style baseline should be hard to beat.”

### 5. Why separate path-to-direct and direct-to-path?

Suggested answer:

“Because they capture different forms of scientific progress, and collapsing them would blur an important asymmetry in the historical record.”

### 6. What is the strongest substantive finding?

Suggested answer:

“That economics more often thickens mechanisms around accepted claims than closes missing direct links that the local literature already seems to imply.”

### 7. Is this useful for junior researchers?

Suggested answer:

“Potentially yes. In fact, one motivation is to make local reading and question screening more inspectable when you do not already know the whole field well.”

### 8. Is this replacing literature review?

Suggested answer:

“No. It is a way to structure and prioritize literature review.”

### 9. Could the method generalize beyond economics?

Suggested answer:

“I think so, but I would rather establish it carefully in one field than claim too much too early.”

### 10. What should a skeptic take from this?

Suggested answer:

“Even if you do not want a question-ranking system, the historical asymmetry between mechanism thickening and direct closure is already an interesting result about the field.”


## If you want a shorter 8-minute version

- Spend less time on the ontology slide.
- Compress slides 5 and 6 into one explanation verbally.
- Treat slide 13 as optional.
- Put most of the time on slides 7 through 12.


## If you want a more economist-facing tone live

- Say “question choice” more often than “candidate generation.”
- Say “later became part of the published literature” rather than “realized.”
- Say “screen” or “reading aid” more often than “ranking system.”
- Keep the LLM language short and matter-of-fact.

