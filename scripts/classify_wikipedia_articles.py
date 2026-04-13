"""Classify Wikipedia economics crawl articles with nano LLM.

The crawl at depth-5 from Category:Economics will return 50K-200K articles.
Not all are true "economics concept" nodes — many are biographies, countries,
events that slipped through category filters. This script classifies them.

Uses single-item classification (learned from Wikidata: single-item >> batched).
High concurrency for speed.

Input:  data/ontology_v2/wikipedia_economics_articles.json (from crawl)
         data/ontology_v2/wikipedia_economics_articles_enriched.json (if available)
Output: data/ontology_v2/wikipedia_classified.json
        data/ontology_v2/wikipedia_valid.json
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

MODEL = "gpt-4.1-nano"
CONCURRENCY = 150


PROMPT_TEMPLATE = """You are classifying Wikipedia article titles for an economics research knowledge graph.

Question: Could this concept plausibly appear as a node (cause or effect) in an economics research paper?

Economics papers study non-economics causes and effects:
- "rainfall" → YES (environment) — economists study rainfall → crop yields → prices
- "malaria" → YES (health) — economists study disease → development
- "democracy" → YES (politics) — economists study institutions → growth
- "steel production" → YES (commodities) — economists study industrial output
- "CO2 emissions" → YES (environment) — environmental economics
- "wages" → YES (econ_core) — core labor economics concept
- "trade openness" → YES (econ_core) — international economics measurement
- "Star Wars" → NO (irrelevant) — no economics paper studies this film
- "list of economists" → NO (irrelevant) — meta/list article
- "John Smith (economist)" → NO (noise) — biography, not a concept

Wikipedia article: {title}
Category path: {category_path}
Short description: {short_desc}

Respond with ONLY a JSON object:
{{"domain": "...", "confidence": "high|med|low"}}

