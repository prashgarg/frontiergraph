"""Scrape the full JEL classification guide with keywords, guidelines,
caveats, and examples at all levels (L1, L2, L3).

Uses the AJAX endpoints discovered from the page structure:
  - second_level.php?class=P     → L1 guideline + keywords + L2 listing
  - jel_sub.php?class=P1         → L3 codes within L2 + guidelines
  - second_level_keyword.php?class=P14 → keywords for L3 code

Output: data/ontology_v2/jel_full.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/ontology_v2"

BASE_URL = "https://www.aeaweb.org/content/jel_guide"

L1_CATEGORIES = list("ABCDEFGHIJKLMNOPQRYZ")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"    FAILED: {e}")
                return ""


def clean_html(text: str) -> str:
    """Strip HTML tags and clean whitespace."""
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_section(html: str, header: str) -> str:
    """Extract text after a section header like 'Guideline:' or 'Keywords:'."""
    pattern = rf'{header}\s*:?\s*</span>\s*(.*?)(?:<span class="sub_header"|<div class="lv|<ul|$)'
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_html(match.group(1))
    # Simpler pattern
    pattern2 = rf'{header}\s*:?\s*(.*?)(?:Keywords|Guideline|Caveats|Examples|<div class="lv|<ul|$)'
    match2 = re.search(pattern2, html, re.DOTALL | re.IGNORECASE)
    if match2:
        return clean_html(match2.group(1))
    return ""


def parse_keywords(text: str) -> list[str]:
    """Parse comma-separated keywords from raw text."""
    if not text:
        return []
    # Split on comma, clean each
    parts = [p.strip() for p in text.split(',')]
    return [p for p in parts if p and len(p) > 1]


def scrape_l1(letter: str) -> dict:
    """Fetch L1 level: guideline, keywords, and L2 code listing."""
    url = f"{BASE_URL}/second_level.php?class={letter}"
    html = fetch(url)
    if not html:
        return {"code": letter, "guideline": "", "keywords": [], "l2_codes": []}

    # Extract L1 guideline
    guideline = extract_section(html, "Guideline")

    # Extract L1 keywords
    kw_match = re.search(r'Keywords:\s*</span>\s*(.*?)</div>', html, re.DOTALL)
    keywords = []
    if kw_match:
        keywords = parse_keywords(clean_html(kw_match.group(1)))

    # Extract L2 codes from the listing
    l2_codes = []
    # Pattern: code like "P1" followed by title
    for m in re.finditer(r'class="first_level"[^>]*>\s*([A-Z]\d{1,2})\s+(.*?)\s*</a>', html, re.DOTALL):
        code = m.group(1).strip()
        title = clean_html(m.group(2))
        l2_codes.append({"code": code, "title": title})

    # Also extract L2-level guidelines if present inline
    # These appear in the lv2_2 divs
    for l2 in l2_codes:
        # Look for guideline text associated with this L2 code
        l2_pattern = rf'{re.escape(l2["code"])}\s.*?Guideline:\s*</span>\s*(.*?)(?:<div class|<br /><br />)'
        l2_guide_match = re.search(l2_pattern, html, re.DOTALL)
        if l2_guide_match:
            l2["guideline"] = clean_html(l2_guide_match.group(1))
        else:
            l2["guideline"] = ""

    return {
        "code": letter,
        "guideline": guideline,
        "keywords": keywords,
        "l2_codes": l2_codes,
    }


def scrape_l3(l2_code: str) -> list[dict]:
    """Fetch L3 codes within an L2 category."""
    url = f"{BASE_URL}/jel_sub.php?class={l2_code}"
    html = fetch(url)
    if not html:
        return []

    entries = []
    # Pattern: L3 codes like "P14" followed by title
    # These appear as links or headers
    for m in re.finditer(r'([A-Z]\d{2,3})\s+(.*?)(?:</a>|</div>|<br)', html, re.DOTALL):
        code = m.group(1).strip()
        title = clean_html(m.group(2))
        if not title or title == "General":
            title = "General"

        entries.append({
            "code": code,
            "title": title,
            "parent": l2_code,
        })

    return entries


def scrape_l3_keywords(l3_code: str) -> dict:
    """Fetch keywords, guideline, caveats, examples for an L3 code."""
    url = f"{BASE_URL}/second_level_keyword.php?class={l3_code}"
    html = fetch(url)
    if not html:
        return {"keywords": [], "guideline": "", "caveats": "", "examples": []}

    # Extract guideline
    guideline = ""
    guide_match = re.search(r'Guideline:\s*</span>\s*(.*?)(?:<br|<span|<div|Keywords|$)', html, re.DOTALL)
    if guide_match:
        guideline = clean_html(guide_match.group(1))

    # Extract keywords
    kw_match = re.search(r'Keywords:\s*</span>\s*(.*?)(?:<br|<div|Caveats|Examples|$)', html, re.DOTALL)
    keywords = []
    if kw_match:
        keywords = parse_keywords(clean_html(kw_match.group(1)))

    # Extract caveats
    caveats = ""
    caveat_match = re.search(r'Caveats:\s*</span>\s*(.*?)(?:<br|<div|Examples|Keywords|$)', html, re.DOTALL)
    if caveat_match:
        caveats = clean_html(caveat_match.group(1))

    # Extract examples
    examples = []
    ex_match = re.search(r'Examples:\s*</span>\s*(.*?)(?:</div>|$)', html, re.DOTALL)
    if ex_match:
        ex_text = clean_html(ex_match.group(1))
        examples = [e.strip() for e in ex_text.split('\n') if e.strip()]

    return {
        "keywords": keywords,
        "guideline": guideline,
        "caveats": caveats,
        "examples": examples,
    }


def main():
    print("Scraping full JEL guide (L1 + L2 + L3 with keywords)...\n")

    all_data = {}
    total_l2 = 0
    total_l3 = 0
    total_keywords = 0

    for letter in L1_CATEGORIES:
        print(f"[{letter}] Fetching L1...")
        l1_data = scrape_l1(letter)
        total_keywords += len(l1_data["keywords"])
        print(f"  L1 guideline: {len(l1_data['guideline'])} chars, {len(l1_data['keywords'])} keywords, {len(l1_data['l2_codes'])} L2 codes")

        # Fetch L3 for each L2
        for l2 in l1_data["l2_codes"]:
            total_l2 += 1
            print(f"  [{l2['code']}] {l2['title'][:40]}...")
            l3_codes = scrape_l3(l2["code"])
            l2["l3_codes"] = l3_codes
            total_l3 += len(l3_codes)

            # Fetch keywords for each L3
            for l3 in l3_codes:
                detail = scrape_l3_keywords(l3["code"])
                l3.update(detail)
                total_keywords += len(detail["keywords"])
                time.sleep(0.3)  # polite rate limit

            time.sleep(0.3)
        time.sleep(0.5)

        all_data[letter] = l1_data

    # Save
    out_path = OUT_DIR / "jel_full.json"
    with open(out_path, "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # Stats
    print(f"\n=== DONE ===")
    print(f"L1 categories: {len(L1_CATEGORIES)}")
    print(f"L2 subcategories: {total_l2}")
    print(f"L3 codes: {total_l3}")
    print(f"Total keywords: {total_keywords}")
    print(f"Saved to {out_path}")

    # Also build a flat keywords list
    all_keywords = set()
    for letter, l1 in all_data.items():
        for kw in l1.get("keywords", []):
            all_keywords.add(kw)
        for l2 in l1.get("l2_codes", []):
            for l3 in l2.get("l3_codes", []):
                for kw in l3.get("keywords", []):
                    all_keywords.add(kw)

    kw_path = OUT_DIR / "jel_all_keywords.txt"
    with open(kw_path, "w") as f:
        for kw in sorted(all_keywords):
            f.write(kw + "\n")
    print(f"Unique keywords: {len(all_keywords)}, saved to {kw_path}")


if __name__ == "__main__":
    main()
