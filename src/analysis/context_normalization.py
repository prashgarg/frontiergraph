from __future__ import annotations

import json
import re
from typing import Any


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


EXPLICIT_CONTEXT_MAP: dict[str, dict[str, str]] = {
    "china": {
        "normalized_display": "China",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::china",
        "status": "canonical",
    },
    "chn": {
        "normalized_display": "China",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::china",
        "status": "normalized_alias",
    },
    "india": {
        "normalized_display": "India",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::india",
        "status": "canonical",
    },
    "ind": {
        "normalized_display": "India",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::india",
        "status": "normalized_alias",
    },
    "united states": {
        "normalized_display": "United States",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::united_states",
        "status": "canonical",
    },
    "usa": {
        "normalized_display": "United States",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::united_states",
        "status": "normalized_alias",
    },
    "united kingdom": {
        "normalized_display": "United Kingdom",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::united_kingdom",
        "status": "canonical",
    },
    "uk": {
        "normalized_display": "United Kingdom",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::united_kingdom",
        "status": "normalized_alias",
    },
    "gbr": {
        "normalized_display": "United Kingdom",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::united_kingdom",
        "status": "normalized_alias",
    },
    "australia": {
        "normalized_display": "Australia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::australia",
        "status": "canonical",
    },
    "brazil": {
        "normalized_display": "Brazil",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::brazil",
        "status": "canonical",
    },
    "bra": {
        "normalized_display": "Brazil",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::brazil",
        "status": "normalized_alias",
    },
    "pakistan": {
        "normalized_display": "Pakistan",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::pakistan",
        "status": "canonical",
    },
    "mexico": {
        "normalized_display": "Mexico",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::mexico",
        "status": "canonical",
    },
    "italy": {
        "normalized_display": "Italy",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::italy",
        "status": "canonical",
    },
    "turkey": {
        "normalized_display": "Turkey",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::turkey",
        "status": "canonical",
    },
    "south africa": {
        "normalized_display": "South Africa",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::south_africa",
        "status": "canonical",
    },
    "zaf": {
        "normalized_display": "South Africa",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::south_africa",
        "status": "normalized_alias",
    },
    "canada": {
        "normalized_display": "Canada",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::canada",
        "status": "canonical",
    },
    "can": {
        "normalized_display": "Canada",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::canada",
        "status": "normalized_alias",
    },
    "japan": {
        "normalized_display": "Japan",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::japan",
        "status": "canonical",
    },
    "germany": {
        "normalized_display": "Germany",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::germany",
        "status": "canonical",
    },
    "deu": {
        "normalized_display": "Germany",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::germany",
        "status": "normalized_alias",
    },
    "france": {
        "normalized_display": "France",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::france",
        "status": "canonical",
    },
    "sweden": {
        "normalized_display": "Sweden",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::sweden",
        "status": "canonical",
    },
    "indonesia": {
        "normalized_display": "Indonesia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::indonesia",
        "status": "canonical",
    },
    "bangladesh": {
        "normalized_display": "Bangladesh",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::bangladesh",
        "status": "canonical",
    },
    "taiwan": {
        "normalized_display": "Taiwan",
        "context_type": "country_or_territory",
        "granularity": "country",
        "canonical_context_id": "country_or_territory::taiwan",
        "status": "canonical",
    },
    "netherlands": {
        "normalized_display": "Netherlands",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::netherlands",
        "status": "canonical",
    },
    "korea": {
        "normalized_display": "South Korea",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::south_korea",
        "status": "normalized_alias",
    },
    "south korea": {
        "normalized_display": "South Korea",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::south_korea",
        "status": "canonical",
    },
    "kor": {
        "normalized_display": "South Korea",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::south_korea",
        "status": "normalized_alias",
    },
    "ghana": {
        "normalized_display": "Ghana",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::ghana",
        "status": "canonical",
    },
    "nigeria": {
        "normalized_display": "Nigeria",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::nigeria",
        "status": "canonical",
    },
    "saudi arabia": {
        "normalized_display": "Saudi Arabia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::saudi_arabia",
        "status": "canonical",
    },
    "tunisia": {
        "normalized_display": "Tunisia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::tunisia",
        "status": "canonical",
    },
    "malaysia": {
        "normalized_display": "Malaysia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::malaysia",
        "status": "canonical",
    },
    "philippines": {
        "normalized_display": "Philippines",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::philippines",
        "status": "canonical",
    },
    "phl": {
        "normalized_display": "Philippines",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::philippines",
        "status": "normalized_alias",
    },
    "egypt": {
        "normalized_display": "Egypt",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::egypt",
        "status": "canonical",
    },
    "russia": {
        "normalized_display": "Russia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::russia",
        "status": "canonical",
    },
    "rus": {
        "normalized_display": "Russia",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::russia",
        "status": "normalized_alias",
    },
    "vietnam": {
        "normalized_display": "Vietnam",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::vietnam",
        "status": "canonical",
    },
    "côte d'ivoire": {
        "normalized_display": "Côte d'Ivoire",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::cote_divoire",
        "status": "canonical",
    },
    "senegal": {
        "normalized_display": "Senegal",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::senegal",
        "status": "canonical",
    },
    "malawi": {
        "normalized_display": "Malawi",
        "context_type": "country",
        "granularity": "country",
        "canonical_context_id": "country::malawi",
        "status": "canonical",
    },
    "european union": {
        "normalized_display": "European Union countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::european_union",
        "status": "canonical_bloc",
    },
    "eu": {
        "normalized_display": "European Union countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::european_union",
        "status": "normalized_alias",
    },
    "eu-15": {
        "normalized_display": "EU-15 countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::eu_15",
        "status": "canonical_bloc",
    },
    "oecd": {
        "normalized_display": "OECD countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::oecd",
        "status": "canonical_bloc",
    },
    "oecd members (38)": {
        "normalized_display": "OECD countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::oecd",
        "status": "normalized_alias",
    },
    "brics": {
        "normalized_display": "BRICS countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::brics",
        "status": "canonical_bloc",
    },
    "g7": {
        "normalized_display": "G7 countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::g7",
        "status": "canonical_bloc",
    },
    "g20": {
        "normalized_display": "G20 countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::g20",
        "status": "canonical_bloc",
    },
    "euro area": {
        "normalized_display": "Euro Area countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::euro_area",
        "status": "canonical_bloc",
    },
    "saarc countries": {
        "normalized_display": "SAARC countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::saarc",
        "status": "canonical_bloc",
    },
    "nato countries": {
        "normalized_display": "NATO countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::nato",
        "status": "canonical_bloc",
    },
    "belt and road initiative countries": {
        "normalized_display": "Belt and Road countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::belt_and_road",
        "status": "canonical_bloc",
    },
    "developing countries": {
        "normalized_display": "developing countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::developing_countries",
        "status": "canonical_bloc",
    },
    "central and eastern european countries": {
        "normalized_display": "Central and Eastern European countries",
        "context_type": "bloc",
        "granularity": "bloc",
        "canonical_context_id": "bloc::cee_countries",
        "status": "canonical_bloc",
    },
    "europe": {
        "normalized_display": "Europe",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::europe",
        "status": "canonical_region",
    },
    "africa": {
        "normalized_display": "Africa",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::africa",
        "status": "canonical_region",
    },
    "sub-saharan africa": {
        "normalized_display": "Sub-Saharan Africa",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::sub_saharan_africa",
        "status": "canonical_region",
    },
    "asia": {
        "normalized_display": "Asia",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::asia",
        "status": "canonical_region",
    },
    "latin america": {
        "normalized_display": "Latin America",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::latin_america",
        "status": "canonical_region",
    },
    "north america": {
        "normalized_display": "North America",
        "context_type": "region",
        "granularity": "region",
        "canonical_context_id": "region::north_america",
        "status": "canonical_region",
    },
    "na": {
        "normalized_display": "unknown context",
        "context_type": "unknown",
        "granularity": "unknown",
        "canonical_context_id": "unknown::na",
        "status": "ambiguous",
    },
    "jiangxi province": {
        "normalized_display": "Jiangxi Province",
        "context_type": "subnational_region",
        "granularity": "subnational",
        "canonical_context_id": "subnational::jiangxi_province",
        "status": "canonical_subnational",
    },
    "ten asian countries with significant pollution": {
        "normalized_display": "ten Asian countries with significant pollution",
        "context_type": "study_defined_group",
        "granularity": "group",
        "canonical_context_id": "group::ten_asian_countries_with_significant_pollution",
        "status": "study_defined_group",
    },
}


