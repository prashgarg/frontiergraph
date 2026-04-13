# Ontology V2 Build

## Status
**Complete as of 2026-04-08.** All artifacts are in `data/ontology_v2/`.
The authoritative methodology reference is `data/ontology_v2/ontology_design_decisions.md`.

## What V2 Is
153,800 economics concepts built from 5 structured vocabulary sources:

| Source | Count | Priority | Key property |
|--------|-------|----------|-------------|
| JEL classification | 5,031 | 1 (highest) | Authoritative controlled vocabulary |
| Wikidata (economics subgraph) | 8,395 | 2 | QID-grounded, human descriptions |
| OpenAlex topics | 1,881 | 3 | MAG-derived hierarchy |
| OpenAlex keywords (≥3 papers) | 9,333 | 4 | Author-assigned, high recall |
| Wikipedia depth-5 BFS | 129,162 | 5 (lowest) | Named concepts, historical episodes |

**Important:** FG3C (v1 canonical concepts) is NOT part of v2.
FG3C artifacts are archived in `data/ontology_v2/_v1_artifacts/` and
`scripts/_v1_archive/`. Do not reference them in v2 analysis.

## Build History (what each version was)
- **v1 (FG3C era):** Deterministic seed ontology → ~6,752 concepts.
  Low coverage, now archived.
- **v2 (old / 2025):** Manual-review seed ontology → still low coverage.
  Superseded.
- **v2_new (current, 2026-04-08):** Full 5-source build → 153,800 concepts.
  This is the canonical v2. "ontology_v2" in all current filenames means this.

## Key Build Decisions
**Wikipedia crawl:** BFS depth-5 from `Category:Economics`, April 2026.
184,628 articles crawled → 133,542 after richer classifier (title + short_desc + category).
Classifier: gpt-4.1-nano, 150 concurrent, $3.69.

**Description enrichment (3 tiers for Wikipedia):**
- Tier 1: Wikidata description via QID (41.8% coverage)
- Tier 2: Wikipedia short_desc (4.7%)
- Tier 3: LLM-generated for short ambiguous titles ≤3 words (31.7%, gpt-4.1-nano, ~$1.02)
- No description by design (19.6% — long self-descriptive titles, or single-word no-QID)

**Deduplication (two-pass):**
- Pass 1: Exact label dedup (case-insensitive) → removed ~5,675 cross-source duplicates
- Pass 2: Cosine similarity dedup at threshold 0.93 → removed 63 near-identical pairs

**Embedding format:** `"{label}: {description}"` when description present, else `"{label}"`.
Truncated to 512 chars. Model: `text-embedding-3-small`.

**Label-only embeddings (separate):** `ontology_v2_label_only_embeddings.npy` — used for
mapping raw extraction labels (which have no descriptions). Using description-enriched
ontology embeddings against label-only query embeddings would bias cosine distances by
mean 0.77–0.82.

## Canonical Artifacts
```
data/ontology_v2/
  ontology_v2_final.json                    # 153,800 concepts
  ontology_v2_embeddings.npy                # label+desc embeddings (for ontology use)
  ontology_v2_label_only_embeddings.npy     # label-only (for extraction matching)
  extraction_labels_v2.parquet              # 1,389,907 labels (122MB)
  extraction_label_mapping_v2.parquet       # mapping results (178MB)
  ontology_design_decisions.md             # full methodology log
  _v1_artifacts/                            # FG3C-era files (do not use)
```

## How to Use for Downstream Tasks
- **Mapping lookup:** load `extraction_label_mapping_v2.parquet`, filter by
  `score >= threshold`. Recommended tiers: ≥0.85 (linked), 0.75–0.85 (soft),
  0.65–0.75 (candidate — see PAPER_INCUBATION_V2ONTOLOGY.md for threshold decision).
- **Ontology browse:** load `ontology_v2_final.json`. Fields: `id`, `label`,
  `source`, `domain`, `description`.
- **New embeddings:** use `text-embedding-3-small`, label-only text, normalize.
  Then cosine against `ontology_v2_label_only_embeddings.npy`.
