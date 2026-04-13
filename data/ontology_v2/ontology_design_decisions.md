# Ontology v2 — Design Decisions Log

This file records every non-trivial methodological choice made in building
`ontology_v2_final.json`.  It is intended as the primary source for the paper's
Data / Methods section on the knowledge-base construction.

---

## 1. Corpus sources and rationale

| Source | Raw count | After dedup | Final count | Rationale |
|--------|-----------|-------------|-------------|-----------|
| JEL classification system | 5,031 | 5,031 | **5,031** | Authoritative controlled vocabulary for economics; codes link directly to academic subfields; used as canonical label when label collision occurs |
| Wikidata (economics subgraph) | 11,976 raw (3,443 duplicates from QID repetitions in upstream file) | 8,533 | **8,395** | Structured knowledge base with QID identifiers; multi-language aliases; Wikidata short descriptions; broad coverage beyond formal taxonomy |
| OpenAlex topics | 1,883 | 1,883 | **1,881** | Machine-generated topic hierarchy derived from MAG; captures emerging interdisciplinary fields not in JEL |
| OpenAlex keywords (≥3 papers) | 10,549 | 10,549 | **9,333** | High-frequency author-assigned terms from the full OpenAlex corpus; reflects actual usage patterns in recent literature |
| Wikipedia (depth-5 BFS from Category:Economics) | 184,628 crawled → 133,542 after richer classification | 133,542 | **129,162** | Fine-grained named concepts (country-level policies, named instruments, historical episodes) that appear in raw extraction labels but are absent from the four structured sources above |

**Pipeline counts (confirmed, final build):**

| Stage | Count | Removed |
|-------|-------|---------|
| Raw (after Wikidata QID dedup at source) | 159,538 | −3,443 QID dupes |
| After Pass 1 – exact label dedup | 153,863 | −5,675 |
| After Pass 2 – cosine dedup (threshold 0.93) | **153,800** | −63 |

Note on Pass 2 count evolution across builds:
- Without any Wikipedia descriptions: 61 pairs merged
- With Wikidata descriptions only (42 % coverage): 82 pairs merged
- With all three description tiers (78 % coverage): 63 pairs merged

The non-monotonic change (82 → 63 after adding LLM descriptions) reflects that LLM descriptions added *specificity* to some Wikipedia entries, making them more distinct from their Wikidata counterparts at the 0.93 threshold.  This is the desired behaviour: the LLM descriptions are intended to disambiguate, not to homogenise.  Near-synonyms like "Inflation" / "Inflation rate" (cosine ≈ 0.87) remain correctly separated throughout.

---

## 2. Wikipedia crawl

### 2a. BFS parameters
- **Seed:** `Category:Economics` on English Wikipedia
- **Depth:** 5 levels
- **Rate limit:** 0.15 s/request (Wikipedia API ToS compliance)
- **Result:** 10,400 categories visited, 184,628 articles, runtime ~82 min

**Justification for depth-5:** Depth-3 misses applied subfields (e.g. "Inflation
in Venezuela" is Category:Economics → Monetary economics → Inflation →
Hyperinflation → … → article).  Depth-5 captures nearly all economics-adjacent
Wikipedia content while remaining computationally feasible in a single run.
Depth-6 would add ~30 % more articles at diminishing economics relevance.

### 2b. Built-in classifier (title + category path only)
- Model: gpt-4.1-nano, 150 concurrent, 146 articles/s
- Acceptance rate: **96.9 %** (178,957 / 184,628)
- This classifier was run automatically by the crawl script.
- **Not used** as the primary filter (too permissive).

### 2c. Richer classifier (title + Wikipedia short description + category path)
- Model: gpt-4.1-nano, 150 concurrent, 146 articles/s
- Cost: **$3.69**
- Acceptance rate: **72.3 %** (133,542 / 184,628)
- **Used** as the primary filter for ontology inclusion.

**Justification for richer classifier:** The short description from the Wikipedia
API disambiguates articles whose titles are ambiguous (e.g. "Banana republic" →
"American clothing and accessory retailer" → rejected; "Banana republic" →
"politically unstable country" → accepted).  The 24.6 pp reduction in acceptance
rate relative to the title-only classifier eliminates most false positives.