FALLBACK_REGION_PATTERNS = [
    (re.compile(r"\bcountries\b", flags=re.IGNORECASE), "bloc", "bloc"),
    (re.compile(r"\bprovince\b", flags=re.IGNORECASE), "subnational_region", "subnational"),
    (re.compile(r"\bregion\b", flags=re.IGNORECASE), "region", "region"),
]


def normalize_context_value(raw_value: Any) -> dict[str, str]:
    raw = _clean(raw_value)
    key = _norm(raw)
    if key in EXPLICIT_CONTEXT_MAP:
        payload = dict(EXPLICIT_CONTEXT_MAP[key])
        payload["raw_value"] = raw
        return payload
    if re.fullmatch(r"[A-Z]{3}", raw):
        return {
            "raw_value": raw,
            "normalized_display": raw,
            "context_type": "unknown",
            "granularity": "unknown",
            "canonical_context_id": f"unknown::{key}",
            "status": "unresolved_iso_like",
        }
    for pattern, context_type, granularity in FALLBACK_REGION_PATTERNS:
        if pattern.search(raw):
            slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_") or "unknown"
            return {
                "raw_value": raw,
                "normalized_display": raw,
                "context_type": context_type,
                "granularity": granularity,
                "canonical_context_id": f"{granularity}::{slug}",
                "status": "fallback_pattern",
            }
    slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_") or "unknown"
    return {
        "raw_value": raw,
        "normalized_display": raw,
        "context_type": "country_or_place",
        "granularity": "country",
        "canonical_context_id": f"country_or_place::{slug}",
        "status": "fallback_passthrough",
    }


