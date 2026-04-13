# FrontierGraph Site Refresh Audit

Date: 12 April 2026

## Goal

Refresh the public site without redesigning it.

The main structural requirement is to stop stale March release data from silently re-entering the site build.

## What is stale now

### 1. Homepage

- The homepage metric count is stale because `site/src/generated/site-data.json` was last generated on `2026-03-17`.
- It still reports `92,663` visible public questions.
- Homepage featured questions also still come from the March generated surface unless overridden by the manual editorial layer.

### 2. Questions page

- The page is a mix of:
  - generated ranking output from `site/src/generated/site-data.json`
  - manual editorial overlays from `site/src/content/editorial-opportunities.json`
  - manual carousel assignments from `site/src/content/questions-carousel-assignments.json`
- The generated ranked window is stale.
- Some card copy, especially `first_next_step`, is intentionally editorial and should be refreshed manually rather than regenerated blindly.

### 3. Graph explorer

- The page itself is simple and not stale in code.
- The underlying JSON it serves is stale because it is still built from the March public candidate backend.
- This includes:
  - selected topic
  - nearby topics
  - local opportunities
  - concept-opportunity shard lookup
- This page cannot be honestly refreshed from the newer paper-facing frontier CSVs alone. It needs a refreshed broad candidate backend.

### 4. Paper page

- Metadata was stale in code and has been patched:
  - subtitle removed
  - status label changed to `Preliminary and Incomplete`
  - last updated changed to `12 April 2026`
- The PDF can be refreshed immediately from `paper/research_allocation_paper.pdf`.
- The HTML manuscript source is still stale because:
  - `paper/research_allocation_paper.md` is stale relative to the current TeX
  - `site/src/generated/paper/research_allocation_paper_full.md` is generated from that stale markdown
- So the paper HTML still needs a proper regeneration step.

### 5. Downloads page

- The page was still exposing an extended abstract that no longer belongs in the public release.
- That button has been removed in both the site page and the site export pipeline.
- The rest of the downloads content is still stale until the new site export and public release bundle are regenerated.

### 6. About page

- No content-level refresh is currently required.

### 7. Literature page

- No refresh is currently required if the underlying literature graph itself is not being updated.

## Structural fix already applied

The site export and public release bundle no longer default silently to the stale March public-app database.

Patched scripts:

- `scripts/export_site_data_v2.py`
- `scripts/build_frontiergraph_public_release_bundle.py`

Both scripts now require:

- `FRONTIERGRAPH_PUBLIC_SOURCE_DB`

If that environment variable is not set explicitly, the build fails.

This is the main guardrail that prevents accidental rebuilds from the old source.

## Build provenance now recorded

`scripts/export_site_data_v2.py` now records source metadata in generated site data:

- public source DB
- public graph DB
- extraction DB
- enriched OpenAlex DB

`scripts/build_frontiergraph_public_release_bundle.py` now records the release source DB in:

- the public downloads manifest
- the generated site data

## Deterministic refresh tasks

These can be done once a refreshed public candidate source is chosen.

1. Regenerate `site/src/generated/site-data.json`
2. Regenerate `site/public/data/v2/*`
3. Regenerate `site/public/downloads/*`
4. Copy the new PDF to the site paper assets
5. Rebuild the public SQLite release bundle

## Manual or editorial refresh tasks

These should be reviewed by hand.

1. `site/src/content/editorial-opportunities.json`
- homepage featured cards
- `short_why`
- `first_next_step`
- `who_its_for`

2. `site/src/content/questions-carousel-assignments.json`
- field shelves
- use-case shelves
- any explicit display titles or display why/first-step overrides

3. Paper HTML
- do not treat it as refreshed until the markdown source is regenerated from the current manuscript

## Important constraint

The newer paper-facing frontier packages are not a full replacement for the public graph backend.

They are good enough to refresh:

- homepage featured questions
- questions-page shelves
- curated front sets

They are not enough, by themselves, to refresh:

- the full graph explorer shard layer
- the full concept-opportunity index

That broader refresh still requires a refreshed public candidate universe.

## Recommended execution order

1. Choose the refreshed public candidate source for the site build.
2. Regenerate site data and downloads from that explicit source.
3. Recurate homepage and questions-page editorial content by hand.
4. Refresh the paper PDF on the site.
5. Regenerate the HTML paper only after the current manuscript markdown is brought into sync.
