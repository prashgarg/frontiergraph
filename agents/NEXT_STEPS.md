# Next Steps — Updated 2026-04-08

## Immediate Priority: V2 Ontology → Paper

### 1. Decide unmatched threshold strategy (USER DECISION needed)
The mapping has 77.2% unmatched labels (68.6% of occurrences). Options:
- Add 0.65 "candidate" tier — covers common compound phrases without new API cost
- Accept gap as-is — use 31.4% matched occurrences
- Targeted ontology enrichment — add top-N compound terms, re-embed

Recommendation: add 0.65 candidate tier, keep 0.75 as primary soft tier.
This is the blocker for Step 2.

### 2. Rewrite paper Appendix — Node normalization (lines 881–947)
`paper/research_allocation_paper.tex`

Current: FG3C-era head-pool / force-map / pending-label pipeline.
Replace with: v2 ontology description (5 sources, embeddings, FAISS matching, tiers).

Source material: `data/ontology_v2/ontology_design_decisions.md` has everything.
Key numbers to include:
- 153,800 concepts, 5 sources
- Wikipedia BFS depth-5, gpt-4.1-nano classifier at 72.3% acceptance
- 3-tier description enrichment (41.8% Wikidata + 4.7% Wikipedia + 31.7% LLM)
- FAISS IVFFlat, streaming 10K chunks
- Linked 6.6%, soft 16.1%, candidate (if chosen) ~X% at 0.65

### 3. Update paper Section 3.3 — Node normalization (line 267)
Remove FG3C concept ID references, update counts for v2 ontology.

### 4. Commit v2 ontology work on paper-incubation-v2ontology
After paper sections are drafted. Key untracked directories to commit:
- `data/ontology_v2/` (except large .npy files — likely .gitignored)
- `scripts/map_extraction_labels_to_ontology_v2.py`
- `scripts/patch_sf_exact_matches.py`
- `scripts/build_ontology_v2.py` and related ontology build scripts

## Parallel Priority: Paper-Incubation Pending Plans

Read each plan file before acting — some may already be implemented:
- `~/.claude/plans/moonlit-mapping-lightning.md` — "Four major pushes to populate
  remaining placeholders" — likely the next pending paper improvement
- `~/.claude/plans/swirling-dreaming-fog.md` — OECD STAN productivity validation
- `~/.claude/plans/velvety-knitting-hopcroft.md` — Enke & Graeber worked example

`federated-singing-pie.md` (SHAP) is already implemented. Always check .tex before
executing a plan.

## After Paper Is Updated

### 5. Rebuild concept graph / benchmark using v2 mapping
Once the paper's methodology section describes v2:
- Build candidate universe from `extraction_label_mapping_v2.parquet`
- Recompute ranking signals (path support, gap, hub penalties)
- Rerun reranker evaluation against v2-mapped graph
- Update benchmark tables in paper (Sections 5.1–5.4)

### 6. Update live product
- Build new app DB from v2-mapped concept graph
- Deploy to Cloud Run
- Update frontiergraph.com to reference v2 ontology
This is downstream of Step 5.

## Deferred (lower priority)

### 7. Unmatched label enrichment
If targeted ontology enrichment chosen in Step 1:
- Extract top ~5,000 high-frequency unmatched compound terms
- Add to ontology_v2_final.json as a "compound" source tier
- Re-embed and re-run mapping

### 8. Working paper expansion (NBER/CEPR)
Not the current blocker. Return after paper is stable.

### 9. Product UX polish
Homepage/graph/opportunities page simplification. Blocked on v2 data refresh.

## Decision Log
- V2 ontology complete (153,800 concepts) — 2026-04-08
- Label mapping complete with SF patch — 2026-04-08
- Unmatched threshold TBD — pending user decision
- Paper ontology section still FG3C-era — rewrite pending
- SHAP/grouped feature decomposition fully in paper — 2026-04-08
