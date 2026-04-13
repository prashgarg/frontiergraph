"""Re-align production concepts using label-only embeddings for both sides.

The first alignment pass embedded vocabulary as "label: description" which
biased similarity scores downward even for identical labels. This pass embeds
ONLY labels on both sides for a fair comparison.

Also does analysis to understand what's truly unlinked vs. vocabulary gap.
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
TOP_K = 5


async def embed_batch(client, texts, sem):
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
                return [item.embedding for item in resp.data]
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
        return [[0.0] * 1536] * len(texts)


async def embed_all(texts, label=""):
    client = openai.AsyncOpenAI()
    sem = asyncio.Semaphore(CONCURRENCY)
    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  Embedding {len(texts):,} {label} texts in {len(batches)} batches...")
    t0 = time.time()
    completed = 0

    async def bounded(batch):
        nonlocal completed
        result = await embed_batch(client, batch, sem)
        completed += 1
        if completed % 10 == 0:
            print(f"    {completed}/{len(batches)} ({time.time()-t0:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(b) for b in batches])
    flat = [e for batch_result in results for e in batch_result]
    print(f"  Done in {time.time()-t0:.1f}s")
    return np.array(flat, dtype=np.float32)


def normalize(embs):
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return embs / norms


async def main():
    print("=== Label-only alignment: production → merged vocabulary ===\n")

    # Load data
    canon_df = pd.read_parquet(PROCESSED_DIR / "canonical_concepts.parquet")
    with open(OUT_DIR / "ontology_candidates.json") as f:
        merged_items = json.load(f)

    print(f"Production concepts: {len(canon_df):,}")
    print(f"Merged vocabulary: {len(merged_items):,} items")

    prod_labels = canon_df["preferred_label"].tolist()
    prod_ids = canon_df["concept_id"].tolist()
    vocab_labels = [item["label"] for item in merged_items]

    # Embed labels only
    print()
    prod_embs = await embed_all(prod_labels, "production")
    vocab_embs = await embed_all(vocab_labels, "vocabulary")

    # Save vocab label-only embeddings
    np.save(OUT_DIR / "ontology_label_embeddings.npy", vocab_embs)

    # Normalize
    prod_norm = normalize(prod_embs)
    vocab_norm = normalize(vocab_embs)

    # Nearest-neighbor search
    print("\nSearching for nearest neighbors...")
    chunk_size = 500
    all_topk_indices = []
    all_topk_scores = []
    t0 = time.time()

    for start in range(0, len(prod_norm), chunk_size):
        batch = prod_norm[start:start+chunk_size]
        sims = batch @ vocab_norm.T
        topk_idx = np.argsort(sims, axis=1)[:, -TOP_K:][:, ::-1]
        topk_sim = np.take_along_axis(sims, topk_idx, axis=1)
        all_topk_indices.append(topk_idx)
        all_topk_scores.append(topk_sim)

    all_topk_indices = np.vstack(all_topk_indices)
    all_topk_scores = np.vstack(all_topk_scores)
    print(f"  Done in {time.time()-t0:.1f}s")

    # Analyze score distribution at multiple thresholds
    scores = all_topk_scores[:, 0]  # best score for each production concept
    print(f"\nBest-match score distribution (label-only embeddings):")
    for threshold in [0.99, 0.97, 0.95, 0.93, 0.90, 0.87, 0.85, 0.80, 0.75, 0.70]:
        n = int((scores >= threshold).sum())
        print(f"  >= {threshold:.2f}: {n:,} ({n/len(scores)*100:.1f}%)")

    # Build full alignment with multiple threshold views
    aligned = []
    for i, (concept_id, label) in enumerate(zip(prod_ids, prod_labels)):
        best_score = float(all_topk_scores[i, 0])
        best_idx = int(all_topk_indices[i, 0])
        best_item = merged_items[best_idx]

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
            })

        aligned.append({
            "concept_id": concept_id,
            "label": label,
            "instance_support": int(canon_df.iloc[i]["instance_support"]),
            "best_score": round(best_score, 4),
            "best_match_label": best_item["label"],
            "best_match_source": best_item["source"],
            "best_match_id": best_item["id"],
            "neighbors": neighbors,
        })

    # Detailed examples to understand the alignment quality
    print(f"\n--- High similarity pairs (cos >= 0.98) ---")
    high_sim = sorted([a for a in aligned if a["best_score"] >= 0.98],
                      key=lambda x: -x["best_score"])
    for a in high_sim[:30]:
        print(f"  [{a['best_score']:.3f}] '{a['label']}' → '{a['best_match_label']}' ({a['best_match_source']})")

    print(f"\n--- Medium similarity (0.90-0.97) samples ---")
    med_sim = [a for a in aligned if 0.90 <= a["best_score"] < 0.97]
    import random; random.seed(42)
    for a in random.sample(med_sim, min(20, len(med_sim))):
        print(f"  [{a['best_score']:.3f}] '{a['label']}' → '{a['best_match_label']}' ({a['best_match_source']})")

    print(f"\n--- Low similarity (<0.75), high support ---")
    low_high = sorted([a for a in aligned if a["best_score"] < 0.75],
                      key=lambda x: -x["instance_support"])[:20]
    for a in low_high:
        print(f"  [{a['best_score']:.3f}|support={a['instance_support']:,}] "
              f"'{a['label']}' → '{a['best_match_label']}'")

    # What fraction of production concepts have an exact or near-exact match?
    thresholds = [0.99, 0.97, 0.95, 0.93, 0.90, 0.85, 0.80, 0.75]
    print(f"\n--- What fraction of PAPER-SUPPORT is covered at each threshold? ---")
    total_support = sum(a["instance_support"] for a in aligned)
    for thr in thresholds:
        covered = sum(a["instance_support"] for a in aligned if a["best_score"] >= thr)
        n = sum(1 for a in aligned if a["best_score"] >= thr)
        print(f"  >= {thr:.2f}: {n:,} concepts ({n/len(aligned)*100:.1f}%), "
              f"{covered:,} paper-mentions ({covered/total_support*100:.1f}% of support)")

    # Save
    out_path = OUT_DIR / "production_alignment_labelonly.json"
    with open(out_path, "w") as f:
        json.dump(aligned, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
