from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
GENERATED_DIR = SITE_ROOT / "src" / "generated"
GENERATED_SITE_DATA_PATH = GENERATED_DIR / os.environ.get("FRONTIERGRAPH_SITE_DATA_FILENAME", "site-data.json")
EDITORIAL_OPPORTUNITIES_PATH = SITE_ROOT / "src" / "content" / "editorial-opportunities.json"
QUESTIONS_CAROUSEL_ASSIGNMENTS_PATH = SITE_ROOT / "src" / "content" / "questions-carousel-assignments.json"
PUBLIC_LABEL_GLOSSARY_PATH = SITE_ROOT / "src" / "content" / "public-label-glossary.json"
PUBLIC_DATA_SEGMENT = os.environ.get("FRONTIERGRAPH_PUBLIC_DATA_SEGMENT", "v2")
PUBLIC_DATA_URL_PREFIX = f"/data/{PUBLIC_DATA_SEGMENT}"
PUBLIC_DATA_DIR = SITE_ROOT / "public" / "data" / PUBLIC_DATA_SEGMENT
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public" / "downloads"
NEIGHBORHOOD_SHARDS_DIR = PUBLIC_DATA_DIR / "concept_neighborhoods"
OPPORTUNITY_SHARDS_DIR = PUBLIC_DATA_DIR / "concept_opportunities"

REPO_URL = "https://github.com/prashgarg/frontiergraph"
DB_FILENAME = "frontiergraph-economics-public.db"
SITE_GRAPH_URL = os.environ.get("FRONTIERGRAPH_SITE_GRAPH_URL", "/graph/")
PUBLIC_APP_URL = os.environ.get(
    "FRONTIERGRAPH_PUBLIC_APP_URL",
    "https://frontiergraph.com/explorer/",
)
QUESTION_URL = os.environ.get("FRONTIERGRAPH_QUESTION_URL", "/questions/")
PUBLIC_DB_URL = os.environ.get(
    "FRONTIERGRAPH_PUBLIC_DB_URL",
    "https://storage.googleapis.com/frontiergraph-public-downloads-1058669339361/frontiergraph-economics-public.db",
)
PUBLIC_RELEASE_DIR = ROOT / "data" / "production" / "frontiergraph_public_release"
DEFAULT_PUBLIC_RELEASE_DB_PATH = Path(os.environ.get("FRONTIERGRAPH_PUBLIC_RELEASE_DB", f"/tmp/{DB_FILENAME}"))
SOURCE_PUBLIC_APP_DB_PATH = Path(
    os.environ.get(
        "FRONTIERGRAPH_PUBLIC_SOURCE_DB",
        ROOT
        / "data"
        / "production"
        / "frontiergraph_concept_compare_v1"
        / "baseline"
        / "suppression"
        / "concept_exploratory_suppressed_top100k_app.sqlite",
    )
)
PUBLIC_RELEASE_DB_PATH = DEFAULT_PUBLIC_RELEASE_DB_PATH
PUBLIC_GRAPH_DB_PATH = Path(
    os.environ.get(
        "FRONTIERGRAPH_PUBLIC_GRAPH_DB",
        str(PUBLIC_RELEASE_DIR / "frontiergraph-economics-public-graph.sqlite"),
    )
)
PAPER_SYNC_SCRIPT = ROOT / "scripts" / "sync_paper_site_assets.py"
DISPLAY_REFINEMENT_SCRIPT = ROOT / "scripts" / "build_public_display_refinement.py"
DISPLAY_REFINEMENT_PATH = PUBLIC_RELEASE_DIR / "display_refinement_v1.json"
BASELINE_ONTOLOGY_DB_PATH = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "baseline" / "ontology_v3.sqlite"
BROAD_ONTOLOGY_DB_PATH = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "broad" / "ontology_v3.sqlite"

EXTRACTION_SUMMARY_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_extraction_v2"
    / "fwci_core150_adj150"
    / "analysis"
    / "fwci_core150_adj150_corpus_summary.json"
)
HYBRID_CORPUS_MANIFEST_PATH = (
    ROOT
    / "data"
    / "processed"
    / "research_allocation_v2"
    / "hybrid_corpus_manifest.json"
)
WORKING_PAPER_PDF_PATH = ROOT / "paper" / "research_allocation_paper.pdf"
EXTENDED_ABSTRACT_PDF_PATH = ROOT / "paper" / "extended_abstract_research_allocation.pdf"

BACKBONE_NODE_LIMIT = 650
BACKBONE_EDGE_LIMIT = 2200
BACKBONE_MIN_SUPPORT = 4
BACKBONE_LABEL_LIMIT = 24
BACKBONE_LAYOUT_ITERATIONS = 140
BACKBONE_LAYOUT_K_MULTIPLIER = 2.8
BACKBONE_LAYOUT_SPREAD = 1.38
NEIGHBOR_LIMIT = 15
CONCEPT_OPPORTUNITY_LIMIT = 12
FEATURED_OPPORTUNITY_LIMIT = 12
PUBLIC_RANKED_WINDOW_LIMIT = 120
PUBLIC_RANKED_SOURCE_LIMIT = 2500
RANKED_EDITORIAL_WINDOW_LIMIT = 48
RANKED_DIVERSE_HEAD_LIMIT = 24
CURATED_ENDPOINT_FAMILY_CAP = 2
RANKED_ENDPOINT_FAMILY_CAP = 2
RANKED_DIVERSE_ENDPOINT_REPEAT_CAP = 2
RANKED_READY_SPECIFICITY_MIN = 0.2
RANKED_EDITORIAL_FALLBACK_PAIR_KEYS = (
    "FG3C000309__FG3C004045",
    "FG3C000843__FG3C002591",
    "FG3C000074__FG3C003563",
    "FG3C000008__FG3C005909",
    "FG3C000013__FG3C005708",
    "FG3C000264__FG3C004045",
    "FG3C004045__FG3C005027",
    "FG3C000100__FG3C003563",
)
PUBLIC_SLICE_EXPORT_LIMIT = 400
CAROUSEL_GROUP_SIZE = 10
FIELD_CAROUSEL_COUNT = 6
USE_CASE_CAROUSEL_COUNT = 3
CAROUSEL_ANCHOR_COUNT = 3
CAROUSEL_MAX_ADDITIONS = 2
FIELD_CAROUSEL_LIMIT = CAROUSEL_GROUP_SIZE
USE_CASE_CAROUSEL_LIMIT = CAROUSEL_GROUP_SIZE
SHARD_SIZE = 256
EDITORIAL_REQUIRED_FIELDS = (
    "pair_key",
    "question_title",
    "short_why",
    "first_next_step",
    "who_its_for",
    "homepage_featured",
    "questions_featured",
    "display_order",
    "homepage_role",
    "field_shelves",
    "collection_tags",
    "editorial_strength",
    "question_family",
)

QUESTION_CAROUSEL_ASSIGNMENT_ITEM_FIELDS = (
    "pair_key",
)

PUBLIC_LABEL_GLOSSARY_REQUIRED_FIELDS = (
    "concept_id",
    "subtitle",
)

FIELD_SHELF_DEFS = [
    {
        "slug": "macro-finance",
        "title": "Macro and finance",
        "caption": "Questions about fiscal space, monetary transmission, and aggregate demand that still feel paper-shaped.",
        "match_tokens": ["debt", "monetary", "inflation", "credit", "bank", "interest", "aggregate demand"],
    },
    {
        "slug": "development-urban",
        "title": "Development and urban",
        "caption": "Questions about growth, cities, capital deepening, and distribution that a development reader can act on quickly.",
        "match_tokens": ["urban", "city", "education", "wage", "inequality", "development", "human capital"],
    },
    {
        "slug": "trade-globalization",
        "title": "Trade and globalization",
        "caption": "Questions where trade exposure, imports, or exports may matter more than the standard growth framing suggests.",
        "match_tokens": ["trade", "export", "import", "sanctions", "globalization", "fdi"],
    },
    {
        "slug": "climate-energy",
        "title": "Climate and energy",
        "caption": "Questions that connect emissions, energy demand, and policy channels without collapsing into generic climate pairings.",
        "match_tokens": ["carbon", "emissions", "pollution", "environmental quality", "energy", "oil", "gas", "electricity", "mineral rents"],
    },
    {
        "slug": "innovation-productivity",
        "title": "Innovation and productivity",
        "caption": "Questions about whether cleaner innovation, environmental outcomes, and productivity really move together.",
        "match_tokens": ["innovation", "green innovation", "technology", "r&d", "productivity", "complexity"],
    },
]

USE_CASE_CAROUSEL_DEFS = [
    {
        "slug": "strong-nearby-evidence",
        "title": "Questions with stronger nearby evidence",
        "caption": "These already sit near more directed links, intermediate topics, and papers in the public release.",
    },
    {
        "slug": "phd-topic",
        "title": "Broader project candidates",
        "caption": "These feel large enough to grow into a project without losing a concrete starting point.",
    },
    {
        "slug": "open-little-direct",
        "title": "Open questions with little direct work",
        "caption": "These still look open in the current public release.",
    },
]

COLLECTION_DEFS = [
    {
        "slug": "cross-field",
        "title": "Cross-field questions",
        "caption": "Use these when you want a question that clearly bridges areas people usually read apart.",
    },
    {
        "slug": "open-little-direct",
        "title": "Open questions with little direct work",
        "caption": "These look especially useful when you want a topic that still seems open in the current public release.",
    },
    {
        "slug": "strong-nearby-evidence",
        "title": "Questions with stronger nearby evidence",
        "caption": "These have enough surrounding structure to feel grounded before you open the app.",
    },
    {
        "slug": "paper-ready",
        "title": "Questions with a clearer empirical shape",
        "caption": "These are among the more concrete questions in the released list.",
    },
    {
        "slug": "phd-topic",
        "title": "Broader project candidates",
        "caption": "These feel broad enough to grow into a project, but narrow enough to inspect as a first step.",
    },
]

GENERIC_PAPER_TITLE_PHRASES = (
    "nexus",
    "evidence from",
    "case study",
    "global perspective",
    "comprehensive analysis",
    "panel ardl",
    "quantile regression",
    "cointegration",
)
PUBLIC_WINDOW_BLOCKLIST_PHRASES = (
    "vector autoregressive model",
    "uncertainty measures",
    "relative prices",
    "distance",
)
RANKED_WINDOW_BLOCKLIST_PHRASES = (
    "high frequency trading",
    "individual forecasts",
    "wage setting",
    "volatility spillovers",
    "observed data",
    "choice data",
    "spot prices",
    "no treatment",
    "non fungible tokens",
    "nfts",
    "china stock market",
    "u s stock market",
    "s p 500",
    "stock returns",
    "equity premium",
    "bid ask spread",
    "logistic regression",
    "spatial durbin model",
    "price cost margin",
    "price to rent ratio",
    "optimal investment strategy",
    "separability",
    "numerical simulation",
    "coupling coordination degree",
    "negative news sentiment",
    "economic fundamentals",
    "marital status",
    "russia ukraine conflict",
    "esg investments",
    "resource allocation efficiency",
    "level of debt",
    "special economic zones",
    "catastrophic health expenditures",
    "u s economic policy uncertainty",
    "covid 19 pandemic",
    "subjective well being",
    "sustainable development",
    "green innovation",
    "green technology innovation",
    "innovation outcomes",
    "renewable portfolio standards",
    "financial performance",
    "tvp sv var model",
    "cyclical component",
    "innovation rate",
    "welfare level",
    "central and western cities",
    "airport efficiency",
    "green economic efficiency",
    "regional economic resilience",
    "high quality economic development",
    "inclusive green growth",
    "green economic growth",
    "sustainable economic growth",
    "industrial wastewater discharge",
    "real gdp per capita",
    "brics stock markets",
    "gcc stock market returns",
    "high tech industry",
    "export product quality",
)
RANKED_WINDOW_GENERIC_TARGETS = {
    "costs",
    "performance",
    "prices",
    "returns",
    "spot prices",
    "technology",
    "volatility",
}
PUBLIC_METHOD_TOPIC_PHRASES = (
    "model performance metrics",
    "method of moments quantile regression",
    "multivariate garch framework",
    "garch 1 1 model",
    "consistency and asymptotic normality of estimator",
    "quantile regression",
    "asymptotic normality",
    "granger causality",
    "cointegration",
    "panel ardl",
    "markov switching",
    "estimator",
    "forecast accuracy",
    "s p 500 volatility",
    "quality adjusted life year",
    "willingness to pay",
    "contingent valuation methods",
    "ordinary least squares",
    "arrival of new information",
    "rate of growth",
    "regional development level",
    "economic development level",
    "health related quality of life",
    "overlapping generations model",
    "error correction model",
    "vector error correction",
    "impulse response function",
    "stochastic frontier analysis",
)
GENERIC_PUBLIC_TOPIC_TERMS = {
    "consumption",
    "credit",
    "development",
    "economic development",
    "economic growth",
    "education",
    "employment",
    "exports",
    "financial development",
    "geopolitical risks",
    "human capital",
    "information and communication technologies",
    "inflation",
    "innovation",
    "institutional quality",
    "institutions",
    "investment",
    "model parameters",
    "monetary policy",
    "output growth",
    "price changes",
    "product innovation",
    "productivity",
    "public debt",
    "trade",
    "trade openness",
    "volatility",
}

TOKEN_STOPWORDS = {
    "and",
    "the",
    "of",
    "in",
    "for",
    "to",
    "with",
    "by",
    "on",
    "a",
    "an",
    "does",
    "do",
    "how",
    "when",
    "into",
    "through",
    "quality",
    "environmental",
    "growth",
    "economic",
    "policy",
    "consumption",
}

