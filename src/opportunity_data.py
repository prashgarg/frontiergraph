from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd


JEL_FIELD_NAMES = {
    "A": "General economics and teaching",
    "B": "History of economic thought",
    "C": "Mathematical and quantitative methods",
    "D": "Microeconomics",
    "E": "Macroeconomics and monetary economics",
    "F": "International economics",
    "G": "Financial economics",
    "H": "Public economics",
    "I": "Health, education, and welfare",
    "J": "Labor and demographic economics",
    "K": "Law and economics",
    "L": "Industrial organization",
    "M": "Business administration and business economics",
    "N": "Economic history",
    "O": "Economic development, innovation, and growth",
    "P": "Economic systems",
    "Q": "Agriculture, natural resources, and environment",
    "R": "Urban, rural, and regional economics",
    "Y": "Miscellaneous",
    "Z": "Other special topics",
}

CONCEPT_BUCKET_NAMES = {
    "core": "Core-heavy",
    "adjacent": "Adjacent-heavy",
    "mixed": "Mixed support",
    "unknown": "Unknown",
}

NOVELTY_LABELS = {
    "gap_internal": "Within-field gap",
    "gap_crossfield": "Cross-field gap",
    "boundary_internal": "Within-field boundary",
    "boundary_crossfield": "Cross-field boundary",
}

PRESET_HELP = {
    "Balanced": "A broad default for browsing candidate research questions without pushing too hard toward either the safest or the boldest end of the list.",
    "Bold frontier": "Pushes toward more boundary-crossing questions that could open fresh lines of work.",
    "Fast follow": "Favors questions that already look grounded enough for a more direct next paper.",
    "Underexplored": "Pushes toward questions where the direct literature still looks thin relative to the surrounding literature.",
    "Bridge builder": "Looks for questions that connect literatures that are usually studied apart.",
}

_READONLY_DB_CACHE: dict[str, Path] = {}
_PUBLIC_LABEL_CACHE: dict[str, dict[str, str]] | None = None
PUBLIC_LABEL_GLOSSARY_PATH = Path(__file__).resolve().parents[1] / "site" / "src" / "content" / "public-label-glossary.json"


def _readonly_uri(path: Path) -> str:
    return f"file:{quote(str(path))}?mode=ro&immutable=1"


def _probe_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA query_only = 1")
    conn.execute("PRAGMA schema_version").fetchone()


def _staged_db_path(source_path: Path) -> Path:
    stat = source_path.stat()
    fingerprint = hashlib.sha1(
        f"{source_path}|{stat.st_size}|{int(stat.st_mtime)}".encode("utf-8"),
    ).hexdigest()[:12]
    cache_root = Path(os.environ.get("FRONTIERGRAPH_DB_CACHE_DIR", "")).expanduser() if os.environ.get("FRONTIERGRAPH_DB_CACHE_DIR") else Path(tempfile.gettempdir()) / "frontiergraph-db-cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix or ".sqlite"
    return cache_root / f"{source_path.stem}-{fingerprint}{suffix}"


def _stage_readonly_db(source_path: Path) -> Path:
    target_path = _staged_db_path(source_path)
    if target_path.exists() and target_path.stat().st_size == source_path.stat().st_size:
        return target_path
    shutil.copyfile(source_path, target_path)
    target_path.chmod(0o644)
    return target_path


