from __future__ import annotations

import json
import math
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
GENERATED_SITE_DATA = SITE_ROOT / "src" / "generated" / "site-data.json"

BROAD_DB = ROOT / "data" / "production" / "frontiergraph_concept_compare_v1" / "broad" / "concept_exploratory_app.sqlite"
BASELINE_DB = ROOT / "data" / "production" / "frontiergraph_concept_compare_v1" / "baseline" / "concept_exploratory_app.sqlite"
BROAD_MANIFEST = ROOT / "data" / "production" / "frontiergraph_concept_compare_v1" / "broad" / "manifest.json"
BROAD_ONTOLOGY_MANIFEST = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "broad" / "manifest.json"

GENERIC_TERMS = {
    "co2 emissions",
    "carbon emissions",
    "economic growth",
    "economic growth (gdp)",
    "energy consumption",
    "environmental degradation",
    "environmental quality",
    "environmental sustainability",
    "financial development",
    "inflation",
    "institutional quality",
    "investment",
    "monetary policy",
    "public debt",
    "renewable energy consumption",
    "trade openness",
}

CLIMATE_TERMS = (
    "climate",
    "carbon",
    "co2",
    "emission",
    "pollution",
    "environment",
    "ecological",
    "energy",
    "renewable",
)
MACRO_TERMS = (
    "inflation",
    "monetary",
    "debt",
    "fiscal",
    "bank",
    "loan",
    "credit",
    "money",
    "interest",
    "exchange rate",
)
TRADE_TERMS = (
    "trade",
    "export",
    "import",
    "product quality",
    "global value chain",
    "competitiveness",
    "openness",
)
INSTITUTION_TERMS = (
    "institution",
    "governance",
    "regulation",
    "policy",
    "liability",
    "corruption",
    "deregulation",
)
INNOVATION_TERMS = (
    "innovation",
    "technology",
    "productivity",
    "r&d",
    "high-tech",
    "industrial",
)


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_label(value: Any) -> str:
    text = str(value or "").lower()
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text)
    return " ".join(cleaned.split())


def slugify(value: str) -> str:
    return normalize_label(value).replace(" ", "-") or "group"


def token_count(value: Any) -> int:
    return len(normalize_label(value).split())


def parse_json_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        loaded = json.loads(str(value))
    except Exception:
        return []
    return loaded if isinstance(loaded, list) else []


def first_distinct(values: list[str], *, limit: int = 3) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        key = normalize_label(cleaned)
        if not cleaned or key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def top_value_labels(raw_json: Any, *, limit: int = 3) -> list[str]:
    out: list[str] = []
    for item in parse_json_list(raw_json):
        if isinstance(item, dict):
            out.append(str(item.get("value") or "").strip())
        else:
            out.append(str(item).strip())
    return first_distinct(out, limit=limit)


def add_query_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def current_site_meta() -> dict[str, str]:
    try:
        payload = read_json(GENERATED_SITE_DATA)
    except Exception:
        return {
            "app_url": os.environ.get("FRONTIERGRAPH_PUBLIC_APP_URL", "https://frontiergraph-app-1058669339361.us-central1.run.app"),
            "repo_url": "https://github.com/prashantg/frontiergraph",
        }
    return {
        "app_url": str(payload.get("app_url") or os.environ.get("FRONTIERGRAPH_PUBLIC_APP_URL") or "https://frontiergraph-app-1058669339361.us-central1.run.app"),
        "repo_url": str(payload.get("repo_url") or "https://github.com/prashantg/frontiergraph"),
    }


def preview_app_base_url() -> str:
    return current_site_meta()["app_url"]


def preview_app_url() -> str:
    return add_query_params(preview_app_base_url(), variant="broad")


def question_app_link(pair_key: str) -> str:
    return add_query_params(preview_app_base_url(), variant="broad", view="question", pair=pair_key)


def concept_app_link(concept_id: str) -> str:
    return add_query_params(preview_app_base_url(), variant="broad", view="concept", concept=concept_id)


def mirror_key(u: str, v: str) -> str:
    return "__".join(sorted((u, v)))


def pair_key(u: str, v: str) -> str:
    return f"{u}__{v}"


def direct_link_status(cooc_count: int) -> str:
    if cooc_count <= 0:
        return "No direct paper yet"
    if cooc_count <= 3:
        return "A few direct papers already exist"
    return "Direct papers already exist"


