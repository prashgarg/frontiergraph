# Frontier Graph public release deployment

## Surfaces

- `frontiergraph.com`: Astro site on Cloudflare Pages
- public database mirror: SQLite hosted from Google Cloud Storage
- archived app code: `app/` in this repository, no longer deployed publicly

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

## Archived app

The old Streamlit app is kept in `app/` as deprecated code. It is no longer part of the public deployment and should not be redeployed automatically.

- `Dockerfile` still captures the old container path if you ever want to revive it
- `src/run_ranker.py` still starts the archived app locally
- if revived locally, `ECON_OPPORTUNITY_DB` should point to the mounted `frontiergraph-economics-public.db` file

The archived app expects the mounted database path:

```bash
/mnt/ranker-data/frontiergraph-economics-public.db
```

## Public data artifact

The repository now ships:

- checksum file at `site/public/downloads/frontiergraph-economics-public.sha256.txt`
- manifest file at `site/public/downloads/frontiergraph-economics-public.manifest.json`

The public DB itself should be hosted as a public GCS object or another public blob store. The site export script reads `FRONTIERGRAPH_PUBLIC_DB_URL` to wire the download link.

## Analytics and feedback

For launch, the cleanest stack is:

- `Cloudflare Web Analytics` for aggregate traffic and performance on the Astro site
- `PostHog Cloud EU` for product events and anonymous feedback
- `Give feedback` surfaces on the site

Cloudflare Web Analytics is enabled in the Cloudflare Pages dashboard. It does not need repo changes.

For the site on Cloudflare Pages, set:

- `PUBLIC_POSTHOG_KEY`
- `PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com`
- `PUBLIC_FEEDBACK_EMAIL=prashant.garg@imperial.ac.uk`

For the Cloud Run app, set these in `deploy/public_release.env` before deploy:

## Refresh workflow

The public release can be refreshed locally by:

1. pointing `FRONTIERGRAPH_PUBLIC_DB_URL` at the current mirrored public database,
2. regenerating the site JSON and CSV artifacts,
3. rebuilding the site.

If you later automate this in GitHub Actions or another CI system, use the same release inputs and generated paths described above.
