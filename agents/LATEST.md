# Latest

## As of 2026-04-14

## Stable Public Line
- Branch: `main`
- Public site: [frontiergraph.com](https://frontiergraph.com)
- Main public routes:
  - `/`
  - `/paper/`
  - `/downloads/`
  - `/questions/`
  - `/graph/`

## What Is Current
- The website refresh is merged to `main`.
- The working paper is frozen on `main` and synced to the website download.
- The seminar Beamer deck is the canonical slide deck on `main`.
- Downloads now expose:
  - Tier 1 lightweight exports
  - Tier 2 split structured bundles
  - Tier 3 live SQLite bundle

## Canonical Files
- Paper source:
  - [paper/research_allocation_paper.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.tex)
- Paper PDF:
  - [paper/research_allocation_paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/research_allocation_paper.pdf)
- Website paper download:
  - [site/public/downloads/frontiergraph-working-paper.pdf](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-working-paper.pdf)
- Canonical seminar deck:
  - [paper/slides_ml_econ_short_beamer.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer.tex)
- Canonical slide script:
  - [paper/slides_ml_econ_short_beamer_script.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/slides_ml_econ_short_beamer_script.md)

## Downloads State
- Tier 3 SQLite bundle is live at:
  - [frontiergraph-economics-public-2026-04-13.db](https://storage.googleapis.com/frontiergraph-public-downloads-1058669339361/frontiergraph-economics-public-2026-04-13.db)
- Current manifest:
  - [site/public/downloads/frontiergraph-economics-public.manifest.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/site/public/downloads/frontiergraph-economics-public.manifest.json)

## Branch Policy
- `main`: stable public line
- `v3_paper`: next research cycle
- `codex-post-seminar-cleanup-2026-04-13`: archive only

## Current Method Decision
- Treat the ontology in the current paper as the canonical paper-facing baseline.
- Use the `v2.3` frozen baseline for the next rebuild.
- Do not reopen grounding thresholds unless a concrete failure appears.
- Keep unmatched tail labels unresolved by default.
- Do not add more hierarchy promotions unless a concrete ontology error is found.

## Immediate Next Work
- Future research should begin on `v3_paper`, not `main`.
- The first likely `v3_paper` packages are:
  - path-length axis work (`max_path_len = 3, 4, 5`)
  - paired-family refresh after the path-length choice
  - context-extension work
- `main` should only get maintenance fixes, not exploratory method growth.

## Avoid These Mistakes
- Do not use old release branches; they were deleted.
- Do not use retired artifacts such as the old markdown paper or the old slide deck.
- Do not merge `codex-post-seminar-cleanup-2026-04-13` wholesale.
