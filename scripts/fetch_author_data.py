"""Fetch author data from OpenAlex for all papers in the corpus.

Uses 3 API keys in round-robin for higher throughput.
OpenAlex works API: filter by work IDs, retrieve authorships.
Async with high concurrency since OpenAlex polite pool allows ~10 req/s per key.

Output: data/processed/research_allocation_v2/paper_authorships.parquet
  Columns: paper_id, work_id, author_id, author_name, author_position, institution_id
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
OUT_PATH = ROOT / "data/processed/research_allocation_v2/paper_authorships.parquet"

# Load API keys (email addresses for polite pool)
KEYS = []
for f in sorted(KEY_DIR.glob("openalex_key_*.txt")):
    KEYS.append(f.read_text().strip())
print(f"Loaded {len(KEYS)} OpenAlex API keys")

CONCURRENCY_PER_KEY = 8  # OpenAlex allows ~10 req/s per polite email
BATCH_SIZE = 50  # works per API call (OpenAlex filter supports pipe-separated IDs)


async def fetch_batch(session, work_ids: list[str], key_idx: int) -> list[dict]:
    """Fetch authorships for a batch of work IDs."""
    import aiohttp

    # Build filter: work IDs pipe-separated
    # OpenAlex format: openalex_id without the URL prefix
    clean_ids = []
    for wid in work_ids:
        if wid.startswith("https://openalex.org/"):
            clean_ids.append(wid.replace("https://openalex.org/", ""))
        elif wid.startswith("W"):
            clean_ids.append(wid)
        else:
            clean_ids.append(wid)

    filter_str = "|".join(clean_ids)
    url = f"https://api.openalex.org/works?filter=openalex:{filter_str}&select=id,authorships&per_page={BATCH_SIZE}&mailto={KEYS[key_idx % len(KEYS)]}"

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
                    for auth in work.get("authorships", []):
                        author = auth.get("author", {})
                        institutions = auth.get("institutions", [])
                        inst_id = institutions[0].get("id", "") if institutions else ""
                        results.append({
                            "work_id": work_id,
                            "author_id": author.get("id", ""),
                            "author_name": author.get("display_name", ""),
                            "author_position": auth.get("author_position", ""),
                            "institution_id": inst_id,
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

    # Load paper IDs
    funding = pd.read_parquet(ROOT / "data/processed/research_allocation_v2/hybrid_papers_funding.parquet")
    paper_map = dict(zip(funding["openalex_work_id"].astype(str), funding["paper_id"].astype(str)))
    all_work_ids = list(paper_map.keys())
    print(f"Total papers to fetch: {len(all_work_ids)}")

    # Check if we already have partial results
    if OUT_PATH.exists():
        existing = pd.read_parquet(OUT_PATH)
        existing_wids = set(existing["work_id"].astype(str))
        remaining = [wid for wid in all_work_ids if wid not in existing_wids]
        print(f"Already have {len(existing_wids)} work_ids, {len(remaining)} remaining")
        if not remaining:
            print("All done!")
            return
    else:
        remaining = all_work_ids
        existing = pd.DataFrame()

    # Batch the work IDs
    batches = [remaining[i:i+BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    print(f"Fetching {len(batches)} batches of {BATCH_SIZE}...")

    sem = asyncio.Semaphore(CONCURRENCY_PER_KEY * len(KEYS))
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
                    rate = completed / elapsed
                    eta = (len(batches) - completed) / rate if rate > 0 else 0
                    print(f"  {completed}/{len(batches)} batches ({rate:.1f}/s, ETA {eta:.0f}s)")
                return result

        tasks = [bounded_fetch(batch, i) for i, batch in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)

    for br in batch_results:
        all_results.extend(br)

    print(f"\nFetched {len(all_results)} authorship rows in {time.time()-t0:.1f}s")

    # Build dataframe
    new_df = pd.DataFrame(all_results)
    if not new_df.empty:
        # Map work_id back to paper_id
        new_df["paper_id"] = new_df["work_id"].map(paper_map)

        # Combine with existing
        if not existing.empty:
            combined = pd.concat([existing, new_df], ignore_index=True).drop_duplicates(["work_id", "author_id"])
        else:
            combined = new_df
    else:
        combined = existing

    combined.to_parquet(OUT_PATH, index=False)
    print(f"Saved {len(combined)} authorship rows to {OUT_PATH}")

    # Stats
    print(f"\nStats:")
    print(f"  Unique papers with authors: {combined['work_id'].nunique()}")
    print(f"  Unique authors: {combined['author_id'].nunique()}")
    print(f"  Unique institutions: {combined['institution_id'].nunique()}")
    print(f"  Mean authors per paper: {combined.groupby('work_id').size().mean():.1f}")


if __name__ == "__main__":
    asyncio.run(main())
