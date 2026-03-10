from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.explain import build_idea_brief_markdown
from src.opportunity_data import (
    CONCEPT_BUCKET_NAMES,
    JEL_FIELD_NAMES,
    NOVELTY_LABELS,
    PRESET_HELP,
    compute_priority_score,
    connect_readonly,
    is_concept_mode,
    load_app_mode,
    load_candidate_summary,
    load_nodes,
    recommendation_play,
    to_float,
    to_int,
    why_now,
)

SITE_URL = "https://frontiergraph.com"
GRAPH_URL = f"{SITE_URL}/graph/"
OPPORTUNITIES_URL = f"{SITE_URL}/opportunities/"
COMPARE_URL = f"{SITE_URL}/compare/"
METHOD_URL = f"{SITE_URL}/method/"
DOWNLOADS_URL = f"{SITE_URL}/downloads/"
REPO_URL = "https://github.com/prashgarg/frontiergraph"


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


@st.cache_data(show_spinner=False)
def load_nodes_cached(db_path: str) -> pd.DataFrame:
    return load_nodes(db_path)


@st.cache_data(show_spinner="Loading ranked economics opportunities...")
def load_candidate_summary_cached(db_path: str) -> pd.DataFrame:
    return load_candidate_summary(db_path)


def query_df(db_path: str, sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def format_rank(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "NA"
    return str(int(numeric))


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
    try:
        source_detail_df = query_df(
            db_path,
            """
            SELECT *
            FROM node_details
            WHERE concept_id = ?
            LIMIT 1
            """,
            (u,),
        )
        target_detail_df = query_df(
            db_path,
            """
            SELECT *
            FROM node_details
            WHERE concept_id = ?
            LIMIT 1
            """,
            (v,),
        )
    except Exception:
        source_detail_df = pd.DataFrame()
        target_detail_df = pd.DataFrame()
    return {
        "candidate_df": candidate_df,
        "candidate_row": candidate_row,
        "mediators_df": mediators_df,
        "paths_df": paths_df,
        "papers_df": papers_df,
        "neighborhood_row": neighborhood_row,
        "source_detail_row": source_detail_df.iloc[0] if not source_detail_df.empty else None,
        "target_detail_row": target_detail_df.iloc[0] if not target_detail_df.empty else None,
    }

def field_option_label(field_code: str, app_mode: str) -> str:
    if is_concept_mode(app_mode):
        return f"{field_code} | {CONCEPT_BUCKET_NAMES.get(field_code, field_code)}"
    return f"{field_code} | {JEL_FIELD_NAMES.get(field_code, 'Unmapped field')}"


def query_param(name: str) -> str:
    if not hasattr(st, "query_params"):
        return ""
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def normalize_preset(value: str) -> str:
    normalized = value.strip().lower()
    for candidate in PRESET_HELP:
        if candidate.lower() == normalized:
            return candidate
    return "Balanced"


def parse_flag(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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


def render_ranker_tab(db_path: str, filtered_df: pd.DataFrame, preset: str, top_n: int, app_mode: str) -> None:
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
    render_candidate_detail(db_path, options_df.loc[int(selected_idx)], app_mode=app_mode)

    st.download_button(
        label="Download current shortlist as CSV",
        data=filtered_download_frame(shortlist_df).to_csv(index=False),
        file_name="frontiergraph_shortlist.csv",
        mime="text/csv",
    )


def render_candidate_detail(db_path: str, row: pd.Series, app_mode: str) -> None:
    bundle = load_candidate_bundle(db_path, str(row["u"]), str(row["v"]))
    candidate_row = bundle["candidate_row"]
    mediators_df = bundle["mediators_df"]
    paths_df = bundle["paths_df"]
    papers_df = bundle["papers_df"]
    neighborhood_row = bundle["neighborhood_row"]
    source_detail_row = bundle["source_detail_row"]
    target_detail_row = bundle["target_detail_row"]

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

    has_suppression = "base_score" in candidate_row.index
    top_cols = st.columns(5 if has_suppression else 4)
    top_cols[0].metric("Priority", f"{to_float(row['priority_score']):.3f}")
    if has_suppression:
        top_cols[1].metric("Adjusted score", f"{to_float(candidate_row.get('score', 0.0)):.3f}")
        top_cols[2].metric("Base score", f"{to_float(candidate_row.get('base_score', 0.0)):.3f}")
        top_cols[3].metric("Prior contact", f"{to_int(candidate_row.get('cooc_count', 0))}")
        top_cols[4].metric("Mediators", f"{to_int(candidate_row.get('mediator_count', 0))}")
    else:
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
                    *(
                        [
                            {"Metric": "Base rank", "Value": format_rank(candidate_row.get("base_rank"))},
                            {"Metric": "Adjusted rank", "Value": format_rank(candidate_row.get("rank"))},
                            {"Metric": "Duplicate penalty", "Value": f"{to_float(candidate_row.get('duplicate_penalty', 0.0)):.3f}"},
                            {"Metric": "Hard suppression reason", "Value": str(candidate_row.get("hard_same_family_reason", "") or "NA")},
                        ]
                        if has_suppression
                        else []
                    ),
                    {"Metric": "Path support", "Value": f"{to_float(candidate_row.get('path_support_norm', 0.0)):.3f}"},
                    {"Metric": "Gap bonus", "Value": f"{to_float(candidate_row.get('gap_bonus', 0.0)):.3f}"},
                    {"Metric": "Motif bonus", "Value": f"{to_float(candidate_row.get('motif_bonus_norm', 0.0)):.3f}"},
                    {"Metric": "Hub penalty", "Value": f"{to_float(candidate_row.get('hub_penalty', 0.0)):.3f}"},
                    {"Metric": "Displayed rank", "Value": format_rank(candidate_row.get('rank'))},
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
            if is_concept_mode(app_mode) and source_detail_row is not None and target_detail_row is not None:
                with st.expander("Inspect concept metadata", expanded=False):
                    st.markdown("**Source concept**")
                    st.code(
                        json.dumps(
                            {
                                "aliases_json": source_detail_row.get("aliases_json", "[]"),
                                "bucket_hint": source_detail_row.get("bucket_hint", ""),
                                "instance_support": to_int(source_detail_row.get("instance_support", 0)),
                                "mean_confidence": to_float(source_detail_row.get("mean_confidence", 0.0)),
                                "low_confidence_share": to_float(source_detail_row.get("low_confidence_share", 0.0)),
                                "mapping_sources_json": source_detail_row.get("mapping_sources_json", "[]"),
                                "representative_contexts_json": source_detail_row.get("representative_contexts_json", "[]"),
                                "representative_years_json": source_detail_row.get("representative_years_json", "[]"),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                    st.markdown("**Target concept**")
                    st.code(
                        json.dumps(
                            {
                                "aliases_json": target_detail_row.get("aliases_json", "[]"),
                                "bucket_hint": target_detail_row.get("bucket_hint", ""),
                                "instance_support": to_int(target_detail_row.get("instance_support", 0)),
                                "mean_confidence": to_float(target_detail_row.get("mean_confidence", 0.0)),
                                "low_confidence_share": to_float(target_detail_row.get("low_confidence_share", 0.0)),
                                "mapping_sources_json": target_detail_row.get("mapping_sources_json", "[]"),
                                "representative_contexts_json": target_detail_row.get("representative_contexts_json", "[]"),
                                "representative_years_json": target_detail_row.get("representative_years_json", "[]"),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
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


def render_field_radar_tab(filtered_df: pd.DataFrame, app_mode: str) -> None:
    st.subheader("Bucket map" if is_concept_mode(app_mode) else "Field map")
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
        1. AI extracts paper-local graph structure from titles and abstracts.
        2. FrontierGraph maps those local graphs into concept regimes and ranks missing links with deterministic graph signals.
        3. The public default is Baseline exploratory, with duplicate cleanup applied to the recommendation surface before it is shown.
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
        page_title="FrontierGraph | Concept explorer",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.markdown(
        f"""
        <div class="app-nav">
            <a href="{SITE_URL}">Site</a>
            <a href="{GRAPH_URL}">Graph</a>
            <a href="{OPPORTUNITIES_URL}">Opportunities</a>
            <a href="{METHOD_URL}">Method</a>
            <a href="{COMPARE_URL}">Compare</a>
            <a href="{DOWNLOADS_URL}">Downloads</a>
            <a href="{REPO_URL}">GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero-shell">
            <div class="eyebrow">FrontierGraph explorer</div>
            <h1 class="hero-title">Explore the concept graph and ranked opportunities.</h1>
            <p class="hero-copy">
                FrontierGraph maps the literature into a concept graph, ranks underexplored links, and keeps ontology
                comparison visible. The default product surface is Baseline exploratory with deterministic duplicate
                cleanup on the public recommendation layer.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    env_db = os.environ.get("ECON_OPPORTUNITY_DB", "").strip()
    concept_env_db = os.environ.get("ECON_CONCEPT_DB", "").strip()
    db_default = env_db or (
        "data/processed/app_causalclaims.db"
        if Path("data/processed/app_causalclaims.db").exists()
        else "data/processed/app.db"
    )
    concept_default = concept_env_db or (
        "data/production/frontiergraph_concept_beta/concept_beta_app.sqlite"
        if Path("data/production/frontiergraph_concept_beta/concept_beta_app.sqlite").exists()
        else ""
    )
    concept_strict_default = (
        "data/production/frontiergraph_concept_v3/concept_hard_app.sqlite"
        if Path("data/production/frontiergraph_concept_v3/concept_hard_app.sqlite").exists()
        else ""
    )
    concept_exploratory_default = (
        "data/production/frontiergraph_concept_v3/concept_exploratory_app.sqlite"
        if Path("data/production/frontiergraph_concept_v3/concept_exploratory_app.sqlite").exists()
        else ""
    )
    compare_root = Path("data/production/frontiergraph_concept_compare_v1")
    regime_db_map: dict[str, dict[str, str]] = {}
    selected_ontology = "Legacy JEL"
    selected_mapping = ""
    for regime_name, regime_label in [
        ("broad", "Broad"),
        ("baseline", "Baseline"),
        ("conservative", "Conservative"),
    ]:
        regime_dir = compare_root / regime_name
        strict_db = regime_dir / "concept_hard_app.sqlite"
        exploratory_db = regime_dir / "concept_exploratory_app.sqlite"
        if regime_name == "baseline":
            suppression_dir = regime_dir / "suppression"
            suppressed_topk = suppression_dir / "concept_exploratory_suppressed_top100k_app.sqlite"
            suppressed_exploratory = suppression_dir / "concept_exploratory_suppressed_app.sqlite"
            if suppressed_topk.exists():
                exploratory_db = suppressed_topk
            elif suppressed_exploratory.exists():
                exploratory_db = suppressed_exploratory
        if strict_db.exists() or exploratory_db.exists():
            regime_db_map[regime_label] = {
                "Strict": str(strict_db) if strict_db.exists() else "",
                "Exploratory": str(exploratory_db) if exploratory_db.exists() else "",
            }

    with st.expander("Advanced settings", expanded=False):
        ontology_options = ["Legacy JEL"]
        ontology_options.extend(label for label in ["Baseline", "Broad", "Conservative"] if label in regime_db_map)
        env_concept_exists = bool(concept_env_db and Path(concept_env_db).exists())
        if not regime_db_map:
            if env_concept_exists:
                ontology_options.append("Baseline")
            elif concept_exploratory_default or concept_strict_default:
                ontology_options.append("Concept beta")
            elif concept_default and Path(concept_default).exists():
                ontology_options.append("Concept beta")
        default_ontology = "Baseline" if "Baseline" in ontology_options else ("Concept beta" if "Concept beta" in ontology_options else "Legacy JEL")
        selected_ontology = st.radio(
            "Ontology",
            options=ontology_options,
            horizontal=True,
            index=ontology_options.index(default_ontology),
        )
        if selected_ontology == "Legacy JEL":
            db_value = db_default
        elif selected_ontology == "Baseline" and not regime_db_map and env_concept_exists:
            selected_mapping = st.radio(
                "Concept mapping",
                options=["Exploratory"],
                horizontal=True,
                index=0,
            )
            db_value = concept_env_db
        elif selected_ontology in regime_db_map:
            available_mapping_modes = [mode for mode, path in regime_db_map[selected_ontology].items() if path]
            default_mapping = "Exploratory" if "Exploratory" in available_mapping_modes else available_mapping_modes[0]
            selected_mapping = st.radio(
                "Concept mapping",
                options=available_mapping_modes,
                horizontal=True,
                index=available_mapping_modes.index(default_mapping),
            )
            db_value = regime_db_map[selected_ontology][selected_mapping]
        else:
            concept_mode_options = []
            if concept_exploratory_default:
                concept_mode_options.append(("Exploratory", concept_exploratory_default))
            if concept_strict_default:
                concept_mode_options.append(("Strict", concept_strict_default))
            if concept_default and Path(concept_default).exists():
                concept_mode_options.append(("Beta", concept_default))
            labels = [label for label, _path in concept_mode_options]
            selected_mapping = st.radio(
                "Concept mapping",
                options=labels,
                horizontal=True,
                index=0,
            )
            db_value = dict(concept_mode_options)[selected_mapping]
        db_path = st.text_input(
            "SQLite DB path",
            value=db_value,
            help="Change this only if you are pointing the app at a different local SQLite build.",
        )

    if not Path(db_path).exists():
        st.error(f"Database not found: {db_path}")
        st.stop()

    app_mode = load_app_mode(db_path)
    nodes_df = load_nodes_cached(db_path)
    candidates_df = load_candidate_summary_cached(db_path)
    if nodes_df.empty or candidates_df.empty:
        st.error("The database is missing the node or candidate tables needed by the app.")
        st.stop()

    if is_concept_mode(app_mode):
        mode_label = f"{selected_ontology} {selected_mapping}".strip()
        st.caption(
            f"Default concept surface: {mode_label}. Use Advanced settings only when you want to compare ontology regimes or switch to the legacy JEL view."
        )
    else:
        st.caption("Legacy JEL is available as a coarse fallback browse layer. The public product default lives in the concept regimes.")

    default_preset = normalize_preset(query_param("preset"))
    default_search = query_param("search")
    default_source_field = query_param("source_field")
    default_target_field = query_param("target_field")
    default_cross_field = parse_flag(query_param("only_cross_field"), default=False)

    available_fields = sorted(set(candidates_df["source_field"]) | set(candidates_df["target_field"]))
    novelty_options = list(NOVELTY_LABELS.values())
    max_base_score = max(to_float(candidates_df["score"].max(), default=0.01), 0.01)
    default_min_score = min(0.18, round(max_base_score, 3))
    slider_max = max(5, int(min(candidates_df["cooc_count"].quantile(0.99), 250)))

    with st.expander("Refine the ranking", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            preset_options = list(PRESET_HELP.keys())
            preset = st.selectbox("Ranking mode", options=preset_options, index=preset_options.index(default_preset))
            search_text = st.text_input("Keyword filter", value=default_search)
            top_n = st.slider("Shortlist size", min_value=10, max_value=150, value=30, step=10)
        with col2:
            source_fields = st.multiselect(
                "From groups" if is_concept_mode(app_mode) else "From fields",
                options=available_fields,
                default=[default_source_field] if default_source_field in available_fields else [],
                format_func=lambda code: field_option_label(code, app_mode=app_mode),
            )
            target_fields = st.multiselect(
                "To groups" if is_concept_mode(app_mode) else "To fields",
                options=available_fields,
                default=[default_target_field] if default_target_field in available_fields else [],
                format_func=lambda code: field_option_label(code, app_mode=app_mode),
            )
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
            only_cross_field = st.checkbox(
                "Only cross-bucket ideas" if is_concept_mode(app_mode) else "Only cross-field ideas",
                value=default_cross_field,
            )

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

    ranker_tab, radar_tab, concept_tab, method_tab = st.tabs(
        ["Ranker", "Bucket map" if is_concept_mode(app_mode) else "Field map", "Concepts", "Method"]
    )

    with ranker_tab:
        render_ranker_tab(db_path, filtered_df, preset, top_n=top_n, app_mode=app_mode)

    with radar_tab:
        render_field_radar_tab(filtered_df, app_mode=app_mode)

    with concept_tab:
        render_concept_tab(db_path, nodes_df)

    with method_tab:
        render_method_tab(filtered_df, preset)


if __name__ == "__main__":
    main()