### 2d. Short description enrichment
- Script: `fetch_wikipedia_crawl_descriptions.py`
- Wikipedia API hit rate: 55.8 % (103,078 / 184,628 unique titles returned data)
- Of returned articles: 78.7 % had a short description; 38.8 % had an extract.
- Articles with no API response receive empty `short_desc` / `extract` fields.

### 2d. Wikidata description back-enrichment for Wikipedia articles

**Observation:** Wikipedia and Wikidata are products of the same Wikimedia
Foundation.  Almost every Wikipedia article has a corresponding Wikidata item
linked via a "sitelink".  Our Wikipedia API fetch captured `wikidata_id` for
54.4 % of the 184,628 crawled articles (100,445 QIDs), but our Wikidata SPARQL
pull used economics-specific property filters and captured only 8,533 QIDs —
a 0.6 % overlap with the Wikipedia articles that had QIDs.  This left 69,927
QIDs known but unenriched.

**Fix:** A dedicated enrichment pass (`enrich_wikipedia_with_wikidata.py`)
batch-fetches English labels and descriptions from the `wbgetentities` API for
all 69,927 missing QIDs (1,399 batches of 50, 30 concurrent, ~102s runtime).

**Results:**
- 62,427 / 69,927 QIDs resolved (89.3 % hit rate)
- 55,807 / 133,542 valid Wikipedia articles gained a Wikidata description (41.8 %)
- Additional 6,237 articles retain Wikipedia `short_desc` as fallback (4.7 %)
- 71,498 articles remain with no description (53.5 %)

**Why Wikidata descriptions are preferred over Wikipedia short_desc:**
Wikidata descriptions are human-curated to be concise and unambiguous (typically
5–10 words).  Wikipedia's `short_desc` is auto-generated from the article lead
and is often longer, less precise, or missing entirely.  Example:

| Article | Wikidata desc | Wikipedia short_desc |
|---------|--------------|---------------------|
| Real economy | "a part of the whole economy concerning the flow of goods and services, contrasted with the monetary sector" | "Production, distribution and consumption of goods and services; distinct from finance" |
| Assume a can opener | "catchphrase used to mock theorists who base their conclusions on impractical or unlikely assumptions" | "Mocking catchphrase" |
| 99ers | "colloquial term for unemployed people in the United States" | "Long-term unemployed people in US" |

**Effect on deduplication:** The enriched descriptions caused 21 additional
Wikipedia–Wikidata pairs to exceed the 0.93 cosine threshold (82 total merged
vs 61 without enrichment), confirming that the descriptions improved embedding
alignment for concept pairs that were already near-duplicates in label space.

### 2e. LLM-generated descriptions for short ambiguous titles

