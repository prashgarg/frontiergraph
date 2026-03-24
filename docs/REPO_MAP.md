# Frontier Graph repository map

This is the quickest way to understand what lives where.

## Core public surfaces

- `site/`: Astro website for the public browsing surface
- `app/`: deprecated Streamlit app kept in-repo for archival and possible later revival
- `paper/`: manuscript sources
- `scripts/`: release/export/build helpers
- `src/`: ranking logic, data access, adapters, and CLI entrypoints

## Data and outputs

- `data/demo/`: lightweight demo data kept in Git
- `site/public/downloads/`: public release companion files bundled with the website
- `site/src/generated/`: generated site data and paper assets used by the website

## Research and analysis code

- `src/analysis/`: analysis code used for research and evaluation; some of this is exploratory rather than a stable public API

## Deployment and configuration

- `deploy/`: deployment notes and example environment files
- `config/`: pipeline configuration files
- `Dockerfile`: container build for the deprecated app if it is ever revived

## What to treat as the stable public surface

If you are new to the repo, start with:

1. `README.md`
2. `site/`
3. `scripts/export_site_data_v2.py`
4. `scripts/export_site_data_v2.py`
5. `paper/`

Those paths correspond most closely to the public product and release workflow. Reach for `app/` only if you want to inspect the archived Streamlit workflow.
