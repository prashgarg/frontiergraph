from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path

from src.ontology_v1 import canonical_pair
from src.ontology_v2 import (
    BLOCKED_AUTO_MERGE_PAIRS,
    HEAD_AUDIT_MEMO_LINES,
    ISOLATE_LABELS,
    PAIRWISE_DIFFERENT_CONCEPTS,
    manual_pair_decision,
)


DEFAULT_V1_DB = "data/production/frontiergraph_ontology_v1/ontology_v1.sqlite"
DEFAULT_REVIEW_CSV = "data/production/frontiergraph_ontology_v1/review/candidate_pairs_review.csv"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_ontology_v2/review"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    output_root = Path(DEFAULT_OUTPUT_ROOT)
    output_root.mkdir(parents=True, exist_ok=True)

    review_rows: list[dict[str, object]] = []
    decision_counts = Counter()
    with Path(DEFAULT_REVIEW_CSV).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            decision = manual_pair_decision(row["left_normalized_label"], row["right_normalized_label"])
            out = dict(row)
            out["manual_decision"] = decision.decision
            out["preferred_label_override"] = decision.preferred_label_override
            out["review_notes"] = decision.review_notes
            review_rows.append(out)
            decision_counts[decision.decision] += 1

    review_fieldnames = list(review_rows[0].keys()) if review_rows else []
    write_csv(output_root / "candidate_pairs_review_completed.csv", review_rows, review_fieldnames)

    manual_negative_overrides: list[dict[str, object]] = []
    for left_label, right_label in sorted(BLOCKED_AUTO_MERGE_PAIRS):
        manual_negative_overrides.append(
            {
                "override_kind": "block_pair",
                "left_normalized_label": left_label,
                "right_normalized_label": right_label,
                "label": "",
                "reason": "Manual Codex audit: block over-broad or acronym-collision auto-merge.",
            }
        )
    for label in sorted(ISOLATE_LABELS):
        manual_negative_overrides.append(
            {
                "override_kind": "isolate_label",
                "left_normalized_label": "",
                "right_normalized_label": "",
                "label": label,
                "reason": "Manual Codex audit: isolate label from over-broad auto cluster.",
            }
        )

    write_csv(
        output_root / "manual_negative_overrides.csv",
        manual_negative_overrides,
        ["override_kind", "left_normalized_label", "right_normalized_label", "label", "reason"],
    )

    conn = sqlite3.connect(DEFAULT_V1_DB)
    conn.row_factory = sqlite3.Row

    accepted_auto_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT left_normalized_label, right_normalized_label, lexical_score, neighbor_jaccard,
                   relationship_profile_similarity, edge_role_profile_similarity, country_overlap,
                   unit_overlap, bucket_profile_similarity, combined_score, notes
            FROM candidate_pairs
            WHERE decision_status = 'accepted_auto'
            ORDER BY combined_score DESC, left_normalized_label, right_normalized_label
            LIMIT 200
            """
        ).fetchall()
    ]
    for row in accepted_auto_rows:
        pair = canonical_pair(row["left_normalized_label"], row["right_normalized_label"])
        row["audit_status"] = "blocked_by_manual_override" if pair in BLOCKED_AUTO_MERGE_PAIRS else "keep"

    top_head_rows = []
    for row in conn.execute(
        """
        SELECT concept_id, preferred_label, instance_support, aliases_count, cluster_member_labels_json
        FROM head_concepts
        ORDER BY instance_support DESC, concept_id
        LIMIT 200
        """
    ):
        payload = dict(row)
        members = json.loads(payload["cluster_member_labels_json"])
        affected = [label for label in members if label in ISOLATE_LABELS]
        payload["audit_status"] = "manual_split_override" if affected else "keep"
        payload["affected_labels_json"] = json.dumps(affected, ensure_ascii=False)
        top_head_rows.append(payload)

    write_csv(
        output_root / "accepted_auto_pairs_audit.csv",
        accepted_auto_rows,
        list(accepted_auto_rows[0].keys()) if accepted_auto_rows else ["left_normalized_label"],
    )
    write_csv(
        output_root / "top_head_concepts_audit.csv",
        top_head_rows,
        list(top_head_rows[0].keys()) if top_head_rows else ["concept_id"],
    )

    memo_lines = [
        "# FrontierGraph Ontology v2 Manual Review Memo",
        "",
        "This review file was completed by Codex using the explicit conservative adjudication rules requested by the user.",
        "",
        "## Pairwise review counts",
        "",
    ]
    for decision, count in sorted(decision_counts.items()):
        memo_lines.append(f"- `{decision}`: {count}")
    memo_lines.extend(
        [
            "",
            "## Manual negative overrides",
            "",
            f"- `block_pair` overrides: {sum(1 for row in manual_negative_overrides if row['override_kind'] == 'block_pair')}",
            f"- `isolate_label` overrides: {sum(1 for row in manual_negative_overrides if row['override_kind'] == 'isolate_label')}",
            "",
            "## Recurring audit patterns",
            "",
        ]
    )
    for line in HEAD_AUDIT_MEMO_LINES:
        memo_lines.append(f"- {line}")
    memo_lines.extend(
        [
            "",
            "## Explicit pairwise different-concept decisions",
            "",
        ]
    )
    for left_label, right_label in sorted(PAIRWISE_DIFFERENT_CONCEPTS):
        memo_lines.append(f"- `{left_label}` vs `{right_label}`")
    (output_root / "manual_review_audit_memo.md").write_text("\n".join(memo_lines) + "\n", encoding="utf-8")

    write_json(
        output_root / "manual_review_manifest.json",
        {
            "pairwise_review_rows": len(review_rows),
            "pairwise_review_counts": dict(decision_counts),
            "blocked_auto_merge_pairs": len(BLOCKED_AUTO_MERGE_PAIRS),
            "isolated_labels": len(ISOLATE_LABELS),
            "top_accepted_auto_audited": len(accepted_auto_rows),
            "top_heads_audited": len(top_head_rows),
        },
    )
    conn.close()


if __name__ == "__main__":
    main()
