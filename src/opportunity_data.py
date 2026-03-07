from __future__ import annotations

import sqlite3
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

NOVELTY_LABELS = {
    "gap_internal": "Within-field gap",
    "gap_crossfield": "Cross-field gap",
    "boundary_internal": "Within-field boundary",
    "boundary_crossfield": "Cross-field boundary",
}

PRESET_HELP = {
    "Balanced": "A broad default that keeps the base graph score central while still rewarding low-contact opportunities.",
    "Bold frontier": "Pushes toward boundary and cross-field links that could open fresh lines of work.",
    "Fast follow": "Favors ideas that already have strong graph support and look tractable now.",
    "Underexplored": "Pushes toward thinly connected areas where direct work has lagged the surrounding graph.",
    "Bridge builder": "Looks for ideas that connect literatures and shift the field map.",
}


def connect_readonly(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    uri = f"file:{quote(str(path))}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False, timeout=30)


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


def classify_novelty(row: pd.Series) -> str:
    cooc_count = to_float(row.get("cooc_count", 0), default=0.0)
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
        return "Build a bridge paper across literatures."
    if novelty == "boundary_crossfield":
        return "Start with a scoping review before a bridge paper."
    if gap_bonus >= 0.4 and mediator_count >= 25:
        return "Convert scattered hints into a direct empirical test."
    if gap_bonus >= 0.4:
        return "Commission a short synthesis and pilot design."
    if path_support >= 0.8 and motif_count >= 100:
        return "This is a strong candidate for a flagship empirical paper."
    if path_support >= 0.7:
        return "Test the direct link with a focused empirical design."
    return "Use this as a seminar seed or targeted replication map."


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


def enrich_candidates(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working["u"] = working["u"].astype(str)
    working["v"] = working["v"].astype(str)
    working["u_label"] = working["u_label"].fillna(working["u"]).astype(str)
    working["v_label"] = working["v_label"].fillna(working["v"]).astype(str)
    working["source_field"] = working["u"].str[0]
    working["target_field"] = working["v"].str[0]
    working["source_field_name"] = working["source_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
    working["target_field_name"] = working["target_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
    working["cross_field"] = working["source_field"] != working["target_field"]
    working["boundary_flag"] = working["cross_field"] & (working["cooc_count"].fillna(0) <= 0)
    working["novelty_type"] = working.apply(classify_novelty, axis=1)
    working["novelty_label"] = working["novelty_type"].map(NOVELTY_LABELS).fillna("Other")
    working["opportunity"] = working["u_label"] + " -> " + working["v_label"]
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
    sql = """
        SELECT
            c.u,
            c.v,
            c.score,
            c.rank,
            c.path_support_norm,
            c.gap_bonus,
            c.motif_bonus_norm,
            c.hub_penalty,
            c.mediator_count,
            c.motif_count,
            c.cooc_count,
            c.first_year_seen,
            c.last_year_seen,
            nu.label AS u_label,
            nv.label AS v_label
        FROM candidates c
        LEFT JOIN nodes nu ON c.u = nu.code
        LEFT JOIN nodes nv ON c.v = nv.code
    """
    with connect_readonly(db_path) as conn:
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

    return enrich_candidates(df)
