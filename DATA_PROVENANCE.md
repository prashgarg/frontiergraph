# FrontierGraph data provenance

## Demo data

The demo dataset in `data/demo/` is a lightweight packaged example for local runs and tests.

## Full economics beta database

The full public beta SQLite database is built from the repository pipeline over the economics claim graph build used for the current public beta.

The repository publishes:

- a versioned manifest,
- a SHA-256 checksum,
- the static site discovery exports generated from the same SQLite build.

## Packaging notes

- the SQLite artifact is intentionally kept out of Git because of size
- the public website and static discovery pages are generated from the SQLite beta build
- the public app reads the same SQLite build through a mounted cloud object

## Current release posture

This is a beta research artifact intended to support transparency and reproducibility for the public FrontierGraph beta. It should not be treated as a final archival release.
