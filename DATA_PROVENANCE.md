# Frontier Graph data provenance

## Demo data

The demo dataset in `data/demo/` is a lightweight packaged example for local runs and tests.

## Full public economics database

The public SQLite database is built from the repository pipeline over the economics claim-graph build used for the current public release.

The repository publishes:

- a versioned manifest
- a SHA-256 checksum
- the static discovery exports generated from the same SQLite build

## Packaging notes

- the SQLite artifact stays out of Git because of size
- the public website and discovery pages are generated from the same release bundle
- the Explorer reads that same bundle through a mounted or mirrored public object

## Current release posture

This is a public beta research artifact intended to support transparency and partial reproducibility for the current Frontier Graph release. It should not be treated as a final archival dataset.
