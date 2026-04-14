# Full Handoff 2026-04-14

This is the current seamless handoff for a fresh Codex thread.

## Executive Summary
FrontierGraph is no longer in the middle of a public-site rescue. That work is done. `main` now contains the stable public line: current website, current working paper, current seminar Beamer deck, and current downloads including live Tier 3 SQLite. The next real work should happen on `v3_paper`, not on `main`.

## Current Branch Policy
- `main`
  - stable public line
  - use for maintenance only
- `v3_paper`
  - active future research branch
  - use for the next paper cycle
- `codex-post-seminar-cleanup-2026-04-13`
  - archive branch
  - keep unchanged unless you need to rescue something specific

## What Was Finished Recently
- refreshed the public site and merged it to `main`
- froze the current working paper and synced it to the website
- froze the current seminar Beamer deck on `main`
- refreshed public downloads
- published live Tier 3 SQLite bundle
- cleaned branch inventory down to `main`, `v3_paper`, and one archive branch

## Canonical Artifacts On `main`

### Paper
- source:
  - [paper/research_allocation_paper.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex)
- PDF:
  - [paper/research_allocation_paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.pdf)
- website download:
  - [site/public/downloads/frontiergraph-working-paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-working-paper.pdf)

### Slides
- canonical Beamer deck:
  - [paper/slides_ml_econ_short_beamer.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer.tex)
- canonical speaker script:
  - [paper/slides_ml_econ_short_beamer_script.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer_script.md)

### Website
- Astro site root:
  - [site](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site)
- main public pages:
  - `/`
  - `/paper/`
  - `/downloads/`
  - `/questions/`
  - `/graph/`

### Public Downloads
- Tier 3 SQLite bundle:
  - [frontiergraph-economics-public-2026-04-13.db](https://storage.googleapis.com/frontiergraph-public-downloads-1058669339361/frontiergraph-economics-public-2026-04-13.db)
- manifest:
  - [site/public/downloads/frontiergraph-economics-public.manifest.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-economics-public.manifest.json)

## Directory Structure That Matters
- [agents](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents)
  - handoff pack
- [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper)
  - canonical paper and canonical seminar deck
- [site](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site)
  - live public website
- [scripts](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts)
  - build/export/release/analysis scripts
- [src](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src)
  - core Python analysis code
- [data/ontology_v2](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/ontology_v2)
  - ontology notes, reviews, and manifests
- [next_steps](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps)
  - working notes and future ideas

## Current Method Decision
Treat this as settled unless a concrete failure appears:
- the ontology in the current paper is the canonical paper-facing baseline
- use the `v2.3` frozen baseline for the next rebuild
- do not reopen grounding thresholds unless a concrete failure mode appears
- keep unmatched tail labels unresolved by default
- do not add more hierarchy promotions unless there is a concrete ontology error

## Workstream Status

### Paper Workstream
- current state: frozen working draft on `main`
- current role: reference baseline, not current bottleneck

### Website Workstream
- current state: live and current on `main`
- current role: maintenance only unless a bug appears

### Slides Workstream
- current state: current seminar deck is canonical on `main`
- current role: no urgent work unless a new presentation requires changes

### Ontology / Method Workstream
- current state: baseline decision taken, broader v2/v3 development deferred
- current role: feed the next paper cycle on `v3_paper`

### Future Research Workstream
- current branch: `v3_paper`
- likely first packages:
  - path-length axis work (`max_path_len = 3, 4, 5`)
  - paired-family refresh after the path-length choice
  - context-extension work
  - broader off-paper extensions from `next_steps`

## What Was Intentionally Deferred
- wholesale merge of `codex-post-seminar-cleanup-2026-04-13`
- large mixed v2 pipeline expansion onto `main`
- broader future-paper ideas on `main`

## What To Avoid
- do not reopen deleted release branches
- do not use retired artifacts like the old markdown paper or old slide deck
- do not treat the archive branch as the next working branch
- do not grow `main` with exploratory research work

## Recommended Resume Sequence For A New Agent
1. read [LATEST.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents/LATEST.md)
2. read this file
3. confirm whether the task is maintenance or future research
4. if maintenance, stay on `main`
5. if future research, switch to `v3_paper`
6. state the first concrete package before editing anything
