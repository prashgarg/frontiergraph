# Short Talk Outline

Working title: `What Should Science Ask Next?`

Audience:
- economists
- metascience / science-of-science researchers
- computational social scientists
- ML-adjacent researchers who care about substantive scientific use, not only benchmark performance

Target length:
- `10–15` minutes
- `10–12` main slides
- `4–6` appendix slides with jump buttons

Design principles:
- graphical
- low text load
- no benchmark horse-race emphasis beyond what is needed for credibility
- every methodological slide earns its place by helping the audience interpret the substantive result
- text small, sparse, and cue-like
- no hype, no startup tone, no “AI will fix science” framing

## Main arc

### 1. Title
Purpose:
- establish the paper and tone immediately

Content:
- title
- name
- affiliation
- website
- visually strong but restrained background

Visual:
- stylized graph texture or paper-to-graph motif in the background

### 2. Motivation
Purpose:
- widen the framing from economics to science
- say why question choice is the scarce input

Talk track:
- choosing what to work on is one of the least formalized decisions in science
- the literature is large, fragmented, and hard to navigate
- AI may lower the cost of many downstream tasks, making question choice relatively more important

On-slide cues:
- `Question choice is under-formalized`
- `Knowledge burden is rising`
- `Attention is scarce`
- one line with anchor citations if useful

Likely citations:
- Jones
- Bloom et al.
- Foster, Rzhetsky, and Evans

### 3. This paper
Purpose:
- say what the paper does and what it finds before any mechanics

On-slide structure:
- left: `We build`
- middle: `We test`
- right: `We find`

Suggested bullets:
- build a dated graph from published economics-facing papers
- use it to rank still-open next questions
- test those rankings prospectively against later publication
- find that the graph helps in two distinct ways:
  - it identifies missing mechanisms around known claims
  - it identifies missing direct relations supported by local structure

### 4. Why two objects?
Purpose:
- define the empirical objects early and symmetrically

Content:
- direct-to-path
- path-to-direct
- one sentence each

Visual:
- compact two-column diagram

Key message:
- these are different forms of research progress, not mirror images

### 5. Method bridge
Purpose:
- move from idea to method without drowning the audience in pipeline detail

Content:
- papers -> paper-local graphs -> shared graph -> dated candidates -> future realization

Visual:
- one simplified bridge figure

Key message:
- use only information available at date `t-1`, then ask what later appears

### 6. Extraction and matching
Purpose:
- explain the graph object with intuition

Visuals:
- Figure 2 style paper-text-to-graph
- Figure 3 style cross-paper matching

Talking points:
- each paper becomes a local graph
- repeated concepts are matched into shared nodes
- candidate questions only exist after cross-paper matching

### 7. Benchmark idea
Purpose:
- establish credibility with the lightest possible benchmark explanation

Visual:
- Figure 5 style benchmark-anchor-versus-surfaced-question slide

Talking points:
- benchmark event is narrow and dateable
- surfaced question is richer and closer to what a reader would inspect
- this separation keeps the exercise historically testable

### 8. Main historical result
Purpose:
- one clean result slide proving the graph matters

Visual:
- paired-family main benchmark figure only

Talking points:
- graph-based screening beats popularity in both families
- richer ranking improves further
- the two families differ in what “good” means

On-slide emphasis:
- direct-to-path: more later realizations per shortlist
- path-to-direct: larger share of all later-realized links

### 9. Main substantive takeaway
Purpose:
- move from “the method works” to “what does this say about how science moves?”

Visual:
- path-evolution / family-comparison figure

Key message:
- the literature more often thickens mechanisms around existing claims than it later states locally implied direct links

This is the core short-talk substantive result.

### 10. What the graph surfaces now
Purpose:
- make the object tangible

Visual:
- curated surfaced examples, one column per family

Requirements:
- examples must read like real economics/science questions
- keep labels clean

Suggested structure:
- `Known claim, missing mechanism`
- `Local support, missing direct relation`

### 11. What changes in the view of the world?
Purpose:
- explicit interpretation slide

Possible slide title:
- `What this changes`

Talking points:
- question choice can be partly disciplined
- the graph is more useful for directing scarce reading time than for replacing judgment
- mechanism thickening appears to be a central mode of scientific progress

### 12. Conclusion
Purpose:
- close without reopening method details

On-slide cues:
- what we built
- what we learned
- what is next

Suggested “next” items:
- longer path support
- context extension
- workflow layer with LLM screening

## Appendix outline

### A1. Extra benchmark detail
- same paired benchmark figure or a compact table
- button back to Slide 8

### A2. Example methodology details
- extraction figure or normalization figure
- button back to Slide 6

### A3. Current surfaced examples
- larger example set
- button back to Slide 10

### A4. Extensions
- paired usefulness screen
- budget frontier if finished and clean
- button back to Slide 11

## Navigation rules

- every main slide that points to appendix should have a small appendix button in one consistent location
- every appendix slide should have a `Back to main` button to the relevant main slide, not only to the title slide
- the short talk should need at most `2–3` appendix jumps live

## Likely figures for short deck

Main:
1. title visual
2. two-object diagram
3. method bridge / pipeline
4. extraction or cross-paper matching
5. benchmark anchor vs surfaced question
6. paired historical result
7. family substantive comparison
8. surfaced examples

Appendix:
1. benchmark table
2. extra examples
3. robustness / usefulness / budget as available
