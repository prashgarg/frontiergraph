# v2.1 Promotion And Downstream Status

## What We Did

We promoted stable round-3 `propose_new_concept_family` decisions into a conservative ontology `v2.1`, rebuilt the extraction-to-ontology mapping from the reviewed round-3 decisions, materialized a new ontology sqlite, rebuilt the normalized hybrid corpus, reran funding enrichment, reran learned reranker tuning, and materialized a new current frontier.

This was an overlay-aware promotion pass, not a fresh embedding/FAISS rematch from scratch.

## Core Artifacts

- base reviewed grounding: `data/ontology_v2/extraction_label_grounding_v2_reviewed_round3.parquet`
- reviewed overlay: `data/ontology_v2/ontology_enrichment_overlay_v2_reviewed_round3.parquet`
- promoted families: `data/ontology_v2/ontology_v2_1_promoted_families.parquet`
- ontology `v2.1`: `data/ontology_v2/ontology_v2_1.json`
- rematerialized mapping: `data/ontology_v2/extraction_label_mapping_v2_1.parquet`
- ontology sqlite: `data/production/frontiergraph_ontology_v2_1/ontology_v2_1.sqlite`
- new hybrid corpus: `data/processed/research_allocation_v2_1/hybrid_corpus.parquet`
- new hybrid papers: `data/processed/research_allocation_v2_1/hybrid_papers.parquet`
- new funding-enriched papers: `data/processed/research_allocation_v2_1/hybrid_papers_funding.parquet`
- reranker tuning: `outputs/paper/52_v2_1_learned_reranker_tuning/`
- current frontier: `outputs/paper/53_current_reranked_frontier_v2_1/`

## Promotion Rule

We promoted a reviewed new-family label into ontology `v2.1` when:

- it did not already exactly overlap an existing ontology label, and
- it satisfied at least one of:
  - `row_support >= 2`
  - `freq_support >= 50`
  - decision source included `remaining_hard_modal_review`
  - decision source included `remaining_manual_override_review`

This rule is intentionally conservative, but it still promotes some generic family labels when support is strong.

## v2.1 Counts

From `data/ontology_v2/ontology_v2_1_promotion_note.md`:

- base ontology size: `153,800`
- promoted family candidates considered: `13,739`
- promoted family nodes added: `767`
- ontology `v2.1` size: `154,567`

Mapping action counts in `data/ontology_v2/extraction_label_mapping_v2_1.parquet`:

- `carry_forward_base_mapping`: `1,349,818`
- `attach_existing_broad`: `21,725`
- `unpromoted_family`: `12,972`
- `add_alias_to_existing`: `2,354`
- `promoted_family`: `1,265`
- `keep_unresolved`: `932`
- `reject_cluster`: `841`

## Ontology SQLite

From `data/ontology_v2/ontology_v2_1_sqlite_note.md`:

- ontology rows: `154,567`
- head concepts rows: `154,567`
- node instance mappings: `1,762,898`
- mapped node instances: `1,709,960`
- promoted family rows in ontology: `767`
- context fingerprints: `59,267`

Node-instance mapping action counts:

- `carry_forward_base_mapping`: `1,596,097`
- `attach_existing_broad`: `84,726`
- `unpromoted_family`: `38,380`
- `add_alias_to_existing`: `18,302`
- `promoted_family`: `10,839`
- `reject_cluster`: `8,655`
- `keep_unresolved`: `5,899`

## New Hybrid Corpus

Old corpus manifest:

- benchmark papers: `230,479`
- hybrid rows: `1,271,014`
- directed rows: `89,737`
- undirected rows: `1,181,277`
- unique concepts: `6,752`
- unique directed pairs: `78,167`
- unique undirected pairs: `705,514`

New `v2.1` corpus manifest:

- benchmark papers: `228,801`
- hybrid rows: `1,241,854`
- directed rows: `86,000`
- undirected rows: `1,155,854`
- unique concepts: `57,989`
- unique directed pairs: `75,772`
- unique undirected pairs: `976,385`

Interpretation:

