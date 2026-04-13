"""Master pipeline: build the complete v2 ontology vocabulary.

Run after:
  1. crawl_wikipedia_economics.py (produces wikipedia_economics_articles.json)
  2. fetch_wikipedia_descriptions.py (enriches with short_desc + extract)
  3. classify_wikipedia_articles.py (produces wikipedia_valid.json)

This script:
  A. Re-merges JEL + OpenAlex + Wikidata + Wikipedia valid articles
  B. Embeds everything with label + description
  C. Deduplicates cross-source duplicates (two-pass)
     Pass 1 – exact label match (case-insensitive): catches within-source QID
              repetitions in Wikidata and cross-source label collisions missed
              by embedding similarity.  Canonical entry chosen by SOURCE_PRIORITY.
     Pass 2 – cosine similarity >= SIM_THRESHOLD (0.93): catches spelling
              variants and near-synonyms across sources (e.g. "electronic
              medical record" vs "Electronic medical record").
  D. Builds the final ontology with structured metadata
  E. Aligns against the production 6752 concepts
  F. Outputs summary stats and coverage analysis

Design decisions (for paper methods section):
  SOURCE_PRIORITY  jel > wikidata > openalex_topic > openalex_keyword > wikipedia
    JEL is the authoritative economics taxonomy; its labels are preferred when
    a conflict exists.  Wikidata labels carry structured Wikidata QIDs and are
    more precise than free-form OpenAlex keywords.  Wikipedia is last because
    its article titles can be disambiguation-heavy (e.g. "Banana republic
    (clothing)") even after classification filtering.
  SIM_THRESHOLD 0.93
    Chosen to collapse near-identical surface forms (capitalisation, singular/
    plural, minor word-order differences) while retaining semantically distinct
    concepts such as "Inflation" and "Inflation rate".  At 0.93 the false-merge
    rate on a 200-pair manual spot-check was <2 %.
  Wikipedia inclusion (133 542 articles after richer classification)
    Added for coverage of fine-grained concepts (country-level policies, named
    instruments, historical events) that appear in raw extraction labels but are
    absent from JEL/OpenAlex/Wikidata.  The richer classification (title +
    Wikipedia short description + category path, gpt-4.1-nano, $3.69) reduced
    the built-in depth-5 crawler count from 178 957 (96.9 % acceptance, title +
    category only) to 133 542 (72.3 % acceptance), trading recall for precision.

Final output: data/ontology_v2/ontology_v2_final.json
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
SIM_THRESHOLD = 0.93   # for cross-source dedup
LINK_THRESHOLD = 0.85  # for production alignment


VALID_DOMAINS = {
    "econ_core", "econ_applied", "finance", "health", "environment",
    "education", "demographics", "politics", "institutions", "technology",
    "events", "commodities", "behavior", "other_valid"
}


# ── Embedding ─────────────────────────────────────────────────────────────────

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
    print(f"  Embedding {len(texts):,} {label} texts in {len(batches)} batches...")
    t0 = time.time()
    completed = 0

    async def bounded(batch):
        nonlocal completed
        result = await embed_batch(client, batch, sem)
        completed += 1
        if completed % 20 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(batches) - completed) / rate if rate > 0 else 0
            print(f"    {completed}/{len(batches)} batches ({rate:.1f}/s, ETA {eta:.0f}s)")
        return result

    results = await asyncio.gather(*[bounded(b) for b in batches])
    flat = [e for batch_result in results for e in batch_result]
    print(f"  Done: {len(flat):,} in {time.time()-t0:.1f}s")
    return np.array(flat, dtype=np.float32)


def normalize(embs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return embs / norms


# ── Sources ───────────────────────────────────────────────────────────────────

def load_wikidata() -> list[dict]:
    with open(OUT_DIR / "wikidata_valid_enriched.json") as f:
        concepts = json.load(f)
    out = []
    seen_qids: set[str] = set()   # Fix: upstream file contains duplicate QIDs
    for c in concepts:
        label = c.get("label", "").strip()
        if not label:
            continue
        qid = c["qid"]
        if qid in seen_qids:       # deduplicate at source level by QID
            continue
        seen_qids.add(qid)
        desc = c.get("description", "") or c.get("short_desc", "") or ""
        out.append({
            "id": qid,
            "label": label,
            "description": desc[:200],
            "source": "wikidata",
            "domain": c.get("domain_voted", c.get("domain_clean", "")),
            "parent_label": c.get("parent_label", ""),
            "root_label": c.get("root_label", ""),
        })
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
            "description": guideline[:150] if guideline else "",
            "source": "jel",
            "jel_code": code,
            "jel_label": code_label,
            "jel_level": level,
            "domain": "econ_core",
        })

    for l1_code, info in jel_data.items():
        g1 = info.get("guideline", "")
        for kw in info.get("keywords", []):
            add(kw, l1_code, 1, l1_code, g1)
        for l2 in info.get("l2_codes", []):
            g2 = l2.get("guideline", "")
            for kw in l2.get("keywords", []):
                add(kw, l2["code"], 2, l2.get("title", ""), g2)
            for l3 in l2.get("l3_codes", []):
                g3 = l3.get("guideline", "")
                for kw in l3.get("keywords", []):
                    add(kw, l3["code"], 3, l3.get("title", ""), g3)
    return out


def load_openalex(min_papers: int = 3) -> list[dict]:
    df = pd.read_parquet(OUT_DIR / "openalex_paper_keywords.parquet")
    kw_df = df[df["type"] == "keyword"]
    kw_counts = kw_df.groupby("display_name").agg(
        paper_count=("work_id", "nunique"),
        mean_score=("score", "mean"),
        item_id=("item_id", "first"),
    ).reset_index()
    kw_counts = kw_counts[kw_counts["paper_count"] >= min_papers]

    kw_out = [
        {
            "id": row["item_id"],
            "label": row["display_name"],
            "description": "",
            "source": "openalex_keyword",
            "paper_count": int(row["paper_count"]),
        }
        for _, row in kw_counts.iterrows()
    ]

    topic_df = df[df["type"] == "topic"]
    topic_counts = topic_df.groupby("display_name").agg(
        paper_count=("work_id", "nunique"),
        subfield=("subfield", "first"),
        field=("field", "first"),
        item_id=("item_id", "first"),
    ).reset_index()

    topic_out = [
        {
            "id": row["item_id"],
            "label": row["display_name"],
            "description": str(row.get("field", "") or ""),
            "source": "openalex_topic",
            "paper_count": int(row["paper_count"]),
        }
        for _, row in topic_counts.iterrows()
    ]
    return kw_out + topic_out


def load_wikipedia() -> list[dict]:
    valid_path = OUT_DIR / "wikipedia_valid.json"
    if not valid_path.exists():
        print("  Wikipedia valid not found — run classify_wikipedia_articles.py first")
        return []
    with open(valid_path) as f:
        data = json.load(f)
    out = []
    n_wd_desc = 0
    for a in data:
        title = a.get("title", "").strip()
        if not title:
            continue
        # Description priority:
        #   1. wikidata_desc  — curated, concise, Wikidata-sourced
        #   2. short_desc     — Wikipedia API short description
        #   3. llm_desc       — gpt-4.1-nano generated for short ambiguous titles
        wikidata_desc = (a.get("wikidata_desc") or "").strip()
        short_desc    = (a.get("short_desc")    or "").strip()
        llm_desc      = (a.get("llm_desc")      or "").strip()
        desc = wikidata_desc or short_desc or llm_desc
        if wikidata_desc:
            n_wd_desc += 1
        out.append({
            "id": f"wp:{a.get('pageid', title)}",
            "label": title,
            "description": desc[:200],
            "source": "wikipedia",
            "domain": a.get("domain", ""),
            "confidence": a.get("confidence", ""),
            "depth": a.get("depth", 0),
            "wikidata_id": a.get("wikidata_id", ""),
        })
    n_llm_desc  = sum(1 for a in data if (a.get("llm_desc") or "").strip()
                                          and not (a.get("wikidata_desc") or "").strip()
                                          and not (a.get("short_desc") or "").strip())
    n_wp_desc   = sum(1 for a in data if (a.get("short_desc") or "").strip()
                                          and not (a.get("wikidata_desc") or "").strip())
    n_any = n_wd_desc + n_llm_desc + n_wp_desc
    print(f"  Wikipedia valid: {len(out):,}")
    print(f"    Wikidata desc: {n_wd_desc:,} | WP short_desc: {n_wp_desc:,} | LLM desc: {n_llm_desc:,}")
    print(f"    Any desc:      {n_any:,} ({n_any/len(out)*100:.0f}%)")
    return out


# ── Deduplication ─────────────────────────────────────────────────────────────

def exact_label_dedup(items: list[dict]) -> tuple[list[dict], int]:
    """Pass-1 dedup: collapse entries with identical labels (case-insensitive).

    Rationale: cosine similarity at 0.93 does not catch exact string matches
    when embeddings contain a zero vector (OpenAI API fallback), or when two
    entries are within the same source (the cross-source similarity loop only
    compares across sources).  Exact-label dedup is cheap, deterministic, and
    catches both intra-source QID repetitions and cross-source collisions that
    share the same surface form.

    Within each label group the canonical entry is chosen by SOURCE_PRIORITY;
    ties broken by longer description (more informative).
    """
    SOURCE_PRIORITY = {
        "jel": 0, "wikidata": 1, "openalex_topic": 2,
        "openalex_keyword": 3, "wikipedia": 4
    }
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        key = item["label"].lower().strip()
        groups[key].append(item)

    out = []
    n_merged = 0
    for key, group in groups.items():
        if len(group) == 1:
            out.append(group[0])
            continue
        n_merged += len(group) - 1
        group.sort(key=lambda x: (
            SOURCE_PRIORITY.get(x["source"], 9),
            -len(x.get("description", ""))
        ))
        canon = dict(group[0])
        # Merge _sources from all duplicates
        existing = canon.get("_sources", [{"source": canon["source"], "id": canon["id"], "label": canon["label"]}])
        for it in group[1:]:
            existing.append({"source": it["source"], "id": it["id"], "label": it["label"]})
        canon["_sources"] = existing
        # Inherit best description
        if not canon.get("description"):
            for it in group[1:]:
                if it.get("description"):
                    canon["description"] = it["description"]
                    break
        # Collect any JEL codes
        jel_codes = [it.get("jel_code") for it in group if it.get("jel_code")]
        if jel_codes:
            canon["jel_codes"] = jel_codes
        out.append(canon)
    return out, n_merged


def find_cross_source_duplicates(items, embs, threshold=SIM_THRESHOLD):
    source_indices = defaultdict(list)
    for idx, item in enumerate(items):
        source_indices[item["source"]].append(idx)

    sources = list(source_indices.keys())
    pairs = []
    norm = normalize(embs)

    for i_idx, src_a in enumerate(sources):
        for src_b in sources[i_idx + 1:]:
            idxs_a = np.array(source_indices[src_a])
            idxs_b = np.array(source_indices[src_b])

            chunk = 500
            for start in range(0, len(idxs_a), chunk):
                batch_idxs = idxs_a[start:start+chunk]
                batch_embs = norm[batch_idxs]
                target_embs = norm[idxs_b]
                sims = batch_embs @ target_embs.T
                above = np.argwhere(sims >= threshold)
                for b_local, n_local in above:
                    pairs.append((
                        int(batch_idxs[b_local]),
                        int(idxs_b[n_local]),
                        float(sims[b_local, n_local])
                    ))
    return pairs


def build_clusters_and_canonicalize(items, pairs):
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

    # JEL first: authoritative economics taxonomy with controlled vocabulary.
    # Wikidata second: QID-grounded, structured descriptions.
    # OpenAlex topic third: peer-reviewed field classification.
    # OpenAlex keyword fourth: free-form but high-frequency signal.
    # Wikipedia last: broad coverage but noisiest labels.
    SOURCE_PRIORITY = {
        "jel": 0, "wikidata": 1, "openalex_topic": 2,
        "openalex_keyword": 3, "wikipedia": 4
    }

    canonical = []
    clusters = list(groups.values())

    for cluster_indices in clusters:
        cluster_items = [items[i] for i in cluster_indices]
        cluster_items.sort(key=lambda x: (SOURCE_PRIORITY.get(x["source"], 9), -len(x.get("description", ""))))
        canon = dict(cluster_items[0])
        canon["_sources"] = [{"source": it["source"], "id": it["id"], "label": it["label"]} for it in cluster_items]

        if not canon.get("description"):
            for it in cluster_items:
                if it.get("description"):
                    canon["description"] = it["description"]
                    break

        jel_codes = [it.get("jel_code") for it in cluster_items if it.get("jel_code")]
        if jel_codes:
            canon["jel_codes"] = jel_codes

        canonical.append(canon)

    return canonical, clusters


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=== Building ontology v2 (full pipeline) ===\n")

    print("Loading sources...")
    wikidata = load_wikidata()
    jel = load_jel()
    openalex = load_openalex()
    wikipedia = load_wikipedia()

    all_items = wikidata + jel + openalex + wikipedia
    print(f"\nTotal candidates: {len(all_items):,}")
    for src, n in Counter(i["source"] for i in all_items).items():
        print(f"  {src}: {n:,}")

    # --- Pass 1: exact label dedup (cheap, handles Wikidata QID repetitions
    #             and cross-source label collisions with identical surface forms)
    print("\nPass 1 – exact label dedup...")
    n_before_exact = len(all_items)
    all_items, n_exact_merged = exact_label_dedup(all_items)
    print(f"  {n_before_exact:,} → {len(all_items):,} "
          f"({n_exact_merged:,} duplicates removed)")

    # Build embedding texts
    embed_texts = []
    for item in all_items:
        label = item["label"]
        desc = item.get("description", "").strip()
        text = f"{label}: {desc}" if desc else label
        embed_texts.append(text[:512])

    # Embed
    print("\nEmbedding...")
    embs = await embed_all(embed_texts, "all candidates")

    # --- Pass 2: cosine similarity dedup (catches spelling variants, different
    #             capitalisations that survived exact dedup, near-synonyms)
    print(f"\nPass 2 – cosine similarity dedup (threshold={SIM_THRESHOLD})...")
    pairs = find_cross_source_duplicates(all_items, embs)
    print(f"  Found {len(pairs):,} near-duplicate pairs")

    # Canonicalize
    print("\nClustering...")
    canonical, clusters = build_clusters_and_canonicalize(all_items, pairs)
    print(f"  {len(all_items):,} → {len(canonical):,} canonical entries")
    print(f"  Merged {sum(1 for c in clusters if len(c)>1):,} clusters")

    # Domain distribution
    domain_counts = Counter(e.get("domain", "") for e in canonical)
    valid_count = sum(n for d, n in domain_counts.items() if d in VALID_DOMAINS)
    print(f"\nDomain distribution (canonical):")
    print(f"  Valid: {valid_count:,} / {len(canonical):,}")
    for d, n in domain_counts.most_common(15):
        if d:
            marker = " ✓" if d in VALID_DOMAINS else ""
            print(f"  {d:20s}: {n:6,}{marker}")

    # Align with production concepts
    print("\nAligning with production concepts...")
    canon_df = pd.read_parquet(PROCESSED_DIR / "canonical_concepts.parquet")
    prod_labels = canon_df["preferred_label"].tolist()
    prod_ids = canon_df["concept_id"].tolist()

    # Use label-only embeddings for alignment
    vocab_label_embs = await embed_all([item["label"] for item in all_items], "vocab labels")
    prod_embs = await embed_all(prod_labels, "production")

    vocab_norm = normalize(vocab_label_embs)
    prod_norm = normalize(prod_embs)

    # Find nearest matches
    all_best_scores = []
    chunk_size = 500
    for start in range(0, len(prod_norm), chunk_size):
        batch = prod_norm[start:start+chunk_size]
        sims = batch @ vocab_norm.T
        best_scores = sims.max(axis=1)
        all_best_scores.extend(best_scores.tolist())

    linked = sum(1 for s in all_best_scores if s >= LINK_THRESHOLD)
    soft = sum(1 for s in all_best_scores if 0.75 <= s < LINK_THRESHOLD)
    unlinked = sum(1 for s in all_best_scores if s < 0.75)

    print(f"\nProduction alignment:")
    print(f"  Total production concepts: {len(prod_labels):,}")
    print(f"  Linked (cos >= {LINK_THRESHOLD}): {linked:,} ({linked/len(prod_labels)*100:.1f}%)")
    print(f"  Soft link (0.75-{LINK_THRESHOLD}): {soft:,} ({soft/len(prod_labels)*100:.1f}%)")
    print(f"  Unlinked (cos < 0.75): {unlinked:,} ({unlinked/len(prod_labels)*100:.1f}%)")

    # Save
    out_path = OUT_DIR / "ontology_v2_final.json"
    with open(out_path, "w") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(canonical):,} concepts to {out_path}")

    # Save embeddings
    # Build canonical embeddings as cluster centroids
    canon_embs = []
    for cluster_indices in clusters:
        centroid = embs[cluster_indices].mean(axis=0)
        canon_embs.append(centroid)
    canon_embs = np.array(canon_embs, dtype=np.float32)
    np.save(OUT_DIR / "ontology_v2_embeddings.npy", canon_embs)
    print(f"Saved embeddings to ontology_v2_embeddings.npy")

    print("\n=== DONE ===")
    src_counts = Counter(c["source"] for c in canonical)
    print(f"Final vocabulary: {len(canonical):,} concepts")
    print(f"  Raw candidates:       {n_before_exact:,}")
    print(f"  After exact dedup:    {n_before_exact - n_exact_merged:,}  (-{n_exact_merged:,})")
    print(f"  After cosine dedup:   {len(canonical):,}  (-{(n_before_exact - n_exact_merged) - len(canonical):,})")
    print(f"\nBy source:")
    for src, n in src_counts.most_common():
        print(f"  {src}: {n:,}")


if __name__ == "__main__":
    asyncio.run(main())
