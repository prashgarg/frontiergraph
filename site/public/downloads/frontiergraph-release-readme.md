# Frontier Graph public release README

Frontier Graph is a public browser for suggested research questions in economics. This release starts from 242,595 papers screened from 1976 to 2026 and packages the public question tables and graph assets that sit behind the site.

## Start here

- If you want a spreadsheet-friendly entry point, start with `top_questions.csv`.
- If you want topic search and summary statistics, add `central_concepts.csv`.
- If you want the same JSON and shard files the public site uses, download the Tier 2 packages.
- If you want a queryable local bundle for app-style inspection, download Tier 3.

## Stable identifiers

- `pair_key`: stable public identifier for a research question or concept pair
- `concept_id`: stable public identifier for a topic in the public concept layer

## Which tier should I use?

- **Tier 1: lightweight exports**. Use these if you want spreadsheet-friendly question tables, shortlist reviews, or quick concept summaries.
- **Tier 2: structured graph assets**. Use these if you want the same literature map, concept index, neighborhoods, opportunity shards, and slice files the public site uses. The release is split across multiple zip packages so it stays deployable on static hosting.
- **Tier 3: SQLite bundle**. Use this if you want one local file for structured querying, reproducible local inspection, or mounting the public release into an app container.

## What each file is for

- `top_questions.csv`: one row per suggested question, with display labels, nearby support, path counts, starter papers, and site links.
- `central_concepts.csv`: one row per central topic, with baseline labels, display labels, graph prominence measures, and literature-view links.
- `curated_questions.json`: curated public question records released alongside the site.
- `hybrid_corpus_manifest.json`: release counts for the broader benchmark corpus.
- `graph_backbone.json`: the lightweight literature map used on the public site.
- `concept_index.json`: searchable concept records with aliases, support, and app links.
- `concept_neighborhoods_index.json`: index into the concept-neighborhood shard files.
- `concept_opportunities_index.json`: index into the concept-opportunity shard files.
- `opportunity_slices.json`: grouped question slices used for the public question page.

## How to read the release

- Suggested questions are surfaced because nearby topics and papers already imply short local routes between the two sides.
- Topic links in the graph are ordered topic-to-topic relations extracted from titles and abstracts. They help organize the literature, but they are not final causal judgments.
- CSV files are the easiest entry point for spreadsheets and quick scripts.
- Several CSV columns store lists as JSON strings so the same fields can survive spreadsheet export.

## Public surfaces

- Site: https://frontiergraph.com
- Repository: https://github.com/prashgarg/frontiergraph
