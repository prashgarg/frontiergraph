# FrontierGraph data dictionary

This dictionary covers the public release files served on the site. CSV and JSON exports are easier entry points; the SQLite bundle contains the fullest released table set.

## Shared identifiers

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public identifier for a released question, built from a normalized concept pair. |
| `concept_id` | Stable public identifier for a normalized concept in the native ontology. |

## `top_questions.csv`

These are the released question rows that drive the public browsing surface.

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public question identifier. |
| `source_id`, `target_id` | Concept IDs for the two ends of the question. |
| `source_label`, `target_label` | Reader-facing concept labels. |
| `source_bucket`, `target_bucket` | Coarse location of each concept in the public graph. |
| `cross_field` | Whether the two concepts sit across different broad buckets. |
| `score` | Final public ranking score. |
| `base_score` | Pre-penalty score before duplicate downweighting. |
| `duplicate_penalty` | Downweight applied when many near-duplicate questions cluster together. |
| `path_support_norm` | Normalized support from nearby paths in the graph. |
| `gap_bonus` | Bonus for links that look underexplored relative to the local neighborhood. |
| `mediator_count` | Count of nearby mediator concepts supporting the question. |
| `motif_count` | Count of reinforcing local structural motifs. |
| `cooc_count` | Count of direct papers already observed in the public sample. |
| `direct_link_status` | Reader-facing summary of direct-literature presence. |
| `supporting_path_count` | Count of supporting paths surfaced in the release. |
| `why_now` | Plain-language explanation of why the question is on the release surface. |
| `recommended_move` | Suggested first research move. |
| `slice_label` | Slice or family label used on the public site. |
| `public_pair_label` | Plain-language pair label. |
| `question_family` | Family label used to avoid repetitive windows. |
| `suppress_from_public_ranked_window` | Whether the question is kept out of the default ranked window. |
| `top_mediator_labels` | JSON list of the most important mediating concepts. |
| `representative_papers` | JSON list of starter papers associated with nearby edges. |
| `top_countries_source`, `top_countries_target` | JSON lists of common settings for each side of the pair. |
| `source_context_summary`, `target_context_summary` | Short context summaries for each side. |
| `common_contexts` | Plain-language summary of overlapping settings. |
| `app_link` | Deep link into the public app. |

## `central_concepts.csv`

These are the topic-level records used for concept lookup and the map-facing concept summaries.

| Field | Meaning |
| --- | --- |
| `concept_id` | Stable concept identifier. |
| `label` | Preferred concept label. |
| `plain_label` | Smoothed public label if one exists. |
| `subtitle` | Public clarifier used where concept naming needs context. |
| `bucket_hint` | Coarse placement of the concept in the graph. |
| `instance_support` | Number of node instances mapped to the concept. |
| `distinct_paper_support` | Number of distinct papers touching the concept. |
| `weighted_degree` | Weighted graph degree in the normalized graph. |
| `pagerank` | PageRank-style prominence measure. |
| `in_degree`, `out_degree` | Directed degree counts in the graph tables. |
| `neighbor_count` | Number of distinct neighboring concepts. |
| `top_countries`, `top_units` | JSON lists of common settings and units. |
| `app_link` | Deep link into the public app. |

## Structured JSON assets

| File | Main object | What it contains |
| --- | --- | --- |
| `graph_backbone.json` | `nodes`, `edges` | The lightweight public literature map. |
| `concept_index.json` | concept records | Searchable concept lookup records with aliases and support. |
| `concept_neighborhoods_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to neighborhood shard file. |
| `concept_opportunities_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to concept-opportunity shard file. |
| `opportunity_slices.json` | slice arrays | Public question slices such as overall, bridges, frontier, and fast-follow. |
| `curated_questions.json` | curated records | Hand-curated questions used in the public site surfaces. |

## SQLite bundle tables

| Table | Grain | Description |
| --- | --- | --- |
| `release_meta` | key-value | Release metadata and artifact paths. |
| `release_metrics` | key-value | Corpus and graph counts for the public release. |
| `top_questions` | one row per released top question | Lightweight question surface mirrored into SQLite. |
| `questions` | one row per released question | Full public question table. |
| `central_concepts` | one row per central concept | Central concept table mirrored from CSV. |
| `concept_index` | one row per concept | Searchable concept records with aliases and app links. |
| `graph_nodes`, `graph_edges` | one row per map node/edge | Lightweight public graph backbone. |
| `opportunity_slices` | one row per pair in a named slice | Slice membership plus JSON payload. |
| `concept_opportunities` | one row per concept-question pairing | Top nearby questions for each concept. |
| `concept_neighborhoods` | one row per concept-neighbor relation | Incoming, outgoing, and top-neighbor records. |
| `question_mediators` | one row per mediator within a question | Ranked mediator concepts for each question. |
| `question_paths` | one row per supporting path | Ranked supporting paths and labels. |
| `question_papers` | one row per starter paper within a path | Starter papers connected to a path. |
| `question_neighborhoods` | one row per question | Cached source/target neighborhood JSON. |

## Question-detail tables inside SQLite

These three tables are the main ones to join when you want to inspect one released question in depth.

| Table | Key fields | What it gives you |
| --- | --- | --- |
| `question_mediators` | `pair_key`, `mediator_concept_id`, `mediator_label`, `rank`, `score` | Ranked mediator concepts that help connect the released source and target. |
| `question_paths` | `pair_key`, `path_rank`, `path_label`, `path_nodes_json`, `path_edges_json` | The supporting paths and their labeled node/edge sequences. |
| `question_papers` | `pair_key`, `paper_id`, `title`, `year`, `journal`, `role`, `path_rank` | Starter papers attached to supporting edges or paths. |

## Concept-detail tables inside SQLite

| Table | Key fields | What it gives you |
| --- | --- | --- |
| `concept_index` | `concept_id`, `plain_label`, `subtitle`, `bucket_hint` | Searchable topic lookup with public labels and aliases. |
| `concept_neighborhoods` | `concept_id`, `neighbor_concept_id`, `direction`, `rank_for_concept` | Incoming and outgoing nearest-neighbor relations around a concept. |
| `concept_opportunities` | `concept_id`, `pair_key`, `rank_for_concept`, `score` | Released questions that sit near that concept. |

## A few fields people usually ask about

| Field | Where it appears | Meaning |
| --- | --- | --- |
| `direct_link_status` | question tables | Reader-facing summary of whether direct papers already exist in the released sample. |
| `recommended_move` | question tables | A short description of the kind of next paper the question seems to invite. |
| `path_support_norm` | question tables | Standardized support from nearby graph paths rather than direct papers. |
| `gap_bonus` | question tables | Extra score for links that look sparse relative to their local neighborhood. |
| `supporting_path_count` | question tables | Count of supporting paths surfaced in the released view. |
| `subtitle` | concept tables | A clarifier used when the public concept label needs context. |
| `bucket_hint` | concept tables | A broad location cue for where the concept sits in the graph. |

## Working with JSON-like columns

- Some CSV and SQLite text fields store arrays or objects as JSON strings.
- Common examples are `top_mediator_labels`, `representative_papers`, `top_countries`, `top_units`, and the path-node or path-edge fields.
- If you are working in spreadsheets, treat these as compact summaries.
- If you are working in Python, R, or SQL pipelines, parse them as JSON before further use.
