# FrontierGraph data packages

FrontierGraph exposes two data layers:

## 1. Demo data

The demo data is kept in-repo under `data/demo/`.

It is intended for:

- local quickstarts,
- smoke tests,
- understanding the end-to-end pipeline without the full economics build.

## 2. Full beta economics database

The public beta database is distributed as a versioned SQLite artifact outside the Git repository.

Repository companion files:

- `site/public/downloads/frontiergraph-economics-beta.manifest.json`
- `site/public/downloads/frontiergraph-economics-beta.sha256.txt`

The downloads page reads a configured public mirror URL via `FRONTIERGRAPH_PUBLIC_DB_URL`.

## Intended use

The beta database is intended for:

- reproducing the public beta website and app views,
- offline exploration of ranked opportunities,
- methodological inspection of the public economics beta.

It is not presented as a final canonical research dataset. Treat it as a versioned public beta artifact.
