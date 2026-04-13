"""Patch extraction_label_mapping_v2.parquet: fix bad SF exact matches.

Pass 2 in the mapping script accepted 1- and 2-word surface forms as exact
match keys.  Short SFs like "ces", "trade", "insurance" spuriously matched
unrelated ontology entries (e.g. "carbon emissions" → JEL "CES").

Fix: for rows where match_kind is exact_sf/exact_sf_stripped AND the SF used
was < 3 words, re-embed the label and re-run FAISS NN to get a proper match.
All other rows are unchanged.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import faiss
import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

EMBED_MODEL  = "text-embedding-3-small"
EMBED_BATCH  = 500
CONCURRENCY  = 20
STREAM_CHUNK = 10_000
TOP_K        = 3
LINK_THRESH  = 0.85
SOFT_THRESH  = 0.75
FAISS_NLIST  = 1024
FAISS_NPROBE = 64


async def embed_ordered(texts):
    batches = [texts[i:i + EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    sem     = asyncio.Semaphore(CONCURRENCY)
    client  = openai.AsyncOpenAI()

    async def bounded(i, batch):
        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.embeddings.create(model=EMBED_MODEL, input=batch)
                    return [r.embedding for r in resp.data]
                except Exception:
                    if attempt == 2:
                        return [[0.0] * 1536] * len(batch)
                    await asyncio.sleep(1.5 ** attempt)

    results  = await asyncio.gather(*[bounded(i, b) for i, b in enumerate(batches)])
    return np.array([e for batch in results for e in batch], dtype=np.float32)


def normalize(e):
    n = np.linalg.norm(e, axis=1, keepdims=True)
    n[n == 0] = 1
    return e / n


async def main():
    print("=== Patching bad SF exact matches ===\n")

    # Load mapping output
    mapping_path = OUT_DIR / "extraction_label_mapping_v2.parquet"
    df = pd.read_parquet(mapping_path)
    print(f"Loaded: {len(df):,} rows")

    # Identify bad rows: short SF used as exact key
    bad_mask = (
        df["match_kind"].isin(["exact_sf", "exact_sf_stripped"])
        & df["matched_via"].apply(lambda s: len(str(s).split()) < 3)
    )
    bad_idx = df[bad_mask].index.tolist()
    print(f"Bad SF exact rows (SF < 3 words): {len(bad_idx):,}")
    print(f"Sample bad rows:")
    for _, r in df[bad_mask].nlargest(10, "freq").iterrows():
        print(f"  [{r['freq']:4d}]  {r['label']:35s}  via={r['matched_via']!r:20s}  → {r['onto_label']!r} ({r['onto_source']})")

    # Load ontology
    print("\nLoading ontology …")
    onto = json.load(open(OUT_DIR / "ontology_v2_final.json"))
    onto_ids     = [c["id"]            for c in onto]
    onto_labels  = [c["label"]         for c in onto]
    onto_sources = [c.get("source","") for c in onto]
    onto_domains = [c.get("domain","") for c in onto]

    onto_embs = np.load(OUT_DIR / "ontology_v2_label_only_embeddings.npy").astype(np.float32)
    onto_norm = normalize(onto_embs)

    # Build FAISS index
    print("Building FAISS index …")
    d = onto_norm.shape[1]
    quantizer = faiss.IndexFlatIP(d)
    idx_faiss = faiss.IndexIVFFlat(quantizer, d, FAISS_NLIST, faiss.METRIC_INNER_PRODUCT)
    idx_faiss.train(onto_norm)
    idx_faiss.add(onto_norm)
    idx_faiss.nprobe = FAISS_NPROBE
    print(f"  Ready")

    # Embed bad labels in streaming chunks
    bad_labels = [df.at[i, "label"] for i in bad_idx]
    n_bad      = len(bad_labels)
    print(f"\nRe-embedding {n_bad:,} labels …")
    t0 = time.time()

    new_scores  = np.full((n_bad, TOP_K), -1.0, dtype=np.float32)
    new_indices = np.full((n_bad, TOP_K), -1,   dtype=np.int32)

    for cs in range(0, n_bad, STREAM_CHUNK):
        ce    = min(cs + STREAM_CHUNK, n_bad)
        chunk = bad_labels[cs:ce]
        embs  = await embed_ordered(chunk)
        qnorm = normalize(embs)
        sc, si = idx_faiss.search(qnorm, TOP_K)
        new_scores[cs:ce]  = sc
        new_indices[cs:ce] = si
        elapsed = time.time() - t0
        print(f"  {ce:,}/{n_bad:,} ({ce/elapsed:.0f}/s)")

    print(f"Done in {time.time()-t0:.1f}s")

    # Update dataframe
    def safe(arr, i): return arr[i] if i >= 0 else None

    for local_j, global_i in enumerate(bad_idx):
        s1 = float(new_scores[local_j, 0])
        i1 = int(new_indices[local_j, 0])
        df.at[global_i, "onto_id"]     = safe(onto_ids,     i1)
        df.at[global_i, "onto_label"]  = safe(onto_labels,  i1)
        df.at[global_i, "onto_source"] = safe(onto_sources, i1)
        df.at[global_i, "onto_domain"] = safe(onto_domains, i1)
        df.at[global_i, "score"]       = s1
        df.at[global_i, "matched_via"] = "label"
        df.at[global_i, "match_kind"]  = "embedding" if s1 >= SOFT_THRESH else "unmatched"
        if TOP_K > 1:
            i2 = int(new_indices[local_j, 1])
            df.at[global_i, "rank2_id"]    = safe(onto_ids,    i2)
            df.at[global_i, "rank2_label"] = safe(onto_labels, i2)
            df.at[global_i, "rank2_score"] = float(new_scores[local_j, 1])
        if TOP_K > 2:
            i3 = int(new_indices[local_j, 2])
            df.at[global_i, "rank3_id"]    = safe(onto_ids,    i3)
            df.at[global_i, "rank3_label"] = safe(onto_labels, i3)
            df.at[global_i, "rank3_score"] = float(new_scores[local_j, 2])

    # Stats after patch
    has_score = df["score"].notna()
    linked    = df[has_score & (df["score"] >= LINK_THRESH)]
    soft      = df[has_score & (df["score"] >= SOFT_THRESH) & (df["score"] < LINK_THRESH)]
    unmatched = df[~has_score | (df["score"] < SOFT_THRESH)]
    total_occ = df["freq"].sum()

    print(f"\n=== Results after patch ===")
    print(f"Total: {len(df):,} labels, {total_occ:,} occurrences")
    print(f"  Linked   (>=0.85): {len(linked):,} ({len(linked)/len(df)*100:.1f}%)  "
          f"{linked['freq'].sum():,} occ ({linked['freq'].sum()/total_occ*100:.1f}%)")
    print(f"  Soft     (0.75-0.85): {len(soft):,} ({len(soft)/len(df)*100:.1f}%)  "
          f"{soft['freq'].sum():,} occ ({soft['freq'].sum()/total_occ*100:.1f}%)")
    print(f"  Unmatched (<0.75): {len(unmatched):,} ({len(unmatched)/len(df)*100:.1f}%)  "
          f"{unmatched['freq'].sum():,} occ ({unmatched['freq'].sum()/total_occ*100:.1f}%)")

    print(f"\nMatch kind breakdown:")
    print(df["match_kind"].value_counts().to_string())

    print(f"\nSample high-freq patched rows:")
    patched = df.loc[bad_idx].nlargest(15, "freq")
    for _, r in patched.iterrows():
        print(f"  [{r['score']:.3f}|{r['match_kind']:12s}] {r['label']!r:35s} → {r['onto_label']!r} ({r['onto_source']})")

    df.to_parquet(mapping_path, index=False)
    print(f"\nSaved patched output → {mapping_path}")
    print("=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
