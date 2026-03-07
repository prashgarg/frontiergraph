# FrontierGraph public beta deployment

## Surfaces

- `frontiergraph.com`: Astro site on Cloudflare Pages
- beta app: Streamlit on Google Cloud Run
- beta database: SQLite mounted read-only from Google Cloud Storage

## Site deployment

Cloudflare Pages should point at the `site/` directory.

- Root directory: `site`
- Build command: `npm install && npm run build`
- Build output directory: `dist`

The static discovery layer depends on generated site data. Before deploying the site, run:

```bash
PYTHONPATH=. python scripts/export_site_data.py
```

If you want the downloads page to point at a live public database mirror:

```bash
export FRONTIERGRAPH_PUBLIC_DB_URL="https://..."
PYTHONPATH=. python scripts/export_site_data.py
```

## App deployment

The current app deploy remains Cloud Run + mounted GCS bucket.

- `Dockerfile` builds the Streamlit app image
- `src/run_ranker.py` starts the app
- `ECON_OPPORTUNITY_DB` points to the mounted SQLite file

The app expects the mounted database path:

```bash
/mnt/ranker-data/app_causalclaims.db
```

## Public data artifact

The repository now ships:

- checksum file at `site/public/downloads/frontiergraph-economics-beta.sha256.txt`
- manifest file at `site/public/downloads/frontiergraph-economics-beta.manifest.json`

The full beta DB itself should be hosted as a public GCS object or another public blob store. The site export script reads `FRONTIERGRAPH_PUBLIC_DB_URL` to wire the download link.

## Refresh workflow

The repository includes a GitHub Actions workflow:

- `.github/workflows/refresh-site-data.yml`

It is designed to:

1. download the beta database from `FRONTIERGRAPH_PUBLIC_DB_URL`,
2. regenerate site JSON/CSV artifacts,
3. commit the updated generated files.

Configure `FRONTIERGRAPH_PUBLIC_DB_URL` as a GitHub Actions secret before using the workflow.
