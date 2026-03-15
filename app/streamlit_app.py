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
        .stApp {
            background: #f8f7f3;
            color: #182226;
        }
        .block-container {
            max-width: 1240px;
            padding-top: 1.35rem;
            padding-bottom: 2.8rem;
        }
        .stApp,
        .stApp p,
        .stApp li,
        .stApp label,
        .stApp .stCaption,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] * {
            color: #182226;
        }
        h1, h2, h3 {
            font-family: Georgia, "Times New Roman", serif;
            color: #182226;
        }
        .hero-shell {
            padding: 0 0 1rem 0;
            border-bottom: 1px solid rgba(24, 34, 38, 0.10);
            margin-bottom: 1rem;
        }
        .eyebrow {
            font-size: 0.74rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #5b666c;
            margin-bottom: 0.35rem;
        }
        .hero-title {
            font-size: 2.25rem;
            line-height: 1.04;
            margin: 0;
        }
        .hero-copy {
            max-width: 50rem;
            margin-top: 0.55rem;
            color: #546066;
            line-height: 1.6;
            font-size: 0.99rem;
        }
        .app-nav {
            margin: 0.2rem 0 1rem;
            color: #5d696f;
            font-size: 0.95rem;
        }
        .app-nav a {
            color: #2e5f8a;
            text-decoration: none;
            margin-right: 1rem;
        }
        .stApp a {
            color: #2e5f8a;
        }
        .stApp a:hover {
            color: #1f4d73;
        }
        .summary-card {
            border: 1px solid rgba(24, 34, 38, 0.10);
            border-radius: 10px;
            background: #ffffff;
            padding: 0.95rem 1rem;
            margin-bottom: 0.8rem;
        }
        .summary-card strong {
            display: block;
            margin-bottom: 0.25rem;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(24, 34, 38, 0.10);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.8rem 0.9rem;
        }
        [data-testid="stMetric"] *,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            color: #182226 !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid rgba(24, 34, 38, 0.10);
            border-radius: 8px;
            background: #ffffff;
        }
        [data-testid="stExpander"] *,
        [data-testid="stExpanderDetails"] *,
        [data-testid="stExpanderSummary"] * {
            color: #182226 !important;
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
            color: #182226;
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
            color: #182226 !important;
        }
        .stApp input,
        .stApp textarea,
        .stApp select {
            color: #182226 !important;
            -webkit-text-fill-color: #182226;
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
            color: #7a858b !important;
            -webkit-text-fill-color: #7a858b;
        }
        .stApp button {
            color: #182226;
        }
        .stApp [data-testid="stDataFrame"] *,
        .stApp [data-testid="stTable"] * {
            color: #182226 !important;
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


@st.cache_data(show_spinner="Loading released research questions...")
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
        f"Likely next study form: {question['recommended_move']}",
        "",
        "## Why this question is on the list",
        str(question.get("why_now", "")),
        "",
        "## Related ideas",
        *(mediator_lines or ["- No stable mediator preview in the current public release."]),
        "",
        "## Starter papers",
        *(paper_lines or ["- No starter papers were exported for this question in the public release."]),
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

    st.markdown(f"### {label_for_question(question)}")
    left, right = st.columns([1.35, 1.0])
    with left:
        render_summary_card("Why this question appears", str(question.get("why_now", "")))
        render_summary_card("Direct-literature status", str(question.get("direct_link_status", "")))
        render_summary_card("Likely next study form", str(question.get("recommended_move", "")))
    with right:
        st.metric("Ranking score", f"{float(question['score']):.3f}")
        st.metric("Related ideas", f"{int(question['mediator_count'])}")
        st.metric("Supporting motifs", f"{int(question['motif_count'])}")
        st.metric("Direct papers already seen", f"{int(question['cooc_count'])}")

    papers_preview = (
        papers.drop_duplicates(subset=["paper_id"], keep="first")
        .loc[:, ["title", "year", "edge_src_label", "edge_dst_label"]]
        .rename(columns={"title": "Paper", "year": "Year", "edge_src_label": "Edge source", "edge_dst_label": "Edge target"})
        .head(8)
    )
    st.markdown("**Starter papers**")
    if papers_preview.empty:
        st.caption("No starter papers were exported for this question in the current public release.")
    else:
        st.dataframe(papers_preview, use_container_width=True, hide_index=True)

    nearby_labels = [str(row.mediator_label) for row in mediators.head(6).itertuples(index=False)]
    if nearby_labels:
        st.caption("Related ideas: " + ", ".join(nearby_labels))

    brief = question_brief_markdown(question, mediators, papers, paths)
    st.download_button(
        "Export question brief",
        data=brief,
        file_name=f"frontiergraph_{pair_key}.md",
        mime="text/markdown",
    )

    with st.expander("Advanced evidence", expanded=False):
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
    search_col, filter_col = st.columns([1.7, 1.0])
    with search_col:
        search = st.text_input(
            "Search questions",
            key="question_search",
            placeholder="Search by topic, outcome, or question wording",
        )
    with filter_col:
        only_cross = st.checkbox("Only cross-bucket questions", key="question_cross_only")

    direct_filters = st.multiselect(
        "Direct-literature status",
        options=status_options,
        default=status_options,
    )
    shortlist_size = st.slider("Shortlist size", min_value=10, max_value=100, value=25, step=5)
    filtered = question_filter_frame(questions, search, direct_filters, only_cross)

    if filtered.empty:
        st.warning("No released questions match the current filters.")
        return

    preview = filtered.head(shortlist_size).copy()
    preview_table = preview.loc[:, ["public_pair_label", "direct_link_status", "recommended_move", "mediator_count", "score"]]
    preview_table.columns = ["Question", "Direct literature", "Likely next study form", "Related ideas", "Score"]
    st.dataframe(preview_table, use_container_width=True, hide_index=True)
    st.download_button(
        "Export shortlist CSV",
        data=shortlist_csv(filtered.head(100)),
        file_name="frontiergraph_shortlist.csv",
        mime="text/csv",
    )

    candidate_map = {str(row.pair_key): row for row in preview.itertuples(index=False)}
    default_pair = pair_default if pair_default in candidate_map else next(iter(candidate_map))
    sync_from_query("question_selection", default_pair, "_sync_question_selection")
    selection = st.selectbox(
        "Inspect one question",
        options=list(candidate_map.keys()),
        key="question_selection",
        format_func=lambda value: question_option_label(pd.Series(candidate_map[value]._asdict())),
    )
    if selection != pair_default or search != search_default or only_cross != (query_param("cross") == "1"):
        set_query_params(view="question", pair=selection, search=search, cross="1" if only_cross else "")
    compare_default = [value for value in query_param("pairs").split(",") if value in candidate_map][:4]
    sync_from_query("question_compare_pairs", compare_default, "_sync_question_compare_pairs")
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
    search = st.text_input(
        "Find a topic",
        key="concept_search",
        placeholder="Search by topic, alias, or concept label",
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
    choice = st.selectbox(
        "Select topic",
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

    st.markdown(f"### {concept['plain_label']}")
    if str(concept.get("subtitle", "")).strip():
        st.caption(str(concept["subtitle"]))
    metrics_cols = st.columns(4)
    metrics_cols[0].metric("Instance support", f"{int(concept['instance_support']):,}")
    metrics_cols[1].metric("Distinct papers", f"{int(concept['distinct_paper_support']):,}")
    metrics_cols[2].metric("Weighted degree", f"{float(concept['weighted_degree']):,.1f}")
    metrics_cols[3].metric("Neighbor count", f"{int(concept['neighbor_count']):,}")

    countries = ", ".join(top_value_labels(concept.get("top_countries_json")))
    units = ", ".join(top_value_labels(concept.get("top_units_json")))
    if countries or units:
        render_summary_card("Common contexts", f"Countries: {countries or 'not surfaced'}<br/>Units: {units or 'not surfaced'}")

    left, right = st.columns([1.0, 1.15])
    with left:
        st.markdown("**Local map**")
        try:
            st.graphviz_chart(concept_graphviz(concept, neighbors), use_container_width=True)
        except Exception:
            st.code(concept_graphviz(concept, neighbors))
    with right:
        n_left, n_right = st.columns(2)
        with n_left:
            st.markdown("**Incoming neighbors**")
            st.dataframe(neighbors[neighbors["direction"] == "incoming"].head(10), use_container_width=True, hide_index=True)
        with n_right:
            st.markdown("**Outgoing neighbors**")
            st.dataframe(neighbors[neighbors["direction"] == "outgoing"].head(10), use_container_width=True, hide_index=True)

    nearby_questions = []
    for row in opportunities.head(12).itertuples(index=False):
        payload = parse_json(row.row_json)
        nearby_questions.append(
            {
                "Question": payload.get("public_pair_label", f"{row.source_label} and {row.target_label}"),
                "Score": payload.get("score", row.score),
                "Likely next study form": payload.get("recommended_move", ""),
                "Open in app": payload.get("app_link", ""),
            }
        )
    st.markdown("**Nearby questions touching this topic**")
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
                st.caption(str(question["recommended_move"]))
                st.write(f"Direct literature: {question['direct_link_status']}")
                st.write(f"Related ideas: {int(question['mediator_count'])}")
                if not papers.empty:
                    st.markdown("**Starter papers**")
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
                st.write(f"Distinct papers: {int(concept['distinct_paper_support']):,}")
                st.write(f"Neighbor count: {int(concept['neighbor_count']):,}")
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
    st.set_page_config(page_title="FrontierGraph | Deeper App", layout="wide", initial_sidebar_state="collapsed")
    inject_css()

    db_path = choose_db_path()
    if not Path(db_path).exists():
        st.error(f"Database not found: {db_path}")
        st.stop()

    st.markdown(
        f"""
        <div class="app-nav">
            <a href="{SITE_URL}">Site</a>
            <a href="{QUESTIONS_URL}">Research questions</a>
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
            <div class="eyebrow">FrontierGraph deeper app</div>
            <h1 class="hero-title">Inspect one question or topic in more detail.</h1>
            <p class="hero-copy">
                This app is the deeper public evidence layer behind the site. Start with a question or topic, inspect the related ideas and starter papers, and only then decide whether it looks concrete enough to read, scope, or test more seriously.
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
        "question": "Question explorer",
        "concept": "Topic explorer",
        "compare": "Compare workspace",
        "advanced": "Advanced evidence",
    }
    view_keys = list(view_labels.keys())
    sync_from_query("active_view", view_default if view_default in view_keys else "question", "_sync_active_view")
    active_view = st.radio(
        "Work area",
        options=view_keys,
        key="active_view",
        format_func=lambda value: view_labels[value],
        horizontal=True,
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
