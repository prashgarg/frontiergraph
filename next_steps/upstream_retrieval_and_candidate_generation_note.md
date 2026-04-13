# Upstream Retrieval, Candidate Generation, and Evaluation Budget Note

Date: 2026-04-10

## Why this note exists

The recent method work has improved reranking and shortlist surfacing, but many of the
remaining weaknesses now look upstream:

- some candidate objects are weakly framed before ranking ever sees them
- the transparent retrieval score still determines which candidates are even eligible for
  reranking
- evaluation is still summarized too heavily by `Recall@100`, even though practical use
  will often be field- or topic-specific

This note clarifies the current design and records the next upstream improvement agenda.

## 1. Intuitive meaning of the current feature families

The current reranker families are nested. That matters.

- `structural`
  - paper-facing name: `local_structure`
  - intuition:
    - does the candidate sit in a plausible local graph neighborhood?
    - are there supporting paths, motifs, mediators, and useful degree patterns nearby?
  - this is the most graph-native family

- `composition`
  - paper-facing name: `historical_composition`
  - intuition:
    - not just whether a neighborhood exists, but what kind of literature supports it
    - is support stable or noisy?
    - does it come from varied evidence types, venues, and sources, or from one narrow pocket?
    - are the endpoints embedded in active, reusable parts of the corpus?
  - this adds “who supports the neighborhood and how” on top of local structure

- `quality`
  - recommended paper-facing rename: `candidate_sharpness`
  - intuition:
    - does this look like a sharp question rather than a broad or generic one?
    - are the endpoints broad containers or reasonably specific objects?
    - is the mediator informative or catch-all?
    - are these concepts old, established, and diffuse, or younger and more discriminating?
  - this adds broadness, resolution, specificity, and age
  - `quality` is a workable code name, but it is too loaded for the paper; `candidate_sharpness`
    or `question_sharpness` is better

- `boundary_gap`
  - paper-facing name: `frontier_boundary`
  - intuition:
    - is this candidate sitting near a real frontier or boundary in the graph?
    - does it bridge groups, show gap-like structure, or sit in a sparse closure neighborhood?
  - this adds a stronger “frontier geometry” read on top of `candidate_sharpness`

- `family_aware_*`
  - paper-facing name: `family_conditioned`
  - intuition:
    - do not treat all candidates as the same object
    - let the model know whether this is:
      - fully open
      - contextual progression
      - ordered-to-causal progression
      - causal-to-identified anchoring
      - or direct-to-path thickening
  - this lets the model assign different weights to different families or subfamilies

## 2. Why horizon-specific winners do not imply binary feature switching

The winning model differs by horizon, but this should not be read as:

- a feature matters at `h=5`
- and then suddenly stops mattering at `h=10`

That would be too strong.

Three clarifications matter:

1. The families are nested.

- `candidate_sharpness` contains `historical_composition`, which contains `local_structure`
- `frontier_boundary` contains `candidate_sharpness`, which contains `historical_composition`,
  which contains `local_structure`

So when `frontier_boundary` wins, it is not dropping structural or composition signals.
It is keeping them and adding more.

2. The model class also changes.

- `glm_logit` learns an absolute score for each candidate
- `pairwise_logit` learns relative ordering between candidates

So a horizon-specific winner partly reflects the loss function and ranking problem, not
just the raw feature set.

3. The historical target changes with horizon.

- `h=5` is a near-term next-step event
- `h=10` is a medium-run development event
- `h=15` is a longer-run realization event

That changes class balance, candidate ambiguity, and how much broadness versus frontier
structure should matter.

The right interpretation is:

- different horizons put different weights on overlapping signal families
- not that the underlying reasoning turns on and off in a binary way

## 3. How the current retrieval-reranking stack works

The current stack is a standard retrieval-then-rerank design.

1. Candidate generation proposes possible questions.
2. The transparent score retrieves the top pool.
3. The learned reranker reorders that retrieved pool.
4. Concentration control reduces overexposure.
5. The surface layer reshapes the visible shortlist.

This design choice is motivated by search and recommender systems:

- large systems often separate candidate generation from ranking
- retrieval is fast and broad
- reranking is slower and more discriminating

Relevant literatures to cite or lean on:

- two-stage retrieval/ranking in recommender systems and web-scale recommendation
  - e.g. Covington, Adams, and Sargin (2016), YouTube candidate generation and ranking
- learning-to-rank
  - pointwise, pairwise, and listwise ranking
  - e.g. Burges (2005), Qin, Liu, and Li (2007), Burges (2010)
- beyond-accuracy recommender evaluation
  - diversity, novelty, coverage, serendipity
  - e.g. Castells, Hurley, and Vargas (2015); Adomavicius and Kwon (2012); Kotkov et al.

What is portable here:

- retrieval versus reranking as separate jobs
- limited top-pool reranking for tractability
- post-ranking diversification or exposure control

What is not portable directly:

- user-personalization assumptions
- click-through objectives
- relevance labels tied to user behavior

Our problem is not user personalization. It is literature-opportunity screening.

## 4. Why reranking only the top pool is both sensible and risky

The reranker currently only sees the top retrieved pool, such as `5000`.

Why this is sensible:

- computation is manageable
- the reranker does not waste capacity sorting obvious low-quality tail items
- this follows standard retrieval/rerank practice

Why this is risky:

- if retrieval misses good candidates, reranking cannot recover them
- weak retrieval can cap the entire system

