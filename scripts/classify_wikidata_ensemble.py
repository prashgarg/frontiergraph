"""Run 2 more nano + 1 mini classification passes on Wikidata concepts.
All three run concurrently. Results saved separately for majority voting."""
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

CONCURRENCY = 150

PROMPT_TEMPLATE = """You are classifying concepts for an economics research knowledge graph.

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
Description: {description}
Parent: {parent}

Respond with ONLY a JSON object, nothing else:
{{"domain": "...", "confidence": "high|med|low"}}

Domains: econ_core, econ_applied, finance, health, environment, education, demographics, politics, institutions, technology, events, commodities, behavior, other_valid, geography, method, noise, irrelevant"""


async def run_pass(concepts: list[dict], model: str, run_name: str) -> list[dict]:
    client = openai.AsyncOpenAI(timeout=20.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    completed = 0
    t0 = time.time()

    async def classify_one(concept: dict) -> dict:
        nonlocal completed
        prompt = PROMPT_TEMPLATE.format(
            label=concept.get("label", ""),
            description=concept.get("description", "")[:120],
            parent=concept.get("parent_label", "") or concept.get("root_label", ""),
        )

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=model,
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
        if completed % 1000 == 0:
            elapsed = time.time() - t0
            rate = completed / elapsed
            eta = (len(concepts) - completed) / rate if rate > 0 else 0
            print(f"  [{run_name}] {completed}/{len(concepts)} ({rate:.0f}/s, ETA {eta:.0f}s)")

        return {
            "qid": concept["qid"],
            "label": concept.get("label", ""),
            "domain": result.get("domain", "unknown"),
            "confidence": result.get("confidence", "low"),
        }

    tasks = [classify_one(c) for c in concepts]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0
    print(f"  [{run_name}] Done: {len(results)} in {elapsed:.1f}s ({len(results)/elapsed:.0f}/s)")
    return results


async def main():
    with open(OUT_DIR / "wikidata_economics_concepts.json") as f:
        concepts = json.load(f)["concepts"]
    print(f"Concepts: {len(concepts)}")
    print(f"Running 3 passes concurrently: nano_run2, nano_run3, mini_run1\n")

    t0 = time.time()

    # Run all three concurrently
    nano2_task = run_pass(concepts, "gpt-4.1-nano", "nano_run2")
    nano3_task = run_pass(concepts, "gpt-4.1-nano", "nano_run3")
    mini_task = run_pass(concepts, "gpt-4.1-mini", "mini_run1")

    nano2, nano3, mini = await asyncio.gather(nano2_task, nano3_task, mini_task)

    print(f"\nAll passes done in {time.time()-t0:.1f}s")

    # Save each run
    for name, results in [("nano_run2", nano2), ("nano_run3", nano3), ("mini_run1", mini)]:
        path = OUT_DIR / f"wikidata_{name}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        from collections import Counter
        counts = Counter(r["domain"] for r in results)
        valid = sum(v for k, v in counts.items() if k not in ("irrelevant", "unknown", "noise", "geography", "method", "time_period"))
        print(f"  {name}: {valid} valid ({valid/len(results)*100:.1f}%)")

    # Load nano_run1 (already done)
    with open(OUT_DIR / "wikidata_classified_v2.json") as f:
        nano1 = json.load(f)["results"]

    # Majority vote across 3 nano runs
    print(f"\n=== MAJORITY VOTE (3 nano runs) ===")
    qid_to_nano = {}
    for r in nano1:
        qid_to_nano.setdefault(r["qid"], []).append(r.get("domain_clean", r.get("domain", "unknown")))
    for r in nano2:
        qid_to_nano.setdefault(r["qid"], []).append(r["domain"])
    for r in nano3:
        qid_to_nano.setdefault(r["qid"], []).append(r["domain"])

    # Canonicalize for voting
    def canon(d):
        d = str(d).lower().strip()
        if d in ("irrelevant", "irrelavent", "irrelavant", "no_economics"): return "irrelevant"
        if d.startswith("geo") or "region" in d or "economy of" in d or d.startswith("admin"): return "geography"
        if d in ("geography", "geo"): return "geography"
        if d in ("method", "technique"): return "method"
        if d in ("noise", "unknown", "none"): return "noise"
        if "econ_core" in d or d in ("macroeconomics", "economics", "efn_core", "economics_core"): return "econ_core"
        if "econ_app" in d or d in ("economics_applied",): return "econ_applied"
        if "financ" in d or "money" in d or "currency" in d: return "finance"
        if d == "health" or "medic" in d: return "health"
        if d in ("environment", "enviroment", "agriculture"): return "environment"
        if d == "education": return "education"
        if "demograph" in d: return "demographics"
        if "politi" in d or "gov" in d: return "politics"
        if d in ("institutions",) or "institution" in d: return "institutions"
        if "tech" in d: return "technology"
        if d in ("events",) or "terror" in d or "histor" in d: return "events"
        if d in ("commodities",): return "commodities"
        if "behavi" in d or "bias" in d or "social" in d or "cultur" in d: return "behavior"
        if "crime" in d or "legal" in d or "law" in d: return "politics"
        if "industr" in d or "business" in d: return "econ_applied"
        return "other_valid"

    voted = []
    for qid, domains in qid_to_nano.items():
        canonical = [canon(d) for d in domains]
        from collections import Counter as C
        vote = C(canonical).most_common(1)[0][0]
        agreement = C(canonical).most_common(1)[0][1]
        voted.append({
            "qid": qid,
            "domain_voted": vote,
            "agreement": agreement,
            "n_votes": len(canonical),
            "votes": canonical,
        })

    # Stats
    from collections import Counter
    vote_counts = Counter(v["domain_voted"] for v in voted)
    valid_domains = [d for d in vote_counts if d not in ("irrelevant", "geography", "method", "noise")]
    valid_count = sum(vote_counts[d] for d in valid_domains)

    print(f"Valid (majority vote): {valid_count} / {len(voted)} ({valid_count/len(voted)*100:.1f}%)")
    print(f"\nAgreement distribution:")
    agree_counts = Counter(v["agreement"] for v in voted)
    for a, c in sorted(agree_counts.items()):
        print(f"  {a}/3 agree: {c} ({c/len(voted)*100:.1f}%)")

    print(f"\nBy domain (voted):")
    for d, c in vote_counts.most_common():
        marker = " ✓" if d in valid_domains else ""
        print(f"  {d:20s}: {c:5d}{marker}")

    # Save voted results
    voted_path = OUT_DIR / "wikidata_voted.json"
    with open(voted_path, "w") as f:
        json.dump(voted, f, indent=2, ensure_ascii=False)

    # Also compare nano vote with mini
    print(f"\n=== NANO VOTE vs MINI ===")
    mini_map = {r["qid"]: canon(r["domain"]) for r in mini}
    agree = sum(1 for v in voted if mini_map.get(v["qid"]) == v["domain_voted"])
    print(f"Nano majority agrees with mini: {agree} / {len(voted)} ({agree/len(voted)*100:.1f}%)")

    # Where they disagree, what does mini say?
    disagree = [(v, mini_map.get(v["qid"], "?")) for v in voted if mini_map.get(v["qid"]) != v["domain_voted"]]
    print(f"Disagreements: {len(disagree)}")
    if disagree:
        # How many disagree on valid/invalid boundary?
        boundary_disagree = sum(1 for v, m in disagree
                               if (v["domain_voted"] in valid_domains) != (m in [d for d in vote_counts if d not in ("irrelevant", "geography", "method", "noise")]))
        print(f"  Disagree on valid/invalid boundary: {boundary_disagree}")

    print(f"\nAll saved. Done.")


if __name__ == "__main__":
    asyncio.run(main())
