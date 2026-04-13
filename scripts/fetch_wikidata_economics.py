"""Query Wikidata for economics-relevant concepts with hierarchies.

Uses the Wikidata SPARQL endpoint to find:
1. All subclasses of key economics root concepts
2. Their labels, descriptions, and hierarchical relations
3. Cross-links to other knowledge bases

Output: data/ontology_v2/wikidata_economics_concepts.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Root concepts to crawl from
ROOT_CONCEPTS = {
    "Q166142": "macroeconomics",
    "Q39680": "microeconomics",
    "Q8134": "economics",
    "Q930752": "economic concept",
    "Q193391": "economic policy",
    "Q159810": "economic system",
    "Q182527": "economic indicator",
    "Q170584": "economic development",
    "Q180490": "economic growth",
    "Q42112": "fiscal policy",
    "Q180495": "monetary policy",
    "Q11183": "tax",
    "Q179671": "trade",
    "Q7503": "market",
    "Q170050": "financial market",
    "Q176686": "international trade",
    "Q431289": "brand",  # skip, wrong domain
    "Q854618": "labor economics",
    "Q192280": "public economics",
    "Q83267": "econometrics",
    "Q1368984": "development economics",
    "Q1048835": "behavioral economics",
    "Q854555": "health economics",
    "Q1402009": "environmental economics",
    "Q2578547": "financial economics",
    "Q1151706": "agricultural economics",
    "Q194425": "industrial organization",
    "Q1530025": "public finance",
    "Q215380": "economic inequality",
    "Q8142": "inflation",
    "Q45776": "unemployment",
    "Q207767": "price",
    "Q37866": "interest rate",
    "Q47043": "GDP",
    "Q42369": "supply and demand",
    "Q174237": "recession",
    "Q43118": "poverty",
    "Q1052430": "capital",
}


def run_sparql(query: str) -> list[dict]:
    """Run a SPARQL query against Wikidata."""
    encoded = urllib.parse.urlencode({"query": query, "format": "json"})
    url = f"{WIKIDATA_SPARQL}?{encoded}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "FrontierGraph/1.0 (prashant.garg@imperial.ac.uk) research project",
        "Accept": "application/sparql-results+json",
    })

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", {}).get("bindings", [])
        except Exception as e:
            if attempt < 2:
                print(f"    Retry ({e})...")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"    Failed: {e}")
                return []


def fetch_subclasses(root_qid: str, root_label: str, max_depth: int = 5) -> list[dict]:
    """Fetch all subclasses of a root concept up to max_depth."""
    query = f"""
    SELECT ?concept ?conceptLabel ?conceptDescription ?parent ?parentLabel
           (COUNT(DISTINCT ?subclass) AS ?childCount)
    WHERE {{
      ?concept wdt:P279* wd:{root_qid}.
      OPTIONAL {{ ?concept wdt:P279 ?parent. }}
      OPTIONAL {{ ?subclass wdt:P279 ?concept. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    GROUP BY ?concept ?conceptLabel ?conceptDescription ?parent ?parentLabel
    LIMIT 2000
    """
    results = run_sparql(query)

    concepts = []
    for r in results:
        qid = r.get("concept", {}).get("value", "").split("/")[-1]
        label = r.get("conceptLabel", {}).get("value", "")
        desc = r.get("conceptDescription", {}).get("value", "")
        parent_qid = r.get("parent", {}).get("value", "").split("/")[-1] if "parent" in r else ""
        parent_label = r.get("parentLabel", {}).get("value", "") if "parentLabel" in r else ""
        child_count = int(r.get("childCount", {}).get("value", "0"))

        if qid and label and not label.startswith("Q"):  # skip items without English labels
            concepts.append({
                "qid": qid,
                "label": label,
                "description": desc,
                "parent_qid": parent_qid,
                "parent_label": parent_label,
                "child_count": child_count,
                "root": root_qid,
                "root_label": root_label,
            })

    return concepts


def fetch_instances(root_qid: str, root_label: str) -> list[dict]:
    """Fetch instances of a concept (e.g., specific economic policies)."""
    query = f"""
    SELECT ?concept ?conceptLabel ?conceptDescription
    WHERE {{
      ?concept wdt:P31 wd:{root_qid}.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 500
    """
    results = run_sparql(query)

    concepts = []
    for r in results:
        qid = r.get("concept", {}).get("value", "").split("/")[-1]
        label = r.get("conceptLabel", {}).get("value", "")
        desc = r.get("conceptDescription", {}).get("value", "")

        if qid and label and not label.startswith("Q"):
            concepts.append({
                "qid": qid,
                "label": label,
                "description": desc,
                "parent_qid": root_qid,
                "parent_label": root_label,
                "child_count": 0,
                "root": root_qid,
                "root_label": root_label,
                "relation": "instance_of",
            })

    return concepts


def main():
    print("Querying Wikidata for economics concepts...\n")

    all_concepts = []
    seen_qids = set()

    for qid, label in ROOT_CONCEPTS.items():
        print(f"  Fetching subclasses of {qid} ({label})...")
        subclasses = fetch_subclasses(qid, label)
        new = [c for c in subclasses if c["qid"] not in seen_qids]
        for c in new:
            seen_qids.add(c["qid"])
        all_concepts.extend(new)
        print(f"    Found {len(subclasses)} total, {len(new)} new")

        # Also fetch instances
        instances = fetch_instances(qid, label)
        new_inst = [c for c in instances if c["qid"] not in seen_qids]
        for c in new_inst:
            seen_qids.add(c["qid"])
        all_concepts.extend(new_inst)
        if new_inst:
            print(f"    + {len(new_inst)} instances")

        time.sleep(2)  # polite rate limiting for Wikidata

    # Deduplicate and save
    print(f"\nTotal unique concepts: {len(all_concepts)}")

    # Build hierarchy summary
    roots_used = set(c["root_label"] for c in all_concepts)
    root_counts = {}
    for c in all_concepts:
        root_counts[c["root_label"]] = root_counts.get(c["root_label"], 0) + 1

    output = {
        "concepts": all_concepts,
        "stats": {
            "total_unique": len(all_concepts),
            "roots_queried": len(ROOT_CONCEPTS),
            "concepts_per_root": root_counts,
        },
    }

    out_path = OUT_DIR / "wikidata_economics_concepts.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved to {out_path}")

    # Also save flat CSV
    import csv
    csv_path = OUT_DIR / "wikidata_economics_flat.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["qid", "label", "description", "parent_qid", "parent_label", "root", "root_label"])
        for c in all_concepts:
            writer.writerow([c["qid"], c["label"], c.get("description", ""), c.get("parent_qid", ""),
                           c.get("parent_label", ""), c["root"], c["root_label"]])
    print(f"CSV saved to {csv_path}")

    # Print sample
    print(f"\nSample concepts:")
    for c in all_concepts[:20]:
        print(f"  {c['qid']:12s} {c['label'][:50]:50s} (root: {c['root_label']})")


if __name__ == "__main__":
    main()
