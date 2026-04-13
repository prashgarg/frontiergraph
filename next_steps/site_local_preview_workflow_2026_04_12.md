# FrontierGraph Local Preview Workflow

Use local preview while the paper and data refresh are still moving.

Do not push website changes live until explicitly approved.

## Fast local dev preview

Run:

```bash
scripts/start_frontiergraph_site_dev.sh
```

Default address:

- `http://127.0.0.1:4321`

Optional overrides:

```bash
HOST=127.0.0.1 PORT=4322 scripts/start_frontiergraph_site_dev.sh
```

Use this mode when:

- editing page copy
- checking layout
- reviewing question cards and page structure
- iterating on local generated files

## Production-style local preview

Run:

```bash
scripts/start_frontiergraph_site_preview.sh
```

Default address:

- `http://127.0.0.1:4321`

Optional overrides:

```bash
HOST=127.0.0.1 PORT=4322 scripts/start_frontiergraph_site_preview.sh
```

Use this mode when:

- checking the built site rather than the dev server
- verifying that generated assets are wired correctly
- doing a final local review before any future deployment decision

Implementation note:

- this script builds the Astro site and serves the built `dist/` directory locally
- it does not depend on Astro's own preview server

## Scope discipline

While the site is in refresh mode:

- keep all changes local
- treat production as unchanged
- regenerate site data only from explicitly named sources
- do not trust the HTML paper view as current unless the markdown source has been regenerated from the current manuscript

## Current paper-page rule

For now:

- the PDF is the current reference version
- the HTML page should be treated as provisional until it is resynced from the April 2026 manuscript
