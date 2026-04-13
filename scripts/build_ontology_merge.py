"""Merge JEL + OpenAlex + Wikidata vocabularies into a clean, deduplicated ontology.

Strategy:
1. Collect all candidate labels from all three sources.
2. Embed everything with text-embedding-3-small (cheap, fast).
3. Use approximate nearest-neighbor search to find cross-source duplicates
   (cosine > 0.93) and cluster them.
4. For each cluster, pick a canonical entry (prefer Wikidata if present;
   otherwise the most common form).
5. Output a merged vocabulary JSON with rich metadata.

Output: data/ontology_v2/ontology_merged.json
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from collections import defaultdict

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

EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 500       # API batch size
CONCURRENCY = 20        # parallel embed requests
SIM_THRESHOLD = 0.93    # cosine similarity threshold for merging


# ── 1. Load sources ──────────────────────────────────────────────────────────

def load_wikidata() -> list[dict]:
    with open(OUT_DIR / "wikidata_valid_enriched.json") as f:
        concepts = json.load(f)
    out = []
    for c in concepts:
        # Build a rich text for embedding: label + Wikidata description
        label = c.get("label", "").strip()
        if not label:
            continue
        desc = c.get("description", "") or c.get("short_desc", "") or ""
        out.append({
            "id": c["qid"],
            "label": label,
            "description": desc[:200],
            "source": "wikidata",
            "domain": c.get("domain_voted", c.get("domain_clean", "")),
            "confidence": c.get("confidence", ""),
            "parent_label": c.get("parent_label", ""),
            "root_label": c.get("root_label", ""),
            "wp_short_desc": c.get("short_desc", ""),
            "wp_extract": c.get("extract", ""),
        })
    print(f"  Wikidata: {len(out)} concepts")
    return out


def load_jel() -> list[dict]:
    with open(OUT_DIR / "jel_full.json") as f:
        jel_data = json.load(f)

    seen = set()
    out = []

    def add(keyword, code, level, code_label, guideline):
        kw = keyword.strip()
        if not kw or kw == "None Speciffied":
            return
        key = kw.lower()
        if key in seen:
            return
        seen.add(key)
        out.append({
            "id": f"jel:{code}:{kw}",
            "label": kw,
            "description": guideline[:200] if guideline else "",
            "source": "jel",
            "jel_code": code,
            "jel_label": code_label,
            "jel_level": level,
        })

    for l1_code, info in jel_data.items():
        guideline_l1 = info.get("guideline", "")
        for kw in info.get("keywords", []):
            add(kw, l1_code, 1, l1_code, guideline_l1)
        for l2 in info.get("l2_codes", []):
            guideline_l2 = l2.get("guideline", "")
            for kw in l2.get("keywords", []):
                add(kw, l2["code"], 2, l2.get("title", ""), guideline_l2)
            for l3 in l2.get("l3_codes", []):
                guideline_l3 = l3.get("guideline", "")
                for kw in l3.get("keywords", []):
                    add(kw, l3["code"], 3, l3.get("title", ""), guideline_l3)

    print(f"  JEL: {len(out)} unique keywords")
    return out


def load_openalex(min_papers: int = 3) -> list[dict]:
    df = pd.read_parquet(OUT_DIR / "openalex_paper_keywords.parquet")

    # Keywords
    kw_df = df[df["type"] == "keyword"]
    kw_counts = kw_df.groupby("display_name").agg(
        paper_count=("work_id", "nunique"),
        mean_score=("score", "mean"),
        item_id=("item_id", "first"),
    ).reset_index()
    kw_counts = kw_counts[kw_counts["paper_count"] >= min_papers]

    kw_out = []
    for _, row in kw_counts.iterrows():
        kw_out.append({
            "id": row["item_id"],
            "label": row["display_name"],
            "description": "",
            "source": "openalex_keyword",
            "paper_count": int(row["paper_count"]),
            "mean_score": float(row["mean_score"]),
        })

    # Topics (always included — curated by OpenAlex team)
    topic_df = df[df["type"] == "topic"]
    topic_counts = topic_df.groupby("display_name").agg(
        paper_count=("work_id", "nunique"),
        mean_score=("score", "mean"),
        subfield=("subfield", "first"),
        field=("field", "first"),
        oa_domain=("domain", "first"),
        item_id=("item_id", "first"),
    ).reset_index()

    topic_out = []
    for _, row in topic_counts.iterrows():
        topic_out.append({
            "id": row["item_id"],
            "label": row["display_name"],
            "description": str(row.get("field", "") or ""),
            "source": "openalex_topic",
            "paper_count": int(row["paper_count"]),
            "subfield": str(row.get("subfield", "") or ""),
            "field": str(row.get("field", "") or ""),
            "oa_domain": str(row.get("oa_domain", "") or ""),
        })

    print(f"  OpenAlex keywords (≥{min_papers} papers): {len(kw_out)}")
    print(f"  OpenAlex topics: {len(topic_out)}")
    return kw_out + topic_out


# ── 2. Embed ──────────────────────────────────────────────────────────────────

async def embed_batch(client: openai.AsyncOpenAI, texts: list[str], sem: asyncio.Semaphore) -> list[list[float]]:
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.embeddings.create(
                    model=EMBED_MODEL,
                    input=texts,
                )
                return [item.embedding for item in resp.data]
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    # return zero vectors on failure
                    return [[0.0] * 1536] * len(texts)
    return [[0.0] * 1536] * len(texts)


async def embed_all(texts: list[str]) -> np.ndarray:
    client = openai.AsyncOpenAI()
    sem = asyncio.Semaphore(CONCURRENCY)
    completed = 0
    t0 = time.time()

    batches = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  Embedding {len(texts):,} texts in {len(batches)} batches...")

    async def bounded(batch, idx):
        nonlocal completed
        result = await embed_batch(client, batch, sem)
        completed += 1
        if completed % 20 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(batches) - completed) / rate if rate > 0 else 0
            print(f"    {completed}/{len(batches)} batches ({rate:.1f}/s, ETA {eta:.0f}s)")
        return result

    tasks = [bounded(b, i) for i, b in enumerate(batches)]
    results = await asyncio.gather(*tasks)

    # Flatten
    all_embs = []
    for batch_result in results:
        all_embs.extend(batch_result)

    elapsed = time.time() - t0
    print(f"  Done: {len(all_embs):,} embeddings in {elapsed:.1f}s")
    return np.array(all_embs, dtype=np.float32)


# ── 3. Deduplication ─────────────────────────────────────────────────────────

def cosine_sim_matrix_chunked(embs: np.ndarray, chunk_size: int = 2000) -> None:
    """We don't build the full matrix (too large). Instead, for each item we
    find its top-K nearest neighbors using batched matrix multiply."""
    pass  # see find_duplicates below


def find_cross_source_duplicates(
    items: list[dict],
    embs: np.ndarray,
    threshold: float = SIM_THRESHOLD,
    k: int = 10,
) -> list[tuple[int, int, float]]:
    """Find pairs (i, j) where embs[i] and embs[j] are similar AND from different
    sources. Only searches across source boundaries to keep it tractable."""
    from collections import defaultdict

    # Build per-source index arrays
    source_indices = defaultdict(list)
    for idx, item in enumerate(items):
        source_indices[item["source"]].append(idx)

    sources = list(source_indices.keys())
    pairs = []

    # L2-normalize for cosine similarity
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embs_norm = embs / norms

    t0 = time.time()
    total_comparisons = 0

    # Compare each source pair
    for i_src_idx, src_a in enumerate(sources):
        for src_b in sources[i_src_idx + 1:]:
            idxs_a = np.array(source_indices[src_a])
            idxs_b = np.array(source_indices[src_b])

            # Chunk through source_a
            chunk = 500
            for start in range(0, len(idxs_a), chunk):
                batch_idxs = idxs_a[start:start+chunk]
                batch_embs = embs_norm[batch_idxs]   # (B, D)
                target_embs = embs_norm[idxs_b]       # (N, D)

                # (B, N) similarity matrix
                sims = batch_embs @ target_embs.T      # (B, N)
                total_comparisons += batch_embs.shape[0] * target_embs.shape[0]

                # Find pairs above threshold
                above = np.argwhere(sims >= threshold)
                for b_local, n_local in above:
                    global_i = int(batch_idxs[b_local])
                    global_j = int(idxs_b[n_local])
                    sim = float(sims[b_local, n_local])
                    pairs.append((global_i, global_j, sim))

    elapsed = time.time() - t0
    print(f"  Found {len(pairs):,} duplicate pairs across sources "
          f"(threshold={threshold}, {total_comparisons:,} comparisons, {elapsed:.1f}s)")
    return pairs


def build_clusters(
    items: list[dict],
    pairs: list[tuple[int, int, float]],
) -> list[list[int]]:
    """Union-find to cluster items that are duplicates of each other."""
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, j, _ in pairs:
        union(i, j)

    groups = defaultdict(list)
    for idx in range(len(items)):
        groups[find(idx)].append(idx)

    clusters = list(groups.values())
    print(f"  Clusters: {len(clusters):,} ({sum(1 for c in clusters if len(c) > 1):,} merged)")
    return clusters


def pick_canonical(cluster_indices: list[int], items: list[dict]) -> dict:
    """Pick the best representative for a cluster.
    Priority: wikidata > openalex_topic > jel > openalex_keyword
    Merge metadata from all members.
    """
    SOURCE_PRIORITY = {"wikidata": 0, "openalex_topic": 1, "jel": 2, "openalex_keyword": 3}

    cluster_items = [items[i] for i in cluster_indices]
    cluster_items.sort(key=lambda x: (SOURCE_PRIORITY.get(x["source"], 9), -len(x.get("description", ""))))
    canonical = dict(cluster_items[0])  # copy

    # Merge source annotations from all members
    canonical["_sources"] = []
    for item in cluster_items:
        entry = {"source": item["source"], "id": item["id"], "label": item["label"]}
        # Carry over source-specific fields
        for field in ["jel_code", "jel_level", "jel_label", "paper_count", "mean_score",
                      "subfield", "field", "oa_domain"]:
            if field in item:
                entry[field] = item[field]
        canonical["_sources"].append(entry)

    # Enrich description if canonical lacks one
    if not canonical.get("description"):
        for item in cluster_items:
            if item.get("description"):
                canonical["description"] = item["description"]
                break

    # Add JEL codes if any member has them
    jel_codes = [e["jel_code"] for e in canonical["_sources"] if "jel_code" in e]
    if jel_codes:
        canonical["jel_codes"] = jel_codes

    return canonical


# ── 4. Wikipedia crawl integration ───────────────────────────────────────────

def load_wikipedia_if_ready() -> list[dict]:
    """Load Wikipedia crawl results if available."""
    wp_path = OUT_DIR / "wikipedia_economics_articles.json"
    if not wp_path.exists():
        print("  Wikipedia crawl not yet complete — skipping")
        return []
    with open(wp_path) as f:
        wp_articles = json.load(f)
    print(f"  Wikipedia: {len(wp_articles)} articles")

    # Check if enriched version exists
    wp_enriched_path = OUT_DIR / "wikipedia_economics_articles_enriched.json"
    if wp_enriched_path.exists():
        with open(wp_enriched_path) as f:
            wp_articles = json.load(f)
        print(f"  Wikipedia enriched: {len(wp_articles)} articles")

    out = []
    for a in wp_articles:
        title = a.get("title", "").strip()
        if not title:
            continue
        # Only include articles that passed nano classification
        domain = a.get("domain_clean", a.get("domain", ""))
        if not domain or domain in ("irrelevant", "geography", "method", "noise", "unknown"):
            continue
        out.append({
            "id": f"wp:{a.get('pageid', title)}",
            "label": title,
            "description": a.get("short_desc", "")[:200],
            "source": "wikipedia",
            "domain": domain,
            "wp_categories": a.get("wp_categories", []),
            "depth": a.get("depth", 0),
        })
    print(f"  Wikipedia valid for graph: {len(out)}")
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=== Building merged ontology vocabulary ===\n")

    # 1. Load all sources
    print("Loading sources...")
    wikidata_items = load_wikidata()
    jel_items = load_jel()
    openalex_items = load_openalex(min_papers=3)
    wp_items = load_wikipedia_if_ready()

    all_items = wikidata_items + jel_items + openalex_items + wp_items
    print(f"\nTotal candidates: {len(all_items):,}")

    # Summary by source
    from collections import Counter
    src_counts = Counter(item["source"] for item in all_items)
    for src, n in src_counts.items():
        print(f"  {src}: {n:,}")

    # 2. Build embedding texts (label + description for richer signal)
    print("\nBuilding embedding texts...")
    embed_texts = []
    for item in all_items:
        label = item["label"]
        desc = item.get("description", "").strip()
        if desc:
            text = f"{label}: {desc}"
        else:
            text = label
        embed_texts.append(text[:512])  # truncate for API

    # 3. Embed
    print("\nEmbedding all candidates...")
    embs = await embed_all(embed_texts)

    # Save embeddings for future use
    emb_path = OUT_DIR / "ontology_candidate_embeddings.npy"
    np.save(emb_path, embs)
    print(f"  Embeddings saved to {emb_path}")

    # Also save item list (without embeddings)
    items_path = OUT_DIR / "ontology_candidates.json"
    with open(items_path, "w") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"  Candidates saved to {items_path}")

    # 4. Find cross-source duplicates
    print("\nFinding cross-source duplicates...")
    pairs = find_cross_source_duplicates(all_items, embs, threshold=SIM_THRESHOLD)

    # 5. Build clusters and pick canonical entries
    print("\nClustering and picking canonical entries...")
    clusters = build_clusters(all_items, pairs)
    canonical_entries = [pick_canonical(cluster, all_items) for cluster in clusters]

    # Stats
    n_merged = sum(1 for c in clusters if len(c) > 1)
    n_singleton = sum(1 for c in clusters if len(c) == 1)
    total_before = len(all_items)
    total_after = len(canonical_entries)
    print(f"  Before merge: {total_before:,} candidates")
    print(f"  After merge: {total_after:,} canonical entries")
    print(f"  Merged clusters (size > 1): {n_merged:,}")
    print(f"  Singletons: {n_singleton:,}")
    print(f"  Compression: {total_before/total_after:.2f}x")

    # Source coverage in merged vocab
    print("\nSource representation in merged vocab:")
    src_coverage = Counter()
    for entry in canonical_entries:
        for s in entry.get("_sources", [entry]):
            src_coverage[s.get("source", entry.get("source", "?"))] += 1
    for src, n in src_coverage.most_common():
        print(f"  {src}: {n:,}")

    # Domain distribution (for wikidata-backed entries)
    print("\nDomain distribution (canonical Wikidata entries):")
    domain_counts = Counter(
        e.get("domain", "") for e in canonical_entries if e.get("source") == "wikidata"
    )
    for d, n in domain_counts.most_common(15):
        if d:
            print(f"  {d}: {n:,}")

    # Sample merged clusters (interesting cross-source matches)
    print("\nSample cross-source merges:")
    multi_source_entries = [e for e in canonical_entries if len(e.get("_sources", [])) > 1]
    import random; random.seed(42)
    for entry in random.sample(multi_source_entries, min(10, len(multi_source_entries))):
        sources_str = ", ".join(s["source"] for s in entry["_sources"])
        labels_str = " | ".join(set(s["label"] for s in entry["_sources"]))
        print(f"  [{sources_str}] {labels_str}")

    # 6. Save merged vocabulary
    out_path = OUT_DIR / "ontology_merged.json"
    with open(out_path, "w") as f:
        json.dump(canonical_entries, f, indent=2, ensure_ascii=False)
    print(f"\nMerged vocabulary saved to {out_path}")

    # Save canonical embeddings (one per merged entry)
    print("\nBuilding canonical embeddings (cluster centroids)...")
    canonical_embs = []
    for cluster_indices in clusters:
        cluster_embs = embs[cluster_indices]
        centroid = cluster_embs.mean(axis=0)
        canonical_embs.append(centroid)
    canonical_embs = np.array(canonical_embs, dtype=np.float32)
    canon_emb_path = OUT_DIR / "ontology_merged_embeddings.npy"
    np.save(canon_emb_path, canonical_embs)
    print(f"  Canonical embeddings saved to {canon_emb_path}")

    print("\n=== DONE ===")
    print(f"Final vocabulary: {len(canonical_entries):,} concepts")


if __name__ == "__main__":
    asyncio.run(main())
