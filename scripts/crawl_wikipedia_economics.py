"""Crawl Wikipedia's economics category tree via the MediaWiki API.
BFS to depth 5, collecting all articles and their category paths.
Then nano-classify all articles for economics relevance.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_DEPTH = 5
RATE_LIMIT = 0.15  # seconds between requests (Wikipedia asks for polite usage)


def wiki_api(params: dict) -> dict:
    """Call Wikipedia API with rate limiting."""
    params["format"] = "json"
    url = f"https://en.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "FrontierGraph/1.0 (prashant.garg@imperial.ac.uk) economics research"
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return {}


def get_members(category: str, member_type: str = "subcat") -> list[dict]:
    """Get all members of a category (handles continuation)."""
    all_members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmtype": member_type,
        "cmlimit": "500",
    }

    while True:
        time.sleep(RATE_LIMIT)
        data = wiki_api(params)
        members = data.get("query", {}).get("categorymembers", [])
        all_members.extend(members)

        if "continue" in data:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
        else:
            break

    return all_members


def crawl():
    print(f"Crawling Wikipedia economics category tree to depth {MAX_DEPTH}...\n")

    visited_cats = set()
    queue = deque([("Category:Economics", 0, ["Economics"])])

    all_categories = []  # (category, depth, path)
    all_articles = {}  # title -> {pageid, depth, categories}

    t0 = time.time()

    while queue:
        cat, depth, path = queue.popleft()

        if cat in visited_cats:
            continue
        visited_cats.add(cat)
        all_categories.append({"category": cat, "depth": depth, "path": path})

        if len(visited_cats) % 100 == 0:
            elapsed = time.time() - t0
            print(f"  Visited {len(visited_cats)} categories, {len(all_articles)} articles, "
                  f"queue={len(queue)}, {elapsed:.0f}s elapsed")

        # Get articles in this category
        articles = get_members(cat, "page")
        for a in articles:
            title = a["title"]
            if title not in all_articles:
                all_articles[title] = {
                    "pageid": a.get("pageid"),
                    "title": title,
                    "depth": depth,
                    "categories": [cat],
                    "path": path,
                }
            else:
                all_articles[title]["categories"].append(cat)
                # Keep shallowest depth
                if depth < all_articles[title]["depth"]:
                    all_articles[title]["depth"] = depth
                    all_articles[title]["path"] = path

        # Expand subcategories if within depth limit
        if depth < MAX_DEPTH:
            subcats = get_members(cat, "subcat")
            for sc in subcats:
                sc_title = sc["title"]
                if sc_title not in visited_cats:
                    # Skip obviously non-economics categories
                    lower = sc_title.lower()
                    skip_patterns = [
                        "biography", "births", "deaths", "albums", "songs",
                        "films", "television", "novels", "video games",
                        "sports teams", "football clubs", "basketball",
                    ]
                    if any(p in lower for p in skip_patterns):
                        continue
                    queue.append((sc_title, depth + 1, path + [sc_title.replace("Category:", "")]))

    elapsed = time.time() - t0
    print(f"\nCrawl complete in {elapsed:.0f}s")
    print(f"  Categories visited: {len(visited_cats)}")
    print(f"  Unique articles: {len(all_articles)}")
    print(f"  Depth distribution:")
    from collections import Counter
    depth_counts = Counter(a["depth"] for a in all_articles.values())
    for d in sorted(depth_counts):
        print(f"    Depth {d}: {depth_counts[d]:,} articles")

    # Save
    cat_path = OUT_DIR / "wikipedia_economics_categories.json"
    with open(cat_path, "w") as f:
        json.dump(all_categories, f, indent=2, ensure_ascii=False)
    print(f"\n  Categories saved to {cat_path}")

    articles_list = list(all_articles.values())
    art_path = OUT_DIR / "wikipedia_economics_articles.json"
    with open(art_path, "w") as f:
        json.dump(articles_list, f, indent=2, ensure_ascii=False)
    print(f"  Articles saved to {art_path}")

    # Sample
    print(f"\n  Sample articles by depth:")
    for d in sorted(depth_counts):
        depth_articles = [a for a in articles_list if a["depth"] == d]
        import random
        random.seed(42)
        sample = random.sample(depth_articles, min(5, len(depth_articles)))
        print(f"\n  Depth {d}:")
        for a in sample:
            print(f"    {a['title']}")

    return articles_list


def main():
    articles = crawl()

    # Now nano-classify
    print(f"\n\n=== NANO CLASSIFICATION OF {len(articles)} ARTICLES ===\n")

    KEY_PATH = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt")
    os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

    import openai

    async def classify_all():
        client = openai.AsyncOpenAI(timeout=20.0)
        sem = asyncio.Semaphore(150)
        completed = 0
        t0 = time.time()

        async def classify_one(article: dict) -> dict:
            nonlocal completed
            title = article["title"]
            cat_path = " → ".join(article.get("path", [])[:3])

            prompt = f"""You are classifying Wikipedia articles for an economics research knowledge graph.

