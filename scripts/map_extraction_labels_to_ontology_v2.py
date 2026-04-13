"""Map LLM-extracted node labels to ontology v2 vocabulary.

Input:   fwci_core150_adj150_extractions.jsonl.gz  (242,595 papers)
         → 1,425,487 unique raw labels, each with surface_forms
Ontology: ontology_v2_final.json  (153,800 structured-source concepts)

Architecture (memory-efficient streaming):
  Exact passes run over the full 1.4M without embedding (just dict lookups).
  Embedding + NN is done in STREAM_CHUNK-sized batches: embed → FAISS search →
  write results → discard embeddings.  Peak RAM ≈ FAISS index (940 MB) +
  one chunk of query embeddings (STREAM_CHUNK × 1536 × 4 bytes, ~48 MB for
  10K labels).

Surface forms:
  Each extracted node has one `label` (LLM canonical form) and N `surface_forms`
  (actual text spans from the paper).  They refer to the SAME concept — a node
  gets ONE ontology mapping, chosen as the best match across label + all SFs.
  Per-SF best matches are stored as sidecar columns for decomposition analysis.

Passes:
  Pass 1  – exact match on normalised label (score = 1.0)
  Pass 2  – exact match on any surface form (score = 0.99)
            also tries parenthetical-stripped label / SF (score = 0.98)
  Pass 3  – streaming embed+NN on label, then upgrade with SF embed+NN

Output: data/ontology_v2/extraction_label_mapping_v2.parquet
"""
from __future__ import annotations

import asyncio
import collections
import gzip
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import faiss

ROOT    = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"
EXTRACT = (
    ROOT
    / "data/production/frontiergraph_extraction_v2"
    / "fwci_core150_adj150/merged"
    / "fwci_core150_adj150_extractions.jsonl.gz"
)

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

EMBED_MODEL   = "text-embedding-3-small"
EMBED_BATCH   = 500       # labels per OpenAI API call
CONCURRENCY   = 20        # parallel API calls
STREAM_CHUNK  = 10_000    # labels to embed + search at once (memory budget)
LINK_THRESH   = 0.85
SOFT_THRESH   = 0.75
TOP_K         = 3
FAISS_NLIST   = 1024
FAISS_NPROBE  = 64

_PAREN_RE = re.compile(r"\s*\([^)]+\)\s*$")

def strip_paren(s: str) -> str:
    return _PAREN_RE.sub("", s).strip()


# ── Embedding ─────────────────────────────────────────────────────────────────

async def embed_batch_async(client, texts, sem):
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
                return [r.embedding for r in resp.data]
            except Exception:
                if attempt == 2:
                    return [[0.0] * 1536] * len(texts)
                await asyncio.sleep(1.5 ** attempt)


