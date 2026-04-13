# Ontology v2 Status

Branch: `paper-incubation-v2ontology`

## Data collected (all in `data/ontology_v2/`)

### 1. JEL Classification
- **File:** `jel_codes.csv` (from GitHub structured source)
- **Count:** 998 codes (20 L1, 122 L2, 856 L3)
- **Status:** Clean and complete for the code hierarchy
- **Missing:** L4 keywords, caveats, examples from the AEA guide pages (need browser-rendered fetch — the AEA site is JavaScript-rendered)
- **Next:** Use WebFetch on individual JEL code guide pages, or use an LLM to expand each L3 code into seed terms

### 2. OpenAlex Keywords + Topics
- **File:** `openalex_paper_keywords.parquet` (3,496,792 rows)
- **Count:** 16,707 unique keywords, 1,883 unique topics, 208 subfields
- **Coverage:** All 230K papers
- **Status:** Complete and clean
- **Top keywords:** Economics (190K papers), Business (82K), Econometrics (69K), Finance (55K)
- **Next:** Filter to economics-relevant keywords, build keyword→topic→subfield mapping

### 3. Wikidata Economics Concepts
- **File:** `wikidata_economics_concepts.json` (15,568 concepts)
- **Status:** NOISY — transitive subclass queries go too deep and pick up non-economics concepts
- **Next:** Re-query with depth limits (max 3 hops), filter against JEL terms and corpus, or use instance-of (P31) instead of subclass-of (P279*)

### 4. Raw LLM Labels (existing)
- **Database:** `data/production/frontiergraph_extraction_v2/.../fwci_core150_adj150_extractions.sqlite`
- **Table:** `nodes` — 1,762,898 instances, 1,389,907 unique labels
- **Distribution:** 93.8% hapax, 6,890 labels appear 10+ times
- **Current mapping:** 206:1 compression to 6,752 concept codes

## Architecture (confirmed)

```
Layer 0: Wikidata Q-IDs (external grounding, hierarchy)
Layer 1: JEL codes (economics-specific backbone, 856 L3 codes)
Layer 2: OpenAlex keywords (corpus-grounded, ~16K unique)
Layer 3: Raw LLM labels (paper-specific, 1.4M unique)
```

Context (country, year, method) stays SEPARATE from the concept hierarchy.
Context can interact with any Layer 2/3 concept downstream but does not define concept identity.

## Key design decisions

1. The ontology is over CONCEPTS, not contexts
2. JEL provides the hierarchical backbone (enables "don't suggest within same family")
3. OpenAlex keywords provide corpus grounding (the concept actually appears in real papers)
4. Wikidata provides external validation (the concept exists independently of our corpus)
5. Target granularity: ~20K-50K concepts (vs current 6,752)

## OpenAlex topic model methodology (for reference)

OpenAlex used:
1. Citation clustering (CWTS/Leiden) to define ~4,500 topic communities
2. LLM labeling of clusters
3. BERT fine-tuning (bert-base-multilingual-cased) on title+abstract to classify works
4. ASJC hierarchy mapping (topic → subfield → field → domain)
5. Training data from CWTS on Zenodo

We could adapt this: cluster our 1.4M raw labels using co-occurrence in papers, map clusters to JEL+Wikidata, train a classifier.

## Next steps (for next session)

1. **Clean Wikidata** — re-query with depth limits, filter to economics-relevant
2. **Fetch JEL L4 keywords** — from AEA guide pages or LLM expansion
3. **Map JEL → OpenAlex topics** — find correspondences
4. **Build the mapping pipeline** — raw labels → OpenAlex keywords → JEL codes → Wikidata
5. **Test on a sample** — map 1,000 random raw labels through the hierarchy, check quality
6. **Compare granularities** — re-run benchmark at 6.7K, 20K, 50K concept levels
