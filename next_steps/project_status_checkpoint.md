# Project Status Checkpoint

## Where we are now

The project is no longer bottlenecked by ontology expansion or draft structure.

The current state is:

- the empirical hierarchy is locked
- the ontology-vNext layer is frozen except for future reviewed override tables
- the routed shortlist is stable
- the paper has now been rewritten around the benchmark/object/overlay hierarchy in both Markdown and TeX
- the TeX manuscript compiles again with the new example discipline and appendix framing
- the next underlying bottleneck is now benchmark positioning and validation rather than ontology or draft structure

This is still a much better place to be than earlier phases. But the latest empirical pass changed what the main open problem is.

## What now feels settled

### 1. The benchmark target and surfaced object are different

This is now a stable project decision.

- benchmark target: later appearance of a missing directed link
- surfaced object: a path-rich or mechanism-rich research question

The paper and the internal notes now treat that distinction consistently.

### 2. The main historical comparison should stay simple

The core benchmark is now locked as:

- graph-based score
- versus preferential-attachment-style benchmark

That comparison is simple, symmetric, and interpretable.

But the latest benchmark-expansion pass now shows that the current transparent graph score does **not** beat stronger transparent baselines such as:

- degree + recency
- directed closure

The follow-up benchmark-strategy pass shows that the **best learned reranker does** beat those stronger baselines on the main top-`K` screening metrics.

So the comparison is still the right structure for the paper.
What changed is the identity of the graph-based winner:

- not the transparent graph score
- but the learned reranker built on the same graph candidate universe

### 3. Routed overlays are extensions, not the main object

The project now has good examples of:

- context-transfer
- evidence-type expansion

But they belong after the baseline surfaced object is clear.

### 4. Ontology-vNext is now support infrastructure

Ontology-vNext now provides:

- reviewed design-family overrides
- reviewed policy semantics and guardrails
- reviewed residual relation semantics
- family-aware comparison as an extension object

That layer is useful and now stable enough to freeze.

### 5. A dedicated substantive frontier-object family is not warranted yet

Once the reviewed edge typing landed, the earlier strong-substantive queue mostly disappeared. That means it was mainly an internal edge-typing problem rather than a stable new surfaced object family.

### 6. The main remaining shortlist problem is redundancy, not wording

The display-layer rewrite fixed the recurring awkward path phrasing issue. The shortlist is now good enough to curate from. The next paper-facing improvement is semantic crowding control, not another broad renderer rewrite.

## What now looks less central

These are no longer the highest-value moves:

- broader ontology growth
- new family promotion
- ranking changes
- routed-selection changes
- more extraction prompt tuning

Those may return later, but they are not the current bottleneck.

## Current stable stack

The working stack is now:

1. frozen canonical ontology
2. transparent retrieval score
3. historical benchmark against preferential attachment
4. surfaced endpoint-quality control
5. path/mechanism question rendering
6. routed overlays for context transfer and evidence-type expansion
7. family-aware comparison as an extension object
8. internal semantic support from reviewed edge typing and ontology-vNext

That is now a coherent layered system rather than an exploratory collection of patches.

## Latest paper-facing update

The latest major pass completed the TeX-first hardening pass.

What changed:

- `paper/research_allocation_paper.tex` now matches the locked hierarchy used in the rewritten Markdown draft
- the abstract and introduction now define the benchmark anchor and surfaced object separately and early
- the benchmark comparison remains graph-based score versus preferential attachment
- routed overlays appear only after the baseline surfaced object is established
- the main-text examples are locked to the curated four-example set
- the appendix now carries a reserve-example table instead of another crowded headline example cluster
- the credibility appendix is self-contained
- the manuscript compiles successfully again

So the paper is now in manuscript-hardening mode rather than structure-discovery mode, and the remaining work is circulation-specific polish rather than conceptual restructuring.

## Latest underlying-method update

The latest underlying-method pass completed:

- stronger transparent benchmark expansion
- benchmark-strategy review for the best learned reranker
- object-ablation review
- redundancy audit
- routed-overlay validation
- a prepared next-day human-validation pack

The most important results are now:

1. the transparent graph score is not strong enough against stronger transparent baselines
2. the best learned reranker **does** rescue the benchmark story on the main top-`K` metrics

Specifically:

- the transparent `graph_score` loses to `degree_recency`, `pref_attach`, and `directed_closure`
- the best learned reranker beats all of those on `precision@100` and `recall@100`
- at `h=10`, it also beats them on `MRR`
- at `h=5`, it still trails the strongest transparent baselines on `MRR`

That means the benchmark layer is no longer simply broken.
It is now:

- partially rescued, but only if the paper is explicit that the winning graph benchmark is the learned reranker rather than the transparent score

The other passes still clarified useful things:

- the path/mechanism layer does the main surfaced-object work
- routed overlays remain selective but useful extensions
- redundancy is the main remaining shortlist-quality issue
- a light diversification rule improves top-slice coverage without touching the frozen ranking stack

## Recommended next major steps

### 1. Reframe the benchmark claim in the paper

The next substantive move should be:

- keep the benchmark family expanded
- move the comparative win claim to the learned reranker
- present the transparent graph score as the interpretable retrieval layer, not the benchmark winner

### 2. Validate the rescued benchmark position

After the benchmark claim is reframed, the next empirical gains are:

- test whether diversification can preserve quality while broadening idea coverage
- run the prepared human-validation pack
- decide whether routed overlays deserve a stronger role based on structured validation

### 3. Only then return to circulation-facing polish

Once the benchmark position is settled, the remaining paper work should be:

- appendix/main-text balance
- final title and abstract tightening
- referee-facing positioning decisions
- deciding which extension material belongs in the main text versus appendix for circulation

## Bottom line

The big conceptual questions about the paper's **object hierarchy** are now mostly answered.

The project has:

- a clean empirical object
- a benchmark layer that is now much more honestly stress-tested
- a usable surfaced question layer
- a frozen internal semantic support layer

The biggest remaining gains are now in **real screening validation and then circulation-facing paper polish**.

## Most recent follow-up

The next underlying pass added three things that matter:

1. a historical diversification backtest on the best learned reranker
2. blinded human-rating materials for the prepared validation pack
3. a manuscript benchmark rewrite so the paper no longer overstates what the transparent score does

The new diversification result is useful and disciplined:

- at `h=5`, a light top-window diversification layer improves both quality and coverage:
  - precision@100 rises from `0.204` to `0.218`
  - recall@100 rises from `0.063834` to `0.067098`
  - MRR rises slightly from `0.006543` to `0.006583`
  - top-50 theme-pair coverage rises by `4.2`
- at `h=10`, diversification still broadens coverage but now at a modest quality cost:
  - precision@100 falls from `0.392` to `0.372`
  - recall@100 falls from `0.060556` to `0.057587`
  - MRR falls slightly from `0.006457` to `0.006366`
  - top-50 theme-pair coverage still rises by `4.6`

So diversification is now best understood as:

- a light screening extension
- promising enough to keep
- not part of the benchmark winner itself

The stronger benchmark claim is now:

- transparent graph score = readable retrieval layer
- learned reranker = strongest graph-based benchmark
- diversification = optional post-ranking coverage layer

The human-validation side is now ready operationally:

- the `24`-row pack has been randomized and blinded
- a clean rating sheet exists
- a separate answer key exists
- written instructions are now in place

That means the next missing evidence is no longer preparation. It is actual human ratings.
