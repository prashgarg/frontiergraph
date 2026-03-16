from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PUBLIC_APP_DB = ROOT / "data" / "production" / "frontiergraph_concept_compare_v1" / "baseline" / "suppression" / "concept_exploratory_suppressed_top100k_app.sqlite"
DEFAULT_BASELINE_ONTOLOGY_DB = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "baseline" / "ontology_v3.sqlite"
DEFAULT_BROAD_ONTOLOGY_DB = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "broad" / "ontology_v3.sqlite"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "production" / "frontiergraph_public_release" / "display_refinement_v1.json"

GENERIC_UMBRELLA_TERMS = {
    "consumption",
    "credit",
    "economic growth",
    "economic development",
    "development",
    "education",
    "employment",
    "financial development",
    "geopolitical risks",
    "human capital",
    "information and communication technologies",
    "inflation",
    "innovation",
    "institutional quality",
    "institutions",
    "investment",
    "model parameters",
    "monetary policy",
    "output growth",
    "price changes",
    "product innovation",
    "productivity",
    "public debt",
    "trade",
    "trade openness",
    "volatility",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a baseline-to-broad display refinement map for public FrontierGraph surfaces.")
    parser.add_argument(
        "--source-db",
        default=os.environ.get("FRONTIERGRAPH_PUBLIC_SOURCE_DB", str(DEFAULT_SOURCE_PUBLIC_APP_DB)),
        help="Baseline public app SQLite DB used for the public release.",
    )
    parser.add_argument(
        "--baseline-ontology-db",
        default=os.environ.get("FRONTIERGRAPH_BASELINE_ONTOLOGY_DB", str(DEFAULT_BASELINE_ONTOLOGY_DB)),
        help="Baseline ontology DB used for ranking and backtests.",
    )
    parser.add_argument(
        "--broad-ontology-db",
        default=os.environ.get("FRONTIERGRAPH_BROAD_ONTOLOGY_DB", str(DEFAULT_BROAD_ONTOLOGY_DB)),
        help="Broader ontology DB used for display refinement.",
    )
    parser.add_argument(
        "--output-path",
        default=os.environ.get("FRONTIERGRAPH_DISPLAY_REFINEMENT_PATH", str(DEFAULT_OUTPUT_PATH)),
        help="Output JSON artifact path.",
    )
    return parser.parse_args()


def connect(path: Path, *, immutable: bool = False) -> sqlite3.Connection:
    if immutable:
        conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalized_label(value: Any) -> str:
    text = clean_text(value).lower()
    text = text.replace("/", " ")
    text = " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text).split())
    return text


def token_count(value: Any) -> int:
    return len([token for token in normalized_label(value).split() if token])


def generic_penalty(label: str) -> float:
    normalized = normalized_label(label)
    penalty = 0.0
    if normalized in GENERIC_UMBRELLA_TERMS:
        penalty += 1.8
    if token_count(label) <= 2:
        penalty += 0.45
    return penalty


def compute_specificity_gain(
    baseline_label: str,
    candidate_label: str,
    baseline_support: int,
    candidate_support: int,
) -> float:
    gain = 0.0
    baseline_tokens = token_count(baseline_label)
    candidate_tokens = token_count(candidate_label)
    if candidate_tokens > baseline_tokens:
        gain += 0.75
    if len(normalized_label(candidate_label)) > len(normalized_label(baseline_label)) + 4:
        gain += 0.35
    if baseline_support and candidate_support and candidate_support < baseline_support:
        gain += min(0.85, math.log1p(baseline_support / max(candidate_support, 1)) / 2.25)
    gain -= generic_penalty(candidate_label)
    return gain


def load_public_concepts(source_db: Path) -> dict[str, dict[str, Any]]:
    with connect(source_db) as conn:
        rows = conn.execute(
            """
            SELECT concept_id, preferred_label, distinct_paper_support
            FROM node_details
            ORDER BY concept_id
            """
        ).fetchall()
    return {
        str(row["concept_id"]): {
            "baseline_label": clean_text(row["preferred_label"]),
            "baseline_support": int(row["distinct_paper_support"] or 0),
        }
        for row in rows
    }


def insert_temp_values(conn: sqlite3.Connection, table_name: str, column_name: str, values: list[str]) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"CREATE TEMP TABLE {table_name} ({column_name} TEXT PRIMARY KEY)")
    conn.executemany(
        f"INSERT OR IGNORE INTO {table_name}({column_name}) VALUES (?)",
        [(value,) for value in values if value],
    )


