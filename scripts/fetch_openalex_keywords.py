"""Fetch OpenAlex keywords and topics for all papers in the corpus.

Uses 3 API keys in round-robin for higher throughput.
Fetches: keywords (with scores) and topics (with hierarchy) per work.

Output: data/ontology_v2/openalex_paper_keywords.parquet
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEY_DIR = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key")
OUT_DIR = ROOT / "data/ontology_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

KEYS = [f.read_text().strip() for f in sorted(KEY_DIR.glob("openalex_key_*.txt"))]
print(f"Loaded {len(KEYS)} OpenAlex API keys")

BATCH_SIZE = 50
CONCURRENCY = 8 * len(KEYS)


async def fetch_batch(session, work_ids: list[str], key_idx: int) -> list[dict]:
    import aiohttp

    clean_ids = [wid.replace("https://openalex.org/", "") for wid in work_ids]
    filter_str = "|".join(clean_ids)
    url = (f"https://api.openalex.org/works?filter=openalex:{filter_str}"
           f"&select=id,keywords,topics&per_page={BATCH_SIZE}"
           f"&mailto={KEYS[key_idx % len(KEYS)]}")

    for attempt in range(3):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for work in data.get("results", []):
                    work_id = work.get("id", "")
                    # Keywords
                    for kw in work.get("keywords", []):
                        results.append({
                            "work_id": work_id,
                            "type": "keyword",
                            "item_id": kw.get("id", ""),
                            "display_name": kw.get("display_name", ""),
                            "score": kw.get("score", 0),
                            "subfield": "",
                            "field": "",
                            "domain": "",
                        })
                    # Topics
                    for topic in work.get("topics", []):
                        results.append({
                            "work_id": work_id,
                            "type": "topic",
                            "item_id": topic.get("id", ""),
                            "display_name": topic.get("display_name", ""),
                            "score": topic.get("score", 0),
                            "subfield": topic.get("subfield", {}).get("display_name", ""),
                            "field": topic.get("field", {}).get("display_name", ""),
                            "domain": topic.get("domain", {}).get("display_name", ""),
                        })
                return results
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
            else:
                return []
    return []


async def main():
    import aiohttp

    out_path = OUT_DIR / "openalex_paper_keywords.parquet"

    # Load paper IDs
    funding = pd.read_parquet(ROOT / "data/processed/research_allocation_v2/hybrid_papers_funding.parquet")
    all_work_ids = funding["openalex_work_id"].astype(str).tolist()
    print(f"Total papers: {len(all_work_ids)}")

    # Check for existing partial results
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        existing_wids = set(existing["work_id"].astype(str))
        remaining = [wid for wid in all_work_ids if wid not in existing_wids]
        print(f"Already have {len(existing_wids)} papers, {len(remaining)} remaining")
        if not remaining:
            print("All done!")
            return
    else:
        remaining = all_work_ids
        existing = pd.DataFrame()

    batches = [remaining[i:i+BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    print(f"Fetching {len(batches)} batches...")

    sem = asyncio.Semaphore(CONCURRENCY)
    all_results = []
    completed = 0
    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        async def bounded_fetch(batch, batch_idx):
            nonlocal completed
            async with sem:
                result = await fetch_batch(session, batch, batch_idx)
                completed += 1
                if completed % 100 == 0:
                    elapsed = time.time() - t0
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (len(batches) - completed) / rate if rate > 0 else 0
                    print(f"  {completed}/{len(batches)} batches ({rate:.1f}/s, ETA {eta:.0f}s)")
                return result

        tasks = [bounded_fetch(b, i) for i, b in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)

    for br in batch_results:
        all_results.extend(br)

    print(f"\nFetched {len(all_results)} keyword/topic rows in {time.time()-t0:.1f}s")

    new_df = pd.DataFrame(all_results)
    if not new_df.empty and not existing.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
    elif not new_df.empty:
        combined = new_df
    else:
        combined = existing

    combined.to_parquet(out_path, index=False)
    print(f"Saved {len(combined)} rows to {out_path}")

    # Stats
    keywords = combined[combined["type"] == "keyword"]
    topics = combined[combined["type"] == "topic"]
    print(f"\nStats:")
    print(f"  Papers with keywords: {keywords['work_id'].nunique()}")
    print(f"  Unique keywords: {keywords['display_name'].nunique()}")
    print(f"  Papers with topics: {topics['work_id'].nunique()}")
    print(f"  Unique topics: {topics['display_name'].nunique()}")
    print(f"  Unique subfields: {topics['subfield'].nunique()}")
    print(f"\n  Top 20 keywords:")
    for kw, count in keywords["display_name"].value_counts().head(20).items():
        print(f"    {count:6,}  {kw}")


if __name__ == "__main__":
    asyncio.run(main())
