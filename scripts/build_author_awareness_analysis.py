"""Author-awareness analysis: does knowing who studies what improve
screening beyond graph content features?

Builds:
1. Author-concept bipartite graph (who studies what)
2. Author-collaboration graph (who co-authors with whom)
3. Author-awareness features for each candidate pair
4. Tests these features in the reranker benchmark
5. Identifies "alien" candidates (high graph score, no author positioned)

Inspired by Sourati et al. (2023, Nature Human Behaviour).
"""
from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking

CORPUS_PATH = ROOT / "data/processed/research_allocation_v2/hybrid_corpus.parquet"
AUTHORSHIP_PATH = ROOT / "data/processed/research_allocation_v2/paper_authorships.parquet"
PANEL_PATH = ROOT / "outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet"
FUNDING_PATH = ROOT / "data/processed/research_allocation_v2/hybrid_papers_funding.parquet"
OUT_DIR = ROOT / "outputs/paper/55_author_awareness"
NOTE_PATH = ROOT / "next_steps/author_awareness_note.md"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZON = 10
K_VALUES = [50, 100, 500]


def _safe(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


# ======================================================================= #
# 1. Build author-concept mappings by cutoff year
# ======================================================================= #
def build_author_concept_maps(corpus_df, authorship_df, cutoff_year):
    """Build author->concepts and concept->authors maps for papers through cutoff-1."""
    # Papers through cutoff-1
    funding = pd.read_parquet(FUNDING_PATH)
    paper_years = dict(zip(funding["paper_id"].astype(str), funding["year"].astype(int)))

    # Map work_id -> paper_id
    work_to_paper = dict(zip(funding["openalex_work_id"].astype(str), funding["paper_id"].astype(str)))

    # Filter authorships to papers before cutoff
    auth = authorship_df.copy()
    auth["paper_id_mapped"] = auth["work_id"].map(work_to_paper)
    auth["year"] = auth["paper_id_mapped"].map(paper_years)
    auth = auth[auth["year"] < cutoff_year].copy()

    # Filter corpus to same period
    corp = corpus_df[corpus_df["year"] < cutoff_year].copy()

    # Build paper->concepts map
    paper_concepts = defaultdict(set)
    for _, row in corp.iterrows():
        pid = str(row["paper_id"])
        paper_concepts[pid].add(str(row["src_code"]))
        paper_concepts[pid].add(str(row["dst_code"]))

    # Build author->concepts and concept->authors
    author_concepts = defaultdict(set)
    concept_authors = defaultdict(set)
    author_coauthors = defaultdict(set)

    # Group authorships by paper to get co-authors
    paper_authors = defaultdict(set)
    for _, row in auth.iterrows():
        aid = str(row["author_id"])
        pid = str(row["paper_id_mapped"])
        if pd.isna(pid) or pid == "nan":
            continue
        paper_authors[pid].add(aid)

    for pid, authors in paper_authors.items():
        concepts = paper_concepts.get(pid, set())
        for aid in authors:
            author_concepts[aid].update(concepts)
            for concept in concepts:
                concept_authors[concept].add(aid)
            # Co-authors
            for other_aid in authors:
                if other_aid != aid:
                    author_coauthors[aid].add(other_aid)

    return author_concepts, concept_authors, author_coauthors


# ======================================================================= #
# 2. Compute author-awareness features for candidate pairs
# ======================================================================= #
def compute_author_features(u, v, author_concepts, concept_authors, author_coauthors):
    """Compute author-awareness features for a (u, v) candidate pair."""
    u_authors = concept_authors.get(str(u), set())
    v_authors = concept_authors.get(str(v), set())

    # Feature 1: Direct expertise overlap — authors who have published on BOTH u and v
    overlap = u_authors & v_authors
    direct_overlap_count = len(overlap)

    # Feature 2: Collaboration proximity — is there an author of u who co-authors with an author of v?
    collab_bridge = 0
    if not overlap and u_authors and v_authors:
        for u_auth in u_authors:
            coauths = author_coauthors.get(u_auth, set())
            if coauths & v_authors:
                collab_bridge += 1

    # Feature 3: Expertise density — how many distinct authors have touched either endpoint
    u_author_count = len(u_authors)
    v_author_count = len(v_authors)
    total_expert_pool = len(u_authors | v_authors)

    # Feature 4: Jaccard overlap of author sets
    union = u_authors | v_authors
    author_jaccard = len(overlap) / len(union) if union else 0.0

    # Feature 5: Institution overlap — do authors of u and v share institutions?
    # (would need institution data — skip for now, use author overlap as proxy)

    return {
        "direct_overlap_count": direct_overlap_count,
        "has_overlap": int(direct_overlap_count > 0),
        "collab_bridge_count": collab_bridge,
        "has_collab_bridge": int(collab_bridge > 0),
        "u_author_count": u_author_count,
        "v_author_count": v_author_count,
        "total_expert_pool": total_expert_pool,
        "author_jaccard": author_jaccard,
    }


# ======================================================================= #
# 3. Enrich panel with author features
# ======================================================================= #
def enrich_panel(panel_df, corpus_df, authorship_df):
    """Add author-awareness features to the panel for each (cutoff, u, v)."""
    print("Enriching panel with author-awareness features...")
    t0 = time.time()

    # Cache maps by cutoff year
    cached_maps = {}
    results = []

    for cutoff in sorted(panel_df["cutoff_year_t"].unique()):
        cutoff = int(cutoff)
        if cutoff not in cached_maps:
            print(f"  Building author maps for cutoff {cutoff}...")
            cached_maps[cutoff] = build_author_concept_maps(corpus_df, authorship_df, cutoff)

        author_concepts, concept_authors, author_coauthors = cached_maps[cutoff]

        cutoff_panel = panel_df[panel_df["cutoff_year_t"] == cutoff]
        for _, row in cutoff_panel.iterrows():
            feats = compute_author_features(row["u"], row["v"], author_concepts, concept_authors, author_coauthors)
            feats["cutoff_year_t"] = cutoff
            feats["u"] = str(row["u"])
            feats["v"] = str(row["v"])
            results.append(feats)

    feat_df = pd.DataFrame(results)
    print(f"  Done in {time.time()-t0:.1f}s")
    return feat_df


# ======================================================================= #
# 4. Test author features in the benchmark
# ======================================================================= #
def evaluate_author_features(panel_df, author_feat_df):
    """Evaluate author-awareness features as standalone and combined baselines."""
    print("\nEvaluating author-awareness features...")

    # Merge
    merged = panel_df.merge(author_feat_df, on=["cutoff_year_t", "u", "v"], how="left")
    for col in ["direct_overlap_count", "has_overlap", "collab_bridge_count", "has_collab_bridge",
                 "u_author_count", "v_author_count", "total_expert_pool", "author_jaccard"]:
        merged[col] = _safe(merged[col])

    # Also compute existing baselines
    merged["pa_score"] = _safe(merged["support_degree_product"])
    merged["graph_score_val"] = _safe(merged["transparent_score"] if "transparent_score" in merged.columns else merged["score"])

    # Author-awareness composite: overlap + bridge + jaccard
    merged["author_composite"] = (
        _safe(merged["direct_overlap_count"]) * 3
        + _safe(merged["collab_bridge_count"])
        + _safe(merged["author_jaccard"]) * 10
        + _safe(merged["total_expert_pool"]) * 0.01
    )

    models = {
        "pref_attach": "pa_score",
        "graph_score": "graph_score_val",
        "author_overlap": "direct_overlap_count",
        "author_jaccard": "author_jaccard",
        "author_composite": "author_composite",
        "collab_bridge": "collab_bridge_count",
    }

    metric_rows = []
    for (cutoff, horizon), group in merged.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives = {(str(r.u), str(r.v)) for r in group[group["appears_within_h"].astype(bool)][["u", "v"]].itertuples(index=False)}
        if not positives:
            continue
        for mname, mcol in models.items():
            ranked = group[["u", "v", mcol]].rename(columns={mcol: "score"}).sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
            ranked["rank"] = ranked.index + 1
            metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES)
            row = {"model": mname, "cutoff_year_t": int(cutoff), "horizon": int(horizon), "n_positives": len(positives), "mrr": float(metrics.get("mrr", 0.0))}
            for k in K_VALUES:
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
            metric_rows.append(row)

    metric_df = pd.DataFrame(metric_rows)
    summary = metric_df.groupby(["model", "horizon"], as_index=False).agg(
        mean_p100=("precision_at_100", "mean"), mean_r100=("recall_at_100", "mean"),
        mean_mrr=("mrr", "mean"), mean_hits100=("hits_at_100", "mean"),
    ).sort_values(["horizon", "mean_p100"], ascending=[True, False])

    return merged, metric_df, summary


