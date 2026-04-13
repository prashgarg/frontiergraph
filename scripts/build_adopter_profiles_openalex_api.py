from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import ensure_dir


DEFAULT_UPTAKE = ROOT / "outputs/paper/167_exploratory_testbeds/uptake_spine/historical_edge_uptake_deduped.parquet"
DEFAULT_BUNDLE_DIR = ROOT / "outputs/paper/167_exploratory_testbeds/bundle_uptake"
DEFAULT_OUT = ROOT / "outputs/paper/167_exploratory_testbeds/adopter_profiles"
DEFAULT_PAPER_META = ROOT / "data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet"
DEFAULT_AUTHORSHIPS = ROOT / "data/processed/research_allocation_v2/paper_authorships.parquet"
DEFAULT_DERIVED_DIR = ROOT / "data/processed/openalex/derived_testbeds"
DEFAULT_PUBLISHED_JOURNAL_CORPORA = ROOT / "data/processed/openalex/published_journal_corpora"
DEFAULT_KEY_FILES = [
    ROOT.parent / "key/openalex_key_prashantgargib2.txt",
    ROOT.parent / "key/openalex_key_prashantgargib1.txt",
    ROOT.parent / "key/openalex_key_prashant.txt",
]

HORIZON_ORDER = [5, 10, 15]
GENERAL_INTEREST_VENUES = {
    "american economic review",
    "quarterly journal of economics",
    "journal of political economy",
    "econometrica",
    "review of economic studies",
    "economic journal",
    "journal of the european economic association",
}
TOP5_VENUES = {
    "american economic review",
    "the quarterly journal of economics",
    "quarterly journal of economics",
    "journal of political economy",
    "econometrica",
    "the review of economic studies",
    "review of economic studies",
}
FIELD_VENUE_TOKENS = [
    "economic",
    "economics",
    "econometrica",
    "journal of labor",
    "journal of public",
    "journal of health economics",
    "journal of development economics",
    "journal of environmental economics",
    "journal of urban economics",
    "journal of monetary economics",
    "journal of financial economics",
    "review of economics",
]
ADJACENT_VENUE_TOKENS = [
    "science",
    "nature",
    "management",
    "sociology",
    "political science",
    "demography",
    "public policy",
    "epidemiology",
]
CENTRAL_BANK_TOKENS = [
    "federal reserve",
    "central bank",
    "bank of england",
    "bank for international settlements",
    "european central bank",
    "reserve bank",
    "monetary authority",
    "treasury",
    "ministry of finance",
    "world bank",
    "international monetary fund",
    "imf",
]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_openalex_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("https://openalex.org/"):
        return text.rsplit("/", 1)[-1]
    return text


def _full_openalex_url(value: str) -> str:
    norm = _normalize_openalex_id(value)
    return f"https://openalex.org/{norm}" if norm else ""


def _safe_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _write_tex_table(df: pd.DataFrame, out_path: Path, index: bool = False) -> None:
    safe = df.copy()
    safe.columns = [str(col).replace("_", r"\_") for col in safe.columns]
    for col in safe.columns:
        if safe[col].dtype == object:
            safe[col] = safe[col].astype(str).str.replace("_", r"\_", regex=False)
    tex = safe.to_latex(index=index, escape=False)
    out_path.write_text(tex, encoding="utf-8")


def _funder_bucket(n: Any) -> str:
    n = int(pd.to_numeric(n, errors="coerce") or 0)
    if n <= 0:
        return "none"
    if n == 1:
        return "one"
    return "two_plus"


def _venue_bucket(venue: str) -> str:
    norm = _normalize_text(venue)
    if norm in GENERAL_INTEREST_VENUES:
        return "general_interest"
    if any(tok in norm for tok in FIELD_VENUE_TOKENS):
        return "field"
    if any(tok in norm for tok in ADJACENT_VENUE_TOKENS):
        return "adjacent_interdisciplinary"
    return "other"


def _clean_institution_type(value: Any, names: list[str] | None = None) -> str:
    norm = _normalize_text(value)
    names_norm = " ".join(_normalize_text(x) for x in (names or []))
    if norm in {"", "nan"}:
        return "missing"
    if any(tok in names_norm for tok in CENTRAL_BANK_TOKENS):
        return "government_central_bank"
    if norm == "education":
        return "university"
    if norm == "government":
        return "government"
    if norm == "company":
        return "company"
    if norm == "healthcare":
        return "healthcare"
    if norm == "nonprofit":
        return "nonprofit"
    if norm == "funder":
        return "funder_org"
    if norm == "facility":
        return "research_facility"
    if norm in {"archive", "museum", "library"}:
        return "cultural_archive"
    if not norm:
        return "missing"
    if norm == "other":
        return "other"
    return norm


def _topic_cluster(primary_topic: str, title: str = "") -> str:
    text = f"{_normalize_text(primary_topic)} {_normalize_text(title)}"
    if any(tok in text for tok in ["health", "medical", "hospital", "patient", "quality of life"]):
        return "health"
    if any(tok in text for tok in ["energy", "climate", "environment", "ecological", "carbon"]):
        return "energy_environment"
    if any(tok in text for tok in ["financial", "bank", "banking", "asset pricing", "volatility", "credit", "housing market"]):
        return "finance_banking"
    if any(tok in text for tok in ["monetary", "fiscal", "business cycle", "productivity", "inflation", "macroeconomic", "growth"]):
        return "macro_policy_growth"
    if any(tok in text for tok in ["labor", "wage", "unemployment", "employment", "human resources"]):
        return "labor"
    if any(tok in text for tok in ["trade", "development", "innovation", "poverty", "global"]):
        return "trade_development_innovation"
    if any(tok in text for tok in ["theor", "equilibrium", "mechanism", "econometric", "identification", "model"]):
        return "theory_methods"
    return "other"


