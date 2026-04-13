# Label Mapping V2

## Status
**Complete as of 2026-04-08** (including post-hoc SF patch).
Output: `data/ontology_v2/extraction_label_mapping_v2.parquet` (178MB, 1,389,907 rows)

## What It Maps
**Input:** 1,389,907 unique normalized labels from `fwci_core150_adj150_extractions.jsonl.gz`
(242,595 papers, 1,762,899 node occurrences). Stored in `extraction_labels_v2.parquet`.

**Target:** `ontology_v2_final.json` (153,800 concepts, label-only embeddings)

## Matching Pipeline (3 passes)

### Pass 1 — Exact label match
Normalized label vs ontology label set (case-insensitive, also stripped of punctuation).
Match kinds: `exact`, `exact_stripped`.

### Pass 2 — Exact surface-form match
Each SF alias of the raw label is tried against the ontology.
**SF length guard:** SFs shorter than 3 words are skipped — single/two-word SFs like
"ces", "trade", "insurance" match wrong JEL entries.
Match kinds: `exact_sf`, `exact_sf_stripped`.

**Bug history:** The original run (before patch) accepted short SFs, causing 123,116 rows
to receive wrong matches (e.g. "carbon emissions" → JEL "CES" via SF "ces"). Fixed by
`scripts/patch_sf_exact_matches.py` which re-embedded those labels and ran FAISS NN.

### Pass 3 — FAISS embedding NN
- Embed remaining labels with `text-embedding-3-small` (label text only)
- Normalize; search `IndexIVFFlat` (nlist=1024, nprobe=64) over normalized ontology vectors
- Returns top-3 nearest neighbours per label
- Streaming: 10K chunks to avoid OOM (full 1.4M × 1536 × 4 bytes = 8.6GB)
- Runtime: ~55 minutes for full run, ~2 minutes for the 123K-row patch

Match kinds: `embedding` (label used), `embedding_sf` (SF embedding used).

## Thresholds
- **Linked** ≥ 0.85 — high-confidence matches
- **Soft** 0.75–0.85 — plausible semantic match
- **Unmatched** < 0.75 — below soft threshold (rank-1 match still stored)

## Final Statistics
| Tier | Labels | % | Occurrences | % occ |
|------|--------|---|-------------|-------|
| Linked ≥ 0.85 | 92,249 | 6.6% | 241,435 | 13.7% |
| Soft 0.75–0.85 | 224,043 | 16.1% | 311,580 | 17.7% |
| Unmatched < 0.75 | 1,073,615 | 77.2% | 1,209,884 | 68.6% |

Match-kind breakdown:
- unmatched: 1,073,615
- embedding_sf: 191,464
- embedding: 76,543
- exact_stripped: 26,902
- exact_sf: 9,131
- exact: 8,251
- exact_sf_stripped: 4,001

## Why Is The Unmatched Rate So High?
This is a structural vocabulary gap, not a pipeline error.

The ontology contains **formal concept names** (JEL: "Renewable Energy", "GDP",
Wikipedia: "Carbon emission trading"). The extraction produces **compound
operationalisation phrases** ("renewable energy consumption", "gdp per capita",
"carbon emissions") — how a paper uses a concept, not the concept name itself.

Typical high-frequency unmatched examples:
| Label | freq | Best match | cosine |
|-------|------|-----------|--------|
| renewable energy consumption | 1,027 | Renewable Energy | 0.732 |
| trade openness | 850 | Trade Liberalization | 0.714 |
| carbon emissions | 845 | Carbon emission trading | 0.690 |
| gdp per capita | ~700 | GDP | 0.708 |
| economic policy uncertainty | ~723 | Policy uncertainty | 0.723 |

The rank-1 match IS stored for all unmatched rows, so a lower threshold can be
applied without re-running the pipeline.

## Open Decision: Threshold Strategy
**UNRESOLVED** — see PAPER_INCUBATION_V2ONTOLOGY.md.
Options:
1. Add a 0.65 "candidate" tier (covers most compound phrases)
2. Accept the gap (use 31.4% matched occurrences)
3. Targeted ontology enrichment (add compound terms, re-embed)

## Parquet Schema
Columns:
- `label` (normalized lowercase), `label_raw` (most common casing), `freq` (paper count)
- `n_surface_forms` (count of SF aliases)
- `match_kind` (exact / exact_stripped / exact_sf / exact_sf_stripped / embedding / embedding_sf / unmatched)
- `onto_id`, `onto_label`, `onto_source`, `onto_domain`, `score`
- `matched_via` (what text was used to match: "label" or the SF string)
- `rank2_id`, `rank2_label`, `rank2_score` — 2nd NN
- `rank3_id`, `rank3_label`, `rank3_score` — 3rd NN
- `sf_best_onto_id`, `sf_best_onto_label`, `sf_best_score` — best SF embedding hit

## Scripts
- `scripts/map_extraction_labels_to_ontology_v2.py` — main pipeline
- `scripts/patch_sf_exact_matches.py` — post-hoc SF fix (already run)
