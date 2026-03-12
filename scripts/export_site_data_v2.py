from __future__ import annotations

import csv
import json
import math
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
GENERATED_DIR = SITE_ROOT / "src" / "generated"
EDITORIAL_OPPORTUNITIES_PATH = SITE_ROOT / "src" / "content" / "editorial-opportunities.json"
PUBLIC_LABEL_GLOSSARY_PATH = SITE_ROOT / "src" / "content" / "public-label-glossary.json"
PUBLIC_DATA_DIR = SITE_ROOT / "public" / "data" / "v2"
NEIGHBORHOOD_SHARDS_DIR = PUBLIC_DATA_DIR / "concept_neighborhoods"
OPPORTUNITY_SHARDS_DIR = PUBLIC_DATA_DIR / "concept_opportunities"

APP_URL = "https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app"
REPO_URL = "https://github.com/prashgarg/frontiergraph"
PUBLIC_DB_URL = os.environ.get(
    "FRONTIERGRAPH_PUBLIC_DB_URL",
    "https://storage.googleapis.com/frontiergraph-public-downloads-1058669339361/frontiergraph-economics-beta.db",
)
DB_FILENAME = "frontiergraph-economics-beta.db"
DB_SHA256 = "e755bcdc3b770fe139dfbbe870be3cc111b10fa95d50f6d6492c70e61c23cde8"
DB_SIZE_GB = 2.33

EXTRACTION_SUMMARY_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_extraction_v2"
    / "fwci_core150_adj150"
    / "analysis"
    / "fwci_core150_adj150_corpus_summary.json"
)
BASELINE_MANIFEST_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "manifest.json"
)
BASELINE_SUPPRESSION_DB_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "suppression"
    / "concept_exploratory_suppressed_top100k_app.sqlite"
)
BASELINE_GRAPH_DB_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "concept_graph_exploratory.sqlite"
)
REGIME_SUMMARY_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_ontology_compare_v1"
    / "analysis"
    / "regime_summary.csv"
)
RANKING_OVERLAP_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_ontology_compare_v1"
    / "analysis"
    / "ranking_overlap_top100.csv"
)
SENSITIVITY_SUMMARY_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_ontology_compare_v1"
    / "analysis"
    / "sensitivity_summary.md"
)
SUPPRESSION_SUMMARY_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "suppression"
    / "analysis"
    / "suppression_summary.json"
)
TOP100_BEFORE_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "suppression"
    / "analysis"
    / "top100_before.csv"
)
TOP100_AFTER_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "suppression"
    / "analysis"
    / "top100_after.csv"
)
REMOVED_BY_HARD_BLOCK_PATH = (
    ROOT
    / "data"
    / "production"
    / "frontiergraph_concept_compare_v1"
    / "baseline"
    / "suppression"
    / "analysis"
    / "removed_by_hard_block.csv"
)

BACKBONE_NODE_LIMIT = 650
BACKBONE_EDGE_LIMIT = 2200
BACKBONE_MIN_SUPPORT = 4
BACKBONE_LABEL_LIMIT = 24
BACKBONE_LAYOUT_ITERATIONS = 140
BACKBONE_LAYOUT_K_MULTIPLIER = 2.8
BACKBONE_LAYOUT_SPREAD = 1.38
NEIGHBOR_LIMIT = 15
CONCEPT_OPPORTUNITY_LIMIT = 12
FEATURED_OPPORTUNITY_LIMIT = 12
SHARD_SIZE = 256
EDITORIAL_REQUIRED_FIELDS = (
    "pair_key",
    "question_title",
    "short_why",
    "first_next_step",
    "who_its_for",
    "homepage_featured",
    "questions_featured",
    "display_order",
    "homepage_role",
)

PUBLIC_LABEL_GLOSSARY_REQUIRED_FIELDS = (
    "concept_id",
    "subtitle",
)


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def to_int(value: Any, default: int = 0) -> int:
    return int(round(to_float(value, float(default))))


def clean_public_text(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "na", "n/a", "nan", "none", "null", "undefined"}:
        return ""
    return text


def parse_json_list(raw: Any) -> list[Any]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    try:
        loaded = json.loads(raw)
    except Exception:
        return []
    return loaded if isinstance(loaded, list) else []


def normalize_bucket_profile(raw: Any) -> dict[str, int]:
    profile: dict[str, int] = {}
    for item in parse_json_list(raw):
        if isinstance(item, dict):
            profile[str(item.get("value", ""))] = int(item.get("count", 0))
    return profile


def top_values(raw: Any, limit: int = 3) -> list[str]:
    values: list[str] = []
    for item in parse_json_list(raw)[:limit]:
        if isinstance(item, dict) and item.get("value"):
            text = clean_public_text(item["value"])
            if text:
                values.append(text)
        elif isinstance(item, str):
            text = clean_public_text(item)
            if text:
                values.append(text)
    return values


