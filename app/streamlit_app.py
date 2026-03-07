from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import streamlit as st

from src.explain import build_idea_brief_markdown


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


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f8f7f3;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
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
            font-size: 2.2rem;
            line-height: 1.04;
            margin: 0;
        }
        .hero-copy {
            max-width: 46rem;
            margin-top: 0.55rem;
            color: #546066;
            line-height: 1.55;
            font-size: 0.98rem;
        }
        .muted {
            color: #5d696f;
            font-size: 0.92rem;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(24, 34, 38, 0.10);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.8rem 0.9rem;
        }
        [data-testid="stExpander"] {
            border: 1px solid rgba(24, 34, 38, 0.10);
            border-radius: 8px;
            background: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def connect_readonly(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    uri = f"file:{quote(str(path))}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False, timeout=30)


@st.cache_data(show_spinner=False)
def load_nodes(db_path: str) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query("SELECT code, label FROM nodes ORDER BY label, code", conn)


@st.cache_data(show_spinner="Loading ranked economics opportunities...")
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

    df["u"] = df["u"].astype(str)
    df["v"] = df["v"].astype(str)
    df["u_label"] = df["u_label"].fillna(df["u"]).astype(str)
    df["v_label"] = df["v_label"].fillna(df["v"]).astype(str)
    df["source_field"] = df["u"].str[0]
    df["target_field"] = df["v"].str[0]
    df["source_field_name"] = df["source_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
    df["target_field_name"] = df["target_field"].map(JEL_FIELD_NAMES).fillna("Unmapped field")
    df["cross_field"] = df["source_field"] != df["target_field"]
    df["boundary_flag"] = df["cross_field"] & (df["cooc_count"].fillna(0) <= 0)
    df["novelty_type"] = df.apply(classify_novelty, axis=1)
    df["novelty_label"] = df["novelty_type"].map(NOVELTY_LABELS).fillna("Other")
    df["opportunity"] = df["u_label"] + " -> " + df["v_label"]
    df["code_pair"] = df["u"] + " -> " + df["v"]

    cooc_log = np.log1p(df["cooc_count"].fillna(0).clip(lower=0))
    mediator_log = np.log1p(df["mediator_count"].fillna(0).clip(lower=0))
    motif_log = np.log1p(df["motif_count"].fillna(0).clip(lower=0))
    last_seen = df["last_year_seen"].fillna(0)

    df["low_contact_norm"] = 1.0 - normalize_series(cooc_log)
    df["mediator_norm"] = normalize_series(mediator_log)
    df["motif_count_norm"] = normalize_series(motif_log)
    df["staleness_norm"] = 1.0 - normalize_series(last_seen)
    df["boundary_norm"] = df["boundary_flag"].astype(float)
    df["cross_field_norm"] = df["cross_field"].astype(float)
    return df


def query_df(db_path: str, sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(show_spinner=False)
def load_candidate_bundle(db_path: str, u: str, v: str) -> dict[str, pd.DataFrame | pd.Series | None]:
    candidate_df = query_df(
        db_path,
        """
        SELECT c.*, nu.label AS u_label, nv.label AS v_label
        FROM candidates c
        LEFT JOIN nodes nu ON c.u = nu.code
        LEFT JOIN nodes nv ON c.v = nv.code
        WHERE c.u = ? AND c.v = ?
        LIMIT 1
        """,
        (u, v),
    )
    mediators_df = query_df(
        db_path,
        """
        SELECT rank, mediator, score
        FROM candidate_mediators
        WHERE candidate_u = ? AND candidate_v = ?
        ORDER BY rank
        """,
        (u, v),
    )
    paths_df = query_df(
        db_path,
        """
        SELECT rank, path_len, path_score, path_text
        FROM candidate_paths
        WHERE candidate_u = ? AND candidate_v = ?
        ORDER BY rank
        """,
        (u, v),
    )
    papers_df = query_df(
        db_path,
        """
        SELECT path_rank, edge_src, edge_dst, paper_id, title, year
        FROM candidate_papers
        WHERE candidate_u = ? AND candidate_v = ?
        ORDER BY path_rank, paper_rank
        """,
        (u, v),
    )
    neighborhood_df = query_df(
        db_path,
        """
        SELECT top_out_neighbors_u_json, top_in_neighbors_v_json
        FROM candidate_neighborhoods
        WHERE candidate_u = ? AND candidate_v = ?
        LIMIT 1
        """,
        (u, v),
    )
    neighborhood_row = neighborhood_df.iloc[0] if not neighborhood_df.empty else None
    candidate_row = candidate_df.iloc[0] if not candidate_df.empty else None
    return {
        "candidate_df": candidate_df,
        "candidate_row": candidate_row,
        "mediators_df": mediators_df,
        "paths_df": paths_df,
        "papers_df": papers_df,
        "neighborhood_row": neighborhood_row,
    }


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


def field_option_label(field_code: str) -> str:
    return f"{field_code} | {JEL_FIELD_NAMES.get(field_code, 'Unmapped field')}"


def candidate_option_label(row: pd.Series) -> str:
    rank = to_int(row.get("priority_rank", 0), default=0)
    return f"#{rank} {row['opportunity']} | {row['priority_score']:.3f}"


def filtered_download_frame(filtered_df: pd.DataFrame) -> pd.DataFrame:
    working = filtered_df.copy()
    if "priority_rank" not in working.columns:
        working["priority_rank"] = np.arange(1, len(working) + 1)

    out = working[
        [
            "priority_rank",
            "priority_score",
            "score",
            "opportunity",
            "code_pair",
            "source_field_name",
            "target_field_name",
            "novelty_label",
            "cooc_count",
            "mediator_count",
            "motif_count",
        ]
    ].copy()
    out["project_shape"] = working.apply(recommendation_play, axis=1)
    out["why_now"] = working.apply(why_now, axis=1)
    return out.rename(
        columns={
            "priority_rank": "rank",
            "score": "base_score",
            "source_field_name": "source_field",
            "target_field_name": "target_field",
            "novelty_label": "novelty",
            "cooc_count": "prior_cooccurrences",
        }
    )


def shortlist_view(shortlist_df: pd.DataFrame) -> pd.DataFrame:
    working = shortlist_df.copy()
    if "priority_rank" not in working.columns:
        working["priority_rank"] = np.arange(1, len(working) + 1)

    return (
        working[
            [
                "priority_rank",
                "opportunity",
                "novelty_label",
                "target_field_name",
                "priority_score",
                "cooc_count",
                "mediator_count",
            ]
        ]
        .rename(
            columns={
                "priority_rank": "Rank",
                "opportunity": "Opportunity",
                "novelty_label": "Type",
                "target_field_name": "Target field",
                "priority_score": "Priority",
                "cooc_count": "Prior contact",
                "mediator_count": "Mediators",
            }
        )
        .assign(Priority=lambda df: df["Priority"].map(lambda value: f"{value:.3f}"))
    )


def filter_candidates(
    candidates_df: pd.DataFrame,
    search_text: str,
    source_fields: list[str],
    target_fields: list[str],
    novelty_filter: list[str],
    min_score: float,
    cooc_cap: int | None,
    min_mediators: int,
    only_cross_field: bool,
) -> pd.DataFrame:
    filtered_df = candidates_df.copy()
    if search_text.strip():
        q = search_text.strip().lower()
        filtered_df = filtered_df[
            filtered_df["u"].str.lower().str.contains(q, na=False)
            | filtered_df["v"].str.lower().str.contains(q, na=False)
            | filtered_df["u_label"].str.lower().str.contains(q, na=False)
            | filtered_df["v_label"].str.lower().str.contains(q, na=False)
        ]
    if source_fields:
        filtered_df = filtered_df[filtered_df["source_field"].isin(source_fields)]
    if target_fields:
        filtered_df = filtered_df[filtered_df["target_field"].isin(target_fields)]
    if novelty_filter:
        allowed_novelties = {key for key, label in NOVELTY_LABELS.items() if label in novelty_filter}
        filtered_df = filtered_df[filtered_df["novelty_type"].isin(allowed_novelties)]
    if only_cross_field:
        filtered_df = filtered_df[filtered_df["cross_field"]]
    filtered_df = filtered_df[filtered_df["score"].fillna(0.0) >= float(min_score)]
    if cooc_cap is not None:
        filtered_df = filtered_df[filtered_df["cooc_count"].fillna(0) <= int(cooc_cap)]
    filtered_df = filtered_df[filtered_df["mediator_count"].fillna(0) >= int(min_mediators)]
    return filtered_df


def render_ranker_tab(db_path: str, filtered_df: pd.DataFrame, preset: str, top_n: int) -> None:
    st.subheader("Shortlist")
    st.caption(PRESET_HELP[preset])

    if filtered_df.empty:
        st.warning("No opportunities match the current filters. Relax the thresholds or switch presets.")
        return

    shortlist_df = filtered_df.head(int(top_n)).reset_index(drop=True)

    top_cols = st.columns(4)
    with top_cols[0]:
        st.metric("Ideas in play", f"{len(filtered_df):,}")
    with top_cols[1]:
        st.metric("Cross-field share", f"{100 * filtered_df['cross_field'].mean():.1f}%")
    with top_cols[2]:
        st.metric("Median priority", f"{filtered_df['priority_score'].median():.3f}")
    with top_cols[3]:
        st.metric("Top idea", shortlist_df.iloc[0]["opportunity"])

    st.dataframe(shortlist_view(shortlist_df), use_container_width=True, hide_index=True)

    options_df = shortlist_df.head(min(100, len(shortlist_df))).reset_index(drop=True)
    selected_idx = st.selectbox(
        "Inspect one opportunity in detail",
        options=options_df.index,
        format_func=lambda i: candidate_option_label(options_df.loc[i]),
    )
    render_candidate_detail(db_path, options_df.loc[int(selected_idx)])

    st.download_button(
        label="Download current shortlist as CSV",
        data=filtered_download_frame(shortlist_df).to_csv(index=False),
        file_name="frontiergraph_shortlist.csv",
        mime="text/csv",
    )


def render_candidate_detail(db_path: str, row: pd.Series) -> None:
    bundle = load_candidate_bundle(db_path, str(row["u"]), str(row["v"]))
    candidate_row = bundle["candidate_row"]
    mediators_df = bundle["mediators_df"]
    paths_df = bundle["paths_df"]
    papers_df = bundle["papers_df"]
    neighborhood_row = bundle["neighborhood_row"]

    if candidate_row is None:
        st.warning("Candidate details were not found in the database.")
        return

    st.markdown("### Selected opportunity")
    st.markdown(f"**{row['opportunity']}**")
    st.caption(
        f"{row['code_pair']} | {row['source_field_name']} -> {row['target_field_name']}"
    )
    st.write(f"Suggested move: {recommendation_play(row)}")
    st.write(why_now(row))

    top_cols = st.columns(4)
    top_cols[0].metric("Priority", f"{to_float(row['priority_score']):.3f}")
    top_cols[1].metric("Base score", f"{to_float(candidate_row['score']):.3f}")
    top_cols[2].metric("Prior contact", f"{to_int(candidate_row.get('cooc_count', 0))}")
    top_cols[3].metric("Mediators", f"{to_int(candidate_row.get('mediator_count', 0))}")

    summary_tab, evidence_tab, papers_tab, export_tab = st.tabs(["Summary", "Evidence", "Papers", "Export"])

    with summary_tab:
        summary_left, summary_right = st.columns(2)
        with summary_left:
            summary_df = pd.DataFrame(
                [
                    {"Metric": "Novelty", "Value": row["novelty_label"]},
                    {"Metric": "Path support", "Value": f"{to_float(candidate_row.get('path_support_norm', 0.0)):.3f}"},
                    {"Metric": "Gap bonus", "Value": f"{to_float(candidate_row.get('gap_bonus', 0.0)):.3f}"},
                    {"Metric": "Motif bonus", "Value": f"{to_float(candidate_row.get('motif_bonus_norm', 0.0)):.3f}"},
                    {"Metric": "Hub penalty", "Value": f"{to_float(candidate_row.get('hub_penalty', 0.0)):.3f}"},
                    {"Metric": "Base-model rank", "Value": str(to_int(candidate_row.get('rank', 0)))},
                ]
            )
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        with summary_right:
            evidence_df = pd.DataFrame(
                [
                    {"Measure": "Mediators", "Count": to_int(candidate_row.get("mediator_count", 0))},
                    {"Measure": "Supporting motifs", "Count": to_int(candidate_row.get("motif_count", 0))},
                    {"Measure": "Prior co-occurrences", "Count": to_int(candidate_row.get("cooc_count", 0))},
                ]
            )
            st.dataframe(evidence_df, use_container_width=True, hide_index=True)
            if neighborhood_row is not None:
                with st.expander("Inspect local neighborhood", expanded=False):
                    st.markdown("**Top outgoing neighbors of the source concept**")
                    st.code(str(neighborhood_row["top_out_neighbors_u_json"]))
                    st.markdown("**Top incoming neighbors of the target concept**")
                    st.code(str(neighborhood_row["top_in_neighbors_v_json"]))

    with evidence_tab:
        ev_left, ev_right = st.columns(2)
        with ev_left:
            st.markdown("**Top mediators**")
            st.dataframe(mediators_df.head(25), use_container_width=True, hide_index=True)
        with ev_right:
            st.markdown("**Top supporting paths**")
            st.dataframe(paths_df.head(25), use_container_width=True, hide_index=True)

    with papers_tab:
        st.markdown("**Supporting papers behind the candidate paths**")
        st.dataframe(papers_df.head(150), use_container_width=True, hide_index=True)

    with export_tab:
        brief = build_idea_brief_markdown(
            candidate_row=candidate_row,
            mediators_df=mediators_df,
            paths_df=paths_df,
            papers_df=papers_df,
            neighborhood_row=neighborhood_row,
        )
        st.markdown(
            "Export a markdown brief if you want to move the idea into a memo, seminar note, or working agenda."
        )
        st.download_button(
            label="Export idea brief (Markdown)",
            data=brief,
            file_name=f"idea_brief_{row['u']}_to_{row['v']}.md",
            mime="text/markdown",
        )


def render_field_radar_tab(filtered_df: pd.DataFrame) -> None:
    st.subheader("Field map")
    if filtered_df.empty:
        st.warning("No ideas to summarize under the current filters.")
        return

    target_summary = (
        filtered_df.groupby("target_field_name", as_index=False)
        .agg(
            ideas=("priority_score", "size"),
            mean_priority=("priority_score", "mean"),
            cross_field_share=("cross_field", "mean"),
        )
        .sort_values(["mean_priority", "ideas"], ascending=[False, False])
    )
    corridor_summary = (
        filtered_df.assign(corridor=filtered_df["source_field"] + " -> " + filtered_df["target_field"])
        .groupby(["corridor", "source_field_name", "target_field_name"], as_index=False)
        .agg(
            ideas=("priority_score", "size"),
            mean_priority=("priority_score", "mean"),
            boundary_share=("boundary_flag", "mean"),
        )
        .sort_values(["mean_priority", "ideas"], ascending=[False, False])
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Most promising target areas**")
        st.dataframe(target_summary.head(12), use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Strongest source -> target corridors**")
        st.dataframe(corridor_summary.head(12), use_container_width=True, hide_index=True)


def render_concept_tab(db_path: str, nodes_df: pd.DataFrame) -> None:
    st.subheader("Concept lookup")
    st.caption("Use this when you already know the concept you want to trace through the graph.")

    query = st.text_input("Find a concept by code or label", value="")
    filtered = nodes_df
    if query.strip():
        q = query.strip().lower()
        filtered = nodes_df[
            nodes_df["code"].str.lower().str.contains(q, na=False)
            | nodes_df["label"].str.lower().str.contains(q, na=False)
        ]
    if filtered.empty:
        st.warning("No concepts match that query.")
        return

    top_matches = filtered.head(200).reset_index(drop=True)
    selected_index = st.selectbox(
        "Select concept",
        options=top_matches.index,
        format_func=lambda i: f"{top_matches.loc[i, 'code']} | {top_matches.loc[i, 'label']}",
    )
    concept_code = str(top_matches.loc[selected_index, "code"])
    concept_label = str(top_matches.loc[selected_index, "label"])
    k = st.slider("How many ideas to show", min_value=5, max_value=60, value=20, step=5, key="concept_k")

    outgoing = query_df(
        db_path,
        """
        SELECT c.u, nu.label AS u_label, c.v, nv.label AS v_label, c.score, c.path_support_norm, c.gap_bonus, c.motif_bonus_norm
        FROM candidates c
        LEFT JOIN nodes nu ON c.u = nu.code
        LEFT JOIN nodes nv ON c.v = nv.code
        WHERE c.u = ?
        ORDER BY c.score DESC
        LIMIT ?
        """,
        (concept_code, int(k)),
    )
    incoming = query_df(
        db_path,
        """
        SELECT c.u, nu.label AS u_label, c.v, nv.label AS v_label, c.score, c.path_support_norm, c.gap_bonus, c.motif_bonus_norm
        FROM candidates c
        LEFT JOIN nodes nu ON c.u = nu.code
        LEFT JOIN nodes nv ON c.v = nv.code
        WHERE c.v = ?
        ORDER BY c.score DESC
        LIMIT ?
        """,
        (concept_code, int(k)),
    )
    underexplored = query_df(
        db_path,
        """
        SELECT u, v, cooc_count, first_year_seen, last_year_seen, gap_bonus
        FROM underexplored_pairs
        WHERE (u = ? OR v = ?) AND underexplored = 1
        ORDER BY cooc_count ASC, gap_bonus DESC
        LIMIT ?
        """,
        (concept_code, concept_code, int(k)),
    )

    st.markdown(f"### {concept_label} ({concept_code})")
    left, right = st.columns(2)
    with left:
        st.markdown("**Top outgoing opportunities**")
        st.dataframe(outgoing, use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Top incoming opportunities**")
        st.dataframe(incoming, use_container_width=True, hide_index=True)

    st.markdown("**Underexplored pairs touching this concept**")
    st.dataframe(underexplored, use_container_width=True, hide_index=True)


def render_method_tab(filtered_df: pd.DataFrame, preset: str) -> None:
    st.subheader("Method")
    st.markdown(
        """
        1. AI extracts graph structure from papers.
        2. The app scores missing links with deterministic graph signals.
        3. Users re-rank and inspect the evidence rather than receiving a black-box recommendation.
        """
    )
    st.caption(f"Current preset: {preset}. {PRESET_HELP[preset]}")

    if filtered_df.empty:
        st.info("The filtered set is empty, so there is no live summary to report.")
        return

    live_summary = pd.DataFrame(
        [
            {
                "Filtered ideas": len(filtered_df),
                "Mean priority score": round(float(filtered_df["priority_score"].mean()), 3),
                "Cross-field share": round(float(filtered_df["cross_field"].mean()), 3),
                "Boundary share": round(float(filtered_df["boundary_flag"].mean()), 3),
                "Median co-occurrence": round(float(filtered_df["cooc_count"].median()), 1),
            }
        ]
    )
    st.dataframe(live_summary, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="FrontierGraph | Economics ranker",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.markdown(
        """
        <div class="hero-shell">
            <div class="eyebrow">FrontierGraph beta</div>
            <h1 class="hero-title">Economics research ranker</h1>
            <p class="hero-copy">
                FrontierGraph turns the economics literature graph into a shortlist of candidate research links. AI
                extracts the graph; the ranking itself is deterministic and inspectable.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    env_db = os.environ.get("ECON_OPPORTUNITY_DB", "").strip()
    db_default = env_db or (
        "data/processed/app_causalclaims.db"
        if Path("data/processed/app_causalclaims.db").exists()
        else "data/processed/app.db"
    )

    with st.expander("Advanced settings", expanded=False):
        db_path = st.text_input(
            "SQLite DB path",
            value=db_default,
            help="Change this only if you are pointing the app at a different local SQLite build.",
        )

    if not Path(db_path).exists():
        st.error(f"Database not found: {db_path}")
        st.stop()

    nodes_df = load_nodes(db_path)
    candidates_df = load_candidate_summary(db_path)
    if nodes_df.empty or candidates_df.empty:
        st.error("The database is missing the node or candidate tables needed by the app.")
        st.stop()

    available_fields = sorted(set(candidates_df["source_field"]) | set(candidates_df["target_field"]))
    novelty_options = list(NOVELTY_LABELS.values())
    max_base_score = max(to_float(candidates_df["score"].max(), default=0.01), 0.01)
    default_min_score = min(0.18, round(max_base_score, 3))
    slider_max = max(5, int(min(candidates_df["cooc_count"].quantile(0.99), 250)))

    with st.expander("Refine the ranking", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            preset = st.selectbox("Ranking mode", options=list(PRESET_HELP.keys()), index=0)
            search_text = st.text_input("Keyword filter", value="")
            top_n = st.slider("Shortlist size", min_value=10, max_value=150, value=30, step=10)
        with col2:
            source_fields = st.multiselect("From fields", options=available_fields, format_func=field_option_label)
            target_fields = st.multiselect("To fields", options=available_fields, format_func=field_option_label)
            novelty_filter = st.multiselect("Novelty lens", options=novelty_options, default=novelty_options)
        with col3:
            min_score = st.slider(
                "Minimum base score",
                min_value=0.0,
                max_value=float(round(max_base_score, 3)),
                value=float(default_min_score),
                step=0.01,
            )
            use_cooc_cap = st.checkbox("Cap prior co-occurrences", value=True)
            cooc_cap = (
                st.slider("Maximum prior co-occurrences", min_value=0, max_value=slider_max, value=min(25, slider_max))
                if use_cooc_cap
                else None
            )
            min_mediators = st.slider("Minimum mediator count", min_value=0, max_value=100, value=5)
            only_cross_field = st.checkbox("Only cross-field ideas", value=False)

    filtered_df = filter_candidates(
        candidates_df,
        search_text=search_text,
        source_fields=source_fields,
        target_fields=target_fields,
        novelty_filter=novelty_filter,
        min_score=min_score,
        cooc_cap=cooc_cap,
        min_mediators=min_mediators,
        only_cross_field=only_cross_field,
    )

    if not filtered_df.empty:
        filtered_df = filtered_df.copy()
        filtered_df["priority_score"] = compute_priority_score(filtered_df, preset=preset)
        filtered_df = filtered_df.sort_values(["priority_score", "score"], ascending=[False, False]).reset_index(drop=True)
        filtered_df["priority_rank"] = filtered_df.index + 1
    else:
        filtered_df = filtered_df.copy()
        filtered_df["priority_score"] = pd.Series(dtype=float)
        filtered_df["priority_rank"] = pd.Series(dtype=int)

    ranker_tab, radar_tab, concept_tab, method_tab = st.tabs(["Ranker", "Field map", "Concepts", "Method"])

    with ranker_tab:
        render_ranker_tab(db_path, filtered_df, preset, top_n=top_n)

    with radar_tab:
        render_field_radar_tab(filtered_df)

    with concept_tab:
        render_concept_tab(db_path, nodes_df)

    with method_tab:
        render_method_tab(filtered_df, preset)


if __name__ == "__main__":
    main()
