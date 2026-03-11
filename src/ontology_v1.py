from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Iterable


STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

PAREN_ACRONYM_RAW_RE = re.compile(r"\s*\(([A-Z][A-Z0-9&/\-]{1,14})\)\s*$")
PAREN_ACRONYM_RE = re.compile(r"\s*\(([A-Za-z][A-Za-z0-9&/\-]{1,14})\)\s*$")
MULTISPACE_RE = re.compile(r"\s+")
NON_ALNUM_KEEP_PAREN_RE = re.compile(r"[^0-9a-z()\-\s]+")
NON_ALNUM_RE = re.compile(r"[^0-9a-z\s]+")


def normalize_label(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("–", "-").replace("—", "-").replace("−", "-")
    value = value.replace("&", " and ")
    value = value.casefold()
    value = value.replace("/", " ")
    value = NON_ALNUM_KEEP_PAREN_RE.sub(" ", value)
    value = MULTISPACE_RE.sub(" ", value).strip(" -")
    return value


def strip_parenthetical_acronym(normalized_label: str) -> str:
    match = PAREN_ACRONYM_RE.search(normalized_label)
    if not match:
        return normalized_label
    return normalized_label[: match.start()].strip()


def extract_parenthetical_acronym(raw_label: str) -> str | None:
    match = PAREN_ACRONYM_RAW_RE.search(raw_label or "")
    if not match:
        return None
    value = normalize_label(match.group(1))
    return value or None


def conservative_singularize_token(token: str) -> str:
    if len(token) <= 4:
        return token
    if token.endswith("ics"):
        return token
    if token.endswith("ies") and len(token) > 5:
        return token[:-3] + "y"
    if token.endswith("sses") or token.endswith("ss"):
        return token
    if token.endswith("s") and not token.endswith(("us", "is")):
        return token[:-1]
    return token


def punctuation_signature(normalized_label: str) -> str:
    text = NON_ALNUM_RE.sub(" ", normalized_label)
    return MULTISPACE_RE.sub(" ", text).strip()


def singular_signature(text: str) -> str:
    tokens = [conservative_singularize_token(token) for token in text.split()]
    return " ".join(tokens).strip()


def initialism_signature(text: str) -> str | None:
    tokens = [token for token in punctuation_signature(text).split() if token and token not in STOPWORDS]
    if not 2 <= len(tokens) <= 8:
        return None
    initialism = "".join(token[0] for token in tokens)
    if len(initialism) < 2:
        return None
    return initialism


def label_signatures(label: str) -> dict[str, str]:
    normalized = normalize_label(label)
    no_paren = strip_parenthetical_acronym(normalized)
    punct = punctuation_signature(no_paren)
    singular = singular_signature(punct)
    paren_acronym = extract_parenthetical_acronym(label)
    initialism = initialism_signature(no_paren)
    return {
        "normalized_label": normalized,
        "no_paren_signature": no_paren,
        "punctuation_signature": punct,
        "singular_signature": singular,
        "paren_acronym": paren_acronym or "",
        "initialism_signature": initialism or "",
    }


def preferred_label(label_counts: Counter[str]) -> str:
    if not label_counts:
        return "NA"
    return sorted(label_counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[0][0]


def top_items(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
        if value
    ]


def context_fingerprint(
    *,
    countries_json: str,
    unit_of_analysis_json: str,
    start_year_json: str,
    end_year_json: str,
    context_note: str,
) -> str:
    payload = {
        "countries": json.loads(countries_json),
        "units": json.loads(unit_of_analysis_json),
        "start_year": json.loads(start_year_json),
        "end_year": json.loads(end_year_json),
        "context_note": context_note,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    a = {item for item in left if item}
    b = {item for item in right if item}
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def counter_cosine_similarity(left: dict[str, int], right: dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    dot = sum(left[key] * right[key] for key in overlap)
    norm_left = sum(value * value for value in left.values()) ** 0.5
    norm_right = sum(value * value for value in right.values()) ** 0.5
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)


def sequence_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def canonical_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)