**Motivation:** After Wikidata enrichment, 71,498 Wikipedia articles (53.5 %)
still had no description.  For multi-word specific titles ("Treasury
Inflation-Protected Securities", "Inflation in Venezuela") the title alone
provides sufficient embedding signal.  For short ambiguous titles ("Dutch
disease", "Animal spirits", "Gig economy") a description is needed to anchor
the embedding in the economics domain and away from competing meanings.

**Target:** Titles ≤ 3 words with no Wikidata or Wikipedia description.
Single-word titles with no `wikidata_id` are excluded — they are most likely
disambiguation pages or misclassified articles where no reliable grounding
exists and hallucination rates are high (observed in pilot: "Slate" with
misleading category path produced a fabricated interdisciplinary economics
meaning; correct interpretation is a Californian political slate or rock type).

**Prompt design:** Wikidata style explicitly requested (5–15 words, lowercase,
no leading article), domain used as disambiguation anchor, category path as
structural context.  Output is plain text after an explicit "Description:" label
— avoids the format-echo failure observed with arrow-separator prompts in the
initial pilot.  Nickname/catchphrase instruction added after pilot showed "The
dismal science" needed explicit guidance ("nickname for economics, coined by
Thomas Carlyle in the 19th century" vs a generic description of pessimistic
economics).

**Bug fixed:** Initial run produced scrambled descriptions due to
`asyncio.as_completed()` returning futures in completion order while results
were zipped with targets in submission order.  Fixed by returning `(title, desc)`
tuples so each result carries its own key regardless of completion order.

**Results:**
- 42,292 descriptions generated (229s at 187/s, gpt-4.1-nano, concurrency=150)
- Actual cost: ~$1.02
- 9,276 single-word no-QID titles skipped (safety filter)
- 19,930 titles ≥ 4 words skipped (self-descriptive)

**Coverage after all three tiers:**

| Tier | Source | Count | Share |
|------|--------|-------|-------|
| 1 | Wikidata description | 55,807 | 41.8 % |
| 2 | Wikipedia short_desc | 6,237 | 4.7 % |
| 3 | LLM-generated (gpt-4.1-nano) | 42,292 | 31.7 % |
| — | No description (by design) | 29,206 | 21.9 % |

The 21.9 % with no description are intentionally uncovered: 19,930 long titles
(self-descriptive) and 9,276 ambiguous single-word titles (high hallucination
risk).

**The 53.5 % without any description:** These fall into three categories:
1. QID not returned by Wikidata API (obscure or recently created items): ~7,500
2. QID exists but has no English description: ~24,000
3. No QID at all (Wikipedia article not linked to Wikidata, or fetch miss): ~40,000

For the raw label mapping downstream, articles without descriptions embed on
label alone.  For self-descriptive multi-word titles ("Inflation in Venezuela",
"Treasury Inflation-Protected Securities") this is sufficient.  For short
ambiguous titles ("Grain", "Slate", "Dollar"), label-only embeddings may
introduce modest noise.  A targeted LLM description pass for single- and
two-word titles without any description (~18,000 articles, estimated cost ~$0.20
with gpt-4.1-nano) is noted as a potential future improvement but was not
implemented in the current build.

---

## 3. Deduplication strategy (two-pass)

### Pass 1 — Exact label dedup (case-insensitive)
**Problem diagnosed:** The upstream `wikidata_valid_enriched.json` file contains
2,724 duplicate QIDs (3,443 extra entries), causing labels like "collapsology" to
appear 12 times.  Additionally, 2,569 cross-source pairs share identical surface
labels (e.g. "Core inflation" in both `openalex_keyword` and `wikipedia`) but
have distinct embeddings, so the cosine pass misses them.

**Fix:** Before embedding, group all entries by `label.lower().strip()`.  Within
each group, keep one canonical entry (chosen by `SOURCE_PRIORITY`; ties broken by
longer description).  Merge all provenance into the `_sources` list.

**Entries removed:** ~8,100 (exact figure reported in build log)

### Pass 2 — Cosine similarity dedup (threshold = 0.93)
**Problem:** Spelling variants and capitalisation differences survive exact
matching (e.g. "electronic medical record" vs "Electronic medical record", or
"decision theory" vs "Decision Theory").

**Threshold = 0.93:**  Chosen to collapse near-identical surface forms while
retaining semantically distinct but related concepts.
- At 0.93: "Inflation" (cos ≈ 0.87 to "Inflation rate") are kept separate ✓
- At 0.93: "electronic medical record" / "Electronic medical record" (cos ≈ 0.999)
  are merged ✓
- Manual spot-check of 200 pairs near threshold: <2 % false-merge rate.

**Why not lower the threshold to catch more near-synonyms?**
The vocabulary is used for nearest-neighbour label mapping, not for building a
strict concept hierarchy.  Merging "Inflation" and "Inflation rate" at a lower
threshold (they are cosine ≈ 0.87 with `text-embedding-3-small`) would lose the
ability to distinguish which sense a raw extraction label refers to.  The two
concepts are genuinely different empirical objects in the economics literature.

---

## 4. Source priority for canonical label selection

```
jel > wikidata > openalex_topic > openalex_keyword > wikipedia
```

| Priority | Source | Reasoning |
|----------|--------|-----------|
| 1 (highest) | JEL | Single authoritative taxonomy; controlled vocabulary; code hierarchy provides free structured metadata |
| 2 | Wikidata | QID-grounded; short descriptions are human-edited and concise; more precise than free-form keywords |
| 3 | OpenAlex topic | Peer-reviewed classification derived from MAG subject areas; more stable than author keywords |
| 4 | OpenAlex keyword | High recall but free-form; capitalisation and normalisation inconsistent across papers |
| 5 (lowest) | Wikipedia | Broadest coverage but most noise; article titles can include disambiguation suffixes ("… (economics)") and named proper nouns that are poor canonical labels |

When sources conflict on the canonical label, the higher-priority source's label
is used verbatim.  The lower-priority source's label is preserved in `_sources`.

---

## 5. Domain taxonomy

The 14 valid domains used throughout the pipeline:

| Domain | Description |
|--------|-------------|
| `econ_core` | Core economic theory and empirical methods |
| `econ_applied` | Applied economics subfields |
| `finance` | Financial economics, markets, instruments |
| `health` | Health economics, epidemiology |
| `environment` | Environmental and energy economics |
| `education` | Education economics |
| `demographics` | Population, migration, labour |
| `politics` | Political economy, governance, institutions |
| `institutions` | Formal institutions and legal structures |
| `technology` | Technology, innovation, R&D |
| `events` | Historical episodes, policy events |
| `commodities` | Commodity markets and natural resources |
| `behavior` | Behavioural economics and psychology |
| `other_valid` | Economics-adjacent concepts that don't fit cleanly above |

Rejected domains: `irrelevant`, `noise`, `method` (methodology articles),
`geography` (pure geography without economics content).

**Note on `other_valid`:** This category is intentionally broad.  In the
Wikipedia classification it captures 77,316 entries — concepts ranging from
"Commonwealth" to "Census" that are clearly relevant reference knowledge for
an economics paper graph but don't map to a specific subfield.  For downstream
tasks the full 14-category breakdown is used rather than collapsing
`other_valid`.

---

## 6. Raw label mapping (v2)

Scripts: `scripts/map_extraction_labels_to_ontology_v2.py` (main mapping),
`scripts/patch_sf_exact_matches.py` (post-hoc fix for short-SF bug).

### 6a. Input

**Labels:** 1,425,487 unique raw labels from `fwci_core150_adj150_extractions.jsonl.gz`
(242,595 papers).  Normalized to lowercase → 1,389,907 unique keys stored in
`data/ontology_v2/extraction_labels_v2.parquet`.

Each row: `label` (normalized), `label_raw` (most common casing), `freq` (paper count),
`surface_forms` (union of all SF aliases across papers), `n_surface_forms`.

**Ontology target:** `ontology_v2_final.json` — 153,800 concepts from JEL,
Wikidata, OpenAlex topics, OpenAlex keywords, Wikipedia.  No FG3C entries.

### 6b. Matching pipeline

**Pass 1 — Exact label match (case-insensitive, stripped):**
Matches raw label directly against ontology label set.  Accounts for
`exact` (precise) and `exact_stripped` (punctuation removed).

**Pass 2 — Exact surface-form match:**
Tries each SF alias of the raw label against the ontology.  Bug fixed:
surface forms shorter than 3 words are skipped — single-word SFs like
"ces", "trade", "insurance" spuriously matched JEL abbreviations and
unrelated entries.  Post-hoc correction via `patch_sf_exact_matches.py`
re-embedded all 123,116 bad rows and replaced with FAISS NN results.

**Pass 3 — Embedding nearest-neighbour (FAISS):**
Raw labels are embedded with `text-embedding-3-small` (label text only;
no descriptions available).  Ontology is also embedded label-only for
symmetry — descriptions shift embeddings by mean cosine 0.77–0.82, so
mixing label-only queries against description-enriched index would bias
distances.  Stored in `ontology_v2_label_only_embeddings.npy`.

FAISS index: `IndexIVFFlat` (inner-product, nlist=1024, nprobe=64) on
153,800 normalised ontology vectors.  Returns top-3 nearest neighbours
per query.  Processing: streaming 10K chunks (prevents OOM on full 1.4M
set ≈ 8.6 GB float32 if loaded at once).

Thresholds: linked ≥ 0.85, soft 0.75–0.85, unmatched < 0.75.

SF hits (from Pass 2 survivors) are stored separately as
`sf_best_onto_id/label/score` for optional post-processing.

### 6c. Final mapping statistics (post-patch)

Output: `data/ontology_v2/extraction_label_mapping_v2.parquet`
(1,389,907 rows; 178 MB)

| Tier | Labels | % | Occurrences | % occ |
|------|--------|---|-------------|-------|
| Linked (≥ 0.85) | 92,249 | 6.6% | 241,435 | 13.7% |
| Soft (0.75–0.85) | 224,043 | 16.1% | 311,580 | 17.7% |
| Unmatched (< 0.75) | 1,073,615 | 77.2% | 1,209,884 | 68.6% |

Match-kind breakdown:

| kind | count |
|------|-------|
| unmatched | 1,073,615 |
| embedding_sf | 191,464 |
| embedding | 76,543 |
| exact_stripped | 26,902 |
| exact_sf | 9,131 |
| exact | 8,251 |
| exact_sf_stripped | 4,001 |

### 6d. Interpretation of high unmatched rate

77% of unique labels (68.6% of occurrences) fall below the 0.75 soft
threshold.  This reflects a structural gap between the ontology and the
LLM extraction vocabulary, not a pipeline error:

- **Ontology entries are formal concept labels** (JEL: "Renewable Energy",
  Wikipedia: "GDP", OpenAlex: "Trade Liberalization").
- **Extraction labels are compound measurement phrases** ("renewable energy
  consumption", "gdp per capita", "trade openness") that describe how
  concepts are operationalised in a specific paper.

Typical unmatched high-frequency examples:

| Label | freq | Best match | cosine |
|-------|------|-----------|--------|
| renewable energy consumption | 1,027 | Renewable Energy (jel) | 0.732 |
| trade openness | 850 | Trade Liberalization (jel) | 0.714 |
| carbon emissions | 845 | Carbon emission trading (wiki) | 0.690 |
| gdp per capita | ~700 | GDP (jel) | 0.708 |
| economic policy uncertainty | ~723 | Policy uncertainty (wiki) | 0.723 |

The rank-1 FAISS match is stored even for unmatched rows (in `onto_id`,
`onto_label`, `score`), so downstream users can apply a different
threshold (e.g. 0.65 "candidate" tier) without re-running the pipeline.

### 6e. Note on v1 artifacts

An earlier exploratory run mapped the v1 FG3C canonical concept vocabulary
(6,752 concepts) against this ontology, and a further experiment appended
those FG3C concepts as a 6th ontology source.  Both are incorrect for v2:
the ontology must be built from structured vocabulary sources only, and
the input labels for the mapping must come from the raw extraction output,
not the v1 canonical concept layer.  Those v1 artifacts are archived in
`data/ontology_v2/_v1_artifacts/` and `scripts/_v1_archive/`; they should
not be referenced in v2 analysis.

---

---

## 8. Embedding model

**Model:** `text-embedding-3-small` (OpenAI)

**Justification:** Sufficient semantic resolution for economics vocabulary;
substantially cheaper than `text-embedding-3-large` with minimal accuracy loss
at the dedup and alignment tasks (both involve high-cosine near-duplicates and
in-domain nearest neighbours).  The 1,536-dimensional vectors fit comfortably in
RAM for the full 162,981-entry matrix (≈ 950 MB float32).

**Embedding text format:** `"{label}: {description}"` when description is
present, else `"{label}"`.  Truncated to 512 characters.  This ensures the
embedding captures both the term and its gloss, reducing polysemy (e.g.
"Commonwealth" embeds differently with "British Commonwealth of Nations" vs
"state government in Virginia").

---

## 9. Known limitations

1. **Wikipedia recency:** The crawl was conducted on 2026-04-07.  Articles added
   or renamed after this date are not captured.  Re-crawling is recommended
   before major revisions.

2. **Wikidata upstream noise:** Even after QID-dedup, Wikidata contains
   economics-adjacent entries that are not economics concepts per se (e.g.
   ambassadors, geographic constituencies, software products).  These pass the
   LLM classifier but add noise to the `other_valid` bucket.  A stricter
   Wikidata filter (requiring a JEL-code parent or an economics-specific
   property) would increase precision at the cost of recall.

3. **`other_valid` size:** 77,316 entries classified as `other_valid` in the
   final ontology.  This is by design (broad coverage) but means the domain
   breakdown does not cleanly represent the economics concept space.  For
   analysis requiring clean domain attribution, restrict to the 13 named domains.

4. **Zero-vector fallback:** When the OpenAI embedding API fails (network error,
   token overflow), a `[0.0] * 1536` zero vector is stored.  This produces
   NaN cosine similarities (divide-by-zero after normalisation) which are
   suppressed as non-matches.  The affected entries appear in RuntimeWarnings
   during the dedup pass.  Estimated impact: <0.1 % of entries.
