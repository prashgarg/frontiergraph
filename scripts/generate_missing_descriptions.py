"""Generate short Wikidata-style descriptions for Wikipedia articles that have none.

Targets short/ambiguous titles (≤3 words) with no wikidata_desc and no short_desc.
Skips single-word titles with no wikidata_id (highest hallucination risk — likely
disambiguation pages or misclassified articles with no reliable grounding).

Prompt design choices (for paper):
  - Wikidata style explicitly requested: 5–15 words, lowercase, no leading article.
  - Domain field used as disambiguation anchor (e.g. domain=behavior ensures
    "Animal spirits (Keynes)" is described as a behavioral economics concept,
    not a biology concept).
  - Category path provides structural context.
  - Explicit instruction for nicknames/catchphrases avoids tautological descriptions
    like "a nickname for economics" for "The dismal science".
  - Output format: plain text after "Description:" label — avoids the format-echo
    failure seen with arrow-separator prompts.

Safety filter:
  Single-word titles with no wikidata_id are skipped: they have no reliable
  grounding and produce high hallucination rates in the pilot (e.g. "Slate"
  with misleading category path → wrong description).

Input/output: updates wikipedia_valid.json in place (adds llm_desc field).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import openai

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path(
    "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/"
    "Prashant Garg/key/openai_key_prashant.txt"
)
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

MODEL = "gpt-4.1-nano"
CONCURRENCY = 150
MAX_WORDS = 3        # only generate for titles ≤ this many words
MAX_TOKENS = 40      # description output cap

PROMPT_TEMPLATE = """Write a Wikidata-style short description for a Wikipedia article in an economics knowledge graph.

Output ONLY the description text — no labels, no formatting, no quotation marks.

Style rules:
- 5–15 words, lowercase (except proper nouns)
- Start with a noun or participial phrase — omit leading "a"/"an"/"the"
- Use the domain field to anchor the meaning in economics/social science
- If the title has a disambiguation suffix like (economics), describe only that meaning
- If the title is a nickname or catchphrase, say what it refers to (e.g. "nickname for X")

Examples:
Title: Gig economy
Category: Economics → Business models
Domain: econ_applied
Description: labor market characterized by short-term contracts and freelance work

Title: Brain drain
Category: Economics → Demographic economics
Domain: demographics
Description: emigration of highly educated workers from developing to developed countries

Title: Crowding out (economics)
Category: Economics → Public economics
Domain: econ_core
Description: reduction in private investment caused by increased government borrowing

Title: Dead cat bounce
Category: Economics → Finance catchphrases
Domain: finance
Description: temporary recovery in asset prices following a significant decline

Title: The dismal science
Category: Economics → Economics catchphrases
Domain: other_valid
Description: nickname for economics, coined by Thomas Carlyle in the 19th century

---
Title: {title}
Category: {cat}
Domain: {domain}
Description:"""


def should_generate(article: dict) -> bool:
    """Return True if this article needs and can safely get an LLM description."""
    title = article.get("title", "")
    word_count = len(title.split())

    # Already has a description
    if article.get("wikidata_desc", "").strip():
        return False
    if article.get("short_desc", "").strip():
        return False
    if article.get("llm_desc", "").strip():
        return False

    # Too long — title is already self-descriptive
    if word_count > MAX_WORDS:
        return False

    # Single-word with no wikidata_id: too ambiguous, skip
    if word_count == 1 and not article.get("wikidata_id", "").strip():
        return False

    return True


async def generate_one(client: openai.AsyncOpenAI,
                        article: dict,
                        sem: asyncio.Semaphore) -> tuple[str, str]:
    """Returns (title, description) so as_completed() ordering doesn't matter."""
    title = article["title"]
    cat   = article.get("category_path", "Economics")[:80]
    domain = article.get("domain", "other_valid")

    prompt = PROMPT_TEMPLATE.format(title=title, cat=cat, domain=domain)

    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_TOKENS,
                    temperature=0.2,
                )
                return title, resp.choices[0].message.content.strip()
            except Exception as e:
                if attempt == 2:
                    return title, ""
                await asyncio.sleep(0.5 * (attempt + 1))
    return title, ""