COUNTRY_CODE_ALIASES = {
    "CHN": "China",
    "USA": "United States",
    "US": "United States",
    "IND": "India",
    "GBR": "United Kingdom",
    "UK": "United Kingdom",
    "BRA": "Brazil",
    "DEU": "Germany",
    "FRA": "France",
    "ITA": "Italy",
    "ESP": "Spain",
    "CAN": "Canada",
    "AUS": "Australia",
    "ZAF": "South Africa",
    "ARE": "United Arab Emirates",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def ensure_display_refinement_artifact() -> Path:
    required_inputs = [
        SOURCE_PUBLIC_APP_DB_PATH,
        BASELINE_ONTOLOGY_DB_PATH,
        BROAD_ONTOLOGY_DB_PATH,
        DISPLAY_REFINEMENT_SCRIPT,
    ]
    artifact_missing = not DISPLAY_REFINEMENT_PATH.exists()
    artifact_stale = artifact_missing or any(
        path.exists() and path.stat().st_mtime > DISPLAY_REFINEMENT_PATH.stat().st_mtime
        for path in required_inputs
    )
    if artifact_stale:
        subprocess.run(
            [
                sys.executable,
                str(DISPLAY_REFINEMENT_SCRIPT),
                "--source-db",
                str(SOURCE_PUBLIC_APP_DB_PATH),
                "--baseline-ontology-db",
                str(BASELINE_ONTOLOGY_DB_PATH),
                "--broad-ontology-db",
                str(BROAD_ONTOLOGY_DB_PATH),
                "--output-path",
                str(DISPLAY_REFINEMENT_PATH),
            ],
            check=True,
        )
    return DISPLAY_REFINEMENT_PATH


def load_display_refinement() -> dict[str, Any]:
    path = ensure_display_refinement_artifact()
    payload = read_json(path)
    concepts = payload.get("concepts", {})
    return concepts if isinstance(concepts, dict) else {}


def connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def to_int(value: Any, default: int = 0) -> int:
    return int(round(to_float(value, float(default))))


def clean_public_text(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "na", "n/a", "nan", "none", "null", "undefined"}:
        return ""
    return text


def append_query_value(base_url: str, params: dict[str, Any]) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        cleaned = clean_public_text(value)
        if cleaned:
            query[key] = cleaned
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def build_question_link(pair_key: Any) -> str:
    cleaned = clean_public_text(pair_key)
    return f"{QUESTION_URL}#{cleaned}" if cleaned else QUESTION_URL


def build_graph_link(query: Any) -> str:
    return append_query_value(SITE_GRAPH_URL, {"q": query})


def build_app_question_link(pair_key: Any) -> str:
    return append_query_value(PUBLIC_APP_URL, {"view": "question", "pair": pair_key})


def build_app_concept_link(concept_id: Any) -> str:
    return append_query_value(PUBLIC_APP_URL, {"view": "concept", "concept": concept_id})


def build_app_compare_link(pair_keys: list[str]) -> str:
    cleaned = [clean_public_text(value) for value in pair_keys if clean_public_text(value)]
    return append_query_value(PUBLIC_APP_URL, {"view": "compare", "pairs": ",".join(cleaned)})


def normalize_context_value(value: Any) -> str:
    text = clean_public_text(value)
    if not text:
        return ""
    normalized = COUNTRY_CODE_ALIASES.get(text.upper(), text)
    if len(normalized) == 3 and normalized.isupper() and normalized in COUNTRY_CODE_ALIASES:
        normalized = COUNTRY_CODE_ALIASES[normalized]
    return normalized


def normalized_label_key(value: Any) -> str:
    text = clean_public_text(value).lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("/", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_count(value: Any) -> int:
    normalized = normalized_label_key(value)
    return len([token for token in normalized.split() if token])


def significant_tokens(*values: Any) -> list[str]:
    tokens: list[str] = []
    for value in values:
        normalized = normalized_label_key(value)
        for token in normalized.split():
            if len(token) < 3 or token in TOKEN_STOPWORDS:
                continue
            tokens.append(token)
    return uniq_keep_order(tokens, limit=8)


def parse_json_list(raw: Any) -> list[Any]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    try:
        loaded = json.loads(raw)
    except Exception:
        return []
    return loaded if isinstance(loaded, list) else []


def normalize_bucket_profile(raw: Any) -> dict[str, int]:
    profile: dict[str, int] = {}
    for item in parse_json_list(raw):
        if isinstance(item, dict):
            profile[str(item.get("value", ""))] = int(item.get("count", 0))
    return profile


def top_values(raw: Any, limit: int = 3) -> list[str]:
    values: list[str] = []
    for item in parse_json_list(raw):
        if isinstance(item, dict) and item.get("value"):
            text = normalize_context_value(item["value"])
            if text:
                values.append(text)
        elif isinstance(item, str):
            text = normalize_context_value(item)
            if text:
                values.append(text)
    return uniq_keep_order(values, limit=limit)


def uniq_keep_order(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = clean_public_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
        if limit is not None and len(out) >= limit:
            break
    return out


def bucket_priority(bucket_hint: str | None) -> tuple[int, str]:
    normalized = clean_public_text(bucket_hint).lower()
    if normalized == "core":
        return (0, normalized)
    if normalized == "mixed":
        return (1, normalized)
    if normalized == "adjacent":
        return (2, normalized)
    return (3, normalized)


def stable_public_pair_label(
    left_label: str,
    right_label: str,
    left_bucket: str | None,
    right_bucket: str | None,
) -> str:
    left = (bucket_priority(left_bucket), clean_public_text(left_label).lower(), clean_public_text(left_label))
    right = (bucket_priority(right_bucket), clean_public_text(right_label).lower(), clean_public_text(right_label))
    ordered = sorted([left, right], key=lambda item: (item[0], item[1]))
    return f"{ordered[0][2]} and {ordered[1][2]}"


def public_label_payload(
    concept_id: str | None,
    raw_label: Any,
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]] | None = None,
) -> dict[str, str]:
    label = clean_public_text(raw_label) or str(concept_id or "")
    refinement = (display_refinement or {}).get(str(concept_id or ""), {})
    display_label = clean_public_text(refinement.get("display_label")) or label
    display_concept_id = clean_public_text(refinement.get("display_concept_id")) or str(concept_id or "")
    entry = glossary.get(str(concept_id or ""), {}) or glossary.get(display_concept_id, {})
    plain_label = clean_public_text(entry.get("plain_label")) or display_label
    subtitle = clean_public_text(entry.get("subtitle"))
    return {
        "baseline_label": label,
        "display_label": display_label,
        "display_concept_id": display_concept_id,
        "display_refined": bool(refinement.get("display_refined", False)),
        "display_refinement_confidence": round(to_float(refinement.get("display_refinement_confidence"), 0.0), 4),
        "alternate_display_labels": uniq_keep_order(
            [clean_public_text(value) for value in refinement.get("alternate_display_labels", []) if clean_public_text(value)],
            limit=3,
        ),
        "plain_label": plain_label,
        "subtitle": subtitle,
    }


def concept_display_row(
    concept_id: str,
    raw_label: Any,
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    payload = public_label_payload(concept_id, raw_label, glossary, display_refinement)
    return {
        "display_label": payload["plain_label"],
        "display_concept_id": payload["display_concept_id"],
        "display_refined": payload["display_refined"],
        "display_refinement_confidence": payload["display_refinement_confidence"],
        "alternate_display_labels": payload["alternate_display_labels"],
    }


def build_common_contexts(
    source_label: str,
    target_label: str,
    source_context_summary: str,
    target_context_summary: str,
) -> str:
    source_summary = clean_public_text(source_context_summary)
    target_summary = clean_public_text(target_context_summary)
    if not source_summary or not target_summary:
        return ""
    if source_summary.startswith("No dominant") or target_summary.startswith("No dominant"):
        return ""
    return f"{source_label} studies are common in {source_summary}; {target_label} studies are common in {target_summary}."


def public_slice_label(values: dict[str, Any]) -> str:
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    gap_bonus = to_float(values.get("gap_bonus", 0.0))
    cross_bucket = bool(values.get("cross_bucket", False))
    if cooc_count <= 0:
        return "Missing direct link"
    if path_support >= 0.95:
        return "Ready to follow through"
    if gap_bonus >= 0.85 and cooc_count <= 2:
        return "Early but promising"
    if cross_bucket:
        return "Connect separate literatures"
    return "Support from nearby literature"


def direct_link_status(cooc_count: int) -> str:
    if cooc_count <= 0:
        return "No direct papers yet"
    if cooc_count == 1:
        return "One direct paper so far"
    if cooc_count <= 5:
        return "A few direct papers already exist"
    return "Direct work already exists"


def recommended_move(values: dict[str, Any]) -> str:
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    mediator_count = to_int(values.get("mediator_count", 0))
    cross_bucket = bool(values.get("cross_bucket", False))
    if cross_bucket and cooc_count <= 0:
        return "Start with a short review or pilot study that follows the nearest mediating topics."
    if path_support >= 0.95 and mediator_count >= 10:
        return "A direct empirical test looks like the natural next step."
    if cooc_count <= 0:
        return "A short synthesis or pilot design looks like the sensible first move."
    return "Use the nearby papers to define a tighter follow-up around the same mechanism."


def plain_language_context(values: list[str], fallback: str) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return fallback
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{cleaned[0]}, {cleaned[1]}, and related settings"


def why_now(values: dict[str, Any]) -> str:
    source_label = str(values.get("u_preferred_label") or values.get("source_label") or "")
    target_label = str(values.get("v_preferred_label") or values.get("target_label") or "")
    mediator_count = to_int(values.get("mediator_count", 0))
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    support_level = "strong" if path_support >= 0.95 else "visible"
    if cooc_count <= 0:
        if mediator_count > 0:
            return f"{source_label} and {target_label} are already linked by {mediator_count} nearby intermediate topics."
        return f"Nearby papers touch both {source_label} and {target_label}, but the local route is still thin."
    if cooc_count == 1:
        direct_copy = "one direct paper so far"
    elif cooc_count <= 5:
        direct_copy = f"{cooc_count} direct papers so far"
    else:
        direct_copy = "an existing direct literature"
    return (
        f"{source_label} and {target_label} already have {direct_copy}, while {mediator_count} nearby topics provide {support_level} support for a tighter follow-up."
    )


def short_path_line(values: dict[str, Any]) -> str:
    mediators = uniq_keep_order(
        [clean_public_text(value) for value in values.get("top_mediator_labels", []) if clean_public_text(value)],
        limit=4,
    )
    if len(mediators) >= 3:
        return f"Linked nearby through {mediators[0]}, {mediators[1]}, and {mediators[2]}."
    if len(mediators) == 2:
        return f"Closest route runs through {mediators[0]} and {mediators[1]}."
    if len(mediators) == 1:
        return f"Closest route runs through {mediators[0]}."
    return "Nearby papers touch both sides, but the local route is still thin."


def generated_first_step(values: dict[str, Any]) -> str:
    source_label = clean_public_text(values.get("source_display_label") or values.get("source_label"))
    target_label = clean_public_text(values.get("target_display_label") or values.get("target_label"))
    mediators = uniq_keep_order(
        [clean_public_text(value) for value in values.get("top_mediator_labels", []) if clean_public_text(value)],
        limit=3,
    )
    if len(mediators) >= 3:
        return (
            f"Start by tracing {source_label} to {target_label} through {mediators[0]}, {mediators[1]}, "
            f"and {mediators[2]} before testing the endpoint link directly."
        )
    if len(mediators) == 2:
        return f"Start by testing whether {mediators[0]} and {mediators[1]} are the main channels linking {source_label} to {target_label}."
    if len(mediators) == 1:
        return f"Start with {mediators[0]} as the first channel linking {source_label} to {target_label}."
    if to_int(values.get("cooc_count", 0)) <= 0:
        return f"Start with a short review that narrows where {source_label} could plausibly reach {target_label}."
    return f"Start with the nearby papers and tighten the mechanism connecting {source_label} to {target_label}."


def resolve_top_mediator_labels(
    raw: Any,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in parse_json_list(raw):
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("mediator", "")).strip()
        if not concept_id:
            continue
        raw_label = concept_label_lookup.get(concept_id, concept_id)
        public_label = public_label_payload(concept_id, raw_label, glossary, display_refinement)["plain_label"]
        normalized = normalized_label_key(public_label)
        if not public_label or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        labels.append(public_label)
        if len(labels) >= limit:
            break
    return labels


def resolve_top_mediator_baseline_labels(
    raw: Any,
    concept_label_lookup: dict[str, str],
    limit: int = 3,
) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in parse_json_list(raw):
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("mediator", "")).strip()
        if not concept_id:
            continue
        baseline_label = clean_public_text(concept_label_lookup.get(concept_id, concept_id))
        normalized = normalized_label_key(baseline_label)
        if not baseline_label or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        labels.append(baseline_label)
        if len(labels) >= limit:
            break
    return labels


def paper_title_score(
    paper: dict[str, Any],
    source_label: str,
    target_label: str,
    source_edge_label: str,
    target_edge_label: str,
) -> float:
    title = normalized_label_key(paper.get("title"))
    if not title:
        return -10.0

    source_phrase = normalized_label_key(source_label)
    target_phrase = normalized_label_key(target_label)
    source_edge_phrase = normalized_label_key(source_edge_label)
    target_edge_phrase = normalized_label_key(target_edge_label)
    title_tokens = set(title.split())

    score = 0.0
    if source_phrase and source_phrase in title:
        score += 4.0
    if target_phrase and target_phrase in title:
        score += 4.0
    if source_edge_phrase and source_edge_phrase in title:
        score += 2.0
    if target_edge_phrase and target_edge_phrase in title:
        score += 2.0

    score += 1.1 * sum(token in title_tokens for token in significant_tokens(source_label, source_edge_label))
    score += 1.1 * sum(token in title_tokens for token in significant_tokens(target_label, target_edge_label))

    generic_penalty = sum(phrase in title for phrase in GENERIC_PAPER_TITLE_PHRASES)
    score -= 0.35 * generic_penalty
    score += max(0.0, 1.6 - 0.3 * float(paper.get("path_rank", 99)))
    score += max(0.0, 0.8 - 0.15 * float(paper.get("paper_rank", 99)))
    score += min(max(to_int(paper.get("year", 0)) - 2016, 0), 8) * 0.04
    return score


def select_representative_papers(
    values: dict[str, Any],
    papers: list[dict[str, Any]],
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not papers:
        return []

    source_public = public_label_payload(values["u"], values["u_preferred_label"], glossary, display_refinement)["plain_label"]
    target_public = public_label_payload(values["v"], values["v_preferred_label"], glossary, display_refinement)["plain_label"]

    scored: list[tuple[float, dict[str, Any]]] = []
    for paper in papers:
        source_edge_label = concept_label_lookup.get(str(paper.get("edge_src", "")), "")
        target_edge_label = concept_label_lookup.get(str(paper.get("edge_dst", "")), "")
        score = paper_title_score(paper, source_public, target_public, source_edge_label, target_edge_label)
        scored.append((score, paper))

    scored.sort(
        key=lambda item: (
            item[0],
            -to_float(item[1].get("path_rank", 99), 99.0),
            -to_float(item[1].get("paper_rank", 99), 99.0),
            to_int(item[1].get("year", 0)),
        ),
        reverse=True,
    )
    strong = [paper for score, paper in scored if score >= 2.0]
    if len(strong) >= 2:
        chosen = strong[:3]
    else:
        chosen = [paper for _score, paper in scored[: min(2, len(scored))]]

    out: list[dict[str, Any]] = []
    for paper in chosen:
        out.append(
            {
                "paper_id": str(paper["paper_id"]),
                "title": clean_public_text(paper["title"]),
                "year": to_int(paper["year"]),
                "edge_src": str(paper["edge_src"]),
                "edge_dst": str(paper["edge_dst"]),
                "edge_src_display_label": public_label_payload(
                    str(paper["edge_src"]),
                    concept_label_lookup.get(str(paper["edge_src"]), str(paper["edge_src"])),
                    glossary,
                    display_refinement,
                )["plain_label"],
                "edge_dst_display_label": public_label_payload(
                    str(paper["edge_dst"]),
                    concept_label_lookup.get(str(paper["edge_dst"]), str(paper["edge_dst"])),
                    glossary,
                    display_refinement,
                )["plain_label"],
            }
        )
    return out


def load_representative_papers() -> dict[tuple[str, str], list[dict[str, Any]]]:
    sql = """
        WITH deduped AS (
            SELECT
                candidate_u,
                candidate_v,
                path_rank,
                paper_rank,
                paper_id,
                title,
                year,
                edge_src,
                edge_dst,
                ROW_NUMBER() OVER (
                    PARTITION BY candidate_u, candidate_v, paper_id
                    ORDER BY path_rank, paper_rank
                ) AS paper_occurrence_rank
            FROM candidate_papers
        ),
        limited AS (
            SELECT
                candidate_u,
                candidate_v,
                path_rank,
                paper_rank,
                paper_id,
                title,
                year,
                edge_src,
                edge_dst,
                ROW_NUMBER() OVER (
                    PARTITION BY candidate_u, candidate_v
                    ORDER BY path_rank, paper_rank, year DESC, paper_id
                ) AS representative_rank
            FROM deduped
            WHERE paper_occurrence_rank = 1
        )
        SELECT
            candidate_u,
            candidate_v,
            path_rank,
            paper_rank,
            paper_id,
            title,
            year,
            edge_src,
            edge_dst
        FROM limited
        WHERE representative_rank <= 16
        ORDER BY candidate_u, candidate_v, representative_rank
    """

    with connect(SOURCE_PUBLIC_APP_DB_PATH) as conn:
        rows = conn.execute(sql).fetchall()

    lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate_u, candidate_v, path_rank, paper_rank, paper_id, title, year, edge_src, edge_dst in rows:
        lookup[(str(candidate_u), str(candidate_v))].append(
            {
                "paper_id": str(paper_id),
                "title": clean_public_text(title),
                "year": to_int(year),
                "edge_src": str(edge_src),
                "edge_dst": str(edge_dst),
                "path_rank": to_int(path_rank),
                "paper_rank": to_int(paper_rank),
            }
        )
    return lookup


def topic_broadness_penalty(label: str, distinct_paper_support: int, refined: bool) -> float:
    normalized = normalized_label_key(label)
    penalty = 0.0
    if normalized in GENERIC_PUBLIC_TOPIC_TERMS:
        penalty += 10.0
    if any(phrase in normalized for phrase in PUBLIC_METHOD_TOPIC_PHRASES):
        penalty += 14.0
    if token_count(label) <= 2:
        penalty += 2.5
    if distinct_paper_support >= 8000:
        penalty += 4.0
    elif distinct_paper_support >= 4000:
        penalty += 2.0
    if not refined:
        penalty += 2.5
    return penalty


def public_specificity_score(
    values: dict[str, Any],
    source_public: dict[str, Any],
    target_public: dict[str, Any],
) -> float:
    score = 0.0
    if source_public["display_refined"]:
        score += 5.0
    if target_public["display_refined"]:
        score += 5.0
    score += min(to_int(values.get("mediator_count", 0)), 20) * 0.35
    score += min(to_int(values.get("supporting_path_count", values.get("mediator_count", 0))), 20) * 0.25
    score += min(to_float(values.get("path_support_norm", 0.0)), 1.0) * 5.0
    if to_int(values.get("cooc_count", 0)) <= 0:
        score += 1.6
    if source_public["display_refined"] and target_public["display_refined"]:
        score += 2.0
    source_penalty = topic_broadness_penalty(
        source_public["plain_label"],
        to_int(values.get("u_distinct_paper_support", 0)),
        bool(source_public["display_refined"]),
    )
    target_penalty = topic_broadness_penalty(
        target_public["plain_label"],
        to_int(values.get("v_distinct_paper_support", 0)),
        bool(target_public["display_refined"]),
    )
    score -= source_penalty + target_penalty
    if (
        normalized_label_key(source_public["plain_label"]) in GENERIC_PUBLIC_TOPIC_TERMS
        and normalized_label_key(target_public["plain_label"]) in GENERIC_PUBLIC_TOPIC_TERMS
        and not source_public["display_refined"]
        and not target_public["display_refined"]
    ):
        score -= 6.0
    return round(score, 4)


def infer_question_family(source_label: str, target_label: str) -> str:
    combined = f"{normalized_label_key(source_label)} {normalized_label_key(target_label)}"
    if "public debt" in combined and any(token in combined for token in ("co2", "carbon", "environmental", "emissions")):
        return "debt-climate"
    if "monetary policy" in combined and "energy" in combined:
        return "monetary-energy"
    if "monetary policy" in combined and any(token in combined for token in ("consumer", "demand", "consumption")):
        return "monetary-demand"
    if "urbanization" in combined and any(token in combined for token in ("output", "growth", "productivity")):
        return "urban-growth"
    if "investment" in combined and any(token in combined for token in ("co2", "carbon", "environmental", "emissions")):
        return "investment-climate"
    if any(token in combined for token in ("trade liberalisation", "trade integration")) and "energy" in combined:
        return "trade-energy"
    if any(token in combined for token in ("exports", "imports", "trade", "foreign direct investment", "fdi")) and any(
        token in combined for token in ("co2", "carbon", "environmental", "pollution", "quality")
    ):
        return "trade-environment"
    if "education" in combined and "wage inequality" in combined:
        return "education-inequality"
    if "green innovation" in combined and "productivity" in combined:
        return "innovation-productivity"
    if any(token in combined for token in ("innovation", "green innovation")) and any(
        token in combined for token in ("environmental", "ecological", "co2", "carbon", "quality", "load capacity")
    ):
        return "innovation-environment"
    if "productivity" in combined and any(token in combined for token in ("co2", "carbon", "environmental")):
        return "productivity-environment"
    return combined.replace(" ", "-")[:80] or "general"


def public_window_penalty(row: dict[str, Any]) -> tuple[int, int]:
    penalty = 0
    source_label = normalized_label_key(row.get("source_display_label") or row.get("source_label"))
    target_label = normalized_label_key(row.get("target_display_label") or row.get("target_label"))
    label_blob = " ".join([source_label, target_label, normalized_label_key(row.get("public_pair_label"))])
    if any(phrase in label_blob for phrase in PUBLIC_WINDOW_BLOCKLIST_PHRASES):
        penalty += 25
    if any(phrase in label_blob for phrase in PUBLIC_METHOD_TOPIC_PHRASES):
        penalty += 20
    if source_label in GENERIC_PUBLIC_TOPIC_TERMS:
        penalty += 9
    if target_label in GENERIC_PUBLIC_TOPIC_TERMS:
        penalty += 9
    if source_label in GENERIC_PUBLIC_TOPIC_TERMS and target_label in GENERIC_PUBLIC_TOPIC_TERMS:
        penalty += 10
    if len(row.get("representative_papers", [])) < 2:
        penalty += 8
    if not row.get("common_contexts"):
        penalty += 4
    if len(row.get("top_mediator_labels", [])) < 2:
        penalty += 4
    if not row.get("source_display_refined"):
        penalty += 2
    if not row.get("target_display_refined"):
        penalty += 2
    if row.get("suppress_from_public_ranked_window"):
        penalty += 100
    penalty -= int(round(max(min(to_float(row.get("public_specificity_score", 0.0)), 18.0), -18.0)))
    return penalty, to_int(row.get("cooc_count", 0))


def ranked_window_title_is_weak(row: dict[str, Any]) -> bool:
    source_label = normalized_label_key(row.get("source_display_label") or row.get("source_label"))
    target_label = normalized_label_key(row.get("target_display_label") or row.get("target_label"))
    label_blob = " ".join(
        value
        for value in (
            source_label,
            target_label,
            normalized_label_key(row.get("public_pair_label")),
            normalized_label_key(" ".join(row.get("top_mediator_labels", []))),
        )
        if value
    )
    if any(phrase in label_blob for phrase in PUBLIC_METHOD_TOPIC_PHRASES):
        return True
    if any(phrase in label_blob for phrase in RANKED_WINDOW_BLOCKLIST_PHRASES):
        return True
    if target_label in RANKED_WINDOW_GENERIC_TARGETS and token_count(row.get("source_display_label") or row.get("source_label")) <= 2:
        return True
    if source_label in RANKED_WINDOW_GENERIC_TARGETS and token_count(row.get("target_display_label") or row.get("target_label")) <= 2:
        return True
    return False


def ranked_window_ready(row: dict[str, Any]) -> bool:
    if row.get("suppress_from_public_ranked_window"):
        return False
    if ranked_window_title_is_weak(row):
        return False
    if row_endpoint_families(row):
        return False
    if len(row.get("representative_papers", [])) < 2:
        return False
    if len(row.get("top_mediator_labels", [])) < 2:
        return False
    if not clean_public_text(row.get("display_question_title")):
        return False
    if to_float(row.get("public_specificity_score", 0.0)) < RANKED_READY_SPECIFICITY_MIN:
        return False
    return True


def opportunity_record(
    row: sqlite3.Row | tuple[Any, ...],
    columns: list[str],
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    values = dict(zip(columns, row))
    cooc_count = to_int(values["cooc_count"])
    top_source = top_values(values["u_top_countries"], limit=3)
    top_target = top_values(values["v_top_countries"], limit=3)
    source_public = public_label_payload(values["u"], values["u_preferred_label"], glossary, display_refinement)
    target_public = public_label_payload(values["v"], values["v_preferred_label"], glossary, display_refinement)
    editorial_entry = (editorial or {}).get(str(values["pair_key"]), {})
    cross_field = clean_public_text(values.get("u_bucket_hint")) != clean_public_text(values.get("v_bucket_hint"))
    representative_papers = select_representative_papers(
        values,
        [
            paper
            for paper in representative_papers_lookup.get((str(values["u"]), str(values["v"])), [])
            if clean_public_text(paper.get("title"))
        ],
        concept_label_lookup,
        glossary,
        display_refinement,
    )
    source_context_summary = plain_language_context(top_source, "No dominant source setting in the current public release")
    target_context_summary = plain_language_context(top_target, "No dominant target setting in the current public release")
    specificity_score = public_specificity_score(values, source_public, target_public)
    display_refinement_confidence = round(
        (
            to_float(source_public["display_refinement_confidence"])
            + to_float(target_public["display_refinement_confidence"])
        )
        / 2.0,
        4,
    )
    return {
        "pair_key": values["pair_key"],
        "source_id": values["u"],
        "target_id": values["v"],
        "source_label": values["u_preferred_label"],
        "target_label": values["v_preferred_label"],
        "source_display_label": source_public["plain_label"],
        "target_display_label": target_public["plain_label"],
        "source_display_concept_id": source_public["display_concept_id"],
        "target_display_concept_id": target_public["display_concept_id"],
        "source_display_refined": source_public["display_refined"],
        "target_display_refined": target_public["display_refined"],
        "display_refinement_confidence": display_refinement_confidence,
        "source_alternate_display_labels": source_public["alternate_display_labels"],
        "target_alternate_display_labels": target_public["alternate_display_labels"],
        "source_bucket": values["u_bucket_hint"],
        "target_bucket": values["v_bucket_hint"],
        "cross_field": cross_field,
        "score": round(to_float(values["score"]), 6),
        "base_score": round(to_float(values["base_score"]), 6),
        "duplicate_penalty": round(to_float(values.get("duplicate_penalty", 0.0)), 6),
        "path_support_norm": round(to_float(values["path_support_norm"]), 6),
        "gap_bonus": round(to_float(values["gap_bonus"]), 6),
        "mediator_count": to_int(values["mediator_count"]),
        "motif_count": to_int(values["motif_count"]),
        "cooc_count": cooc_count,
        "direct_link_status": direct_link_status(cooc_count),
        "supporting_path_count": to_int(values["mediator_count"]),
        "why_now": why_now(
            {
                **values,
                "u_preferred_label": source_public["plain_label"],
                "v_preferred_label": target_public["plain_label"],
            }
        ),
        "recommended_move": recommended_move(values),
        "slice_label": public_slice_label(values),
        "public_pair_label": stable_public_pair_label(
            source_public["plain_label"],
            target_public["plain_label"],
            values.get("u_bucket_hint"),
            values.get("v_bucket_hint"),
        ),
        "display_question_title": "",
        "representative_papers": representative_papers,
        "question_family": clean_public_text(editorial_entry.get("question_family"))
        or infer_question_family(source_public["plain_label"], target_public["plain_label"]),
        "suppress_from_public_ranked_window": bool(editorial_entry.get("suppress_from_public_ranked_window", False)),
        "top_mediator_display_labels": resolve_top_mediator_labels(
            values.get("top_mediators_json"),
            concept_label_lookup,
            glossary,
            display_refinement,
            limit=3,
        ),
        "top_mediator_labels": resolve_top_mediator_labels(
            values.get("top_mediators_json"),
            concept_label_lookup,
            glossary,
            display_refinement,
            limit=3,
        ),
        "top_mediator_baseline_labels": resolve_top_mediator_baseline_labels(
            values.get("top_mediators_json"),
            concept_label_lookup,
            limit=3,
        ),
        "top_countries_source": top_source,
        "top_countries_target": top_target,
        "source_context_summary": source_context_summary,
        "target_context_summary": target_context_summary,
        "common_contexts": build_common_contexts(
            source_public["plain_label"],
            target_public["plain_label"],
            source_context_summary,
            target_context_summary,
        ),
        "public_specificity_score": specificity_score,
        "app_link": build_app_question_link(values["pair_key"]),
        "editorial_question_title": clean_public_text(editorial_entry.get("question_title")),
    }


def export_rows_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_candidates() -> pd.DataFrame:
    with connect(SOURCE_PUBLIC_APP_DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM candidates ORDER BY score DESC", conn)


def load_node_details() -> pd.DataFrame:
    with connect(SOURCE_PUBLIC_APP_DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM node_details", conn)


def load_graph_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with connect(PUBLIC_GRAPH_DB_PATH) as conn:
        edges = pd.read_sql_query("SELECT * FROM concept_edges", conn)
        profiles = pd.read_sql_query("SELECT * FROM concept_edge_profiles", conn)
        contexts = pd.read_sql_query("SELECT * FROM concept_edge_contexts", conn)
        exemplars = pd.read_sql_query("SELECT * FROM concept_edge_exemplars", conn)
    return edges, profiles, contexts, exemplars


def add_slice_flags(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working["cross_bucket"] = working["u_bucket_hint"] != working["v_bucket_hint"]
    working["bridge_flag"] = working["cross_bucket"]
    working["frontier_flag"] = working["cooc_count"].fillna(0) <= 1
    working["fast_follow_flag"] = (working["cooc_count"].fillna(0) > 0) & (working["path_support_norm"].fillna(0) >= 0.95)
    gap_cut = float(working["gap_bonus"].quantile(0.85)) if len(working) else 0.0
    working["underexplored_flag"] = (working["cooc_count"].fillna(0) <= 2) & (working["gap_bonus"].fillna(0) >= gap_cut)
    return working


def build_slices(
    df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    columns = list(df.columns)
    def top_records(mask: pd.Series | None, limit: int = PUBLIC_SLICE_EXPORT_LIMIT) -> list[dict[str, Any]]:
        raw_limit = max(limit * 30, 2500)
        if mask is None:
            subset = df.head(raw_limit)
        else:
            subset = df.loc[mask].head(raw_limit)
        subset_rows = [tuple(row) for row in subset.itertuples(index=False, name=None)]
        records = [
            opportunity_record(row, columns, concept_label_lookup, glossary, display_refinement, representative_papers_lookup, editorial)
            for row in subset_rows
        ]
        records.sort(
            key=lambda row: (
                is_climate_heavy(row),
                public_window_penalty(row),
                -to_float(row.get("public_specificity_score", 0.0)),
                -to_float(row.get("score", 0.0)),
                str(row.get("pair_key", "")),
            )
        )
        return records[:limit]

    return {
        "overall": top_records(None),
        "bridges": top_records(df["bridge_flag"]),
        "frontier": top_records(df["frontier_flag"]),
        "fast_follow": top_records(df["fast_follow_flag"]),
        "underexplored": top_records(df["underexplored_flag"]),
    }


def build_ranked_source_rows(
    df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]],
    limit: int = PUBLIC_RANKED_SOURCE_LIMIT,
) -> list[dict[str, Any]]:
    raw_limit = max(limit * 10, 6000)
    subset = df.head(raw_limit)
    columns = list(df.columns)
    subset_rows = [tuple(row) for row in subset.itertuples(index=False, name=None)]
    records = [
        opportunity_record(row, columns, concept_label_lookup, glossary, display_refinement, representative_papers_lookup, editorial)
        for row in subset_rows
    ]
    records.sort(
        key=lambda row: (
            is_climate_heavy(row),
            public_window_penalty(row),
            -to_float(row.get("public_specificity_score", 0.0)),
            -to_float(row.get("score", 0.0)),
            str(row.get("pair_key", "")),
        )
    )
    return records[:limit]


def build_specific_opportunity_rows(
    pair_keys: list[str] | tuple[str, ...],
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    requested = [clean_public_text(pair_key) for pair_key in pair_keys if clean_public_text(pair_key)]
    if not requested:
        return []
    subset_df = candidates_df[candidates_df["pair_key"].isin(requested)].copy()
    columns = list(subset_df.columns)
    records_by_pair: dict[str, dict[str, Any]] = {}
    for row in subset_df.itertuples(index=False, name=None):
        record = opportunity_record(
            tuple(row),
            columns,
            concept_label_lookup,
            glossary,
            display_refinement,
            representative_papers_lookup,
            editorial,
        )
        existing = records_by_pair.get(record["pair_key"])
        if existing is None or safe_number_for_sort(record["score"]) > safe_number_for_sort(existing["score"]):
            records_by_pair[record["pair_key"]] = record
    return [records_by_pair[pair_key] for pair_key in requested if pair_key in records_by_pair]


def compute_centrality(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> tuple[pd.DataFrame, nx.DiGraph]:
    graph = nx.DiGraph()
    for row in nodes_df.itertuples(index=False):
        graph.add_node(row.concept_id)
    for row in edges_df.itertuples(index=False):
        graph.add_edge(
            row.source_concept_id,
            row.target_concept_id,
            weight=float(row.support_count),
            distinct_papers=int(row.distinct_papers),
            avg_stability=float(row.avg_stability),
        )
    pagerank = nx.pagerank(graph, weight="weight")
    metrics: list[dict[str, Any]] = []
    for concept_id in graph.nodes:
        in_support = float(graph.in_degree(concept_id, weight="weight"))
        out_support = float(graph.out_degree(concept_id, weight="weight"))
        metrics.append(
            {
                "concept_id": concept_id,
                "in_degree": int(graph.in_degree(concept_id)),
                "out_degree": int(graph.out_degree(concept_id)),
                "weighted_in_degree": in_support,
                "weighted_out_degree": out_support,
                "weighted_degree": in_support + out_support,
                "pagerank": float(pagerank.get(concept_id, 0.0)),
                "neighbor_count": len(set(graph.predecessors(concept_id)) | set(graph.successors(concept_id))),
            }
        )
    metrics_df = pd.DataFrame(metrics)
    metrics_df.sort_values(["weighted_degree", "pagerank"], ascending=[False, False], inplace=True)
    return metrics_df, graph


def scale_positions(raw_positions: dict[str, tuple[float, float]], spread: float = 1.0) -> dict[str, dict[str, float]]:
    xs = [float(pos[0]) for pos in raw_positions.values()]
    ys = [float(pos[1]) for pos in raw_positions.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = max(x_max - x_min, 1e-9)
    y_span = max(y_max - y_min, 1e-9)
    scaled: dict[str, dict[str, float]] = {}
    for node, (x, y) in raw_positions.items():
        x_norm = (float(x) - x_min) / x_span
        y_norm = (float(y) - y_min) / y_span
        scaled[node] = {
            "x": round(0.5 + ((x_norm - 0.5) * spread), 6),
            "y": round(0.5 + ((y_norm - 0.5) * spread), 6),
        }
    return scaled


def node_bucket_group(bucket_hint: str | None) -> str:
    value = (bucket_hint or "").lower()
    if "core" in value and "adjacent" not in value and "mixed" not in value:
        return "core"
    if "adjacent" in value and "core" not in value and "mixed" not in value:
        return "adjacent"
    return "mixed"


def build_backbone(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    node_metrics_df: pd.DataFrame,
    edge_profiles_df: pd.DataFrame,
    edge_contexts_df: pd.DataFrame,
    edge_exemplars_df: pd.DataFrame,
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    top_node_ids = set(node_metrics_df.head(BACKBONE_NODE_LIMIT)["concept_id"])
    edges_subset = edges_df[
        edges_df["source_concept_id"].isin(top_node_ids) & edges_df["target_concept_id"].isin(top_node_ids)
    ].copy()
    edges_subset = edges_subset[edges_subset["support_count"] >= BACKBONE_MIN_SUPPORT].copy()
    edges_subset.sort_values(["support_count", "distinct_papers"], ascending=[False, False], inplace=True)
    edges_subset = edges_subset.head(BACKBONE_EDGE_LIMIT)

    undirected = nx.Graph()
    for row in edges_subset.itertuples(index=False):
        undirected.add_edge(row.source_concept_id, row.target_concept_id, weight=float(row.support_count))
    if undirected.number_of_nodes() == 0:
        return {"nodes": [], "edges": []}, []
    component_nodes = max(nx.connected_components(undirected), key=len)
    component_edges = edges_subset[
        edges_subset["source_concept_id"].isin(component_nodes) & edges_subset["target_concept_id"].isin(component_nodes)
    ].copy()
    layout_graph = undirected.subgraph(component_nodes).copy()
    layout_k = BACKBONE_LAYOUT_K_MULTIPLIER / math.sqrt(max(layout_graph.number_of_nodes(), 1))
    positions_raw = nx.spring_layout(
        layout_graph,
        seed=7,
        weight="weight",
        iterations=BACKBONE_LAYOUT_ITERATIONS,
        k=layout_k,
    )
    positions = scale_positions(positions_raw, spread=BACKBONE_LAYOUT_SPREAD)

    node_details = nodes_df.set_index("concept_id").to_dict("index")
    central_metrics = node_metrics_df.set_index("concept_id").to_dict("index")
    edge_profiles = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_profiles_df.itertuples(index=False)
    }
    edge_contexts = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_contexts_df.itertuples(index=False)
    }
    edge_exemplars_map: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in edge_exemplars_df.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        if len(edge_exemplars_map[key]) >= 3:
            continue
        edge_exemplars_map[key].append(
            {
                "title": row.title,
                "year": row.year,
                "bucket": row.bucket,
                "evidence_text": row.evidence_text,
            }
        )

    label_nodes = set(node_metrics_df[node_metrics_df["concept_id"].isin(component_nodes)].head(BACKBONE_LABEL_LIMIT)["concept_id"])

    backbone_nodes: list[dict[str, Any]] = []
    for concept_id in component_nodes:
        detail = node_details.get(concept_id, {})
        metrics = central_metrics.get(concept_id, {})
        pos = positions.get(concept_id, {"x": 0.5, "y": 0.5})
        aliases = uniq_keep_order(parse_json_list(detail.get("aliases_json")), limit=8)
        public_label = public_label_payload(concept_id, detail.get("preferred_label", concept_id), glossary, display_refinement)
        backbone_nodes.append(
            {
                "id": concept_id,
                "label": detail.get("preferred_label", concept_id),
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "display_concept_id": public_label["display_concept_id"],
                "display_refined": public_label["display_refined"],
                "display_refinement_confidence": public_label["display_refinement_confidence"],
                "alternate_display_labels": public_label["alternate_display_labels"],
                "aliases": aliases,
                "alias_count": len(parse_json_list(detail.get("aliases_json"))),
                "bucket_hint": detail.get("bucket_hint", "unknown"),
                "instance_support": int(detail.get("instance_support", 0) or 0),
                "distinct_paper_support": int(detail.get("distinct_paper_support", 0) or 0),
                "top_countries": top_values(detail.get("top_countries"), limit=3),
                "top_units": top_values(detail.get("top_units"), limit=3),
                "x": pos["x"],
                "y": pos["y"],
                "weighted_degree": round(float(metrics.get("weighted_degree", 0.0)), 4),
                "pagerank": round(float(metrics.get("pagerank", 0.0)), 8),
                "in_degree": int(metrics.get("in_degree", 0) or 0),
                "out_degree": int(metrics.get("out_degree", 0) or 0),
                "neighbor_count": int(metrics.get("neighbor_count", 0) or 0),
                "bucket_group": node_bucket_group(detail.get("bucket_hint", "unknown")),
                "show_label": concept_id in label_nodes,
            }
        )

    backbone_edges: list[dict[str, Any]] = []
    for row in component_edges.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        profile = edge_profiles.get(key)
        context = edge_contexts.get(key)
        backbone_edges.append(
            {
                "id": f"{row.source_concept_id}__{row.target_concept_id}",
                "source": row.source_concept_id,
                "target": row.target_concept_id,
                "support_count": int(row.support_count),
                "distinct_papers": int(row.distinct_papers),
                "avg_stability": round(float(row.avg_stability), 4),
                "strength": round(min(1.0, 0.22 + math.log1p(float(row.support_count)) / 3.4), 4),
                "directionality_mix": parse_json_list(getattr(profile, "directionality_json", "[]")) if profile else [],
                "relationship_type_mix": parse_json_list(getattr(profile, "relationship_type_json", "[]")) if profile else [],
                "edge_role_mix": parse_json_list(getattr(profile, "edge_role_json", "[]")) if profile else [],
                "dominant_countries": top_values(getattr(context, "dominant_countries_json", "[]"), limit=3) if context else [],
                "dominant_units": top_values(getattr(context, "dominant_units_json", "[]"), limit=3) if context else [],
                "dominant_years": parse_json_list(getattr(context, "dominant_years_json", "[]")) if context else [],
                "examples": edge_exemplars_map.get(key, []),
            }
        )

    backbone_nodes.sort(key=lambda row: row["weighted_degree"], reverse=True)
    backbone_edges.sort(key=lambda row: row["support_count"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "nodes": len(backbone_nodes),
            "edges": len(backbone_edges),
        },
        "nodes": backbone_nodes,
        "edges": backbone_edges,
    }, backbone_nodes


def build_neighborhoods(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    edge_profiles_df: pd.DataFrame,
    edge_contexts_df: pd.DataFrame,
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    node_label_map = nodes_df.set_index("concept_id")["preferred_label"].to_dict()
    edge_profile_map = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_profiles_df.itertuples(index=False)
    }
    edge_context_map = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_contexts_df.itertuples(index=False)
    }
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges_df.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        profile = edge_profile_map.get(key)
        context = edge_context_map.get(key)
        payload = {
            "concept_id": row.target_concept_id,
            "label": public_label_payload(
                row.target_concept_id,
                node_label_map.get(row.target_concept_id, row.target_concept_id),
                glossary,
                display_refinement,
            )["plain_label"],
            "support_count": int(row.support_count),
            "distinct_papers": int(row.distinct_papers),
            "avg_stability": round(float(row.avg_stability), 4),
            "directionality_mix": parse_json_list(getattr(profile, "directionality_json", "[]")) if profile else [],
            "relationship_type_mix": parse_json_list(getattr(profile, "relationship_type_json", "[]")) if profile else [],
            "edge_role_mix": parse_json_list(getattr(profile, "edge_role_json", "[]")) if profile else [],
            "dominant_countries": top_values(getattr(context, "dominant_countries_json", "[]"), limit=3) if context else [],
        }
        outgoing[row.source_concept_id].append(payload)
        incoming[row.target_concept_id].append(
            {
                **payload,
                "concept_id": row.source_concept_id,
                "label": public_label_payload(
                    row.source_concept_id,
                    node_label_map.get(row.source_concept_id, row.source_concept_id),
                    glossary,
                    display_refinement,
                )["plain_label"],
            }
        )

    neighborhoods: dict[str, Any] = {}
    for concept_id in node_label_map:
        out_list = sorted(outgoing.get(concept_id, []), key=lambda item: item["support_count"], reverse=True)[:NEIGHBOR_LIMIT]
        in_list = sorted(incoming.get(concept_id, []), key=lambda item: item["support_count"], reverse=True)[:NEIGHBOR_LIMIT]
        combined = sorted(out_list + in_list, key=lambda item: item["support_count"], reverse=True)
        top_neighbors: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in combined:
            if item["concept_id"] in seen:
                continue
            seen.add(item["concept_id"])
            top_neighbors.append(item)
            if len(top_neighbors) >= NEIGHBOR_LIMIT:
                break
        neighborhoods[concept_id] = {
            "incoming": in_list,
            "outgoing": out_list,
            "top_neighbors": top_neighbors,
        }
    return neighborhoods


def build_concept_opportunities(
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    columns = list(candidates_df.columns)
    concept_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in candidates_df.itertuples(index=False):
        record = opportunity_record(
            tuple(row),
            columns,
            concept_label_lookup,
            glossary,
            display_refinement,
            representative_papers_lookup,
            editorial,
        )
        for concept_id in (row.u, row.v):
            existing = concept_map[concept_id].get(record["pair_key"])
            if existing is None or safe_number_for_sort(record["score"]) > safe_number_for_sort(existing["score"]):
                concept_map[concept_id][record["pair_key"]] = record
    out: dict[str, list[dict[str, Any]]] = {}
    for concept_id, pair_rows in concept_map.items():
        rows = list(pair_rows.values())
        rows.sort(key=lambda item: item["score"], reverse=True)
        out[concept_id] = rows[:CONCEPT_OPPORTUNITY_LIMIT]
    return out


def safe_number_for_sort(value: Any) -> float:
    numeric = to_float(value, 0.0)
    return numeric if math.isfinite(numeric) else 0.0


def build_search_index(
    nodes_df: pd.DataFrame,
    node_metrics_df: pd.DataFrame,
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    metrics_map = node_metrics_df.set_index("concept_id").to_dict("index")
    records: list[dict[str, Any]] = []
    for row in nodes_df.itertuples(index=False):
        metrics = metrics_map.get(row.concept_id, {})
        aliases = uniq_keep_order(parse_json_list(row.aliases_json), limit=12)
        search_terms = uniq_keep_order(
            [
                str(row.preferred_label).lower(),
                public_label_payload(row.concept_id, row.preferred_label, glossary, display_refinement)["plain_label"].lower(),
            ]
            + [alias.lower() for alias in aliases],
            limit=20,
        )
        public_label = public_label_payload(row.concept_id, row.preferred_label, glossary, display_refinement)
        records.append(
            {
                "concept_id": row.concept_id,
                "label": row.preferred_label,
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "display_concept_id": public_label["display_concept_id"],
                "display_refined": public_label["display_refined"],
                "display_refinement_confidence": public_label["display_refinement_confidence"],
                "alternate_display_labels": public_label["alternate_display_labels"],
                "aliases": aliases,
                "bucket_hint": row.bucket_hint,
                "instance_support": int(row.instance_support),
                "distinct_paper_support": int(row.distinct_paper_support),
                "weighted_degree": round(float(metrics.get("weighted_degree", 0.0)), 4),
                "pagerank": round(float(metrics.get("pagerank", 0.0)), 8),
                "in_degree": int(metrics.get("in_degree", 0) or 0),
                "out_degree": int(metrics.get("out_degree", 0) or 0),
                "neighbor_count": int(metrics.get("neighbor_count", 0) or 0),
                "top_countries": top_values(getattr(row, "top_countries", None), limit=3),
                "top_units": top_values(getattr(row, "top_units", None), limit=3),
                "search_terms": search_terms,
                "app_link": build_app_concept_link(row.concept_id),
            }
        )
    records.sort(key=lambda item: (item["weighted_degree"], item["instance_support"]), reverse=True)
    return records


def diversify_featured_opportunities(
    slices: dict[str, list[dict[str, Any]]], limit: int = FEATURED_OPPORTUNITY_LIMIT
) -> list[dict[str, Any]]:
    ordered_keys = ["bridges", "frontier", "fast_follow", "underexplored", "overall"]
    homepage_labels = {
        "bridges": "Connect separate literatures",
        "frontier": "Missing direct link",
        "fast_follow": "Ready to follow through",
        "underexplored": "Early but promising",
    }
    featured: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_slice_limits = {"overall": 4, "bridges": 2, "frontier": 2, "fast_follow": 2, "underexplored": 2}
    slice_counts: dict[str, int] = defaultdict(int)
    label_counts: dict[str, int] = defaultdict(int)
    climate_cap = max(1, limit // 6)
    climate_count = 0

    for slice_key in ordered_keys:
        for item in slices.get(slice_key, []):
            if item["pair_key"] in seen:
                continue
            if slice_counts[slice_key] >= per_slice_limits.get(slice_key, 2):
                break
            featured_item = {
                **item,
                "slice_label": homepage_labels.get(slice_key, item["slice_label"]),
            }
            if label_counts[featured_item["slice_label"]] >= 2:
                continue
            if is_climate_heavy(featured_item) and climate_count >= climate_cap:
                continue
            featured.append(featured_item)
            seen.add(featured_item["pair_key"])
            slice_counts[slice_key] += 1
            label_counts[featured_item["slice_label"]] += 1
            if is_climate_heavy(featured_item):
                climate_count += 1
            if len(featured) >= limit:
                return featured[:limit]

    for item in slices.get("overall", []):
        if item["pair_key"] in seen:
            continue
        if label_counts[item["slice_label"]] >= 2:
            continue
        if is_climate_heavy(item) and climate_count >= climate_cap:
            continue
        featured.append(item)
        seen.add(item["pair_key"])
        label_counts[item["slice_label"]] += 1
        if is_climate_heavy(item):
            climate_count += 1
        if len(featured) >= limit:
            break

    for item in slices.get("overall", []):
        if item["pair_key"] in seen:
            continue
        if is_climate_heavy(item) and climate_count >= climate_cap:
            continue
        featured.append(item)
        seen.add(item["pair_key"])
        if is_climate_heavy(item):
            climate_count += 1
        if len(featured) >= limit:
            break
    return featured[:limit]


def load_editorial_opportunities() -> dict[str, dict[str, Any]]:
    payload = read_json(EDITORIAL_OPPORTUNITIES_PATH)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("editorial-opportunities.json must be a non-empty object keyed by pair_key")

    editorial: dict[str, dict[str, Any]] = {}
    for pair_key, item in payload.items():
        if not isinstance(item, dict):
            raise ValueError(f"Editorial entry for {pair_key} must be an object")
        entry = {**item}
        entry.setdefault("pair_key", pair_key)
        if entry["pair_key"] != pair_key:
            raise ValueError(f"Editorial entry {pair_key} must keep pair_key in sync with its object key")
        missing = [field for field in EDITORIAL_REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"Editorial entry {pair_key} is missing required fields: {', '.join(missing)}")
        entry["field_shelves"] = [clean_public_text(value) for value in entry.get("field_shelves", []) if clean_public_text(value)]
        entry["collection_tags"] = [clean_public_text(value) for value in entry.get("collection_tags", []) if clean_public_text(value)]
        editorial[pair_key] = entry
    return editorial


def load_questions_carousel_assignments() -> dict[str, list[dict[str, Any]]]:
    payload = read_json(QUESTIONS_CAROUSEL_ASSIGNMENTS_PATH)
    if not isinstance(payload, dict):
        raise ValueError("questions-carousel-assignments.json must be an object")

    def normalize_groups(section_key: str, expected_count: int) -> list[dict[str, Any]]:
        groups = payload.get(section_key)
        if not isinstance(groups, list) or len(groups) != expected_count:
            raise ValueError(f"{section_key} must contain exactly {expected_count} groups")
        normalized_groups: list[dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError(f"{section_key} entries must be objects")
            slug = clean_public_text(group.get("slug"))
            title = clean_public_text(group.get("title"))
            items = group.get("items")
            if not slug or not title:
                raise ValueError(f"{section_key} groups must include slug and title")
            if not isinstance(items, list) or len(items) != CAROUSEL_GROUP_SIZE:
                raise ValueError(f"{section_key}.{slug} must contain exactly {CAROUSEL_GROUP_SIZE} items")
            normalized_items: list[dict[str, Any]] = []
            seen_in_group: set[str] = set()
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"{section_key}.{slug} items must be objects")
                missing = [field for field in QUESTION_CAROUSEL_ASSIGNMENT_ITEM_FIELDS if field not in item]
                if missing:
                    raise ValueError(
                        f"{section_key}.{slug} item is missing required fields: {', '.join(missing)}"
                    )
                pair_key = clean_public_text(item.get("pair_key"))
                if not pair_key:
                    raise ValueError(f"{section_key}.{slug} item must include pair_key")
                if pair_key in seen_in_group:
                    raise ValueError(f"{section_key}.{slug} repeats pair_key {pair_key}")
                seen_in_group.add(pair_key)
                normalized_items.append(
                    {
                        "pair_key": pair_key,
                        "display_title": clean_public_text(item.get("display_title")),
                        "display_why": clean_public_text(item.get("display_why")),
                        "display_first_step": clean_public_text(item.get("display_first_step")),
                        "display_category": clean_public_text(item.get("display_category")),
                    }
                )
            normalized_groups.append(
                {
                    "slug": slug,
                    "title": title,
                    "items": normalized_items,
                }
            )
        return normalized_groups

    normalized = {
        "field_carousels": normalize_groups("field_carousels", FIELD_CAROUSEL_COUNT),
        "use_case_carousels": normalize_groups("use_case_carousels", USE_CASE_CAROUSEL_COUNT),
    }
    seen_pairs: set[str] = set()
    duplicates: set[str] = set()
    for group in normalized["field_carousels"] + normalized["use_case_carousels"]:
        for item in group["items"]:
            pair_key = item["pair_key"]
            if pair_key in seen_pairs:
                duplicates.add(pair_key)
            seen_pairs.add(pair_key)
    if duplicates:
        raise ValueError(
            "questions-carousel-assignments.json must keep pair_keys globally unique: "
            + ", ".join(sorted(duplicates))
        )
    return normalized


def load_public_label_glossary(valid_concept_ids: set[str]) -> dict[str, dict[str, Any]]:
    payload = read_json(PUBLIC_LABEL_GLOSSARY_PATH)
    if not isinstance(payload, dict):
        raise ValueError("public-label-glossary.json must be an object keyed by concept_id")

    glossary: dict[str, dict[str, Any]] = {}
    for concept_id, item in payload.items():
        if not isinstance(item, dict):
            raise ValueError(f"Public label glossary entry for {concept_id} must be an object")
        entry = {**item}
        entry.setdefault("concept_id", concept_id)
        if entry["concept_id"] != concept_id:
            raise ValueError(f"Public label glossary entry {concept_id} must keep concept_id in sync with its object key")
        missing = [field for field in PUBLIC_LABEL_GLOSSARY_REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"Public label glossary entry {concept_id} is missing required fields: {', '.join(missing)}")
        if concept_id not in valid_concept_ids:
            raise ValueError(f"Public label glossary concept_id {concept_id} is not present in the public concept index")
        glossary[concept_id] = {
            "concept_id": concept_id,
            "plain_label": clean_public_text(entry.get("plain_label")),
            "subtitle": clean_public_text(entry.get("subtitle")),
        }
    return glossary


def build_editorial_records(
    editorial: dict[str, dict[str, Any]],
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    available_pair_keys = {str(value) for value in candidates_df["pair_key"].tolist()}
    missing_pairs = [pair_key for pair_key in editorial if pair_key not in available_pair_keys]
    if missing_pairs:
        raise ValueError(
            "Curated editorial pair_keys are missing from the exported opportunity set: "
            + ", ".join(missing_pairs)
        )

    subset_df = candidates_df[candidates_df["pair_key"].isin(editorial.keys())].copy()
    columns = list(subset_df.columns)
    records_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in subset_df.itertuples(index=False, name=None):
        record = opportunity_record(
            tuple(row),
            columns,
            concept_label_lookup,
            glossary,
            display_refinement,
            representative_papers_lookup,
            editorial,
        )
        records_by_pair[record["pair_key"]].append(record)

    curated_rows: list[dict[str, Any]] = []
    for pair_key, entry in sorted(editorial.items(), key=lambda item: int(item[1]["display_order"])):
        candidates = records_by_pair.get(pair_key, [])
        if not candidates:
            raise ValueError(f"Curated editorial pair_key {pair_key} could not be resolved to an opportunity record")
        base_record = candidates[0]
        curated_rows.append({**base_record, **entry})
    return curated_rows


def build_editorial_groups(
    curated_rows: list[dict[str, Any]],
    definitions: list[dict[str, str]],
    tag_field: str,
) -> list[dict[str, Any]]:
    rows_by_pair = {row["pair_key"]: row for row in curated_rows}
    groups: list[dict[str, Any]] = []
    pair_counts: dict[str, int] = defaultdict(int)
    for definition in definitions:
        slug = definition["slug"]
        items = [row for row in curated_rows if slug in row.get(tag_field, [])]
        if len(items) != 3:
            raise ValueError(f"{tag_field} group {slug} must contain exactly 3 editorial questions")
        groups.append(
            {
                "slug": slug,
                "title": definition["title"],
                "caption": definition["caption"],
                "items": items,
            }
        )
        if tag_field == "field_shelves":
            for row in items:
                pair_counts[row["pair_key"]] += 1

    if tag_field == "field_shelves":
        repeated = [pair_key for pair_key, count in pair_counts.items() if count > 2]
        if repeated:
            raise ValueError(
                "Field shelves may show the same question at most twice: " + ", ".join(sorted(repeated))
            )
    return groups


def auto_question_title(public_pair_label: Any) -> str:
    label = clean_public_text(public_pair_label)
    if not label:
        return "Open question"
    return label[:1].upper() + label[1:]


def normalized_endpoint_family(label: Any) -> str:
    normalized = normalized_label_key(label)
    if not normalized:
        return ""
    if any(token in normalized for token in ("co2 emissions", "carbon emissions", "carbon dioxide")):
        return "family:carbon-emissions"
    if any(
        token in normalized
        for token in (
            "green total factor productivity",
            "total factor productivity",
            "firm total factor productivity",
        )
    ):
        return "family:tfp"
    if any(token in normalized for token in ("green credit", "green finance", "digital inclusive finance")):
        return "family:green-finance-channel"
    if "low carbon city" in normalized:
        return "family:low-carbon-city"
    if any(token in normalized for token in ("ecological carrying capacity", "load capacity factor")):
        return "family:ecology-capacity"
    return ""


def row_endpoint_families(row: dict[str, Any]) -> list[str]:
    return uniq_keep_order(
        [
            normalized_endpoint_family(row.get("source_display_label") or row.get("source_label")),
            normalized_endpoint_family(row.get("target_display_label") or row.get("target_label")),
        ]
    )


def ranked_endpoint_key(label: Any) -> str:
    family = normalized_endpoint_family(label)
    if family:
        return family
    return normalized_label_key(label)


def row_ranked_endpoint_keys(row: dict[str, Any]) -> list[str]:
    return uniq_keep_order(
        [
            ranked_endpoint_key(row.get("source_display_label") or row.get("source_label")),
            ranked_endpoint_key(row.get("target_display_label") or row.get("target_label")),
        ]
    )


def generated_ranked_question_title(row: dict[str, Any]) -> str:
    source = clean_public_text(row.get("source_display_label") or row.get("source_label"))
    target = clean_public_text(row.get("target_display_label") or row.get("target_label"))
    if not source or not target:
        return ""
    return f"How might {source} change {target}?"


def display_category(row: dict[str, Any]) -> str:
    if bool(row.get("cross_field")) and to_int(row.get("cooc_count", 0)) == 0:
        return "Cross-area question"
    if to_int(row.get("cooc_count", 0)) == 0:
        return "Little direct work"
    if bool(row.get("cross_field")):
        return "Cross-area evidence"
    return "Nearby evidence"


def decorate_carousel_record(
    row: dict[str, Any],
    editorial: dict[str, dict[str, Any]],
    assignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    editorial_entry = editorial.get(clean_public_text(row.get("pair_key")), {})
    assignment_entry = assignment or {}
    custom_title = clean_public_text(assignment_entry.get("display_title")) or clean_public_text(
        editorial_entry.get("question_title")
    )
    custom_why = clean_public_text(assignment_entry.get("display_why")) or clean_public_text(
        editorial_entry.get("short_why")
    )
    custom_first_step = clean_public_text(assignment_entry.get("display_first_step")) or clean_public_text(
        editorial_entry.get("first_next_step")
    )
    custom_category = clean_public_text(assignment_entry.get("display_category"))
    editorial_strength = clean_public_text(editorial_entry.get("editorial_strength"))
    return {
        **row,
        "display_title": custom_title or auto_question_title(row.get("public_pair_label")),
        "display_why": custom_why or short_path_line(row),
        "display_first_step": custom_first_step or generated_first_step(row),
        "display_category": custom_category
        or editorial_strength.replace("-", " ").title()
        or display_category(row),
    }


def row_match_text(row: dict[str, Any]) -> str:
    return " ".join(
        normalized_label_key(value)
        for value in (
            row.get("source_label"),
            row.get("target_label"),
            row.get("public_pair_label"),
            row.get("question_family"),
            row.get("why_now"),
        )
        if clean_public_text(value)
    )


CLIMATE_HEAVY_TOKENS = (
    "climate",
    "carbon",
    "co2",
    "emissions",
    "pollution",
    "environment",
    "environmental quality",
    "environmental pollution",
    "ecological carrying capacity",
    "energy consumption",
    "energy demand",
    "energy use",
    "energy",
    "renewable energy",
    "ecological",
    "load capacity",
    "mineral rents",
    "oil",
    "gas",
    "electricity",
)

CAROUSEL_BLOCKLIST_FAMILIES = {
    "covid-19-pandemic-net-interest-margin",
    "education-inequality",
    "green-finance-life-expectancy",
    "gross-domestic-product-industrialization",
    "high-tech-industry-export-product-quality",
    "individual-forecasts-long-term-interest-rate",
    "us-stock-market-volatility-spillovers",
    "volatility-spillovers-us-stock-market",
    "wage-setting-costs",
}


def climate_signal_count(row: dict[str, Any]) -> int:
    haystack = row_match_text(row)
    return sum(token in haystack for token in CLIMATE_HEAVY_TOKENS)


def is_climate_heavy(row: dict[str, Any]) -> bool:
    return climate_signal_count(row) >= 1


def row_matches_tokens(row: dict[str, Any], tokens: list[str]) -> bool:
    haystack = row_match_text(row)
    return any(normalized_label_key(token) in haystack for token in tokens)


def family_key(row: dict[str, Any]) -> str:
    return clean_public_text(row.get("question_family")) or clean_public_text(row.get("pair_key"))


def endpoint_signature(row: dict[str, Any]) -> tuple[str, str]:
    left = normalized_label_key(row.get("source_display_label") or row.get("source_label"))
    right = normalized_label_key(row.get("target_display_label") or row.get("target_label"))
    return tuple(sorted([left, right]))


def row_has_direct_title_overlap(row: dict[str, Any]) -> bool:
    source_label = clean_public_text(row.get("source_display_label") or row.get("source_label"))
    target_label = clean_public_text(row.get("target_display_label") or row.get("target_label"))
    source_phrase = normalized_label_key(source_label)
    target_phrase = normalized_label_key(target_label)
    source_tokens = set(significant_tokens(source_label))
    target_tokens = set(significant_tokens(target_label))
    if not source_tokens or not target_tokens:
        return False

    for paper in row.get("representative_papers", []):
        title = normalized_label_key(paper.get("title"))
        title_tokens = set(title.split())
        source_hit = (source_phrase and source_phrase in title) or bool(source_tokens & title_tokens)
        target_hit = (target_phrase and target_phrase in title) or bool(target_tokens & title_tokens)
        if source_hit and target_hit:
            return True
    return False


def row_looks_like_duplicate_family(candidate: dict[str, Any], existing_rows: list[dict[str, Any]]) -> bool:
    candidate_family = family_key(candidate)
    candidate_signature = endpoint_signature(candidate)
    candidate_tokens = set(
        significant_tokens(
            candidate.get("source_display_label") or candidate.get("source_label"),
            candidate.get("target_display_label") or candidate.get("target_label"),
        )
    )
    for existing in existing_rows:
        if family_key(existing) == candidate_family:
            return True
        if endpoint_signature(existing) == candidate_signature:
            return True
        existing_tokens = set(
            significant_tokens(
                existing.get("source_display_label") or existing.get("source_label"),
                existing.get("target_display_label") or existing.get("target_label"),
            )
        )
        if len(candidate_tokens & existing_tokens) >= 3:
            return True
    return False


def strict_autofill_candidate(
    row: dict[str, Any],
    existing_rows: list[dict[str, Any]],
    *,
    allow_climate: bool,
) -> bool:
    if family_key(row) in CAROUSEL_BLOCKLIST_FAMILIES:
        return False
    if to_int(row.get("supporting_path_count", 0)) < 5:
        return False
    if to_int(row.get("mediator_count", 0)) < 3:
        return False
    if to_float(row.get("public_specificity_score", 0.0)) < 4.0:
        return False
    if not allow_climate and is_climate_heavy(row):
        return False
    if row_has_direct_title_overlap(row):
        return False
    if row_looks_like_duplicate_family(row, existing_rows):
        return False
    return True


def append_unique_records(
    target: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    editorial: dict[str, dict[str, Any]],
    limit: int,
    family_cap: int = 2,
    climate_cap: int | None = None,
) -> list[dict[str, Any]]:
    seen_pairs = {clean_public_text(item.get("pair_key")) for item in target}
    family_counts: dict[str, int] = defaultdict(int)
    climate_count = 0
    for item in target:
        family_counts[family_key(item)] += 1
        if is_climate_heavy(item):
            climate_count += 1

    for row in rows:
        pair_key = clean_public_text(row.get("pair_key"))
        if not pair_key or pair_key in seen_pairs:
            continue
        key = family_key(row)
        if family_counts[key] >= family_cap:
            continue
        if climate_cap is not None and is_climate_heavy(row) and climate_count >= climate_cap:
            continue
        target.append(decorate_carousel_record(row, editorial))
        seen_pairs.add(pair_key)
        family_counts[key] += 1
        if is_climate_heavy(row):
            climate_count += 1
        if len(target) >= limit:
            break
    return target


def append_strict_autofill_records(
    target: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    editorial: dict[str, dict[str, Any]],
    max_additions: int,
    allow_climate: bool,
) -> list[dict[str, Any]]:
    additions = 0
    seen_pairs = {clean_public_text(item.get("pair_key")) for item in target}
    for row in rows:
        pair_key = clean_public_text(row.get("pair_key"))
        if not pair_key or pair_key in seen_pairs:
            continue
        if not strict_autofill_candidate(row, target, allow_climate=allow_climate):
            continue
        target.append(decorate_carousel_record(row, editorial))
        seen_pairs.add(pair_key)
        additions += 1
        if additions >= max_additions:
            break
    return target


def build_field_carousels(
    overall_rows: list[dict[str, Any]],
    curated_rows: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    editorial: dict[str, dict[str, Any]],
    limit: int = FIELD_CAROUSEL_LIMIT,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for definition in definitions:
        slug = definition["slug"]
        anchors = sorted(
            [row for row in curated_rows if slug in row.get("field_shelves", [])],
            key=lambda row: (is_climate_heavy(row), public_window_penalty(row)),
        )
        matches = sorted(
            [row for row in overall_rows if row_matches_tokens(row, definition.get("match_tokens", []))],
            key=lambda row: (is_climate_heavy(row), public_window_penalty(row)),
        )
        items = append_unique_records(
            [],
            anchors[:CAROUSEL_ANCHOR_COUNT],
            editorial=editorial,
            limit=min(limit, CAROUSEL_ANCHOR_COUNT),
            climate_cap=None,
        )
        items = append_strict_autofill_records(
            items,
            matches,
            editorial=editorial,
            max_additions=CAROUSEL_MAX_ADDITIONS,
            allow_climate=slug == "climate-energy",
        )
        groups.append(
            {
                "slug": slug,
                "title": definition["title"],
                "caption": definition["caption"],
                "items": items[:limit],
            }
        )
    return groups


def build_use_case_carousels(
    overall_rows: list[dict[str, Any]],
    curated_rows: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    editorial: dict[str, dict[str, Any]],
    limit: int = USE_CASE_CAROUSEL_LIMIT,
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []

    for definition in definitions:
        slug = definition["slug"]
        anchors = sorted(
            [row for row in curated_rows if slug in row.get("collection_tags", [])],
            key=lambda row: (is_climate_heavy(row), public_window_penalty(row)),
        )
        if slug == "strong-nearby-evidence":
            matches = sorted(
                overall_rows,
                key=lambda row: (
                    is_climate_heavy(row),
                    -to_float(row.get("path_support_norm"), 0.0),
                    -to_int(row.get("supporting_path_count", 0)),
                    public_window_penalty(row),
                ),
            )
        elif slug == "phd-topic":
            matches = sorted(
                overall_rows,
                key=lambda row: (
                    is_climate_heavy(row),
                    -to_int(row.get("mediator_count", 0)),
                    -to_int(row.get("supporting_path_count", 0)),
                    public_window_penalty(row),
                ),
            )
        else:
            matches = sorted(
                [row for row in overall_rows if to_int(row.get("cooc_count", 0)) == 0],
                key=lambda row: (is_climate_heavy(row), public_window_penalty(row)),
            )

        items = append_unique_records(
            [],
            anchors[:CAROUSEL_ANCHOR_COUNT],
            editorial=editorial,
            limit=min(limit, CAROUSEL_ANCHOR_COUNT),
            climate_cap=None,
        )
        items = append_strict_autofill_records(
            items,
            matches,
            editorial=editorial,
            max_additions=CAROUSEL_MAX_ADDITIONS,
            allow_climate=False,
        )
        groups.append(
            {
                "slug": slug,
                "title": definition["title"],
                "caption": definition["caption"],
                "items": items[:limit],
            }
        )
    return groups


def build_curated_questions_carousels(
    assignments: dict[str, list[dict[str, Any]]],
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    display_refinement: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
    editorial: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pair_keys = [
        item["pair_key"]
        for group in assignments["field_carousels"] + assignments["use_case_carousels"]
        for item in group["items"]
    ]
    available_pair_keys = {str(value) for value in candidates_df["pair_key"].tolist()}
    missing_pairs = [pair_key for pair_key in pair_keys if pair_key not in available_pair_keys]
    if missing_pairs:
        raise ValueError(
            "Carousel pair_keys are missing from the exported opportunity set: "
            + ", ".join(sorted(missing_pairs))
        )

    subset_df = candidates_df[candidates_df["pair_key"].isin(pair_keys)].copy()
    columns = list(subset_df.columns)
    record_by_pair: dict[str, dict[str, Any]] = {}
    for row in subset_df.itertuples(index=False, name=None):
        record = opportunity_record(
            tuple(row),
            columns,
            concept_label_lookup,
            glossary,
            display_refinement,
            representative_papers_lookup,
            editorial,
        )
        existing = record_by_pair.get(record["pair_key"])
        if existing is None or safe_number_for_sort(record["score"]) > safe_number_for_sort(existing["score"]):
            record_by_pair[record["pair_key"]] = record

    def render_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rendered: list[dict[str, Any]] = []
        for group in groups:
            items: list[dict[str, Any]] = []
            for assignment in group["items"]:
                pair_key = assignment["pair_key"]
                base = record_by_pair.get(pair_key)
                if base is None:
                    raise ValueError(f"Missing resolved carousel record for {pair_key}")
                items.append(decorate_carousel_record(base, editorial, assignment))
            rendered.append(
                {
                    "slug": group["slug"],
                    "title": group["title"],
                    "caption": "",
                    "items": items,
                }
            )
        return rendered

    field_groups = render_groups(assignments["field_carousels"])
    use_case_groups = render_groups(assignments["use_case_carousels"])

    endpoint_family_counts: dict[str, int] = defaultdict(int)
    for group in field_groups + use_case_groups:
        for item in group["items"]:
            for family in row_endpoint_families(item):
                endpoint_family_counts[family] += 1

    repeated_families = {
        family: count
        for family, count in endpoint_family_counts.items()
        if family and count > CURATED_ENDPOINT_FAMILY_CAP
    }
    if repeated_families:
        repeated_text = ", ".join(f"{family}={count}" for family, count in sorted(repeated_families.items()))
        raise ValueError(
            "questions-carousel-assignments.json exceeds the curated endpoint-family cap: " + repeated_text
        )

    return field_groups, use_case_groups


def build_public_ranked_window(
    overall_rows: list[dict[str, Any]],
    excluded_pair_keys: set[str],
    editorial_fallback_rows: list[dict[str, Any]] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    exploratory_tail: list[dict[str, Any]] = []
    family_counts: dict[str, int] = defaultdict(int)
    endpoint_family_counts: dict[str, int] = defaultdict(int)
    climate_cap = max(6, RANKED_EDITORIAL_WINDOW_LIMIT // 6)
    climate_count = 0
    editorial_window_limit = min(limit, RANKED_EDITORIAL_WINDOW_LIMIT)
    diverse_head_limit = min(editorial_window_limit, RANKED_DIVERSE_HEAD_LIMIT)
    ranked_rows = sorted(
        [row for row in overall_rows if row["pair_key"] not in excluded_pair_keys],
        key=lambda row: (is_climate_heavy(row), public_window_penalty(row)),
    )

    prepared_rows: list[dict[str, Any]] = []
    for row in ranked_rows:
        prepared_rows.append(
            {
                **row,
                "display_question_title": clean_public_text(row.get("editorial_question_title"))
                or generated_ranked_question_title(row),
            }
        )

    ready_rows = [row for row in prepared_rows if ranked_window_ready(row)]
    selected_pair_keys: set[str] = set()
    source_counts: dict[str, int] = defaultdict(int)
    target_counts: dict[str, int] = defaultdict(int)

    for row in ready_rows:
        if len(visible) >= diverse_head_limit:
            break
        family = clean_public_text(row.get("question_family")) or row["pair_key"]
        endpoint_families = row_endpoint_families(row)
        source_key = ranked_endpoint_key(row.get("source_display_label") or row.get("source_label"))
        target_key = ranked_endpoint_key(row.get("target_display_label") or row.get("target_label"))
        if family_counts[family] >= 1:
            continue
        if any(endpoint_family_counts[endpoint_family] >= RANKED_ENDPOINT_FAMILY_CAP for endpoint_family in endpoint_families):
            continue
        if source_key and source_counts[source_key] >= RANKED_DIVERSE_ENDPOINT_REPEAT_CAP:
            continue
        if target_key and target_counts[target_key] >= RANKED_DIVERSE_ENDPOINT_REPEAT_CAP:
            continue
        if is_climate_heavy(row) and climate_count >= climate_cap:
            continue
        visible.append(row)
        selected_pair_keys.add(row["pair_key"])
        family_counts[family] += 1
        for endpoint_family in endpoint_families:
            endpoint_family_counts[endpoint_family] += 1
        if source_key:
            source_counts[source_key] += 1
        if target_key:
            target_counts[target_key] += 1
        if is_climate_heavy(row):
            climate_count += 1

    for row in editorial_fallback_rows or []:
        if len(visible) >= editorial_window_limit:
            break
        if row["pair_key"] in excluded_pair_keys or row["pair_key"] in selected_pair_keys:
            continue
        candidate = {
            **row,
            "display_question_title": clean_public_text(row.get("editorial_question_title"))
            or generated_ranked_question_title(row),
        }
        if ranked_window_title_is_weak(candidate):
            continue
        family = clean_public_text(candidate.get("question_family")) or candidate["pair_key"]
        endpoint_families = row_endpoint_families(candidate)
        if family_counts[family] >= 1:
            continue
        if any(endpoint_family_counts[endpoint_family] >= RANKED_ENDPOINT_FAMILY_CAP for endpoint_family in endpoint_families):
            continue
        if is_climate_heavy(candidate) and climate_count >= climate_cap:
            continue
        visible.append(candidate)
        selected_pair_keys.add(candidate["pair_key"])
        family_counts[family] += 1
        for endpoint_family in endpoint_families:
            endpoint_family_counts[endpoint_family] += 1
        if is_climate_heavy(candidate):
            climate_count += 1

    for row in ready_rows:
        if len(visible) >= editorial_window_limit:
            break
        if row["pair_key"] in selected_pair_keys:
            continue
        family = clean_public_text(row.get("question_family")) or row["pair_key"]
        endpoint_families = row_endpoint_families(row)
        if family_counts[family] >= 1:
            continue
        if any(endpoint_family_counts[endpoint_family] >= RANKED_ENDPOINT_FAMILY_CAP for endpoint_family in endpoint_families):
            continue
        if is_climate_heavy(row) and climate_count >= climate_cap:
            continue
        visible.append(row)
        selected_pair_keys.add(row["pair_key"])
        family_counts[family] += 1
        for endpoint_family in endpoint_families:
            endpoint_family_counts[endpoint_family] += 1
        if is_climate_heavy(row):
            climate_count += 1

    exploratory_tail.extend([row for row in ready_rows if row["pair_key"] not in selected_pair_keys])
    exploratory_tail.extend(
        [row for row in prepared_rows if row["pair_key"] not in selected_pair_keys and not ranked_window_ready(row)]
    )

    for row in exploratory_tail:
        if row["pair_key"] in selected_pair_keys:
            continue
        visible.append(row)
        selected_pair_keys.add(row["pair_key"])
        if len(visible) >= limit:
            break
    return visible[:limit]


def write_json(path: Path, payload: Any) -> None:
    def sanitize(value: Any) -> Any:
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(sanitize(payload), handle, indent=2)


def copy_public_download(source: Path, target_filename: str) -> str:
    if not source.exists():
        raise FileNotFoundError(f"Required public download asset is missing: {source}")
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = PUBLIC_DOWNLOADS_DIR / target_filename
    shutil.copy2(source, target_path)
    return f"/downloads/{target_filename}"


def write_public_download_text(target_filename: str, content: str) -> str:
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = PUBLIC_DOWNLOADS_DIR / target_filename
    target_path.write_text(content, encoding="utf-8")
    return f"/downloads/{target_filename}"


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def public_path_to_local(public_path: str) -> Path:
    cleaned = public_path.lstrip("/")
    return SITE_ROOT / "public" / cleaned


def build_download_file_entry(public_path: str) -> dict[str, Any]:
    local_path = public_path_to_local(public_path)
    if not local_path.exists():
        raise FileNotFoundError(f"Expected public asset is missing: {local_path}")
    return {
        "path": public_path,
        "filename": local_path.name,
        "size_bytes": local_path.stat().st_size,
    }


def write_zip_bundle(target_filename: str, entries: list[tuple[Path, str]]) -> dict[str, Any]:
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = PUBLIC_DOWNLOADS_DIR / target_filename
    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for source_path, archive_name in entries:
            if not source_path.exists():
                raise FileNotFoundError(f"Bundle source asset is missing: {source_path}")
            bundle.write(source_path, archive_name)
    return {
        "path": f"/downloads/{target_filename}",
        "filename": target_filename,
        "size_bytes": target_path.stat().st_size,
    }


def bundle_entries_for_directory(directory: Path, archive_prefix: str) -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        entries.append((path, f"{archive_prefix}/{path.relative_to(directory).as_posix()}"))
    return entries


def write_public_db_release_assets(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"Required public database bundle is missing: {db_path}")
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    size_bytes = db_path.stat().st_size
    sha256 = sha256_file(db_path)
    manifest = {
        "filename": DB_FILENAME,
        "db_size_bytes": size_bytes,
        "db_size_gb": round(size_bytes / (1024**3), 2),
        "sha256": sha256,
        "public_url": PUBLIC_DB_URL,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.manifest.json", manifest)
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-public.sha256.txt").write_text(
        f"{sha256}  {DB_FILENAME}\n"
    )
    return manifest


def build_release_readme_markdown(metrics: dict[str, Any], app_url: str) -> str:
    return f"""# Frontier Graph public release README

Frontier Graph is a public browser for suggested research questions in economics. This release starts from {metrics["papers"]:,} papers screened from 1976 to 2026 and packages the public question tables, graph assets, and SQLite bundle that sit behind the site.

## Start here

- If you want a spreadsheet-friendly entry point, start with `top_questions.csv`.
- If you want topic search and summary statistics, add `central_concepts.csv`.
- If you want the same JSON and shard files the public site uses, download Tier 2.
- If you want the full local evidence tables in one file, download `frontiergraph-economics-public.db`.

## Stable identifiers

- `pair_key`: stable public identifier for a research question or concept pair
- `concept_id`: stable public identifier for a topic in the public concept layer

## Which tier should I use?

- **Tier 1: lightweight exports**. Use these if you want spreadsheet-friendly question tables, shortlist reviews, or quick concept summaries.
- **Tier 2: structured graph assets**. Use these if you want the same literature map, concept index, neighborhoods, opportunity shards, and slice files the public site uses.
- **Tier 3: SQLite bundle**. Use this if you want the full local evidence tables in one file for Python, R, or DB Browser for SQLite.

## What each file is for

- `top_questions.csv`: one row per suggested question, with display labels, nearby support, path counts, starter papers, and explorer link.
- `central_concepts.csv`: one row per central topic, with baseline labels, display labels, and graph prominence measures.
- `curated_questions.json`: the hand-curated site questions shown in featured shelves.
- `hybrid_corpus_manifest.json`: release counts for the broader benchmark corpus.
- `graph_backbone.json`: the lightweight literature map used on the public site.
- `concept_index.json`: searchable concept records with aliases, support, and app links.
- `concept_neighborhoods_index.json`: index into the concept-neighborhood shard files.
- `concept_opportunities_index.json`: index into the concept-opportunity shard files.
- `opportunity_slices.json`: grouped question slices used for the public question page.
- `frontiergraph-economics-public.db`: the full public SQLite bundle.

## How to read the release

- Suggested questions are surfaced because nearby topics and papers already imply short local routes between the two sides.
- Topic links in the graph are ordered topic-to-topic relations extracted from titles and abstracts. They help organize the literature, but they are not final causal judgments.
- CSV files are the easiest entry point for spreadsheets and quick scripts.
- Several CSV columns store lists as JSON strings so the same fields can survive spreadsheet export.
- The SQLite bundle is the most complete public package. It includes question-level tables such as `question_mediators`, `question_paths`, and `question_papers`, plus both baseline and public display labels.

## Public surfaces

- Site: https://frontiergraph.com
- Explorer: {app_url}
- Repository: {REPO_URL}
"""


def build_data_dictionary_markdown() -> str:
    return """# Frontier Graph data dictionary

This guide summarizes the main fields in the public download files. If you want one row per suggested question, start with `top_questions.csv`. If you want the full local evidence tables, use the SQLite bundle.

## Shared identifiers

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public identifier for a released question, built from a normalized concept pair. |
| `concept_id` | Stable public identifier for a topic in the public concept layer. |

## `top_questions.csv`

| Field | Meaning |
| --- | --- |
| `pair_key` | Stable public question identifier. |
| `source_display_label`, `target_display_label` | Public-facing labels used by the site and app when a cleaner or narrower wording is available. |
| `display_refinement_confidence` | Confidence score for the public display refinement layer. |
| `source_id`, `target_id` | Concept IDs for the two ends of the question. |
| `source_label`, `target_label` | Baseline concept labels preserved for reproducibility. |
| `source_bucket`, `target_bucket` | Coarse location of each concept in the public graph. |
| `cross_field` | Whether the two concepts sit across different broad buckets. |
| `score` | Final public ranking score. |
| `base_score` | Pre-penalty score before duplicate downweighting. |
| `duplicate_penalty` | Downweight applied when many near-duplicate questions cluster together. |
| `path_support_norm` | Normalized support from nearby topic paths in the graph. |
| `gap_bonus` | Bonus for links that look underexplored relative to the local neighborhood. |
| `mediator_count` | Count of intermediate topics supporting the question. |
| `motif_count` | Count of repeated local patterns around the question. |
| `cooc_count` | Count of direct papers already observed in the public release. |
| `direct_link_status` | Reader-facing summary of direct-literature presence. |
| `supporting_path_count` | Count of supporting topic paths surfaced in the release. |
| `why_now` | Plain-language explanation of why the suggested question appears on the public surface. |
| `recommended_move` | Suggested first research move or reading strategy. |
| `slice_label` | Slice or family label used on the public site. |
| `public_pair_label` | Plain-language pair label. |
| `display_question_title` | Question-style title used on the ranked public questions page. |
| `question_family` | Family label used to avoid repetitive windows. |
| `suppress_from_public_ranked_window` | Whether the question is kept out of the default ranked window. |
| `top_mediator_labels` | JSON list of the most important intermediate topics in public display form. |
| `top_mediator_baseline_labels` | JSON list of the corresponding baseline mediator labels kept for reproducibility. |
| `representative_papers` | JSON list of starter papers attached to nearby paths and edges. |
| `top_countries_source`, `top_countries_target` | JSON lists of common settings for each side of the pair. |
| `source_context_summary`, `target_context_summary` | Short context summaries for each side. |
| `common_contexts` | Plain-language summary of overlapping settings. |
| `app_link` | Deep link into the public explorer. |

## `central_concepts.csv`

| Field | Meaning |
| --- | --- |
| `concept_id` | Stable concept identifier. |
| `label` | Baseline preferred concept label. |
| `plain_label` | Public display label used by the site and app. |
| `subtitle` | Public clarifier used where concept naming needs context. |
| `display_concept_id` | Concept ID for the display-layer refinement when one exists. |
| `display_refined` | Whether the public display label comes from the finer display layer. |
| `display_refinement_confidence` | Confidence score for the display-layer refinement. |
| `alternate_display_labels` | Alternate finer labels considered for the public surface. |
| `bucket_hint` | Coarse placement of the concept in the graph. |
| `instance_support` | Number of mapped node mentions assigned to the concept. |
| `distinct_paper_support` | Number of distinct papers touching the concept. |
| `weighted_degree` | Weighted graph degree in the normalized graph. |
| `pagerank` | PageRank-style prominence measure. |
| `in_degree`, `out_degree` | Directed degree counts in the graph tables. |
| `neighbor_count` | Number of distinct neighboring concepts. |
| `top_countries`, `top_units` | JSON lists of common settings and units. |
| `app_link` | Deep link into the public explorer. |

## Structured JSON assets

| File | Main object | What it contains |
| --- | --- | --- |
| `graph_backbone.json` | `nodes`, `edges` | The lightweight public literature map. |
| `concept_index.json` | concept records | Searchable concept lookup records with aliases and support. |
| `concept_neighborhoods_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to neighborhood shard file. |
| `concept_opportunities_index.json` | `{concept_id: shard_path}` | Lookup map from concept ID to concept-opportunity shard file. |
| `opportunity_slices.json` | slice arrays | Public question slices such as overall, cross-area, frontier, and fast-follow. |
| `curated_questions.json` | curated records | Hand-curated questions used in the public site surfaces. |

## SQLite bundle tables

| Table | Grain | Description |
| --- | --- | --- |
| `release_meta` | key-value | Release metadata and artifact paths. |
| `release_metrics` | key-value | Corpus and graph counts for the public release. |
| `top_questions` | one row per released top question | Lightweight question surface mirrored into SQLite. |
| `questions` | one row per released question | Full public question table. |
| `central_concepts` | one row per central concept | Central concept table mirrored from CSV. |
| `concept_index` | one row per concept | Searchable concept records with aliases and app links. |
| `graph_nodes`, `graph_edges` | one row per map node/edge | Lightweight public graph backbone. |
| `opportunity_slices` | one row per pair in a named slice | Slice membership plus JSON payload. |
| `concept_opportunities` | one row per concept-question pairing | Top nearby questions for each concept. |
| `concept_neighborhoods` | one row per concept-neighbor relation | Incoming, outgoing, and top-neighbor records. |
| `question_mediators` | one row per mediator within a question | Ranked mediator concepts for each question. |
| `question_paths` | one row per supporting path | Ranked supporting paths and labels. |
| `question_papers` | one row per paper within a path | Papers connected to a path. |
| `question_neighborhoods` | one row per question | Cached source/target neighborhood JSON. |
"""


def chunk_mapping(mapping: dict[str, Any], output_dir: Path, stem: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shard_index: dict[str, str] = {}
    items = list(mapping.items())
    for chunk_no in range(0, len(items), SHARD_SIZE):
        shard_items = items[chunk_no : chunk_no + SHARD_SIZE]
        shard_name = f"{stem}-{chunk_no // SHARD_SIZE:03d}.json"
        shard_path = output_dir / shard_name
        write_json(shard_path, {key: value for key, value in shard_items})
        for key, _value in shard_items:
            shard_index[key] = f"{PUBLIC_DATA_URL_PREFIX}/{output_dir.name}/{shard_name}"
    return shard_index


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(PAPER_SYNC_SCRIPT)], check=True)

    extraction_summary = read_json(EXTRACTION_SUMMARY_PATH)
    hybrid_manifest = read_json(HYBRID_CORPUS_MANIFEST_PATH)
    editorial_opportunities = load_editorial_opportunities()
    questions_carousel_assignments = load_questions_carousel_assignments()

    candidates_df = add_slice_flags(load_candidates())
    node_details_df = load_node_details()
    representative_papers_lookup = load_representative_papers()
    public_concept_ids = {str(value) for value in node_details_df["concept_id"].tolist()}
    public_label_glossary = load_public_label_glossary(public_concept_ids)
    display_refinement = load_display_refinement()
    concept_label_lookup = (
        node_details_df.set_index("concept_id")["preferred_label"].to_dict()
    )
    graph_edges_df, edge_profiles_df, edge_contexts_df, edge_exemplars_df = load_graph_tables()

    node_metrics_df, _graph = compute_centrality(node_details_df, graph_edges_df)
    backbone_payload, backbone_nodes = build_backbone(
        node_details_df,
        graph_edges_df,
        node_metrics_df,
        edge_profiles_df,
        edge_contexts_df,
        edge_exemplars_df,
        public_label_glossary,
        display_refinement,
    )
    neighborhoods = build_neighborhoods(
        node_details_df,
        graph_edges_df,
        edge_profiles_df,
        edge_contexts_df,
        public_label_glossary,
        display_refinement,
    )
    concept_opportunities = build_concept_opportunities(
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
        editorial_opportunities,
    )
    search_index = build_search_index(node_details_df, node_metrics_df, public_label_glossary, display_refinement)

    central_concepts_df = (
        node_details_df.merge(node_metrics_df, left_on="concept_id", right_on="concept_id", how="left")
        .sort_values(["weighted_degree", "pagerank"], ascending=[False, False])
        .reset_index(drop=True)
    )
    central_concepts_rows = []
    for row in central_concepts_df.head(200).itertuples(index=False):
        public_label = public_label_payload(row.concept_id, row.preferred_label, public_label_glossary, display_refinement)
        central_concepts_rows.append(
            {
                "concept_id": row.concept_id,
                "label": row.preferred_label,
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "display_concept_id": public_label["display_concept_id"],
                "display_refined": public_label["display_refined"],
                "display_refinement_confidence": public_label["display_refinement_confidence"],
                "alternate_display_labels": public_label["alternate_display_labels"],
                "bucket_hint": row.bucket_hint,
                "instance_support": int(row.instance_support),
                "distinct_paper_support": int(row.distinct_paper_support),
                "weighted_degree": round(float(row.weighted_degree), 4),
                "pagerank": round(float(row.pagerank), 8),
                "in_degree": int(row.in_degree),
                "out_degree": int(row.out_degree),
                "neighbor_count": int(row.neighbor_count),
                "top_countries": top_values(row.top_countries, limit=3),
                "top_units": top_values(row.top_units, limit=3),
                "app_link": build_app_concept_link(row.concept_id),
            }
        )

    slices = build_slices(
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
        editorial_opportunities,
    )
    ranked_source_rows = build_ranked_source_rows(
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
        editorial_opportunities,
        limit=PUBLIC_RANKED_SOURCE_LIMIT,
    )
    ranked_editorial_fallback_rows = build_specific_opportunity_rows(
        RANKED_EDITORIAL_FALLBACK_PAIR_KEYS,
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
        editorial_opportunities,
    )
    featured_opportunities = diversify_featured_opportunities(slices, limit=FEATURED_OPPORTUNITY_LIMIT)
    editorial_records = build_editorial_records(
        editorial_opportunities,
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
    )
    home_curated_questions = [row for row in editorial_records if bool(row["homepage_featured"])]
    curated_front_set = [row for row in editorial_records if bool(row["questions_featured"])]
    if editorial_records:
        home_roles = [str(row.get("homepage_role", "")) for row in home_curated_questions]
        if home_roles.count("lead") != 1 or home_roles.count("supporting") != 2:
            raise ValueError("Homepage curation must contain exactly one lead question and two supporting questions")
        if len(home_curated_questions) != 3:
            raise ValueError("Homepage curation must contain exactly 3 questions")
        if len(curated_front_set) != 6:
            raise ValueError("Questions front set must contain exactly 6 questions")
        field_shelves = build_editorial_groups(editorial_records, FIELD_SHELF_DEFS, "field_shelves")
        collections = build_editorial_groups(editorial_records, COLLECTION_DEFS, "collection_tags")
    else:
        field_shelves = []
        collections = []
    field_carousels, use_case_carousels = build_curated_questions_carousels(
        questions_carousel_assignments,
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        display_refinement,
        representative_papers_lookup,
        editorial_opportunities,
    )
    top_carousel_pair_keys = {
        item["pair_key"]
        for group in field_carousels + use_case_carousels
        for item in group["items"]
    }
    ranked_questions = build_public_ranked_window(
        ranked_source_rows,
        {row["pair_key"] for row in editorial_records} | top_carousel_pair_keys,
        editorial_fallback_rows=ranked_editorial_fallback_rows,
        limit=PUBLIC_RANKED_WINDOW_LIMIT,
    )

    write_json(PUBLIC_DATA_DIR / "graph_backbone.json", backbone_payload)
    write_json(PUBLIC_DATA_DIR / "concept_index.json", search_index)
    neighborhood_shard_index = chunk_mapping(neighborhoods, NEIGHBORHOOD_SHARDS_DIR, "neighborhoods")
    opportunity_shard_index = chunk_mapping(concept_opportunities, OPPORTUNITY_SHARDS_DIR, "opportunities")
    write_json(PUBLIC_DATA_DIR / "concept_neighborhoods_index.json", neighborhood_shard_index)
    write_json(PUBLIC_DATA_DIR / "concept_opportunities_index.json", opportunity_shard_index)
    write_json(PUBLIC_DATA_DIR / "opportunity_slices.json", slices)
    write_json(PUBLIC_DATA_DIR / "curated_questions.json", editorial_records)
    write_json(PUBLIC_DATA_DIR / "central_concepts.json", central_concepts_rows)
    write_json(PUBLIC_DATA_DIR / "hybrid_corpus_manifest.json", hybrid_manifest)
    export_rows_csv(
        PUBLIC_DATA_DIR / "central_concepts.csv",
        central_concepts_rows,
        [
            "concept_id",
            "label",
            "plain_label",
            "subtitle",
            "display_concept_id",
            "display_refined",
            "display_refinement_confidence",
            "alternate_display_labels",
            "bucket_hint",
            "instance_support",
            "distinct_paper_support",
            "weighted_degree",
            "pagerank",
            "in_degree",
            "out_degree",
            "neighbor_count",
            "top_countries",
            "top_units",
            "app_link",
        ],
    )
    export_rows_csv(
        PUBLIC_DATA_DIR / "top_questions.csv",
        slices["overall"],
        [
            "pair_key",
            "source_id",
            "target_id",
            "source_label",
            "target_label",
            "source_display_label",
            "target_display_label",
            "source_display_concept_id",
            "target_display_concept_id",
            "source_display_refined",
            "target_display_refined",
            "display_refinement_confidence",
            "source_alternate_display_labels",
            "target_alternate_display_labels",
            "source_bucket",
            "target_bucket",
            "cross_field",
            "score",
            "base_score",
            "duplicate_penalty",
            "path_support_norm",
            "gap_bonus",
            "mediator_count",
            "motif_count",
            "cooc_count",
            "direct_link_status",
            "supporting_path_count",
            "why_now",
            "recommended_move",
            "slice_label",
            "public_pair_label",
            "display_question_title",
            "question_family",
            "suppress_from_public_ranked_window",
            "top_mediator_labels",
            "top_mediator_display_labels",
            "top_mediator_baseline_labels",
            "representative_papers",
            "top_countries_source",
            "top_countries_target",
            "source_context_summary",
            "target_context_summary",
            "common_contexts",
            "public_specificity_score",
            "app_link",
        ],
    )

    working_paper_download = copy_public_download(WORKING_PAPER_PDF_PATH, "frontiergraph-working-paper.pdf")
    extended_abstract_download = copy_public_download(
        EXTENDED_ABSTRACT_PDF_PATH,
        "frontiergraph-extended-abstract.pdf",
    )
    db_manifest = write_public_db_release_assets(PUBLIC_RELEASE_DB_PATH)
    release_readme_path = write_public_download_text(
        "frontiergraph-release-readme.md",
        build_release_readme_markdown(
            {
                "papers": int(extraction_summary["records"]),
                "normalized_links": int(hybrid_manifest["normalized_hybrid_rows"]),
                "native_concepts": int(hybrid_manifest["unique_concepts_in_hybrid_corpus"]),
                "visible_public_questions": int(candidates_df["pair_key"].astype(str).nunique()) if "pair_key" in candidates_df.columns else int(len(candidates_df)),
            },
            PUBLIC_APP_URL,
        ),
    )
    data_dictionary_path = write_public_download_text(
        "frontiergraph-data-dictionary.md",
        build_data_dictionary_markdown(),
    )

    tier1_bundle = write_zip_bundle(
        "frontiergraph-tier1-lightweight-exports.zip",
        [
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/top_questions.csv"), "top_questions.csv"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/central_concepts.csv"), "central_concepts.csv"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/curated_questions.json"), "curated_questions.json"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/hybrid_corpus_manifest.json"), "hybrid_corpus_manifest.json"),
            (public_path_to_local(release_readme_path), "README.md"),
            (public_path_to_local(data_dictionary_path), "DATA_DICTIONARY.md"),
        ],
    )
    tier2_bundle = write_zip_bundle(
        "frontiergraph-tier2-structured-assets.zip",
        [
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/graph_backbone.json"), "graph_backbone.json"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/concept_index.json"), "concept_index.json"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/concept_neighborhoods_index.json"), "concept_neighborhoods_index.json"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/concept_opportunities_index.json"), "concept_opportunities_index.json"),
            (public_path_to_local(f"{PUBLIC_DATA_URL_PREFIX}/opportunity_slices.json"), "opportunity_slices.json"),
            (public_path_to_local(release_readme_path), "README.md"),
            (public_path_to_local(data_dictionary_path), "DATA_DICTIONARY.md"),
            *bundle_entries_for_directory(NEIGHBORHOOD_SHARDS_DIR, "concept_neighborhoods"),
            *bundle_entries_for_directory(OPPORTUNITY_SHARDS_DIR, "concept_opportunities"),
        ],
    )

    artifact_details = {
        "working_paper_pdf": build_download_file_entry(working_paper_download),
        "extended_abstract_pdf": build_download_file_entry(extended_abstract_download),
        "benchmark_manifest_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/hybrid_corpus_manifest.json"),
        "top_questions_csv": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/top_questions.csv"),
        "curated_questions_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/curated_questions.json"),
        "central_concepts_csv": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/central_concepts.csv"),
        "graph_backbone_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/graph_backbone.json"),
        "concept_index_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/concept_index.json"),
        "concept_neighborhoods_index_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/concept_neighborhoods_index.json"),
        "concept_opportunities_index_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/concept_opportunities_index.json"),
        "opportunity_slices_json": build_download_file_entry(f"{PUBLIC_DATA_URL_PREFIX}/opportunity_slices.json"),
        "manifest_json": build_download_file_entry("/downloads/frontiergraph-economics-public.manifest.json"),
        "checksum_txt": build_download_file_entry("/downloads/frontiergraph-economics-public.sha256.txt"),
    }

    site_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_url": PUBLIC_APP_URL,
        "repo_url": REPO_URL,
        "public_label_glossary": public_label_glossary,
        "metrics": {
            "papers": int(extraction_summary["records"]),
            "papers_with_extracted_edges": int(hybrid_manifest["papers_with_extracted_edges"]),
            "normalized_graph_papers": int(hybrid_manifest["normalized_benchmark_papers"]),
            "node_instances": int(extraction_summary["total_nodes"]),
            "edges": int(extraction_summary["total_edges"]),
            "normalized_links": int(hybrid_manifest["normalized_hybrid_rows"]),
            "normalized_directed_links": int(hybrid_manifest["normalized_directed_rows"]),
            "normalized_undirected_links": int(hybrid_manifest["normalized_undirected_rows"]),
            "native_concepts": int(hybrid_manifest["unique_concepts_in_hybrid_corpus"]),
            "visible_public_questions": int(candidates_df["pair_key"].astype(str).nunique()) if "pair_key" in candidates_df.columns else int(len(candidates_df)),
        },
        "home": {
            "featured_questions": featured_opportunities[:6],
            "curated_questions": home_curated_questions,
            "featured_central_concepts": central_concepts_rows[:8],
            "graph_snapshot": {
                "nodes": backbone_payload["counts"]["nodes"],
                "edges": backbone_payload["counts"]["edges"],
                "path": f"{PUBLIC_DATA_URL_PREFIX}/graph_backbone.json",
            },
        },
        "graph": {
            "backbone_path": f"{PUBLIC_DATA_URL_PREFIX}/graph_backbone.json",
            "concept_index_path": f"{PUBLIC_DATA_URL_PREFIX}/concept_index.json",
            "concept_neighborhoods_index_path": f"{PUBLIC_DATA_URL_PREFIX}/concept_neighborhoods_index.json",
            "concept_opportunities_index_path": f"{PUBLIC_DATA_URL_PREFIX}/concept_opportunities_index.json",
            "central_concepts_path": f"{PUBLIC_DATA_URL_PREFIX}/central_concepts.json",
        },
        "questions": {
            "slices_path": f"{PUBLIC_DATA_URL_PREFIX}/opportunity_slices.json",
            "concept_opportunities_index_path": f"{PUBLIC_DATA_URL_PREFIX}/concept_opportunities_index.json",
            "curated_front_set": curated_front_set,
            "field_shelves": field_shelves,
            "collections": collections,
            "field_carousels": field_carousels,
            "use_case_carousels": use_case_carousels,
            "ranked_questions": ranked_questions,
            "top_slices": {
                "overall": slices["overall"][:12],
                "bridges": slices["bridges"][:12],
                "frontier": slices["frontier"][:12],
                "fast_follow": slices["fast_follow"][:12],
                "underexplored": slices["underexplored"][:12],
            },
        },
        "downloads": {
            "public_db": {
                "filename": DB_FILENAME,
                "public_url": db_manifest["public_url"],
                "sha256": db_manifest["sha256"],
                "db_size_bytes": db_manifest["db_size_bytes"],
                "db_size_gb": db_manifest["db_size_gb"],
            },
            "checksum_path": "/downloads/frontiergraph-economics-public.sha256.txt",
            "manifest_path": "/downloads/frontiergraph-economics-public.manifest.json",
            "guides": {
                "readme": build_download_file_entry(release_readme_path),
                "data_dictionary": build_download_file_entry(data_dictionary_path),
            },
            "tier_bundles": {
                "tier1": tier1_bundle,
                "tier2": tier2_bundle,
            },
            "artifacts": {
                "working_paper_pdf": working_paper_download,
                "extended_abstract_pdf": extended_abstract_download,
                "benchmark_manifest_json": f"{PUBLIC_DATA_URL_PREFIX}/hybrid_corpus_manifest.json",
                "top_questions_csv": f"{PUBLIC_DATA_URL_PREFIX}/top_questions.csv",
                "curated_questions_json": f"{PUBLIC_DATA_URL_PREFIX}/curated_questions.json",
                "central_concepts_csv": f"{PUBLIC_DATA_URL_PREFIX}/central_concepts.csv",
                "graph_backbone_json": f"{PUBLIC_DATA_URL_PREFIX}/graph_backbone.json",
                "concept_index_json": f"{PUBLIC_DATA_URL_PREFIX}/concept_index.json",
                "concept_neighborhoods_index_json": f"{PUBLIC_DATA_URL_PREFIX}/concept_neighborhoods_index.json",
                "concept_opportunities_index_json": f"{PUBLIC_DATA_URL_PREFIX}/concept_opportunities_index.json",
                "opportunity_slices_json": f"{PUBLIC_DATA_URL_PREFIX}/opportunity_slices.json",
            },
            "artifact_details": artifact_details,
        },
    }
    write_json(GENERATED_SITE_DATA_PATH, site_data)


if __name__ == "__main__":
    main()
