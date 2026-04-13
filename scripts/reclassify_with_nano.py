"""Re-classify with a better taxonomy that reflects what belongs in the graph.

The key insight: the ontology is for ALL nodes that appear in economics research
claims, not just "economics concepts." Rainfall, mortality, gold, COVID-19 are
all valid nodes because economics papers make directed claims about them.

New taxonomy:
  GRAPH NODES (belong in the concept ontology):
    econ_core      - core economics variables (GDP, inflation, trade, monetary policy)
    econ_applied   - applied economics variables (wages, housing prices, firm productivity)
    finance        - financial variables (stock returns, asset prices, credit)
    health         - health variables (mortality, life expectancy, insurance)
    environment    - environmental variables (CO2, rainfall, temperature, pollution)
    education      - education variables (test scores, enrollment, human capital)
    demographics   - demographic variables (birth rate, migration, fertility)
    politics       - political variables (democracy, corruption, political stability)
    institutions   - institutional actors (central bank, SOEs, Medicare)
    technology     - technology variables (ICT, automation, digital economy)
    events         - events and shocks (financial crisis, COVID-19, oil shock)
    commodities    - commodities and assets (gold, oil, bitcoin, wheat)
    behavior       - behavioral/psychological (risk aversion, trust, preferences)
    other_valid    - valid node that doesn't fit above categories

  NOT GRAPH NODES (separate layers or drop):
    geography      - geographic settings (China, EU, sub-Saharan Africa)
    time_period    - temporal settings (2008 crisis, post-war, colonial era)
    method         - research methods (regression discontinuity, IV, Monte Carlo)
    noise          - extraction artifacts (model parameters, sample size, this paper)

Task 1: Re-classify Wikidata (broader filter)
Task 2: Re-classify a sample of raw labels with domain assignment
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
BATCH_SIZE = 20

DOMAIN_LIST = """Valid graph node domains (could appear as a node in an economics research paper):
- econ_core: core economics (GDP, inflation, interest rates, trade, monetary policy, fiscal policy)
- econ_applied: applied economics (wages, employment, housing prices, firm productivity, inequality)
- finance: financial (stock returns, credit, banking, portfolio, derivatives)
- health: health & medicine (mortality, disease, healthcare, insurance coverage)
- environment: environment & natural resources (CO2, pollution, rainfall, temperature, energy)
- education: education (test scores, enrollment, school quality, human capital)
- demographics: demographics (birth rate, migration, aging, fertility, population)
- politics: political (democracy, corruption, elections, political stability, war)
- institutions: institutions & organizations (central bank, SOEs, WTO, Medicare, unions)
- technology: technology (ICT, automation, digital economy, R&D, innovation)
- events: events & shocks (financial crisis, COVID-19, oil shock, natural disaster)
- commodities: commodities & assets (gold, oil, bitcoin, wheat, real estate)
- behavior: behavioral & psychological (risk aversion, trust, preferences, expectations)
- other_valid: valid research variable that doesn't fit above

Not graph nodes:
- geography: geographic settings only (China, EU, OECD — NOT "Chinese economy")
- time_period: purely temporal references (post-2008, colonial era)
- method: research methods & techniques (regression, Monte Carlo, IV estimation)
- noise: extraction artifacts, meta-references (model parameters, sample size, this paper)"""


async def reclassify_wikidata():
    print("=== Re-classify Wikidata concepts (broader filter) ===")

    with open(OUT_DIR / "wikidata_economics_concepts.json") as f:
        data = json.load(f)
    concepts = data["concepts"]
    print(f"  Total: {len(concepts)}")

    client = openai.AsyncOpenAI(timeout=30.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    completed = 0
    t0 = time.time()

    batches = [concepts[i:i+BATCH_SIZE] for i in range(0, len(concepts), BATCH_SIZE)]

    async def classify_batch(batch):
        nonlocal completed
        items = "\n".join(f"{i+1}. {c['qid']}|{c['label']}|{c.get('description','')[:80]}" for i, c in enumerate(batch))

        prompt = f"""Classify each item. Could this concept plausibly appear as a node in an economics research paper? Economics papers study effects of many non-economics things (rainfall on crops, disease on productivity, wars on trade).

{DOMAIN_LIST}

For each item output: QID|domain|confidence(high/med/low)
If it could NOT plausibly appear in any economics paper, use domain=irrelevant.