def load_baseline_label_rows(baseline_ontology_db: Path, public_concepts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    concept_ids = sorted(public_concepts)
    with connect(baseline_ontology_db, immutable=True) as conn:
        insert_temp_values(conn, "public_concepts", "concept_id", concept_ids)
        rows = conn.execute(
            """
            SELECT
                ims.concept_id,
                ims.normalized_label,
                COUNT(*) AS assignment_count,
                AVG(ims.confidence) AS avg_confidence,
                ns.preferred_label AS normalized_preferred_label,
                ns.distinct_papers AS normalized_distinct_papers
            FROM instance_mappings_soft ims
            INNER JOIN public_concepts pc
                ON pc.concept_id = ims.concept_id
            INNER JOIN node_strings ns
                ON ns.normalized_label = ims.normalized_label
            WHERE ims.concept_id IS NOT NULL
            GROUP BY ims.concept_id, ims.normalized_label
            ORDER BY ims.concept_id, assignment_count DESC, ims.normalized_label
            """
        ).fetchall()
    return [
        {
            "concept_id": str(row["concept_id"]),
            "normalized_label": str(row["normalized_label"]),
            "assignment_count": int(row["assignment_count"] or 0),
            "avg_confidence": float(row["avg_confidence"] or 0.0),
            "normalized_preferred_label": clean_text(row["normalized_preferred_label"]),
            "normalized_distinct_papers": int(row["normalized_distinct_papers"] or 0),
        }
        for row in rows
    ]


def load_broad_label_assignments(
    broad_ontology_db: Path,
    normalized_labels: list[str],
) -> dict[str, list[dict[str, Any]]]:
    with connect(broad_ontology_db, immutable=True) as conn:
        insert_temp_values(conn, "needed_labels", "normalized_label", sorted(set(normalized_labels)))
        rows = conn.execute(
            """
            SELECT
                ims.normalized_label,
                ims.concept_id AS broad_concept_id,
                COUNT(*) AS assignment_count,
                AVG(ims.confidence) AS avg_confidence,
                hc.preferred_label AS broad_label,
                hc.distinct_paper_support AS broad_distinct_paper_support
            FROM instance_mappings_soft ims
            INNER JOIN needed_labels nl
                ON nl.normalized_label = ims.normalized_label
            LEFT JOIN head_concepts hc
                ON hc.concept_id = ims.concept_id
            WHERE ims.concept_id IS NOT NULL
            GROUP BY ims.normalized_label, ims.concept_id
            ORDER BY ims.normalized_label, assignment_count DESC, ims.concept_id
            """
        ).fetchall()
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        lookup[str(row["normalized_label"])].append(
            {
                "broad_concept_id": str(row["broad_concept_id"]),
                "broad_label": clean_text(row["broad_label"]),
                "assignment_count": int(row["assignment_count"] or 0),
                "avg_confidence": float(row["avg_confidence"] or 0.0),
                "broad_distinct_paper_support": int(row["broad_distinct_paper_support"] or 0),
            }
        )
    return lookup


def choose_display_refinement(
    baseline_label: str,
    baseline_support: int,
    concept_rows: list[dict[str, Any]],
    broad_assignments: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    candidate_scores: dict[str, dict[str, Any]] = {}
    total_weight = 0.0

    for item in concept_rows:
        normalized = item["normalized_label"]
        label_weight = float(item["assignment_count"]) * (1.0 + min(item["normalized_distinct_papers"], 30) / 30.0)
        broad_matches = broad_assignments.get(normalized, [])
        if not broad_matches:
            continue
        broad_match = broad_matches[0]
        total_weight += label_weight
        entry = candidate_scores.setdefault(
            broad_match["broad_concept_id"],
            {
                "display_concept_id": broad_match["broad_concept_id"],
                "display_label": broad_match["broad_label"] or baseline_label,
                "weight": 0.0,
                "shared_label_count": 0,
                "confidence_sum": 0.0,
                "candidate_support": int(broad_match["broad_distinct_paper_support"] or 0),
                "sample_labels": [],
            },
        )
        entry["weight"] += label_weight
        entry["shared_label_count"] += 1
        entry["confidence_sum"] += float(broad_match["avg_confidence"] or 0.0) * label_weight
        if item["normalized_preferred_label"] and item["normalized_preferred_label"] not in entry["sample_labels"]:
            entry["sample_labels"].append(item["normalized_preferred_label"])

    sorted_candidates = sorted(
        candidate_scores.values(),
        key=lambda item: (
            item["weight"],
            item["shared_label_count"],
            -item["candidate_support"],
            item["display_label"],
        ),
        reverse=True,
    )

    base_normalized = normalized_label(baseline_label)
    if not sorted_candidates:
        return {
            "display_concept_id": "",
            "display_label": baseline_label,
            "display_refined": False,
            "display_refinement_confidence": 0.0,
            "fallback": True,
            "alternate_display_labels": [],
            "candidate_preview": [],
        }

    def decorate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
        share = candidate["weight"] / total_weight if total_weight > 0 else 0.0
        specificity_gain = compute_specificity_gain(
            baseline_label,
            candidate["display_label"],
            baseline_support,
            int(candidate["candidate_support"]),
        )
        confidence = candidate["confidence_sum"] / candidate["weight"] if candidate["weight"] > 0 else 0.0
        return {
            **candidate,
            "share": share,
            "specificity_gain": specificity_gain,
            "confidence": confidence,
        }

    decorated = [decorate_candidate(candidate) for candidate in sorted_candidates]
    top = decorated[0]
    runner_up_weight = decorated[1]["weight"] if len(decorated) > 1 else 0.0
    same_label = normalized_label(top["display_label"]) == base_normalized
    dominant = top["share"] >= 0.42 or (top["share"] >= 0.32 and top["weight"] >= runner_up_weight * 1.25)
    meaningful_refinement = top["specificity_gain"] >= 0.35
    accepted = bool(top["display_label"]) and not same_label and dominant and meaningful_refinement

    alternate_labels = [
        clean_text(candidate["display_label"])
        for candidate in decorated[1:]
        if normalized_label(candidate["display_label"]) != base_normalized and candidate["specificity_gain"] > 0
    ]

    top_confidence = min(
        0.98,
        max(
            0.0,
            0.55 * float(top["share"])
            + 0.25 * float(top["confidence"])
            + 0.20 * max(float(top["specificity_gain"]), 0.0),
        ),
    )

    return {
        "display_concept_id": str(top["display_concept_id"]) if accepted else "",
        "display_label": clean_text(top["display_label"]) if accepted else baseline_label,
        "display_refined": accepted,
        "display_refinement_confidence": round(top_confidence, 4) if accepted else 0.0,
        "fallback": not accepted,
        "alternate_display_labels": alternate_labels[:3],
        "candidate_preview": [
            {
                "display_concept_id": str(candidate["display_concept_id"]),
                "display_label": clean_text(candidate["display_label"]),
                "weight": round(float(candidate["weight"]), 4),
                "share": round(float(candidate["share"]), 4),
                "specificity_gain": round(float(candidate["specificity_gain"]), 4),
                "confidence": round(float(candidate["confidence"]), 4),
                "shared_label_count": int(candidate["shared_label_count"]),
                "candidate_support": int(candidate["candidate_support"]),
                "sample_labels": candidate["sample_labels"][:4],
            }
            for candidate in decorated[:5]
        ],
    }


def build_refinement_payload(
    source_db: Path,
    baseline_ontology_db: Path,
    broad_ontology_db: Path,
) -> dict[str, Any]:
    public_concepts = load_public_concepts(source_db)
    baseline_rows = load_baseline_label_rows(baseline_ontology_db, public_concepts)
    broad_assignments = load_broad_label_assignments(
        broad_ontology_db,
        [row["normalized_label"] for row in baseline_rows],
    )

    rows_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        rows_by_concept[row["concept_id"]].append(row)

    concepts_payload: dict[str, Any] = {}
    refined_count = 0
    fallback_count = 0
    confidence_values: list[float] = []
    for concept_id, metadata in public_concepts.items():
        refinement = choose_display_refinement(
            metadata["baseline_label"],
            int(metadata["baseline_support"]),
            rows_by_concept.get(concept_id, []),
            broad_assignments,
        )
        concepts_payload[concept_id] = {
            "baseline_concept_id": concept_id,
            "baseline_label": metadata["baseline_label"],
            "baseline_distinct_paper_support": int(metadata["baseline_support"]),
            **refinement,
        }
        if refinement["display_refined"]:
            refined_count += 1
            confidence_values.append(float(refinement["display_refinement_confidence"]))
        else:
            fallback_count += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "public_source_db": str(source_db),
            "baseline_ontology_db": str(baseline_ontology_db),
            "broad_ontology_db": str(broad_ontology_db),
            "variant": "baseline_to_broad_display_layer_v1",
        },
        "summary": {
            "public_concept_count": len(public_concepts),
            "refined_concept_count": refined_count,
            "fallback_concept_count": fallback_count,
            "refined_share": round(refined_count / len(public_concepts), 4) if public_concepts else 0.0,
            "mean_refinement_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
        },
        "concepts": concepts_payload,
    }


def main() -> None:
    args = parse_args()
    source_db = Path(args.source_db)
    baseline_ontology_db = Path(args.baseline_ontology_db)
    broad_ontology_db = Path(args.broad_ontology_db)
    output_path = Path(args.output_path)

    payload = build_refinement_payload(source_db, baseline_ontology_db, broad_ontology_db)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                **payload["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
