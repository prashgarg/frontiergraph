# Frontier Graph reproducibility notes

Frontier Graph is designed to be inspectable and partially reproducible from the public repository, but not every upstream dependency is bundled into Git.

## What is reproducible from the public repo alone

- the website code in `site/`
- the deprecated app code in `app/`
- the paper source in `paper/`
- the demo-data path in `data/demo/`
- the release/export logic in `scripts/`

## What depends on the public release bundle

To reproduce the public website against the current release, you should use the public SQLite bundle and generated release artifacts linked from the downloads page.

That is the intended reproduction path for the current public release. The deprecated app can also be pointed at that same bundle if you want to inspect the archived workflow locally.

## What is only partially reproducible

Full rebuilds of the economics-facing release depend on external inputs that are not all bundled into Git, including:

- upstream corpora and metadata sources
- API-backed extraction steps
- deployment and hosting infrastructure

## Demo path versus full economics path

The demo path is included to make the end-to-end pipeline easier to inspect locally.

The full economics build is broader and closer to the public release, but it is not a one-command fully self-contained reproduction target from Git alone.

## Recommended interpretation

Treat the public repo as:

- the source for the website, deprecated app code, paper, and release pipeline
- a transparent companion to the public release bundle
- a research codebase whose maintained public surfaces are narrower than its full experimental history
