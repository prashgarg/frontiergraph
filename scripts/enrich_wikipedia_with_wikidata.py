"""Enrich Wikipedia valid articles with Wikidata descriptions.

For each valid Wikipedia article that has a Wikidata QID (from the Wikipedia
API sitelinks), fetches the Wikidata English label and description via the
wbgetentities batch API.  Wikidata descriptions are typically shorter and more
precise than Wikipedia's short_desc (e.g. "branch of economics concerned with
how auctions work" vs a truncated first sentence).

The enriched descriptions are written as a new field `wikidata_desc` in
wikipedia_valid.json alongside the existing `short_desc`, so downstream scripts
can choose which to prefer.

Input:
    data/ontology_v2/wikipedia_valid.json          (133,542 articles)
    data/ontology_v2/wikipedia_economics_articles_enriched.json  (wikidata_id map)

Output:
    data/ontology_v2/wikipedia_valid.json           (updated in place)
    + new fields: wikidata_id, wikidata_label, wikidata_desc on each article

Design choice (for paper):
    We prefer Wikidata descriptions over Wikipedia short_desc when available,
    because Wikidata descriptions are human-curated to be concise and
    unambiguous (median ~5 words vs ~15 words for Wikipedia short_desc).
    The wikidata_desc is stored separately so the preference can be changed.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
BATCH_SIZE = 50
CONCURRENCY = 30
RATE_LIMIT = 0.1   # seconds between requests per worker


async def fetch_batch(session: aiohttp.ClientSession,
                      qids: list[str],
                      sem: asyncio.Semaphore) -> dict[str, dict]:
    """Fetch labels + descriptions for a batch of QIDs."""
    async with sem:
        params = {
            "action": "wbgetentities",
            "ids": "|".join(qids),
            "props": "labels|descriptions",
            "languages": "en",
            "format": "json",
        }
        for attempt in range(4):
            try:
                async with session.get(WIKIDATA_API, params=params,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    data = await resp.json()
                    results = {}
                    for qid, entity in data.get("entities", {}).items():
                        if "missing" in entity:
                            continue
                        label = (entity.get("labels", {})
                                       .get("en", {})
                                       .get("value", ""))
                        desc  = (entity.get("descriptions", {})
                                       .get("en", {})
                                       .get("value", ""))
                        results[qid] = {"label": label, "desc": desc}
                    await asyncio.sleep(RATE_LIMIT)
                    return results
            except Exception as e:
                if attempt == 3:
                    print(f"  [warn] batch failed after 4 attempts: {e}")
                    return {}
                await asyncio.sleep(1.5 ** attempt)
    return {}


async def fetch_all(qids: list[str]) -> dict[str, dict]:
    batches = [qids[i:i+BATCH_SIZE] for i in range(0, len(qids), BATCH_SIZE)]
    print(f"  Fetching {len(qids):,} QIDs in {len(batches):,} batches "
          f"(concurrency={CONCURRENCY})...")

    sem = asyncio.Semaphore(CONCURRENCY)
    all_results: dict[str, dict] = {}
    t0 = time.time()

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    headers = {"User-Agent": "OntologyBuilder/1.0 (research; contact prashgarg@example.com)"}
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [fetch_batch(session, batch, sem) for batch in batches]
        n_done = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            all_results.update(result)
            n_done += 1
            if n_done % 100 == 0:
                elapsed = time.time() - t0
                rate = n_done / elapsed
                eta = (len(batches) - n_done) / rate if rate > 0 else 0
                print(f"    {n_done}/{len(batches)} batches "
                      f"({rate:.1f}/s, ETA {eta:.0f}s)")

    elapsed = time.time() - t0
    print(f"  Done: {len(all_results):,} QIDs resolved in {elapsed:.1f}s")
    return all_results


async def main():
    print("=== Enriching Wikipedia articles with Wikidata descriptions ===\n")

    # Load valid articles
    valid_path = OUT_DIR / "wikipedia_valid.json"
    valid = json.load(open(valid_path))
    print(f"Valid Wikipedia articles: {len(valid):,}")

    # Load enriched articles to get the wikidata_id mapping
    enriched_path = OUT_DIR / "wikipedia_economics_articles_enriched.json"
    enriched = json.load(open(enriched_path))
    title_to_wdid = {
        a["title"]: a["wikidata_id"].strip()
        for a in enriched
        if a.get("wikidata_id", "").strip()
    }
    print(f"Title→QID map: {len(title_to_wdid):,} entries")

    # Load existing Wikidata pull so we can reuse descriptions we already have
    wd_path = OUT_DIR / "wikidata_valid_enriched.json"
    existing_wd = json.load(open(wd_path))
    existing_qid_map = {
        c["qid"]: {
            "label": c.get("label", ""),
            "desc": c.get("description", "") or c.get("short_desc", "")
        }
        for c in existing_wd
    }
    print(f"Existing Wikidata pull: {len(existing_qid_map):,} QIDs\n")

    # Collect QIDs that need fresh fetching
    qids_needed: set[str] = set()
    for article in valid:
        qid = title_to_wdid.get(article["title"], "")
        if qid and qid not in existing_qid_map:
            qids_needed.add(qid)

    already_have = sum(
        1 for a in valid
        if title_to_wdid.get(a["title"], "") in existing_qid_map
    )
    print(f"Articles with QID already in Wikidata pull: {already_have:,}")
    print(f"QIDs to fetch fresh from Wikidata API:      {len(qids_needed):,}")

    # Fetch
    fresh = await fetch_all(list(qids_needed))

    # Combine: existing pull + freshly fetched
    full_qid_map = {**existing_qid_map, **fresh}

    # Merge back into valid articles
    n_wd_desc = 0
    n_wp_desc = 0
    n_no_desc = 0

    for article in valid:
        title = article["title"]
        qid = title_to_wdid.get(title, "")
        article["wikidata_id"] = qid

        if qid and qid in full_qid_map:
            wd = full_qid_map[qid]
            article["wikidata_label"] = wd.get("label", "")
            article["wikidata_desc"]  = wd.get("desc", "")
            if wd.get("desc"):
                n_wd_desc += 1
            elif article.get("short_desc"):
                n_wp_desc += 1
            else:
                n_no_desc += 1
        else:
            article["wikidata_label"] = ""
            article["wikidata_desc"]  = ""
            if article.get("short_desc"):
                n_wp_desc += 1
            else:
                n_no_desc += 1

    print(f"\nDescription coverage after enrichment:")
    print(f"  Has Wikidata description:       {n_wd_desc:,} ({n_wd_desc/len(valid)*100:.1f}%)")
    print(f"  Wikipedia short_desc only:      {n_wp_desc:,} ({n_wp_desc/len(valid)*100:.1f}%)")
    print(f"  No description at all:          {n_no_desc:,} ({n_no_desc/len(valid)*100:.1f}%)")

    # Show some examples of Wikidata desc vs Wikipedia short_desc
    print("\nSample enrichments (Wikidata desc vs Wikipedia short_desc):")
    shown = 0
    for a in valid:
        if a.get("wikidata_desc") and a.get("short_desc") and shown < 8:
            print(f"  Title:   {a['title']}")
            print(f"  WD desc: {a['wikidata_desc']}")
            print(f"  WP desc: {a['short_desc']}")
            print()
            shown += 1

    # Save
    json.dump(valid, open(valid_path, "w"), indent=2, ensure_ascii=False)
    print(f"Saved {len(valid):,} enriched articles to {valid_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
