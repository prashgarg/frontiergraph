from __future__ import annotations

import json
import os
import sqlite3
import sys
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
DEFAULT_DB = Path("data/production/frontiergraph_public_release/frontiergraph-economics-public.db")
FALLBACK_DB = Path(
    "data/production/frontiergraph_concept_compare_v1/baseline/suppression/concept_exploratory_suppressed_top100k_app.sqlite"
)


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


def choose_db_path() -> str:
    env_db = os.environ.get("ECON_OPPORTUNITY_DB", "").strip()
    if env_db:
        return env_db
    if DEFAULT_DB.exists():
        return str(DEFAULT_DB)
    if FALLBACK_DB.exists():
        return str(FALLBACK_DB)
    return str(DEFAULT_DB)


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


@st.cache_data(show_spinner="Loading released questions...")
def load_questions(db_path: str) -> pd.DataFrame:
    df = query_df(db_path, "SELECT * FROM questions ORDER BY score DESC, pair_key")
    if df.empty:
        return df
    for column in ["score", "base_score", "duplicate_penalty", "path_support_norm", "gap_bonus"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["mediator_count", "motif_count", "cooc_count", "supporting_path_count", "cross_field"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
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
        SELECT pair_key, rank, mediator_concept_id, mediator_label, score
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
        SELECT pair_key, rank, path_len, path_score, path_text, path_nodes_json, path_labels_json
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
        SELECT pair_key, path_rank, paper_rank, paper_id, title, year, edge_src_label, edge_dst_label
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
        "A few direct papers in the current public sample": "A few exact released papers",
        "Direct literature exists in the current public sample": "Direct released papers exist",
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
        "Scoping review before a bridge paper": "A short review or pilot can connect the two nearby literatures before a direct test.",
        "Seminar seed or targeted replication map": "This looks most useful as a seminar seed or a targeted replication map.",
        "Synthesis plus pilot design": "A synthesis paper plus a small pilot design looks like a sensible first move.",
        "Bridge paper across literatures": "A paper that connects two nearby literatures looks like the natural next step.",
        "This looks ready for a direct empirical follow-through.": "A direct empirical test looks like the natural next step.",
        "Treat this as a missing direct test, not a settled result.": "Treat this as an open direct question, not a settled result.",
        "Use this as a focused follow-up question in the nearby literature.": "Use this as a focused follow-up question in the nearby literature.",
        "Start with a bridge review or cross-field pilot.": "A short review or pilot can help connect the two nearby literatures.",
    }
    return mapping.get(text, text)


def question_brief_markdown(question: pd.Series, mediators: pd.DataFrame, papers: pd.DataFrame, paths: pd.DataFrame) -> str:
    mediator_lines = [
        f"- {row.mediator_label} (rank {int(row.rank)}, score {float(row.score):.1f})"
        for row in mediators.head(6).itertuples(index=False)
    ]
    paper_lines = [
        f"- {row.title} ({int(row.year)}) [{row.edge_src_label} -> {row.edge_dst_label}]"
        for row in papers.drop_duplicates(subset=["paper_id"]).head(6).itertuples(index=False)
    ]
    path_lines = [
        f"- {row.path_text}"
        for row in paths.head(5).itertuples(index=False)
    ]
    parts = [
        f"# {label_for_question(question)}",
        "",
        f"Direct literature status: {question['direct_link_status']}",
        f"Suggested first step: {plain_recommended_move(question['recommended_move'])}",
        "",
        "## Why this question is on the list",
        str(question.get("why_now", "")),
        "",
        "## Nearby linking concepts",
        *(mediator_lines or ["- No stable mediator preview in the current public release."]),
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


def question_filter_frame(questions: pd.DataFrame, search: str, direct_filters: list[str], only_cross_field: bool) -> pd.DataFrame:
    filtered = questions.copy()
    if search.strip():
        needle = search.strip().lower()
        filtered = filtered[
            filtered["public_pair_label"].str.lower().str.contains(needle, na=False)
            | filtered["source_label"].str.lower().str.contains(needle, na=False)
            | filtered["target_label"].str.lower().str.contains(needle, na=False)
            | filtered["why_now"].str.lower().str.contains(needle, na=False)
        ]
    if direct_filters:
        filtered = filtered[filtered["direct_link_status"].isin(direct_filters)]
    if only_cross_field:
        filtered = filtered[filtered["cross_field"] == 1]
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
    st.markdown(str(question.get("why_now", "")))

    summary_cols = st.columns(2)
    with summary_cols[0]:
        mediator_labels = [str(row.mediator_label) for row in mediators.head(5).itertuples(index=False)]
        render_summary_card(
            "Nearby topics",
            ", ".join(mediator_labels) if mediator_labels else "No stable nearby-topic summary was exported for this question.",
        )
    with summary_cols[1]:
        render_summary_card("A useful first step", plain_recommended_move(question.get("recommended_move", "")))

    metrics_cols = st.columns(3)
    metrics_cols[0].metric("Nearby topics", f"{int(question['mediator_count'])}")
    metrics_cols[1].metric("Supporting paths", f"{int(question['supporting_path_count'])}")
    metrics_cols[2].metric("Exact released papers", f"{int(question['cooc_count'])}")
    st.caption(
        f"Exact released papers: {plain_direct_status(question.get('direct_link_status', ''))}. "
        "All counts refer to the current public release, not the full economics literature."
    )

    papers_preview = (
        papers.drop_duplicates(subset=["paper_id"], keep="first")
        .loc[:, ["title", "year", "edge_src_label", "edge_dst_label"]]
        .rename(columns={"title": "Paper", "year": "Year", "edge_src_label": "Edge source", "edge_dst_label": "Edge target"})
        .head(8)
    )
    st.markdown("### Papers to begin with")
    if papers_preview.empty:
        st.caption("No paper list was exported for this question in the current public release.")
    else:
        st.dataframe(papers_preview, use_container_width=True, hide_index=True)

    brief = question_brief_markdown(question, mediators, papers, paths)
    st.download_button(
        "Export question brief",
        data=brief,
        file_name=f"frontiergraph_{pair_key}.md",
        mime="text/markdown",
    )

    with st.expander("Technical tables", expanded=False):
        st.markdown("**Top mediators**")
        st.dataframe(mediators, use_container_width=True, hide_index=True)

        path_frame = paths.copy()
        if not path_frame.empty:
            path_frame["path_labels"] = path_frame["path_labels_json"].map(
                lambda value: " -> ".join(parse_json(value)) if parse_json(value) else ""
            )
            st.markdown("**Supporting paths**")
            st.dataframe(
                path_frame.loc[:, ["rank", "path_len", "path_score", "path_labels"]],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("**Supporting papers**")
        st.dataframe(papers, use_container_width=True, hide_index=True)

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
    status_options = sorted(questions["direct_link_status"].dropna().unique().tolist())
    sync_from_query("question_search", search_default, "_sync_question_search")
    sync_from_query("question_cross_only", query_param("cross") == "1", "_sync_question_cross_only")
    with st.sidebar:
        st.markdown("### Question explorer")
        st.markdown(
            '<p class="sidebar-caption">Choose a question here. The main panel stays focused on the reading notes, nearby topics, and paper list.</p>',
            unsafe_allow_html=True,
        )
        search = st.text_input(
            "Search questions",
            key="question_search",
            placeholder="Search by topic, outcome, or question wording",
        )
        only_cross = st.checkbox("Only cross-area questions", key="question_cross_only")
        with st.expander("Filters", expanded=False):
            direct_filters = st.multiselect(
                "Exact released papers",
                options=status_options,
                default=status_options,
                format_func=plain_direct_status,
            )
            shortlist_size = st.slider("Questions to preview", min_value=12, max_value=80, value=24, step=6)
    filtered = question_filter_frame(questions, search, direct_filters, only_cross)

    if filtered.empty:
        st.warning("No released questions match the current filters.")
        return

    preview = diversified_question_preview(filtered, shortlist_size)
    candidate_frame = diversified_question_preview(filtered, max(shortlist_size, 60))
    candidate_map = {str(row.pair_key): row for row in candidate_frame.itertuples(index=False)}
    default_pair = pair_default if pair_default in candidate_map else preferred_question_pair(candidate_frame)
    sync_from_query("question_selection", default_pair, "_sync_question_selection")
    with st.sidebar:
        selection = st.selectbox(
            "Read one question",
            options=list(candidate_map.keys()),
            key="question_selection",
            format_func=lambda value: question_option_label(pd.Series(candidate_map[value]._asdict())),
        )
    if selection != pair_default or search != search_default or only_cross != (query_param("cross") == "1"):
        set_query_params(view="question", pair=selection, search=search, cross="1" if only_cross else "")
    compare_default = [value for value in query_param("pairs").split(",") if value in candidate_map][:4]
    sync_from_query("question_compare_pairs", compare_default, "_sync_question_compare_pairs")
    with st.sidebar:
        with st.expander("Compare questions", expanded=False):
            compare_pairs = st.multiselect(
                "Pin questions to compare",
                options=list(candidate_map.keys()),
                key="question_compare_pairs",
                format_func=lambda value: question_option_label(pd.Series(candidate_map[value]._asdict())),
            )
            if len(compare_pairs) >= 2 and st.button("Open compare workspace"):
                set_query_params(view="compare", pairs=",".join(compare_pairs))
                st.rerun()

    render_question_detail(db_path, selection, concept_lookup)

    st.markdown("### Current shortlist")
    preview_table = preview.loc[:, ["public_pair_label", "supporting_path_count", "mediator_count", "recommended_move"]].copy()
    preview_table["Nearby support"] = preview_table.apply(
        lambda row: f"{int(row['supporting_path_count'])} supporting paths · {int(row['mediator_count'])} nearby topics",
        axis=1,
    )
    preview_table["recommended_move"] = preview_table["recommended_move"].map(plain_recommended_move)
    preview_table = preview_table.loc[:, ["public_pair_label", "Nearby support", "recommended_move"]]
    preview_table.columns = ["Question", "Nearby support", "A useful first step"]
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
        st.markdown("### Topic explorer")
        st.markdown(
            '<p class="sidebar-caption">Search for a topic on the left. The main panel then keeps the local map, neighbors, and nearby questions together.</p>',
            unsafe_allow_html=True,
        )
        search = st.text_input(
            "Find a topic",
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
    with st.sidebar:
        choice = st.selectbox(
            "Read one topic",
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

    st.markdown(f"## {concept['plain_label']}")
    if str(concept.get("subtitle", "")).strip():
        st.caption(str(concept["subtitle"]))
    metrics_cols = st.columns(3)
    metrics_cols[0].metric("Mapped node mentions", f"{int(concept['instance_support']):,}")
    metrics_cols[1].metric("Papers in release", f"{int(concept['distinct_paper_support']):,}")
    metrics_cols[2].metric("Nearby topics", f"{int(concept['neighbor_count']):,}")
    st.caption("These counts refer to the current public FrontierGraph release. They describe where the topic sits in the released graph; they are not a claim about overall importance.")

    countries = ", ".join(top_value_labels(concept.get("top_countries_json")))
    units = ", ".join(top_value_labels(concept.get("top_units_json")))
    if countries or units:
        render_summary_card("Common contexts", f"Countries: {countries or 'not surfaced'}<br/>Units: {units or 'not surfaced'}")

    left, right = st.columns([1.0, 1.15])
    with left:
        st.markdown("### Local neighborhood")
        try:
            st.graphviz_chart(concept_graphviz(concept, neighbors), use_container_width=True)
        except Exception:
            st.code(concept_graphviz(concept, neighbors))
    with right:
        n_left, n_right = st.columns(2)
        with n_left:
            st.markdown("### Incoming")
            st.dataframe(neighbors[neighbors["direction"] == "incoming"].head(10), use_container_width=True, hide_index=True)
        with n_right:
            st.markdown("### Outgoing")
            st.dataframe(neighbors[neighbors["direction"] == "outgoing"].head(10), use_container_width=True, hide_index=True)

    nearby_questions = []
    for row in opportunities.head(12).itertuples(index=False):
        payload = parse_json(row.row_json)
        nearby_questions.append(
            {
                "Question": payload.get("public_pair_label", f"{row.source_label} and {row.target_label}"),
                "Nearby support": f"{int(payload.get('supporting_path_count', 0) or 0)} supporting paths",
                "A useful first step": plain_recommended_move(payload.get("recommended_move", "")),
            }
        )
    st.markdown("### Questions touching this topic")
    st.dataframe(pd.DataFrame(nearby_questions), use_container_width=True, hide_index=True)


def render_compare_workspace(db_path: str, questions: pd.DataFrame, concepts: pd.DataFrame) -> None:
    pair_defaults = [value for value in query_param("pairs").split(",") if value]
    sync_from_query("compare_mode", "Questions" if pair_defaults else st.session_state.get("compare_mode", "Questions"), "_sync_compare_mode")
    compare_mode = st.radio("Compare questions or topics", options=["Questions", "Topics"], horizontal=True, key="compare_mode")
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
            return
        cols = st.columns(len(selected[:4]))
        for col, pair_key in zip(cols, selected[:4]):
            bundle = load_question_bundle(db_path, pair_key)
            question = bundle["question"]
            if question is None:
                continue
            papers = bundle["papers"].drop_duplicates(subset=["paper_id"]).head(3)
            with col:
                st.markdown(f"**{label_for_question(question)}**")
                st.caption(plain_recommended_move(question["recommended_move"]))
                st.write(f"Exact released papers: {int(question['cooc_count'])}")
                st.write(f"Nearby topics: {int(question['mediator_count'])}")
                if not papers.empty:
                    st.markdown("**Papers to begin with**")
                    for paper in papers.itertuples(index=False):
                        st.markdown(f"- {paper.title} ({int(paper.year)})")
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
                st.write(f"Nearby released questions: {len(opportunities):,}")
                if not neighbors.empty:
                    st.markdown("**Nearest neighbors**")
                    for row in neighbors.head(4).itertuples(index=False):
                        st.markdown(f"- {row.label}")


def render_advanced_evidence(db_path: str, questions: pd.DataFrame, concepts: pd.DataFrame) -> None:
    pair_default = query_param("pair")
    question_map = {str(row.pair_key): row for row in questions.head(150).itertuples(index=False)}
    selected_pair = pair_default if pair_default in question_map else next(iter(question_map))
    sync_from_query("advanced_pair", selected_pair, "_sync_advanced_pair")
    choice = st.selectbox(
        "Question for raw evidence",
        options=list(question_map.keys()),
        key="advanced_pair",
        format_func=lambda value: question_option_label(pd.Series(question_map[value]._asdict())),
    )
    if choice != pair_default:
        set_query_params(view="advanced", pair=choice)
    bundle = load_question_bundle(db_path, choice)
    question = bundle["question"]
    st.markdown(f"### Advanced evidence for {label_for_question(question)}")

    with st.expander("Raw question row", expanded=True):
        st.json({key: (value.item() if hasattr(value, "item") else value) for key, value in question.to_dict().items()})

    with st.expander("Mediator table", expanded=False):
        st.dataframe(bundle["mediators"], use_container_width=True, hide_index=True)

    with st.expander("Path table", expanded=False):
        st.dataframe(bundle["paths"], use_container_width=True, hide_index=True)

    with st.expander("Paper table", expanded=False):
        st.dataframe(bundle["papers"], use_container_width=True, hide_index=True)

    with st.expander("Release metadata", expanded=False):
        st.json(load_release_meta(db_path))
        st.json(load_release_metrics(db_path))

    st.markdown("### Concept lookup")
    concept_map = {str(row.concept_id): row for row in concepts.head(150).itertuples(index=False)}
    ensure_widget_state("advanced_concept", next(iter(concept_map)))
    concept_choice = st.selectbox(
        "Inspect one concept row",
        options=list(concept_map.keys()),
        key="advanced_concept",
        format_func=lambda value: concept_option_label(pd.Series(concept_map[value]._asdict())),
    )
    concept_bundle = load_concept_bundle(db_path, concept_choice)
    if concept_bundle["concept"] is not None:
        st.json({key: (value.item() if hasattr(value, "item") else value) for key, value in concept_bundle["concept"].to_dict().items()})


def main() -> None:
    st.set_page_config(page_title="FrontierGraph | App", layout="wide", initial_sidebar_state="expanded")
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
            <a href="{GRAPH_URL}">Literature map</a>
            <a href="{PAPER_URL}">Paper</a>
            <a href="{DOWNLOADS_URL}">Downloads</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hero-shell">
            <div class="eyebrow">FrontierGraph app</div>
            <h1 class="hero-title">Read one question or topic in the released graph.</h1>
            <p class="hero-copy">
                Choose a question or topic in the left sidebar. The main panel keeps the nearby topics, supporting paths, and paper list together so you can read one object at a time.
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
        st.error("The canonical public bundle is missing the released questions or concepts tables.")
        st.stop()

    concept_lookup = {
        str(row.concept_id): str(row.plain_label or row.label)
        for row in concepts.itertuples(index=False)
    }

    view_default = query_param("view") or "question"
    view_labels = {
        "question": "Questions",
        "concept": "Topics",
        "compare": "Compare",
        "advanced": "Tables",
    }
    view_keys = list(view_labels.keys())
    sync_from_query("active_view", view_default if view_default in view_keys else "question", "_sync_active_view")
    with st.sidebar:
        st.markdown("### Browse")
        active_view = st.radio(
            "View",
            options=view_keys,
            key="active_view",
            format_func=lambda value: view_labels[value],
            horizontal=False,
        )
    if active_view != view_default:
        set_query_params(view=active_view)

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
