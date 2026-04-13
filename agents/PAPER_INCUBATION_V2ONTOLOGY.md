# Paper Incubation V2 Ontology — Branch: paper-incubation-v2ontology

## What This Branch Is
`paper-incubation-v2ontology` is the active work stream for:
1. Building the v2 ontology (153,800 economics concepts from 5 structured sources)
2. Mapping 1.4M raw extraction labels to the ontology
3. Eventually: rewriting the paper's ontology/node-normalization section to describe v2

Everything is uncommitted in the working tree. The branch tip is the same as main
(`f40d87a`). The v2 ontology data lives entirely in `data/ontology_v2/` (untracked).

## What Has Been Built (2026-04-07/08)

### Ontology (ontology_v2_final.json)
153,800 concepts from 5 sources:
| Source | Count | Notes |
|--------|-------|-------|
| JEL classification | 5,031 | Authoritative; highest priority |
| Wikidata (economics) | 8,395 | QID-grounded, human descriptions |
| OpenAlex topics | 1,881 | MAG-derived hierarchy |
| OpenAlex keywords (≥3 papers) | 9,333 | Author-assigned terms |
| Wikipedia (depth-5 BFS) | 129,162 | Broad coverage; fine-grained named concepts |

Build details: `data/ontology_v2/ontology_design_decisions.md` — full methodology log.
Embeddings: `data/ontology_v2/ontology_v2_label_only_embeddings.npy` (label-only,
symmetric with query side — descriptions shift embeddings by mean cosine 0.77–0.82).

FG3C/v1 artifacts archived: `data/ontology_v2/_v1_artifacts/`, `scripts/_v1_archive/`.
**FG3C must not appear in v2 pipeline.** See design_decisions.md §6e for rationale.

### Label Mapping (extraction_label_mapping_v2.parquet)
1,389,907 unique normalized labels from 242,595 papers mapped against ontology.
Source: `data/ontology_v2/extraction_labels_v2.parquet` (122MB label table).

Matching pipeline:
- Pass 1: Exact label match (case-insensitive, stripped)
- Pass 2: Exact surface-form match (SFs ≥ 3 words only — short SFs cause spurious matches)
- Pass 3: FAISS IVFFlat embedding NN (nlist=1024, nprobe=64, streaming 10K chunks)

Post-hoc patch: `scripts/patch_sf_exact_matches.py` fixed 123,116 rows where 1-2 word
surface forms had matched wrong JEL entries (e.g. "carbon emissions" → JEL "CES").

**Final statistics (post-patch):**
| Tier | Labels | % | Occurrences | % |
|------|--------|---|-------------|---|
| Linked ≥ 0.85 | 92,249 | 6.6% | 241,435 | 13.7% |
| Soft 0.75–0.85 | 224,043 | 16.1% | 311,580 | 17.7% |
| Unmatched < 0.75 | 1,073,615 | 77.2% | 1,209,884 | 68.6% |

Match-kind: unmatched 1,073,615; embedding_sf 191,464; embedding 76,543;
exact_stripped 26,902; exact_sf 9,131; exact 8,251; exact_sf_stripped 4,001.

### Scripts Written (all in scripts/, all untracked)
- `build_ontology_v2.py` — builds ontology_v2_final.json
- `crawl_wikipedia_economics.py` — BFS depth-5 from Category:Economics
- `classify_wikipedia_articles.py` — gpt-4.1-nano classifier
- `fetch_wikipedia_crawl_descriptions.py` — enriches with short_desc + Wikidata desc
- `enrich_wikipedia_with_wikidata.py` — Wikidata description back-enrichment
- `generate_missing_descriptions.py` — LLM descriptions for short ambiguous titles
- `map_extraction_labels_to_ontology_v2.py` — main mapping script (streaming FAISS)
- `patch_sf_exact_matches.py` — post-hoc fix for short-SF exact match bug

## Open Decision (BLOCKS PAPER REWRITE)

**The 77.2% unmatched label rate.** The ontology uses formal concept names; the
extraction produces compound operationalisation phrases. Typical unmatched examples:
- "renewable energy consumption" (freq=1027) → best match "Renewable Energy" cosine 0.732
- "trade openness" (freq=850) → "Trade Liberalization" cosine 0.714
- "gdp per capita" (~700) → "GDP" cosine 0.708

Three options:
1. **Lower threshold to ~0.65** — quick, no new API cost, covers most common compounds
2. **Accept the gap** — use 31.4% matched occurrences; unmatched are paper-specific variants
3. **Targeted ontology enrichment** — add top-N high-freq unmatched compounds to ontology_v2

**Recommendation:** Option 1 (lower to 0.65 as a "candidate" tier) + Option 2 (keep
0.75 as the primary "soft" tier). Store both thresholds in the parquet and let the paper
explain the tiered confidence bands. This avoids a new enrichment run while making the
data usable at a reasonable coverage level.

## What Needs Doing Next

### Step 1 (decision needed): Pick threshold strategy
See open decision above. Once decided, no code change needed — the rank-1 FAISS match
is already stored for all unmatched rows; it's just a matter of which threshold the
paper references.

### Step 2: Rewrite paper Appendix — Node normalization (lines 881–947)
File: `paper/research_allocation_paper.tex`
Current content: FG3C-era pipeline (head-pool, FG3C concept IDs, force-mapped tail)
New content should describe:
- 5-source ontology (153,800 concepts) — why each source, how deduplicated
- Embedding strategy (label-only, text-embedding-3-small, symmetric query/index)
- FAISS matching pipeline (3 passes, thresholds)
- Unmatched rate interpretation (structural gap, not a bug)
- Tiered confidence bands (linked/soft/candidate)
The `ontology_design_decisions.md` has all the detail needed to draft this section.

### Step 3: Update paper Section 3.3 (line 267)
"Node normalization and concept identity" — update counts, remove FG3C references.

### Step 4: Commit and align
Once paper section is drafted, commit v2 ontology work on this branch.

## Key Files to Read Before Paper Rewrite
- `data/ontology_v2/ontology_design_decisions.md` — full v2 methodology (primary source)
- `scripts/map_extraction_labels_to_ontology_v2.py` — mapping pipeline
- `paper/research_allocation_paper.tex` lines 881–947 — current FG3C description to replace
- `paper/research_allocation_paper.tex` lines 267–297 — current normalization section

## What This Does NOT Change (yet)
- The live product (frontiergraph.com) still runs on FG3C-era data
- The main benchmark results in the paper (reranker, SHAP) still use FG3C-era mapping
- Rebuilding the concept graph / candidate universe with v2 mapping is a future step
  (downstream of finalizing the paper's methodology section first)