Could this concept plausibly appear as a node (cause or effect) in an economics research paper?

Examples:
- "Inflation" → YES (econ_core)
- "Rainfall" → YES (environment) — economists study rainfall → crop yields
- "Malaria" → YES (health) — economists study disease → development
- "Democracy" → YES (politics)
- "Steel" → YES (commodities)
- "Fibonacci number" → NO (irrelevant)
- "Star Trek" → NO (irrelevant)

Article: {title}
Category path: {cat_path}

Respond ONLY with a JSON object:
{{"domain": "...", "confidence": "high|med|low"}}

Domains: econ_core, econ_applied, finance, health, environment, education, demographics, politics, institutions, technology, events, commodities, behavior, other_valid, geography, method, noise, irrelevant"""

            async with sem:
                for attempt in range(3):
                    try:
                        resp = await client.chat.completions.create(
                            model="gpt-4.1-nano",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=30,
                        )
                        text = resp.choices[0].message.content.strip()
                        start = text.find("{")
                        end = text.rfind("}") + 1
                        if start >= 0 and end > start:
                            result = json.loads(text[start:end])
                        else:
                            result = {"domain": "unknown", "confidence": "low"}
                        break
                    except json.JSONDecodeError:
                        result = {"domain": "unknown", "confidence": "low"}
                        break
                    except Exception:
                        if attempt < 2:
                            await asyncio.sleep(0.5)
                        else:
                            result = {"domain": "unknown", "confidence": "low"}

            completed += 1
            if completed % 2000 == 0:
                elapsed = time.time() - t0
                rate = completed / elapsed
                eta = (len(articles) - completed) / rate if rate > 0 else 0
                print(f"  {completed}/{len(articles)} ({rate:.0f}/s, ETA {eta:.0f}s)")

            return {
                "title": title,
                "pageid": article.get("pageid"),
                "depth": article["depth"],
                "domain": result.get("domain", "unknown"),
                "confidence": result.get("confidence", "low"),
                "category_path": cat_path,
            }

        tasks = [classify_one(a) for a in articles]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - t0
        print(f"\nClassified {len(results)} in {elapsed:.1f}s ({len(results)/elapsed:.0f}/s)")
        return results

    results = asyncio.run(classify_all())

    # Stats
    from collections import Counter

    def canon(d):
        d = str(d).lower().strip()
        if d in ("irrelevant", "irrelavent", "no"): return "irrelevant"
        if d in ("geography", "geo"): return "geography"
        if d in ("method", "technique"): return "method"
        if d in ("noise", "unknown", "none"): return "noise"
        valid_domains = ["econ_core", "econ_applied", "finance", "health", "environment",
                        "education", "demographics", "politics", "institutions", "technology",
                        "events", "commodities", "behavior", "other_valid"]
        for v in valid_domains:
            if v in d:
                return v
        if "politi" in d or "gov" in d or "crime" in d or "law" in d: return "politics"
        if "financ" in d or "money" in d or "bank" in d: return "finance"
        if "tech" in d: return "technology"
        if "health" in d or "medic" in d: return "health"
        if "environ" in d or "energy" in d or "climate" in d: return "environment"
        if "educat" in d: return "education"
        if "trade" in d or "econ" in d: return "econ_core"
        if "industr" in d or "business" in d: return "econ_applied"
        return "other_valid"

    for r in results:
        r["domain_clean"] = canon(r["domain"])

    counts = Counter(r["domain_clean"] for r in results)
    valid_domains = [d for d in counts if d not in ("irrelevant", "geography", "method", "noise")]
    valid_count = sum(counts[d] for d in valid_domains)

    print(f"\nValid graph nodes: {valid_count:,} / {len(results):,} ({valid_count/len(results)*100:.1f}%)")
    print(f"\nBy domain:")
    for d, c in counts.most_common():
        marker = " ✓" if d in valid_domains else ""
        print(f"  {d:20s}: {c:6,}{marker}")

    # Save
    out_path = OUT_DIR / "wikipedia_economics_classified.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    valid_only = [r for r in results if r["domain_clean"] in valid_domains]
    valid_path = OUT_DIR / "wikipedia_economics_valid.json"
    with open(valid_path, "w") as f:
        json.dump(valid_only, f, indent=2, ensure_ascii=False)

    print(f"\nSaved all to {out_path}")
    print(f"Saved {len(valid_only):,} valid to {valid_path}")


if __name__ == "__main__":
    main()
