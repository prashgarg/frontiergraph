# FrontierGraph public release deployment

## Surfaces

- `frontiergraph.com`: Astro site on Cloudflare Pages
- `https://frontiergraph-app-1058669339361.us-central1.run.app`: Streamlit app on Google Cloud Run
- public database mirror: SQLite hosted from Google Cloud Storage

## Site deployment

Cloudflare Pages should point at the `site/` directory.

- Root directory: `site`
- Build command: `npm install && npm run build`
- Build output directory: `dist`

The static discovery layer depends on generated site data. Before deploying the site, run:

```bash
PYTHONPATH=. python scripts/export_site_data_v2.py
python scripts/build_frontiergraph_public_release_bundle.py
PYTHONPATH=. python scripts/export_site_data_v2.py
```

If you want the downloads page to point at a live public database mirror:

```bash
export FRONTIERGRAPH_PUBLIC_DB_URL="https://..."
PYTHONPATH=. python scripts/export_site_data_v2.py
```

## App deployment

The public deeper app deploys to Cloud Run and should read the canonical public bundle.

- `Dockerfile` builds the Streamlit app image
- `src/run_ranker.py` starts the app
- `ECON_OPPORTUNITY_DB` should point to the mounted `frontiergraph-economics-public.db` file

The app expects the mounted database path:

```bash
/mnt/ranker-data/frontiergraph-economics-public.db
```

## Public data artifact

The repository now ships:

- checksum file at `site/public/downloads/frontiergraph-economics-public.sha256.txt`
- manifest file at `site/public/downloads/frontiergraph-economics-public.manifest.json`

The public DB itself should be hosted as a public GCS object or another public blob store. The site export script reads `FRONTIERGRAPH_PUBLIC_DB_URL` to wire the download link. The site export also reads `FRONTIERGRAPH_PUBLIC_APP_URL` to wire the deeper-app links.

## Analytics and feedback

For launch, the cleanest stack is:

- `Cloudflare Web Analytics` for aggregate traffic and performance on the Astro site
- `PostHog Cloud EU` for product events and anonymous feedback
- `Give feedback` surfaces on both the site and app

Cloudflare Web Analytics is enabled in the Cloudflare Pages dashboard. It does not need repo changes.

For the site on Cloudflare Pages, set:

- `PUBLIC_POSTHOG_KEY`
- `PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com`
- `PUBLIC_FEEDBACK_EMAIL=prashant.garg@imperial.ac.uk`

For the Cloud Run app, set these in `deploy/public_release.env` before deploy:

- `FRONTIERGRAPH_POSTHOG_KEY`
- `FRONTIERGRAPH_POSTHOG_HOST=https://eu.i.posthog.com`
- `FRONTIERGRAPH_FEEDBACK_EMAIL=prashant.garg@imperial.ac.uk`

The current implementation is anonymous by default and does not depend on session replay.

## Refresh workflow

The repository includes a GitHub Actions workflow:

- `.github/workflows/refresh-site-data.yml`

It is designed to:

1. download the public database from `FRONTIERGRAPH_PUBLIC_DB_URL`,
2. regenerate site JSON/CSV artifacts,
3. commit the updated generated files.

Configure `FRONTIERGRAPH_PUBLIC_DB_URL` as a GitHub Actions secret before using the workflow.
