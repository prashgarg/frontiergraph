# Paper Object Rewrite Note

Date: 2026-04-05

This note records the object-level rewrite applied to the current paper draft.

## Core shift

Old reading:

- the paper ranks **missing directed links**
- the candidate question is therefore a missing directed link

New reading:

- the paper still uses **missing directed links as retrieval anchors**
- but the surfaced question is usually a **path-rich** or **mechanism-rich** question
- the historical benchmark remains direct-link appearance because that is the clean observable event

## Old language -> new language

### Old

- "a candidate question is a missing directed link"
- "the paper predicts missing links"
- "the surfaced object is a missing link"
- "the graph asks what direct link appears next"

### New

- "a missing directed link is the retrieval anchor"
- "the historical benchmark evaluates whether that anchor later appears"
- "the surfaced research object is usually the nearby path or mechanism question suggested by that anchor"
- "the graph helps surface path-rich or mechanism-rich next questions"

## Why this shift is necessary

Three things now look clear.

1. The current ranked shortlist rarely reads best as a direct-edge object.
2. The prototype review suggests path-question framing is usually better.
3. The path-evolution evidence shows that research often develops by thickening mechanisms around existing direct claims, not only by closing a missing direct link.

So keeping direct-edge language as the main substantive object is now misleading, even if the benchmark still uses it.

## Sections that required rewriting

### Abstract

Needed change:

- from "represent plausible next questions as missing links"
- to "use missing links as retrieval anchors, then read the highest-scoring anchors as path-rich or mechanism-rich questions"

### Introduction

Needed change:

- define the difference between the computational anchor and the research object early
- give a concrete example

### Candidate-question section

Needed change:

- explicitly separate:
  - retrieval anchor
  - surfaced question
- show side-by-side examples

### Results section

Needed change:

- remind the reader that the benchmark is on anchors
- interpret current shortlist objects in path/mechanism language

### Conclusion

Needed change:

- stop closing with language that implies the paper is mainly about direct-edge prediction

## Applied examples

### Example 1

Direct-edge anchor:

- `Income tax rate -> CO2 emissions`

Path-rich reading:

- `Through which nearby pathways might income tax rate shape CO2 emissions?`

Mechanism-rich reading:

- `Which nearby mechanisms most plausibly link income tax rate to CO2 emissions?`

### Example 2

Direct-edge anchor:

- `Financial development -> green innovation`

Path-rich reading:

- `Through which nearby pathways might financial development shape green innovation?`

Mechanism-rich reading:

- `Which nearby mechanisms most plausibly link financial development to green innovation?`

### Example 3

Direct-edge anchor:

- `Environmental pollution -> carbon emissions`

Path-rich reading:

- `Through which nearby pathways might environmental pollution shape carbon emissions?`

Mechanism-rich reading:

- `Which nearby mechanisms most plausibly link environmental pollution to carbon emissions?`

## What this rewrite does not change

- the historical benchmark target
- the rolling-cutoff design
- the transparent score
- the claim that preferential attachment is the main null

So the empirical comparison stays clean. The rewrite changes the paper's **interpretation and surfaced object**, not the benchmark event.
