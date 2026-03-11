from __future__ import annotations

import csv
import json
import math
import os
import sqlite3
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_SCRIPT = ROOT / "scripts" / "build_frontiergraph_ontology_v3.py"
CONCEPT_SCRIPT = ROOT / "scripts" / "build_frontiergraph_concept_v3.py"
V2_DB = ROOT / "data/production/frontiergraph_ontology_v2/ontology_v2.sqlite"
ONTOLOGY_COMPARE_ROOT = ROOT / "data/production/frontiergraph_ontology_compare_v1"
CONCEPT_COMPARE_ROOT = ROOT / "data/production/frontiergraph_concept_compare_v1"
PROTOCOL_PATH = ROOT / "paper/frontiergraph_ontology_compare_protocol_v1.md"

REGIMES = [
    {"name": "broad", "label": "Broad", "min_distinct_papers": 5, "min_distinct_journals": 3},
    {"name": "baseline", "label": "Baseline", "min_distinct_papers": 10, "min_distinct_journals": 3},
    {"name": "conservative", "label": "Conservative", "min_distinct_papers": 15, "min_distinct_journals": 3},
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_command(cmd: list[str]) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def build_regime(regime: dict[str, Any]) -> tuple[Path, Path]:
    ontology_root = ONTOLOGY_COMPARE_ROOT / regime["name"]
    concept_root = CONCEPT_COMPARE_ROOT / regime["name"]
    ensure_dir(ontology_root)
    ensure_dir(concept_root)
    ontology_manifest = ontology_root / "manifest.json"
    concept_manifest = concept_root / "manifest.json"
    if not ontology_manifest.exists():
        run_command(
            [
                sys.executable,
                str(ONTOLOGY_SCRIPT),
                "--v2-db",
                str(V2_DB),
                "--output-root",
                str(ontology_root),
                "--ontology-version",
                f"compare_v1_{regime['name']}",
                "--min-distinct-papers",
                str(regime["min_distinct_papers"]),
                "--min-distinct-journals",
                str(regime["min_distinct_journals"]),
                "--support-only-heads",
            ]
        )
    if not concept_manifest.exists():
        run_command(
            [
                sys.executable,
                str(CONCEPT_SCRIPT),
                "--ontology-db",
                str(ontology_root / "ontology_v3.sqlite"),
                "--output-root",
                str(concept_root),
            ]
        )
    return ontology_root, concept_root


def export_manual_head_review(ontology_db: Path, output_root: Path, regime_label: str) -> None:
    conn = sqlite3.connect(ontology_db)
    conn.row_factory = sqlite3.Row
    try:
        top_heads = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    hc.concept_id,
                    hc.preferred_label,
                    hc.instance_support,
                    hc.distinct_paper_support,
                    hc.aliases_count,
                    hc.selection_rank,
                    hc.review_status,
                    hc.cluster_member_labels_json
                FROM head_concepts hc
                ORDER BY hc.selection_rank ASC, hc.instance_support DESC
                LIMIT 200
                """
            ).fetchall()
        ]
        top_hard = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    im.normalized_label,
                    im.concept_id,
                    hc.preferred_label AS concept_label,
                    im.mapping_source,
                    im.confidence,
                    ns.instance_count,
                    ns.distinct_papers,
                    ns.distinct_journals
                FROM instance_mappings_hard im
                JOIN node_strings ns
                  ON ns.normalized_label = im.normalized_label
                LEFT JOIN head_concepts hc
                  ON hc.concept_id = im.concept_id
                WHERE im.mapping_source IN ('embedding_auto', 'embedding_manual')
                GROUP BY im.normalized_label, im.concept_id, hc.preferred_label, im.mapping_source, im.confidence,
                         ns.instance_count, ns.distinct_papers, ns.distinct_journals
                ORDER BY ns.instance_count DESC, im.confidence DESC, im.normalized_label
                LIMIT 200
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    review_rows: list[dict[str, Any]] = []
    for row in top_heads:
        review_rows.append(
            {
                "row_type": "head",
                "concept_id": row["concept_id"],
                "preferred_label": row["preferred_label"],
                "instance_support": row["instance_support"],
                "distinct_paper_support": row["distinct_paper_support"],
                "aliases_count": row["aliases_count"],
                "selection_rank": row["selection_rank"],
                "review_status": row["review_status"],
                "cluster_member_labels_json": row["cluster_member_labels_json"],
                "manual_decision": "",
                "review_notes": "",
            }
        )
    for row in top_hard:
        review_rows.append(
            {
                "row_type": "hard_mapping",
                "concept_id": row["concept_id"],
                "preferred_label": row["concept_label"],
                "instance_support": row["instance_count"],
                "distinct_paper_support": row["distinct_papers"],
                "aliases_count": "",
                "selection_rank": "",
                "review_status": row["mapping_source"],
                "cluster_member_labels_json": row["normalized_label"],
                "manual_decision": "",
                "review_notes": "",
            }
        )
    write_csv(
        output_root / "review" / "manual_head_review.csv",
        review_rows,
        [
            "row_type",
            "concept_id",
            "preferred_label",
            "instance_support",
            "distinct_paper_support",
            "aliases_count",
            "selection_rank",
            "review_status",
            "cluster_member_labels_json",
            "manual_decision",
            "review_notes",
        ],
    )
    write_csv(
        output_root / "review" / "manual_negative_overrides.csv",
        [],
        ["override_kind", "left_label", "right_label", "label", "reason"],
    )
    memo = "\n".join(
        [
            f"# {regime_label} Manual Head Review Memo",
            "",
            "This file is the regime-specific audit starter for the ontology comparison build.",
            "",
            "- Review the top 200 heads by support/rank.",
            "- Review the top 200 hard embedding-derived mappings.",
            "- Record only negative overrides or forced splits here; keep conservative identity rules.",
            "",
        ]
    )
    (output_root / "review" / "manual_head_review_memo.md").write_text(memo, encoding="utf-8")


def export_manual_soft_audit(ontology_db: Path, output_root: Path, regime_label: str) -> None:
    conn = sqlite3.connect(ontology_db)
    conn.row_factory = sqlite3.Row
    try:
        high_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity,
                       margin, graph_context_similarity, lexical_contradiction, candidate_source
                FROM tail_soft_candidates
                WHERE candidate_rank = 1
                ORDER BY cosine_similarity DESC, margin DESC, normalized_label
                LIMIT 100
                """
            ).fetchall()
        ]
        medium_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity,
                       margin, graph_context_similarity, lexical_contradiction, candidate_source
                FROM tail_soft_candidates
                WHERE candidate_rank = 1
                ORDER BY ABS(COALESCE(cosine_similarity, 0.0) - 0.90) ASC, normalized_label
                LIMIT 100
                """
            ).fetchall()
        ]
        low_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT normalized_label, candidate_concept_id, candidate_preferred_label, cosine_similarity,
                       margin, graph_context_similarity, lexical_contradiction, candidate_source
                FROM tail_soft_candidates
                WHERE candidate_rank = 1
                ORDER BY COALESCE(cosine_similarity, 0.0) ASC, normalized_label
                LIMIT 100
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    rows: list[dict[str, Any]] = []
    for audit_bucket, bucket_rows in [("high", high_rows), ("medium", medium_rows), ("low", low_rows)]:
        for row in bucket_rows:
            row = dict(row)
            row["audit_bucket"] = audit_bucket
            row["manual_decision"] = ""
            row["review_notes"] = ""
            rows.append(row)
    write_csv(
        output_root / "review" / "manual_soft_audit.csv",
        rows,
        [
            "audit_bucket",
            "normalized_label",
            "candidate_concept_id",
            "candidate_preferred_label",
            "cosine_similarity",
            "margin",
            "graph_context_similarity",
            "lexical_contradiction",
            "candidate_source",
            "manual_decision",
            "review_notes",
        ],
    )
    summary = "\n".join(
        [
            f"# {regime_label} Manual Soft Audit Summary",
            "",
            "- Sample contains 100 high-confidence, 100 medium-confidence, and 100 low-confidence top-1 soft assignments.",
            "- Purpose: audit exploratory precision without manually adjudicating the entire soft map.",
            "",
        ]
    )
    (output_root / "review" / "manual_soft_audit_summary.md").write_text(summary, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_regime(regime: dict[str, Any], ontology_root: Path, concept_root: Path) -> dict[str, Any]:
    ontology_manifest = load_json(ontology_root / "manifest.json")
    concept_manifest = load_json(concept_root / "manifest.json")
    concept_views = concept_manifest.get("views", {})
    hard_view = concept_views.get("hard", concept_manifest.get("hard", {}))
    exploratory_view = concept_views.get("exploratory", concept_manifest.get("exploratory", {}))
    return {
        "regime": regime["name"],
        "label": regime["label"],
        "min_distinct_papers": regime["min_distinct_papers"],
        "min_distinct_journals": regime["min_distinct_journals"],
        "head_candidate_count": ontology_manifest["counts"]["head_candidate_count"],
        "head_count": ontology_manifest["counts"]["final_head_count"],
        "hard_mapped_instances": ontology_manifest["counts"]["hard_mapped_instances"],
        "hard_unresolved_instances": ontology_manifest["counts"]["hard_unresolved_instances"],
        "soft_mapped_instances": ontology_manifest["counts"]["soft_mapped_instances"],
        "soft_unresolved_instances": ontology_manifest["counts"]["soft_unresolved_instances"],
        "hard_coverage": ontology_manifest["counts"]["hard_mapped_instances"] / ontology_manifest["counts"]["node_instances"],
        "soft_coverage": ontology_manifest["counts"]["soft_mapped_instances"] / ontology_manifest["counts"]["node_instances"],
        "strict_concept_nodes": hard_view["counts"]["concept_nodes"],
        "strict_concept_edges": hard_view["counts"]["concept_edges"],
        "strict_candidate_rows": hard_view["counts"]["candidate_rows"],
        "exploratory_concept_nodes": exploratory_view["counts"]["concept_nodes"],
        "exploratory_concept_edges": exploratory_view["counts"]["concept_edges"],
        "exploratory_candidate_rows": exploratory_view["counts"]["candidate_rows"],
    }


def top_candidate_keys(app_db: Path, limit: int = 100) -> set[str]:
    conn = sqlite3.connect(app_db)
    try:
        rows = conn.execute(
            "SELECT u, v FROM candidates ORDER BY score DESC, u, v LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return {f"{row[0]}__{row[1]}" for row in rows}


def top_edge_rows(graph_db: Path, limit: int = 100) -> list[dict[str, Any]]:
    conn = sqlite3.connect(graph_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source_concept_id, target_concept_id, support_count, distinct_papers, avg_stability
                FROM concept_edges
                ORDER BY support_count DESC, distinct_papers DESC, source_concept_id, target_concept_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        ]
    finally:
        conn.close()
    return rows


def build_comparison_summary(regime_summaries: list[dict[str, Any]]) -> None:
    analysis_root = ONTOLOGY_COMPARE_ROOT / "analysis"
    ensure_dir(analysis_root)
    write_csv(
        analysis_root / "regime_summary.csv",
        regime_summaries,
        list(regime_summaries[0].keys()),
    )
    write_json(analysis_root / "regime_summary.json", regime_summaries)

    overlap_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    candidate_sets: dict[str, set[str]] = {}
    for regime in REGIMES:
        concept_root = CONCEPT_COMPARE_ROOT / regime["name"]
        for variant, app_name, graph_name in [
            ("strict", "concept_hard_app.sqlite", "concept_graph_hard.sqlite"),
            ("exploratory", "concept_exploratory_app.sqlite", "concept_graph_exploratory.sqlite"),
        ]:
            key = f"{regime['name']}::{variant}"
            candidate_sets[key] = top_candidate_keys(concept_root / app_name)
            for row in top_edge_rows(concept_root / graph_name):
                row["regime"] = regime["name"]
                row["variant"] = variant
                edge_rows.append(row)

    for left, right in combinations(sorted(candidate_sets), 2):
        left_set = candidate_sets[left]
        right_set = candidate_sets[right]
        inter = len(left_set & right_set)
        union = len(left_set | right_set)
        overlap_rows.append(
            {
                "left": left,
                "right": right,
                "intersection_top100": inter,
                "jaccard_top100": (inter / union) if union else 0.0,
            }
        )
    write_csv(
        analysis_root / "ranking_overlap_top100.csv",
        overlap_rows,
        ["left", "right", "intersection_top100", "jaccard_top100"],
    )
    write_csv(
        analysis_root / "top_concept_edges.csv",
        edge_rows,
        ["regime", "variant", "source_concept_id", "target_concept_id", "support_count", "distinct_papers", "avg_stability"],
    )

    baseline = next(row for row in regime_summaries if row["regime"] == "baseline")
    summary_md = "\n".join(
        [
            "# FrontierGraph Ontology Compare v1",
            "",
            f"- default regime: Baseline (`{baseline['min_distinct_papers']} papers / {baseline['min_distinct_journals']} journals`)",
            f"- broad heads: `{next(row for row in regime_summaries if row['regime'] == 'broad')['head_count']}`",
            f"- baseline heads: `{baseline['head_count']}`",
            f"- conservative heads: `{next(row for row in regime_summaries if row['regime'] == 'conservative')['head_count']}`",
            "",
            "See `regime_summary.csv` and `ranking_overlap_top100.csv` for sensitivity comparisons.",
            "",
        ]
    )
    (analysis_root / "sensitivity_summary.md").write_text(summary_md, encoding="utf-8")


def write_protocol(regime_summaries: list[dict[str, Any]]) -> None:
    broad = next(row for row in regime_summaries if row["regime"] == "broad")
    baseline = next(row for row in regime_summaries if row["regime"] == "baseline")
    conservative = next(row for row in regime_summaries if row["regime"] == "conservative")
    text = "\n".join(
        [
            "# FrontierGraph Ontology Compare Protocol v1",
            "",
            "## Overview",
            "",
            "This protocol records the first support-gated ontology comparison build. It supersedes the earlier coverage-based `v3` head rule for production use while preserving that run as a diagnostic artifact.",
            "",
            "## Why support-gated regimes were adopted",
            "",
            "The coverage-based `v3` rule produced very high coverage only by promoting too much of the label universe into heads. The comparison build therefore returns to support-gated head pools and treats graph reuse as a ranking/refinement signal within each regime rather than as a separate hard gate.",
            "",
            "## Frozen regimes",
            "",
            f"- Broad: `distinct_papers >= {broad['min_distinct_papers']}` and `distinct_journals >= {broad['min_distinct_journals']}`",
            f"- Baseline: `distinct_papers >= {baseline['min_distinct_papers']}` and `distinct_journals >= {baseline['min_distinct_journals']}`",
            f"- Conservative: `distinct_papers >= {conservative['min_distinct_papers']}` and `distinct_journals >= {conservative['min_distinct_journals']}`",
            "",
            "## Mapping layers",
            "",
            "- Strict: conservative identity mapping only",
            "- Exploratory: strict mappings plus soft nearest-head assignment for unresolved tails",
            "",
            "## Product default",
            "",
            "- default ontology: Baseline",
            "- default mapping mode: Exploratory",
            "- legacy JEL remains available as a separate fallback",
            "",
            "## Comparison artifacts",
            "",
            "- regime manifests and review exports are written under `data/production/frontiergraph_ontology_compare_v1/`",
            "- regime concept graph/app outputs are written under `data/production/frontiergraph_concept_compare_v1/`",
            "- sensitivity summaries are written under `data/production/frontiergraph_ontology_compare_v1/analysis/`",
            "",
            "See also `paper/frontiergraph_head_gate_deliberation.md` for the support-gate deliberation and grid search that motivated the baseline threshold.",
            "",
        ]
    )
    PROTOCOL_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dir(ONTOLOGY_COMPARE_ROOT)
    ensure_dir(CONCEPT_COMPARE_ROOT)
    regime_summaries: list[dict[str, Any]] = []
    for regime in REGIMES:
        ontology_root, concept_root = build_regime(regime)
        export_manual_head_review(ontology_root / "ontology_v3.sqlite", ontology_root, regime["label"])
        export_manual_soft_audit(ontology_root / "ontology_v3.sqlite", ontology_root, regime["label"])
        regime_summaries.append(summarize_regime(regime, ontology_root, concept_root))
    build_comparison_summary(regime_summaries)
    write_protocol(regime_summaries)


if __name__ == "__main__":
    main()
