# FrontierGraph public release README

FrontierGraph is a public research-allocation release built from a published-journal economics corpus. The current release covers 242,595 screened papers, 1,271,014 normalized links, 6,752 native concepts, and 92,663 released research questions.

## Stable identifiers

- `pair_key`: stable public identifier for a research question or concept pair
- `concept_id`: stable public identifier for a normalized concept

## Which tier should I use?

- **Tier 1: lightweight exports**. Use these if you want spreadsheet-friendly question tables or quick concept summaries.
- **Tier 2: structured graph assets**. Use these if you want the same public graph objects the site uses: the literature map, concept index, neighborhoods, opportunity shards, and slice files.
- **Tier 3: rich public graph bundle**. Use the SQLite bundle if you want to explore locally, reproduce the public app surface, or join question-level evidence tables without rebuilding the release.

## Quick start

- Start with **Tier 1** if you want to sort promising questions, build reading lists, or hand a file to an RA.
- Move to **Tier 2** if you want to rebuild the public map or topic lookup from JSON assets.
- Use **Tier 3** if you want the released questions, concept lookup, neighborhoods, mediators, paths, and starter papers in one local database.

## Typical uses by tier

- **Tier 1**: shortlist candidate topics, filter by direct-literature status, scan likely next study forms, and build spreadsheets for supervisors or lab meetings.
- **Tier 2**: power a local viewer, build a lightweight API, or work directly with topic neighborhoods and question slices without SQL.
- **Tier 3**: inspect one question in depth, join questions to mediators and paths, or run local SQL queries against the same released bundle that powers the public app.

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

## Minimal SQL examples

```sql
-- Top 20 released questions by score
SELECT public_pair_label, direct_link_status, recommended_move, score
FROM questions
ORDER BY score DESC
LIMIT 20;
```

```sql
-- Mediators for one released question
SELECT mediator_label, rank, score
FROM question_mediators
WHERE pair_key = 'FG3C000003__FG3C000208'
ORDER BY rank;
```

```sql
-- Nearby released questions for one concept
SELECT source_label, target_label, rank_for_concept, score
FROM concept_opportunities
WHERE concept_id = 'FG3C000001'
ORDER BY rank_for_concept
LIMIT 15;
```

## What is not included

- The release does **not** redistribute the full underlying extraction corpus.
- The release does **not** claim that surfaced questions are true, important, or socially optimal.
- The release is meant to narrow what to read and inspect next, not replace paper-level judgment.

## Public surfaces

- Site: https://frontiergraph.com
- App: https://frontiergraph-app-1058669339361.us-central1.run.app
- Repository: https://github.com/prashgarg/frontiergraph