def _paper_type_bucket(primary_topic: str, title: str = "") -> str:
    cluster = _topic_cluster(primary_topic, title)
    mapping = {
        "health": "health_policy_or_health_econ",
        "energy_environment": "energy_environment",
        "finance_banking": "finance_banking_housing",
        "macro_policy_growth": "macro_monetary_fiscal_growth",
        "labor": "labor_public_human_capital",
        "trade_development_innovation": "trade_development_innovation",
        "theory_methods": "theory_or_methods",
        "other": "other",
    }
    return mapping.get(cluster, "other")


def _venue_cluster(venue: str) -> str:
    norm = _normalize_text(venue)
    if norm in {"american economic review", "econometrica", "the review of economic studies", "review of economic studies", "journal of economic theory", "journal of economic dynamics and control", "european economic review", "the review of economics and statistics", "journal of international economics", "journal of economic behavior & organization", "economic modelling", "the journal of human resources"}:
        return "core_econ_theory_macro"
    if norm in {"journal of banking & finance", "the journal of finance", "international review of economics & finance"}:
        return "finance_banking"
    if norm in {"health affairs", "health economics", "journal of health economics", "medical care", "social science & medicine", "jama", "health policy", "health and quality of life outcomes", "pharmacoeconomics"}:
        return "health_policy"
    if norm in {"sustainability", "energy policy", "energy economics", "journal of cleaner production", "renewable and sustainable energy reviews", "ecological economics"}:
        return "energy_environment"
    if norm in {"world development", "journal of development economics", "research policy", "economics of innovation and new technology", "structural change and economic dynamics"}:
        return "development_growth"
    return "other"


def _mode_nonempty(values: pd.Series) -> str:
    ser = pd.Series(values).replace("", np.nan).dropna()
    if ser.empty:
        return ""
    mode = ser.mode()
    return str(mode.iloc[0]) if not mode.empty else str(ser.iloc[0])


