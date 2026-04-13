"""Cheap LLM classification pass on noisy vocabularies.

Two tasks:
1. Wikidata concepts (15K): economics-relevant? JEL category?
2. Raw LLM labels (1.4M): concept type classification

Uses GPT-5.4-nano with high async concurrency for speed.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

KEY_PATH = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt")
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

MODEL = "gpt-4.1-nano"
CONCURRENCY = 80
BATCH_SIZE = 20  # items per LLM call (batch multiple items in one prompt)


# ======================================================================= #
# Task 1: Wikidata classification
# ======================================================================= #
async def classify_wikidata():
    print("=== TASK 1: Classify Wikidata concepts ===")

    with open(OUT_DIR / "wikidata_economics_concepts.json") as f:
        data = json.load(f)
    concepts = data["concepts"]
    print(f"  Total concepts: {len(concepts)}")

    client = openai.AsyncOpenAI(timeout=30.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    completed = 0
    t0 = time.time()

    # Batch concepts for efficiency
    batches = [concepts[i:i+BATCH_SIZE] for i in range(0, len(concepts), BATCH_SIZE)]
    print(f"  Batches: {len(batches)} of {BATCH_SIZE}")

    async def classify_batch(batch: list[dict]) -> list[dict]:
        nonlocal completed
        items_text = "\n".join(
            f"{i+1}. {c['qid']}|{c['label']}|{c.get('description','')[:80]}"
            for i, c in enumerate(batch)
        )

        prompt = f"""Classify each item as economics-relevant or not. For each, output one line:
QID|yes_or_no|confidence(high/medium/low)|jel_letter(A-Z or NONE)|type(concept/method/institution/person/other)

Items:
{items_text}

Rules:
- "yes" = directly relevant to economics research (concepts, policies, markets, methods, institutions)
- "no" = not economics (software, biology, physics, etc.)
- jel_letter = best-matching JEL category letter (A-Z), or NONE
- Be generous: if it COULD appear in an economics paper, say yes"""

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=BATCH_SIZE * 30,
                    )
                    text = resp.choices[0].message.content.strip()
                    break
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(1)
                    else:
                        text = ""

        # Parse response
        batch_results = []
        for line in text.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 4:
                batch_results.append({
                    "qid": parts[0].strip(),
                    "relevant": parts[1].strip().lower(),
                    "confidence": parts[2].strip().lower() if len(parts) > 2 else "low",
                    "jel_category": parts[3].strip().upper() if len(parts) > 3 else "NONE",
                    "type": parts[4].strip().lower() if len(parts) > 4 else "other",
                })

        completed += 1
        if completed % 50 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(batches) - completed) / rate if rate > 0 else 0
            print(f"    {completed}/{len(batches)} ({rate:.1f}/s, ETA {eta:.0f}s)")

        return batch_results

    tasks = [classify_batch(b) for b in batches]
    all_results = await asyncio.gather(*tasks)

    for batch_result in all_results:
        results.extend(batch_result)

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s ({len(results)} classified)")

    # Merge with original data
    qid_to_class = {r["qid"]: r for r in results}
    for concept in concepts:
        cls = qid_to_class.get(concept["qid"], {})
        concept["relevant"] = cls.get("relevant", "unknown")
        concept["confidence"] = cls.get("confidence", "unknown")
        concept["jel_category"] = cls.get("jel_category", "NONE")
        concept["concept_type"] = cls.get("type", "unknown")

    # Save
    out_path = OUT_DIR / "wikidata_classified.json"
    with open(out_path, "w") as f:
        json.dump({"concepts": concepts}, f, indent=2, ensure_ascii=False)

    # Stats
    relevant = sum(1 for c in concepts if c.get("relevant") == "yes")
    print(f"\n  Relevant: {relevant} / {len(concepts)} ({relevant/len(concepts)*100:.1f}%)")
    print(f"  By JEL category:")
    from collections import Counter
    jel_counts = Counter(c.get("jel_category", "NONE") for c in concepts if c.get("relevant") == "yes")
    for cat, count in jel_counts.most_common(10):
        print(f"    {cat}: {count}")
    print(f"  Saved to {out_path}")

    return concepts


# ======================================================================= #
# Task 2: Raw label classification (pilot on 50K sample first)
# ======================================================================= #
async def classify_raw_labels(sample_size: int = 50000):
    import sqlite3

    print(f"\n=== TASK 2: Classify raw LLM labels (sample of {sample_size:,}) ===")

    db = sqlite3.connect(str(ROOT / "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"))
    cursor = db.cursor()

    # Get labels with their frequency
    cursor.execute("""
        SELECT LOWER(TRIM(label)) as clean_label, COUNT(*) as freq
        FROM nodes
        GROUP BY clean_label
        ORDER BY freq DESC
    """)
    all_labels = [(label, freq) for label, freq in cursor.fetchall()]
    db.close()

    print(f"  Total unique labels: {len(all_labels):,}")

    # Strategy: classify ALL labels appearing 2+ times (much smaller set)
    # plus a random sample of hapax labels
    frequent = [(l, f) for l, f in all_labels if f >= 2]
    hapax = [(l, f) for l, f in all_labels if f == 1]

    import random
    random.seed(42)
    hapax_budget = max(0, sample_size - len(frequent))
    hapax_sample = random.sample(hapax, min(hapax_budget, len(hapax)))

    to_classify = frequent + hapax_sample
    print(f"  Classifying: {len(frequent):,} frequent (freq>=2) + {len(hapax_sample):,} hapax sample = {len(to_classify):,}")

    client = openai.AsyncOpenAI(timeout=30.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    completed = 0
    t0 = time.time()

    label_batch_size = 30  # more items per call since labels are short
    batches = [to_classify[i:i+label_batch_size] for i in range(0, len(to_classify), label_batch_size)]
    print(f"  Batches: {len(batches)}")

    async def classify_label_batch(batch: list[tuple]) -> list[dict]:
        nonlocal completed
        items_text = "\n".join(f"{i+1}. {label}" for i, (label, freq) in enumerate(batch))

        prompt = f"""Classify each economics research label. Output one line per item:
