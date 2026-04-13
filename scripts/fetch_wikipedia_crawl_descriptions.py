"""Enrich Wikipedia economics crawl results with short descriptions and extracts.

Standalone version that ONLY processes the crawl output (skips Wikidata which is
already done in wikidata_valid_enriched.json).

Input:  data/ontology_v2/wikipedia_economics_articles.json (from crawl)
Output: data/ontology_v2/wikipedia_economics_articles_enriched.json
"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

CONCURRENCY = 30
BATCH_SIZE = 50


async def fetch_batch(session: aiohttp.ClientSession, titles: list[str], sem: asyncio.Semaphore) -> dict:
    titles_str = "|".join(titles)
    params = {
        "action": "query",
        "titles": titles_str,
        "prop": "extracts|pageprops|categories",
        "exintro": "true",
        "exsentences": "3",
        "explaintext": "true",
        "ppprop": "wikibase_item|wikibase-shortdesc",
        "cllimit": "5",
        "clshow": "!hidden",
        "format": "json",
    }
    url = f"https://en.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"

    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    data = await resp.json()
                    results = {}
                    for pid, page in data.get("query", {}).get("pages", {}).items():
                        title = page.get("title", "")
                        props = page.get("pageprops", {})
                        cats = page.get("categories", [])
                        results[title] = {
                            "short_desc": props.get("wikibase-shortdesc", ""),
                            "extract": page.get("extract", ""),
                            "wikidata_id": props.get("wikibase_item", ""),
                            "categories": [c["title"].replace("Category:", "") for c in cats],
                        }
                    return results
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(1)
    return {}


async def fetch_all(titles: list[str]) -> dict:
    sem = asyncio.Semaphore(CONCURRENCY)
    all_results = {}
    completed = 0
    t0 = time.time()
    batches = [titles[i:i+BATCH_SIZE] for i in range(0, len(titles), BATCH_SIZE)]
    print(f"  Fetching {len(titles):,} titles in {len(batches)} batches...")

    async with aiohttp.ClientSession(headers={
        "User-Agent": "FrontierGraph/1.0 (prashant.garg@imperial.ac.uk) research"
    }) as session:
        async def bounded(batch):
            nonlocal completed
            result = await fetch_batch(session, batch, sem)
            completed += 1
            if completed % 100 == 0:
                elapsed = time.time() - t0
                rate = completed / elapsed
                eta = (len(batches) - completed) / rate if rate > 0 else 0
                print(f"    {completed}/{len(batches)} ({rate:.1f}/s, ETA {eta:.0f}s)")
            return result

        results = await asyncio.gather(*[bounded(b) for b in batches])

    for r in results:
        all_results.update(r)

    elapsed = time.time() - t0
    print(f"  Done: {len(all_results):,} in {elapsed:.1f}s ({len(all_results)/elapsed:.0f}/s)")
    has_desc = sum(1 for v in all_results.values() if v["short_desc"])
    has_extract = sum(1 for v in all_results.values() if v["extract"])
    print(f"  Has short_desc: {has_desc:,} ({has_desc/max(len(all_results),1)*100:.1f}%)")
    print(f"  Has extract: {has_extract:,} ({has_extract/max(len(all_results),1)*100:.1f}%)")
    return all_results


async def main():
    crawl_path = OUT_DIR / "wikipedia_economics_articles.json"
    if not crawl_path.exists():
        print("Crawl output not found. Run crawl_wikipedia_economics.py first.")
        return

    print("=== Enriching Wikipedia crawl articles ===")
    with open(crawl_path) as f:
        articles = json.load(f)
    print(f"Articles: {len(articles):,}")

    titles = list(set(a["title"] for a in articles))
    print(f"Unique titles: {len(titles):,}")

    desc_map = await fetch_all(titles)

    # Merge back
    for a in articles:
        desc = desc_map.get(a["title"], {})
        a["short_desc"] = desc.get("short_desc", "")
        a["extract"] = desc.get("extract", "")
        a["wikidata_id"] = desc.get("wikidata_id", "")
        a["wp_categories"] = desc.get("categories", [])

    out_path = OUT_DIR / "wikipedia_economics_articles_enriched.json"
    with open(out_path, "w") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(articles):,} enriched articles to {out_path}")

    # Sample
    import random; random.seed(42)
    print("\nSample:")
    for a in random.sample(articles, min(5, len(articles))):
        print(f"  {a['title']}")
        print(f"    desc: {a.get('short_desc','')[:80]}")
        print(f"    extract: {a.get('extract','')[:100]}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