def recommended_move(cross_field: bool, cooc_count: int, mediator_count: int) -> str:
    if cross_field and cooc_count <= 0:
        return "Start with a short review or pilot that follows the intermediate topics already connecting the two sides."
    if cooc_count <= 0 and mediator_count >= 12:
        return "A focused paper that follows the strongest nearby intermediate topics looks plausible."
    if cooc_count <= 0:
        return "Treat this as an open direct question and inspect the nearby papers first."
    return "Use the nearby directed links and papers to sharpen the empirical angle before writing."


def question_family(source_label: str, target_label: str) -> str:
    return slugify(f"{source_label}-{target_label}")


def common_context_sentence(
    source_label: str,
    target_label: str,
    source_countries: list[str],
    target_countries: list[str],
) -> str:
    source_text = ", ".join(source_countries[:2]) or "similar settings"
    target_text = ", ".join(target_countries[:2]) or "similar settings"
    return f"{source_label} papers often mention {source_text}; {target_label} papers often mention {target_text}."


def regime_copy_summary(source_label: str, target_label: str, mediator_count: int, cooc_count: int) -> str:
    if mediator_count > 0:
        return (
            f"{source_label} and {target_label} already sit near {mediator_count:,} intermediate topics "
            f"in the broad regime, while the direct literature here is {cooc_count:,} paper(s)."
        )
    return f"{source_label} and {target_label} already sit near the same local literature neighborhood in the broad regime."


def broadness_penalty(label: str, distinct_paper_support: int) -> float:
    normalized = normalize_label(label)
    penalty = 0.0
    if normalized in GENERIC_TERMS:
        penalty += 6.0
    if token_count(label) <= 2:
        penalty += 1.5
    if distinct_paper_support >= 3000:
        penalty += 2.5
    elif distinct_paper_support >= 1500:
        penalty += 1.0
    return penalty


def specificity_score(
    source_label: str,
    target_label: str,
    source_support: int,
    target_support: int,
    mediator_count: int,
    cooc_count: int,
    cross_field: bool,
) -> float:
    score = 0.0
    score += min(mediator_count, 20) * 0.35
    score += 1.2 if cross_field else 0.0
    score += 1.4 if cooc_count <= 0 else 0.0
    score += min(token_count(source_label) + token_count(target_label), 10) * 0.25
    score -= broadness_penalty(source_label, source_support)
    score -= broadness_penalty(target_label, target_support)
    return round(score, 4)


def pagerank(nodes: list[str], edges: list[dict[str, Any]], alpha: float = 0.85) -> dict[str, float]:
    if not nodes:
        return {}
    incoming: dict[str, list[tuple[str, float]]] = defaultdict(list)
    out_weight: dict[str, float] = defaultdict(float)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        weight = float(edge.get("support_count") or 1.0)
        incoming[target].append((source, weight))
        out_weight[source] += weight
    n = len(nodes)
    ranks = {node_id: 1.0 / n for node_id in nodes}
    base = (1.0 - alpha) / n
    for _ in range(80):
        dangling = alpha * sum(ranks[node_id] for node_id in nodes if out_weight[node_id] == 0.0) / n
        updated: dict[str, float] = {}
        delta = 0.0
        for node_id in nodes:
            value = base + dangling
            for source, weight in incoming.get(node_id, []):
                if out_weight[source] > 0:
                    value += alpha * ranks[source] * (weight / out_weight[source])
            updated[node_id] = value
            delta = max(delta, abs(value - ranks[node_id]))
        ranks = updated
        if delta < 1e-10:
            break
    return ranks