number|type|jel_letter

Types:
- concept: an economics concept or variable (GDP, inflation, trade openness)
- method: a research method or technique (regression discontinuity, IV, panel data)
- context: a geographic/temporal/institutional setting (China, 2008 crisis, OECD)
- outcome: a measurable outcome variable (mortality, test scores, wages)
- policy: a specific policy or intervention (minimum wage, QE, carbon tax)
- artifact: extraction noise, not meaningful (model parameters, number of agents)

Items:
{items_text}"""

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=label_batch_size * 15,
                    )
                    text = resp.choices[0].message.content.strip()
                    break
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(1)
                    else:
                        text = ""

        batch_results = []
        for line in text.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0].strip().rstrip(".")) - 1
                    if 0 <= idx < len(batch):
                        label, freq = batch[idx]
                        batch_results.append({
                            "label": label,
                            "freq": freq,
                            "type": parts[1].strip().lower(),
                            "jel_category": parts[2].strip().upper() if len(parts) > 2 else "NONE",
                        })
                except (ValueError, IndexError):
                    pass

        completed += 1
        if completed % 100 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(batches) - completed) / rate if rate > 0 else 0
            print(f"    {completed}/{len(batches)} ({rate:.1f}/s, ETA {eta:.0f}s)")

        return batch_results

    tasks = [classify_label_batch(b) for b in batches]
    all_results = await asyncio.gather(*tasks)

    for batch_result in all_results:
        results.extend(batch_result)

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s ({len(results):,} classified)")

    # Save
    results_df = pd.DataFrame(results)
    out_path = OUT_DIR / "raw_labels_classified.parquet"
    results_df.to_parquet(out_path, index=False)

    # Stats
    print(f"\n  Classification distribution:")
    from collections import Counter
    type_counts = Counter(r["type"] for r in results)
    for t, count in type_counts.most_common():
        print(f"    {t:15s}: {count:,} ({count/len(results)*100:.1f}%)")

    # Weighted by frequency
    print(f"\n  Weighted by frequency (instance count):")
    type_weighted = Counter()
    for r in results:
        type_weighted[r["type"]] += r["freq"]
    total_weighted = sum(type_weighted.values())
    for t, count in type_weighted.most_common():
        print(f"    {t:15s}: {count:,} instances ({count/total_weighted*100:.1f}%)")

    # Top JEL categories for concepts
    concept_jels = Counter(r["jel_category"] for r in results if r["type"] == "concept")
    print(f"\n  Top JEL categories for concepts:")
    for cat, count in concept_jels.most_common(10):
        print(f"    {cat}: {count:,}")

    print(f"\n  Saved to {out_path}")
    return results


# ======================================================================= #
async def main():
    # Skip Wikidata if already done
    wiki_path = OUT_DIR / "wikidata_classified.json"
    if wiki_path.exists():
        print("Wikidata already classified, loading...")
        with open(wiki_path) as f:
            wikidata_results = json.load(f)["concepts"]
    else:
        wikidata_results = await classify_wikidata()

    label_results = await classify_raw_labels(sample_size=100000)

    print("\n=== ALL DONE ===")
    print(f"Wikidata: {sum(1 for c in wikidata_results if c.get('relevant')=='yes')} economics-relevant concepts")
    print(f"Labels: {len(label_results):,} classified")


if __name__ == "__main__":
    asyncio.run(main())
