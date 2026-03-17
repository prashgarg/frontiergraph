from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.opportunity_data import connect_readonly


SITE_URL = "https://frontiergraph.com"
QUESTIONS_URL = f"{SITE_URL}/questions/"
GRAPH_URL = f"{SITE_URL}/graph/"
PAPER_URL = f"{SITE_URL}/paper/"
DOWNLOADS_URL = f"{SITE_URL}/downloads/"
DEFAULT_DB = Path(os.environ.get("FRONTIERGRAPH_PUBLIC_RELEASE_DB", "/tmp/frontiergraph-economics-public.db"))
LEGACY_DEFAULT_DB = Path("data/production/frontiergraph_public_release/frontiergraph-economics-public.db")
FALLBACK_DB = Path(
    "data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite"
)
POSTHOG_KEY = os.environ.get("FRONTIERGRAPH_POSTHOG_KEY", "").strip()
POSTHOG_HOST = os.environ.get("FRONTIERGRAPH_POSTHOG_HOST", "https://eu.i.posthog.com").strip().rstrip("/")
FEEDBACK_EMAIL = os.environ.get("FRONTIERGRAPH_FEEDBACK_EMAIL", "prashant.garg@imperial.ac.uk").strip()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

        :root {
            --paper: #f6f1e8;
            --paper-strong: #fffdf8;
            --surface: rgba(255, 253, 248, 0.98);
            --surface-muted: rgba(246, 240, 230, 0.95);
            --surface-strong: #fffdf8;
            --line: rgba(37, 48, 66, 0.12);
            --line-strong: rgba(37, 48, 66, 0.2);
            --ink: #18263a;
            --muted: #5b6676;
            --accent: #1f3248;
            --accent-soft: #2d776d;
            --shadow: 0 14px 38px rgba(39, 52, 70, 0.08);
        }
        .stApp {
            background:
                radial-gradient(circle at 18% 14%, rgba(45, 119, 109, 0.08), transparent 26%),
                radial-gradient(circle at 82% 10%, rgba(31, 50, 72, 0.05), transparent 28%),
                linear-gradient(180deg, #faf6ef 0%, var(--paper) 56%, #fbf8f2 100%);
            color: var(--ink);
            font-family: "Source Sans 3", sans-serif;
        }
        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
        }
        .block-container {
            max-width: 1240px;
            padding-top: 0.9rem;
            padding-bottom: 3rem;
        }
        section[data-testid="stSidebar"] {
            background: color-mix(in srgb, var(--surface-muted) 94%, transparent);
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] .sidebar-caption {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.55;
            margin: 0 0 0.7rem;
        }
        .stApp,
        .stApp p,
        .stApp li,
        .stApp label,
        .stApp .stCaption,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] * {
            color: var(--ink);
        }
        h1, h2, h3 {
            font-family: "Newsreader", Georgia, serif;
            color: var(--ink);
            letter-spacing: -0.02em;
        }
        .hero-shell {
            padding: 0.95rem 1.05rem;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: var(--surface);
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }
        .eyebrow {
            font-size: 0.74rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--accent-soft);
            margin-bottom: 0.35rem;
        }
        .hero-title {
            font-size: 1.75rem;
            line-height: 1;
            margin: 0;
        }
        .hero-copy {
            max-width: 42rem;
            margin-top: 0.45rem;
            color: var(--muted);
            line-height: 1.62;
            font-size: 0.98rem;
        }
        .app-nav {
            margin: 0.15rem 0 1rem;
            color: var(--muted);
            font-size: 0.96rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem 0.9rem;
        }
        .app-nav a {
            color: var(--accent);
            text-decoration: none;
        }
        .stApp a {
            color: var(--accent);
        }
        .stApp a:hover {
            color: var(--accent-soft);
        }
        .summary-card {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            padding: 1rem 1.05rem;
            margin-bottom: 0.8rem;
            min-height: 100%;
            box-shadow: var(--shadow);
        }
        .summary-card strong {
            display: block;
            margin-bottom: 0.3rem;
            color: var(--muted);
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 600;
        }
        [data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            padding: 0.9rem 0.95rem;
            box-shadow: var(--shadow);
        }
        [data-testid="stMetric"] *,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            color: var(--ink) !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--muted) !important;
        }
        [data-testid="stMetricValue"] {
            font-family: "Newsreader", Georgia, serif !important;
            font-size: 2rem !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            box-shadow: var(--shadow);
        }
        [data-testid="stExpander"] *,
        [data-testid="stExpanderDetails"] *,
        [data-testid="stExpanderSummary"] * {
            color: var(--ink) !important;
        }
        [data-testid="stExpander"] details > summary,
        [data-testid="stExpander"] summary {
            background: var(--surface-strong) !important;
            border-radius: 14px;
        }
        .stApp [data-testid="stExpanderDetails"] {
            background: var(--surface) !important;
        }
        .stApp [data-baseweb="input"],
        .stApp [data-baseweb="base-input"],
        .stApp [data-baseweb="select"],
        .stApp [data-baseweb="textarea"],
        .stApp [role="listbox"],
        .stApp [role="option"],
        .stApp [role="radiogroup"],
        .stApp [data-testid="stTextInput"],
        .stApp [data-testid="stMultiSelect"],
        .stApp [data-testid="stSelectbox"],
        .stApp [data-testid="stRadio"],
        .stApp [data-testid="stSlider"] {
            color: var(--ink);
        }
        .stApp [data-baseweb="input"] *,
        .stApp [data-baseweb="base-input"] *,
        .stApp [data-baseweb="select"] *,
        .stApp [data-baseweb="textarea"] *,
        .stApp [role="radiogroup"] *,
        .stApp [role="option"] *,
        .stApp [data-testid="stTextInput"] *,
        .stApp [data-testid="stMultiSelect"] *,
        .stApp [data-testid="stSelectbox"] *,
        .stApp [data-testid="stRadio"] *,
        .stApp [data-testid="stSlider"] * {
            color: var(--ink) !important;
        }
        .stApp [data-baseweb="input"] > div,
        .stApp [data-baseweb="base-input"] > div,
        .stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="textarea"] > div,
        .stApp [data-baseweb="select"] [role="combobox"],
        .stApp [data-baseweb="select"] [data-testid="stSelectbox"],
        .stApp [data-baseweb="textarea"] textarea,
        .stApp [data-baseweb="base-input"] input {
            background: var(--surface-strong) !important;
            border-radius: 0.95rem !important;
        }
        .stApp [data-baseweb="input"] > div,
        .stApp [data-baseweb="base-input"] > div,
        .stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="textarea"] > div {
            border: 1px solid var(--line-strong) !important;
            box-shadow: none !important;
        }
        .stApp [data-baseweb="select"] svg {
            fill: var(--muted) !important;
        }
        .stApp input,
        .stApp textarea,
        .stApp select {
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink);
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
            color: #7a858b !important;
            -webkit-text-fill-color: #7a858b;
        }
        .stApp button {
            color: var(--ink);
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 999px;
            border: 1px solid var(--line-strong);
            background: var(--surface);
            color: var(--ink);
            padding: 0.48rem 1rem;
            font-weight: 600;
        }
        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: var(--accent);
            color: #f8f5ee;
            border-color: var(--accent);
        }
        .stRadio [role="radiogroup"] {
            gap: 0.45rem;
        }
        .stRadio [role="radio"] {
            border: 1px solid var(--line);
            border-radius: 999px;
            background: var(--surface);
            padding: 0.35rem 0.75rem;
        }
        .stApp [data-testid="stDataFrame"],
        .stApp [data-testid="stTable"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
            background: var(--surface);
            box-shadow: var(--shadow);
        }
        .stApp [data-testid="stDataFrame"] *,
        .stApp [data-testid="stTable"] * {
            color: var(--ink) !important;
        }
        .stApp [data-testid="stDataFrame"] [role="columnheader"],
        .stApp [data-testid="stDataFrame"] [role="gridcell"],
        .stApp [data-testid="stDataFrame"] [role="rowheader"],
        .stApp [data-testid="stTable"] table th,
        .stApp [data-testid="stTable"] table td {
            background: var(--surface-strong) !important;
            color: var(--ink) !important;
            border-color: var(--line) !important;
        }
        .stApp [data-testid="stAlert"] {
            background: var(--surface) !important;
            border: 1px solid var(--line) !important;
            color: var(--ink) !important;
            border-radius: 16px !important;
        }
        .stApp [data-testid="stAlert"] * {
            color: var(--ink) !important;
        }
        .stApp [data-testid="stCodeBlock"],
        .stApp [data-testid="stCodeBlock"] *,
        .stApp pre,
        .stApp pre *,
        .stApp code,
        .stApp code * {
            background: var(--surface-strong) !important;
            color: var(--ink) !important;
        }
        .stApp [data-baseweb="popover"],
        .stApp [role="tooltip"],
        .stApp [role="listbox"] {
            background: var(--surface-strong) !important;
            color: var(--ink) !important;
            border: 1px solid var(--line) !important;
            box-shadow: var(--shadow) !important;
        }
        @media (max-width: 820px) {
            .hero-shell {
                padding: 1rem 1rem 1.05rem;
            }
            .hero-title {
                font-size: 1.5rem;
            }
            .hero-copy {
                font-size: 0.98rem;
            }
            .block-container {
                padding-left: 0.95rem;
                padding-right: 0.95rem;
            }
            .app-nav {
                font-size: 0.9rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_json(value: Any) -> Any:
    if value is None or value == "":
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return []


def query_param(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def set_query_params(**kwargs: str) -> None:
    clean = {key: value for key, value in kwargs.items() if value}
    st.query_params.clear()
    for key, value in clean.items():
        st.query_params[key] = value


def sync_from_query(key: str, value: Any, marker: str) -> None:
    if st.session_state.get(marker, object()) != value:
        st.session_state[key] = value
        st.session_state[marker] = value


def ensure_widget_state(key: str, value: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def analytics_enabled() -> bool:
    return bool(POSTHOG_KEY)


def app_distinct_id() -> str:
    ensure_widget_state("_analytics_distinct_id", str(uuid.uuid4()))
    return str(st.session_state["_analytics_distinct_id"])


def posthog_capture(event: str, properties: dict[str, Any]) -> bool:
    if not analytics_enabled():
        return False
    payload = {
        "api_key": POSTHOG_KEY,
        "distinct_id": app_distinct_id(),
        "event": event,
        "properties": {
            "source": "frontiergraph_app",
            "$process_person_profile": False,
            **properties,
        },
    }
    request = urllib.request.Request(
        f"{POSTHOG_HOST}/i/v0/e/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=4):
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def track_once(state_key: str, event: str, properties: dict[str, Any]) -> None:
    signature = json.dumps(properties, sort_keys=True, default=str)
    if st.session_state.get(state_key) == signature:
        return
    posthog_capture(event, properties)
    st.session_state[state_key] = signature


def choose_db_path() -> str:
    env_db = os.environ.get("ECON_OPPORTUNITY_DB", "").strip()
    if env_db and bundle_is_usable(Path(env_db)):
        return env_db
    if bundle_is_usable(DEFAULT_DB):
        return str(DEFAULT_DB)
    if bundle_is_usable(LEGACY_DEFAULT_DB):
        return str(LEGACY_DEFAULT_DB)
    if FALLBACK_DB.exists():
        return str(FALLBACK_DB)
    return str(DEFAULT_DB)


def bundle_is_usable(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with sqlite3.connect(path) as conn:
            top_questions = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='top_questions'").fetchone()
            questions = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='questions'").fetchone()
            if not top_questions or not questions or top_questions[0] <= 0 or questions[0] <= 0:
                return False
            counts = conn.execute("SELECT (SELECT count(*) FROM top_questions), (SELECT count(*) FROM questions)").fetchone()
            return bool(counts and counts[0] > 0 and counts[1] > 0)
    except sqlite3.DatabaseError:
        return False


def query_df(db_path: str, sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(show_spinner=False)
def load_release_meta(db_path: str) -> dict[str, str]:
    try:
        with connect_readonly(db_path) as conn:
            rows = conn.execute("SELECT key, value FROM release_meta").fetchall()
    except sqlite3.Error:
        return {}
    return {str(key): str(value) for key, value in rows}


@st.cache_data(show_spinner=False)
def load_release_metrics(db_path: str) -> dict[str, int]:
    try:
        with connect_readonly(db_path) as conn:
            rows = conn.execute("SELECT key, value FROM release_metrics").fetchall()
    except sqlite3.Error:
        return {}
    return {str(key): int(value) for key, value in rows}


@st.cache_data(show_spinner="Loading question candidates...")
def load_questions(db_path: str) -> pd.DataFrame:
    df = query_df(
        db_path,
        """
        SELECT *
        FROM questions
        ORDER BY score DESC, public_specificity_score DESC, pair_key
        """,
    )
    if df.empty:
        return df
    for column in ["score", "base_score", "duplicate_penalty", "path_support_norm", "gap_bonus", "public_specificity_score"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["mediator_count", "motif_count", "cooc_count", "supporting_path_count", "cross_field"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    df["display_priority"] = (
        df["score"].fillna(0.0)
        + 0.05 * df["public_specificity_score"].fillna(0.0)
        + 0.01 * df["supporting_path_count"].fillna(0)
    )
    df = df.sort_values(by=["display_priority", "score", "pair_key"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_concepts(db_path: str) -> pd.DataFrame:
    df = query_df(db_path, "SELECT * FROM concepts ORDER BY weighted_degree DESC, concept_id")
    if df.empty:
        return df
    for column in ["instance_support", "distinct_paper_support", "in_degree", "out_degree", "neighbor_count"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    for column in ["weighted_degree", "pagerank"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    return df


@st.cache_data(show_spinner=False)
def load_question_bundle(db_path: str, pair_key: str) -> dict[str, Any]:
    question_df = query_df(db_path, "SELECT * FROM questions WHERE pair_key = ? LIMIT 1", (pair_key,))
    mediators = query_df(
        db_path,
        """
        SELECT pair_key, rank, mediator_concept_id, mediator_label, mediator_baseline_label, score
        FROM question_mediators
        WHERE pair_key = ?
        ORDER BY rank
        LIMIT 25
        """,
        (pair_key,),
    )
    paths = query_df(
        db_path,
        """
        SELECT pair_key, rank, path_len, path_score, path_text, path_nodes_json, path_labels_json, path_baseline_labels_json
        FROM question_paths
        WHERE pair_key = ?
        ORDER BY rank
        LIMIT 20
        """,
        (pair_key,),
    )
    papers = query_df(
        db_path,
        """
        SELECT
            pair_key,
            path_rank,
            paper_rank,
            paper_id,
            title,
            year,
            edge_src_label,
            edge_src_baseline_label,
            edge_dst_label,
            edge_dst_baseline_label
        FROM question_papers
        WHERE pair_key = ?
        ORDER BY path_rank, paper_rank
        LIMIT 150
        """,
        (pair_key,),
    )
    neighborhoods = query_df(
        db_path,
        """
        SELECT pair_key, source_out_neighbors_json, target_in_neighbors_json
        FROM question_neighborhoods
        WHERE pair_key = ?
        LIMIT 1
        """,
        (pair_key,),
    )
    return {
        "question": question_df.iloc[0] if not question_df.empty else None,
        "mediators": mediators,
        "paths": paths,
        "papers": papers,
        "neighborhoods": neighborhoods.iloc[0] if not neighborhoods.empty else None,
    }


@st.cache_data(show_spinner=False)
def load_concept_bundle(db_path: str, concept_id: str) -> dict[str, Any]:
    concept_df = query_df(db_path, "SELECT * FROM concepts WHERE concept_id = ? LIMIT 1", (concept_id,))
    neighbors = query_df(
        db_path,
        """
        SELECT concept_id, direction, rank_for_concept, neighbor_concept_id, label, support_count, distinct_papers, avg_stability
        FROM concept_neighbors
        WHERE concept_id = ?
        ORDER BY direction, rank_for_concept
        LIMIT 45
        """,
        (concept_id,),
    )
    opportunities = query_df(
        db_path,
        """
        SELECT concept_id, rank_for_concept, pair_key, score, source_label, target_label, row_json
        FROM concept_opportunities
        WHERE concept_id = ?
        ORDER BY rank_for_concept
        LIMIT 24
        """,
        (concept_id,),
    )
    return {
        "concept": concept_df.iloc[0] if not concept_df.empty else None,
        "neighbors": neighbors,
        "opportunities": opportunities,
    }


def label_for_question(row: pd.Series) -> str:
    source_label = str(row.get("source_display_label") or row.get("source_label") or "").strip()
    target_label = str(row.get("target_display_label") or row.get("target_label") or "").strip()
    if source_label and target_label:
        return f"{source_label} and {target_label}"
    return str(row.get("public_pair_label") or f"{row.get('source_label', '')} and {row.get('target_label', '')}")


def question_option_label(row: pd.Series) -> str:
    return f"{label_for_question(row)}"


def concept_option_label(row: pd.Series) -> str:
    subtitle = str(row.get("subtitle") or "").strip()
    if subtitle:
        return f"{row['plain_label']} | {subtitle}"
    return str(row["plain_label"])


CLIMATE_TERMS = (
    "climate",
    "carbon",
    "co2",
    "emission",
    "pollution",
    "environment",
    "ecological",
    "energy",
    "oil",
    "gas",
    "electricity",
    "renewable",
)


def question_text_blob(row: pd.Series | dict[str, Any]) -> str:
    return " ".join(
        str(value or "").lower()
        for value in (
            row.get("public_pair_label"),
            row.get("source_display_label"),
            row.get("target_display_label"),
            row.get("source_label"),
            row.get("target_label"),
            row.get("why_now"),
            row.get("question_family"),
        )
    )


def question_is_climate_heavy(row: pd.Series | dict[str, Any]) -> bool:
    haystack = question_text_blob(row)
    return any(term in haystack for term in CLIMATE_TERMS)


def plain_direct_status(value: Any) -> str:
    text = str(value or "").strip()
    mapping = {
        "No direct papers yet in the current public sample": "No exact released paper yet",
        "No direct papers yet in the current public release": "No exact released paper yet",
        "A few direct papers in the current public sample": "A few exact released papers",
        "A few direct papers already exist in the current public release": "A few exact released papers",
        "Direct literature exists in the current public sample": "Direct released papers exist",
        "Direct literature already exists in the current public release": "Direct released papers exist",
    }
    return mapping.get(text, text)


def shortlist_csv(filtered_df: pd.DataFrame) -> str:
    columns = [
        "pair_key",
        "public_pair_label",
        "score",
        "base_score",
        "direct_link_status",
        "recommended_move",
        "mediator_count",
        "motif_count",
        "cooc_count",
    ]
    return filtered_df.loc[:, columns].to_csv(index=False)


def plain_recommended_move(value: Any) -> str:
    text = str(value or "").strip()
    mapping = {
        "Direct empirical test": "A direct empirical test looks like the natural next step.",
        "Focused empirical test": "A focused empirical test looks like the natural next step.",
        "Scoping review before a bridge paper": "Start with a short review or pilot that follows the nearby links between the two topics.",
        "Seminar seed or targeted replication map": "This looks most useful as a seminar seed or a targeted replication map.",
        "Synthesis plus pilot design": "A synthesis paper plus a small pilot design looks like a sensible first move.",
        "Bridge paper across literatures": "A paper that follows the nearby links between the two topics looks like the natural next step.",
        "This looks ready for a direct empirical follow-through.": "A direct empirical test looks like the natural next step.",
        "Treat this as a missing direct test, not a settled result.": "Treat this as an open direct question, not a settled result.",
        "Use this as a focused follow-up question in the nearby literature.": "Use this as a focused follow-up question around the nearby papers.",
        "Start with a bridge review or cross-field pilot.": "Start with a short review or pilot that follows the nearby links between the two topics.",
    }
    return mapping.get(text, text)


def question_surface_summary(row: pd.Series | dict[str, Any]) -> str:
    path_count = int(row.get("supporting_path_count") or 0)
    mediator_count = int(row.get("mediator_count") or 0)
    cross_field = bool(row.get("cross_field"))
    common_contexts = str(row.get("common_contexts") or "").strip()
    pieces: list[str] = []
    if path_count and mediator_count:
        pieces.append(
            f"{format(path_count, ',')} nearby paths and {format(mediator_count, ',')} intermediate topics already connect the two sides in the public release."
        )
    elif path_count:
        pieces.append(f"{format(path_count, ',')} nearby paths already connect the two sides in the public release.")
    elif mediator_count:
        pieces.append(f"{format(mediator_count, ',')} intermediate topics already connect the two sides in the public release.")
    if cross_field:
        pieces.append("It bridges areas that are often read separately.")
    if common_contexts:
        pieces.append(common_contexts[0].upper() + common_contexts[1:])
    return " ".join(pieces[:3]) or "This question already sits near directed links and papers in the public release."


def question_is_broader_project(row: pd.Series | dict[str, Any]) -> bool:
    recommended_move = str(row.get("recommended_move") or "").lower()
    if any(term in recommended_move for term in ("bridge", "review", "synthesis", "seminar", "pilot")):
        return True
    mediator_count = int(row.get("mediator_count") or 0)
    supporting_path_count = int(row.get("supporting_path_count") or 0)
    motif_count = int(row.get("motif_count") or 0)
    return mediator_count >= 6 or supporting_path_count >= 8 or motif_count >= 5


def question_project_shape(row: pd.Series | dict[str, Any]) -> str:
    return "Broader project" if question_is_broader_project(row) else "Focused question"


def ordered_frame(frame: pd.DataFrame, preferred: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    columns = [column for column in preferred if column in frame.columns]
    columns.extend(column for column in frame.columns if column not in columns)
    return frame.loc[:, columns]


def series_display_frame(row: pd.Series | None, preferred: list[str]) -> pd.DataFrame:
    if row is None:
        return pd.DataFrame()
    payload = {
        key: (value.item() if hasattr(value, "item") else value)
        for key, value in row.to_dict().items()
    }
    return ordered_frame(pd.DataFrame([payload]), preferred)


def key_value_frame(payload: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "field": key,
            "value": value.item() if hasattr(value, "item") else value,
        }
        for key, value in payload.items()
    ]
    return pd.DataFrame(rows)


def mediator_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return ordered_frame(
        frame,
        ["rank", "mediator_label", "score", "mediator_baseline_label", "mediator_concept_id", "pair_key"],
    )


def path_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    display = frame.copy()
    display["path_labels"] = display["path_labels_json"].map(
        lambda value: " -> ".join(parse_json(value)) if parse_json(value) else ""
    )
    display["baseline_path_labels"] = display["path_baseline_labels_json"].map(
        lambda value: " -> ".join(parse_json(value)) if parse_json(value) else ""
    )
    return ordered_frame(
        display,
        [
            "rank",
            "path_len",
            "path_score",
            "path_text",
            "path_labels",
            "baseline_path_labels",
            "path_nodes_json",
            "path_labels_json",
            "path_baseline_labels_json",
            "pair_key",
        ],
    )


def paper_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return ordered_frame(
        frame,
        [
            "path_rank",
            "paper_rank",
            "title",
            "year",
            "edge_src_label",
            "edge_dst_label",
            "edge_src_baseline_label",
            "edge_dst_baseline_label",
            "paper_id",
            "pair_key",
        ],
    )


def question_row_display_frame(row: pd.Series | None) -> pd.DataFrame:
    return series_display_frame(
        row,
        [
            "public_pair_label",
            "source_display_label",
            "target_display_label",
            "why_now",
            "recommended_move",
            "direct_link_status",
            "question_family",
            "score",
            "base_score",
            "public_specificity_score",
            "supporting_path_count",
            "mediator_count",
            "cooc_count",
            "motif_count",
            "cross_field",
            "common_contexts",
            "source_label",
            "target_label",
            "source_concept_id",
            "target_concept_id",
            "pair_key",
        ],
    )


def concept_row_display_frame(row: pd.Series | None) -> pd.DataFrame:
    return series_display_frame(
        row,
        [
            "plain_label",
            "subtitle",
            "distinct_paper_support",
            "instance_support",
            "neighbor_count",
            "weighted_degree",
            "pagerank",
            "in_degree",
            "out_degree",
            "concept_id",
        ],
    )


def compact_author_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = [part.strip() for part in re.split(r";|\|", raw) if part.strip()]
    if not parts:
        return raw
    if len(parts) >= 3:
        return f"{parts[0]}, {parts[1]} et al."
    if len(parts) == 2:
        return f"{parts[0]}, {parts[1]}"
    return parts[0]


def paper_preview_frame(papers: pd.DataFrame, limit: int = 3) -> pd.DataFrame:
    if papers.empty:
        return papers
    frame = papers.copy()
    for column in ["path_rank", "paper_rank", "year", "fwci"]:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["path_rank_sort"] = pd.to_numeric(frame["path_rank"], errors="coerce").fillna(9999)
    frame["paper_rank_sort"] = pd.to_numeric(frame["paper_rank"], errors="coerce").fillna(9999)
    frame["year_sort"] = pd.to_numeric(frame["year"], errors="coerce").fillna(0)
    frame["fwci_sort"] = pd.to_numeric(frame["fwci"], errors="coerce").fillna(-1.0)
    frame = frame.sort_values(
        by=["path_rank_sort", "paper_rank_sort", "fwci_sort", "year_sort"],
        ascending=[True, True, False, False],
        kind="mergesort",
    )
    frame = frame.drop_duplicates(subset=["paper_id"], keep="first")
    return frame.head(limit)


def paper_preview_metadata(row: pd.Series | dict[str, Any]) -> tuple[str, str]:
    year = row.get("year")
    year_text = str(int(year)) if pd.notna(year) and str(year).strip() else ""
    authors_text = compact_author_text(row.get("authors"))
    venue_text = str(row.get("venue") or row.get("journal") or row.get("source_display_name") or "").strip()
    edge_text = f"{str(row.get('edge_src_label') or '').strip()} -> {str(row.get('edge_dst_label') or '').strip()}".strip(" ->")
    top_line = " · ".join([part for part in [year_text, authors_text, venue_text] if part])
    return top_line, edge_text


QUESTION_SUGGESTION_TERMS = (
    "public debt",
    "urbanization",
    "monetary policy",
    "trade liberalisation",
    "education",
    "wage inequality",
    "financial development",
)


TOPIC_SUGGESTION_LABELS = (
    "public debt",
    "inflation",
    "monetary policy",
    "education",
    "urbanization",
    "trade openness",
    "financial development",
)


def suggested_question_rows(questions: pd.DataFrame, limit: int = 4) -> list[pd.Series]:
    candidate_frame = diversified_question_preview(questions, max(limit * 8, 40))
    chosen: list[pd.Series] = []
    seen: set[str] = set()
    for term in QUESTION_SUGGESTION_TERMS:
        for _, row in candidate_frame.iterrows():
            pair_key = str(row["pair_key"])
            if pair_key in seen:
                continue
            if term in str(row.get("public_pair_label") or "").lower():
                chosen.append(row)
                seen.add(pair_key)
                break
        if len(chosen) >= limit:
            return chosen
    for _, row in candidate_frame.iterrows():
        pair_key = str(row["pair_key"])
        if pair_key in seen:
            continue
        chosen.append(row)
        seen.add(pair_key)
        if len(chosen) >= limit:
            break
    return chosen


def suggested_topic_rows(concepts: pd.DataFrame, limit: int = 5) -> list[pd.Series]:
    chosen: list[pd.Series] = []
    seen: set[str] = set()
    top = concepts.head(220).reset_index(drop=True)
    for label in TOPIC_SUGGESTION_LABELS:
        match = top[
            top["plain_label"].fillna("").str.strip().str.lower().eq(label)
            | top["label"].fillna("").str.strip().str.lower().eq(label)
        ]
        if match.empty:
            continue
        row = match.iloc[0]
        concept_id = str(row["concept_id"])
        if concept_id in seen:
            continue
        chosen.append(row)
        seen.add(concept_id)
        if len(chosen) >= limit:
            return chosen
    for _, row in top.iterrows():
        concept_id = str(row["concept_id"])
        if concept_id in seen:
            continue
        chosen.append(row)
        seen.add(concept_id)
        if len(chosen) >= limit:
            break
    return chosen


def question_brief_markdown(question: pd.Series, mediators: pd.DataFrame, papers: pd.DataFrame, paths: pd.DataFrame) -> str:
    mediator_lines = [
        f"- {row.mediator_label} (rank {int(row.rank)}, score {float(row.score):.1f})"
        for row in mediators.head(6).itertuples(index=False)
    ]
    paper_lines = [
        (
            lambda top_line, edge_line: f"- {row.title}"
            + (f" ({top_line})" if top_line else "")
            + (f" [{edge_line}]" if edge_line else "")
        )(*paper_preview_metadata(row._asdict()))
        for row in paper_preview_frame(papers, limit=6).itertuples(index=False)
    ]
    path_lines = [
        f"- {row.path_text}"
        for row in paths.head(5).itertuples(index=False)
    ]
    parts = [
        f"# {label_for_question(question)}",
        "",
        f"Exact released papers: {plain_direct_status(question['direct_link_status'])}",
        f"Suggested first step: {plain_recommended_move(question['recommended_move'])}",
        "",
        "## Why this question is on the list",
        question_surface_summary(question),
        "",
        "## Intermediate topics already nearby",
        *(mediator_lines or ["- No stable intermediate-topic preview in the public release."]),
        "",
        "## Papers to begin with",
        *(paper_lines or ["- No paper list was exported for this question in the public release."]),
        "",
        "## Supporting paths",
        *(path_lines or ["- No supporting paths were exported for this question in the public release."]),
        "",
        "Source: FrontierGraph public release",
    ]
    return "\n".join(parts)


def render_summary_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="summary-card"><strong>{title}</strong><div>{body}</div></div>',
        unsafe_allow_html=True,
    )


def top_value_labels(value: Any, *, limit: int = 4) -> list[str]:
    labels: list[str] = []
    for item in parse_json(value)[:limit]:
        if isinstance(item, dict):
            text = str(item.get("value", "")).strip()
        else:
            text = str(item).strip()
        if text:
            labels.append(text)
    return labels


def feedback_mailto_link(surface: str, feedback_type: str, message: str, email: str, context: dict[str, Any]) -> str:
    subject = urllib.parse.quote(f"FrontierGraph feedback: {surface}")
    context_lines = [f"{key}: {value}" for key, value in context.items() if value]
    body_parts = [
        f"Surface: {surface}",
        f"Type: {feedback_type}",
        *(context_lines or []),
        "",
        message or "(No message entered)",
    ]
    if email.strip():
        body_parts.extend(["", f"Reply email: {email.strip()}"])
    body = urllib.parse.quote("\n".join(body_parts))
    return f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"


def render_feedback_box(surface: str, context: dict[str, Any]) -> None:
    with st.expander("Give feedback", expanded=False):
        st.caption("Tell me what was confusing, what worked, or what would make this more useful.")
        feedback_type = st.selectbox(
            "Feedback type",
            options=["Something was unclear", "Bug or broken flow", "Idea or request"],
            key=f"feedback-type-{surface}",
        )
        message = st.text_area(
            "Your feedback",
            key=f"feedback-message-{surface}",
            placeholder="What were you trying to do, and what got in the way?",
            height=120,
        )
        email = st.text_input(
            "Optional email",
            key=f"feedback-email-{surface}",
            placeholder="If you'd like a reply",
        )
        if st.button("Submit feedback", key=f"feedback-submit-{surface}", use_container_width=True):
            if not message.strip():
                st.warning("Add a short note before submitting feedback.")
                return
            payload = {
                "surface": surface,
                "feedback_type": feedback_type,
                "message": message.strip(),
                "reply_email": email.strip(),
                **context,
            }
            if analytics_enabled():
                posthog_capture("feedback_submitted", payload)
                st.success("Thanks. Your feedback was recorded.")
            else:
                st.info("Analytics feedback capture is not configured yet. You can still send this by email below.")
        mailto_link = feedback_mailto_link(surface, feedback_type, message.strip(), email.strip(), context)
        st.markdown(f"[Send by email instead]({mailto_link})")


def question_filter_frame(
    questions: pd.DataFrame,
    search: str,
    direct_filters: list[str],
    only_cross_field: bool,
    broader_project_only: bool,
) -> pd.DataFrame:
    filtered = questions.copy()
    if search.strip():
        needle = search.strip().lower()
        filtered = filtered[
            filtered["public_pair_label"].str.lower().str.contains(needle, na=False)
            | filtered["source_display_label"].fillna("").str.lower().str.contains(needle, na=False)
            | filtered["target_display_label"].fillna("").str.lower().str.contains(needle, na=False)
            | filtered["source_label"].str.lower().str.contains(needle, na=False)
            | filtered["target_label"].str.lower().str.contains(needle, na=False)
            | filtered["why_now"].str.lower().str.contains(needle, na=False)
        ]
    if direct_filters:
        filtered = filtered[filtered["direct_link_status"].isin(direct_filters)]
    if only_cross_field:
        filtered = filtered[filtered["cross_field"] == 1]
    if broader_project_only:
        filtered = filtered[filtered.apply(question_is_broader_project, axis=1)]
    return filtered.reset_index(drop=True)


def diversified_question_preview(questions: pd.DataFrame, limit: int) -> pd.DataFrame:
    if questions.empty:
        return questions

    visible_rows: list[dict[str, Any]] = []
    deferred_rows: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    climate_count = 0
    climate_cap = max(1, limit // 6)

    for row in questions.itertuples(index=False):
        payload = row._asdict()
        family = str(payload.get("question_family") or payload.get("pair_key") or "")
        is_climate = question_is_climate_heavy(payload)
        if family_counts.get(family, 0) >= 1 or (is_climate and climate_count >= climate_cap):
            deferred_rows.append(payload)
            continue
        visible_rows.append(payload)
        family_counts[family] = family_counts.get(family, 0) + 1
        if is_climate:
            climate_count += 1
        if len(visible_rows) >= limit:
            break

    if len(visible_rows) < limit:
        seen_pairs = {str(row["pair_key"]) for row in visible_rows}
        for payload in deferred_rows:
            if str(payload.get("pair_key")) in seen_pairs:
                continue
            if question_is_climate_heavy(payload) and climate_count >= climate_cap:
                continue
            visible_rows.append(payload)
            if question_is_climate_heavy(payload):
                climate_count += 1
            if len(visible_rows) >= limit:
                break

    return pd.DataFrame(visible_rows)


def preferred_question_pair(questions: pd.DataFrame) -> str:
    if questions.empty:
        return ""

    preferred_terms = ("urbanization", "consumer demand", "wage inequality", "international sanctions", "public debt")
    for row in questions.itertuples(index=False):
        payload = row._asdict()
        label = str(payload.get("public_pair_label") or "").lower()
        if any(term in label for term in preferred_terms) and not question_is_climate_heavy(payload):
            return str(payload["pair_key"])

    for row in questions.itertuples(index=False):
        payload = row._asdict()
        if not question_is_climate_heavy(payload):
            return str(payload["pair_key"])

    return str(questions.iloc[0]["pair_key"])


def render_question_detail(db_path: str, pair_key: str, concept_lookup: dict[str, str]) -> None:
    bundle = load_question_bundle(db_path, pair_key)
    question = bundle["question"]
    if question is None:
        st.warning("That question was not found in the public bundle.")
        return

    mediators = bundle["mediators"]
    paths = bundle["paths"]
    papers = bundle["papers"]
    neighborhoods = bundle["neighborhoods"]

    st.markdown(f"## {label_for_question(question)}")
    st.markdown(question_surface_summary(question))

    summary_cols = st.columns(2)
    with summary_cols[0]:
        mediator_labels = [str(row.mediator_label) for row in mediators.head(5).itertuples(index=False)]
        render_summary_card(
            "Intermediate topics",
            ", ".join(mediator_labels) if mediator_labels else "No stable intermediate-topic summary was exported for this question.",
        )
    with summary_cols[1]:
        render_summary_card("What to do first", plain_recommended_move(question.get("recommended_move", "")))

    metrics_cols = st.columns(3)
    metrics_cols[0].metric("Intermediate topics", f"{int(question['mediator_count'])}")
    metrics_cols[1].metric("Supporting paths", f"{int(question['supporting_path_count'])}")
    metrics_cols[2].metric("Project shape", question_project_shape(question))
    if str(question.get("common_contexts") or "").strip():
        st.caption(str(question.get("common_contexts")))
    else:
        st.caption("All counts refer to the public release, not the full economics literature.")

    detail_cols = st.columns(2)
    with detail_cols[0]:
        st.markdown("### Supporting paths")
        path_rows = paths.head(3)
        if path_rows.empty:
            st.caption("No supporting paths were exported for this question in the public release.")
        else:
            st.caption("These are the clearest local routes already tying the two sides together in the release graph.")
            st.caption("Higher path scores mean stronger local support for this question. Compare the scores within this question rather than across unrelated questions.")
            for row in path_rows.itertuples(index=False):
                labels = parse_json(row.path_labels_json)
                path_text = " -> ".join(labels) if labels else str(row.path_text or "")
                with st.container(border=True):
                    st.caption(f"Path {int(row.rank)}")
                    st.markdown(f"**{path_text}**")
                    st.caption(f"Path score {float(row.path_score):.1f}")

    papers_preview = paper_preview_frame(papers, limit=3)
    with detail_cols[1]:
        st.markdown("### Papers to begin with")
        if papers_preview.empty:
            st.caption("No paper list was exported for this question in the public release.")
        else:
            for row in papers_preview.itertuples(index=False):
                top_line, edge_line = paper_preview_metadata(row._asdict())
                with st.container(border=True):
                    st.markdown(f"**{row.title}**")
                    if top_line:
                        st.caption(top_line)
                    if edge_line:
                        st.caption(edge_line)

    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("Open compare workspace", key=f"question-open-compare-{pair_key}", use_container_width=True):
            st.session_state["compare_mode"] = "Questions"
            st.session_state["question_compare_pairs"] = [pair_key]
            set_query_params(view="compare", pairs=pair_key)
            st.rerun()
    with action_cols[1]:
        if st.button("Open raw tables", key=f"question-open-advanced-{pair_key}", use_container_width=True):
            set_query_params(view="advanced", pair=pair_key)
            st.rerun()

    brief = question_brief_markdown(question, mediators, papers, paths)
    with action_cols[2]:
        st.download_button(
            "Export question brief",
            data=brief,
            file_name=f"frontiergraph_{pair_key}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with st.expander("Technical tables", expanded=False):
        st.caption("These raw tables show the exported evidence behind the selected question, with readable labels shown before internal identifiers.")
        st.markdown("**Top intermediate topics**")
        st.caption("These are the intermediate topics that most clearly connect the two sides in the local graph.")
        st.dataframe(mediator_display_frame(mediators), use_container_width=True, hide_index=True)

        path_frame = path_display_frame(paths)
        if not path_frame.empty:
            st.markdown("**Supporting paths**")
            st.caption("These rows show the exported path objects, including the label sequence and the path score used to order them locally.")
            st.dataframe(
                path_frame,
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("**Supporting papers**")
        st.caption("These papers attach to nearby edges and paths and give you a concrete place to start reading.")
        st.dataframe(paper_display_frame(papers), use_container_width=True, hide_index=True)

        if neighborhoods is not None:
            out_neighbors = []
            in_neighbors = []
            for row in parse_json(neighborhoods["source_out_neighbors_json"]):
                neighbor = str(row.get("neighbor", ""))
                out_neighbors.append(
                    {
                        "neighbor": concept_lookup.get(neighbor, neighbor),
                        "count": int(row.get("count", 0)),
                        "weight": float(row.get("weight", 0.0)),
                    }
                )
            for row in parse_json(neighborhoods["target_in_neighbors_json"]):
                neighbor = str(row.get("neighbor", ""))
                in_neighbors.append(
                    {
                        "neighbor": concept_lookup.get(neighbor, neighbor),
                        "count": int(row.get("count", 0)),
                        "weight": float(row.get("weight", 0.0)),
                    }
                )
            n_left, n_right = st.columns(2)
            with n_left:
                st.markdown("**Source-side neighborhood**")
                st.dataframe(pd.DataFrame(out_neighbors), use_container_width=True, hide_index=True)
            with n_right:
                st.markdown("**Target-side neighborhood**")
                st.dataframe(pd.DataFrame(in_neighbors), use_container_width=True, hide_index=True)


def render_question_explorer(db_path: str, questions: pd.DataFrame, concept_lookup: dict[str, str]) -> None:
    search_default = query_param("search")
    pair_default = query_param("pair")
    broader_default = query_param("shape") == "broader"
    status_options = sorted(questions["direct_link_status"].dropna().unique().tolist())
    sync_from_query("question_search", search_default, "_sync_question_search")
    sync_from_query("question_cross_only", query_param("cross") == "1", "_sync_question_cross_only")
    sync_from_query("question_broader_project_only", broader_default, "_sync_question_broader_project_only")
    ensure_widget_state("question_exact_filters", status_options)
    ensure_widget_state("question_shortlist_size", 24)
    with st.sidebar:
        st.markdown("### Narrow the shortlist")
        st.markdown(
            '<p class="sidebar-caption">Keep the main panel focused on one question. Narrow by exact papers, cross-area questions, or broader project-shaped questions only when you need to.</p>',
            unsafe_allow_html=True,
        )
        only_cross = st.checkbox("Cross-area only", key="question_cross_only")
        broader_project_only = st.checkbox("Broader project", key="question_broader_project_only")
        with st.expander("Filters", expanded=False):
            direct_filters = st.multiselect(
                "Exact papers",
                options=status_options,
                key="question_exact_filters",
                format_func=plain_direct_status,
            )
            shortlist_size = st.slider("Questions to preview", min_value=12, max_value=80, key="question_shortlist_size", step=6)
    search = st.text_input(
        "Search questions",
        key="question_search",
        placeholder="Search by topic, outcome, or question wording",
    )
    filtered = question_filter_frame(questions, search, direct_filters, only_cross, broader_project_only)

    if filtered.empty:
        st.warning("No question candidates match the current filters.")
        return

    preview = diversified_question_preview(filtered, shortlist_size)
    candidate_frame = diversified_question_preview(filtered, max(shortlist_size, 60))
    candidate_map = {str(row.pair_key): row for row in candidate_frame.itertuples(index=False)}
    default_pair = pair_default if pair_default in candidate_map else preferred_question_pair(candidate_frame)
    sync_from_query("question_selection", default_pair, "_sync_question_selection")
    st.markdown("### Choose a question")
    suggestion_rows = suggested_question_rows(filtered if search.strip() else questions)
    if suggestion_rows and not search.strip():
        st.caption("Try one of these")
        suggestion_columns = st.columns(len(suggestion_rows))
        for column, row in zip(suggestion_columns, suggestion_rows):
            with column:
                if st.button(label_for_question(row), key=f"suggest-question-{row['pair_key']}", use_container_width=True):
                    st.session_state["question_selection"] = str(row["pair_key"])
                    set_query_params(
                        view="question",
                        pair=str(row["pair_key"]),
                        search=search,
                        cross="1" if only_cross else "",
                        shape="broader" if broader_project_only else "",
                    )
                    st.rerun()
    selection = st.selectbox(
        "Question",
        options=list(candidate_map.keys()),
        key="question_selection",
        format_func=lambda value: question_option_label(pd.Series(candidate_map[value]._asdict())),
    )
    if (
        selection != pair_default
        or search != search_default
        or only_cross != (query_param("cross") == "1")
        or broader_project_only != broader_default
    ):
        set_query_params(
            view="question",
            pair=selection,
            search=search,
            cross="1" if only_cross else "",
            shape="broader" if broader_project_only else "",
        )
    with st.sidebar:
        with st.expander("Secondary workspaces", expanded=False):
            if st.button("Open compare workspace", key="sidebar-open-question-compare", use_container_width=True):
                posthog_capture("app_secondary_workspace_opened", {"workspace": "compare", "surface": "question", "pair_key": selection})
                st.session_state["compare_mode"] = "Questions"
                st.session_state["question_compare_pairs"] = [selection]
                set_query_params(view="compare", pairs=selection)
                st.rerun()
            if st.button("Open raw tables for this question", key="sidebar-open-question-advanced", use_container_width=True):
                posthog_capture("app_secondary_workspace_opened", {"workspace": "advanced", "surface": "question", "pair_key": selection})
                set_query_params(view="advanced", pair=selection)
                st.rerun()

    selection_row = pd.Series(candidate_map[selection]._asdict())
    track_once(
        "_analytics_question_selection",
        "app_question_viewed",
        {
            "view": "question",
            "pair_key": selection,
            "question_label": str(selection_row.get("public_pair_label") or ""),
            "cross_field": int(selection_row.get("cross_field") or 0),
            "project_shape": question_project_shape(selection_row),
        },
    )
    render_question_detail(db_path, selection, concept_lookup)
    render_feedback_box(
        "app_question",
        {
            "pair_key": selection,
            "question_label": str(selection_row.get("public_pair_label") or ""),
            "view": "question",
        },
    )

    with st.expander("More questions in this shortlist", expanded=False):
        preview_table = preview.loc[:, ["public_pair_label", "supporting_path_count", "mediator_count", "recommended_move"]].copy()
        preview_table["Nearby support"] = preview_table.apply(
            lambda row: f"{int(row['supporting_path_count'])} supporting paths · {int(row['mediator_count'])} intermediate topics",
            axis=1,
        )
        preview_table["recommended_move"] = preview_table["recommended_move"].map(plain_recommended_move)
        preview_table = preview_table.loc[:, ["public_pair_label", "Nearby support", "recommended_move"]]
        preview_table.columns = ["Question", "Nearby support", "What to inspect first"]
        st.dataframe(preview_table, use_container_width=True, hide_index=True)
        st.download_button(
            "Export shortlist CSV",
            data=shortlist_csv(filtered.head(100)),
            file_name="frontiergraph_shortlist.csv",
            mime="text/csv",
        )


def concept_graphviz(concept: pd.Series, neighbors: pd.DataFrame) -> str:
    concept_label = str(concept.get("plain_label") or concept.get("label"))
    lines = [
        "digraph G {",
        'graph [rankdir=LR, bgcolor="transparent"];',
        'node [shape=ellipse, style=filled, color="#dce7f8", fontname="Helvetica"];',
        f'"{concept_label}" [fillcolor="#8ed0ff", color="#3f79b8"];',
    ]
    for row in neighbors[neighbors["direction"] == "incoming"].head(4).itertuples(index=False):
        lines.append(f'"{row.label}" -> "{concept_label}" [color="#7aa0c3"];')
    for row in neighbors[neighbors["direction"] == "outgoing"].head(4).itertuples(index=False):
        lines.append(f'"{concept_label}" -> "{row.label}" [color="#5c8b77"];')
    lines.append("}")
    return "\n".join(lines)


def render_topic_explorer(db_path: str, concepts: pd.DataFrame) -> None:
    concept_default = query_param("concept")
    search_default = query_param("search")
    sync_from_query("concept_search", search_default, "_sync_concept_search")
    with st.sidebar:
        st.markdown("### Topic notes")
        st.markdown(
            '<p class="sidebar-caption">Use the main panel to choose a topic. This sidebar only holds secondary tools.</p>',
            unsafe_allow_html=True,
        )
    search = st.text_input(
        "Search topics",
        key="concept_search",
        placeholder="Search by topic, alias, or label",
    )
    working = concepts.copy()
    if search.strip():
        needle = search.strip().lower()
        working = working[
            working["plain_label"].str.lower().str.contains(needle, na=False)
            | working["label"].str.lower().str.contains(needle, na=False)
            | working["subtitle"].fillna("").str.lower().str.contains(needle, na=False)
        ]
    if working.empty:
        st.warning("No concepts match that query.")
        return

    top = working.head(150).reset_index(drop=True)
    concept_map = {str(row.concept_id): row for row in top.itertuples(index=False)}
    selected = concept_default if concept_default in concept_map else next(iter(concept_map))
    sync_from_query("concept_selection", selected, "_sync_concept_selection")
    st.markdown("### Choose a topic")
    suggestion_rows = suggested_topic_rows(concepts)
    if suggestion_rows and not search.strip():
        st.caption("Try one of these")
        suggestion_columns = st.columns(len(suggestion_rows))
        for column, row in zip(suggestion_columns, suggestion_rows):
            with column:
                if st.button(str(row["plain_label"] or row["label"]), key=f"suggest-topic-{row['concept_id']}", use_container_width=True):
                    st.session_state["concept_selection"] = str(row["concept_id"])
                    set_query_params(view="concept", concept=str(row["concept_id"]), search=search)
                    st.rerun()
    choice = st.selectbox(
        "Topic",
        options=list(concept_map.keys()),
        key="concept_selection",
        format_func=lambda value: concept_option_label(pd.Series(concept_map[value]._asdict())),
    )
    if choice != concept_default or search != search_default:
        set_query_params(view="concept", concept=choice, search=search)

    bundle = load_concept_bundle(db_path, choice)
    concept = bundle["concept"]
    neighbors = bundle["neighbors"]
    opportunities = bundle["opportunities"]
    if concept is None:
        st.warning("That concept was not found in the public bundle.")
        return

    track_once(
        "_analytics_topic_selection",
        "app_topic_viewed",
        {
            "view": "concept",
            "concept_id": choice,
            "concept_label": str(concept["plain_label"]),
        },
    )

    st.markdown(f"## {concept['plain_label']}")
    if str(concept.get("subtitle", "")).strip():
        st.caption(str(concept["subtitle"]))
    metrics_cols = st.columns(3)
    metrics_cols[0].metric("Topic mentions", f"{int(concept['instance_support']):,}")
    metrics_cols[1].metric("Papers in release", f"{int(concept['distinct_paper_support']):,}")
    metrics_cols[2].metric("Nearby topics", f"{int(concept['neighbor_count']):,}")
    st.caption("These counts refer to the public Frontier Graph release. They describe how this topic sits in the released topic map, not overall importance.")

    summary_cols = st.columns(2)
    with summary_cols[0]:
        render_summary_card(
            "What this topic is",
            str(concept.get("subtitle") or f"This topic appears in {int(concept['distinct_paper_support']):,} released papers."),
        )
    with summary_cols[1]:
        render_summary_card(
            "What to inspect first",
            "Start with the question candidates below, then move through nearby topics if you want a broader local reading.",
        )

    countries = ", ".join(top_value_labels(concept.get("top_countries_json")))
    units = ", ".join(top_value_labels(concept.get("top_units_json")))
    if countries or units:
        render_summary_card("Common contexts", f"Countries: {countries or 'not surfaced'}<br/>Units: {units or 'not surfaced'}")
    st.markdown("### Questions touching this topic")
    if opportunities.empty:
        st.caption("No public question candidates touching this topic are available in the public release.")
    else:
        for row in opportunities.head(5).itertuples(index=False):
            payload = parse_json(row.row_json)
            with st.container(border=True):
                st.markdown(f"**{payload.get('public_pair_label', f'{row.source_label} and {row.target_label}')}**")
                st.caption(question_surface_summary(payload))
                st.write(plain_recommended_move(payload.get("recommended_move", "")))
                if st.button("Open question detail", key=f"open-topic-question-{row.pair_key}"):
                    set_query_params(view="question", pair=str(row.pair_key))
                    st.rerun()

    incoming = neighbors[neighbors["direction"] == "incoming"].head(6)
    outgoing = neighbors[neighbors["direction"] == "outgoing"].head(6)
    st.markdown("### Nearby topics")
    nearby_cols = st.columns(2)
    with nearby_cols[0]:
        st.markdown("**Builds on**")
        if incoming.empty:
            st.caption("No incoming-side topics were exported for this release node.")
        else:
            for row in incoming.itertuples(index=False):
                if st.button(f"{row.label} · {int(row.support_count)} papers", key=f"incoming-{choice}-{row.neighbor_concept_id}", use_container_width=True):
                    set_query_params(view="concept", concept=str(row.neighbor_concept_id))
                    st.rerun()
    with nearby_cols[1]:
        st.markdown("**Leads toward**")
        if outgoing.empty:
            st.caption("No outgoing-side topics were exported for this release node.")
        else:
            for row in outgoing.itertuples(index=False):
                if st.button(f"{row.label} · {int(row.support_count)} papers", key=f"outgoing-{choice}-{row.neighbor_concept_id}", use_container_width=True):
                    set_query_params(view="concept", concept=str(row.neighbor_concept_id))
                    st.rerun()

    st.markdown("### Local map")
    st.caption("Use the local map after you have read the topic summary and question cards. It is there to give local context, not to replace them.")
    try:
        st.graphviz_chart(concept_graphviz(concept, neighbors), use_container_width=True)
    except Exception:
        st.code(concept_graphviz(concept, neighbors))

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Open compare workspace", key=f"topic-open-compare-{choice}", use_container_width=True):
            posthog_capture("app_secondary_workspace_opened", {"workspace": "compare", "surface": "topic", "concept_id": choice})
            st.session_state["compare_mode"] = "Topics"
            st.session_state["compare_concept_ids"] = [choice]
            set_query_params(view="compare")
            st.rerun()
    with action_cols[1]:
        if st.button("Open raw tables", key=f"topic-open-advanced-{choice}", use_container_width=True):
            posthog_capture("app_secondary_workspace_opened", {"workspace": "advanced", "surface": "topic", "concept_id": choice})
            set_query_params(view="advanced", concept=choice)
            st.rerun()

    with st.expander("Technical tables", expanded=False):
        n_left, n_right = st.columns(2)
        with n_left:
            st.markdown("**Incoming topics**")
            st.dataframe(neighbors[neighbors["direction"] == "incoming"].head(10), use_container_width=True, hide_index=True)
        with n_right:
            st.markdown("**Outgoing topics**")
            st.dataframe(neighbors[neighbors["direction"] == "outgoing"].head(10), use_container_width=True, hide_index=True)
    with st.sidebar:
        with st.expander("Secondary workspaces", expanded=False):
            if st.button("Open compare workspace", key="sidebar-open-topic-compare", use_container_width=True):
                posthog_capture("app_secondary_workspace_opened", {"workspace": "compare", "surface": "topic", "concept_id": choice})
                st.session_state["compare_mode"] = "Topics"
                st.session_state["compare_concept_ids"] = [choice]
                set_query_params(view="compare")
                st.rerun()
            if st.button("Open raw tables for this topic", key="sidebar-open-topic-advanced", use_container_width=True):
                posthog_capture("app_secondary_workspace_opened", {"workspace": "advanced", "surface": "topic", "concept_id": choice})
                set_query_params(view="advanced", concept=choice)
                st.rerun()
    render_feedback_box(
        "app_topic",
        {
            "concept_id": choice,
            "concept_label": str(concept["plain_label"]),
            "view": "concept",
        },
    )


def render_compare_workspace(db_path: str, questions: pd.DataFrame, concepts: pd.DataFrame) -> None:
    track_once("_analytics_compare_workspace", "app_secondary_workspace_viewed", {"workspace": "compare"})
    pair_defaults = [value for value in query_param("pairs").split(",") if value]
    sync_from_query("compare_mode", "Questions" if pair_defaults else st.session_state.get("compare_mode", "Questions"), "_sync_compare_mode")
    compare_mode = st.radio("Compare questions or topics", options=["Questions", "Topics"], horizontal=True, key="compare_mode")
    feedback_context = {"workspace": "compare", "mode": compare_mode.lower()}
    if compare_mode == "Questions":
        candidate_map = {str(row.pair_key): row for row in questions.head(150).itertuples(index=False)}
        sync_from_query(
            "compare_question_pairs",
            [value for value in pair_defaults if value in candidate_map][:4],
            "_sync_compare_question_pairs",
        )
        selected = st.multiselect(
            "Choose 2 to 4 questions",
            options=list(candidate_map.keys()),
            key="compare_question_pairs",
            format_func=lambda value: question_option_label(pd.Series(candidate_map[value]._asdict())),
        )
        if selected:
            set_query_params(view="compare", pairs=",".join(selected[:4]))
        if len(selected) < 2:
            st.info("Select at least two questions to compare them side by side.")
            render_feedback_box("app_compare", feedback_context)
            return
        cols = st.columns(len(selected[:4]))
        for col, pair_key in zip(cols, selected[:4]):
            bundle = load_question_bundle(db_path, pair_key)
            question = bundle["question"]
            if question is None:
                continue
            papers = paper_preview_frame(bundle["papers"], limit=3)
            with col:
                st.markdown(f"**{label_for_question(question)}**")
                st.caption(plain_recommended_move(question["recommended_move"]))
                st.write(f"Exact released papers: {int(question['cooc_count'])}")
                st.write(f"Intermediate topics: {int(question['mediator_count'])}")
                if not papers.empty:
                    st.markdown("**Papers to begin with**")
                    for paper in papers.itertuples(index=False):
                        top_line, _edge_line = paper_preview_metadata(paper._asdict())
                        st.markdown(f"- {paper.title}" + (f" ({top_line})" if top_line else ""))
    else:
        concept_map = {str(row.concept_id): row for row in concepts.head(150).itertuples(index=False)}
        ensure_widget_state("compare_concept_ids", [])
        selected = st.multiselect(
            "Choose 2 to 4 topics",
            options=list(concept_map.keys()),
            key="compare_concept_ids",
            format_func=lambda value: concept_option_label(pd.Series(concept_map[value]._asdict())),
        )
        if len(selected) < 2:
            st.info("Select at least two topics to compare them side by side.")
            render_feedback_box("app_compare", feedback_context)
            return
        cols = st.columns(len(selected[:4]))
        for col, concept_id in zip(cols, selected[:4]):
            bundle = load_concept_bundle(db_path, concept_id)
            concept = bundle["concept"]
            neighbors = bundle["neighbors"]
            opportunities = bundle["opportunities"]
            if concept is None:
                continue
            with col:
                st.markdown(f"**{concept['plain_label']}**")
                st.caption(str(concept.get("subtitle", "")))
                st.write(f"Papers in release: {int(concept['distinct_paper_support']):,}")
                st.write(f"Nearby topics: {int(concept['neighbor_count']):,}")
                st.write(f"Nearby question candidates: {len(opportunities):,}")
                if not neighbors.empty:
                    st.markdown("**Nearest neighbors**")
                    for row in neighbors.head(4).itertuples(index=False):
                        st.markdown(f"- {row.label}")
    render_feedback_box("app_compare", feedback_context)


def render_advanced_evidence(db_path: str, questions: pd.DataFrame, concepts: pd.DataFrame) -> None:
    track_once("_analytics_advanced_workspace", "app_secondary_workspace_viewed", {"workspace": "advanced"})
    pair_default = query_param("pair")
    concept_default = query_param("concept")
    question_map = {str(row.pair_key): row for row in questions.head(150).itertuples(index=False)}
    selected_pair = pair_default if pair_default in question_map else next(iter(question_map))
    sync_from_query("advanced_pair", selected_pair, "_sync_advanced_pair")
    choice = st.selectbox(
        "Question for raw evidence",
        options=list(question_map.keys()),
        key="advanced_pair",
        format_func=lambda value: question_option_label(pd.Series(question_map[value]._asdict())),
    )
    concept_map = {str(row.concept_id): row for row in concepts.head(150).itertuples(index=False)}
    selected_concept = concept_default if concept_default in concept_map else next(iter(concept_map))
    sync_from_query("advanced_concept", selected_concept, "_sync_advanced_concept")
    concept_choice = st.selectbox(
        "Inspect one concept row",
        options=list(concept_map.keys()),
        key="advanced_concept",
        format_func=lambda value: concept_option_label(pd.Series(concept_map[value]._asdict())),
    )
    if choice != pair_default or concept_choice != concept_default:
        set_query_params(view="advanced", pair=choice, concept=concept_choice)
    bundle = load_question_bundle(db_path, choice)
    question = bundle["question"]
    st.markdown(f"### Advanced evidence for {label_for_question(question)}")

    with st.expander("Raw question row", expanded=True):
        st.caption("This is the exported question row behind the selected card, with public labels and evidence counts shown before internal keys.")
        st.dataframe(question_row_display_frame(question), use_container_width=True, hide_index=True)

    with st.expander("Mediator table", expanded=False):
        st.caption("These intermediate topics are the main connectors between the two sides of the question in the local graph.")
        st.dataframe(mediator_display_frame(bundle["mediators"]), use_container_width=True, hide_index=True)

    with st.expander("Path table", expanded=False):
        st.caption("These are the exported supporting paths. Path scores tell you how strongly each local route is supported for this question.")
        st.dataframe(path_display_frame(bundle["paths"]), use_container_width=True, hide_index=True)

    with st.expander("Paper table", expanded=False):
        st.caption("These starter papers sit on nearby edges and paths around the selected question.")
        st.dataframe(paper_display_frame(bundle["papers"]), use_container_width=True, hide_index=True)

    with st.expander("Release metadata", expanded=False):
        st.caption("This section shows the release-level metadata and headline counts for the bundle loaded into the app.")
        st.markdown("**Release metadata**")
        st.dataframe(key_value_frame(load_release_meta(db_path)), use_container_width=True, hide_index=True)
        st.markdown("**Release metrics**")
        st.dataframe(key_value_frame(load_release_metrics(db_path)), use_container_width=True, hide_index=True)

    st.markdown("### Concept lookup")
    concept_bundle = load_concept_bundle(db_path, concept_choice)
    if concept_bundle["concept"] is not None:
        st.caption("This is the exported concept row for the selected topic, again with readable fields shown before internal identifiers.")
        st.dataframe(concept_row_display_frame(concept_bundle["concept"]), use_container_width=True, hide_index=True)
    render_feedback_box("app_advanced", {"workspace": "advanced", "pair_key": choice, "concept_id": concept_choice})


def main() -> None:
    st.set_page_config(page_title="Frontier Graph | Explorer", layout="wide", initial_sidebar_state="expanded")
    inject_css()

    db_path = choose_db_path()
    if not Path(db_path).exists():
        st.error(f"Database not found: {db_path}")
        st.stop()

    st.markdown(
        f"""
        <div class="app-nav">
            <a href="{SITE_URL}">Site</a>
            <a href="{QUESTIONS_URL}">Questions</a>
            <a href="{GRAPH_URL}">Graph</a>
            <a href="{PAPER_URL}">Paper</a>
            <a href="{DOWNLOADS_URL}">Downloads</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="eyebrow">Frontier Graph Explorer</div>
            <h1 class="hero-title">Read one question or topic at a time.</h1>
            <p class="hero-copy">
                Start with a question or a topic below. Search and pick one object first; filters and technical tables stay out of the way until you need them.
            </p>
            <p class="hero-copy" style="margin-top: 0.2rem;">
                The public app can take 5 to 10 seconds to load the first time.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        questions = load_questions(db_path)
        concepts = load_concepts(db_path)
    except sqlite3.Error as exc:
        st.error(f"Could not read the configured public bundle: {db_path}")
        st.code(str(exc))
        st.stop()

    if questions.empty or concepts.empty:
        st.error("The canonical public bundle is missing the question-candidate or topic tables.")
        st.stop()

    concept_lookup = {
        str(row.concept_id): str(row.plain_label or row.label)
        for row in concepts.itertuples(index=False)
    }

    view_default = query_param("view") or "question"
    primary_view_keys = ["question", "concept"]
    sync_from_query(
        "primary_view",
        view_default if view_default in primary_view_keys else st.session_state.get("primary_view", "question"),
        "_sync_primary_view",
    )
    active_view = view_default if view_default in {"compare", "advanced"} else st.session_state.get("primary_view", "question")
    previous_primary_view = st.session_state.get("_last_primary_view", st.session_state.get("primary_view", "question"))
    primary_view = st.radio(
        "Start with",
        options=primary_view_keys,
        key="primary_view",
        format_func=lambda value: {"question": "Questions", "concept": "Topics"}[value],
        horizontal=True,
    )
    if active_view in {"compare", "advanced"}:
        if primary_view != previous_primary_view:
            st.session_state["_last_primary_view"] = primary_view
            set_query_params(view=primary_view)
            st.rerun()
        st.caption("You are in a secondary workspace. Use the main picker above to return to questions or topics.")
    elif primary_view != view_default:
        st.session_state["_last_primary_view"] = primary_view
        set_query_params(view=primary_view)
        st.rerun()
    else:
        st.session_state["_last_primary_view"] = primary_view

    if active_view == "question":
        render_question_explorer(db_path, questions, concept_lookup)
    elif active_view == "concept":
        render_topic_explorer(db_path, concepts)
    elif active_view == "compare":
        render_compare_workspace(db_path, questions, concepts)
    else:
        render_advanced_evidence(db_path, questions, concepts)


if __name__ == "__main__":
    main()