def normalize_context_items(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    text = str(raw).strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = []
    out: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        for item in parsed:
            count = None
            if isinstance(item, dict):
                raw_value = item.get("value", "")
                count = item.get("count")
            else:
                raw_value = item
            normed = normalize_context_value(raw_value)
            if count is not None:
                normed["count"] = count
            out.append(normed)
    return out


def serialize_normalized_context_items(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def best_context_values(items: list[dict[str, Any]], allowed_granularities: set[str] | None = None, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    filtered = items
    if allowed_granularities is not None:
        filtered = [item for item in items if item.get("granularity") in allowed_granularities]
    sorted_items = sorted(filtered, key=lambda x: (-int(x.get("count", 0) or 0), x.get("normalized_display", "")))
    for item in sorted_items:
        key = str(item.get("canonical_context_id", "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        display = str(item.get("normalized_display", "")).strip()
        if display:
            out.append(display)
        if len(out) >= limit:
            break
    return out


def matched_context_sets(endpoint_items: list[dict[str, Any]], edge_items: list[dict[str, Any]]) -> tuple[set[str], set[str], str | None]:
    granularities = ["country", "subnational", "region", "bloc", "group", "global"]
    endpoint_by_gran = {
        gran: {str(item["canonical_context_id"]) for item in endpoint_items if item.get("granularity") == gran}
        for gran in granularities
    }
    edge_by_gran = {
        gran: {str(item["canonical_context_id"]) for item in edge_items if item.get("granularity") == gran}
        for gran in granularities
    }
    for gran in granularities:
        if endpoint_by_gran[gran] and edge_by_gran[gran]:
            return endpoint_by_gran[gran], edge_by_gran[gran], gran
    return set(), set(), None

