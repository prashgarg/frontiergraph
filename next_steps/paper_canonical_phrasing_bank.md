# Canonical Phrasing Bank

Date: 2026-04-05

This note stores the preferred language for the current paper pass.

## One-sentence description

- "The paper uses missing directed links as retrieval anchors in a literature graph, then surfaces the resulting candidates as nearby path-rich or mechanism-rich questions."

## Abstract language

Good:

- "uses missing directed links as retrieval anchors"
- "tests the anchor ranking prospectively"
- "reads the highest-scoring anchors as path-rich or mechanism-rich questions"

Avoid:

- "represents plausible next questions as missing links"
- "predicts missing links" as the whole object

## Introduction language

Good:

- "The missing directed link is the computational anchor."
- "The surfaced research object is usually richer than that anchor."
- "A promising candidate is often better read as a path or mechanism question."

Avoid:

- "The question itself is a missing link."

## Methods language

Good:

- "historical benchmark"
- "retrieval anchor"
- "surfaced question"
- "path-rich question"
- "mechanism-rich question"
- "fixed-budget shortlist"

Avoid:

- "generic network completion"
- "the system predicts the next edge" without qualification

## Results language

Good:

- "The benchmark is evaluated on direct-link anchors because that is the clean event that later appears or does not appear."
- "The stricter top-rank benchmark favors preferential attachment."
- "The graph-based screen becomes more useful at broader shortlists and in literatures with richer local support."

Avoid:

- "the graph wins"
- "the system solves question choice"
- "the model predicts the frontier" without qualification

## Path/mechanism language

Good:

- "Through which nearby pathways might X shape Y?"
- "Which nearby mechanisms most plausibly link X to Y?"
- "path-rich or mechanism-rich question"
- "mechanism-deepening around an existing direct claim"
- "income tax rate -> CO2 emissions is better read as a path question through income inequality and environmental taxes"
- "financial development -> green innovation is better read through environmental sustainability, environmental pollution, and green growth"

Avoid:

- "research program" as the default label in main text unless needed
- "hyperedge-like" or other internal computational terms in main prose

## Limits language

Good:

- "future appearance is not the same thing as truth or importance"
- "the benchmark is narrower than a welfare theory of what economics should study"
- "the historical event is cleaner than the surfaced research object"

Avoid:

- "validation" unless it is clear what is being validated against what