def connect_readonly(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    cache_key = str(path)
    cached_path = _READONLY_DB_CACHE.get(cache_key)
    errors: list[Exception] = []

    seen_candidates: set[Path] = set()
    for candidate in [cached_path, path]:
        if candidate is None or candidate in seen_candidates:
            continue
        seen_candidates.add(candidate)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(_readonly_uri(candidate), uri=True, check_same_thread=False, timeout=30)
            _probe_connection(conn)
            _READONLY_DB_CACHE[cache_key] = candidate
            return conn
        except sqlite3.OperationalError as exc:
            errors.append(exc)
            try:
                conn.close()
            except Exception:
                pass

    try:
        staged_path = _stage_readonly_db(path)
    except OSError as exc:
        errors.append(exc)
        staged_path = None
    if staged_path and staged_path != path:
        conn = None
        try:
            conn = sqlite3.connect(_readonly_uri(staged_path), uri=True, check_same_thread=False, timeout=30)
            _probe_connection(conn)
            _READONLY_DB_CACHE[cache_key] = staged_path
            return conn
        except sqlite3.OperationalError as exc:
            errors.append(exc)
            try:
                conn.close()
            except Exception:
                pass

    if errors:
        raise errors[-1]
    raise sqlite3.OperationalError(f"unable to open database file: {path}")


def load_app_mode(db_path: str) -> str:
    with connect_readonly(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "app_meta" not in tables:
            return "legacy"
        row = conn.execute("SELECT value FROM app_meta WHERE key = 'app_mode' LIMIT 1").fetchone()
        return str(row[0]) if row and row[0] else "legacy"


def is_concept_mode(app_mode: str) -> bool:
    return app_mode.startswith("concept_") or app_mode == "concept_beta"


def normalize_series(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if s.empty:
        return s
    s_min = float(s.min())
    s_max = float(s.max())
    if np.isclose(s_min, s_max):
        if s_max <= 0:
            return pd.Series(np.zeros(len(s)), index=s.index)
        return pd.Series(np.ones(len(s)), index=s.index)
    return (s - s_min) / (s_max - s_min)


def to_float(value: object, default: float = 0.0) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return default if pd.isna(numeric) else float(numeric)


def to_int(value: object, default: int = 0) -> int:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return default if pd.isna(numeric) else int(numeric)


def direct_literature_status(value: object) -> str:
    cooc_count = to_int(value, default=0)
    if cooc_count <= 0:
        return "No direct papers yet in the current public sample"
    if cooc_count <= 3:
        return "A few direct papers already exist in the current public sample"
    return "Direct literature already exists in the current public sample"


def _public_label_glossary() -> dict[str, dict[str, str]]:
    global _PUBLIC_LABEL_CACHE
    if _PUBLIC_LABEL_CACHE is not None:
        return _PUBLIC_LABEL_CACHE
    try:
        with PUBLIC_LABEL_GLOSSARY_PATH.open() as handle:
            payload = json.load(handle)
    except Exception:
        _PUBLIC_LABEL_CACHE = {}
        return _PUBLIC_LABEL_CACHE

    glossary: dict[str, dict[str, str]] = {}
    if isinstance(payload, dict):
        for concept_id, entry in payload.items():
            if isinstance(entry, dict):
                glossary[str(concept_id)] = {
                    "plain_label": str(entry.get("plain_label") or "").strip(),
                    "subtitle": str(entry.get("subtitle") or "").strip(),
                }
    _PUBLIC_LABEL_CACHE = glossary
    return glossary


def public_display_label(concept_id: object, raw_label: object) -> str:
    glossary = _public_label_glossary()
    entry = glossary.get(str(concept_id))
    if entry and entry.get("plain_label"):
        return entry["plain_label"]
    return str(raw_label or concept_id or "").strip()


def public_pair_label(row: pd.Series) -> str:
    source_label = public_display_label(row.get("u"), row.get("u_label", row.get("u", "")))
    target_label = public_display_label(row.get("v"), row.get("v_label", row.get("v", "")))
    return f"{source_label} and {target_label}"


def classify_novelty(row: pd.Series) -> str:
    cooc_count = to_float(row.get("cooc_count", 0), default=0.0)
    if "cross_field" in row.index:
        cross_field = bool(row.get("cross_field"))
    else:
        cross_field = str(row.get("u", ""))[:1] != str(row.get("v", ""))[:1]
    if cooc_count <= 0:
        return "boundary_crossfield" if cross_field else "boundary_internal"
    return "gap_crossfield" if cross_field else "gap_internal"


def compute_priority_score(df: pd.DataFrame, preset: str) -> pd.Series:
    base = df["score"].fillna(0.0)
    path = df["path_support_norm"].fillna(0.0)
    gap = df["gap_bonus"].fillna(0.0)
    motif = df["motif_bonus_norm"].fillna(0.0)
    hub = df["hub_penalty"].fillna(0.0)
    low_contact = df["low_contact_norm"].fillna(0.0)
    mediator = df["mediator_norm"].fillna(0.0)
    staleness = df["staleness_norm"].fillna(0.0)
    cross = df["cross_field_norm"].fillna(0.0)
    boundary = df["boundary_norm"].fillna(0.0)

    if preset == "Bold frontier":
        return 0.38 * base + 0.24 * boundary + 0.16 * cross + 0.12 * low_contact + 0.10 * (1.0 - hub)
    if preset == "Fast follow":
        return 0.42 * path + 0.20 * motif + 0.16 * base + 0.12 * mediator + 0.10 * (1.0 - low_contact)
    if preset == "Underexplored":
        return 0.28 * base + 0.26 * gap + 0.20 * low_contact + 0.14 * staleness + 0.12 * (1.0 - hub)
    if preset == "Bridge builder":
        return 0.34 * base + 0.24 * cross + 0.18 * boundary + 0.14 * path + 0.10 * (1.0 - hub)
    return 0.72 * base + 0.10 * cross + 0.08 * low_contact + 0.06 * (1.0 - hub) + 0.04 * mediator


def recommendation_play(row: pd.Series) -> str:
    novelty = str(row.get("novelty_type", ""))
    path_support = to_float(row.get("path_support_norm", 0.0), default=0.0)
    gap_bonus = to_float(row.get("gap_bonus", 0.0), default=0.0)
    mediator_count = to_int(row.get("mediator_count", 0), default=0)
    motif_count = to_int(row.get("motif_count", 0), default=0)

    if novelty == "boundary_crossfield" and path_support >= 0.7:
        return "Bridge paper across literatures"
    if novelty == "boundary_crossfield":
        return "Scoping review before a bridge paper"
    if gap_bonus >= 0.4 and mediator_count >= 25:
        return "Direct empirical test"
    if gap_bonus >= 0.4:
        return "Synthesis plus pilot design"
    if path_support >= 0.8 and motif_count >= 100:
        return "Flagship empirical paper"
    if path_support >= 0.7:
        return "Focused empirical test"
    return "Seminar seed or targeted replication map"


def why_now(row: pd.Series) -> str:
    source_label = str(row.get("u_label", row.get("u", "")))
    target_label = str(row.get("v_label", row.get("v", "")))
    mediator_count = to_int(row.get("mediator_count", 0), default=0)
    motif_count = to_int(row.get("motif_count", 0), default=0)
    cooc_count = to_int(row.get("cooc_count", 0), default=0)
    novelty = str(row.get("novelty_label", ""))
    return (
        f"{source_label} -> {target_label} has {mediator_count} mediators and {motif_count} supporting motifs, "
        f"while direct contact remains at {cooc_count} prior co-occurrences. In the current graph it looks like a "
        f"{novelty.lower()}."
    )


def enrich_candidates(df: pd.DataFrame, app_mode: str = "legacy") -> pd.DataFrame:
    working = df.copy()
    working["u"] = working["u"].astype(str)
    working["v"] = working["v"].astype(str)
    working["u_label"] = working["u_label"].fillna(working["u"]).astype(str)
    working["v_label"] = working["v_label"].fillna(working["v"]).astype(str)
    if is_concept_mode(app_mode):
        working["source_field"] = working.get("u_bucket_hint", pd.Series("mixed", index=working.index)).fillna("mixed").astype(str)
        working["target_field"] = working.get("v_bucket_hint", pd.Series("mixed", index=working.index)).fillna("mixed").astype(str)
        working["source_field_name"] = working["source_field"].map(CONCEPT_BUCKET_NAMES).fillna(working["source_field"])
        working["target_field_name"] = working["target_field"].map(CONCEPT_BUCKET_NAMES).fillna(working["target_field"])
    else:
        working["source_field"] = working["u"].str[0]
        working["target_field"] = working["v"].str[0]
        working["source_field_name"] = working["source_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
        working["target_field_name"] = working["target_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
    working["cross_field"] = working["source_field"] != working["target_field"]
    working["boundary_flag"] = working["cross_field"] & (working["cooc_count"].fillna(0) <= 0)
    working["novelty_type"] = working.apply(classify_novelty, axis=1)
    working["novelty_label"] = working["novelty_type"].map(NOVELTY_LABELS).fillna("Other")
    working["opportunity"] = working.apply(public_pair_label, axis=1)
    working["code_pair"] = working["u"] + " -> " + working["v"]

    cooc_log = np.log1p(working["cooc_count"].fillna(0).clip(lower=0))
    mediator_log = np.log1p(working["mediator_count"].fillna(0).clip(lower=0))
    motif_log = np.log1p(working["motif_count"].fillna(0).clip(lower=0))
    last_seen = working["last_year_seen"].fillna(0)

    working["low_contact_norm"] = 1.0 - normalize_series(cooc_log)
    working["mediator_norm"] = normalize_series(mediator_log)
    working["motif_count_norm"] = normalize_series(motif_log)
    working["staleness_norm"] = 1.0 - normalize_series(last_seen)
    working["boundary_norm"] = working["boundary_flag"].astype(float)
    working["cross_field_norm"] = working["cross_field"].astype(float)
    return working


def load_nodes(db_path: str) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query("SELECT code, label FROM nodes ORDER BY label, code", conn)


def load_candidate_summary(db_path: str) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        candidate_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(candidates)")
        }
        app_mode = "legacy"
        if "app_meta" in tables:
            row = conn.execute("SELECT value FROM app_meta WHERE key = 'app_mode' LIMIT 1").fetchone()
            if row and row[0]:
                app_mode = str(row[0])
        if is_concept_mode(app_mode) and {
            "u_preferred_label",
            "v_preferred_label",
            "u_bucket_hint",
            "v_bucket_hint",
        }.issubset(candidate_columns):
            sql = """
                SELECT
                    c.*,
                    COALESCE(c.u_preferred_label, nu.label) AS u_label,
                    COALESCE(c.v_preferred_label, nv.label) AS v_label
                FROM candidates c
                LEFT JOIN nodes nu ON c.u = nu.code
                LEFT JOIN nodes nv ON c.v = nv.code
            """
        elif "node_details" in tables:
            sql = """
                SELECT
                    c.*,
                    nu.label AS u_label,
                    nv.label AS v_label,
                    du.bucket_hint AS u_bucket_hint,
                    dv.bucket_hint AS v_bucket_hint,
                    du.instance_support AS u_instance_support,
                    dv.instance_support AS v_instance_support,
                    du.aliases_json AS u_aliases_json,
                    dv.aliases_json AS v_aliases_json,
                    du.representative_contexts_json AS u_contexts_json,
                    dv.representative_contexts_json AS v_contexts_json
                FROM candidates c
                LEFT JOIN nodes nu ON c.u = nu.code
                LEFT JOIN nodes nv ON c.v = nv.code
                LEFT JOIN node_details du ON c.u = du.concept_id
                LEFT JOIN node_details dv ON c.v = dv.concept_id
            """
        else:
            sql = """
                SELECT
                    c.*,
                    nu.label AS u_label,
                    nv.label AS v_label
                FROM candidates c
                LEFT JOIN nodes nu ON c.u = nu.code
                LEFT JOIN nodes nv ON c.v = nv.code
            """
        df = pd.read_sql_query(sql, conn)

    for col in [
        "score",
        "rank",
        "path_support_norm",
        "gap_bonus",
        "motif_bonus_norm",
        "hub_penalty",
        "mediator_count",
        "motif_count",
        "cooc_count",
        "first_year_seen",
        "last_year_seen",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return enrich_candidates(df, app_mode=app_mode)
