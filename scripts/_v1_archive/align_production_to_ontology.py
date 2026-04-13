"""Align the 6,752 production FG3C concepts to the new 28,523-item merged vocabulary.

For each production concept:
  1. Embed its preferred label.
  2. Find top-K nearest neighbors in the merged vocabulary embeddings.
  3. If cosine ≥ 0.85 → linked (the concept maps to a reference vocab item).
  4. If cosine < 0.85 → unlinked (concept is too specific / novel).

Produces:
  - data/ontology_v2/production_alignment.json — full alignment results
  - data/ontology_v2/alignment_summary.json    — stats and coverage breakdown

Also shows what the new vocab ADDS on top of the production concepts.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"
PROCESSED_DIR = ROOT / "data/processed/ontology_vnext_proto_v1"

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 500
CONCURRENCY = 20
LINK_THRESHOLD = 0.85    # cos ≥ this → linked
SOFT_THRESHOLD = 0.75    # cos ≥ this → soft link (close but imperfect)
TOP_K = 5               # store top-5 neighbors for each concept


# ── Embed ─────────────────────────────────────────────────────────────────────

async def embed_batch(client: openai.AsyncOpenAI, texts: list[str], sem: asyncio.Semaphore) -> list[list[float]]:
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
                return [item.embedding for item in resp.data]
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
        return [[0.0] * 1536] * len(texts)


async def embed_all(texts: list[str]) -> np.ndarray:
    client = openai.AsyncOpenAI()
    sem = asyncio.Semaphore(CONCURRENCY)
    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  Embedding {len(texts):,} texts in {len(batches)} batches...")
    t0 = time.time()
    completed = 0

    async def bounded(batch):
        nonlocal completed
        result = await embed_batch(client, batch, sem)
        completed += 1
        if completed % 5 == 0:
            print(f"    {completed}/{len(batches)} batches ({time.time()-t0:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(b) for b in batches])
    flat = [e for batch_result in results for e in batch_result]
    print(f"  Done in {time.time()-t0:.1f}s")
    return np.array(flat, dtype=np.float32)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=== Aligning production concepts to merged vocabulary ===\n")

    # 1. Load production concepts
    canon_df = pd.read_parquet(PROCESSED_DIR / "canonical_concepts.parquet")
    print(f"Production concepts: {len(canon_df):,}")

    prod_labels = canon_df["preferred_label"].tolist()
    prod_ids = canon_df["concept_id"].tolist()

    # 2. Load merged vocabulary
    with open(OUT_DIR / "ontology_candidates.json") as f:
        merged_items = json.load(f)
    merged_embs = np.load(OUT_DIR / "ontology_candidate_embeddings.npy")
    print(f"Merged vocabulary: {len(merged_items):,} items")

    # L2-normalize merged embeddings for cosine similarity
    norms = np.linalg.norm(merged_embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    merged_norm = merged_embs / norms

    # 3. Embed production labels
    print("\nEmbedding production concept labels...")
    prod_embs = await embed_all(prod_labels)
    prod_norms = np.linalg.norm(prod_embs, axis=1, keepdims=True)
    prod_norms[prod_norms == 0] = 1
    prod_norm = prod_embs / prod_norms

    # 4. Nearest-neighbor search: each production concept → top-K in merged vocab
    print("\nSearching for nearest neighbors...")
    t0 = time.time()

    chunk_size = 500
    all_topk_indices = []
    all_topk_scores = []

    for start in range(0, len(prod_norm), chunk_size):
        batch = prod_norm[start:start+chunk_size]        # (B, D)
        sims = batch @ merged_norm.T                      # (B, N)
        topk_idx = np.argsort(sims, axis=1)[:, -TOP_K:][:, ::-1]
        topk_sim = np.take_along_axis(sims, topk_idx, axis=1)
        all_topk_indices.append(topk_idx)
        all_topk_scores.append(topk_sim)

    all_topk_indices = np.vstack(all_topk_indices)
    all_topk_scores = np.vstack(all_topk_scores)
    print(f"  Done in {time.time()-t0:.1f}s")

    # 5. Build alignment records
    print("\nBuilding alignment records...")
    aligned = []
    for i, (concept_id, label) in enumerate(zip(prod_ids, prod_labels)):
        best_score = float(all_topk_scores[i, 0])
        best_idx = int(all_topk_indices[i, 0])
        best_item = merged_items[best_idx]

        # Top-K neighbors
        neighbors = []
        for k in range(TOP_K):
            k_idx = int(all_topk_indices[i, k])
            k_sim = float(all_topk_scores[i, k])
            k_item = merged_items[k_idx]
            neighbors.append({
                "rank": k + 1,
                "score": round(k_sim, 4),
                "label": k_item["label"],
                "source": k_item["source"],
                "id": k_item["id"],
                "description": k_item.get("description", "")[:100],
            })

        # Link status
        if best_score >= LINK_THRESHOLD:
            link_status = "linked"
        elif best_score >= SOFT_THRESHOLD:
            link_status = "soft_link"
        else:
            link_status = "unlinked"

        aligned.append({
            "concept_id": concept_id,
            "label": label,
            "instance_support": int(canon_df.iloc[i]["instance_support"]),
            "link_status": link_status,
            "best_score": round(best_score, 4),
            "best_match_label": best_item["label"],
            "best_match_source": best_item["source"],
            "best_match_id": best_item["id"],
            "neighbors": neighbors,
        })

    # 6. Statistics
    from collections import Counter

    link_counts = Counter(a["link_status"] for a in aligned)
    print(f"\n--- Alignment Stats ---")
    print(f"Total production concepts: {len(aligned):,}")
    for status in ["linked", "soft_link", "unlinked"]:
        n = link_counts[status]
        print(f"  {status}: {n:,} ({n/len(aligned)*100:.1f}%)")

    # Score distribution
    scores = [a["best_score"] for a in aligned]
    print(f"\nBest-match score distribution:")
    for threshold in [0.99, 0.95, 0.93, 0.90, 0.87, 0.85, 0.80, 0.75, 0.70]:
        n = sum(1 for s in scores if s >= threshold)
        print(f"  >= {threshold:.2f}: {n:,} ({n/len(scores)*100:.1f}%)")

    # Best source breakdown for linked
    linked_items = [a for a in aligned if a["link_status"] == "linked"]
    src_counts = Counter(a["best_match_source"] for a in linked_items)
    print(f"\nLinked to source:")
    for src, n in src_counts.most_common():
        print(f"  {src}: {n:,}")

    # Sample good links
    print(f"\nSample linked concepts (cos >= 0.90):")
    high_linked = sorted([a for a in aligned if a["best_score"] >= 0.90],
                          key=lambda x: -x["best_score"])[:20]
    for a in high_linked:
        print(f"  [{a['best_score']:.3f}] {a['label']} → {a['best_match_label']} ({a['best_match_source']})")

    # Sample soft links
    print(f"\nSample soft links (0.75-0.85):")
    soft = [a for a in aligned if a["link_status"] == "soft_link"]
    import random; random.seed(42)
    for a in random.sample(soft, min(15, len(soft))):
        print(f"  [{a['best_score']:.3f}] {a['label']} → {a['best_match_label']} ({a['best_match_source']})")

    # Sample unlinked
    print(f"\nSample unlinked concepts (cos < 0.75):")
    unlinked = [a for a in aligned if a["link_status"] == "unlinked"]
    high_support_unlinked = sorted(unlinked, key=lambda x: -x["instance_support"])[:20]
    for a in high_support_unlinked:
        print(f"  [support={a['instance_support']}] {a['label']} → best: {a['best_match_label']} ({a['best_score']:.3f})")

    # 7. What does the merged vocab ADD beyond production?
    print(f"\n--- New vocabulary coverage ---")
    # Find merged items NOT linked to any production concept
    matched_indices = set(int(all_topk_indices[i, 0]) for i in range(len(aligned))
                          if float(all_topk_scores[i, 0]) >= LINK_THRESHOLD)
    total_merged = len(merged_items)
    new_items = [merged_items[i] for i in range(total_merged) if i not in matched_indices]
    print(f"  Merged vocab total: {total_merged:,}")
    print(f"  Already covered by production: {len(matched_indices):,}")
    print(f"  Genuinely new concepts: {len(new_items):,}")

    new_src_counts = Counter(item["source"] for item in new_items)
    print(f"\n  New by source:")
    for src, n in new_src_counts.most_common():
        print(f"    {src}: {n:,}")

    # Sample new items
    print(f"\n  Sample new concepts from each source:")
    for src in ["wikidata", "jel", "openalex_topic", "openalex_keyword"]:
        src_new = [item for item in new_items if item["source"] == src]
        if src_new:
            import random
            samples = random.sample(src_new, min(5, len(src_new)))
            print(f"  {src}:")
            for item in samples:
                desc = item.get("description", "")[:60]
                print(f"    {item['label']} — {desc}")

    # 8. Save results
    out_path = OUT_DIR / "production_alignment.json"
    with open(out_path, "w") as f:
        json.dump(aligned, f, indent=2, ensure_ascii=False)
    print(f"\nAlignment saved to {out_path}")

    summary = {
        "total_production": len(aligned),
        "linked": link_counts["linked"],
        "soft_link": link_counts["soft_link"],
        "unlinked": link_counts["unlinked"],
        "total_merged": total_merged,
        "already_covered": len(matched_indices),
        "genuinely_new": len(new_items),
        "new_by_source": dict(new_src_counts),
    }
    summary_path = OUT_DIR / "alignment_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to {summary_path}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
