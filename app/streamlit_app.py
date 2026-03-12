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
    direct_literature_status,
    is_concept_mode,
    load_app_mode,
    load_candidate_summary,
    load_nodes,
    public_pair_label,
    recommendation_play,
    to_float,
    to_int,
)

SITE_URL = "https://frontiergraph.com"
QUESTIONS_URL = f"{SITE_URL}/questions/"
HOW_IT_WORKS_URL = f"{SITE_URL}/how-it-works/"
SHORTLIST_MODE_TO_PRESET = {
    "General browse": "Balanced",
    "More exploratory": "Bold frontier",
    "Closer to paper-ready": "Fast follow",
}
PRESET_TO_SHORTLIST_MODE = {value: key for key, value in SHORTLIST_MODE_TO_PRESET.items()}
SHORTLIST_MODE_HELP = {
    "General browse": "A broad default for browsing questions that could plausibly become the next paper.",
    "More exploratory": "Pushes toward questions that look less worked through and more boundary-crossing.",
    "Closer to paper-ready": "Favors questions that already look closer to a direct next paper.",
}
QUESTION_STYLE_LABELS = {
    "Within-field gap": "More open within one area",
    "Cross-field gap": "More open across areas",
    "Within-field boundary": "More grounded within one area",
    "Cross-field boundary": "More grounded across areas",
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


@st.cache_data(show_spinner="Loading ranked research questions...")
def load_candidate_summary_cached(db_path: str) -> pd.DataFrame:
    return load_candidate_summary(db_path)


def query_df(db_path: str, sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect_readonly(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def format_rank(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "Not available"
    return str(int(numeric))


def source_target_context(row: pd.Series) -> str:
    return f"{row['source_field_name']} and {row['target_field_name']}"


def shortlist_pair_label(row: pd.Series) -> str:
    return public_pair_label(row)


def shortlist_direct_status(row: pd.Series) -> str:
    return direct_literature_status(row.get("cooc_count", 0))


def representative_paper_preview(papers_df: pd.DataFrame, limit: int = 3) -> pd.DataFrame:
    if papers_df.empty:
        return pd.DataFrame(columns=["title", "year", "edge_src", "edge_dst"])
    deduped = papers_df.drop_duplicates(subset=["paper_id"], keep="first").copy()
    return deduped.head(limit).loc[:, ["title", "year", "edge_src", "edge_dst"]]


def mediator_preview(mediators_df: pd.DataFrame, limit: int = 3) -> list[str]:
    if mediators_df.empty:
        return []
    label_column = "mediator_label" if "mediator_label" in mediators_df.columns else "mediator"
    labels = mediators_df[label_column].fillna("").astype(str)
    cleaned = [label.strip() for label in labels.tolist() if label and label.strip()]
    return cleaned[:limit]


def render_bullet_list(items: list[str]) -> None:
    for item in items:
        st.markdown(f"- {item}")


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
        SELECT cm.rank, cm.mediator, COALESCE(n.label, cm.mediator) AS mediator_label, cm.score
        FROM candidate_mediators cm
        LEFT JOIN nodes n ON cm.mediator = n.code
        WHERE cm.candidate_u = ? AND cm.candidate_v = ?
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


def normalize_shortlist_mode(value: str) -> str:
    normalized = value.strip().lower()
    for mode in SHORTLIST_MODE_TO_PRESET:
        if mode.lower() == normalized:
            return mode
    for preset, mode in PRESET_TO_SHORTLIST_MODE.items():
        if preset.lower() == normalized:
            return mode
    return "General browse"


def parse_flag(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def candidate_option_label(row: pd.Series) -> str:
    rank = to_int(row.get("priority_rank", 0), default=0)
    return f"#{rank} {shortlist_pair_label(row)}"


def pair_key_for_row(row: pd.Series) -> str:
    pair_key = str(row.get("pair_key", "")).strip()
    if pair_key:
        return pair_key
    return f"{row.get('u', '')}__{row.get('v', '')}"


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
    out["direct_literature"] = working["cooc_count"].map(direct_literature_status)
    out["next_study_shape"] = working.apply(recommendation_play, axis=1)
    return out.rename(
        columns={
            "priority_rank": "rank",
            "score": "base_score",
            "opportunity": "research_question",
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
    working["public_pair"] = working.apply(shortlist_pair_label, axis=1)
    working["direct_literature"] = working["cooc_count"].map(direct_literature_status)
    working["next_study_shape"] = working.apply(recommendation_play, axis=1)

    return (
        working[
            [
                "priority_rank",
                "public_pair",
                "direct_literature",
                "next_study_shape",
                "mediator_count",
            ]
        ]
        .rename(
            columns={
                "priority_rank": "Rank",
                "public_pair": "Question",
                "direct_literature": "Papers on this exact question",
                "next_study_shape": "Likely study shape",
                "mediator_count": "Related ideas",
            }
        )
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


def render_ranker_tab(db_path: str, filtered_df: pd.DataFrame, shortlist_mode: str, top_n: int, app_mode: str) -> None:
    st.subheader("Questions worth checking")
    st.caption(SHORTLIST_MODE_HELP[shortlist_mode])

    if filtered_df.empty:
        st.warning("No research questions match the current filters. Relax the filters or switch shortlist mode.")
        return

    shortlist_df = filtered_df.head(int(top_n)).reset_index(drop=True)
    st.caption(f"Showing {len(shortlist_df):,} questions from {len(filtered_df):,} visible matches under the current settings.")

    st.dataframe(shortlist_view(shortlist_df), use_container_width=True, hide_index=True)

    options_df = shortlist_df.head(min(100, len(shortlist_df))).reset_index(drop=True)
    pair_lookup = {pair_key_for_row(options_df.loc[i]): options_df.loc[i] for i in options_df.index}
    selected_idx = st.selectbox(
        "Inspect one question in detail",
        options=options_df.index,
        format_func=lambda i: candidate_option_label(options_df.loc[i]),
    )
    selected_row = options_df.loc[int(selected_idx)]
    selected_pair_key = pair_key_for_row(selected_row)

    available_pair_keys = list(pair_lookup.keys())
    saved_compare = [pair for pair in st.session_state.get("compare_pairs_widget", []) if pair in pair_lookup]
    if saved_compare != st.session_state.get("compare_pairs_widget", []):
        st.session_state["compare_pairs_widget"] = saved_compare
    elif "compare_pairs_widget" not in st.session_state:
        st.session_state["compare_pairs_widget"] = []

    compare_button_col, clear_button_col = st.columns([1.3, 1.0])
    with compare_button_col:
        if st.button("Pin selected question", use_container_width=True):
            updated = list(st.session_state.get("compare_pairs_widget", []))
            if selected_pair_key not in updated:
                updated.append(selected_pair_key)
            st.session_state["compare_pairs_widget"] = updated[:4]
    with clear_button_col:
        if st.button("Clear comparison", use_container_width=True):
            st.session_state["compare_pairs_widget"] = []

    compare_pairs = st.multiselect(
        "Pinned questions to compare",
        options=available_pair_keys,
        format_func=lambda pair_key: candidate_option_label(pair_lookup[pair_key]),
        key="compare_pairs_widget",
    )
    if len(compare_pairs) > 4:
        compare_pairs = compare_pairs[:4]
        st.session_state["compare_pairs_widget"] = compare_pairs
        st.warning("Comparison is limited to 4 questions at a time.")

    if len(compare_pairs) >= 2:
        render_question_comparison(db_path, pair_lookup, compare_pairs)

    render_candidate_detail(db_path, selected_row, app_mode=app_mode)

    st.download_button(
        label="Export working shortlist",
        data=filtered_download_frame(shortlist_df).to_csv(index=False),
        file_name="frontiergraph_shortlist.csv",
        mime="text/csv",
    )


def render_question_comparison(
    db_path: str,
    pair_lookup: dict[str, pd.Series],
    compare_pairs: list[str],
) -> None:
    st.markdown("### Compare pinned questions")
    columns = st.columns(len(compare_pairs))
    for column, pair_key in zip(columns, compare_pairs):
        row = pair_lookup[pair_key]
        bundle = load_candidate_bundle(db_path, str(row["u"]), str(row["v"]))
        candidate_row = bundle["candidate_row"]
        mediators_df = bundle["mediators_df"]
        papers_df = bundle["papers_df"]
        direct_status = direct_literature_status(
            candidate_row.get("cooc_count", row.get("cooc_count", 0)) if candidate_row is not None else row.get("cooc_count", 0)
        )
        nearby_labels = mediator_preview(mediators_df)
        paper_preview = representative_paper_preview(papers_df, limit=2)
        related_idea_count = to_int(row.get("mediator_count", 0))

        with column:
            st.markdown(f"**{shortlist_pair_label(row)}**")
            st.caption(f"Likely study shape: {recommendation_play(row)}")
            st.write(f"Papers on this exact question: {direct_status}")
            st.write(f"Related ideas in the current sample: {related_idea_count}")
            if nearby_labels:
                st.caption("Examples: " + ", ".join(nearby_labels))
            else:
                st.caption("No stable mediator preview in the current sample.")
            if paper_preview.empty:
                st.caption("No starter papers were exported for this pair.")
            else:
                st.markdown("**Papers to start with**")
                for paper in paper_preview.itertuples(index=False):
                    year_suffix = f" ({to_int(getattr(paper, 'year', 0))})" if to_int(getattr(paper, "year", 0)) > 0 else ""
                    st.markdown(f"- {getattr(paper, 'title', '')}{year_suffix}")


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
        st.warning("Question details were not found in the database.")
        return

    pair_label = shortlist_pair_label(row)
    direct_status = direct_literature_status(candidate_row.get("cooc_count", row.get("cooc_count", 0)))
    nearby_labels = mediator_preview(mediators_df)
    paper_preview = representative_paper_preview(papers_df)
    next_study_shape = recommendation_play(row)
    verify_steps = [
        "Check direct literature under close synonyms",
        "Inspect nearby linking ideas",
        "Read the papers to start with",
        "Decide whether this is a mechanism, outcome, or setting question",
    ]

    st.markdown("### Selected question")
    st.markdown(f"**{pair_label}**")

    summary_left, summary_right = st.columns([1.35, 1.0])
    with summary_left:
        st.markdown("**Question summary**")
        st.write(f"Papers on this exact question: {direct_status}")
        st.write(f"Likely study shape: {next_study_shape}")
        if nearby_labels:
            st.write(f"Related ideas: {', '.join(nearby_labels)}")
        else:
            st.write("Related ideas: No stable mediator preview in the current public sample")
    with summary_right:
        st.markdown("**What to verify next**")
        render_bullet_list(verify_steps)

    st.markdown("**Papers to start with**")
    if paper_preview.empty:
        st.caption("No starter papers were exported for this pair in the current public sample.")
    else:
        preview_df = paper_preview.rename(
            columns={
                "title": "Paper",
                "year": "Year",
                "edge_src": "Edge source",
                "edge_dst": "Edge target",
            }
        )
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

    brief = build_idea_brief_markdown(
        candidate_row=candidate_row,
        mediators_df=mediators_df,
        paths_df=paths_df,
        papers_df=papers_df,
        neighborhood_row=neighborhood_row,
    )
    st.download_button(
        label="Export working brief",
        data=brief,
        file_name=f"idea_brief_{row['u']}_to_{row['v']}.md",
        mime="text/markdown",
    )

    has_suppression = "base_score" in candidate_row.index
    with st.expander("Technical details", expanded=False):
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
                            {"Metric": "Hard suppression reason", "Value": str(candidate_row.get("hard_same_family_reason", "") or "Not applied")},
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

        evidence_left, evidence_right = st.columns(2)
        with evidence_left:
            st.markdown("**Top mediators**")
            st.dataframe(mediators_df.head(25), use_container_width=True, hide_index=True)
        with evidence_right:
            st.markdown("**Top supporting paths**")
            st.dataframe(paths_df.head(25), use_container_width=True, hide_index=True)

        st.markdown("**Supporting papers behind the candidate paths**")
        st.dataframe(papers_df.head(150), use_container_width=True, hide_index=True)

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


def render_field_radar_tab(filtered_df: pd.DataFrame, app_mode: str) -> None:
    st.subheader("Literature map by group" if is_concept_mode(app_mode) else "Literature map by field")
    if filtered_df.empty:
        st.warning("No research questions to summarize under the current filters.")
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
    st.caption("Use this when you already know the concept you want to trace through the literature map.")

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
    try:
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
    except Exception:
        underexplored = pd.DataFrame(columns=["u", "v", "cooc_count", "first_year_seen", "last_year_seen", "gap_bonus"])

    st.markdown(f"### {concept_label} ({concept_code})")
    left, right = st.columns(2)
    with left:
        st.markdown("**Top outgoing research questions**")
        st.dataframe(outgoing, use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Top incoming research questions**")
        st.dataframe(incoming, use_container_width=True, hide_index=True)

    st.markdown("**Underexplored pairs touching this concept**")
    if underexplored.empty:
        st.caption("No underexplored-pair table was exported for this database build.")
    else:
        st.dataframe(underexplored, use_container_width=True, hide_index=True)


def render_method_tab(filtered_df: pd.DataFrame, preset: str) -> None:
    st.subheader("Method")
    st.markdown(
        f"Use the public <a href=\"{HOW_IT_WORKS_URL}\">How It Works</a> page for interpretation and limits. Use this tab when you want the compact technical summary behind the current evidence view.",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        1. AI extracts paper-local graph structure from titles and abstracts.
        2. FrontierGraph maps those local graphs into concept regimes and ranks missing links with deterministic graph signals.
        3. The public default is Baseline exploratory, with duplicate cleanup applied before the research-question surface is shown.
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
        page_title="FrontierGraph | Workbench",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.markdown(
        f"""
        <div class="app-nav">
            <a href="{SITE_URL}">Site</a>
            <a href="{QUESTIONS_URL}">Research Questions</a>
            <a href="{HOW_IT_WORKS_URL}">How It Works</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="eyebrow">FrontierGraph Workbench</div>
            <h1 class="hero-title">Decide whether a question could become your next paper.</h1>
            <p class="hero-copy">
                Use this as the deeper evidence layer behind the public site. Start with a shortlist, inspect
                related ideas and starter papers, then decide whether the question looks concrete enough to read,
                scope, or test more seriously.
            </p>
            <p class="hero-copy">
                Keep the public interpretation page nearby: <a href="{HOW_IT_WORKS_URL}">How It Works</a> explains how to
                read the product, what is model-extracted, what is deterministic, and where the public build can still fail.
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
    selected_ontology = "Baseline"
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
        ontology_options: list[str] = []
        ontology_options.extend(label for label in ["Baseline", "Broad", "Conservative"] if label in regime_db_map)
        env_concept_exists = bool(concept_env_db and Path(concept_env_db).exists())
        if not regime_db_map:
            if env_concept_exists:
                ontology_options.append("Baseline")
            elif concept_exploratory_default or concept_strict_default:
                ontology_options.append("Concept beta")
            elif concept_default and Path(concept_default).exists():
                ontology_options.append("Concept beta")
        if not ontology_options:
            ontology_options = ["Legacy JEL"]
        default_ontology = "Baseline" if "Baseline" in ontology_options else ("Concept beta" if "Concept beta" in ontology_options else ontology_options[0])
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

    try:
        app_mode = load_app_mode(db_path)
        nodes_df = load_nodes_cached(db_path)
        candidates_df = load_candidate_summary_cached(db_path)
    except sqlite3.Error as exc:
        st.error(f"Could not open the configured database: {db_path}")
        st.caption("The public app uses a read-only SQLite build. If the mounted copy cannot be read in place, FrontierGraph now retries from a local cache.")
        st.code(str(exc))
        st.stop()

    if nodes_df.empty or candidates_df.empty:
        st.error("The database is missing the node or candidate tables needed by the app.")
        st.stop()

    default_shortlist_mode = normalize_shortlist_mode(query_param("preset"))
    default_search = query_param("search")
    default_source_field = query_param("source_field")
    default_target_field = query_param("target_field")
    default_cross_field = parse_flag(query_param("only_cross_field"), default=False)

    available_fields = sorted(set(candidates_df["source_field"]) | set(candidates_df["target_field"]))
    novelty_options = list(NOVELTY_LABELS.values())
    max_base_score = max(to_float(candidates_df["score"].max(), default=0.01), 0.01)
    default_min_score = min(0.18, round(max_base_score, 3))
    slider_max = max(5, int(min(candidates_df["cooc_count"].quantile(0.99), 250)))
    search_col, mode_col = st.columns([1.65, 1.0])
    with search_col:
        search_text = st.text_input("Search by topic or outcome", value=default_search, placeholder="Search by topic or outcome")
    with mode_col:
        shortlist_mode = st.selectbox(
            "Browse mode",
            options=list(SHORTLIST_MODE_TO_PRESET.keys()),
            index=list(SHORTLIST_MODE_TO_PRESET.keys()).index(default_shortlist_mode),
        )
    preset = SHORTLIST_MODE_TO_PRESET[shortlist_mode]

    with st.expander("Refine the list", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            top_n = st.slider("Shortlist size", min_value=10, max_value=150, value=30, step=10)
            novelty_filter = st.multiselect(
                "Question style",
                options=novelty_options,
                default=novelty_options,
                format_func=lambda label: QUESTION_STYLE_LABELS.get(label, label),
            )
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
                "Only cross-bucket questions" if is_concept_mode(app_mode) else "Only cross-field questions",
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

    render_ranker_tab(db_path, filtered_df, shortlist_mode, top_n=top_n, app_mode=app_mode)

    with st.expander("Advanced tools", expanded=False):
        st.caption("Use these only when you want the literature map, direct concept lookup, or the technical method notes.")
        radar_tab, concept_tab, method_tab = st.tabs(
            ["Literature map" if is_concept_mode(app_mode) else "Field map", "Concept lookup", "Method"]
        )

        with radar_tab:
            render_field_radar_tab(filtered_df, app_mode=app_mode)

        with concept_tab:
            render_concept_tab(db_path, nodes_df)

        with method_tab:
            render_method_tab(filtered_df, preset)


if __name__ == "__main__":
    main()
