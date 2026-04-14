# Project State

## What FrontierGraph Is Right Now
FrontierGraph is currently two things at once:
- a stable public website and working-paper surface on `main`
- a queued next research cycle that should happen on `v3_paper`

The project is no longer in the earlier "find the product framing" phase. The public line is already live and coherent. The next work is research extension, not core cleanup.

## Branch Map
- `main`
  - stable public line
  - canonical website, paper, downloads, and seminar deck
- `v3_paper`
  - future research branch
  - intended home for context extension, path-length work, and next paper-cycle extensions
- `codex-post-seminar-cleanup-2026-04-13`
  - archive branch
  - mixed snapshot of post-seminar cleanup, notes, v2 pipeline work, and context-extension material
  - keep unchanged unless you need to rescue something from it

## Directory Map
- [agents](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/agents)
  - canonical handoff pack
- [paper](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper)
  - canonical paper and seminar deck on `main`
- [site](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site)
  - Astro public site
- [scripts](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts)
  - build, export, release, and analysis scripts
- [src](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/src)
  - core Python analysis code
- [data](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data)
  - production artifacts and ontology work
- [next_steps](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps)
  - working notes and future ideas

## Canonical Public Artifacts
- Working paper source:
  - [paper/research_allocation_paper.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex)
- Working paper PDF:
  - [paper/research_allocation_paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.pdf)
- Website paper download:
  - [site/public/downloads/frontiergraph-working-paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-working-paper.pdf)
- Seminar deck:
  - [paper/slides_ml_econ_short_beamer.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer.tex)
- Public release manifest:
  - [site/public/downloads/frontiergraph-economics-public.manifest.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-economics-public.manifest.json)

## Workstream Status

### Paper
- State: frozen working draft on `main`
- The paper is already on the public website.
- The old markdown paper artifact was retired from `main`.

### Slides
- State: seminar deck frozen on `main`
- Canonical deck is the Beamer source in `paper/`.
- The old PowerPoint-era workspace was retired from `main`.

### Website
- State: live and current on `main`
- Main public routes were refreshed and are already merged.
- Downloads now include live Tier 1, Tier 2, and Tier 3 artifacts.

### Ontology / Method
- State: current paper uses the conservative `v2.3` frozen ontology baseline.
- That is the current production-facing method decision.
- More aggressive ontology redesign remains future work, not current public work.

### Future Research
- State: should happen on `v3_paper`
- Current likely research packages:
  - path-length axis work
  - context extension
  - broader paired-family extensions
  - additional testbeds that were not in the current paper

## Recent Completed Work
- merged website refresh to `main`
- froze paper and synced site PDF
- froze seminar deck on `main`
- refreshed public downloads
- published live Tier 3 SQLite bundle
- cleaned branch inventory down to `main`, `v3_paper`, and one archive branch

## Retired / Avoid
- old release branches
- old incubation pointers
- old markdown paper artifact
- old `slides_research_allocation.*` deck files
- merging the cleanup archive branch wholesale
