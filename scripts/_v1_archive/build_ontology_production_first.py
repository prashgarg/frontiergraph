"""Build ontology v2 with production concepts as the backbone.

Strategy (revised):
  1. Start with the 6,752 production FG3C concepts — these are quality-filtered
     from 242K papers and represent what economists actually study.
  2. Enrich them with Wikidata/JEL/OpenAlex descriptions where linked.
  3. Add new concepts from JEL/OpenAlex/Wikidata that DON'T overlap with production
     (at lowercase or embedding similarity > 0.85).
  4. After Wikipedia crawl is done, add non-overlapping Wikipedia valid articles.

This gives a vocabulary that:
  - STARTS from what we know is good (production)
  - ADDS formal ontology coverage (JEL, OpenAlex topics)
  - ADDS entity knowledge (Wikidata, Wikipedia)
  - Is COMPLETE for the existing graph, and EXTENSIBLE for future extractions

Output: data/ontology_v2/ontology_production_first.json
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from collections import Counter, defaultdict

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
NEW_THRESHOLD = 0.85  # cos < this → new concept (not already in production)


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


async def embed_all(texts: list[str], label: str = "") -> np.ndarray:
    client = openai.AsyncOpenAI()
    sem = asyncio.Semaphore(CONCURRENCY)
    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  Embedding {len(texts):,} {label} texts...")
    t0 = time.time()
    completed = 0

    async def bounded(batch):
        nonlocal completed
        result = await embed_batch(client, batch, sem)
        completed += 1
        if completed % 20 == 0:
            print(f"    {completed}/{len(batches)} ({time.time()-t0:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(b) for b in batches])
    flat = [e for batch in results for e in batch]
    print(f"  Done in {time.time()-t0:.1f}s")
    return np.array(flat, dtype=np.float32)


def normalize(embs):
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return embs / norms


async def main():
    print("=== Building production-first ontology v2 ===\n")

    # ── 1. Production backbone ────────────────────────────────────────────────
    print("Loading production backbone...")
    canon_df = pd.read_parquet(PROCESSED_DIR / "canonical_concepts.parquet")
    families_df = pd.read_parquet(PROCESSED_DIR / "concept_families.parquet")
    sigs_df = pd.read_parquet(PROCESSED_DIR / "concept_context_signatures.parquet")

    # Build family lookup
    family_map = {}
    for _, row in families_df.iterrows():
        cid = row["member_concept_id"]
        family_map.setdefault(cid, []).append({
            "family_id": row["family_id"],
            "family_label": row["family_label"],
            "family_type": row["family_type"],
        })

    # Build signature lookup
    sig_map = {}
    for _, row in sigs_df.iterrows():
        sig_map[row["concept_id"]] = {
            "top_geographies": row.get("top_geographies_json", "[]"),
            "top_units": row.get("top_units_json", "[]"),
            "bucket_profile": row.get("bucket_profile_json", "[]"),
            "context_support": int(row.get("context_support", 0)),
        }

    # Build production items
    production_items = []
    for _, row in canon_df.iterrows():
        cid = row["concept_id"]
        import json as json_lib
        aliases = json_lib.loads(row["aliases_json"]) if isinstance(row["aliases_json"], str) else []

        production_items.append({
            "id": cid,
            "label": row["preferred_label"],
            "aliases": aliases,
            "description": "",   # will be enriched from aligned sources
            "source": "production",
            "instance_support": int(row["instance_support"]),
            "distinct_paper_support": int(row["distinct_paper_support"]),
            "bucket_hint": row.get("bucket_hint", ""),
            "primary_concept_type": row.get("primary_concept_type", ""),
            "families": family_map.get(cid, []),
            "context_signature": sig_map.get(cid, {}),
        })

    print(f"  Production concepts: {len(production_items):,}")

    # ── 2. Reference vocabulary (JEL + OpenAlex + Wikidata) ──────────────────
    print("\nLoading reference vocabulary...")
    with open(OUT_DIR / "ontology_candidates.json") as f:
        ref_items = json.load(f)

    ref_wikidata = [i for i in ref_items if i["source"] == "wikidata"]
    ref_jel = [i for i in ref_items if i["source"] == "jel"]
    ref_oa_kw = [i for i in ref_items if i["source"] == "openalex_keyword"]
    ref_oa_topic = [i for i in ref_items if i["source"] == "openalex_topic"]

    print(f"  Wikidata: {len(ref_wikidata):,}")
    print(f"  JEL: {len(ref_jel):,}")
    print(f"  OpenAlex keywords: {len(ref_oa_kw):,}")
    print(f"  OpenAlex topics: {len(ref_oa_topic):,}")

    # ── 3. Enrich production with reference descriptions ─────────────────────
    print("\nLoading pre-computed label-only embeddings...")

    # Use pre-computed label-only embeddings if available
    label_emb_path = OUT_DIR / "ontology_label_embeddings.npy"
    if label_emb_path.exists():
        ref_label_embs = np.load(label_emb_path)
        print(f"  Loaded ref label embeddings: {ref_label_embs.shape}")
    else:
        print("  Computing ref label embeddings...")
        ref_labels = [item["label"] for item in ref_items]
        ref_label_embs = await embed_all(ref_labels, "ref labels")
        np.save(label_emb_path, ref_label_embs)

    # Also load/compute production label embeddings
    print("  Computing production label embeddings...")
    prod_labels = [item["label"] for item in production_items]
    prod_embs = await embed_all(prod_labels, "production labels")

    ref_norm = normalize(ref_label_embs)
    prod_norm = normalize(prod_embs)

    # For each production concept, find best reference match
    print("\nAligning production → reference vocabulary...")
    chunk_size = 500
    prod_best_idx = []
    prod_best_score = []

    for start in range(0, len(prod_norm), chunk_size):
        batch = prod_norm[start:start+chunk_size]
        sims = batch @ ref_norm.T
        best_idx = sims.argmax(axis=1)
        best_score = sims.max(axis=1)
        prod_best_idx.extend(best_idx.tolist())
        prod_best_score.extend(best_score.tolist())

    # Enrich production items with reference descriptions
    enriched_count = 0
    for i, item in enumerate(production_items):
        score = prod_best_score[i]
        best_ref = ref_items[prod_best_idx[i]]

        if score >= NEW_THRESHOLD:
            # Link to reference
            item["ref_link"] = {
                "score": round(score, 4),
                "ref_id": best_ref["id"],
                "ref_label": best_ref["label"],
                "ref_source": best_ref["source"],
            }
            # Enrich description
            if not item.get("description") and best_ref.get("description"):
                item["description"] = best_ref["description"][:200]
                enriched_count += 1
            # Add JEL codes if reference is JEL
            if best_ref.get("jel_code"):
                item["jel_codes"] = [best_ref["jel_code"]]
        else:
            item["ref_link"] = None

    linked = sum(1 for item in production_items if item["ref_link"])
    print(f"  Linked: {linked:,} ({linked/len(production_items)*100:.1f}%) concepts")
    print(f"  Description enriched: {enriched_count:,}")

    # ── 4. Find genuinely NEW reference concepts not in production ───────────
    print("\nFinding genuinely new reference concepts...")

    # For each reference item, find best production match
    # New concept = cos < NEW_THRESHOLD to all production concepts
    chunk_size = 500
    ref_best_scores = []

    for start in range(0, len(ref_norm), chunk_size):
        batch = ref_norm[start:start+chunk_size]
        sims = batch @ prod_norm.T      # (B, N_prod)
        best_score = sims.max(axis=1)
        ref_best_scores.extend(best_score.tolist())

    new_ref_items = []
    for i, (item, score) in enumerate(zip(ref_items, ref_best_scores)):
        if score < NEW_THRESHOLD:
            new_ref_items.append(dict(item))
            new_ref_items[-1]["_is_new"] = True
            new_ref_items[-1]["_best_prod_score"] = round(score, 4)

    print(f"  New reference concepts (not in production): {len(new_ref_items):,}")

    # Breakdown by source
    new_src_counts = Counter(item["source"] for item in new_ref_items)
    print(f"  By source:")
    for src, n in new_src_counts.most_common():
        print(f"    {src}: {n:,}")

    # ── 5. Combine ────────────────────────────────────────────────────────────
    print("\nCombining into final vocabulary...")
    final_items = production_items + new_ref_items

    # Add Wikipedia if available
    wp_path = OUT_DIR / "wikipedia_valid.json"
    if wp_path.exists():
        with open(wp_path) as f:
            wp_data = json.load(f)
        print(f"  Wikipedia valid available: {len(wp_data):,}")
        # TODO: align Wikipedia vs production and add new ones
        # For now, add all Wikipedia valid as new concepts
        # (proper dedup will be done in build_ontology_v2.py)
        for a in wp_data:
            final_items.append({
                "id": f"wp:{a.get('pageid', a['title'])}",
                "label": a["title"],
                "description": a.get("short_desc", "")[:200],
                "source": "wikipedia",
                "domain": a.get("domain", ""),
            })
        print(f"  Added {len(wp_data):,} Wikipedia valid articles")
    else:
        print("  Wikipedia valid not yet available (crawl in progress)")

    print(f"\n  Final vocabulary size: {len(final_items):,}")
    src_counts = Counter(item["source"] for item in final_items)
    for src, n in src_counts.items():
        print(f"    {src}: {n:,}")

    # ── 6. Statistics ─────────────────────────────────────────────────────────
    # Production with enriched descriptions
    prod_with_desc = sum(1 for item in production_items if item.get("description"))
    print(f"\nProduction concepts with descriptions: {prod_with_desc:,} ({prod_with_desc/len(production_items)*100:.1f}%)")

    # Domain coverage
    domain_counts = Counter()
    for item in final_items:
        domain = item.get("domain", "")
        if not domain and item.get("source") == "production":
            domain = item.get("families", [{}])[0].get("family_type", "") if item.get("families") else ""
        domain_counts[domain] += 1

    # Sample new concepts by source
    import random; random.seed(42)
    print(f"\nSample new JEL keywords added:")
    new_jel = [i for i in new_ref_items if i["source"] == "jel"]
    for item in random.sample(new_jel, min(10, len(new_jel))):
        print(f"  {item['label']} ({item.get('jel_code', '')})")

    print(f"\nSample new OpenAlex topics added:")
    new_topics = [i for i in new_ref_items if i["source"] == "openalex_topic"]
    for item in random.sample(new_topics, min(10, len(new_topics))):
        print(f"  {item['label']}")

    print(f"\nSample new Wikidata concepts added:")
    new_wikidata = [i for i in new_ref_items if i["source"] == "wikidata"]
    for item in random.sample(new_wikidata, min(10, len(new_wikidata))):
        desc = item.get("description", "")[:60]
        print(f"  {item['label']} — {desc}")

    # ── 7. Save ───────────────────────────────────────────────────────────────
    out_path = OUT_DIR / "ontology_production_first.json"
    with open(out_path, "w") as f:
        json.dump(final_items, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(final_items):,} items to {out_path}")

    # Summary
    summary = {
        "total": len(final_items),
        "production_backbone": len(production_items),
        "production_linked_to_ref": linked,
        "production_with_description": prod_with_desc,
        "new_from_reference": len(new_ref_items),
        "new_by_source": dict(new_src_counts),
    }
    with open(OUT_DIR / "ontology_production_first_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== DONE ===")
    print(f"Vocabulary: {len(production_items):,} production + {len(new_ref_items):,} new = {len(final_items):,} total")


if __name__ == "__main__":
    asyncio.run(main())