# ======================================================================= #
# 5. Identify "alien" candidates
# ======================================================================= #
def identify_aliens(merged, panel_df):
    """Find pairs with high graph score but no author positioned."""
    print("\nIdentifying 'alien' candidates...")

    h_panel = merged[merged["horizon"] == HORIZON].copy()
    h_panel["graph_rank"] = h_panel.groupby("cutoff_year_t")["graph_score_val"].rank(ascending=False)

    # Alien = top 500 by graph score AND no direct overlap AND no collab bridge
    aliens = h_panel[
        (h_panel["graph_rank"] <= 500) &
        (h_panel["direct_overlap_count"] == 0) &
        (h_panel["collab_bridge_count"] == 0)
    ]

    # Non-alien = top 500 by graph score AND has overlap or bridge
    non_aliens = h_panel[
        (h_panel["graph_rank"] <= 500) &
        ((h_panel["direct_overlap_count"] > 0) | (h_panel["collab_bridge_count"] > 0))
    ]

    alien_pos_rate = aliens["appears_within_h"].astype(float).mean() if len(aliens) > 0 else 0
    non_alien_pos_rate = non_aliens["appears_within_h"].astype(float).mean() if len(non_aliens) > 0 else 0
    overall_pos_rate = h_panel["appears_within_h"].astype(float).mean()

    print(f"  Aliens (top-500, no author positioned): {len(aliens)}, positive rate: {alien_pos_rate:.3f}")
    print(f"  Non-aliens (top-500, author positioned): {len(non_aliens)}, positive rate: {non_alien_pos_rate:.3f}")
    print(f"  Overall positive rate: {overall_pos_rate:.3f}")

    return {
        "n_aliens": len(aliens),
        "n_non_aliens": len(non_aliens),
        "alien_pos_rate": alien_pos_rate,
        "non_alien_pos_rate": non_alien_pos_rate,
        "overall_pos_rate": overall_pos_rate,
    }


