# Frontier Graph

Frontier Graph is an open-source research tool for browsing suggested questions in economics from a literature graph.

- Website: [frontiergraph.com](https://frontiergraph.com)
- Explorer: [frontiergraph.com/explorer/](https://frontiergraph.com/explorer/)
- Working paper: [frontiergraph.com/paper/](https://frontiergraph.com/paper/)
- Downloads: [frontiergraph.com/downloads/](https://frontiergraph.com/downloads/)
- Repository: [github.com/prashgarg/frontiergraph](https://github.com/prashgarg/frontiergraph)

> Public beta. This repository powers the public website, the Explorer, the release bundle, and the working paper. The maintained public surfaces are `site/`, `app/`, and the release/export pipeline. Some analysis scripts remain exploratory research code rather than stable public APIs.

## What Frontier Graph does

Frontier Graph surfaces plausible next questions from missing links in an economics-facing literature graph, then lets you inspect the nearby topics, supporting paths, and starter papers behind each suggestion.

This repository contains:

- the public Astro website in `site/`
- the Streamlit Explorer in `app/`
- the ranking and data logic in `src/`
- release and export scripts in `scripts/`
- the paper sources in `paper/`
- a small demo dataset in `data/demo/`

## Quickstart

### Install the Python package

```bash
python -m pip install -e '.[dev]'
```

This installs the `frontiergraph` CLI. The legacy `economics-ranker` alias still works.

### Run the website locally

```bash
npm --prefix site install
npm --prefix site run dev
```

### Run the Explorer locally

If you already have the public SQLite bundle in `data/production/frontiergraph_public_release/frontiergraph-economics-public.db`, this is enough:

```bash
frontiergraph --headless
```

Or point the app at an explicit database path:

```bash
frontiergraph --db /path/to/frontiergraph-economics-public.db --headless
```

## Public release workflow

The public website and the Explorer share one canonical public release bundle. A typical refresh sequence is:

```bash
PYTHONPATH=. python scripts/export_site_data_v2.py
python scripts/build_frontiergraph_public_release_bundle.py
PYTHONPATH=. python scripts/export_site_data_v2.py
```

This updates the generated site data, paper assets, and public download metadata.

If you want the website to point at a live public database mirror and branded Explorer handoff, set:

```bash
export FRONTIERGRAPH_PUBLIC_DB_URL="https://..."
export FRONTIERGRAPH_PUBLIC_APP_URL="https://frontiergraph.com/explorer/"
```

before running the export.

## Reproducibility and scope

Frontier Graph is a research codebase, not a polished library package. The public repository is intended to make the method, release pipeline, website, Explorer, and paper inspectable.

- The public site and Explorer can be reproduced from this repo plus the public release bundle.
- The demo path is reproducible from the repo alone.
- Full economics rebuilds depend on external corpora, API access, and deployment infrastructure that are not all bundled into Git.

See [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for the full breakdown and [docs/REPO_MAP.md](docs/REPO_MAP.md) for a guide to the repo layout.

## Contribution model

Issues are welcome. Small pull requests are welcome too, especially for bugs, docs, or usability fixes. For larger changes, please open an issue first so we can agree on the shape before code is written.

See:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [SUPPORT.md](SUPPORT.md)

## Data, paper, and citation

- Data packaging: [DATA_README.md](DATA_README.md)
- Data provenance: [DATA_PROVENANCE.md](DATA_PROVENANCE.md)
- Deployment notes: [deploy/PUBLIC_RELEASE.md](deploy/PUBLIC_RELEASE.md)
- Citation: [CITATION.cff](CITATION.cff)
- License: [LICENSE](LICENSE)
