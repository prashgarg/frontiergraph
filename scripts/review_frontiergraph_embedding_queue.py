from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from src.ontology_v2 import manual_pair_decision, select_cluster_preferred_label


DEFAULT_ONTOLOGY_DB = "data/production/frontiergraph_ontology_v2/ontology_v2.sqlite"
DEFAULT_OUTPUT_CSV = "data/production/frontiergraph_ontology_v2/review/embedding_review_completed.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply conservative Codex-style manual decisions to the ontology embedding review queue.")
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--out-csv", default=DEFAULT_OUTPUT_CSV)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = sqlite3.connect(args.ontology_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT erq.normalized_label,
               ns.preferred_label AS candidate_label,
               hc.preferred_label AS candidate_preferred_label,
               erq.candidate_concept_id,
               erq.cosine_similarity,
               erq.margin,
               erq.graph_context_similarity,
               erq.lexical_contradiction,
               erq.notes
        FROM embedding_review_queue erq
        LEFT JOIN node_strings ns ON ns.normalized_label = erq.normalized_label
        LEFT JOIN head_concepts hc ON hc.concept_id = erq.candidate_concept_id
        ORDER BY ns.instance_count DESC, erq.cosine_similarity DESC, erq.margin ASC, erq.normalized_label
        """
    ).fetchall()
    conn.close()

    output_path = Path(args.out_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "normalized_label",
            "candidate_concept_id",
            "candidate_preferred_label",
            "cosine_similarity",
            "margin",
            "graph_context_similarity",
            "lexical_contradiction",
            "manual_decision",
            "preferred_label_override",
            "review_notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            left = str(row["candidate_label"] or row["normalized_label"])
            right = str(row["candidate_preferred_label"] or "")
            decision = manual_pair_decision(left, right)
            if decision.decision == "same_concept":
                preferred = decision.preferred_label_override or select_cluster_preferred_label({left: 1, right: 1})
            else:
                preferred = "NA"
            writer.writerow(
                {
                    "normalized_label": row["normalized_label"],
                    "candidate_concept_id": row["candidate_concept_id"],
                    "candidate_preferred_label": row["candidate_preferred_label"],
                    "cosine_similarity": row["cosine_similarity"],
                    "margin": row["margin"],
                    "graph_context_similarity": row["graph_context_similarity"],
                    "lexical_contradiction": row["lexical_contradiction"],
                    "manual_decision": decision.decision,
                    "preferred_label_override": preferred,
                    "review_notes": decision.review_notes,
                }
            )


if __name__ == "__main__":
    main()