- the corpus shrinks slightly in papers and rows
- the concept universe expands massively because promoted family nodes and broader/open-world grounding preserve much more semantic variation
- undirected distinct pair count increases sharply, consistent with less over-collapse

## Funding Enrichment

From `outputs/paper/50_v2_1_funding/funding_manifest.json`:

- benchmark papers: `228,801`
- papers with grants: `26,027`
- grant coverage rate: `0.1138`
- directed-causal papers: `22,826`
- directed-causal papers with grants: `4,412`
- undirected-noncausal papers: `219,481`
- undirected-noncausal papers with grants: `24,158`

## Transparent Model Search Limitation

The existing transparent `model_search` code is not scale-safe on `v2.1`.

Reason:

- `src.analysis.model_search` still builds an all-pairs universe over all grounded nodes
- at `57,989` concepts this explodes combinatorially
- the process died before producing outputs

Practical consequence:

- for this pass, downstream reranker scripts used a base candidate config written to `outputs/paper/51_v2_1_model_search/best_config.yaml`
- this is a pragmatic placeholder, not a freshly re-estimated transparent optimum on `v2.1`

This should be fixed before claiming a full transparent-model rerun on `v2.1`.

## Learned Reranker Tuning

Old best tuned variants from `outputs/paper/24_learned_reranker_tuning_patch_v2/tuning_best_configs.csv`:

- horizon `5`: `glm_logit + boundary_gap`, `alpha=0.01`, `MRR=0.006739`, `Recall@100=0.071850`
- horizon `10`: `pairwise_logit + composition`, `alpha=0.10`, `MRR=0.006245`, `Recall@100=0.062955`

New `v2.1` best tuned variants from `outputs/paper/52_v2_1_learned_reranker_tuning/tuning_best_configs.csv`:

- horizon `5`: `pairwise_logit + composition`, `alpha=0.20`, `MRR=0.015867`, `Recall@100=0.107298`
- horizon `10`: `glm_logit + structural`, `alpha=0.20`, `MRR=0.009707`, `Recall@100=0.101054`

Interpretation:

- tuned reranker quality improves materially on the `v2.1` corpus
- the preferred feature family changes
- composition wins at `h=5`
- structural wins at `h=10`
- v2.1 looks more learnable than the earlier over-collapsed graph

## Current Frontier

New frontier outputs:

- `outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.parquet`
- `outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.csv`
- `outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier_summary.csv`

New frontier summary:

- horizon `5`: `pairwise_logit + composition`, `alpha=0.2`
- horizon `10`: `glm_logit + structural`, `alpha=0.2`

Top-100 overlap versus prior `patch_v2` frontier:

- overlap: `0 / 100`

This confirms the ontology promotion materially changes the frontier.

## Important New Ranking Pathology

The new frontier shows heavy concentration on a few destination labels, especially:

- `Willingness to pay`
- `Carbon dioxide`
- `R&D`
- `Total factor productivity`
- `Green innovation`

Within the top 20, `Willingness to pay` appears `10` times.
Within the top 100, it appears `14` times.

This is not automatically wrong, but it is a warning sign. It suggests `v2.1` preserved structure better while also exposing a new ranking concentration problem around broad or flexible endpoint labels.

## What This Means

Good news:

- `v2.1` promotion worked
- open-world grounding now propagates into the actual benchmark corpus
- the reranker performs better on the new corpus
- within-graph semantic richness is much higher than before

Open problems:

- transparent `model_search` does not scale to `v2.1` as currently written
- some promoted family nodes are still generic
- the current reranked frontier appears to have a new endpoint concentration pathology

## Recommended Next Steps

1. Make transparent `model_search` scale-safe on the `v2.1` concept universe.
2. Add concentration diagnostics and penalties for flexible endpoint sinks such as `Willingness to pay`.
3. Review the `767` promoted family nodes and split:
   - clearly good family promotions
   - generic promotions that should be demoted or merged
4. Rerun the frontier after endpoint-concentration controls are in place.
5. Only then treat `v2.1` as the default benchmark graph for paper-facing results.
