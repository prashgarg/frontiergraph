"""Classify Wikidata concepts one-at-a-time with nano. High concurrency."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt")
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

MODEL = "gpt-4.1-nano"
CONCURRENCY = 150


async def main():
    with open(OUT_DIR / "wikidata_economics_concepts.json") as f:
        concepts = json.load(f)["concepts"]
    print(f"Concepts to classify: {len(concepts)}")

    client = openai.AsyncOpenAI(timeout=20.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    completed = 0
    t0 = time.time()

    async def classify_one(concept: dict) -> dict:
        nonlocal completed
        label = concept.get("label", "")
        desc = concept.get("description", "")[:120]
        parent = concept.get("parent_label", "")
        root = concept.get("root_label", "")

        prompt = f"""You are classifying concepts for an economics research knowledge graph.

Question: Could this concept plausibly appear as a node (cause or effect) in an economics research paper?

Economics papers routinely study non-economics causes and effects:
- "rainfall" → YES (environment) — economists study rainfall → crop yields → prices
- "malaria prevalence" → YES (health) — economists study disease → development
- "soil quality" → YES (environment) — economists study land quality → land prices
- "democracy" → YES (politics) — economists study institutions → growth
- "steel production" → YES (commodities) — economists study industrial output
- "birth order" → YES (demographics) — economists study family structure → outcomes
- "browser engine" → NO (irrelevant) — no economics paper studies this
- "quantum entanglement" → NO (irrelevant) — no economics paper studies this
- "Linux kernel" → NO (irrelevant) — no economics paper studies this

Concept: {label}
Description: {desc}
Parent: {parent or root}

Respond with ONLY a JSON object, nothing else:
{{"domain": "...", "confidence": "high|med|low"}}

Domains: econ_core, econ_applied, finance, health, environment, education, demographics, politics, institutions, technology, events, commodities, behavior, other_valid, geography, method, noise, irrelevant"""

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=30,
                    )
                    text = resp.choices[0].message.content.strip()
                    # Parse JSON
                    if text.startswith("{"):
                        result = json.loads(text)
                    else:
                        # Try to extract JSON from response
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
        if completed % 500 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(concepts) - completed) / rate if rate > 0 else 0
            print(f"  {completed}/{len(concepts)} ({rate:.0f}/s, ETA {eta:.0f}s)")

        return {
            "qid": concept["qid"],
            "label": label,
            "description": desc,
            "parent_label": parent,
            "root_label": root,
            "domain": result.get("domain", "unknown"),
            "confidence": result.get("confidence", "low"),
        }

    tasks = [classify_one(c) for c in concepts]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0
    print(f"\nDone: {len(results)} in {elapsed:.1f}s ({len(results)/elapsed:.0f}/s)")

    # Stats
    from collections import Counter
    domain_counts = Counter(r["domain"] for r in results)
    valid = [d for d in domain_counts if d not in ("irrelevant", "unknown", "noise", "geography", "time_period", "method")]
    valid_count = sum(domain_counts[d] for d in valid)

    print(f"\nValid graph nodes: {valid_count} / {len(results)} ({valid_count/len(results)*100:.1f}%)")
    print(f"\nBy domain:")
    for d, count in domain_counts.most_common():
        marker = " ✓" if d in valid else ""
        print(f"  {d:20s}: {count:5d}{marker}")

    # Save
    out_path = OUT_DIR / "wikidata_classified_v2.json"
    with open(out_path, "w") as f:
        json.dump({"results": results, "stats": dict(domain_counts)}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")

    # Also save just the valid ones as a flat list
    valid_concepts = [r for r in results if r["domain"] in valid]
    valid_path = OUT_DIR / "wikidata_valid_concepts.json"
    with open(valid_path, "w") as f:
        json.dump(valid_concepts, f, indent=2, ensure_ascii=False)
    print(f"Valid concepts saved to {valid_path} ({len(valid_concepts)} concepts)")


if __name__ == "__main__":
    asyncio.run(main())
