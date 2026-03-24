# Frontier Graph data dictionary

This guide summarizes the main fields in the public download files. If you want one row per suggested question, start with `top_questions.csv`. If you want the full local evidence tables, use the SQLite bundle.

## Shared identifiers

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public identifier for a released question, built from a normalized concept pair. |
| `concept_id` | Stable public identifier for a topic in the public concept layer. |

## `top_questions.csv`

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public question identifier. |
| `source_display_label`, `target_display_label` | Public-facing labels used by the site and app when a cleaner or narrower wording is available. |
| `display_refinement_confidence` | Confidence score for the public display refinement layer. |
| `source_id`, `target_id` | Concept IDs for the two ends of the question. |
| `source_label`, `target_label` | Baseline concept labels preserved for reproducibility. |
| `source_bucket`, `target_bucket` | Coarse location of each concept in the public graph. |
| `cross_field` | Whether the two concepts sit across different broad buckets. |
| `score` | Final public ranking score. |
| `base_score` | Pre-penalty score before duplicate downweighting. |
| `duplicate_penalty` | Downweight applied when many near-duplicate questions cluster together. |
| `path_support_norm` | Normalized support from nearby topic paths in the graph. |
| `gap_bonus` | Bonus for links that look underexplored relative to the local neighborhood. |
| `mediator_count` | Count of intermediate topics supporting the question. |
| `motif_count` | Count of repeated local patterns around the question. |
| `cooc_count` | Count of direct papers already observed in the public release. |
| `direct_link_status` | Reader-facing summary of direct-literature presence. |
| `supporting_path_count` | Count of supporting topic paths surfaced in the release. |
| `why_now` | Plain-language explanation of why the suggested question appears on the public surface. |
| `recommended_move` | Suggested first research move or reading strategy. |
| `slice_label` | Slice or family label used on the public site. |
| `public_pair_label` | Plain-language pair label. |
| `display_question_title` | Question-style title used on the ranked public questions page. |
| `question_family` | Family label used to avoid repetitive windows. |
| `suppress_from_public_ranked_window` | Whether the question is kept out of the default ranked window. |
| `top_mediator_labels` | JSON list of the most important intermediate topics in public display form. |
| `top_mediator_baseline_labels` | JSON list of the corresponding baseline mediator labels kept for reproducibility. |
| `representative_papers` | JSON list of starter papers attached to nearby paths and edges. |
| `top_countries_source`, `top_countries_target` | JSON lists of common settings for each side of the pair. |
| `source_context_summary`, `target_context_summary` | Short context summaries for each side. |
| `common_contexts` | Plain-language summary of overlapping settings. |
| `app_link` | Link into the maintained public site for that question. |

## `central_concepts.csv`

| Field | Meaning |
| --- | --- |
| `concept_id` | Stable concept identifier. |
| `label` | Baseline preferred concept label. |
| `plain_label` | Public display label used by the site and app. |
| `subtitle` | Public clarifier used where concept naming needs context. |
| `display_concept_id` | Concept ID for the display-layer refinement when one exists. |
| `display_refined` | Whether the public display label comes from the finer display layer. |
| `display_refinement_confidence` | Confidence score for the display-layer refinement. |
| `alternate_display_labels` | Alternate finer labels considered for the public surface. |
| `bucket_hint` | Coarse placement of the concept in the graph. |
| `instance_support` | Number of mapped node mentions assigned to the concept. |
| `distinct_paper_support` | Number of distinct papers touching the concept. |
| `weighted_degree` | Weighted graph degree in the normalized graph. |
| `pagerank` | PageRank-style prominence measure. |
| `in_degree`, `out_degree` | Directed degree counts in the graph tables. |
| `neighbor_count` | Number of distinct neighboring concepts. |
| `top_countries`, `top_units` | JSON lists of common settings and units. |
| `app_link` | Link into the maintained public literature view for that concept. |

## Structured JSON assets

| File | Main object | What it contains |
| --- | --- | --- |
| `graph_backbone.json` | `nodes`, `edges` | The lightweight public literature map. |
| `concept_index.json` | concept records | Searchable concept lookup records with aliases and support. |
| `concept_neighborhoods_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to neighborhood shard file. |
| `concept_opportunities_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to concept-opportunity shard file. |
| `opportunity_slices.json` | slice arrays | Public question slices such as overall, cross-area, frontier, and fast-follow. |
| `curated_questions.json` | curated records | Hand-curated questions used in the public site surfaces. |

## SQLite bundle tables

| Table | Grain | Description |
| --- | --- | --- |
| `release_meta` | key-value | Release metadata and artifact paths. |
| `release_metrics` | key-value | Corpus and graph counts for the public release. |
| `top_questions` | one row per released top question | Lightweight question surface mirrored into SQLite. |
| `questions` | one row per released question | Full public question table. |
| `central_concepts` | one row per central concept | Central concept table mirrored from CSV. |
| `concept_index` | one row per concept | Searchable concept records with aliases and literature-view links. |
| `graph_nodes`, `graph_edges` | one row per map node/edge | Lightweight public graph backbone. |
| `opportunity_slices` | one row per pair in a named slice | Slice membership plus JSON payload. |
| `concept_opportunities` | one row per concept-question pairing | Top nearby questions for each concept. |
| `concept_neighborhoods` | one row per concept-neighbor relation | Incoming, outgoing, and top-neighbor records. |
| `question_mediators` | one row per mediator within a question | Ranked mediator concepts for each question. |
| `question_paths` | one row per supporting path | Ranked supporting paths and labels. |
| `question_papers` | one row per paper within a path | Papers connected to a path. |
| `question_neighborhoods` | one row per question | Cached source/target neighborhood JSON. |
