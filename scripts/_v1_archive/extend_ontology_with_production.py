"""Extend ontology_v2_final.json with FG3C production concepts not already present.

5,053 FG3C production concepts have labels absent from ontology_v2_final.  These
include high-frequency extraction targets like "CO2 emissions", "trade openness",
and "COVID-19 pandemic" that appear in empirical papers but were not captured by
any structured vocabulary source (JEL/Wikidata/OpenAlex/Wikipedia).

Strategy:
  1.  Load ontology_v2_final.json (153,800 concepts).
  2.  Load FG3C production concepts from ontology_production_first.json.
  3.  Skip any FG3C concept whose label (case-insensitive) already appears in
      the ontology — those are already covered by a higher-priority source.
  4.  For each new concept, infer domain from its ref_link (look up the matched
      ontology entry's domain); fall back to "other_valid".
  5.  Append the 5,053 new production concepts to produce:
        data/ontology_v2/ontology_v2_extended.json   (153,800 + 5,053 = 158,853)
  6.  Embed the 5,053 new labels and append to the cached label-only embeddings,
      saving as:
        data/ontology_v2/ontology_v2_extended_label_embeddings.npy

Output is consumed by map_raw_labels_to_ontology_v2.py (pass --extended flag).

Design note:
  We do NOT modify ontology_v2_final.json because that file records the output of
  the structured-source pipeline.  The extended file is clearly labelled as such.
  The "production" source is a 6th tier below "wikipedia" in the canonical ranking
  — it appears only when no structured source covers the concept.

  Domain inference: look up the ref_link id in ontology_v2_final; if found use
  that concept's domain.  This gives "CO2 emissions" → environment (via its
  nearest JEL/WikiData match), while still labelling the source as "production".
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 500
CONCURRENCY = 20


# ── Embedding helpers ─────────────────────────────────────────────────────────

async def embed_batch(client, texts, sem):
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
                return [r.embedding for r in resp.data]
            except Exception:
                if attempt == 2:
                    return [[0.0] * 1536] * len(texts)
                await asyncio.sleep(1.5 ** attempt)


async def embed_all_ordered(texts: list[str]) -> np.ndarray:
    batches = [texts[i:i + EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    sem = asyncio.Semaphore(CONCURRENCY)
    client = openai.AsyncOpenAI()
    t0 = time.time()
    print(f"  Embedding {len(texts):,} texts in {len(batches):,} batches...")

    async def bounded(i, batch):
        result = await embed_batch(client, batch, sem)
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            eta = (len(batches) - (i + 1)) / ((i + 1) / elapsed) if (i + 1) else 0
            print(f"    {i + 1}/{len(batches)} ({(i + 1) / elapsed:.1f}/s, ETA {eta:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(i, b) for i, b in enumerate(batches)])
    all_embs = [e for batch in results for e in batch]
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")
    return np.array(all_embs, dtype=np.float32)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("=== Extending ontology_v2_final with FG3C production concepts ===\n")

    # Load base ontology
    print("Loading ontology_v2_final.json...")
    onto = json.load(open(OUT_DIR / "ontology_v2_final.json"))
    print(f"  {len(onto):,} concepts")

    # Build label→concept lookup and id→domain lookup
    onto_label_lower: dict[str, int] = {c["label"].lower().strip(): i for i, c in enumerate(onto)}
    onto_id_to_domain: dict[str, str] = {c["id"]: c.get("domain", "") for c in onto}

    # Load FG3C production concepts
    print("Loading FG3C production concepts...")
    prod_onto = json.load(open(OUT_DIR / "ontology_production_first.json"))
    prod_entries = [c for c in prod_onto if c.get("source") == "production"]
    print(f"  {len(prod_entries):,} production concepts")

    # Split: already covered vs new
    already_covered = [c for c in prod_entries if c["label"].lower().strip() in onto_label_lower]
    new_entries     = [c for c in prod_entries if c["label"].lower().strip() not in onto_label_lower]
    print(f"  Already in ontology (skip): {len(already_covered):,}")
    print(f"  New (to add):               {len(new_entries):,}")

    # Infer domain for each new concept via its ref_link
    def infer_domain(prod_concept: dict) -> str:
        ref_link = prod_concept.get("ref_link") or {}
        ref_id   = (ref_link.get("ref_id") or "").strip()
        if ref_id and ref_id in onto_id_to_domain:
            domain = onto_id_to_domain[ref_id]
            if domain:
                return domain
        return "other_valid"

    # Build new ontology entries
    new_onto_entries = []
    for c in new_entries:
        desc = (c.get("description") or "").strip()
        new_onto_entries.append({
            "id":          c["id"],
            "label":       c["label"],
            "source":      "production",
            "description": desc,
            "domain":      infer_domain(c),
            "instance_support": c.get("instance_support", 0),
            # ref_link preserved for traceability
            "ref_link_id":    ((c.get("ref_link") or {}).get("ref_id") or ""),
            "ref_link_score": float((c.get("ref_link") or {}).get("score") or 0.0),
        })

    # Domain distribution of new entries
    domain_counts: dict[str, int] = {}
    for e in new_onto_entries:
        domain_counts[e["domain"]] = domain_counts.get(e["domain"], 0) + 1
    print(f"\nDomain distribution of new entries:")
    for d, n in sorted(domain_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {d:20s}: {n:,}")

    # ── Embed new labels ─────────────────────────────────────────────────────
    print(f"\nEmbedding {len(new_onto_entries):,} new labels...")
    new_labels = [e["label"] for e in new_onto_entries]
    new_embs = await embed_all_ordered(new_labels)
    print(f"  New embeddings shape: {new_embs.shape}")

    # Concatenate with existing label-only embeddings
    existing_embs_path = OUT_DIR / "ontology_v2_label_only_embeddings.npy"
    existing_embs = np.load(existing_embs_path).astype(np.float32)
    print(f"  Existing embeddings shape: {existing_embs.shape}")
    extended_embs = np.concatenate([existing_embs, new_embs], axis=0)
    print(f"  Extended embeddings shape: {extended_embs.shape}")

    # ── Save extended ontology ────────────────────────────────────────────────
    extended_onto = onto + new_onto_entries
    extended_path = OUT_DIR / "ontology_v2_extended.json"
    json.dump(extended_onto, open(extended_path, "w"), ensure_ascii=False)
    print(f"\nSaved extended ontology: {len(extended_onto):,} concepts → {extended_path}")

    extended_embs_path = OUT_DIR / "ontology_v2_extended_label_embeddings.npy"
    np.save(extended_embs_path, extended_embs)
    print(f"Saved extended embeddings: {extended_embs.shape} → {extended_embs_path}")

    # Sanity check
    assert len(extended_onto) == extended_embs.shape[0], \
        f"Mismatch: {len(extended_onto)} concepts vs {extended_embs.shape[0]} embeddings"

    # Stats
    print(f"\n=== Summary ===")
    print(f"  Base ontology:    {len(onto):,}")
    print(f"  New (production): {len(new_onto_entries):,}")
    print(f"  Extended total:   {len(extended_onto):,}")
    print(f"\nTop 20 new entries by instance_support:")
    top20 = sorted(new_onto_entries, key=lambda x: -x.get("instance_support", 0))[:20]
    for e in top20:
        print(f"  [{e['domain']:15s}] {e['label']:40s} support={e['instance_support']:,}  ref_score={e['ref_link_score']:.3f}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