def _p_display(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "p<0.001"
    return f"p={p:.3f}"


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _comparison_rows(df: pd.DataFrame, metrics: list[tuple[str, str, str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for horizon in sorted(df["horizon"].dropna().unique()):
        block = df[df["horizon"] == horizon].copy()
        left = block[block["candidate_family_mode"] == "path_to_direct"].copy()
        right = block[block["candidate_family_mode"] == "direct_to_path"].copy()
        for metric, label, kind in metrics:
            x = pd.to_numeric(left[metric], errors="coerce").dropna()
            y = pd.to_numeric(right[metric], errors="coerce").dropna()
            if x.empty or y.empty:
                continue
            mx = float(x.mean())
            my = float(y.mean())
            diff = mx - my
            if kind == "binary":
                vx = mx * (1 - mx)
                vy = my * (1 - my)
            else:
                vx = float(x.var(ddof=1)) if len(x) > 1 else 0.0
                vy = float(y.var(ddof=1)) if len(y) > 1 else 0.0
            se = math.sqrt((vx / len(x)) + (vy / len(y))) if len(x) and len(y) else float("nan")
            z = diff / se if se and se > 0 else float("nan")
            p = 2 * (1 - _normal_cdf(abs(z))) if np.isfinite(z) else float("nan")
            ci_low = diff - 1.96 * se if np.isfinite(se) else float("nan")
            ci_high = diff + 1.96 * se if np.isfinite(se) else float("nan")
            rows.append(
                {
                    "horizon": int(horizon),
                    "metric": metric,
                    "label": label,
                    "path_to_direct_mean": mx,
                    "direct_to_path_mean": my,
                    "difference_path_minus_direct": diff,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "n_path_to_direct": int(len(x)),
                    "n_direct_to_path": int(len(y)),
                    "p_value": p,
                    "p_display": _p_display(p),
                }
            )
    return pd.DataFrame(rows)


def _load_corpus_venue_sets(base_dir: Path) -> tuple[set[str], set[str]]:
    core_names: set[str] = set()
    adjacent_names: set[str] = set()
    files = [
        (base_dir / "published_core_econ.jsonl.gz", core_names),
        (base_dir / "published_adjacent_econ_relevant.jsonl.gz", adjacent_names),
    ]
    for path, target in files:
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                src = ((obj.get("primary_location") or {}).get("source") or {})
                name = src.get("display_name") or src.get("raw_source_name") or ""
                name = str(name).strip()
                if name:
                    target.add(name)
    return core_names, adjacent_names


def _load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    uptake = pd.read_parquet(Path(args.uptake))
    bundle = pd.read_parquet(Path(args.bundle_dir) / "bundle_uptake_paper_level.parquet")
    paper_meta = pd.read_parquet(
        Path(args.paper_meta),
        columns=[
            "paper_id",
            "year",
            "title",
            "authors",
            "venue",
            "primary_subfield_display_name",
            "unique_funder_count",
            "first_funder",
        ],
    )
    authorships = pd.read_parquet(Path(args.authorships))
    for col in ["paper_id", "work_id", "author_id", "institution_id"]:
        if col in authorships.columns:
            authorships[col] = authorships[col].fillna("").astype(str)
    paper_meta["paper_id"] = paper_meta["paper_id"].astype(str)
    uptake["realizing_paper_id"] = uptake["realizing_paper_id"].astype(str)
    uptake["realizing_work_id"] = uptake["realizing_work_id"].astype(str).map(_full_openalex_url)
    if "realizing_work_id" in bundle.columns:
        bundle["realizing_work_id"] = bundle["realizing_work_id"].astype(str).map(_full_openalex_url)
    if "work_id" in authorships.columns:
        authorships["work_id"] = authorships["work_id"].astype(str).map(_full_openalex_url)
    return uptake, bundle, paper_meta, authorships


def _build_focal_authorships(uptake: pd.DataFrame, paper_meta: pd.DataFrame, authorships: pd.DataFrame) -> pd.DataFrame:
    focal_papers = (
        uptake[
            [
                "realizing_paper_id",
                "realizing_work_id",
                "realizing_paper_year",
                "realizing_primary_subfield_display_name",
            ]
        ]
        .drop_duplicates()
        .copy()
    )
    focal = focal_papers.merge(
        authorships.rename(columns={"paper_id": "realizing_paper_id"}),
        on="realizing_paper_id",
        how="left",
    )
    focal = focal[focal["author_id"].astype(str) != ""].copy()
    paper_meta_local = paper_meta[["paper_id", "year", "primary_subfield_display_name"]].rename(
        columns={
            "paper_id": "history_paper_id",
            "year": "history_year",
            "primary_subfield_display_name": "history_subfield",
        }
    )
    author_history = authorships.rename(columns={"paper_id": "history_paper_id"}).merge(
        paper_meta_local,
        on="history_paper_id",
        how="left",
    )
    author_history = author_history[author_history["author_id"].astype(str) != ""].copy()
    return focal, author_history


def _compute_local_author_metrics(focal: pd.DataFrame, author_history: pd.DataFrame) -> pd.DataFrame:
    author_history["history_year"] = pd.to_numeric(author_history["history_year"], errors="coerce")
    by_author = {
        str(author_id): grp.sort_values("history_year").copy()
        for author_id, grp in author_history.groupby("author_id", sort=False)
    }
    rows: list[dict[str, Any]] = []
    for row in focal.itertuples(index=False):
        author_id = str(row.author_id)
        hist = by_author.get(author_id)
        focal_year = int(row.realizing_paper_year)
        if hist is None or hist.empty:
            rows.append(
                {
                    "realizing_paper_id": str(row.realizing_paper_id),
                    "realizing_work_id": str(row.realizing_work_id),
                    "author_id": author_id,
                    "career_age_local": np.nan,
                    "prior_works_local": np.nan,
                    "prior_same_subfield_local": np.nan,
                    "prior_distinct_subfields_local": np.nan,
                "prior_focal_subfield_share_local": np.nan,
                "entrant_local": np.nan,
                    "incumbent_local": np.nan,
                    "specialist_author_local": np.nan,
                    "bridge_author_local": np.nan,
                    "outsider_author_local": np.nan,
                }
            )
            continue
        prior = hist[pd.to_numeric(hist["history_year"], errors="coerce") < focal_year].copy()
        prior_works = int(len(prior))
        prior_same = int(prior["history_subfield"].fillna("").astype(str).eq(str(row.realizing_primary_subfield_display_name or "")).sum())
        prior_distinct = int(prior["history_subfield"].fillna("").astype(str).replace("", np.nan).dropna().nunique())
        earliest_year = pd.to_numeric(hist["history_year"], errors="coerce").dropna()
        earliest = float(earliest_year.min()) if not earliest_year.empty else np.nan
        prior_share = float(prior_same / prior_works) if prior_works > 0 else np.nan
        rows.append(
            {
                "realizing_paper_id": str(row.realizing_paper_id),
                "realizing_work_id": str(row.realizing_work_id),
                "author_id": author_id,
                "career_age_local": float(focal_year - earliest) if np.isfinite(earliest) else np.nan,
                "prior_works_local": float(prior_works),
                "prior_same_subfield_local": float(prior_same),
                "prior_distinct_subfields_local": float(prior_distinct),
                "prior_focal_subfield_share_local": prior_share,
                "entrant_local": float(prior_same == 0) if prior_works >= 0 else np.nan,
                "incumbent_local": float(prior_same > 0) if prior_works >= 0 else np.nan,
                "specialist_author_local": float(prior_works >= 2 and not np.isnan(prior_share) and prior_share >= (2 / 3)) if prior_works > 0 else np.nan,
                "bridge_author_local": float(prior_works >= 2 and prior_distinct >= 2 and not np.isnan(prior_share) and 0 < prior_share < (2 / 3)) if prior_works > 0 else np.nan,
                "outsider_author_local": float(prior_works >= 2 and not np.isnan(prior_share) and prior_share <= 0.2) if prior_works > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _load_api_keys(paths: list[Path]) -> list[str]:
    keys: list[str] = []
    for path in paths:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                keys.append(text)
    return keys


def _cached_jsonl_map(path: Path, id_field: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            norm = _normalize_openalex_id(obj.get(id_field) or obj.get("id"))
            if norm:
                out[norm] = obj
    return out


def _fetch_openalex_json(entity: str, entity_id: str, api_key: str | None, max_retries: int = 6) -> dict[str, Any]:
    entity_id = _normalize_openalex_id(entity_id)
    url = f"https://api.openalex.org/{entity}/{entity_id}"
    params = {}
    if api_key:
        params["api_key"] = api_key
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "FrontierGraph/0.1 (mailto:prashant@example.com)"}
    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {404}:
                return {"id": _full_openalex_url(entity_id), "_missing": True}
            if exc.code in {429, 500, 502, 503, 504}:
                time.sleep(min(10.0, 0.75 * (2 ** attempt)))
                continue
            raise
        except Exception:
            time.sleep(min(10.0, 0.75 * (2 ** attempt)))
    raise RuntimeError(f"OpenAlex fetch failed for {entity}/{entity_id}")


def _fetch_missing_entities(entity: str, ids: list[str], cache_path: Path, keys: list[str], concurrency: int) -> dict[str, dict[str, Any]]:
    ensure_dir(cache_path.parent)
    cached = _cached_jsonl_map(cache_path, "id")
    missing = [x for x in ids if _normalize_openalex_id(x) not in cached]
    if not missing:
        return cached

    print(f"[openalex] fetching {len(missing):,} missing {entity} records", flush=True)
    results: list[dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(missing)))) as ex:
        future_map = {}
        for idx, entity_id in enumerate(missing):
            key = keys[idx % len(keys)] if keys else None
            fut = ex.submit(_fetch_openalex_json, entity, entity_id, key)
            future_map[fut] = entity_id
        for i, fut in enumerate(cf.as_completed(future_map), start=1):
            obj = fut.result()
            results.append(obj)
            if i % 250 == 0 or i == len(future_map):
                print(f"[openalex] fetched {i:,}/{len(future_map):,} {entity} records", flush=True)

    with open(cache_path, "a", encoding="utf-8") as fh:
        for obj in results:
            fh.write(json.dumps(obj, ensure_ascii=True) + "\n")
            norm = _normalize_openalex_id(obj.get("id"))
            if norm:
                cached[norm] = obj
    return cached


def _counts_by_year_metrics(counts_by_year: list[dict[str, Any]], focal_year: int) -> tuple[float, float, float]:
    rows = []
    for item in counts_by_year:
        try:
            year = int(item.get("year"))
        except Exception:
            continue
        works_count = float(item.get("works_count") or 0.0)
        cited_by_count = float(item.get("cited_by_count") or 0.0)
        rows.append((year, works_count, cited_by_count))
    if not rows:
        return np.nan, np.nan, np.nan
    earliest = min(year for year, works, _ in rows if works > 0) if any(works > 0 for year, works, _ in rows) else min(year for year, _, _ in rows)
    prior = [(works, cites) for year, works, cites in rows if year < focal_year]
    prior_works = float(sum(w for w, _ in prior))
    prior_cites = float(sum(c for _, c in prior))
    career_age = float(focal_year - earliest)
    return career_age, prior_works, prior_cites


def _build_author_global_metrics(focal: pd.DataFrame, derived_dir: Path, keys: list[str], concurrency: int) -> pd.DataFrame:
    author_ids = sorted({_normalize_openalex_id(x) for x in focal["author_id"].dropna().astype(str) if str(x).strip()})
    cache_path = derived_dir / "openalex_authors_raw.jsonl"
    cached = _fetch_missing_entities("authors", author_ids, cache_path, keys, concurrency)
    rows = []
    for row in focal[["realizing_paper_id", "author_id", "realizing_paper_year"]].drop_duplicates().itertuples(index=False):
        author_id = _normalize_openalex_id(row.author_id)
        payload = cached.get(author_id, {})
        career_age, prior_works, prior_cites = _counts_by_year_metrics(payload.get("counts_by_year") or [], int(row.realizing_paper_year))
        rows.append(
            {
                "realizing_paper_id": str(row.realizing_paper_id),
                "author_id": _full_openalex_url(author_id),
                "career_age_global": career_age,
                "prior_works_global": prior_works,
                "prior_citations_global": prior_cites,
                "works_count_lifetime_global": float(payload.get("works_count") or np.nan),
                "cited_by_count_lifetime_global": float(payload.get("cited_by_count") or np.nan),
            }
        )
    out = pd.DataFrame(rows)
    out.to_parquet(derived_dir / "openalex_author_global_metrics.parquet", index=False)
    out.to_csv(derived_dir / "openalex_author_global_metrics.csv", index=False)
    return out


def _build_work_institution_metrics(focal: pd.DataFrame, derived_dir: Path, keys: list[str], concurrency: int) -> pd.DataFrame:
    work_ids = sorted({_normalize_openalex_id(x) for x in focal["realizing_work_id"].dropna().astype(str) if str(x).strip()})
    cache_path = derived_dir / "openalex_works_raw.jsonl"
    cached = _fetch_missing_entities("works", work_ids, cache_path, keys, concurrency)
    rows: list[dict[str, Any]] = []
    for work_id_norm, payload in cached.items():
        work_url = _full_openalex_url(work_id_norm)
        for authorship in payload.get("authorships") or []:
            author = authorship.get("author") or {}
            author_id = _full_openalex_url(_normalize_openalex_id(author.get("id")))
            institutions = authorship.get("institutions") or []
            country_codes = sorted({str(inst.get("country_code") or "") for inst in institutions if str(inst.get("country_code") or "")})
            inst_types = sorted({str(inst.get("type") or "") for inst in institutions if str(inst.get("type") or "")})
            inst_names = sorted({str(inst.get("display_name") or "") for inst in institutions if str(inst.get("display_name") or "")})
            inst_ids = sorted({_full_openalex_url(_normalize_openalex_id(inst.get("id"))) for inst in institutions if str(inst.get("id") or "")})
            rows.append(
                {
                    "realizing_work_id": work_url,
                    "author_id": author_id,
                    "institution_ids_json": json.dumps(inst_ids, ensure_ascii=True),
                    "institution_names_json": json.dumps(inst_names, ensure_ascii=True),
                    "institution_country_codes_json": json.dumps(country_codes, ensure_ascii=True),
                    "institution_types_json": json.dumps(inst_types, ensure_ascii=True),
                    "primary_country_code": country_codes[0] if country_codes else "",
                    "primary_institution_type": inst_types[0] if inst_types else "",
                }
            )
    out = pd.DataFrame(rows).drop_duplicates(subset=["realizing_work_id", "author_id"])
    out.to_parquet(derived_dir / "openalex_work_institutions.parquet", index=False)
    out.to_csv(derived_dir / "openalex_work_institutions.csv", index=False)
    return out


def _build_work_metadata(focal: pd.DataFrame, derived_dir: Path, published_journal_dir: Path) -> pd.DataFrame:
    cache_path = derived_dir / "openalex_works_raw.jsonl"
    cached = _cached_jsonl_map(cache_path, "id")
    core_set, adjacent_set = _load_corpus_venue_sets(published_journal_dir)
    work_ids = sorted({_normalize_openalex_id(x) for x in focal["realizing_work_id"].dropna().astype(str) if str(x).strip()})
    rows: list[dict[str, Any]] = []
    for work_id in work_ids:
        payload = cached.get(work_id, {})
        primary_topic = payload.get("primary_topic") or {}
        source = ((payload.get("primary_location") or {}).get("source") or {})
        venue = str(source.get("display_name") or source.get("raw_source_name") or "")
        venue_norm = _normalize_text(venue)
        source_is_core = bool(source.get("is_core")) if source.get("is_core") is not None else False
        if venue_norm in TOP5_VENUES:
            venue_tier = "top5_general_interest"
        elif venue in core_set or source_is_core:
            venue_tier = "core_other"
        elif venue in adjacent_set:
            venue_tier = "adjacent"
        else:
            venue_tier = "other"
        primary_topic_display = str(primary_topic.get("display_name") or "")
        rows.append(
            {
                "realizing_work_id": _full_openalex_url(work_id),
                "oa_work_type": str(payload.get("type") or ""),
                "oa_source_is_core": int(source_is_core),
                "oa_primary_topic_display_name": primary_topic_display,
                "oa_primary_topic_subfield": str((primary_topic.get("subfield") or {}).get("display_name") or ""),
                "oa_primary_topic_field": str((primary_topic.get("field") or {}).get("display_name") or ""),
                "venue_tier": venue_tier,
                "venue_cluster": _venue_cluster(venue),
                "paper_type_bucket": _paper_type_bucket(primary_topic_display, str(payload.get("display_name") or payload.get("title") or "")),
            }
        )
    out = pd.DataFrame(rows)
    out.to_parquet(derived_dir / "openalex_work_metadata.parquet", index=False)
    out.to_csv(derived_dir / "openalex_work_metadata.csv", index=False)
    return out


def _assemble_focal_enriched(
    focal: pd.DataFrame,
    local_metrics: pd.DataFrame,
    author_global: pd.DataFrame,
    work_inst: pd.DataFrame,
    work_meta: pd.DataFrame,
    derived_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = focal.merge(
        local_metrics,
        on=["realizing_paper_id", "realizing_work_id", "author_id"],
        how="left",
    )
    out = out.merge(author_global, on=["realizing_paper_id", "author_id"], how="left")
    out = out.merge(work_inst, on=["realizing_work_id", "author_id"], how="left")
    out = out.merge(work_meta, on=["realizing_work_id"], how="left")
    out["primary_institution_type_clean"] = out.apply(
        lambda r: _clean_institution_type(r.get("primary_institution_type"), _safe_list(r.get("institution_names_json"))),
        axis=1,
    )
    out.to_parquet(derived_dir / "author_paper_enriched_local_and_openalex.parquet", index=False)
    out.to_csv(derived_dir / "author_paper_enriched_local_and_openalex.csv", index=False)

    coverage = pd.DataFrame(
        [
            {"field": "career_age_local", "missing_share": float(out["career_age_local"].isna().mean())},
            {"field": "prior_works_local", "missing_share": float(out["prior_works_local"].isna().mean())},
            {"field": "career_age_global", "missing_share": float(out["career_age_global"].isna().mean())},
            {"field": "prior_works_global", "missing_share": float(out["prior_works_global"].isna().mean())},
            {"field": "prior_citations_global", "missing_share": float(out["prior_citations_global"].isna().mean())},
            {"field": "bridge_author_local", "missing_share": float(out["bridge_author_local"].isna().mean())},
            {"field": "specialist_author_local", "missing_share": float(out["specialist_author_local"].isna().mean())},
            {"field": "primary_country_code", "missing_share": float(out["primary_country_code"].replace("", np.nan).isna().mean())},
            {"field": "primary_institution_type", "missing_share": float(out["primary_institution_type"].replace("", np.nan).isna().mean())},
        ]
    )
    coverage.to_csv(derived_dir / "author_enrichment_coverage.csv", index=False)
    return out, coverage


def _build_paper_level_adopter_package(
    uptake: pd.DataFrame,
    bundle: pd.DataFrame,
    paper_meta: pd.DataFrame,
    focal_enriched: pd.DataFrame,
    coverage: pd.DataFrame,
    out_dir: Path,
) -> dict[str, Any]:
    ensure_dir(out_dir)
    paper_level = bundle.merge(
        uptake[
            [
                "realizing_paper_id",
                "realizing_work_id",
                "realizing_paper_year",
                "realizing_paper_title",
                "realizing_paper_venue",
                "realizing_primary_subfield_display_name",
                "realizing_unique_funder_count",
                "realizing_first_funder",
            ]
        ].drop_duplicates(),
        on=[
            "realizing_paper_id",
            "realizing_work_id",
            "realizing_paper_year",
            "realizing_paper_title",
            "realizing_paper_venue",
            "realizing_primary_subfield_display_name",
        ],
        how="left",
    )

    auth_agg = (
        focal_enriched.groupby("realizing_paper_id", as_index=False)
        .agg(
            team_size=("author_id", pd.Series.nunique),
            share_entrant_local=("entrant_local", "mean"),
            share_incumbent_local=("incumbent_local", "mean"),
            share_specialist_author_local=("specialist_author_local", "mean"),
            share_bridge_author_local=("bridge_author_local", "mean"),
            share_outsider_author_local=("outsider_author_local", "mean"),
            mean_career_age_local=("career_age_local", "mean"),
            max_career_age_local=("career_age_local", "max"),
            mean_prior_works_local=("prior_works_local", "mean"),
            max_prior_works_local=("prior_works_local", "max"),
            mean_career_age_global=("career_age_global", "mean"),
            max_career_age_global=("career_age_global", "max"),
            mean_prior_works_global=("prior_works_global", "mean"),
            mean_prior_citations_global=("prior_citations_global", "mean"),
            distinct_institutions=("institution_id", lambda s: pd.Series(s).replace("", np.nan).dropna().nunique()),
            distinct_countries=("primary_country_code", lambda s: pd.Series(s).replace("", np.nan).dropna().nunique()),
            dominant_institution_type=("primary_institution_type", _mode_nonempty),
            dominant_institution_sector=("primary_institution_type_clean", _mode_nonempty),
            any_government_or_central_bank=("primary_institution_type_clean", lambda s: int(pd.Series(s).eq("government_central_bank").any())),
            any_healthcare_institution=("primary_institution_type_clean", lambda s: int(pd.Series(s).eq("healthcare").any())),
        )
    )
    auth_agg["solo_vs_team"] = np.where(pd.to_numeric(auth_agg["team_size"], errors="coerce").fillna(0).astype(int) <= 1, "solo", "team")
    auth_agg["team_size_bucket"] = pd.cut(
        pd.to_numeric(auth_agg["team_size"], errors="coerce").fillna(0),
        bins=[-1, 1, 3, 6, 1000],
        labels=["solo", "2-3", "4-6", "7+"],
    ).astype(str)
    auth_agg["cross_country_team"] = (pd.to_numeric(auth_agg["distinct_countries"], errors="coerce").fillna(0) > 1).astype(int)

    paper_level = paper_level.merge(auth_agg, on="realizing_paper_id", how="left")
    work_meta_cols = [
        "realizing_work_id",
        "oa_work_type",
        "oa_source_is_core",
        "oa_primary_topic_display_name",
        "oa_primary_topic_subfield",
        "oa_primary_topic_field",
        "venue_tier",
        "venue_cluster",
        "paper_type_bucket",
    ]
    paper_level = paper_level.merge(
        focal_enriched[work_meta_cols].drop_duplicates(),
        on="realizing_work_id",
        how="left",
    )
    paper_level["dominant_institution_sector"] = paper_level["dominant_institution_sector"].fillna("missing").replace("", "missing")
    paper_level["venue_tier"] = paper_level["venue_tier"].fillna("other").replace("", "other")
    paper_level["venue_cluster"] = paper_level["venue_cluster"].fillna("other").replace("", "other")
    paper_level["paper_type_bucket"] = paper_level["paper_type_bucket"].fillna("other").replace("", "other")
    paper_level["has_any_funder"] = (pd.to_numeric(paper_level["realizing_unique_funder_count"], errors="coerce").fillna(0) > 0).astype(int)
    paper_level["funder_count_bucket"] = pd.to_numeric(paper_level["realizing_unique_funder_count"], errors="coerce").fillna(0).astype(int).map(_funder_bucket)
    paper_level["venue_bucket"] = paper_level["realizing_paper_venue"].map(_venue_bucket)

    paper_base = uptake[
        [
            "realizing_paper_id",
            "realizing_work_id",
            "realizing_paper_year",
            "realizing_paper_title",
            "realizing_paper_venue",
            "realizing_primary_subfield_display_name",
            "horizon",
            "candidate_family_mode",
        ]
    ].drop_duplicates().merge(
        paper_level,
        on=[
            "realizing_paper_id",
            "realizing_work_id",
            "realizing_paper_year",
            "realizing_paper_title",
            "realizing_paper_venue",
            "realizing_primary_subfield_display_name",
            "horizon",
        ],
        how="left",
    )

    venue_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "venue_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    team_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "team_size_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    funder_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "funder_count_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    venue_tier_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "venue_tier"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    venue_cluster_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "venue_cluster"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    paper_type_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "paper_type_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    institution_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "dominant_institution_sector"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
    )
    top_subfields = (
        paper_base.groupby(["horizon", "candidate_family_mode", "realizing_primary_subfield_display_name"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "n_papers"], ascending=[True, True, False])
        .groupby(["horizon", "candidate_family_mode"], as_index=False)
        .head(5)
        .reset_index(drop=True)
    )
    bundle_split_summary = (
        paper_base.assign(bundle_type=np.where(pd.to_numeric(paper_base["predicted_edge_count"], errors="coerce").fillna(0) > 1, "multi_edge", "single_edge"))
        .groupby(["horizon", "candidate_family_mode", "bundle_type"], as_index=False)
        .agg(
            n_papers=("realizing_paper_id", "nunique"),
            mean_team_size=("team_size", "mean"),
            share_any_funder=("has_any_funder", "mean"),
            share_cross_country=("cross_country_team", "mean"),
            share_incumbent_local=("share_incumbent_local", "mean"),
            share_bridge_author_local=("share_bridge_author_local", "mean"),
            mean_prior_works_global=("mean_prior_works_global", "mean"),
        )
    )
    overview = (
        paper_base.groupby(["horizon", "candidate_family_mode"], as_index=False)
        .agg(
            n_papers=("realizing_paper_id", "nunique"),
            mean_team_size=("team_size", "mean"),
            share_any_funder=("has_any_funder", "mean"),
            share_cross_country=("cross_country_team", "mean"),
            share_incumbent_local=("share_incumbent_local", "mean"),
            share_bridge_author_local=("share_bridge_author_local", "mean"),
            mean_career_age_local=("mean_career_age_local", "mean"),
            mean_career_age_global=("mean_career_age_global", "mean"),
            mean_prior_works_global=("mean_prior_works_global", "mean"),
            share_mixed_family=("family_mix", lambda s: float((pd.Series(s) == "mixed_family").mean())),
        )
    )

    comparison_table = _comparison_rows(
        paper_base,
        [
            ("team_size", "Team size", "continuous"),
            ("has_any_funder", "Any recorded funder", "binary"),
            ("cross_country_team", "Cross-country team", "binary"),
            ("share_incumbent_local", "Share incumbent authors", "continuous"),
            ("share_bridge_author_local", "Share bridge authors", "continuous"),
            ("mean_career_age_global", "Mean global career age", "continuous"),
            ("mean_prior_works_global", "Mean global prior works", "continuous"),
        ],
    )

    venue_review = (
        paper_base.groupby(
            [
                "horizon",
                "candidate_family_mode",
                "realizing_paper_venue",
                "venue_bucket",
                "venue_tier",
                "venue_cluster",
                "paper_type_bucket",
            ],
            as_index=False,
        )
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "n_papers"], ascending=[True, True, False])
    )
    suspicious_venues = venue_review[
        venue_review["venue_tier"].fillna("").eq("other")
        | (
            venue_review["venue_cluster"].fillna("").eq("other")
            & venue_review["n_papers"].ge(5)
        )
    ].copy()

    paper_level.to_parquet(out_dir / "adopter_profile_paper_level_unique.parquet", index=False)
    paper_level.to_csv(out_dir / "adopter_profile_paper_level_unique.csv", index=False)
    paper_base.to_parquet(out_dir / "adopter_profile_paper_level.parquet", index=False)
    paper_base.to_csv(out_dir / "adopter_profile_paper_level.csv", index=False)
    venue_summary.to_csv(out_dir / "adopter_profile_venue_summary.csv", index=False)
    team_summary.to_csv(out_dir / "adopter_profile_team_summary.csv", index=False)
    funder_summary.to_csv(out_dir / "adopter_profile_funder_summary.csv", index=False)
    venue_tier_summary.to_csv(out_dir / "adopter_profile_venue_tier_summary.csv", index=False)
    venue_cluster_summary.to_csv(out_dir / "adopter_profile_venue_cluster_summary.csv", index=False)
    paper_type_summary.to_csv(out_dir / "adopter_profile_paper_type_summary.csv", index=False)
    institution_summary.to_csv(out_dir / "adopter_profile_institution_summary.csv", index=False)
    top_subfields.to_csv(out_dir / "adopter_profile_top_subfields.csv", index=False)
    bundle_split_summary.to_csv(out_dir / "adopter_profile_bundle_split_summary.csv", index=False)
    comparison_table.to_csv(out_dir / "adopter_profile_difference_tests.csv", index=False)
    venue_review.to_csv(out_dir / "adopter_profile_venue_review.csv", index=False)
    suspicious_venues.to_csv(out_dir / "adopter_profile_suspicious_venues.csv", index=False)
    coverage.to_csv(out_dir / "adopter_profile_enrichment_coverage.csv", index=False)
    _write_tex_table(overview.round(3), out_dir / "adopter_profile_overview.tex", index=False)
    comparison_tex = comparison_table.copy()
    for col in ["path_to_direct_mean", "direct_to_path_mean", "difference_path_minus_direct", "ci_low", "ci_high"]:
        comparison_tex[col] = pd.to_numeric(comparison_tex[col], errors="coerce").round(3)
    comparison_tex = comparison_tex[
        [
            "horizon",
            "label",
            "path_to_direct_mean",
            "direct_to_path_mean",
            "difference_path_minus_direct",
            "ci_low",
            "ci_high",
            "p_display",
            "n_path_to_direct",
            "n_direct_to_path",
        ]
    ].rename(
        columns={
            "label": "Metric",
            "path_to_direct_mean": "Path-direct",
            "direct_to_path_mean": "Direct-path",
            "difference_path_minus_direct": "Difference",
            "ci_low": "CI low",
            "ci_high": "CI high",
            "p_display": "p",
            "n_path_to_direct": "N path",
            "n_direct_to_path": "N direct",
            "horizon": "Horizon",
        }
    )
    _write_tex_table(comparison_tex, out_dir / "adopter_profile_difference_tests.tex", index=False)

    def _bar_pair_plot(summary: pd.DataFrame, idx_order: list[str], xlabels: list[str], title: str, out_name: str) -> None:
        fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
        for ax, horizon in zip(axes, HORIZON_ORDER):
            sub = summary[summary["horizon"] == horizon]
            key_col = [c for c in summary.columns if c not in {"horizon", "candidate_family_mode", "n_papers"}][0]
            pivot = sub.pivot(index=key_col, columns="candidate_family_mode", values="n_papers").fillna(0)
            pivot = pivot.reindex(idx_order).fillna(0)
            x = np.arange(len(pivot))
            width = 0.38
            ax.bar(x - width / 2, pivot.get("path_to_direct", pd.Series(0, index=pivot.index)).values, width=width, color="#1d4ed8")
            ax.bar(x + width / 2, pivot.get("direct_to_path", pd.Series(0, index=pivot.index)).values, width=width, color="#b45309")
            ax.set_xticks(x)
            ax.set_xticklabels(xlabels)
            ax.set_title(f"h={horizon}")
        axes[0].set_ylabel("Realizing papers")
        fig.suptitle(title, y=1.02)
        fig.tight_layout()
        fig.savefig(out_dir / f"{out_name}.png", dpi=200, bbox_inches="tight")
        fig.savefig(out_dir / f"{out_name}.pdf", bbox_inches="tight")
        plt.close(fig)

    _bar_pair_plot(venue_summary, ["general_interest", "field", "adjacent_interdisciplinary", "other"], ["GI", "Field", "Adj.", "Other"], "Adopter profiles: venue bucket by family", "adopter_profile_venue")
    _bar_pair_plot(team_summary, ["solo", "2-3", "4-6", "7+"], ["Solo", "2-3", "4-6", "7+"], "Adopter profiles: team size by family", "adopter_profile_team_size")
    _bar_pair_plot(funder_summary, ["none", "one", "two_plus"], ["None", "One", "2+"], "Adopter profiles: funder presence by family", "adopter_profile_funders")
    _bar_pair_plot(venue_tier_summary, ["top5_general_interest", "core_other", "adjacent", "other"], ["Top5", "Core", "Adj.", "Other"], "Adopter profiles: venue tier by family", "adopter_profile_venue_tier")
    _bar_pair_plot(paper_type_summary, ["macro_monetary_fiscal_growth", "finance_banking_housing", "energy_environment", "health_policy_or_health_econ", "trade_development_innovation", "labor_public_human_capital", "theory_or_methods", "other"], ["Macro", "Finance", "Energy", "Health", "Trade", "Labor", "Theory", "Other"], "Adopter profiles: paper type by family", "adopter_profile_paper_type")

    note_lines = [
        "# Adopter profiles note",
        "",
        "This package describes which papers and teams independently move toward graph-supported questions.",
        "",
    ]
    for horizon in HORIZON_ORDER:
        block = overview[overview["horizon"] == horizon]
        if block.empty:
            continue
        note_lines.append(f"## h={horizon}")
        for row in block.itertuples(index=False):
            note_lines.append(
                f"- {row.candidate_family_mode}: mean team size {float(row.mean_team_size):.2f}, share with any funder {float(row.share_any_funder):.3f}, share cross-country {float(row.share_cross_country):.3f}, share incumbent authors {float(row.share_incumbent_local):.3f}, share bridge authors {float(row.share_bridge_author_local):.3f}, mean global prior works {float(row.mean_prior_works_global):.2f}."
            )
        note_lines.append("")
    note_lines.append("## Venue review")
    odd = suspicious_venues[suspicious_venues["horizon"] == 10].head(10)
    for row in odd.itertuples(index=False):
        note_lines.append(
            f"- h={int(row.horizon)} {row.candidate_family_mode}: {row.realizing_paper_venue} -> tier={row.venue_tier}, bucket={row.venue_bucket}, cluster={row.venue_cluster}, n={int(row.n_papers)}."
        )
    note_lines.append("## Coverage")
    for row in coverage.itertuples(index=False):
        note_lines.append(f"- {row.field}: missing share {float(row.missing_share):.3f}")
    (out_dir / "adopter_profile_note.md").write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    return {
        "paper_base": paper_base,
        "overview": overview,
        "coverage": coverage,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build adopter profiles using local metadata plus targeted OpenAlex API enrichment.")
    parser.add_argument("--uptake", default=str(DEFAULT_UPTAKE))
    parser.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE_DIR))
    parser.add_argument("--paper-meta", default=str(DEFAULT_PAPER_META))
    parser.add_argument("--authorships", default=str(DEFAULT_AUTHORSHIPS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--derived-dir", default=str(DEFAULT_DERIVED_DIR))
    parser.add_argument("--published-journal-dir", default=str(DEFAULT_PUBLISHED_JOURNAL_CORPORA))
    parser.add_argument("--key-files", nargs="*", default=[str(p) for p in DEFAULT_KEY_FILES])
    parser.add_argument("--concurrency", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    derived_dir = Path(args.derived_dir)
    ensure_dir(out_dir)
    ensure_dir(derived_dir)

    print("[adopters] loading inputs", flush=True)
    uptake, bundle, paper_meta, authorships = _load_inputs(args)
    print(f"[adopters] uptake rows={len(uptake):,}, bundle papers={len(bundle):,}", flush=True)

    print("[adopters] building focal authorship spine", flush=True)
    focal, author_history = _build_focal_authorships(uptake, paper_meta, authorships)
    print(
        f"[adopters] focal papers={focal['realizing_paper_id'].nunique():,}, focal authors={focal['author_id'].nunique():,}, local author-history rows={len(author_history):,}",
        flush=True,
    )

    print("[adopters] computing local author history metrics", flush=True)
    local_metrics = _compute_local_author_metrics(focal, author_history)
    local_metrics.to_parquet(derived_dir / "author_local_history_metrics.parquet", index=False)
    local_metrics.to_csv(derived_dir / "author_local_history_metrics.csv", index=False)

    key_paths = [Path(x) for x in args.key_files]
    keys = _load_api_keys(key_paths)
    if not keys:
        raise RuntimeError("No OpenAlex API keys found. Provide --key-files or ensure the default key files exist.")
    print(f"[adopters] loaded {len(keys)} OpenAlex API keys", flush=True)

    print("[adopters] fetching author-level OpenAlex metrics", flush=True)
    author_global = _build_author_global_metrics(focal, derived_dir, keys, args.concurrency)
    print("[adopters] fetching work-level OpenAlex institution data", flush=True)
    work_inst = _build_work_institution_metrics(focal, derived_dir, keys, args.concurrency)
    print("[adopters] building cached work metadata", flush=True)
    work_meta = _build_work_metadata(focal, derived_dir, Path(args.published_journal_dir))

    print("[adopters] assembling enriched author-paper table", flush=True)
    focal_enriched, coverage = _assemble_focal_enriched(focal, local_metrics, author_global, work_inst, work_meta, derived_dir)
    print("[adopters] building paper-level adopter package", flush=True)
    outputs = _build_paper_level_adopter_package(uptake, bundle, paper_meta, focal_enriched, coverage, out_dir)

    manifest = {
        "uptake": str(Path(args.uptake)),
        "bundle_dir": str(Path(args.bundle_dir)),
        "paper_meta": str(Path(args.paper_meta)),
        "authorships": str(Path(args.authorships)),
        "derived_dir": str(derived_dir),
        "n_realizing_papers": int(outputs["paper_base"]["realizing_paper_id"].nunique()),
        "n_unique_authors": int(focal["author_id"].nunique()),
        "n_unique_works": int(focal["realizing_work_id"].nunique()),
        "coverage": coverage.to_dict(orient="records"),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print("[adopters] complete", flush=True)


if __name__ == "__main__":
    main()
