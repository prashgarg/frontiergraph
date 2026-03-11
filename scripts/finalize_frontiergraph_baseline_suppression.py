from __future__ import annotations

import argparse
from pathlib import Path

from scripts.build_frontiergraph_baseline_suppression import (
    DEFAULT_OUTPUT_ROOT,
    export_review_outputs,
    finalize_target_db,
    load_concept_profiles,
    write_protocol,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize an interrupted baseline suppression build.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--app-db",
        default="data/production/frontiergraph_concept_compare_v1/baseline/concept_exploratory_app.sqlite",
    )
    parser.add_argument(
        "--ontology-db",
        default="data/production/frontiergraph_ontology_compare_v1/baseline/ontology_v3.sqlite",
    )
    parser.add_argument("--lambda-weight", type=float, default=0.50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    target_db = output_root / "concept_exploratory_suppressed_app.sqlite"
    if not target_db.exists():
        raise SystemExit(f"Suppressed DB not found: {target_db}")

    import sqlite3

    conn = sqlite3.connect(target_db)
    try:
        finalize_target_db(conn)
    finally:
        conn.close()

    _profiles, centrality = load_concept_profiles(Path(args.app_db), Path(args.ontology_db))
    conn = sqlite3.connect(target_db)
    try:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS candidate_count,
              SUM(CASE WHEN suppressed = 1 THEN 1 ELSE 0 END) AS suppressed_count,
              SUM(CASE WHEN hard_same_family = 1 THEN 1 ELSE 0 END) AS hard_same_family_count,
              SUM(CASE WHEN COALESCE(override_type, '') <> '' THEN 1 ELSE 0 END) AS override_count
            FROM candidates_scored
            """
        ).fetchone()
    finally:
        conn.close()
    stats = {
        "candidate_count": int(row[0] or 0),
        "suppressed_count": int(row[1] or 0),
        "hard_same_family_count": int(row[2] or 0),
        "override_count": int(row[3] or 0),
    }

    export_review_outputs(
        target_db=target_db,
        output_root=output_root,
        centrality=centrality,
        stats=stats,
        lambda_weight=float(args.lambda_weight),
    )
    write_protocol(Path("paper/frontiergraph_duplicate_suppression_protocol_v1.md"))


if __name__ == "__main__":
    main()
