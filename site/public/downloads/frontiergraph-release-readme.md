# FrontierGraph public release README

FrontierGraph is a public research-allocation release built from a published-journal economics corpus. The current release covers 242,595 screened papers, 1,271,014 normalized links, 6,752 native concepts, and 92,663 released questions.

## Stable identifiers

- `pair_key`: stable public identifier for a research question or concept pair
- `concept_id`: stable public identifier for a normalized concept

## Which tier should I use?

- **Tier 1: lightweight exports**. Use these if you want spreadsheet-friendly question tables or quick concept summaries.
- **Tier 2: structured graph assets**. Use these if you want the same public graph objects the site uses: the literature map, concept index, neighborhoods, opportunity shards, and slice files.
- **Tier 3: rich public graph bundle**. Use the SQLite bundle if you want to explore locally, reproduce the public app surface, or join question-level evidence tables without rebuilding the release.

## What each file is for

- `top_questions.csv`: one row per released question, with ranking fields, nearby support, and app link.
- `central_concepts.csv`: one row per central concept, with support and graph prominence measures.
- `curated_questions.json`: the hand-curated site questions shown in featured shelves.
- `hybrid_corpus_manifest.json`: canonical release counts for the fuller published-journal benchmark.
- `graph_backbone.json`: the lightweight literature map used on the public site.
- `concept_index.json`: searchable concept records with aliases, support, and app links.
- `concept_neighborhoods_index.json`: index into the concept-neighborhood shard files.
- `concept_opportunities_index.json`: index into the concept-opportunity shard files.
- `opportunity_slices.json`: grouped question slices used for the public question page.
- `frontiergraph-economics-public.db`: the rich public SQLite bundle.

## Notes on formats

- CSV files are the easiest entry point for spreadsheets and quick scripts.
- Several CSV columns store lists as JSON strings so the same fields can survive spreadsheet export.
- The SQLite bundle is the most complete public package. It includes question-level tables such as `question_mediators`, `question_paths`, and `question_papers`.

## Public surfaces

- Site: https://frontiergraph.com
- App: https://frontiergraph-app-1058669339361.us-central1.run.app
- Repository: https://github.com/prashgarg/frontiergraph
