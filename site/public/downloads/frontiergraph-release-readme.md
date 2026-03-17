# Frontier Graph public release README

Frontier Graph is a public browser for suggested research questions in economics. This release starts from 242,595 papers screened from 1976 to 2026 and packages the public question tables, graph assets, and SQLite bundle that sit behind the site.

## Start here

- If you want a spreadsheet-friendly entry point, start with `top_questions.csv`.
- If you want topic search and summary statistics, add `central_concepts.csv`.
- If you want the same JSON and shard files the public site uses, download Tier 2.
- If you want the full local evidence tables in one file, download `frontiergraph-economics-public.db`.

## Stable identifiers

- `pair_key`: stable public identifier for a research question or concept pair
- `concept_id`: stable public identifier for a topic in the public concept layer

## Which tier should I use?

- **Tier 1: lightweight exports**. Use these if you want spreadsheet-friendly question tables, shortlist reviews, or quick concept summaries.
- **Tier 2: structured graph assets**. Use these if you want the same literature map, concept index, neighborhoods, opportunity shards, and slice files the public site uses.
- **Tier 3: SQLite bundle**. Use this if you want the full local evidence tables in one file for Python, R, or DB Browser for SQLite.

## What each file is for

- `top_questions.csv`: one row per suggested question, with display labels, nearby support, path counts, starter papers, and explorer link.
- `central_concepts.csv`: one row per central topic, with baseline labels, display labels, and graph prominence measures.
- `curated_questions.json`: the hand-curated site questions shown in featured shelves.
- `hybrid_corpus_manifest.json`: release counts for the broader benchmark corpus.
- `graph_backbone.json`: the lightweight literature map used on the public site.
- `concept_index.json`: searchable concept records with aliases, support, and app links.
- `concept_neighborhoods_index.json`: index into the concept-neighborhood shard files.
- `concept_opportunities_index.json`: index into the concept-opportunity shard files.
- `opportunity_slices.json`: grouped question slices used for the public question page.
- `frontiergraph-economics-public.db`: the full public SQLite bundle.

## How to read the release

- Suggested questions are surfaced because nearby topics and papers already imply short local routes between the two sides.
- Topic links in the graph are ordered topic-to-topic relations extracted from titles and abstracts. They help organize the literature, but they are not final causal judgments.
- CSV files are the easiest entry point for spreadsheets and quick scripts.
- Several CSV columns store lists as JSON strings so the same fields can survive spreadsheet export.
- The SQLite bundle is the most complete public package. It includes question-level tables such as `question_mediators`, `question_paths`, and `question_papers`, plus both baseline and public display labels.

## Public surfaces

- Site: https://frontiergraph.com
- Explorer: https://frontiergraph-app-1058669339361.us-central1.run.app
- Repository: https://github.com/prashgarg/frontiergraph