# ======================================================================= #
# MAIN
# ======================================================================= #
def main():
    print("Loading data...")
    corpus_df = pd.read_parquet(CORPUS_PATH)
    authorship_df = pd.read_parquet(AUTHORSHIP_PATH)
    panel_df = pd.read_parquet(PANEL_PATH)
    pool_col = [c for c in panel_df.columns if c.startswith("in_pool_")]
    if pool_col:
        panel_df = panel_df[panel_df[pool_col[0]].astype(bool)]
    panel_df = panel_df[panel_df["horizon"] == HORIZON].copy()
    print(f"  Panel: {len(panel_df)} rows")
    print(f"  Authorships: {len(authorship_df)} rows, {authorship_df['author_id'].nunique()} unique authors")

    # Enrich panel
    author_feat_df = enrich_panel(panel_df, corpus_df, authorship_df)
    author_feat_df.to_parquet(OUT_DIR / "author_features.parquet", index=False)

    # Stats
    print(f"\nAuthor feature stats:")
    for col in ["direct_overlap_count", "has_overlap", "collab_bridge_count", "has_collab_bridge", "author_jaccard"]:
        vals = _safe(author_feat_df[col])
        print(f"  {col:30s}  mean={vals.mean():.4f}  >0: {(vals > 0).sum()} ({(vals > 0).mean()*100:.1f}%)")

    # Evaluate
    merged, metric_df, summary = evaluate_author_features(panel_df, author_feat_df)
    metric_df.to_csv(OUT_DIR / "author_benchmark_panel.csv", index=False)
    summary.to_csv(OUT_DIR / "author_benchmark_summary.csv", index=False)

    print(f"\nBenchmark results (h={HORIZON}):")
    for _, row in summary.iterrows():
        print(f"  {row['model']:25s}  P@100={row['mean_p100']:.6f}  R@100={row['mean_r100']:.6f}  Hits={row['mean_hits100']:.1f}")

    # Aliens
    alien_stats = identify_aliens(merged, panel_df)

    # Write note
    lines = [
        "# Author-Awareness Analysis",
        "",
        "## Data",
        f"- Papers with authors: {authorship_df['work_id'].nunique()}",
        f"- Unique authors: {authorship_df['author_id'].nunique()}",
        f"- Unique institutions: {authorship_df['institution_id'].nunique()}",
        f"- Mean authors per paper: {authorship_df.groupby('work_id').size().mean():.1f}",
        "",
        "## Author feature coverage in candidate panel",
        "",
    ]
    for col in ["has_overlap", "has_collab_bridge"]:
        vals = _safe(author_feat_df[col])
        lines.append(f"- {col}: {(vals > 0).sum()} pairs ({(vals > 0).mean()*100:.1f}%)")
    lines.append("")

    lines.append(f"## Benchmark results (h={HORIZON})")
    lines.append("")
    lines.append("| Model | P@100 | R@100 | MRR | Hits@100 |")
    lines.append("|-------|-------|-------|-----|----------|")
    for _, row in summary.iterrows():
        lines.append(f"| {row['model']} | {row['mean_p100']:.6f} | {row['mean_r100']:.6f} | {row['mean_mrr']:.6f} | {row['mean_hits100']:.1f} |")
    lines.append("")

    lines.append("## Alien candidates (Sourati & Evans parallel)")
    lines.append("")
    lines.append(f"- Aliens (top-500, no author positioned): {alien_stats['n_aliens']}, positive rate: {alien_stats['alien_pos_rate']:.3f}")
    lines.append(f"- Non-aliens (top-500, author positioned): {alien_stats['n_non_aliens']}, positive rate: {alien_stats['non_alien_pos_rate']:.3f}")
    lines.append(f"- Ratio: non-alien positive rate is {alien_stats['non_alien_pos_rate']/max(alien_stats['alien_pos_rate'],0.001):.1f}x higher")
    lines.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(lines) + "\n")

    print(f"\nOutputs: {OUT_DIR}")
    print(f"Note: {NOTE_PATH}")


if __name__ == "__main__":
    main()