def layout_positions(concepts: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    groups: dict[str, list[dict[str, Any]]] = {"core": [], "adjacent": [], "mixed": [], "unknown": []}
    for concept in concepts:
        groups.get(str(concept.get("bucket_hint") or "unknown"), groups["unknown"]).append(concept)
    centers = {"core": 0.28, "adjacent": 0.72, "mixed": 0.5, "unknown": 0.5}
    positions: dict[str, tuple[float, float]] = {}
    for bucket, items in groups.items():
        if not items:
            continue
        items.sort(key=lambda row: (-float(row.get("weighted_degree") or 0.0), str(row.get("concept_id") or "")))
        count = len(items)
        for index, concept in enumerate(items):
            angle = (2 * math.pi * index / max(count, 1)) - math.pi / 2
            radius_x = 0.14 + min(0.18, count / 220)
            radius_y = 0.2 + min(0.18, count / 220)
            x = centers.get(bucket, 0.5) + math.cos(angle) * radius_x
            y = 0.5 + math.sin(angle) * radius_y
            positions[str(concept["concept_id"])] = (round(min(max(x, 0.06), 0.94), 6), round(min(max(y, 0.08), 0.92), 6))
    return positions


def classify_field_group(question: dict[str, Any]) -> str:
    haystack = normalize_label(
        " ".join(
            [
                str(question.get("source_display_label") or ""),
                str(question.get("target_display_label") or ""),
                " ".join(question.get("top_mediator_display_labels") or []),
            ]
        )
    )
    if any(term in haystack for term in CLIMATE_TERMS):
        return "Climate and energy"
    if any(term in haystack for term in MACRO_TERMS):
        return "Macro and finance"
    if any(term in haystack for term in TRADE_TERMS + INNOVATION_TERMS):
        return "Trade, innovation, and growth"
    if any(term in haystack for term in INSTITUTION_TERMS):
        return "Institutions and policy"
    return "Other broad-regime questions"


def build_question_groups(questions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    field_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        field_buckets[classify_field_group(question)].append(question)

    field_groups: list[dict[str, Any]] = []
    for title, items in sorted(field_buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        trimmed = items[:8]
        if not trimmed:
            continue
        field_groups.append(
            {
                "slug": slugify(title),
                "title": title,
                "caption": "Questions in this cluster are ordered within the broad exploratory regime.",
                "items": trimmed,
            }
        )
        if len(field_groups) >= 4:
            break

    use_case_groups = [
        {
            "slug": "sharper-wording",
            "title": "More specific-looking candidates",
            "caption": "These rise when the broader vocabulary produces narrower endpoint wording.",
            "items": sorted(questions, key=lambda row: (-float(row.get("public_specificity_score") or 0.0), -float(row.get("score") or 0.0)))[:8],
        },
        {
            "slug": "many-intermediates",
            "title": "Questions with strong local support",
            "caption": "These have many nearby intermediate topics already connecting the two sides.",
            "items": sorted(questions, key=lambda row: (-int(row.get("mediator_count") or 0), -float(row.get("score") or 0.0)))[:8],
        },
        {
            "slug": "no-direct-paper",
            "title": "No direct paper yet",
            "caption": "These have no direct paper in the preview window and are easiest to inspect as missing direct links.",
            "items": [row for row in questions if int(row.get("cooc_count") or 0) <= 0][:8],
        },
    ]
    return field_groups, use_case_groups


def slice_questions(questions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "overall": questions[:100],
        "bridges": [row for row in questions if row.get("cross_field")][:100],
        "frontier": [row for row in questions if int(row.get("cooc_count") or 0) <= 0][:100],
        "fast_follow": sorted(
            [row for row in questions if int(row.get("cooc_count") or 0) > 0],
            key=lambda row: (-float(row.get("score") or 0.0), -int(row.get("mediator_count") or 0)),
        )[:100],
        "underexplored": sorted(
            questions,
            key=lambda row: (int(row.get("cooc_count") or 0), -int(row.get("mediator_count") or 0), -float(row.get("score") or 0.0)),
        )[:100],
    }


def _broad_metrics() -> dict[str, int]:
    broad_manifest = read_json(BROAD_MANIFEST)
    broad_ontology = read_json(BROAD_ONTOLOGY_MANIFEST)
    view_counts = broad_manifest.get("views", {}).get("exploratory", {}).get("counts", {})
    ontology_counts = broad_ontology.get("counts", {})
    return {
        "papers": int(view_counts.get("works", 0)),
        "papers_with_extracted_edges": int(view_counts.get("corpus_rows", 0)),
        "normalized_graph_papers": int(view_counts.get("corpus_rows", 0)),
        "node_instances": int(ontology_counts.get("node_instances", 0)),
        "edges": int(view_counts.get("concept_edges", 0)),
        "normalized_links": int(view_counts.get("concept_edge_instances", 0)),
        "normalized_directed_links": int(view_counts.get("concept_edge_instances", 0)),
        "normalized_undirected_links": 0,
        "native_concepts": int(ontology_counts.get("final_head_count", 0)),
        "visible_public_questions": 100,
    }


def build_broad_preview_dataset(limit: int = 100) -> dict[str, Any]:
    base_meta = current_site_meta()
    generated_at = utc_now()
    metrics = _broad_metrics()

    conn = sqlite3.connect(BROAD_DB)
    conn.row_factory = sqlite3.Row
    try:
        scan_rows = conn.execute(
            """
            SELECT
              u,
              v,
              COALESCE(u_preferred_label, u) AS u_label,
              COALESCE(v_preferred_label, v) AS v_label,
              u_bucket_hint,
              v_bucket_hint,
              score,
              rank,
              cooc_count,
              mediator_count,
              motif_count,
              path_support_norm,
              gap_bonus,
              top_mediators_json,
              top_paths_json
            FROM candidates
            ORDER BY score DESC, rank ASC
            LIMIT 8000
            """
        ).fetchall()
        selected_rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in scan_rows:
            row_dict = dict(row)
            key = mirror_key(str(row_dict["u"]), str(row_dict["v"]))
            if key in seen:
                continue
            seen.add(key)
            row_dict["pair_key"] = pair_key(str(row_dict["u"]), str(row_dict["v"]))
            selected_rows.append(row_dict)
            if len(selected_rows) >= limit:
                break

        conn.execute("DROP TABLE IF EXISTS temp.selected_pairs")
        conn.execute("CREATE TEMP TABLE selected_pairs(candidate_u TEXT, candidate_v TEXT, pair_key TEXT, pair_order INTEGER)")
        conn.executemany(
            "INSERT INTO selected_pairs(candidate_u, candidate_v, pair_key, pair_order) VALUES (?, ?, ?, ?)",
            [(row["u"], row["v"], row["pair_key"], index) for index, row in enumerate(selected_rows, start=1)],
        )

        mediator_rows = conn.execute(
            """
            SELECT
              sp.pair_key,
              m.rank,
              m.mediator AS mediator_concept_id,
              COALESCE(nd.preferred_label, n.label, m.mediator) AS mediator_label,
              m.score
            FROM candidate_mediators m
            JOIN selected_pairs sp
              ON m.candidate_u = sp.candidate_u
             AND m.candidate_v = sp.candidate_v
            LEFT JOIN node_details nd
              ON m.mediator = nd.concept_id
            LEFT JOIN nodes n
              ON m.mediator = n.code
            ORDER BY sp.pair_order, m.rank
            """
        ).fetchall()
        path_rows = conn.execute(
            """
            SELECT
              sp.pair_key,
              p.rank,
              p.path_len,
              p.path_score,
              p.path_text,
              p.path_nodes_json
            FROM candidate_paths p
            JOIN selected_pairs sp
              ON p.candidate_u = sp.candidate_u
             AND p.candidate_v = sp.candidate_v
            ORDER BY sp.pair_order, p.rank
            """
        ).fetchall()
        paper_rows = conn.execute(
            """
            SELECT
              sp.pair_key,
              p.path_rank,
              p.paper_rank,
              p.paper_id,
              p.title,
              p.year,
              p.edge_src,
              COALESCE(src_details.preferred_label, src_nodes.label, p.edge_src) AS edge_src_label,
              p.edge_dst,
              COALESCE(dst_details.preferred_label, dst_nodes.label, p.edge_dst) AS edge_dst_label
            FROM candidate_papers p
            JOIN selected_pairs sp
              ON p.candidate_u = sp.candidate_u
             AND p.candidate_v = sp.candidate_v
            LEFT JOIN node_details src_details
              ON p.edge_src = src_details.concept_id
            LEFT JOIN node_details dst_details
              ON p.edge_dst = dst_details.concept_id
            LEFT JOIN nodes src_nodes
              ON p.edge_src = src_nodes.code
            LEFT JOIN nodes dst_nodes
              ON p.edge_dst = dst_nodes.code
            ORDER BY sp.pair_order, p.path_rank, p.paper_rank
            """
        ).fetchall()

        mediators_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in mediator_rows:
            record = dict(row)
            if len(mediators_by_pair[record["pair_key"]]) < 10:
                mediators_by_pair[record["pair_key"]].append(record)

        paths_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in path_rows:
            record = dict(row)
            if len(paths_by_pair[record["pair_key"]]) < 8:
                paths_by_pair[record["pair_key"]].append(record)

        papers_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in paper_rows:
            record = dict(row)
            if len(papers_by_pair[record["pair_key"]]) < 6:
                papers_by_pair[record["pair_key"]].append(record)

        selected_concepts: set[str] = set()
        for row in selected_rows:
            selected_concepts.add(str(row["u"]))
            selected_concepts.add(str(row["v"]))
            for mediator in mediators_by_pair[row["pair_key"]][:3]:
                selected_concepts.add(str(mediator["mediator_concept_id"]))

        conn.execute("DROP TABLE IF EXISTS temp.selected_concepts")
        conn.execute("CREATE TEMP TABLE selected_concepts(concept_id TEXT PRIMARY KEY)")
        conn.executemany(
            "INSERT OR IGNORE INTO selected_concepts(concept_id) VALUES (?)",
            [(concept_id,) for concept_id in sorted(selected_concepts)],
        )

        concept_rows = conn.execute(
            """
            SELECT
              sc.concept_id,
              COALESCE(nd.preferred_label, n.label, sc.concept_id) AS label,
              COALESCE(nd.preferred_label, n.label, sc.concept_id) AS plain_label,
              nd.aliases_json,
              nd.instance_support,
              nd.distinct_paper_support,
              nd.bucket_hint,
              nd.top_countries,
              nd.top_units
            FROM selected_concepts sc
            LEFT JOIN node_details nd
              ON sc.concept_id = nd.concept_id
            LEFT JOIN nodes n
              ON sc.concept_id = n.code
            ORDER BY COALESCE(nd.distinct_paper_support, 0) DESC, sc.concept_id
            """
        ).fetchall()

        edge_rows = conn.execute(
            """
            SELECT
              e.source_concept_id,
              e.target_concept_id,
              e.support_count,
              e.distinct_papers,
              e.avg_stability
            FROM concept_edges e
            JOIN selected_concepts src
              ON e.source_concept_id = src.concept_id
            JOIN selected_concepts dst
              ON e.target_concept_id = dst.concept_id
            WHERE e.source_concept_id != e.target_concept_id
            """
        ).fetchall()
    finally:
        conn.close()

    concept_records: dict[str, dict[str, Any]] = {}
    for row in concept_rows:
        record = dict(row)
        concept_id = str(record["concept_id"])
        aliases = first_distinct(parse_json_list(record.get("aliases_json")), limit=12)
        plain_label = str(record.get("plain_label") or record.get("label") or concept_id)
        search_terms = first_distinct([plain_label, str(record.get("label") or "")] + aliases, limit=16)
        top_countries = top_value_labels(record.get("top_countries"), limit=3)
        top_units = top_value_labels(record.get("top_units"), limit=3)
        concept_records[concept_id] = {
            "concept_id": concept_id,
            "label": plain_label,
            "plain_label": plain_label,
            "subtitle": "",
            "display_concept_id": concept_id,
            "display_refined": False,
            "display_refinement_confidence": 0.0,
            "alternate_display_labels": aliases[:3],
            "aliases": aliases,
            "bucket_hint": str(record.get("bucket_hint") or "mixed"),
            "instance_support": int(record.get("instance_support") or 0),
            "distinct_paper_support": int(record.get("distinct_paper_support") or 0),
            "weighted_degree": 0.0,
            "pagerank": 0.0,
            "in_degree": 0,
            "out_degree": 0,
            "neighbor_count": 0,
            "top_countries": top_countries,
            "top_units": top_units,
            "search_terms": search_terms,
            "app_link": concept_app_link(concept_id),
        }

    graph_edges: list[dict[str, Any]] = []
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edge_rows:
        record = dict(row)
        source = str(record["source_concept_id"])
        target = str(record["target_concept_id"])
        if source not in concept_records or target not in concept_records:
            continue
        edge = {
            "id": f"{source}__{target}",
            "source": source,
            "target": target,
            "support_count": int(record.get("support_count") or 0),
            "distinct_papers": int(record.get("distinct_papers") or 0),
            "avg_stability": round(float(record.get("avg_stability") or 0.0), 4),
            "strength": 0.0,
            "directionality_mix": [["directed", int(record.get("support_count") or 0)]],
            "relationship_type_mix": [],
            "edge_role_mix": [],
            "dominant_countries": first_distinct(
                concept_records[source]["top_countries"] + concept_records[target]["top_countries"],
                limit=3,
            ),
            "dominant_units": first_distinct(
                concept_records[source]["top_units"] + concept_records[target]["top_units"],
                limit=3,
            ),
            "dominant_years": [],
            "examples": [],
        }
        graph_edges.append(edge)

        summary = {
            "concept_id": target,
            "label": concept_records[target]["plain_label"],
            "support_count": edge["support_count"],
            "distinct_papers": edge["distinct_papers"],
            "avg_stability": edge["avg_stability"],
            "directionality_mix": edge["directionality_mix"],
            "relationship_type_mix": [],
            "edge_role_mix": [],
            "dominant_countries": edge["dominant_countries"],
        }
        outgoing[source].append(summary)
        incoming[target].append(
            {
                **summary,
                "concept_id": source,
                "label": concept_records[source]["plain_label"],
                "dominant_countries": edge["dominant_countries"],
            }
        )

    if graph_edges:
        max_support = max(edge["support_count"] for edge in graph_edges) or 1
        for edge in graph_edges:
            edge["strength"] = round(edge["support_count"] / max_support, 6)

    weighted_degree: dict[str, float] = defaultdict(float)
    indegree: dict[str, int] = defaultdict(int)
    outdegree: dict[str, int] = defaultdict(int)
    neighbors: dict[str, set[str]] = defaultdict(set)
    for edge in graph_edges:
        source = edge["source"]
        target = edge["target"]
        support = float(edge["support_count"])
        weighted_degree[source] += support
        weighted_degree[target] += support
        outdegree[source] += 1
        indegree[target] += 1
        neighbors[source].add(target)
        neighbors[target].add(source)

    pr = pagerank(list(concept_records), graph_edges)
    for concept_id, record in concept_records.items():
        record["weighted_degree"] = round(weighted_degree.get(concept_id, 0.0), 4)
        record["pagerank"] = round(pr.get(concept_id, 0.0), 8)
        record["in_degree"] = int(indegree.get(concept_id, 0))
        record["out_degree"] = int(outdegree.get(concept_id, 0))
        record["neighbor_count"] = int(len(neighbors.get(concept_id, set())))

    concept_list = sorted(
        concept_records.values(),
        key=lambda row: (-float(row["weighted_degree"]), -int(row["distinct_paper_support"]), row["concept_id"]),
    )
    positions = layout_positions(concept_list)
    graph_nodes: list[dict[str, Any]] = []
    for concept in concept_list:
        x, y = positions.get(concept["concept_id"], (0.5, 0.5))
        graph_nodes.append(
            {
                "id": concept["concept_id"],
                "label": concept["label"],
                "plain_label": concept["plain_label"],
                "subtitle": "",
                "display_concept_id": concept["display_concept_id"],
                "display_refined": concept["display_refined"],
                "display_refinement_confidence": concept["display_refinement_confidence"],
                "alternate_display_labels": concept["alternate_display_labels"],
                "aliases": concept["aliases"],
                "alias_count": len(concept["aliases"]),
                "bucket_hint": concept["bucket_hint"],
                "instance_support": concept["instance_support"],
                "distinct_paper_support": concept["distinct_paper_support"],
                "top_countries": concept["top_countries"],
                "top_units": concept["top_units"],
                "x": x,
                "y": y,
                "weighted_degree": concept["weighted_degree"],
                "pagerank": concept["pagerank"],
                "in_degree": concept["in_degree"],
                "out_degree": concept["out_degree"],
                "neighbor_count": concept["neighbor_count"],
                "bucket_group": concept["bucket_hint"],
                "show_label": concept["weighted_degree"] >= sorted([c["weighted_degree"] for c in concept_list], reverse=True)[min(11, max(len(concept_list) - 1, 0))] if concept_list else False,
            }
        )

    question_records: list[dict[str, Any]] = []
    question_mediators: list[dict[str, Any]] = []
    question_paths: list[dict[str, Any]] = []
    question_papers: list[dict[str, Any]] = []
    question_neighborhoods: list[dict[str, Any]] = []

    for row in selected_rows:
        source_id = str(row["u"])
        target_id = str(row["v"])
        pair = str(row["pair_key"])
        source = concept_records[source_id]
        target = concept_records[target_id]
        mediator_rows_for_pair = mediators_by_pair.get(pair, [])[:8]
        top_mediator_labels = [str(item["mediator_label"]) for item in mediator_rows_for_pair[:3]]
        top_paths = paths_by_pair.get(pair, [])[:6]
        top_papers = papers_by_pair.get(pair, [])[:6]
        specificity = specificity_score(
            source["plain_label"],
            target["plain_label"],
            source["distinct_paper_support"],
            target["distinct_paper_support"],
            int(row.get("mediator_count") or 0),
            int(row.get("cooc_count") or 0),
            bool(str(row.get("u_bucket_hint") or "") != str(row.get("v_bucket_hint") or "")),
        )
        question = {
            "pair_key": pair,
            "source_id": source_id,
            "target_id": target_id,
            "source_label": source["label"],
            "target_label": target["label"],
            "source_display_label": source["plain_label"],
            "target_display_label": target["plain_label"],
            "source_display_concept_id": source_id,
            "target_display_concept_id": target_id,
            "source_display_refined": False,
            "target_display_refined": False,
            "display_refinement_confidence": 0.0,
            "source_alternate_display_labels": source["alternate_display_labels"],
            "target_alternate_display_labels": target["alternate_display_labels"],
            "source_bucket": str(row.get("u_bucket_hint") or "mixed"),
            "target_bucket": str(row.get("v_bucket_hint") or "mixed"),
            "cross_field": int(str(row.get("u_bucket_hint") or "") != str(row.get("v_bucket_hint") or "")),
            "score": round(float(row.get("score") or 0.0), 6),
            "base_score": round(float(row.get("score") or 0.0), 6),
            "duplicate_penalty": 0.0,
            "path_support_norm": round(float(row.get("path_support_norm") or 0.0), 6),
            "gap_bonus": round(float(row.get("gap_bonus") or 0.0), 6),
            "mediator_count": int(row.get("mediator_count") or 0),
            "motif_count": int(row.get("motif_count") or 0),
            "cooc_count": int(row.get("cooc_count") or 0),
            "direct_link_status": direct_link_status(int(row.get("cooc_count") or 0)),
            "supporting_path_count": int(row.get("mediator_count") or 0),
            "why_now": regime_copy_summary(source["plain_label"], target["plain_label"], int(row.get("mediator_count") or 0), int(row.get("cooc_count") or 0)),
            "recommended_move": recommended_move(bool(str(row.get("u_bucket_hint") or "") != str(row.get("v_bucket_hint") or "")), int(row.get("cooc_count") or 0), int(row.get("mediator_count") or 0)),
            "slice_label": "No direct paper yet" if int(row.get("cooc_count") or 0) <= 0 else "Direct literature already exists",
            "public_pair_label": f"{source['plain_label']} and {target['plain_label']}",
            "question_family": question_family(source["plain_label"], target["plain_label"]),
            "suppress_from_public_ranked_window": False,
            "top_mediator_display_labels": top_mediator_labels,
            "top_mediator_labels": top_mediator_labels,
            "top_mediator_baseline_labels": top_mediator_labels,
            "representative_papers": [
                {
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "year": int(paper["year"] or 0),
                    "edge_src": paper["edge_src"],
                    "edge_dst": paper["edge_dst"],
                    "edge_src_display_label": paper["edge_src_label"],
                    "edge_dst_display_label": paper["edge_dst_label"],
                }
                for paper in top_papers[:3]
            ],
            "top_countries_source": source["top_countries"],
            "top_countries_target": target["top_countries"],
            "source_context_summary": ", ".join(source["top_countries"][:2]) or source["plain_label"],
            "target_context_summary": ", ".join(target["top_countries"][:2]) or target["plain_label"],
            "common_contexts": common_context_sentence(source["plain_label"], target["plain_label"], source["top_countries"], target["top_countries"]),
            "public_specificity_score": specificity,
            "app_link": question_app_link(pair),
        }
        question_records.append(question)

        for mediator in mediator_rows_for_pair:
            question_mediators.append(
                {
                    "pair_key": pair,
                    "rank": int(mediator["rank"]),
                    "mediator_concept_id": str(mediator["mediator_concept_id"]),
                    "mediator_label": str(mediator["mediator_label"]),
                    "mediator_baseline_label": str(mediator["mediator_label"]),
                    "score": round(float(mediator["score"] or 0.0), 6),
                }
            )

        for path in top_paths:
            node_ids = parse_json_list(path.get("path_nodes_json"))
            node_labels = [concept_records.get(str(node_id), {}).get("plain_label", str(node_id)) for node_id in node_ids]
            question_paths.append(
                {
                    "pair_key": pair,
                    "rank": int(path["rank"]),
                    "path_len": int(path["path_len"]),
                    "path_score": round(float(path["path_score"] or 0.0), 6),
                    "path_text": " -> ".join(node_labels),
                    "path_nodes_json": json.dumps(node_ids, ensure_ascii=False),
                    "path_labels_json": json.dumps(node_labels, ensure_ascii=False),
                    "path_baseline_labels_json": json.dumps(node_labels, ensure_ascii=False),
                }
            )

        for paper in top_papers:
            question_papers.append(
                {
                    "pair_key": pair,
                    "path_rank": int(paper["path_rank"]),
                    "paper_rank": int(paper["paper_rank"]),
                    "paper_id": str(paper["paper_id"]),
                    "title": str(paper["title"] or ""),
                    "year": int(paper["year"] or 0),
                    "edge_src": str(paper["edge_src"]),
                    "edge_src_label": str(paper["edge_src_label"] or paper["edge_src"]),
                    "edge_src_baseline_label": str(paper["edge_src_label"] or paper["edge_src"]),
                    "edge_dst": str(paper["edge_dst"]),
                    "edge_dst_label": str(paper["edge_dst_label"] or paper["edge_dst"]),
                    "edge_dst_baseline_label": str(paper["edge_dst_label"] or paper["edge_dst"]),
                }
            )

        question_neighborhoods.append(
            {
                "pair_key": pair,
                "source_out_neighbors_json": json.dumps(outgoing.get(source_id, [])[:12], ensure_ascii=False),
                "target_in_neighbors_json": json.dumps(incoming.get(target_id, [])[:12], ensure_ascii=False),
            }
        )

    question_records.sort(key=lambda row: (-float(row["score"]), row["pair_key"]))

    concept_neighborhoods: dict[str, dict[str, Any]] = {}
    concept_neighbors_rows: list[dict[str, Any]] = []
    concept_opportunities_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    concept_opportunities_rows: list[dict[str, Any]] = []

    questions_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in question_records:
        questions_by_concept[question["source_id"]].append(question)
        questions_by_concept[question["target_id"]].append(question)

    for concept in concept_list:
        concept_id = concept["concept_id"]
        outgoing_rows = sorted(outgoing.get(concept_id, []), key=lambda row: (-int(row["support_count"]), row["label"]))[:12]
        incoming_rows = sorted(incoming.get(concept_id, []), key=lambda row: (-int(row["support_count"]), row["label"]))[:12]
        top_neighbors = first_distinct(
            [row["concept_id"] for row in outgoing_rows + incoming_rows],
            limit=12,
        )
        top_neighbor_rows = []
        for neighbor_id in top_neighbors:
            row = next((item for item in outgoing_rows + incoming_rows if item["concept_id"] == neighbor_id), None)
            if row:
                top_neighbor_rows.append(row)

        concept_neighborhoods[concept_id] = {
            "incoming": incoming_rows,
            "outgoing": outgoing_rows,
            "top_neighbors": top_neighbor_rows,
        }

        for index, row in enumerate(incoming_rows, start=1):
            concept_neighbors_rows.append(
                {
                    "concept_id": concept_id,
                    "direction": "incoming",
                    "rank_for_concept": index,
                    "neighbor_concept_id": row["concept_id"],
                    "label": row["label"],
                    "support_count": int(row["support_count"]),
                    "distinct_papers": int(row["distinct_papers"]),
                    "avg_stability": float(row["avg_stability"]),
                    "row_json": json.dumps(row, ensure_ascii=False),
                }
            )
        for index, row in enumerate(outgoing_rows, start=1):
            concept_neighbors_rows.append(
                {
                    "concept_id": concept_id,
                    "direction": "outgoing",
                    "rank_for_concept": index,
                    "neighbor_concept_id": row["concept_id"],
                    "label": row["label"],
                    "support_count": int(row["support_count"]),
                    "distinct_papers": int(row["distinct_papers"]),
                    "avg_stability": float(row["avg_stability"]),
                    "row_json": json.dumps(row, ensure_ascii=False),
                }
            )

        opportunities = sorted(
            questions_by_concept.get(concept_id, []),
            key=lambda row: (-float(row.get("score") or 0.0), -float(row.get("public_specificity_score") or 0.0), row["pair_key"]),
        )[:16]
        concept_opportunities_map[concept_id] = opportunities
        for index, question in enumerate(opportunities, start=1):
            concept_opportunities_rows.append(
                {
                    "concept_id": concept_id,
                    "rank_for_concept": index,
                    "pair_key": question["pair_key"],
                    "score": float(question["score"]),
                    "source_label": question["source_display_label"],
                    "target_label": question["target_display_label"],
                    "row_json": json.dumps(question, ensure_ascii=False),
                }
            )

    field_carousels, use_case_carousels = build_question_groups(question_records)
    top_slices = slice_questions(question_records)

    central_concepts = concept_list[:24]

    dataset = {
        "generated_at": generated_at,
        "variant": "broad",
        "variant_label": "Broad preview",
        "preview_note": "This preview uses the broad exploratory regime directly and shows a preview-sized top window rather than a full public release.",
        "app_url": preview_app_url(),
        "repo_url": base_meta["repo_url"],
        "metrics": metrics,
        "questions": question_records,
        "top_questions": question_records[: min(100, len(question_records))],
        "question_mediators": question_mediators,
        "question_paths": question_paths,
        "question_papers": question_papers,
        "question_neighborhoods": question_neighborhoods,
        "concepts": concept_list,
        "central_concepts": central_concepts,
        "graph": {
            "generated_at": generated_at,
            "counts": {"nodes": len(graph_nodes), "edges": len(graph_edges)},
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
        "concept_neighborhoods": concept_neighborhoods,
        "concept_opportunities": concept_opportunities_map,
        "concept_neighbors_rows": concept_neighbors_rows,
        "concept_opportunities_rows": concept_opportunities_rows,
        "field_carousels": field_carousels,
        "use_case_carousels": use_case_carousels,
        "top_slices": top_slices,
    }
    return dataset
