"""Scrape the AEA JEL classification guide for all codes, keywords,
caveats, and examples.

Output: data/ontology_v2/jel_classification.json
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# JEL codes: 20 broad categories
JEL_CATEGORIES = {
    "A": "General Economics and Teaching",
    "B": "History of Economic Thought, Methodology, and Heterodox Approaches",
    "C": "Mathematical and Quantitative Methods",
    "D": "Microeconomics",
    "E": "Macroeconomics and Monetary Economics",
    "F": "International Economics",
    "G": "Financial Economics",
    "H": "Public Economics",
    "I": "Health, Education, and Welfare",
    "J": "Labor and Demographic Economics",
    "K": "Law and Economics",
    "L": "Industrial Organization",
    "M": "Business Administration and Business Economics; Marketing; Accounting; Personnel Economics",
    "N": "Economic History",
    "O": "Economic Development, Innovation, Technological Change, and Growth",
    "P": "Economic Systems",
    "Q": "Agricultural and Natural Resource Economics; Environmental and Ecological Economics",
    "R": "Urban, Rural, Regional, Real Estate, and Transportation Economics",
    "Y": "Miscellaneous Categories",
    "Z": "Other Special Topics",
}


def fetch_jel_page(url: str) -> str:
    """Fetch a URL and return the HTML content."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research project)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_jel_main_page(html: str) -> list[dict]:
    """Parse the main JEL guide page for L2 codes and links."""
    # The main page has links like /jel/guide/jel-A/
    codes = []
    # Pattern: links to subcategory pages
    for match in re.finditer(r'href="(/jel/guide/jel-([A-Z]\d{1,2})/)"[^>]*>([^<]+)', html):
        path, code, name = match.groups()
        codes.append({
            "code": code,
            "name": name.strip(),
            "url": f"https://www.aeaweb.org{path}",
        })
    return codes


def parse_jel_detail_page(html: str, parent_code: str) -> list[dict]:
    """Parse a JEL detail page for L3 codes with keywords, caveats, examples."""
    entries = []

    # Look for detailed code entries
    # Pattern varies but typically has code headers and content sections
    # Try to find all L3 codes (e.g., D110, F140)
    blocks = re.split(r'<h[23][^>]*>', html)

    current_code = None
    current_entry = None

    for block in blocks:
        # Look for code pattern like "D110" or "F14"
        code_match = re.search(r'([A-Z]\d{2,3})\s', block[:100])
        if code_match:
            if current_entry:
                entries.append(current_entry)

            code = code_match.group(1)
            # Extract title (text after code, before next HTML tag)
            title_match = re.search(rf'{re.escape(code)}\s+(.*?)(?:<|$)', block[:500])
            title = title_match.group(1).strip() if title_match else ""
            title = re.sub(r'<[^>]+>', '', title).strip()

            current_entry = {
                "code": code,
                "title": title,
                "parent": parent_code,
                "keywords": [],
                "caveats": [],
                "examples": [],
                "guideline": "",
            }

        if current_entry:
            # Extract keywords
            kw_match = re.search(r'Keywords?:\s*(.*?)(?:<br|<p|<div|$)', block, re.IGNORECASE | re.DOTALL)
            if kw_match:
                kw_text = re.sub(r'<[^>]+>', '', kw_match.group(1)).strip()
                keywords = [k.strip() for k in kw_text.split(',') if k.strip()]
                current_entry["keywords"].extend(keywords)

            # Extract caveats
            caveat_match = re.search(r'Caveats?:\s*(.*?)(?:<br|<p|<div|Keywords|Examples|$)', block, re.IGNORECASE | re.DOTALL)
            if caveat_match:
                caveat_text = re.sub(r'<[^>]+>', '', caveat_match.group(1)).strip()
                if caveat_text:
                    current_entry["caveats"].append(caveat_text)

            # Extract examples
            example_match = re.search(r'Examples?:\s*(.*?)(?:<br|<p|<div|$)', block, re.IGNORECASE | re.DOTALL)
            if example_match:
                ex_text = re.sub(r'<[^>]+>', '', example_match.group(1)).strip()
                examples = [e.strip() for e in re.split(r'\n|<br', ex_text) if e.strip()]
                current_entry["examples"].extend(examples)

            # Extract guideline
            guide_match = re.search(r'Guideline:\s*(.*?)(?:<br|<p|<div|Keywords|Caveats|Examples|$)', block, re.IGNORECASE | re.DOTALL)
            if guide_match:
                guide_text = re.sub(r'<[^>]+>', '', guide_match.group(1)).strip()
                if guide_text:
                    current_entry["guideline"] = guide_text

    if current_entry:
        entries.append(current_entry)

    return entries


def main():
    print("Scraping JEL classification guide...")

    # Step 1: Get the main page
    print("  Fetching main page...")
    main_url = "https://www.aeaweb.org/jel/guide/jel.php"
    main_html = fetch_jel_page(main_url)

    # Step 2: Parse L2 codes
    l2_codes = parse_jel_main_page(main_html)
    print(f"  Found {len(l2_codes)} L2 subcategories")

    # Also extract L2 from the main page structure
    # The page lists categories A through Z with subcategories

    # Step 3: Fetch each subcategory page for L3 details
    all_entries = []
    for i, l2 in enumerate(l2_codes):
        try:
            print(f"  [{i+1}/{len(l2_codes)}] Fetching {l2['code']}: {l2['name'][:50]}...")
            html = fetch_jel_page(l2["url"])
            entries = parse_jel_detail_page(html, l2["code"])

            # Also store the L2 entry itself
            l2_entry = {
                "code": l2["code"],
                "title": l2["name"],
                "level": 2,
                "parent": l2["code"][0],  # L1 category letter
                "keywords": [],
                "caveats": [],
                "examples": [],
                "guideline": "",
                "children": [e["code"] for e in entries],
            }
            all_entries.append(l2_entry)

            for e in entries:
                e["level"] = 3
                all_entries.append(e)

            time.sleep(0.5)  # polite rate limiting
        except Exception as ex:
            print(f"    Error: {ex}")

    # Step 4: Build the full hierarchy
    hierarchy = {
        "categories": {k: v for k, v in JEL_CATEGORIES.items()},
        "entries": all_entries,
        "stats": {
            "l1_categories": len(JEL_CATEGORIES),
            "l2_subcategories": len([e for e in all_entries if e.get("level") == 2]),
            "l3_codes": len([e for e in all_entries if e.get("level") == 3]),
            "total_keywords": sum(len(e.get("keywords", [])) for e in all_entries),
            "total_examples": sum(len(e.get("examples", [])) for e in all_entries),
        },
    }

    # Save
    out_path = OUT_DIR / "jel_classification.json"
    with open(out_path, "w") as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {out_path}")
    print(f"Stats: {hierarchy['stats']}")

    # Also save a flat CSV for easy inspection
    csv_path = OUT_DIR / "jel_codes_flat.csv"
    import csv
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "level", "parent", "title", "keywords", "n_examples"])
        for e in all_entries:
            writer.writerow([
                e["code"],
                e.get("level", ""),
                e.get("parent", ""),
                e.get("title", ""),
                "; ".join(e.get("keywords", [])),
                len(e.get("examples", [])),
            ])
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
