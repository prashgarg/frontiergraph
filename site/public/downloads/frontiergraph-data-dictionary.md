# FrontierGraph data dictionary

## Shared identifiers

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public identifier for a released question, built from a normalized concept pair. |
| `concept_id` | Stable public identifier for a normalized concept in the native ontology. |

## `top_questions.csv`

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
| `mediator_count` | Count of nearby linking concepts supporting the question. |
| `motif_count` | Count of repeated local patterns around the question. |
| `cooc_count` | Count of direct papers already observed in the public sample. |
| `direct_link_status` | Reader-facing summary of direct-literature presence. |
| `supporting_path_count` | Count of nearby linking concepts surfaced in the release. |
| `why_now` | Plain-language explanation of why the question is on the release surface. |
| `recommended_move` | Suggested first research move. |
| `slice_label` | Slice or family label used on the public site. |
| `public_pair_label` | Plain-language pair label. |
| `question_family` | Family label used to avoid repetitive windows. |
| `suppress_from_public_ranked_window` | Whether the question is kept out of the default ranked window. |
| `top_mediator_labels` | JSON list of the most important mediating concepts. |
| `representative_papers` | JSON list of papers to begin with, attached to nearby edges. |
| `top_countries_source`, `top_countries_target` | JSON lists of common settings for each side of the pair. |
| `source_context_summary`, `target_context_summary` | Short context summaries for each side. |
| `common_contexts` | Plain-language summary of overlapping settings. |
| `app_link` | Deep link into the public app. |

## `central_concepts.csv`

| Field | Meaning |
| --- | --- |
| `concept_id` | Stable concept identifier. |
| `label` | Preferred concept label. |
| `plain_label` | Smoothed public label if one exists. |
| `subtitle` | Public clarifier used where concept naming needs context. |
| `bucket_hint` | Coarse placement of the concept in the graph. |
| `instance_support` | Number of mapped node mentions assigned to the concept. |
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
| `concept_index` | one row per concept | Searchable concept records with aliases and app links. |
| `graph_nodes`, `graph_edges` | one row per map node/edge | Lightweight public graph backbone. |
| `opportunity_slices` | one row per pair in a named slice | Slice membership plus JSON payload. |
| `concept_opportunities` | one row per concept-question pairing | Top nearby questions for each concept. |
| `concept_neighborhoods` | one row per concept-neighbor relation | Incoming, outgoing, and top-neighbor records. |
| `question_mediators` | one row per mediator within a question | Ranked mediator concepts for each question. |
| `question_paths` | one row per supporting path | Ranked supporting paths and labels. |
| `question_papers` | one row per paper within a path | Papers connected to a path. |
| `question_neighborhoods` | one row per question | Cached source/target neighborhood JSON. |
