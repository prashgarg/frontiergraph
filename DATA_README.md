# Frontier Graph data packages

Frontier Graph exposes two public data layers.

## 1. Demo data

The demo data lives in-repo under `data/demo/`.

Use it for:

- local quickstarts
- smoke tests
- understanding the end-to-end pipeline without the full economics build

## 2. Public economics release bundle

The full public economics database is distributed as a versioned SQLite artifact outside Git.

Repository companion files:

- `site/public/downloads/frontiergraph-economics-public.manifest.json`
- `site/public/downloads/frontiergraph-economics-public.sha256.txt`

The public downloads page reads a configured mirror URL via `FRONTIERGRAPH_PUBLIC_DB_URL`.

## Intended use

The public release bundle is intended for:

- reproducing the public website and Explorer views
- offline exploration of surfaced questions and local evidence tables
- methodological inspection of the current public release

It is a versioned public research artifact, not a final archival dataset.