async def embed_ordered(texts: list[str]) -> np.ndarray:
    batches = [texts[i:i + EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    sem     = asyncio.Semaphore(CONCURRENCY)
    client  = openai.AsyncOpenAI()

    async def bounded(i, batch):
        return await embed_batch_async(client, batch, sem)

    results  = await asyncio.gather(*[bounded(i, b) for i, b in enumerate(batches)])
    all_embs = [e for batch in results for e in batch]
    return np.array(all_embs, dtype=np.float32)


def normalize(embs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return embs / norms


# ── Step 1: build / load label table ─────────────────────────────────────────

def build_label_table(extract_path: Path) -> pd.DataFrame:
    print(f"Reading {extract_path.name} …")
    freq      = collections.Counter()
    raw_forms = collections.defaultdict(collections.Counter)
    sf_map    = collections.defaultdict(set)

    with gzip.open(extract_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            out = rec.get("output", {})
            if not isinstance(out, dict):
                continue
            for nd in out.get("nodes", []):
                lbl = nd.get("label", "").strip()
                if not lbl:
                    continue
                key = lbl.lower()
                freq[key]           += 1
                raw_forms[key][lbl] += 1
                for sf in nd.get("surface_forms", []):
                    sf = sf.strip()
                    if sf and sf.lower() != key:
                        sf_map[key].add(sf.lower())

    print(f"  {len(freq):,} unique labels, {sum(freq.values()):,} occurrences")

    rows = []
    for key, f in freq.items():
        best_raw = raw_forms[key].most_common(1)[0][0]
        rows.append({
            "label":          key,
            "label_raw":      best_raw,
            "freq":           f,
            "surface_forms":  list(sf_map[key]),
            "n_surface_forms": len(sf_map[key]),
        })
    df = pd.DataFrame(rows).sort_values("freq", ascending=False).reset_index(drop=True)
    return df


# ── Step 2: FAISS index ───────────────────────────────────────────────────────

def build_faiss_index(onto_norm: np.ndarray) -> faiss.Index:
    d = onto_norm.shape[1]
    quantizer = faiss.IndexFlatIP(d)
    index     = faiss.IndexIVFFlat(quantizer, d, FAISS_NLIST, faiss.METRIC_INNER_PRODUCT)
    index.train(onto_norm)
    index.add(onto_norm)
    index.nprobe = FAISS_NPROBE
    return index


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("=== Mapping extraction labels → ontology v2 ===\n")

    # ── Label table ───────────────────────────────────────────────────────
    cache = OUT_DIR / "extraction_labels_v2.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        print(f"Label table: {len(df):,} labels (from cache)")
    else:
        df = build_label_table(EXTRACT)
        df.to_parquet(cache, index=False)
        print(f"Saved label table → {cache}")

    n          = len(df)
    labels     = df["label"].tolist()
    labels_raw = df["label_raw"].tolist()
    # surface_forms is stored as a Python list in the parquet
    sfs_list   = df["surface_forms"].tolist()

    # ── Ontology ──────────────────────────────────────────────────────────
    print("\nLoading ontology …")
    onto         = json.load(open(OUT_DIR / "ontology_v2_final.json"))
    onto_ids     = [c["id"]            for c in onto]
    onto_labels  = [c["label"]         for c in onto]
    onto_sources = [c.get("source","") for c in onto]
    onto_domains = [c.get("domain","") for c in onto]
    onto_lower   = {lbl.lower().strip(): i for i, lbl in enumerate(onto_labels)}
    print(f"  {len(onto):,} concepts")

    onto_embs = np.load(OUT_DIR / "ontology_v2_label_only_embeddings.npy").astype(np.float32)
    onto_norm = normalize(onto_embs)

    print("Building FAISS index …")
    idx = build_faiss_index(onto_norm)
    print(f"  IVFFlat ready (nlist={FAISS_NLIST}, nprobe={FAISS_NPROBE})")

    # ── Result arrays (pre-allocated) ─────────────────────────────────────
    match_kind  = ["unmatched"] * n
    scores      = np.full(n, -1.0, dtype=np.float32)
    matched_via = [""] * n
    best_idx    = np.full(n, -1, dtype=np.int32)
    r2_idx      = np.full(n, -1, dtype=np.int32)
    r3_idx      = np.full(n, -1, dtype=np.int32)
    r2_scr      = np.full(n, np.nan, dtype=np.float32)
    r3_scr      = np.full(n, np.nan, dtype=np.float32)
    sf_best_idx = np.full(n, -1, dtype=np.int32)
    sf_best_scr = np.full(n, np.nan, dtype=np.float32)

    def record_exact(i, kind, score, via, oi):
        match_kind[i]  = kind
        scores[i]      = score
        matched_via[i] = via
        best_idx[i]    = oi

    # ── Pass 1: exact label match ─────────────────────────────────────────
    print("\nPass 1 – exact label match …")
    needs_pass2 = []
    for i, lbl in enumerate(labels):
        if lbl in onto_lower:
            record_exact(i, "exact", 1.0, "label", onto_lower[lbl])
        else:
            needs_pass2.append(i)
    print(f"  Exact (label):  {n - len(needs_pass2):,}")

    # ── Pass 2: exact SF / stripped matches ───────────────────────────────
    print(f"\nPass 2 – exact SF / stripped matches ({len(needs_pass2):,} labels) …")
    needs_embed = []
    for i in needs_pass2:
        lbl = labels[i]
        matched = False
        # try parenthetical-stripped label first
        stripped = strip_paren(lbl)
        if stripped != lbl and stripped in onto_lower:
            record_exact(i, "exact_stripped", 0.99, "label_stripped", onto_lower[stripped])
            matched = True
        if not matched:
            # Try each surface form.  Minimum 3 words required: short SFs (1-2
            # words) are abbreviations or fragments that exact-match unrelated
            # ontology entries (e.g. "ces" → JEL "CES" for label "carbon
            # emissions"; "trade" → JEL "Trade" for label "trade openness").
            for sf in sfs_list[i]:
                sf_key = sf.lower().strip()
                if len(sf_key.split()) < 3:
                    continue   # too short — skip exact matching, let embedding handle
                if sf_key in onto_lower:
                    record_exact(i, "exact_sf", 0.99, sf, onto_lower[sf_key])
                    matched = True
                    break
                sf_stripped = strip_paren(sf_key)
                if sf_stripped != sf_key and len(sf_stripped.split()) >= 3 and sf_stripped in onto_lower:
                    record_exact(i, "exact_sf_stripped", 0.98, sf, onto_lower[sf_stripped])
                    matched = True
                    break
        if not matched:
            needs_embed.append(i)

    n_exact_sf = sum(1 for i in range(n)
                     if match_kind[i] in ("exact_sf", "exact_sf_stripped", "exact_stripped"))
    print(f"  Exact (SF/stripped): {n_exact_sf:,}")
    print(f"  Needs embedding:     {len(needs_embed):,}")

    # ── Pass 3: streaming embed + FAISS NN ───────────────────────────────
    print(f"\nPass 3 – streaming embed + NN ({len(needs_embed):,} labels in chunks of {STREAM_CHUNK:,}) …")
    t0         = time.time()
    n_embed    = len(needs_embed)
    n_done     = 0

    for chunk_start in range(0, n_embed, STREAM_CHUNK):
        chunk_end    = min(chunk_start + STREAM_CHUNK, n_embed)
        chunk_global = needs_embed[chunk_start:chunk_end]
        chunk_labels = [labels[i] for i in chunk_global]

        # Embed labels
        embs      = await embed_ordered(chunk_labels)
        qnorm     = normalize(embs)

        # FAISS search
        scrs, idxs = idx.search(qnorm, TOP_K)

        # Record results
        for local_j, global_i in enumerate(chunk_global):
            s1 = float(scrs[local_j, 0])
            i1 = int(idxs[local_j, 0])
            scores[global_i]  = s1
            best_idx[global_i] = i1
            matched_via[global_i] = "label"
            match_kind[global_i] = (
                "embedding" if s1 >= SOFT_THRESH else "unmatched"
            )
            if TOP_K > 1:
                r2_idx[global_i] = int(idxs[local_j, 1])
                r2_scr[global_i] = float(scrs[local_j, 1])
            if TOP_K > 2:
                r3_idx[global_i] = int(idxs[local_j, 2])
                r3_scr[global_i] = float(scrs[local_j, 2])

        n_done += len(chunk_global)
        elapsed = time.time() - t0
        eta     = (n_embed - n_done) / (n_done / elapsed) if n_done else 0
        print(f"  {n_done:,}/{n_embed:,} labels "
              f"({n_done/elapsed:.0f}/s, ETA {eta:.0f}s)  "
              f"[{elapsed:.0f}s elapsed]")

    # ── Pass 4: embed surface forms for labels that needed embedding ───────
    # Collect all distinct SF strings for those labels
    print(f"\nPass 4 – embed surface forms for {len(needs_embed):,} labels …")
    sf_needed: dict[str, int] = {}   # sf_string → position in sf_emb array
    for i in needs_embed:
        for sf in sfs_list[i]:
            sf = sf.lower().strip()
            if sf and sf not in sf_needed:
                sf_needed[sf] = len(sf_needed)

    n_sf = len(sf_needed)
    print(f"  {n_sf:,} distinct SF strings to embed")

    if n_sf > 0:
        sf_list_all = list(sf_needed.keys())
        t0 = time.time()
        # Stream-embed the SF strings in chunks too
        sf_scores_arr  = np.full((n_sf, TOP_K), -1.0, dtype=np.float32)
        sf_indices_arr = np.full((n_sf, TOP_K), -1,   dtype=np.int32)

        for cs in range(0, n_sf, STREAM_CHUNK):
            ce        = min(cs + STREAM_CHUNK, n_sf)
            sf_chunk  = sf_list_all[cs:ce]
            sf_embs   = await embed_ordered(sf_chunk)
            sf_qnorm  = normalize(sf_embs)
            sc, si    = idx.search(sf_qnorm, TOP_K)
            sf_scores_arr[cs:ce]  = sc
            sf_indices_arr[cs:ce] = si
            elapsed = time.time() - t0
            print(f"  SF {ce:,}/{n_sf:,} ({ce/elapsed:.0f}/s)")

        # For each label, check if any SF beats the current label score
        n_upgraded = 0
        for i in needs_embed:
            best_sf_s = -1.0
            best_sf_i = -1
            best_sf_str = ""
            for sf in sfs_list[i]:
                sf_key = sf.lower().strip()
                if sf_key in sf_needed:
                    pos = sf_needed[sf_key]
                    s   = float(sf_scores_arr[pos, 0])
                    if s > best_sf_s:
                        best_sf_s   = s
                        best_sf_i   = int(sf_indices_arr[pos, 0])
                        best_sf_str = sf_key

            if best_sf_i >= 0:
                sf_best_idx[i] = best_sf_i
                sf_best_scr[i] = best_sf_s

            if best_sf_s > scores[i]:
                scores[i]      = best_sf_s
                best_idx[i]    = best_sf_i
                matched_via[i] = best_sf_str
                match_kind[i]  = (
                    "embedding_sf" if best_sf_s >= SOFT_THRESH else "unmatched"
                )
                n_upgraded += 1

        print(f"  SF upgrades (SF beat label): {n_upgraded:,}")

    # ── Build output dataframe ────────────────────────────────────────────
    def safe(arr, i):
        v = arr[i] if i >= 0 else None
        return v

    rows = []
    for i in range(n):
        bi = int(best_idx[i])
        rows.append({
            "label":           labels[i],
            "label_raw":       labels_raw[i],
            "freq":            int(df.at[i, "freq"]),
            "n_surface_forms": int(df.at[i, "n_surface_forms"]),
            "match_kind":      match_kind[i],
            "onto_id":         safe(onto_ids,     bi),
            "onto_label":      safe(onto_labels,  bi),
            "onto_source":     safe(onto_sources, bi),
            "onto_domain":     safe(onto_domains, bi),
            "score":           float(scores[i]) if scores[i] >= 0 else None,
            "matched_via":     matched_via[i],
            "rank2_id":        safe(onto_ids,    int(r2_idx[i])) if r2_idx[i] >= 0 else None,
            "rank2_label":     safe(onto_labels, int(r2_idx[i])) if r2_idx[i] >= 0 else None,
            "rank2_score":     float(r2_scr[i])  if not np.isnan(r2_scr[i])  else None,
            "rank3_id":        safe(onto_ids,    int(r3_idx[i])) if r3_idx[i] >= 0 else None,
            "rank3_label":     safe(onto_labels, int(r3_idx[i])) if r3_idx[i] >= 0 else None,
            "rank3_score":     float(r3_scr[i])  if not np.isnan(r3_scr[i])  else None,
            "sf_best_onto_id":    safe(onto_ids,    int(sf_best_idx[i])) if sf_best_idx[i] >= 0 else None,
            "sf_best_onto_label": safe(onto_labels, int(sf_best_idx[i])) if sf_best_idx[i] >= 0 else None,
            "sf_best_score":      float(sf_best_scr[i]) if not np.isnan(sf_best_scr[i]) else None,
        })

    result = pd.DataFrame(rows).sort_values("freq", ascending=False).reset_index(drop=True)

    # ── Stats ─────────────────────────────────────────────────────────────
    total_freq = result["freq"].sum()
    has_score  = result["score"].notna()
    linked     = result[has_score & (result["score"] >= LINK_THRESH)]
    soft       = result[has_score & (result["score"] >= SOFT_THRESH) & (result["score"] < LINK_THRESH)]
    unmatched  = result[~has_score | (result["score"] < SOFT_THRESH)]

    print(f"\n=== Results ===")
    print(f"Total unique labels:  {len(result):,}   ({total_freq:,} occurrences)")
    print(f"  Linked    (>={LINK_THRESH}): "
          f"{len(linked):,} ({len(linked)/len(result)*100:.1f}%)  "
          f"{linked['freq'].sum():,} occ ({linked['freq'].sum()/total_freq*100:.1f}%)")
    print(f"  Soft link ({SOFT_THRESH}-{LINK_THRESH}): "
          f"{len(soft):,} ({len(soft)/len(result)*100:.1f}%)  "
          f"{soft['freq'].sum():,} occ ({soft['freq'].sum()/total_freq*100:.1f}%)")
    print(f"  Unmatched (<{SOFT_THRESH}):  "
          f"{len(unmatched):,} ({len(unmatched)/len(result)*100:.1f}%)  "
          f"{unmatched['freq'].sum():,} occ ({unmatched['freq'].sum()/total_freq*100:.1f}%)")

    print(f"\nMatch kind breakdown:")
    print(result["match_kind"].value_counts().to_string())

    print(f"\nLinked by ontology source:")
    print(linked["onto_source"].value_counts().to_string())

    print(f"\nTop-20 unmatched by frequency:")
    print(unmatched.nlargest(20, "freq")[["label","freq","score","onto_label"]].to_string())

    print(f"\nSample linked (high freq):")
    for _, r in linked.nlargest(15, "freq").iterrows():
        print(f"  [{r['score']:.3f}|{r['match_kind']:15s}] "
              f"{r['label']!r:35s} → {r['onto_label']!r} ({r['onto_source']})")

    out_path = OUT_DIR / "extraction_label_mapping_v2.parquet"
    result.to_parquet(out_path, index=False)
    print(f"\nSaved → {out_path}")
    print("=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
