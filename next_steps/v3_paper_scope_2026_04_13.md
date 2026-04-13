# v3 paper branch scope

Date: 2026-04-13

Branch: `v3_paper`

## Purpose

This branch is the working home for the next paper beyond the current public
paper and seminar deck. It can carry material that is too exploratory, too
large, or too branch-specific for `main`.

## Included by design

- context extension paper and any integration path back into the main paper
- the path-length axis beyond `max_path_len = 2`
- longer-horizon paper ideas and branch-specific next-step experiments
- appendix-grade analyses that were omitted from the current paper for narrative
  discipline rather than because they were uninteresting

## Core workstreams

### 1. Path-length axis

- run and compare `max_path_len = 2, 3, 4, 5` for `path-to-direct`
- decide whether one longer support length is worth keeping
- if strong, bring back one selective comparison rather than the full axis grid

### 2. Context extension

- develop the separate context-extension paper on breadth, concentration, and
  cross-country scope
- decide what belongs as a standalone note versus what should feed back into the
  main FrontierGraph paper

### 3. Off-paper extensions that could return later

- paired-family usefulness refresh after the path-length choice is made
- paired frontier and broader reading-budget extensions
- more systematic adopter-profile and bundle-uptake writeups
- concentration diagnostics and objective-specific frontier packages
- direct-to-path readability and object-quality improvements

### 4. Next-step idea bank

- branch-specific notes and design memos
- candidate paper directions that are not yet ready for the canonical paper
- scoped experiments on concentration, diversification, and surfaced-object
  construction

## What should stay off `main` for now

- context-extension drafts and side analyses
- path-length experiments that have not been interpreted
- exploratory method notes and partial rebuilds
- branch-specific slide or packet work that is not part of the canonical public
  deck

## Merge standard back to `main`

Bring work back to `main` only when it is one of:

- a stable paper revision
- a stable website-facing asset or manuscript sync
- a clearly decided methodological change
- a finished appendix or extension that is no longer exploratory

## Current candidate items for this branch

- context extension paper materials
- path-length axis execution and comparison
- paired-family usefulness refresh after path-length selection
- broader reading-budget and paired-frontier extensions
- concentration and diversification follow-ons
- author-awareness / adopter-profile formalization
- branch notes in `next_steps/` that are not ready to become canonical claims
