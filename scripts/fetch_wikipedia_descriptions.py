"""Fetch short descriptions and extracts from Wikipedia for concept lists.
Works on any list of article titles — Wikidata concepts, Wikipedia crawl results, etc.

Uses Wikipedia API with async for speed. Fetches:
- Short description (wikibase-shortdesc)
- First 3 sentences of the article (extract)
- Wikidata Q-ID
- Categories

Output: enriched JSON with descriptions added to each concept.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.parse
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

CONCURRENCY = 30  # Wikipedia asks for politeness, but async helps
BATCH_SIZE = 50  # Wikipedia API supports up to 50 titles per request


async def fetch_batch(session: aiohttp.ClientSession, titles: list[str], sem: asyncio.Semaphore) -> dict:
    """Fetch descriptions for a batch of up to 50 titles."""
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
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
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
                else:
                    return {}
    return {}


async def fetch_all_descriptions(titles: list[str]) -> dict:
    """Fetch descriptions for all titles."""
    sem = asyncio.Semaphore(CONCURRENCY)
    all_results = {}
    completed = 0
    t0 = time.time()

    batches = [titles[i:i+BATCH_SIZE] for i in range(0, len(titles), BATCH_SIZE)]
    print(f"  Fetching descriptions for {len(titles):,} titles in {len(batches)} batches...")

    async with aiohttp.ClientSession(headers={
        "User-Agent": "FrontierGraph/1.0 (prashant.garg@imperial.ac.uk) research"
    }) as session:
        async def bounded_fetch(batch, batch_idx):
            nonlocal completed
            result = await fetch_batch(session, batch, sem)
            completed += 1
            if completed % 50 == 0:
                elapsed = time.time() - t0
                rate = completed / elapsed
                eta = (len(batches) - completed) / rate if rate > 0 else 0
                print(f"    {completed}/{len(batches)} batches ({rate:.1f}/s, ETA {eta:.0f}s)")
            return result

        tasks = [bounded_fetch(b, i) for i, b in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)

    for br in batch_results:
        all_results.update(br)

    elapsed = time.time() - t0
    print(f"  Done: {len(all_results):,} descriptions in {elapsed:.1f}s")

    # Stats
    has_desc = sum(1 for v in all_results.values() if v["short_desc"])
    has_extract = sum(1 for v in all_results.values() if v["extract"])
    has_qid = sum(1 for v in all_results.values() if v["wikidata_id"])
    print(f"  Has short_desc: {has_desc:,} ({has_desc/max(len(all_results),1)*100:.1f}%)")
    print(f"  Has extract: {has_extract:,} ({has_extract/max(len(all_results),1)*100:.1f}%)")
    print(f"  Has wikidata_id: {has_qid:,} ({has_qid/max(len(all_results),1)*100:.1f}%)")

    return all_results


async def main():
    # Task 1: Enrich Wikidata valid concepts with Wikipedia descriptions
    print("=== Enriching Wikidata valid concepts ===")
    with open(OUT_DIR / "wikidata_valid_concepts_clean.json") as f:
        wiki_concepts = json.load(f)
    print(f"  Wikidata concepts: {len(wiki_concepts)}")

    titles = [c["label"] for c in wiki_concepts]
    # Deduplicate
    unique_titles = list(set(titles))
    print(f"  Unique titles to fetch: {len(unique_titles)}")

    desc_map = await fetch_all_descriptions(unique_titles)

    # Merge back
    for c in wiki_concepts:
        desc = desc_map.get(c["label"], {})
        c["short_desc"] = desc.get("short_desc", "")
        c["extract"] = desc.get("extract", "")
        c["wikidata_id_from_wp"] = desc.get("wikidata_id", "")
        c["wp_categories"] = desc.get("categories", [])

    out_path = OUT_DIR / "wikidata_valid_enriched.json"
    with open(out_path, "w") as f:
        json.dump(wiki_concepts, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {out_path}")

    # Task 2: If Wikipedia crawl results exist, enrich those too
    wp_crawl_path = OUT_DIR / "wikipedia_economics_articles.json"
    if wp_crawl_path.exists():
        print(f"\n=== Enriching Wikipedia crawl results ===")
        with open(wp_crawl_path) as f:
            wp_articles = json.load(f)
        print(f"  Articles: {len(wp_articles)}")

        titles = list(set(a["title"] for a in wp_articles))
        print(f"  Unique titles: {len(titles)}")

        desc_map = await fetch_all_descriptions(titles)

        for a in wp_articles:
            desc = desc_map.get(a["title"], {})
            a["short_desc"] = desc.get("short_desc", "")
            a["extract"] = desc.get("extract", "")
            a["wikidata_id"] = desc.get("wikidata_id", "")
            a["wp_categories"] = desc.get("categories", [])

        out_path = OUT_DIR / "wikipedia_economics_articles_enriched.json"
        with open(out_path, "w") as f:
            json.dump(wp_articles, f, indent=2, ensure_ascii=False)
        print(f"  Saved to {out_path}")

        # Stats
        has_desc = sum(1 for a in wp_articles if a.get("short_desc"))
        has_extract = sum(1 for a in wp_articles if a.get("extract"))
        print(f"  With short_desc: {has_desc:,} ({has_desc/len(wp_articles)*100:.1f}%)")
        print(f"  With extract: {has_extract:,} ({has_extract/len(wp_articles)*100:.1f}%)")

        # Sample
        print(f"\n  Sample enriched articles:")
        import random
        random.seed(42)
        for a in random.sample(wp_articles, min(5, len(wp_articles))):
            print(f"    {a['title']}")
            print(f"      desc: {a.get('short_desc', '')[:80]}")
            print(f"      extract: {a.get('extract', '')[:120]}")
            print()
    else:
        print(f"\n  Wikipedia crawl not complete yet — will enrich when available")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
