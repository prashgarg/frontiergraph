# Contributing to Frontier Graph

Thanks for your interest in improving Frontier Graph.

## What kind of contributions are helpful

This repository welcomes:

- bug reports
- unclear suggestion or missing-literature reports
- documentation improvements
- small usability fixes
- small, well-scoped pull requests

For larger changes, please open an issue first so we can agree on the shape before code is written.

## Before opening a pull request

Please:

1. explain the user-facing problem or research-use problem being solved
2. keep changes scoped
3. avoid unrelated cleanup in the same PR
4. note any assumptions or tradeoffs

## Local checks

For website-facing changes:

```bash
npm --prefix site run build
```

For Python-side changes, run the relevant checks for the files you touched. At minimum, add or update tests where the change warrants it and make sure the CLI or script path you changed still runs.

## Contribution model

Frontier Graph is an active research codebase. The public site, Explorer, and release pipeline are maintained more tightly than every exploratory analysis script in the repo.

That means:

- issues are welcome
- small PRs are welcome
- larger architecture changes should start as an issue
- review timing may vary

## Questions

If you are unsure whether something belongs in a PR, open an issue first. That is the easiest way to keep the repo coherent while it is still evolving.
