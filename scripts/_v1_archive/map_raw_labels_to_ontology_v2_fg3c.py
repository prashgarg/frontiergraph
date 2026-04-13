"""Map raw extraction labels to ontology v2 vocabulary.

Takes the 99,431 unique raw labels (with frequencies) from
raw_labels_classified.parquet and finds each label's nearest neighbours
in the 153,800-concept ontology_v2_final.json using cosine similarity of
text-embedding-3-small embeddings.

Two-pass matching:
  Pass 1 – exact string match (case-insensitive): zero cost, catches the
            most frequent labels ("economic growth", "inflation") instantly.
  Pass 2 – embedding nearest-neighbour for the remainder: embeds raw labels
            label-only (matching the style of short extraction labels) and
            computes cosine similarity against the pre-saved ontology
            embeddings (label+description centroids).

Output columns:
  raw_label, freq, type, jel_category    (from input)
  match_kind        exact | embedding | unmatched
  onto_id           ontology concept id
  onto_label        canonical label in ontology
  onto_source       jel | wikidata | openalex_keyword | openalex_topic | wikipedia
  onto_domain       domain string
  score             cosine similarity (1.0 for exact matches)
  rank2_id, rank2_label, rank2_score    second-best match
  rank3_id, rank3_label, rank3_score    third-best match

Thresholds (for paper):
  linked:    score >= 0.85   high-confidence semantic match
  soft_link: 0.75 <= score < 0.85   probable match, manual review recommended
  unmatched: score < 0.75   no reliable ontology anchor

Output: data/ontology_v2/raw_label_mapping_v2.parquet
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
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
LINK_THRESH  = 0.85
SOFT_THRESH  = 0.75
TOP_K        = 3


# ── Embedding helpers ─────────────────────────────────────────────────────────

async def embed_batch(client, texts, sem):
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(
                    model=EMBED_MODEL, input=texts
                )
                return [r.embedding for r in resp.data]
            except Exception:
                if attempt == 2:
                    return [[0.0] * 1536] * len(texts)
                await asyncio.sleep(1.5 ** attempt)


async def embed_all(texts: list[str]) -> np.ndarray:
    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    sem = asyncio.Semaphore(CONCURRENCY)
    client = openai.AsyncOpenAI()
    t0 = time.time()
    print(f"  Embedding {len(texts):,} texts in {len(batches):,} batches...")
    tasks = [embed_batch(client, b, sem) for b in batches]
    results = []
    done = 0
    for coro in asyncio.as_completed(tasks):
        batch_embs = await coro
        results.append(batch_embs)
        done += 1
        if done % 20 == 0:
            elapsed = time.time() - t0
            eta = (len(batches) - done) / (done / elapsed) if done else 0
            print(f"    {done}/{len(batches)} ({done/elapsed:.1f}/s, ETA {eta:.0f}s)")
    # Flatten in original order — as_completed scrambles; reorder by task index
    # We need order-preserving here, so use gather instead
    return None  # placeholder — see below


async def embed_all_ordered(texts: list[str]) -> np.ndarray:
    """Order-preserving embedding (uses gather, not as_completed)."""
    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    sem = asyncio.Semaphore(CONCURRENCY)
    client = openai.AsyncOpenAI()
    t0 = time.time()
    print(f"  Embedding {len(texts):,} texts in {len(batches):,} batches...")

    async def bounded(i, batch):
        result = await embed_batch(client, batch, sem)
        if (i + 1) % 20 == 0:
            elapsed = time.time() - t0
            eta = (len(batches) - (i+1)) / ((i+1)/elapsed) if (i+1) else 0
            print(f"    {i+1}/{len(batches)} ({(i+1)/elapsed:.1f}/s, ETA {eta:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(i, b) for i, b in enumerate(batches)])
    all_embs = [e for batch in results for e in batch]
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")
    return np.array(all_embs, dtype=np.float32)


def normalize(embs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return embs / norms


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("=== Mapping raw labels → ontology v2 ===\n")

    # Load raw labels
    df = pd.read_parquet(OUT_DIR / "raw_labels_classified.parquet")
    print(f"Raw labels: {len(df):,} unique  ({df['freq'].sum():,} total occurrences)")

    # Load ontology — use extended version (ontology_v2_final + 5,053 FG3C production
    # concepts whose labels were absent from the structured-source vocabulary).
    # The extended ontology was built by extend_ontology_with_production.py.
    # Fall back to base ontology if extended file is not yet built.
    extended_path = OUT_DIR / "ontology_v2_extended.json"
    extended_embs_path = OUT_DIR / "ontology_v2_extended_label_embeddings.npy"
    if extended_path.exists() and extended_embs_path.exists():
        onto = json.load(open(extended_path))
        print(f"Ontology:   {len(onto):,} concepts (extended = base + production)")
        onto_label_cache = extended_embs_path
    else:
        onto = json.load(open(OUT_DIR / "ontology_v2_final.json"))
        print(f"Ontology:   {len(onto):,} concepts (base only — run extend_ontology_with_production.py for extended)")
        onto_label_cache = OUT_DIR / "ontology_v2_label_only_embeddings.npy"

    onto_ids     = [c["id"]            for c in onto]
    onto_labels  = [c["label"]         for c in onto]
    onto_sources = [c.get("source","") for c in onto]
    onto_domains = [c.get("domain","") for c in onto]

    # Embed ontology LABELS ONLY (not label+description).
    # Rationale: raw extraction labels are short strings with no descriptions;
    # using label+description ontology embeddings creates an asymmetry that
    # systematically deflates similarity scores.  "CO2 emissions" (raw) vs
    # "Carbon dioxide emissions: the release of CO2..." (ontology) embeds
    # ~0.70 when label-only would give ~0.95.  Symmetric label-only embeddings
    # give fair comparisons for the nearest-neighbour matching task.
    if onto_label_cache.exists():
        onto_embs = np.load(onto_label_cache).astype(np.float32)
        print(f"Ontology label-only embeddings loaded from cache: {onto_embs.shape}")
    else:
        print("Embedding ontology labels (label-only, first time — cached after this)...")
        onto_embs = await embed_all_ordered(onto_labels)
        np.save(onto_label_cache, onto_embs)
        print(f"Saved label-only embeddings to {onto_label_cache}")
    onto_norm = normalize(onto_embs)

    # Build fast lookup: lowercase label → ontology index
    onto_label_lower = {lbl.lower().strip(): i for i, lbl in enumerate(onto_labels)}

    # ── Pass 1: exact string match ─────────────────────────────────────────
    print("\nPass 1 – exact string match...")
    exact_rows = []
    needs_embed = []

    for _, row in df.iterrows():
        raw = row["label"]
        key = raw.lower().strip()
        if key in onto_label_lower:
            idx = onto_label_lower[key]
            exact_rows.append({
                "raw_label": raw, "freq": row["freq"],
                "type": row["type"], "jel_category": row["jel_category"],
                "match_kind": "exact",
                "onto_id": onto_ids[idx], "onto_label": onto_labels[idx],
                "onto_source": onto_sources[idx], "onto_domain": onto_domains[idx],
                "score": 1.0,
                "rank2_id": None, "rank2_label": None, "rank2_score": None,
                "rank3_id": None, "rank3_label": None, "rank3_score": None,
            })
        else:
            needs_embed.append(row)

    print(f"  Exact matches:  {len(exact_rows):,}")
    print(f"  Need embedding: {len(needs_embed):,}")

    # ── Pass 1.5: parenthetical-strip exact match ──────────────────────────
    # Many raw labels include a trailing parenthetical abbreviation or qualifier:
    #   "environmental regulation (er)" → "environmental regulation"
    #   "developing countries (sample)" → "developing countries"
    #   "money supply (m2)" → "Money Supply"
    # Strip the parenthetical and retry exact match.  Score is 0.99 (not 1.0)
    # to distinguish from true exact matches in downstream analysis.
    print("\nPass 1.5 – parenthetical-strip exact match...")
    _paren_re = re.compile(r"\s*\([^)]+\)\s*$")
    still_needs_embed = []
    strip_rows = []
    for row in needs_embed:
        raw = row["label"]
        stripped = _paren_re.sub("", raw).strip()
        if stripped != raw:
            key = stripped.lower()
            if key in onto_label_lower:
                idx = onto_label_lower[key]
                strip_rows.append({
                    "raw_label": raw, "freq": row["freq"],
                    "type": row["type"], "jel_category": row["jel_category"],
                    "match_kind": "exact_stripped",
                    "onto_id": onto_ids[idx], "onto_label": onto_labels[idx],
                    "onto_source": onto_sources[idx], "onto_domain": onto_domains[idx],
                    "score": 0.99,
                    "rank2_id": None, "rank2_label": None, "rank2_score": None,
                    "rank3_id": None, "rank3_label": None, "rank3_score": None,
                })
                continue
        still_needs_embed.append(row)
    needs_embed = still_needs_embed
    print(f"  Stripped-exact matches: {len(strip_rows):,}")
    print(f"  Still need embedding:   {len(needs_embed):,}")

    # ── Pass 2: embedding nearest-neighbour ───────────────────────────────
    print("\nPass 2 – embedding nearest-neighbour...")
    embed_labels = [r["label"] for r in needs_embed]
    raw_embs = await embed_all_ordered(embed_labels)
    raw_norm = normalize(raw_embs)

    # Batch cosine similarity: raw_norm @ onto_norm.T, top-3 per row
    print(f"  Computing top-{TOP_K} nearest neighbours ({len(needs_embed):,} × {len(onto):,})...")
    t0 = time.time()
    chunk = 500
    top_indices = np.zeros((len(needs_embed), TOP_K), dtype=np.int32)
    top_scores  = np.zeros((len(needs_embed), TOP_K), dtype=np.float32)

    for start in range(0, len(needs_embed), chunk):
        end = min(start + chunk, len(needs_embed))
        sims = raw_norm[start:end] @ onto_norm.T          # (chunk, N_onto)
        # argpartition for efficiency
        for local_i in range(end - start):
            row_sims = sims[local_i]
            best_k = np.argpartition(row_sims, -TOP_K)[-TOP_K:]
            best_k = best_k[np.argsort(row_sims[best_k])[::-1]]
            top_indices[start + local_i] = best_k
            top_scores[start + local_i]  = row_sims[best_k]

        if (start // chunk + 1) % 20 == 0:
            elapsed = time.time() - t0
            n_done = end
            eta = (len(needs_embed) - n_done) / (n_done / elapsed) if n_done else 0
            print(f"    {n_done}/{len(needs_embed)} ({n_done/elapsed:.0f}/s, ETA {eta:.0f}s)")

    print(f"  Done in {time.time()-t0:.1f}s")

    embed_rows = []
    for i, row in enumerate(needs_embed):
        score1 = float(top_scores[i, 0])
        kind = "embedding" if score1 >= SOFT_THRESH else "unmatched"
        idx1, idx2, idx3 = top_indices[i]
        embed_rows.append({
            "raw_label": row["label"], "freq": row["freq"],
            "type": row["type"], "jel_category": row["jel_category"],
            "match_kind": kind,
            "onto_id":     onto_ids[idx1],     "onto_label":  onto_labels[idx1],
            "onto_source": onto_sources[idx1], "onto_domain": onto_domains[idx1],
            "score": score1,
            "rank2_id":    onto_ids[idx2],    "rank2_label": onto_labels[idx2],
            "rank2_score": float(top_scores[i, 1]),
            "rank3_id":    onto_ids[idx3],    "rank3_label": onto_labels[idx3],
            "rank3_score": float(top_scores[i, 2]),
        })

    # ── Combine and save ──────────────────────────────────────────────────
    all_rows = exact_rows + strip_rows + embed_rows
    result = pd.DataFrame(all_rows)
    result = result.sort_values("freq", ascending=False).reset_index(drop=True)

    # Stats
    print(f"\n=== Results ===")
    print(f"Total labels mapped: {len(result):,}")
    linked    = result[result["score"] >= LINK_THRESH]
    soft      = result[(result["score"] >= SOFT_THRESH) & (result["score"] < LINK_THRESH)]
    unmatched = result[result["score"] < SOFT_THRESH]
    print(f"  Linked    (score >= {LINK_THRESH}): {len(linked):,}  ({len(linked)/len(result)*100:.1f}%)")
    print(f"  Soft link ({SOFT_THRESH}–{LINK_THRESH}):     {len(soft):,}  ({len(soft)/len(result)*100:.1f}%)")
    print(f"  Unmatched (score <  {SOFT_THRESH}): {len(unmatched):,}  ({len(unmatched)/len(result)*100:.1f}%)")

    print(f"\nMatch kind breakdown:")
    print(result["match_kind"].value_counts().to_string())

    print(f"\nLinked concepts by source:")
    print(linked["onto_source"].value_counts().to_string())

    print(f"\nTop-20 unmatched by frequency:")
    print(unmatched.nlargest(20, "freq")[["raw_label", "freq", "score", "onto_label"]].to_string())

    print(f"\nSample linked pairs (high freq):")
    for _, r in linked.nlargest(15, "freq").iterrows():
        print(f"  [{r['score']:.3f}] {r['raw_label']!r:35s} → {r['onto_label']!r} ({r['onto_source']})")

    # Save: use _extended suffix if we used the extended ontology
    if extended_path.exists() and extended_embs_path.exists():
        out_path = OUT_DIR / "raw_label_mapping_v2_extended.parquet"
    else:
        out_path = OUT_DIR / "raw_label_mapping_v2.parquet"
    result.to_parquet(out_path, index=False)
    print(f"\nSaved {len(result):,} rows to {out_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