async def main():
    print("=== Generating missing descriptions for Wikipedia articles ===\n")

    valid_path = OUT_DIR / "wikipedia_valid.json"
    valid = json.load(open(valid_path))
    print(f"Total valid articles: {len(valid):,}")

    targets = [a for a in valid if should_generate(a)]
    skipped_long  = sum(1 for a in valid
                        if not a.get("wikidata_desc","").strip()
                        and not a.get("short_desc","").strip()
                        and not a.get("llm_desc","").strip()
                        and len(a.get("title","").split()) > MAX_WORDS)
    skipped_nogrnd = sum(1 for a in valid
                         if not a.get("wikidata_desc","").strip()
                         and not a.get("short_desc","").strip()
                         and not a.get("llm_desc","").strip()
                         and len(a.get("title","").split()) == 1
                         and not a.get("wikidata_id","").strip())

    print(f"Targets (≤{MAX_WORDS} words, no desc): {len(targets):,}")
    print(f"Skipped — long titles (>{MAX_WORDS} words):    {skipped_long:,}")
    print(f"Skipped — 1-word, no wikidata_id:              {skipped_nogrnd:,}")

    word_dist = {}
    for a in targets:
        wc = len(a["title"].split())
        word_dist[wc] = word_dist.get(wc, 0) + 1
    print(f"\nTitle word distribution of targets:")
    for wc in sorted(word_dist):
        print(f"  {wc} words: {word_dist[wc]:,}")

    # Cost estimate
    avg_input_tokens = 180  # prompt template + title/cat/domain
    avg_output_tokens = 15
    cost_est = len(targets) * (avg_input_tokens * 0.10 + avg_output_tokens * 0.40) / 1_000_000
    print(f"\nEstimated cost: ${cost_est:.2f}")

    print(f"\nGenerating {len(targets):,} descriptions...")
    t0 = time.time()
    sem = asyncio.Semaphore(CONCURRENCY)
    client = openai.AsyncOpenAI()

    # Build lookup for fast update
    title_to_article = {a["title"]: a for a in valid}

    tasks = [generate_one(client, a, sem) for a in targets]
    n_done = 0
    n_success = 0
    # Use as_completed for throughput but unpack (title, desc) so ordering
    # doesn't matter — each result carries its own key.
    for coro in asyncio.as_completed(tasks):
        title, desc = await coro
        if desc:
            title_to_article[title]["llm_desc"] = desc
            n_success += 1
        n_done += 1
        if n_done % 2000 == 0:
            elapsed = time.time() - t0
            rate = n_done / elapsed
            eta = (len(targets) - n_done) / rate if rate > 0 else 0
            print(f"  {n_done}/{len(targets)} ({rate:.0f}/s, ETA {eta:.0f}s)")

    elapsed = time.time() - t0
    print(f"\nDone: {n_success:,} descriptions generated in {elapsed:.1f}s")

    # Sample output
    print("\nSample generated descriptions:")
    shown = 0
    for a in valid:
        if a.get("llm_desc") and shown < 12:
            print(f"  [{a['domain']:15s}] {a['title']!r:35s} → {a['llm_desc']!r}")
            shown += 1

    # Final coverage
    has_any = sum(1 for a in valid if
                  a.get("wikidata_desc","").strip() or
                  a.get("short_desc","").strip() or
                  a.get("llm_desc","").strip())
    print(f"\nDescription coverage: {has_any:,} / {len(valid):,} "
          f"({has_any/len(valid)*100:.1f}%)")

    json.dump(valid, open(valid_path, "w"), indent=2, ensure_ascii=False)
    print(f"Saved to {valid_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
