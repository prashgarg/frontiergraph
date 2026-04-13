# Field Shelf Cleanup And Paper-Worthiness Audit

This note records the non-LLM cleanup pass on the current objective-specific frontier packages.

What we are trying to answer:

- Do the within-field shelves read like real subfield browse objects, or like leftover global ranking?
- Is `other` genuinely large, or only mechanically large because of package construction?
- What are the main remaining paper-worthiness failure modes without using an LLM?

Key current diagnostics to preserve:

- The within-field package is a real shelf object, but it duplicates some candidates across shelves by design.
- `Other` is mechanically fixed in the current package builder because each horizon takes `100` rows for each of the six shelves.
- The current shortlist problem is not mainly wild fully-open gaps. It is broad anchored progression with weak endpoint-plus-mediator compression.

The audit should therefore report:

1. Field support source
- endpoint-only matches
- mediator-only matches
- both
- none

2. Other-bucket patterns
- top repeated sources, targets, theme pairs, and semantic families inside `other`

3. Paper-worthiness failure modes
- anchored share
- causal-to-identified share
- high-broad share
- low-compression share
- method-like mediator share
- textbook-like share

4. Flagged examples
- rows that are broad, low-compression, method-like, or textbook-like

Interpretation rule:

- If many shelf assignments are mediator-only, the shelf is too easy to distort through mechanism text.
- If broad and low-compression shares stay high, the next cleanup pass should stay focused on screening and generator framing rather than more reranker tuning.

Recommended near-term direction:

- move toward endpoint-first field assignment
- keep mediator text as secondary support rather than the main field trigger
- continue non-LLM paper-worthiness cleanup before any live LLM scoring pass