Items:
{items}"""

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL, messages=[{"role": "user", "content": prompt}],
                        max_tokens=BATCH_SIZE * 20,
                    )
                    text = resp.choices[0].message.content.strip()
                    break
                except:
                    if attempt < 2: await asyncio.sleep(1)
                    else: text = ""

        batch_results = []
        for line in text.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 2:
                batch_results.append({
                    "qid": parts[0].strip(),
                    "domain": parts[1].strip().lower(),
                    "confidence": parts[2].strip().lower() if len(parts) > 2 else "low",
                })

        completed += 1
        if completed % 50 == 0:
            elapsed = time.time() - t0
            print(f"    {completed}/{len(batches)} ({completed/elapsed:.1f}/s)")

        return batch_results

    all_results = await asyncio.gather(*[classify_batch(b) for b in batches])
    for br in all_results:
        results.extend(br)

    print(f"  Done in {time.time()-t0:.1f}s ({len(results)} classified)")

    # Merge
    qid_map = {r["qid"]: r for r in results}
    for c in concepts:
        cls = qid_map.get(c["qid"], {})
        c["domain"] = cls.get("domain", "unknown")
        c["confidence"] = cls.get("confidence", "unknown")

    # Save
    out_path = OUT_DIR / "wikidata_reclassified.json"
    with open(out_path, "w") as f:
        json.dump({"concepts": concepts}, f, indent=2, ensure_ascii=False)

    # Stats
    from collections import Counter
    domain_counts = Counter(c["domain"] for c in concepts)
    relevant = sum(v for k, v in domain_counts.items() if k not in ("irrelevant", "unknown", "noise", "geography", "time_period", "method"))
    print(f"\n  Valid graph nodes: {relevant} / {len(concepts)} ({relevant/len(concepts)*100:.1f}%)")
    print(f"  By domain:")
    for d, count in domain_counts.most_common():
        marker = "  ✓" if d not in ("irrelevant", "unknown", "noise") else ""
        print(f"    {d:20s}: {count:5d}{marker}")
    print(f"  Saved to {out_path}")

    return concepts


async def reclassify_raw_labels():
    print(f"\n=== Re-classify raw labels with domain assignment ===")

    df = pd.read_parquet(OUT_DIR / "raw_labels_classified.parquet")
    # Re-classify ALL labels from the previous run
    labels_with_freq = list(zip(df["label"].tolist(), df["freq"].tolist()))
    print(f"  Labels to reclassify: {len(labels_with_freq):,}")

    client = openai.AsyncOpenAI(timeout=30.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    completed = 0
    t0 = time.time()

    batch_size = 25
    batches = [labels_with_freq[i:i+batch_size] for i in range(0, len(labels_with_freq), batch_size)]
    print(f"  Batches: {len(batches)}")

    async def classify_batch(batch):
        nonlocal completed
        items = "\n".join(f"{i+1}. {label}" for i, (label, freq) in enumerate(batch))

        prompt = f"""Classify each label. These are extracted from economics research paper titles and abstracts. They appear as nodes in directed causal claims (e.g., "inflation → unemployment", "rainfall → crop yield").

{DOMAIN_LIST}

For each: number|domain
Be GENEROUS: if it could plausibly be a cause or effect studied in economics, it's a valid node.

Items:
{items}"""

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL, messages=[{"role": "user", "content": prompt}],
                        max_tokens=batch_size * 10,
                    )
                    text = resp.choices[0].message.content.strip()
                    break
                except:
                    if attempt < 2: await asyncio.sleep(1)
                    else: text = ""

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
                            "domain": parts[1].strip().lower(),
                        })
                except (ValueError, IndexError):
                    pass

        completed += 1
        if completed % 200 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(batches) - completed) / rate if rate > 0 else 0
            print(f"    {completed}/{len(batches)} ({rate:.1f}/s, ETA {eta:.0f}s)")

        return batch_results

    all_results = await asyncio.gather(*[classify_batch(b) for b in batches])
    for br in all_results:
        results.extend(br)

    print(f"  Done in {time.time()-t0:.1f}s ({len(results):,} classified)")

    results_df = pd.DataFrame(results)
    out_path = OUT_DIR / "raw_labels_reclassified.parquet"
    results_df.to_parquet(out_path, index=False)

    # Stats
    from collections import Counter
    domain_counts = Counter(r["domain"] for r in results)
    valid_domains = [d for d in domain_counts if d not in ("geography", "time_period", "method", "noise", "irrelevant", "unknown")]
    valid_count = sum(domain_counts[d] for d in valid_domains)
    valid_instances = sum(r["freq"] for r in results if r["domain"] in valid_domains)
    total_instances = sum(r["freq"] for r in results)

    print(f"\n  Valid graph nodes: {valid_count:,} labels ({valid_count/len(results)*100:.1f}%)")
    print(f"  Valid instances: {valid_instances:,} ({valid_instances/total_instances*100:.1f}%)")
    print(f"\n  By domain (labels / instances):")
    # Sort by instance count
    domain_inst = Counter()
    for r in results:
        domain_inst[r["domain"]] += r["freq"]
    for d, inst in domain_inst.most_common():
        labels = domain_counts[d]
        marker = " ✓" if d in valid_domains else ""
        print(f"    {d:20s}: {labels:6,} labels, {inst:7,} instances{marker}")

    print(f"\n  Saved to {out_path}")
    return results


async def main():
    await reclassify_wikidata()
    await reclassify_raw_labels()
    print("\n=== ALL DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