So the reranker is only as good as the candidate pool it inherits.

That is why upstream work now matters so much.

## 5. Candidate generation is likely the biggest remaining bottleneck

### What candidate generation controls

Candidate generation decides what questions even exist downstream.

If the object is weakly framed here, later ranking can only partially help.

### What likely needs improvement

- stronger family assignment
  - fewer awkward or overly broad cross-family cases
- better gating of broad `path_to_direct` cases
  - especially broad anchored progression pairs
- richer local evidence objects
  - better path bundles, topology bundles, and provenance
- better endpoint-plus-mediator compression
  - more candidates should be expressed as sharp mechanism questions rather than raw broad pairs
- later:
  - dormant-node / node-activation extensions

### Success criteria

Candidate-generation improvements should be judged by:

- higher positive rate in the candidate universe
- higher future-positive recall at the same retrieval budget
- better family consistency
- fewer placeholder or obviously generic surfaced candidates
- better human ratings on paper-likeness and specificity
- better field/topic coverage without exploding noise

### Expected gains

The main likely gain is not a tiny MRR improvement. It is:

- better semantic quality of the candidate universe
- fewer obviously weak candidates entering the reranker pool
- a more defensible surfaced shortlist

This is why candidate generation may now be higher leverage than another small reranker tweak.

### Literature to motivate this

Three literatures are useful here:

- retrieval and candidate-generation in recommender systems
  - because this is exactly the “what even gets considered?” layer
- link prediction / scientific-discovery / knowledge-graph completion
  - because our object is still a graph-screened scientific opportunity
- economics-facing framing
  - because papers are not arbitrary motifs; they are readable question objects

## 6. Transparent score improvements matter because retrieval defines the pool

The transparent score is the retrieval score.

Its job is not to be the best final model. Its job is to:

- screen a large candidate universe
- preserve likely positives
- stay interpretable

### Likely next improvements

- better weighting of support vs opportunity vs resolution
- subfamily-specific score formulas
- better genericity penalties
- better use of motif/topology evidence
- possibly family-aware retrieval rather than one blended score

### Success criteria

- better recall at retrieval budgets such as `500`, `2000`, `5000`, `10000`
- higher positive rates inside the retrieved pool
- better downstream reranker performance at fixed pool size
- clearer score decomposition for surfaced items

### Expected gains

Transparent-score improvements are likely to matter more for:

- retrieval recall
- pool purity
- computational efficiency

than for final top-rank aesthetics by themselves.

## 7. The paper should preempt the pool-size question

The current answer is:

- we use a top-pool retrieval step, then rerank within that pool
- pool size is tuned as part of the ranking-system design
- the goal is to preserve enough recall while keeping reranking tractable

This should be stated directly in the paper methods when the next methods-text pass happens.

That paper text should also say:

- the pool size is an empirical design parameter, not a scientific constant
- the reranker evaluates only retrieved candidates
- therefore retrieval quality and reranking quality are distinct objects

## 8. `Recall@100` is useful, but it should not be the only budget

`Recall@100` is practical because shortlists are finite, but it is not enough.

The immediate problem is obvious:

- `100` total items is not much once we break results down by field or topic
- a finance scholar may care about the top `100` finance questions, not the top `100` overall

### What to add next

- recall curves over multiple `K`
  - at least `20, 50, 100, 250, 500`
- score-gap diagnostics
  - to see whether top ranks are steep or flat
- plateau diagnostics
  - to detect whether many top items are effectively tied
- field-conditioned evaluation
  - top `K` within broad field buckets
- macro-averaged field coverage
  - so one overactive area does not dominate the whole picture

### Field/topic structure

We should move toward a broad field layer with perhaps `10–20` top-level buckets, such as:

- macro
- finance
- labor
- development
- trade
- IO
- public
- environment/energy
- health
- education
- methods
- plus `other`

This does not need to replace the ontology. It can be an evaluation and surfacing layer
on top of the existing semi-hierarchical ontology.

### Success criteria for multi-budget evaluation

- the system should look good not only at overall `Recall@100`
- it should also preserve useful depth within broad fields
- and it should not let `other` absorb most concepts

## 9. What to call `quality` in the paper

`quality` is too broad and normatively loaded.

Recommended paper-facing rename:

- `candidate_sharpness`

Possible alternatives:

- `question_sharpness`
- `semantic_sharpness`
- `specificity_and_resolution`

My preference is `candidate_sharpness`, because it describes:

- broadness
- resolution
- mediator specificity
- age

without pretending that the system directly measures scientific merit.

## 10. Recommended next implementation order

1. Candidate-generation pass
   - tighten family assignment
   - improve endpoint-plus-mediator compression
   - gate broad anchored `path_to_direct` cases better
2. Transparent retrieval pass
   - run a retrieval-budget study over `K = 500, 2000, 5000, 10000`
   - compare recall and positive-rate tradeoffs
3. Evaluation-budget pass
   - add multi-`K` curves and field-conditioned top-`K`
4. Only then decide how large an LLM paper-worthiness layer should be
   - top `500`
   - top `2000`
   - or the full current `5000` per horizon

## Bottom line

The current method has moved past “can the graph retrieve plausible opportunities?” and is
now at “is the upstream object good enough for the ranking stack to work on?”

That is a healthier place to be. It means:

- reranking and surfacing are no longer the only bottlenecks
- candidate generation and retrieval deserve first-class attention
- and future evaluation should be more explicit about pool size, multi-`K`, and field-specific use
