# Paper Incubation — Branch: paper-incubation

## What This Branch Is
`paper-incubation` was a dedicated work stream for improving `paper/research_allocation_paper.tex`
(the academic paper on FrontierGraph methodology and the learned reranker).  All changes are
in the working tree — nothing has been committed to the branch.

## Paper File
`paper/research_allocation_paper.tex` — 1,405 lines as of 2026-04-08.

Structure:
1. Introduction (line 75)
2. Related Literature and Positioning (line 91)
3. Corpus, Paper-Local Extraction, and Node Normalization (line 127)
4. Direct-Edge Retrieval Anchors, Surfaced Questions, and Evaluation Design (line 299)
5. What the Benchmark Shows (line 571)
6. Discussion and Conclusion (line 755)
Appendices:
- Paper-local graph extraction (line 786)
- Node normalization and ontology construction (line 881)  ← NEEDS V2 REWRITE
- Benchmark construction and significance (line 949)
- Learned reranker design (line 1030)
- Heterogeneity atlas extensions (line 1236)
- Credibility audit summaries (line 1327)
- Path-evolution extensions (line 1378)

## What the Paper-Incubation Agent Did

### Reranker section (Section 5.2, line 595)
Fully written. The reranker reaches precision@100 of 0.222 at h=5 vs 0.160 for
degree+recency. Feature-set decomposition: directed-only (0.204) vs co-occurrence-only
(0.168). Confirmed directed causal degree is the primary signal.

### SHAP / grouped feature decomposition (Section 5.2, line 607 + Appendix line 1135)
Plan: `~/.claude/plans/federated-singing-pie.md` — **FULLY IMPLEMENTED**

- Main text paragraph (line 607): "A Shapley-value decomposition of the reranker's
  predictions reveals what the model is actually learning…" — describes grouped
  feature importance, negative coefficient on support degree, directed causal degree dominates.
- Appendix "What the reranker learns" (line 1135): full section with grouped SHAP figure
  (`grouped_shap_importance.png`), multi-model comparison (`grouped_multi_model.png`),
  VIF comparison (`vif_comparison.png`), beeswarm (`grouped_beeswarm.png`),
  correlation matrix (`grouped_correlation.png`).
- Figures at `outputs/paper/54_grouped_shap/` and `outputs/paper/52_hypothesis_discovery/`
- graphicspath updated to include both directories.

### Other analyses built (all scripts in `scripts/`)
- `build_feature_decomposition.py` — feature-set decomposition figures
- `build_grouped_shap_analysis.py` — grouped SHAP figures
- `build_shap_robustness.py` — SHAP robustness figures
- `build_hypothesis_figures.py`, `run_hypothesis_discovery.py` — hypothesis discovery
- `build_extended_analyses.py`, `build_regime_split_analyses.py` — heterogeneity atlas
- `build_human_validation_materials.py` — validation pack
- `build_single_feature_importance.py` — single-feature ablation table
- Many others in `scripts/build_*.py`

## Active Plan Files (in ~/.claude/plans/)
These plans may be pending or may have been executed — check each before acting:
- `federated-singing-pie.md`: SHAP/hypothesis discovery → **IMPLEMENTED** (see above)
- `moonlit-mapping-lightning.md`: "Four major pushes to populate remaining placeholders"
- `abundant-leaping-gizmo.md`: "Integrate Full 8,500-Item Pilot Results Into paper_v1"
- `reflective-cuddling-bentley.md`: "Sandbox of Ideas — Four New Paper Drafts"
- `swirling-dreaming-fog.md`: "External Productivity Validation (OECD STAN)"
- `velvety-knitting-hopcroft.md`: "Enke & Graeber worked example in Benchmark Selection"

Before picking up paper-incubation work, read each plan file and verify whether the
described changes are in the .tex file before executing.

## Key Thing That Still Needs Doing
**The ontology appendix (lines 881–947) still describes the FG3C/v1 pipeline.**
It references `FG3C...` concept IDs, head-pool construction, force-mapped tail, etc.
This needs to be replaced with a description of the v2 ontology pipeline once the
unmatched-rate decision is resolved (see PAPER_INCUBATION_V2ONTOLOGY.md).

## How To Resume
1. Check out or stay on `paper-incubation-v2ontology` (the v2 ontology work is also here)
2. Read `~/.claude/plans/moonlit-mapping-lightning.md` — likely the next pending plan
3. Compile the paper: `cd paper && tectonic research_allocation_paper.tex`
4. Review the section that needs the most work before each change
