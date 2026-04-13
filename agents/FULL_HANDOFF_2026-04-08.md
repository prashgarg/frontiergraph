# Full Handoff 2026-04-08

## Purpose
Complete handoff for a fresh thread. Read this before diving into topic files.
The previous handoff (`FULL_HANDOFF_2026-03-11_ARCHIVED.md`) is now stale — the
ontology has been completely rebuilt since then.

## What FrontierGraph Is
FrontierGraph is a deterministic metascience product for economics. It:
- collects a curated literature corpus (242,595 papers, top 300 economics journals)
- extracts paper-local concept graphs via LLM from titles and abstracts
- builds a concept-level ontology and maps raw labels to it
- computes deterministic ranking signals over missing concept-graph links
- surfaces underexplored concept pairs as research opportunities

The product is a concept graph, not a JEL browser. Ranking and cleanup are
deterministic and inspectable. AI is only used for extraction and description
generation, not for the ranking or recommendation logic.

## Current Branch
`paper-incubation-v2ontology` — all work uncommitted in working tree.
Branch tip is same as `main` at `f40d87a`.

Two work streams are both uncommitted:
- **paper-incubation**: paper rewrites (reranker, SHAP, grouped feature decomposition)
- **paper-incubation-v2ontology**: v2 ontology build + extraction label mapping

## Live Product State
Runs on FG3C (v1) data — unchanged since March 2026.

- Site: frontiergraph.com (Cloudflare Pages, Astro)
- App: economics-opportunity-ranker-beta-1058669339361.us-central1.run.app (Cloud Run)
- Live DB: `concept_exploratory_suppressed_top100k_app_20260309.sqlite`
- Default view: Baseline exploratory (6,752 FG3C head concepts)

The live product will be refreshed with v2 ontology data after the paper section
is finalized. No rush on that — paper comes first.

## Two Parallel Work Streams

### 1. Paper (paper-incubation)
`paper/research_allocation_paper.tex` — 1,405 lines

What's done:
- Full learned reranker section (Section 5.2)
- Grouped SHAP feature decomposition (Section 5.2 paragraph + Appendix line 1135)
- Heterogeneity atlas, failure mode profiles, temporal generalization

What still needs FG3C → v2 rewrite:
- **Appendix: Node normalization and ontology construction (lines 881–947)**
  Currently describes FG3C head-pool / force-map / pending pipeline.
  Needs to describe the v2 5-source ontology instead.
- **Section 3.3: Node normalization (line 267)**
  Remove FG3C concept ID references, update counts.

Pending plan files in `~/.claude/plans/`:
- `moonlit-mapping-lightning.md` — "Four major pushes to populate remaining placeholders"
- `swirling-dreaming-fog.md` — OECD STAN productivity validation
- `velvety-knitting-hopcroft.md` — Enke & Graeber worked example
- `federated-singing-pie.md` — **ALREADY IMPLEMENTED** (SHAP — do not re-execute)

### 2. V2 Ontology (paper-incubation-v2ontology)
Everything built and mapped. Full detail in ONTOLOGY_V2_BUILD.md and LABEL_MAPPING_V2.md.

What's done:
- `data/ontology_v2/ontology_v2_final.json` — 153,800 concepts (5 sources)
- `data/ontology_v2/extraction_label_mapping_v2.parquet` — 1.4M labels mapped + patched
- All scripts in `scripts/` (build, crawl, classify, map, patch)

One open decision blocks the paper rewrite:
**Unmatched threshold strategy** — 77.2% of labels fall below 0.75 soft threshold.
This is structural (formal names vs compound phrases), not a bug. Options:
1. Add 0.65 "candidate" tier (recommended)
2. Accept gap, use 31.4% matched
3. Targeted enrichment (slower)

## Corpus And Data
Unchanged since March 2026.

- Papers: 242,595 (core top 150 + adjacent top 150 journals by mean FWCI)
- Node instances: 1,762,899
- Edges: 1,443,407
- Extraction JSONL: `data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.jsonl.gz`
- Extraction SQLite: same path, `.sqlite` extension
- Enriched OpenAlex metadata: `data/processed/openalex/published_enriched/openalex_published_enriched.sqlite`

Extraction schema: nodes (label, surface_forms, study_context) + edges (source, target,
directionality, relationship_type, causal_presentation, claim_status, evidence_method,
sign, explicitness). Model: gpt-5-mini low reasoning.

## Ontology History

### FG3C (v1, archived)
6,752 canonical concepts from support-gated head rules. Low coverage. Archived in
`data/ontology_v2/_v1_artifacts/` and `scripts/_v1_archive/`. Do not use for v2.

### V2 (current, 153,800 concepts)
5 structured sources: JEL (5,031) + Wikidata (8,395) + OpenAlex topics (1,881) +
OpenAlex keywords (9,333) + Wikipedia depth-5 BFS (129,162).

Matching: 3-pass FAISS pipeline. SF length guard (≥3 words). Streaming 10K chunks.
Final stats: 6.6% linked, 16.1% soft, 77.2% unmatched.
Methodology: `data/ontology_v2/ontology_design_decisions.md`

## Extraction Schema (unchanged)
Node fields: `label`, `surface_forms`, `study_context`
Edge fields: `source`, `target`, `directionality`, `relationship_type`,
`causal_presentation`, `claim_status`, `evidence_method`, `sign`, `explicitness`

Surface forms: text spans from paper referring to the same concept as the label.
Aggregated across all papers per unique normalized label in the mapping.

## Immediate Next Steps
1. User decides unmatched threshold (0.65 candidate tier recommended)
2. Rewrite paper Appendix lines 881–947 to describe v2 ontology
3. Read pending plan files before executing them
4. Commit v2 ontology work on branch

## Recommended Read Order For A New Thread

If resuming v2 ontology / paper rewrite work:
1. This file
2. LATEST.md
3. PAPER_INCUBATION_V2ONTOLOGY.md
4. NEXT_STEPS.md

If resuming paper-incubation (non-ontology paper work):
1. This file
2. LATEST.md
3. PAPER_INCUBATION.md
4. Read each plan file in `~/.claude/plans/` before acting

If understanding the ontology build:
1. ONTOLOGY_V2_BUILD.md
2. LABEL_MAPPING_V2.md
3. `data/ontology_v2/ontology_design_decisions.md`

If working on the live product (site / app):
1. WEBSITE_AND_PRODUCT.md
2. DEPLOYMENT_AND_STORAGE.md
3. PROJECT_STATE.md

## Key Rule
FG3C must not appear in v2 analysis. If you see `FG3C`, `frontiergraph_concept_compare_v1`,
`frontiergraph_ontology_compare_v1`, or `build_frontiergraph_concept_v3.py` in a v2
context, that is a contamination error. The correct v2 ontology target is always
`data/ontology_v2/ontology_v2_final.json`.