def uniq_keep_order(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = clean_public_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
        if limit is not None and len(out) >= limit:
            break
    return out


def bucket_priority(bucket_hint: str | None) -> tuple[int, str]:
    normalized = clean_public_text(bucket_hint).lower()
    if normalized == "core":
        return (0, normalized)
    if normalized == "mixed":
        return (1, normalized)
    if normalized == "adjacent":
        return (2, normalized)
    return (3, normalized)


def stable_public_pair_label(
    left_label: str,
    right_label: str,
    left_bucket: str | None,
    right_bucket: str | None,
) -> str:
    left = (bucket_priority(left_bucket), clean_public_text(left_label).lower(), clean_public_text(left_label))
    right = (bucket_priority(right_bucket), clean_public_text(right_label).lower(), clean_public_text(right_label))
    ordered = sorted([left, right], key=lambda item: (item[0], item[1]))
    return f"{ordered[0][2]} and {ordered[1][2]}"


def public_label_payload(
    concept_id: str | None,
    raw_label: Any,
    glossary: dict[str, dict[str, Any]],
) -> dict[str, str]:
    label = clean_public_text(raw_label) or str(concept_id or "")
    entry = glossary.get(str(concept_id or ""), {})
    plain_label = clean_public_text(entry.get("plain_label")) or label
    subtitle = clean_public_text(entry.get("subtitle"))
    return {
        "plain_label": plain_label,
        "subtitle": subtitle,
    }


def public_slice_label(values: dict[str, Any]) -> str:
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    gap_bonus = to_float(values.get("gap_bonus", 0.0))
    cross_bucket = bool(values.get("cross_bucket", False))
    if cooc_count <= 0:
        return "Missing direct link"
    if path_support >= 0.95:
        return "Ready to follow through"
    if gap_bonus >= 0.85 and cooc_count <= 2:
        return "Early but promising"
    if cross_bucket:
        return "Connect separate literatures"
    return "Support from nearby literature"


def direct_link_status(cooc_count: int) -> str:
    if cooc_count <= 0:
        return "No direct papers yet"
    if cooc_count == 1:
        return "One direct paper so far"
    if cooc_count <= 5:
        return "A few direct papers already exist"
    return "Direct work already exists"


def recommended_move(values: dict[str, Any]) -> str:
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    mediator_count = to_int(values.get("mediator_count", 0))
    cross_bucket = bool(values.get("cross_bucket", False))
    if cross_bucket and cooc_count <= 0:
        return "Start with a bridge review or cross-field pilot."
    if path_support >= 0.95 and mediator_count >= 10:
        return "This looks ready for a direct empirical follow-through."
    if cooc_count <= 0:
        return "Treat this as a missing direct test, not a settled result."
    return "Use this as a focused follow-up question in the nearby literature."


def plain_language_context(values: list[str], fallback: str) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return fallback
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{cleaned[0]}, {cleaned[1]}, and related settings"


def why_now(values: dict[str, Any]) -> str:
    source_label = str(values.get("u_preferred_label") or values.get("source_label") or "")
    target_label = str(values.get("v_preferred_label") or values.get("target_label") or "")
    mediator_count = to_int(values.get("mediator_count", 0))
    cooc_count = to_int(values.get("cooc_count", 0))
    path_support = to_float(values.get("path_support_norm", 0.0))
    support_level = "strong" if path_support >= 0.95 else "visible"
    if cooc_count <= 0:
        return (
            f"{source_label} and {target_label} are close in the surrounding graph, "
            f"but the public sample shows no direct papers linking them yet."
        )
    if cooc_count == 1:
        direct_copy = "one direct paper so far"
    elif cooc_count <= 5:
        direct_copy = f"{cooc_count} direct papers so far"
    else:
        direct_copy = "an existing direct literature in the public sample"
    return (
        f"{source_label} and {target_label} already have {direct_copy}, "
        f"while {mediator_count} nearby concepts provide {support_level} support for a more direct follow-up."
    )


def resolve_top_mediator_labels(
    raw: Any,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in parse_json_list(raw):
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("mediator", "")).strip()
        if not concept_id:
            continue
        raw_label = concept_label_lookup.get(concept_id, concept_id)
        public_label = public_label_payload(concept_id, raw_label, glossary)["plain_label"]
        if not public_label or public_label in seen:
            continue
        seen.add(public_label)
        labels.append(public_label)
        if len(labels) >= limit:
            break
    return labels


def load_representative_papers() -> dict[tuple[str, str], list[dict[str, Any]]]:
    sql = """
        WITH deduped AS (
            SELECT
                candidate_u,
                candidate_v,
                path_rank,
                paper_rank,
                paper_id,
                title,
                year,
                edge_src,
                edge_dst,
                ROW_NUMBER() OVER (
                    PARTITION BY candidate_u, candidate_v, paper_id
                    ORDER BY path_rank, paper_rank
                ) AS paper_occurrence_rank
            FROM candidate_papers
        ),
        limited AS (
            SELECT
                candidate_u,
                candidate_v,
                paper_id,
                title,
                year,
                edge_src,
                edge_dst,
                ROW_NUMBER() OVER (
                    PARTITION BY candidate_u, candidate_v
                    ORDER BY path_rank, paper_rank, year DESC, paper_id
                ) AS representative_rank
            FROM deduped
            WHERE paper_occurrence_rank = 1
        )
        SELECT
            candidate_u,
            candidate_v,
            paper_id,
            title,
            year,
            edge_src,
            edge_dst
        FROM limited
        WHERE representative_rank <= 3
        ORDER BY candidate_u, candidate_v, representative_rank
    """

    with connect(BASELINE_SUPPRESSION_DB_PATH) as conn:
        rows = conn.execute(sql).fetchall()

    lookup: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate_u, candidate_v, paper_id, title, year, edge_src, edge_dst in rows:
        lookup[(str(candidate_u), str(candidate_v))].append(
            {
                "paper_id": str(paper_id),
                "title": clean_public_text(title),
                "year": to_int(year),
                "edge_src": str(edge_src),
                "edge_dst": str(edge_dst),
            }
        )
    return lookup


def opportunity_record(
    row: sqlite3.Row | tuple[Any, ...],
    columns: list[str],
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    values = dict(zip(columns, row))
    pair_query = quote(f"{values['u_preferred_label']} -> {values['v_preferred_label']}")
    cooc_count = to_int(values["cooc_count"])
    top_source = top_values(values["u_top_countries"], limit=3)
    top_target = top_values(values["v_top_countries"], limit=3)
    source_public = public_label_payload(values["u"], values["u_preferred_label"], glossary)
    target_public = public_label_payload(values["v"], values["v_preferred_label"], glossary)
    cross_field = clean_public_text(values.get("u_bucket_hint")) != clean_public_text(values.get("v_bucket_hint"))
    representative_papers = [
        paper
        for paper in representative_papers_lookup.get((str(values["u"]), str(values["v"])), [])
        if clean_public_text(paper.get("title"))
    ]
    return {
        "pair_key": values["pair_key"],
        "source_id": values["u"],
        "target_id": values["v"],
        "source_label": values["u_preferred_label"],
        "target_label": values["v_preferred_label"],
        "source_bucket": values["u_bucket_hint"],
        "target_bucket": values["v_bucket_hint"],
        "cross_field": cross_field,
        "score": round(to_float(values["score"]), 6),
        "base_score": round(to_float(values["base_score"]), 6),
        "duplicate_penalty": round(to_float(values.get("duplicate_penalty", 0.0)), 6),
        "path_support_norm": round(to_float(values["path_support_norm"]), 6),
        "gap_bonus": round(to_float(values["gap_bonus"]), 6),
        "mediator_count": to_int(values["mediator_count"]),
        "motif_count": to_int(values["motif_count"]),
        "cooc_count": cooc_count,
        "direct_link_status": direct_link_status(cooc_count),
        "supporting_path_count": to_int(values["mediator_count"]),
        "why_now": why_now(values),
        "recommended_move": recommended_move(values),
        "slice_label": public_slice_label(values),
        "public_pair_label": stable_public_pair_label(
            source_public["plain_label"],
            target_public["plain_label"],
            values.get("u_bucket_hint"),
            values.get("v_bucket_hint"),
        ),
        "top_mediator_labels": resolve_top_mediator_labels(values.get("top_mediators_json"), concept_label_lookup, glossary, limit=3),
        "representative_papers": representative_papers,
        "top_countries_source": top_source,
        "top_countries_target": top_target,
        "source_context_summary": plain_language_context(top_source, "No dominant source setting in the current public sample"),
        "target_context_summary": plain_language_context(top_target, "No dominant target setting in the current public sample"),
        "app_link": f"{APP_URL}?search={pair_query}",
    }


def export_rows_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_candidates() -> pd.DataFrame:
    with connect(BASELINE_SUPPRESSION_DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM candidates ORDER BY score DESC", conn)


def load_node_details() -> pd.DataFrame:
    with connect(BASELINE_SUPPRESSION_DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM node_details", conn)


def load_graph_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with connect(BASELINE_GRAPH_DB_PATH) as conn:
        edges = pd.read_sql_query("SELECT * FROM concept_edges", conn)
        profiles = pd.read_sql_query("SELECT * FROM concept_edge_profiles", conn)
        contexts = pd.read_sql_query("SELECT * FROM concept_edge_contexts", conn)
        exemplars = pd.read_sql_query("SELECT * FROM concept_edge_exemplars", conn)
    return edges, profiles, contexts, exemplars


def add_slice_flags(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working["cross_bucket"] = working["u_bucket_hint"] != working["v_bucket_hint"]
    working["bridge_flag"] = working["cross_bucket"]
    working["frontier_flag"] = working["cooc_count"].fillna(0) <= 1
    working["fast_follow_flag"] = (working["cooc_count"].fillna(0) > 0) & (working["path_support_norm"].fillna(0) >= 0.95)
    gap_cut = float(working["gap_bonus"].quantile(0.85)) if len(working) else 0.0
    working["underexplored_flag"] = (working["cooc_count"].fillna(0) <= 2) & (working["gap_bonus"].fillna(0) >= gap_cut)
    return working


def build_slices(
    df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    columns = list(df.columns)
    def top_records(mask: pd.Series | None, limit: int = 100) -> list[dict[str, Any]]:
        if mask is None:
            subset = df.head(limit)
        else:
            subset = df.loc[mask].head(limit)
        subset_rows = [tuple(row) for row in subset.itertuples(index=False, name=None)]
        return [opportunity_record(row, columns, concept_label_lookup, glossary, representative_papers_lookup) for row in subset_rows]

    return {
        "overall": top_records(None),
        "bridges": top_records(df["bridge_flag"]),
        "frontier": top_records(df["frontier_flag"]),
        "fast_follow": top_records(df["fast_follow_flag"]),
        "underexplored": top_records(df["underexplored_flag"]),
    }


def compute_centrality(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> tuple[pd.DataFrame, nx.DiGraph]:
    graph = nx.DiGraph()
    for row in nodes_df.itertuples(index=False):
        graph.add_node(row.concept_id)
    for row in edges_df.itertuples(index=False):
        graph.add_edge(
            row.source_concept_id,
            row.target_concept_id,
            weight=float(row.support_count),
            distinct_papers=int(row.distinct_papers),
            avg_stability=float(row.avg_stability),
        )
    pagerank = nx.pagerank(graph, weight="weight")
    metrics: list[dict[str, Any]] = []
    for concept_id in graph.nodes:
        in_support = float(graph.in_degree(concept_id, weight="weight"))
        out_support = float(graph.out_degree(concept_id, weight="weight"))
        metrics.append(
            {
                "concept_id": concept_id,
                "in_degree": int(graph.in_degree(concept_id)),
                "out_degree": int(graph.out_degree(concept_id)),
                "weighted_in_degree": in_support,
                "weighted_out_degree": out_support,
                "weighted_degree": in_support + out_support,
                "pagerank": float(pagerank.get(concept_id, 0.0)),
                "neighbor_count": len(set(graph.predecessors(concept_id)) | set(graph.successors(concept_id))),
            }
        )
    metrics_df = pd.DataFrame(metrics)
    metrics_df.sort_values(["weighted_degree", "pagerank"], ascending=[False, False], inplace=True)
    return metrics_df, graph


def scale_positions(raw_positions: dict[str, tuple[float, float]], spread: float = 1.0) -> dict[str, dict[str, float]]:
    xs = [float(pos[0]) for pos in raw_positions.values()]
    ys = [float(pos[1]) for pos in raw_positions.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = max(x_max - x_min, 1e-9)
    y_span = max(y_max - y_min, 1e-9)
    scaled: dict[str, dict[str, float]] = {}
    for node, (x, y) in raw_positions.items():
        x_norm = (float(x) - x_min) / x_span
        y_norm = (float(y) - y_min) / y_span
        scaled[node] = {
            "x": round(0.5 + ((x_norm - 0.5) * spread), 6),
            "y": round(0.5 + ((y_norm - 0.5) * spread), 6),
        }
    return scaled


def node_bucket_group(bucket_hint: str | None) -> str:
    value = (bucket_hint or "").lower()
    if "core" in value and "adjacent" not in value and "mixed" not in value:
        return "core"
    if "adjacent" in value and "core" not in value and "mixed" not in value:
        return "adjacent"
    return "mixed"


def build_backbone(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    node_metrics_df: pd.DataFrame,
    edge_profiles_df: pd.DataFrame,
    edge_contexts_df: pd.DataFrame,
    edge_exemplars_df: pd.DataFrame,
    glossary: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    top_node_ids = set(node_metrics_df.head(BACKBONE_NODE_LIMIT)["concept_id"])
    edges_subset = edges_df[
        edges_df["source_concept_id"].isin(top_node_ids) & edges_df["target_concept_id"].isin(top_node_ids)
    ].copy()
    edges_subset = edges_subset[edges_subset["support_count"] >= BACKBONE_MIN_SUPPORT].copy()
    edges_subset.sort_values(["support_count", "distinct_papers"], ascending=[False, False], inplace=True)
    edges_subset = edges_subset.head(BACKBONE_EDGE_LIMIT)

    undirected = nx.Graph()
    for row in edges_subset.itertuples(index=False):
        undirected.add_edge(row.source_concept_id, row.target_concept_id, weight=float(row.support_count))
    if undirected.number_of_nodes() == 0:
        return {"nodes": [], "edges": []}, []
    component_nodes = max(nx.connected_components(undirected), key=len)
    component_edges = edges_subset[
        edges_subset["source_concept_id"].isin(component_nodes) & edges_subset["target_concept_id"].isin(component_nodes)
    ].copy()
    layout_graph = undirected.subgraph(component_nodes).copy()
    layout_k = BACKBONE_LAYOUT_K_MULTIPLIER / math.sqrt(max(layout_graph.number_of_nodes(), 1))
    positions_raw = nx.spring_layout(
        layout_graph,
        seed=7,
        weight="weight",
        iterations=BACKBONE_LAYOUT_ITERATIONS,
        k=layout_k,
    )
    positions = scale_positions(positions_raw, spread=BACKBONE_LAYOUT_SPREAD)

    node_details = nodes_df.set_index("concept_id").to_dict("index")
    central_metrics = node_metrics_df.set_index("concept_id").to_dict("index")
    edge_profiles = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_profiles_df.itertuples(index=False)
    }
    edge_contexts = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_contexts_df.itertuples(index=False)
    }
    edge_exemplars_map: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in edge_exemplars_df.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        if len(edge_exemplars_map[key]) >= 3:
            continue
        edge_exemplars_map[key].append(
            {
                "title": row.title,
                "year": row.year,
                "bucket": row.bucket,
                "evidence_text": row.evidence_text,
            }
        )

    label_nodes = set(node_metrics_df[node_metrics_df["concept_id"].isin(component_nodes)].head(BACKBONE_LABEL_LIMIT)["concept_id"])

    backbone_nodes: list[dict[str, Any]] = []
    for concept_id in component_nodes:
        detail = node_details.get(concept_id, {})
        metrics = central_metrics.get(concept_id, {})
        pos = positions.get(concept_id, {"x": 0.5, "y": 0.5})
        aliases = uniq_keep_order(parse_json_list(detail.get("aliases_json")), limit=8)
        public_label = public_label_payload(concept_id, detail.get("preferred_label", concept_id), glossary)
        backbone_nodes.append(
            {
                "id": concept_id,
                "label": detail.get("preferred_label", concept_id),
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "aliases": aliases,
                "alias_count": len(parse_json_list(detail.get("aliases_json"))),
                "bucket_hint": detail.get("bucket_hint", "unknown"),
                "instance_support": int(detail.get("instance_support", 0) or 0),
                "distinct_paper_support": int(detail.get("distinct_paper_support", 0) or 0),
                "top_countries": top_values(detail.get("top_countries"), limit=3),
                "top_units": top_values(detail.get("top_units"), limit=3),
                "x": pos["x"],
                "y": pos["y"],
                "weighted_degree": round(float(metrics.get("weighted_degree", 0.0)), 4),
                "pagerank": round(float(metrics.get("pagerank", 0.0)), 8),
                "in_degree": int(metrics.get("in_degree", 0) or 0),
                "out_degree": int(metrics.get("out_degree", 0) or 0),
                "neighbor_count": int(metrics.get("neighbor_count", 0) or 0),
                "bucket_group": node_bucket_group(detail.get("bucket_hint", "unknown")),
                "show_label": concept_id in label_nodes,
            }
        )

    backbone_edges: list[dict[str, Any]] = []
    for row in component_edges.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        profile = edge_profiles.get(key)
        context = edge_contexts.get(key)
        backbone_edges.append(
            {
                "id": f"{row.source_concept_id}__{row.target_concept_id}",
                "source": row.source_concept_id,
                "target": row.target_concept_id,
                "support_count": int(row.support_count),
                "distinct_papers": int(row.distinct_papers),
                "avg_stability": round(float(row.avg_stability), 4),
                "strength": round(min(1.0, 0.22 + math.log1p(float(row.support_count)) / 3.4), 4),
                "directionality_mix": parse_json_list(getattr(profile, "directionality_json", "[]")) if profile else [],
                "relationship_type_mix": parse_json_list(getattr(profile, "relationship_type_json", "[]")) if profile else [],
                "edge_role_mix": parse_json_list(getattr(profile, "edge_role_json", "[]")) if profile else [],
                "dominant_countries": top_values(getattr(context, "dominant_countries_json", "[]"), limit=3) if context else [],
                "dominant_units": top_values(getattr(context, "dominant_units_json", "[]"), limit=3) if context else [],
                "dominant_years": parse_json_list(getattr(context, "dominant_years_json", "[]")) if context else [],
                "examples": edge_exemplars_map.get(key, []),
            }
        )

    backbone_nodes.sort(key=lambda row: row["weighted_degree"], reverse=True)
    backbone_edges.sort(key=lambda row: row["support_count"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "nodes": len(backbone_nodes),
            "edges": len(backbone_edges),
        },
        "nodes": backbone_nodes,
        "edges": backbone_edges,
    }, backbone_nodes


def build_neighborhoods(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    edge_profiles_df: pd.DataFrame,
    edge_contexts_df: pd.DataFrame,
) -> dict[str, Any]:
    node_label_map = nodes_df.set_index("concept_id")["preferred_label"].to_dict()
    edge_profile_map = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_profiles_df.itertuples(index=False)
    }
    edge_context_map = {
        (row.source_concept_id, row.target_concept_id): row
        for row in edge_contexts_df.itertuples(index=False)
    }
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges_df.itertuples(index=False):
        key = (row.source_concept_id, row.target_concept_id)
        profile = edge_profile_map.get(key)
        context = edge_context_map.get(key)
        payload = {
            "concept_id": row.target_concept_id,
            "label": node_label_map.get(row.target_concept_id, row.target_concept_id),
            "support_count": int(row.support_count),
            "distinct_papers": int(row.distinct_papers),
            "avg_stability": round(float(row.avg_stability), 4),
            "directionality_mix": parse_json_list(getattr(profile, "directionality_json", "[]")) if profile else [],
            "relationship_type_mix": parse_json_list(getattr(profile, "relationship_type_json", "[]")) if profile else [],
            "edge_role_mix": parse_json_list(getattr(profile, "edge_role_json", "[]")) if profile else [],
            "dominant_countries": top_values(getattr(context, "dominant_countries_json", "[]"), limit=3) if context else [],
        }
        outgoing[row.source_concept_id].append(payload)
        incoming[row.target_concept_id].append(
            {
                **payload,
                "concept_id": row.source_concept_id,
                "label": node_label_map.get(row.source_concept_id, row.source_concept_id),
            }
        )

    neighborhoods: dict[str, Any] = {}
    for concept_id in node_label_map:
        out_list = sorted(outgoing.get(concept_id, []), key=lambda item: item["support_count"], reverse=True)[:NEIGHBOR_LIMIT]
        in_list = sorted(incoming.get(concept_id, []), key=lambda item: item["support_count"], reverse=True)[:NEIGHBOR_LIMIT]
        combined = sorted(out_list + in_list, key=lambda item: item["support_count"], reverse=True)
        top_neighbors: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in combined:
            if item["concept_id"] in seen:
                continue
            seen.add(item["concept_id"])
            top_neighbors.append(item)
            if len(top_neighbors) >= NEIGHBOR_LIMIT:
                break
        neighborhoods[concept_id] = {
            "incoming": in_list,
            "outgoing": out_list,
            "top_neighbors": top_neighbors,
        }
    return neighborhoods


def build_concept_opportunities(
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    columns = list(candidates_df.columns)
    concept_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in candidates_df.itertuples(index=False):
        record = opportunity_record(tuple(row), columns, concept_label_lookup, glossary, representative_papers_lookup)
        for concept_id in (row.u, row.v):
            existing = concept_map[concept_id].get(record["pair_key"])
            if existing is None or safe_number_for_sort(record["score"]) > safe_number_for_sort(existing["score"]):
                concept_map[concept_id][record["pair_key"]] = record
    out: dict[str, list[dict[str, Any]]] = {}
    for concept_id, pair_rows in concept_map.items():
        rows = list(pair_rows.values())
        rows.sort(key=lambda item: item["score"], reverse=True)
        out[concept_id] = rows[:CONCEPT_OPPORTUNITY_LIMIT]
    return out


def safe_number_for_sort(value: Any) -> float:
    numeric = to_float(value, 0.0)
    return numeric if math.isfinite(numeric) else 0.0


def build_search_index(
    nodes_df: pd.DataFrame,
    node_metrics_df: pd.DataFrame,
    glossary: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    metrics_map = node_metrics_df.set_index("concept_id").to_dict("index")
    records: list[dict[str, Any]] = []
    for row in nodes_df.itertuples(index=False):
        metrics = metrics_map.get(row.concept_id, {})
        aliases = uniq_keep_order(parse_json_list(row.aliases_json), limit=12)
        search_terms = uniq_keep_order(
            [str(row.preferred_label).lower(), public_label_payload(row.concept_id, row.preferred_label, glossary)["plain_label"].lower()] + [alias.lower() for alias in aliases],
            limit=20,
        )
        public_label = public_label_payload(row.concept_id, row.preferred_label, glossary)
        records.append(
            {
                "concept_id": row.concept_id,
                "label": row.preferred_label,
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "aliases": aliases,
                "bucket_hint": row.bucket_hint,
                "instance_support": int(row.instance_support),
                "distinct_paper_support": int(row.distinct_paper_support),
                "weighted_degree": round(float(metrics.get("weighted_degree", 0.0)), 4),
                "pagerank": round(float(metrics.get("pagerank", 0.0)), 8),
                "in_degree": int(metrics.get("in_degree", 0) or 0),
                "out_degree": int(metrics.get("out_degree", 0) or 0),
                "neighbor_count": int(metrics.get("neighbor_count", 0) or 0),
                "top_countries": top_values(getattr(row, "top_countries", None), limit=3),
                "top_units": top_values(getattr(row, "top_units", None), limit=3),
                "search_terms": search_terms,
                "app_link": f"{APP_URL}?search={quote(str(row.preferred_label))}",
            }
        )
    records.sort(key=lambda item: (item["weighted_degree"], item["instance_support"]), reverse=True)
    return records


def diversify_featured_opportunities(
    slices: dict[str, list[dict[str, Any]]], limit: int = FEATURED_OPPORTUNITY_LIMIT
) -> list[dict[str, Any]]:
    ordered_keys = ["bridges", "frontier", "fast_follow", "underexplored", "overall"]
    homepage_labels = {
        "bridges": "Connect separate literatures",
        "frontier": "Missing direct link",
        "fast_follow": "Ready to follow through",
        "underexplored": "Early but promising",
    }
    featured: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_slice_limits = {"overall": 4, "bridges": 2, "frontier": 2, "fast_follow": 2, "underexplored": 2}
    slice_counts: dict[str, int] = defaultdict(int)
    label_counts: dict[str, int] = defaultdict(int)

    for slice_key in ordered_keys:
        for item in slices.get(slice_key, []):
            if item["pair_key"] in seen:
                continue
            if slice_counts[slice_key] >= per_slice_limits.get(slice_key, 2):
                break
            featured_item = {
                **item,
                "slice_label": homepage_labels.get(slice_key, item["slice_label"]),
            }
            if label_counts[featured_item["slice_label"]] >= 2:
                continue
            featured.append(featured_item)
            seen.add(featured_item["pair_key"])
            slice_counts[slice_key] += 1
            label_counts[featured_item["slice_label"]] += 1
            if len(featured) >= limit:
                return featured[:limit]

    for item in slices.get("overall", []):
        if item["pair_key"] in seen:
            continue
        if label_counts[item["slice_label"]] >= 2:
            continue
        featured.append(item)
        seen.add(item["pair_key"])
        label_counts[item["slice_label"]] += 1
        if len(featured) >= limit:
            break

    for item in slices.get("overall", []):
        if item["pair_key"] in seen:
            continue
        featured.append(item)
        seen.add(item["pair_key"])
        if len(featured) >= limit:
            break
    return featured[:limit]


def load_editorial_opportunities() -> dict[str, dict[str, Any]]:
    payload = read_json(EDITORIAL_OPPORTUNITIES_PATH)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("editorial-opportunities.json must be a non-empty object keyed by pair_key")

    editorial: dict[str, dict[str, Any]] = {}
    for pair_key, item in payload.items():
        if not isinstance(item, dict):
            raise ValueError(f"Editorial entry for {pair_key} must be an object")
        entry = {**item}
        entry.setdefault("pair_key", pair_key)
        if entry["pair_key"] != pair_key:
            raise ValueError(f"Editorial entry {pair_key} must keep pair_key in sync with its object key")
        missing = [field for field in EDITORIAL_REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"Editorial entry {pair_key} is missing required fields: {', '.join(missing)}")
        editorial[pair_key] = entry
    return editorial


def load_public_label_glossary(valid_concept_ids: set[str]) -> dict[str, dict[str, Any]]:
    payload = read_json(PUBLIC_LABEL_GLOSSARY_PATH)
    if not isinstance(payload, dict):
        raise ValueError("public-label-glossary.json must be an object keyed by concept_id")

    glossary: dict[str, dict[str, Any]] = {}
    for concept_id, item in payload.items():
        if not isinstance(item, dict):
            raise ValueError(f"Public label glossary entry for {concept_id} must be an object")
        entry = {**item}
        entry.setdefault("concept_id", concept_id)
        if entry["concept_id"] != concept_id:
            raise ValueError(f"Public label glossary entry {concept_id} must keep concept_id in sync with its object key")
        missing = [field for field in PUBLIC_LABEL_GLOSSARY_REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"Public label glossary entry {concept_id} is missing required fields: {', '.join(missing)}")
        if concept_id not in valid_concept_ids:
            raise ValueError(f"Public label glossary concept_id {concept_id} is not present in the public concept index")
        glossary[concept_id] = {
            "concept_id": concept_id,
            "plain_label": clean_public_text(entry.get("plain_label")),
            "subtitle": clean_public_text(entry.get("subtitle")),
        }
    return glossary


def build_curated_opportunities(
    editorial: dict[str, dict[str, Any]],
    candidates_df: pd.DataFrame,
    concept_label_lookup: dict[str, str],
    glossary: dict[str, dict[str, Any]],
    representative_papers_lookup: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    available_pair_keys = {str(value) for value in candidates_df["pair_key"].tolist()}
    missing_pairs = [pair_key for pair_key in editorial if pair_key not in available_pair_keys]
    if missing_pairs:
        raise ValueError(
            "Curated editorial pair_keys are missing from the exported opportunity set: "
            + ", ".join(missing_pairs)
        )

    subset_df = candidates_df[candidates_df["pair_key"].isin(editorial.keys())].copy()
    columns = list(subset_df.columns)
    records_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in subset_df.itertuples(index=False, name=None):
        record = opportunity_record(tuple(row), columns, concept_label_lookup, glossary, representative_papers_lookup)
        records_by_pair[record["pair_key"]].append(record)

    curated_rows: list[dict[str, Any]] = []
    for pair_key, entry in sorted(editorial.items(), key=lambda item: int(item[1]["display_order"])):
        candidates = records_by_pair.get(pair_key, [])
        if not candidates:
            raise ValueError(f"Curated editorial pair_key {pair_key} could not be resolved to an opportunity record")
        base_record = candidates[0]
        curated_rows.append({**base_record, **entry})

    home_rows = [row for row in curated_rows if bool(row["homepage_featured"])]
    question_rows = [row for row in curated_rows if bool(row["questions_featured"])]
    home_roles = [str(row.get("homepage_role", "")) for row in home_rows]
    if home_roles.count("lead") != 1 or home_roles.count("supporting") != 2:
        raise ValueError("Homepage curation must contain exactly one lead question and two supporting questions")
    return home_rows, question_rows


def build_compare_payload(regime_summary_df: pd.DataFrame, overlap_df: pd.DataFrame) -> dict[str, Any]:
    display_names = {"broad": "Broad", "baseline": "Baseline", "conservative": "Conservative"}
    summary_rows: list[dict[str, Any]] = []
    for row in regime_summary_df.itertuples(index=False):
        summary_rows.append(
            {
                "regime": row.regime,
                "label": display_names.get(row.regime, row.label),
                "head_count": int(row.head_count),
                "hard_coverage": float(row.hard_coverage),
                "soft_coverage": float(row.soft_coverage),
                "strict_candidate_rows": int(row.strict_candidate_rows),
                "exploratory_candidate_rows": int(row.exploratory_candidate_rows),
                "strict_concept_edges": int(row.strict_concept_edges),
                "exploratory_concept_edges": int(row.exploratory_concept_edges),
            }
        )
    overlaps = overlap_df.to_dict("records")
    return {
        "default_view": {"regime": "baseline", "mapping": "exploratory"},
        "best_strict_view": {"regime": "broad", "mapping": "strict"},
        "summary": summary_rows,
        "overlaps": overlaps,
        "narrative": {
            "default_reason": "Baseline exploratory keeps the head inventory compact while reaching essentially the same exploratory coverage as the other regimes.",
            "strict_reason": "Broad strict is the clearest strict comparison view because it preserves more observed structure without fragmenting concepts as aggressively as the conservative regime.",
        },
    }


def write_json(path: Path, payload: Any) -> None:
    def sanitize(value: Any) -> Any:
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(sanitize(payload), handle, indent=2)


def chunk_mapping(mapping: dict[str, Any], output_dir: Path, stem: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shard_index: dict[str, str] = {}
    items = list(mapping.items())
    for chunk_no in range(0, len(items), SHARD_SIZE):
        shard_items = items[chunk_no : chunk_no + SHARD_SIZE]
        shard_name = f"{stem}-{chunk_no // SHARD_SIZE:03d}.json"
        shard_path = output_dir / shard_name
        write_json(shard_path, {key: value for key, value in shard_items})
        for key, _value in shard_items:
            shard_index[key] = f"/data/v2/{output_dir.name}/{shard_name}"
    return shard_index


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    extraction_summary = read_json(EXTRACTION_SUMMARY_PATH)
    baseline_manifest = read_json(BASELINE_MANIFEST_PATH)
    suppression_summary = read_json(SUPPRESSION_SUMMARY_PATH)
    editorial_opportunities = load_editorial_opportunities()
    regime_summary_df = pd.read_csv(REGIME_SUMMARY_PATH)
    overlap_df = pd.read_csv(RANKING_OVERLAP_PATH)
    top100_before_df = pd.read_csv(TOP100_BEFORE_PATH)
    top100_after_df = pd.read_csv(TOP100_AFTER_PATH)
    removed_hard_df = pd.read_csv(REMOVED_BY_HARD_BLOCK_PATH)

    candidates_df = add_slice_flags(load_candidates())
    node_details_df = load_node_details()
    representative_papers_lookup = load_representative_papers()
    public_concept_ids = {str(value) for value in node_details_df["concept_id"].tolist()}
    public_label_glossary = load_public_label_glossary(public_concept_ids)
    concept_label_lookup = (
        node_details_df.set_index("concept_id")["preferred_label"].to_dict()
    )
    graph_edges_df, edge_profiles_df, edge_contexts_df, edge_exemplars_df = load_graph_tables()

    node_metrics_df, _graph = compute_centrality(node_details_df, graph_edges_df)
    backbone_payload, backbone_nodes = build_backbone(
        node_details_df,
        graph_edges_df,
        node_metrics_df,
        edge_profiles_df,
        edge_contexts_df,
        edge_exemplars_df,
        public_label_glossary,
    )
    neighborhoods = build_neighborhoods(node_details_df, graph_edges_df, edge_profiles_df, edge_contexts_df)
    concept_opportunities = build_concept_opportunities(
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        representative_papers_lookup,
    )
    search_index = build_search_index(node_details_df, node_metrics_df, public_label_glossary)
    compare_payload = build_compare_payload(regime_summary_df, overlap_df)

    central_concepts_df = (
        node_details_df.merge(node_metrics_df, left_on="concept_id", right_on="concept_id", how="left")
        .sort_values(["weighted_degree", "pagerank"], ascending=[False, False])
        .reset_index(drop=True)
    )
    central_concepts_rows = []
    for row in central_concepts_df.head(200).itertuples(index=False):
        public_label = public_label_payload(row.concept_id, row.preferred_label, public_label_glossary)
        central_concepts_rows.append(
            {
                "concept_id": row.concept_id,
                "label": row.preferred_label,
                "plain_label": public_label["plain_label"],
                "subtitle": public_label["subtitle"],
                "bucket_hint": row.bucket_hint,
                "instance_support": int(row.instance_support),
                "distinct_paper_support": int(row.distinct_paper_support),
                "weighted_degree": round(float(row.weighted_degree), 4),
                "pagerank": round(float(row.pagerank), 8),
                "in_degree": int(row.in_degree),
                "out_degree": int(row.out_degree),
                "neighbor_count": int(row.neighbor_count),
                "top_countries": top_values(row.top_countries, limit=3),
                "top_units": top_values(row.top_units, limit=3),
                "app_link": f"{APP_URL}?search={quote(str(row.preferred_label))}",
            }
        )

    slices = build_slices(candidates_df, concept_label_lookup, public_label_glossary, representative_papers_lookup)
    featured_opportunities = diversify_featured_opportunities(slices, limit=FEATURED_OPPORTUNITY_LIMIT)
    home_curated_questions, curated_front_set = build_curated_opportunities(
        editorial_opportunities,
        candidates_df,
        concept_label_lookup,
        public_label_glossary,
        representative_papers_lookup,
    )

    write_json(PUBLIC_DATA_DIR / "graph_backbone.json", backbone_payload)
    write_json(PUBLIC_DATA_DIR / "concept_index.json", search_index)
    neighborhood_shard_index = chunk_mapping(neighborhoods, NEIGHBORHOOD_SHARDS_DIR, "neighborhoods")
    opportunity_shard_index = chunk_mapping(concept_opportunities, OPPORTUNITY_SHARDS_DIR, "opportunities")
    write_json(PUBLIC_DATA_DIR / "concept_neighborhoods_index.json", neighborhood_shard_index)
    write_json(PUBLIC_DATA_DIR / "concept_opportunities_index.json", opportunity_shard_index)
    write_json(PUBLIC_DATA_DIR / "opportunity_slices.json", slices)
    write_json(PUBLIC_DATA_DIR / "central_concepts.json", central_concepts_rows)
    write_json(PUBLIC_DATA_DIR / "compare_summary.json", compare_payload)
    write_json(
        PUBLIC_DATA_DIR / "suppression_before_after.json",
        {
            "before": top100_before_df.to_dict("records"),
            "after": top100_after_df.to_dict("records"),
            "removed_by_hard_block": removed_hard_df.to_dict("records"),
            "summary": suppression_summary,
        },
    )
    export_rows_csv(
        PUBLIC_DATA_DIR / "central_concepts.csv",
        central_concepts_rows,
        ["concept_id", "label", "plain_label", "subtitle", "bucket_hint", "instance_support", "distinct_paper_support", "weighted_degree", "pagerank", "in_degree", "out_degree", "neighbor_count", "top_countries", "top_units", "app_link"],
    )
    export_rows_csv(
        PUBLIC_DATA_DIR / "top_opportunities.csv",
        slices["overall"],
        ["pair_key", "source_id", "target_id", "source_label", "target_label", "source_bucket", "target_bucket", "cross_field", "score", "base_score", "duplicate_penalty", "path_support_norm", "gap_bonus", "mediator_count", "motif_count", "cooc_count", "direct_link_status", "supporting_path_count", "why_now", "recommended_move", "slice_label", "public_pair_label", "top_mediator_labels", "representative_papers", "top_countries_source", "top_countries_target", "source_context_summary", "target_context_summary", "app_link"],
    )

    baseline_exploratory = next(
        row for row in compare_payload["summary"] if row["regime"] == "baseline"
    )
    site_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_url": APP_URL,
        "repo_url": REPO_URL,
        "public_label_glossary": public_label_glossary,
        "default_view": {
            "regime": "Baseline",
            "mapping": "Exploratory",
            "db_path": str(BASELINE_SUPPRESSION_DB_PATH),
        },
        "metrics": {
            "papers": int(extraction_summary["records"]),
            "node_instances": int(extraction_summary["total_nodes"]),
            "edges": int(extraction_summary["total_edges"]),
            "baseline_head_concepts": int(baseline_exploratory["head_count"]),
            "baseline_soft_coverage": float(baseline_exploratory["soft_coverage"]),
            "suppressed_candidate_count": int(suppression_summary["visible_count"]),
            "duplicate_loops_removed_top100": int(suppression_summary["top100_removed_count"]),
        },
        "home": {
            "featured_questions": featured_opportunities[:6],
            "featured_opportunities": featured_opportunities[:6],
            "curated_questions": home_curated_questions,
            "curated_opportunities": home_curated_questions,
            "featured_central_concepts": central_concepts_rows[:8],
            "graph_snapshot": {
                "nodes": backbone_payload["counts"]["nodes"],
                "edges": backbone_payload["counts"]["edges"],
                "path": "/data/v2/graph_backbone.json",
            },
        },
        "graph": {
            "backbone_path": "/data/v2/graph_backbone.json",
            "concept_index_path": "/data/v2/concept_index.json",
            "concept_neighborhoods_index_path": "/data/v2/concept_neighborhoods_index.json",
            "concept_opportunities_index_path": "/data/v2/concept_opportunities_index.json",
            "central_concepts_path": "/data/v2/central_concepts.json",
        },
        "questions": {
            "slices_path": "/data/v2/opportunity_slices.json",
            "concept_opportunities_index_path": "/data/v2/concept_opportunities_index.json",
            "curated_front_set": curated_front_set,
            "top_slices": {
                "overall": slices["overall"][:12],
                "bridges": slices["bridges"][:12],
                "frontier": slices["frontier"][:12],
                "fast_follow": slices["fast_follow"][:12],
                "underexplored": slices["underexplored"][:12],
            },
        },
        "opportunities": {
            "slices_path": "/data/v2/opportunity_slices.json",
            "concept_opportunities_index_path": "/data/v2/concept_opportunities_index.json",
            "curated_front_set": curated_front_set,
            "top_slices": {
                "overall": slices["overall"][:12],
                "bridges": slices["bridges"][:12],
                "frontier": slices["frontier"][:12],
                "fast_follow": slices["fast_follow"][:12],
                "underexplored": slices["underexplored"][:12],
            },
        },
        "compare": {
            "summary_path": "/data/v2/compare_summary.json",
            "default_reason": compare_payload["narrative"]["default_reason"],
            "strict_reason": compare_payload["narrative"]["strict_reason"],
            "regimes": compare_payload["summary"],
            "overlaps_preview": compare_payload["overlaps"][:12],
        },
        "suppression": {
            "summary_path": "/data/v2/suppression_before_after.json",
            "summary": suppression_summary,
            "top_after": top100_after_df.head(12).to_dict("records"),
            "top_before": top100_before_df.head(12).to_dict("records"),
            "removed_preview": removed_hard_df.head(20).to_dict("records"),
        },
        "downloads": {
            "beta_db": {
                "filename": DB_FILENAME,
                "public_url": PUBLIC_DB_URL,
                "sha256": DB_SHA256,
                "db_size_gb": DB_SIZE_GB,
            },
            "checksum_path": "/downloads/frontiergraph-economics-beta.sha256.txt",
            "manifest_path": "/downloads/frontiergraph-economics-beta.manifest.json",
            "artifacts": {
                "top_opportunities_csv": "/data/v2/top_opportunities.csv",
                "central_concepts_csv": "/data/v2/central_concepts.csv",
                "compare_summary_json": "/data/v2/compare_summary.json",
                "graph_backbone_json": "/data/v2/graph_backbone.json",
            },
        },
    }
    write_json(GENERATED_DIR / "site-data.json", site_data)


if __name__ == "__main__":
    main()