Domains: econ_core, econ_applied, finance, health, environment, education, demographics, politics, institutions, technology, events, commodities, behavior, other_valid, geography, method, noise, irrelevant"""


def canon_domain(d: str) -> str:
    """Canonicalize domain label."""
    d = str(d).lower().strip()
    if d in ("irrelevant", "irrelavent", "no", "list", "meta"): return "irrelevant"
    if d.startswith("geo") or "region" in d: return "geography"
    if d in ("geography", "geo"): return "geography"
    if d in ("method", "technique", "methodology"): return "method"
    if d in ("noise", "unknown", "none", "biography", "person"): return "noise"
    if "econ_core" in d or d in ("macroeconomics", "economics", "econ"): return "econ_core"
    if "econ_app" in d or d in ("economics_applied",): return "econ_applied"
    if "financ" in d or "money" in d or "currency" in d or "banking" in d: return "finance"
    if d == "health" or "medic" in d or "disease" in d: return "health"
    if d in ("environment", "enviroment", "agriculture", "climate"): return "environment"
    if d == "education": return "education"
    if "demograph" in d or "population" in d: return "demographics"
    if "politi" in d or "gov" in d or "instit" in d: return "politics"
    if "tech" in d: return "technology"
    if d in ("events",) or "histor" in d: return "events"
    if d in ("commodities",) or "commodity" in d: return "commodities"
    if "behavi" in d or "bias" in d or "social" in d or "cultur" in d: return "behavior"
    if "crime" in d or "legal" in d or "law" in d: return "politics"
    if "industr" in d or "business" in d: return "econ_applied"
    if "trade" in d or "labor" in d: return "econ_core"
    return "other_valid"


VALID_DOMAINS = {
    "econ_core", "econ_applied", "finance", "health", "environment",
    "education", "demographics", "politics", "institutions", "technology",
    "events", "commodities", "behavior", "other_valid"
}


async def classify_all(articles: list[dict]) -> list[dict]:
    client = openai.AsyncOpenAI(timeout=20.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    completed = 0
    t0 = time.time()

    async def classify_one(article: dict) -> dict:
        nonlocal completed
        title = article.get("title", "")

        # Build category path
        if isinstance(article.get("path"), list):
            cat_path = " → ".join(article["path"][:3])
        elif isinstance(article.get("categories"), list):
            cat_path = article["categories"][0].replace("Category:", "") if article["categories"] else ""
        else:
            cat_path = ""

        short_desc = article.get("short_desc", "") or ""

        prompt = PROMPT_TEMPLATE.format(
            title=title,
            category_path=cat_path[:100],
            short_desc=short_desc[:120],
        )

        async with sem:
            result = {"domain": "unknown", "confidence": "low"}
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=30,
                    )
                    text = resp.choices[0].message.content.strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        result = json.loads(text[start:end])
                    break
                except json.JSONDecodeError:
                    break
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(0.5)

        completed += 1
        if completed % 2000 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(articles) - completed) / rate if rate > 0 else 0
            print(f"  {completed}/{len(articles)} ({rate:.0f}/s, ETA {eta:.0f}s)")

        domain_raw = result.get("domain", "unknown")
        domain_clean = canon_domain(domain_raw)

        return {
            "title": title,
            "pageid": article.get("pageid"),
            "depth": article.get("depth", 0),
            "domain_raw": domain_raw,
            "domain": domain_clean,
            "confidence": result.get("confidence", "low"),
            "category_path": cat_path,
            "short_desc": short_desc,
            "extract": article.get("extract", ""),
        }

    tasks = [classify_one(a) for a in articles]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0
    print(f"\nDone: {len(results):,} in {elapsed:.1f}s ({len(results)/elapsed:.0f}/s)")
    return results


async def main():
    # Load Wikipedia articles
    # Try enriched version first (has short_desc + extract), fall back to raw
    enriched_path = OUT_DIR / "wikipedia_economics_articles_enriched.json"
    raw_path = OUT_DIR / "wikipedia_economics_articles.json"

    if enriched_path.exists():
        with open(enriched_path) as f:
            articles = json.load(f)
        print(f"Loaded enriched articles: {len(articles):,}")
    elif raw_path.exists():
        with open(raw_path) as f:
            articles = json.load(f)
        print(f"Loaded raw articles: {len(articles):,}")
        print("  (enriched version not yet available — run fetch_wikipedia_descriptions.py after)")
    else:
        print("No Wikipedia crawl results found. Run crawl_wikipedia_economics.py first.")
        return

    print(f"\nDepth distribution:")
    depth_counts = Counter(a.get("depth", 0) for a in articles)
    for d in sorted(depth_counts):
        print(f"  Depth {d}: {depth_counts[d]:,}")

    print(f"\nClassifying {len(articles):,} articles with {MODEL}...")
    t0 = time.time()
    results = await classify_all(articles)

    # Stats
    domain_counts = Counter(r["domain"] for r in results)
    valid_results = [r for r in results if r["domain"] in VALID_DOMAINS]

    print(f"\nTotal articles: {len(results):,}")
    print(f"Valid for graph: {len(valid_results):,} ({len(valid_results)/len(results)*100:.1f}%)")
    print(f"\nBy domain:")
    for d, n in domain_counts.most_common():
        marker = " ✓" if d in VALID_DOMAINS else ""
        print(f"  {d:20s}: {n:6,}{marker}")

    # Confidence distribution for valid
    conf_counts = Counter(r["confidence"] for r in valid_results)
    print(f"\nConfidence (valid only):")
    for c, n in conf_counts.most_common():
        print(f"  {c}: {n:,}")

    # Sample valid by domain
    import random; random.seed(42)
    print(f"\nSample valid concepts:")
    for domain in sorted(VALID_DOMAINS)[:6]:
        domain_items = [r for r in valid_results if r["domain"] == domain]
        if domain_items:
            samples = random.sample(domain_items, min(3, len(domain_items)))
            print(f"  {domain}:")
            for s in samples:
                print(f"    {s['title']} — {s['short_desc'][:60]}")

    # Save all results
    all_path = OUT_DIR / "wikipedia_classified.json"
    with open(all_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nAll results saved to {all_path}")

    # Save valid only
    valid_path = OUT_DIR / "wikipedia_valid.json"
    with open(valid_path, "w") as f:
        json.dump(valid_results, f, indent=2, ensure_ascii=False)
    print(f"Valid ({len(valid_results):,}) saved to {valid_path}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s")
    print(f"Estimated cost: ${len(results) * 0.0000001 * 200:.2f} (approx)")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
