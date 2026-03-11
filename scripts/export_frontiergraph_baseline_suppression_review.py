from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scripts.build_frontiergraph_baseline_suppression import DEFAULT_OUTPUT_ROOT, write_protocol


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export review artifacts from the finalized baseline suppression DB.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--lambda-weight", type=float, default=0.50)
    parser.add_argument("--top-k-shift", type=int, default=5000)
    return parser.parse_args()


def ensure_dirs(output_root: Path) -> tuple[Path, Path]:
    analysis_dir = output_root / "analysis"
    review_dir = output_root / "review"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir, review_dir


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    target_db = output_root / "concept_exploratory_suppressed_app.sqlite"
    analysis_dir, review_dir = ensure_dirs(output_root)

    conn = sqlite3.connect(target_db)
    try:
        before = pd.read_sql_query(
            """
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label, base_score
            FROM candidates_scored
            ORDER BY base_rank
            LIMIT 100
            """,
            conn,
        )
        after = pd.read_sql_query(
            """
            SELECT u, v, u_preferred_label, v_preferred_label, base_score, final_score,
                   duplicate_penalty, hard_same_family_reason
            FROM candidates_scored
            WHERE suppressed = 0
            ORDER BY final_score DESC, base_score DESC, u, v
            LIMIT 100
            """,
            conn,
        )
        after.insert(0, "final_rank", range(1, len(after) + 1))

        removed = pd.read_sql_query(
            """
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label, base_score,
                   hard_same_family_reason
            FROM candidates_scored
            WHERE suppressed = 1
            ORDER BY base_score DESC, base_rank ASC
            LIMIT 250
            """,
            conn,
        )

        before_shift = pd.read_sql_query(
            f"""
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label, base_score
            FROM candidates_scored
            ORDER BY base_rank
            LIMIT {int(args.top_k_shift)}
            """,
            conn,
        )
        after_shift = pd.read_sql_query(
            f"""
            SELECT u, v, u_preferred_label, v_preferred_label, base_score, final_score, duplicate_penalty
            FROM candidates_scored
            WHERE suppressed = 0
            ORDER BY final_score DESC, base_score DESC, u, v
            LIMIT {int(args.top_k_shift)}
            """,
            conn,
        )
        after_shift.insert(0, "final_rank", range(1, len(after_shift) + 1))
        downranked = before_shift.merge(
            after_shift,
            on=["u", "v"],
            how="inner",
            suffixes=("_base", "_final"),
        )
        downranked["rank_shift"] = downranked["final_rank"] - downranked["base_rank"]
        downranked = downranked.sort_values(
            ["rank_shift", "duplicate_penalty", "final_score"],
            ascending=[False, False, False],
        ).head(250)
        downranked = downranked[
            [
                "base_rank",
                "final_rank",
                "rank_shift",
                "u",
                "v",
                "u_preferred_label_base",
                "v_preferred_label_base",
                "base_score_base",
                "final_score",
                "duplicate_penalty",
            ]
        ].rename(
            columns={
                "u_preferred_label_base": "u_preferred_label",
                "v_preferred_label_base": "v_preferred_label",
                "base_score_base": "base_score",
            }
        )

        central_ids = [
            row[0]
            for row in conn.execute(
                """
                SELECT concept_id
                FROM (
                    SELECT source_concept_id AS concept_id, support_count AS weight FROM concept_edges
                    UNION ALL
                    SELECT target_concept_id AS concept_id, support_count AS weight FROM concept_edges
                )
                GROUP BY concept_id
                ORDER BY SUM(weight) DESC
                LIMIT 100
                """
            ).fetchall()
        ]
        if central_ids:
            placeholders = ",".join("?" for _ in central_ids)
            central_df = pd.read_sql_query(
                f"""
                SELECT base_rank, u, v, u_preferred_label, v_preferred_label,
                       base_score, final_score, duplicate_penalty, hard_same_family_reason,
                       contrastive_reason
                FROM candidates_scored
                WHERE (u IN ({placeholders}) OR v IN ({placeholders}))
                ORDER BY duplicate_penalty DESC, base_score DESC
                LIMIT 200
                """,
                conn,
                params=tuple(central_ids) * 2,
            )
        else:
            central_df = pd.DataFrame()

        high_penalty_top500 = pd.read_sql_query(
            """
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label,
                   base_score, final_score, duplicate_penalty, hard_same_family_reason,
                   contrastive_reason
            FROM candidates_scored
            WHERE base_rank <= 500
            ORDER BY duplicate_penalty DESC, base_score DESC
            LIMIT 250
            """,
            conn,
        )

        boundary = pd.read_sql_query(
            """
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label,
                   base_score, final_score, duplicate_penalty, hard_same_family_reason,
                   alias_overlap, embedding_similarity, lexical_overlap
            FROM candidates_scored
            WHERE suppressed = 0
              AND hard_same_family = 0
              AND (
                    alias_overlap >= 0.6
                 OR (duplicate_penalty BETWEEN 0.35 AND 0.55)
              )
            ORDER BY base_score DESC
            LIMIT 200
            """,
            conn,
        )

        stats_row = conn.execute(
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

    before.to_csv(analysis_dir / "top100_before.csv", index=False)
    after.to_csv(analysis_dir / "top100_after.csv", index=False)
    removed.to_csv(analysis_dir / "removed_by_hard_block.csv", index=False)
    downranked.to_csv(analysis_dir / "largest_downranked_pairs.csv", index=False)

    queue_frames = []
    if not removed.empty:
        top_hard = removed.head(100).copy()
        top_hard.insert(0, "queue_section", "hard_block_top_loss")
        queue_frames.append(top_hard)
    if not high_penalty_top500.empty:
        hp = high_penalty_top500.copy()
        hp.insert(0, "queue_section", "high_penalty_top500")
        queue_frames.append(hp)
    if not central_df.empty:
        cp = central_df.copy()
        cp.insert(0, "queue_section", "high_centrality_pairs")
        queue_frames.append(cp)
    if not boundary.empty:
        bc = boundary.copy()
        bc.insert(0, "queue_section", "boundary_cases")
        queue_frames.append(bc)
    queue = pd.concat(queue_frames, ignore_index=True) if queue_frames else pd.DataFrame()
    if not queue.empty:
        queue = queue.drop_duplicates(subset=["u", "v"], keep="first")
    queue.to_csv(review_dir / "suppression_review_queue.csv", index=False)

    top100_before_pairs = set(zip(before["u"], before["v"]))
    top100_after_pairs = set(zip(after["u"], after["v"]))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lambda_weight": float(args.lambda_weight),
        "candidate_count": int(stats_row[0] or 0),
        "suppressed_count": int(stats_row[1] or 0),
        "hard_same_family_count": int(stats_row[2] or 0),
        "override_count": int(stats_row[3] or 0),
        "top100_removed_count": int(len(top100_before_pairs - top100_after_pairs)),
        "top100_overlap_count": int(len(top100_before_pairs & top100_after_pairs)),
        "mean_duplicate_penalty_top100_after": float(after["duplicate_penalty"].mean()) if not after.empty else 0.0,
        "mean_duplicate_penalty_top500_before": float(high_penalty_top500["duplicate_penalty"].mean()) if not high_penalty_top500.empty else 0.0,
        "hard_block_reason_counts": removed["hard_same_family_reason"].value_counts().to_dict(),
    }
    (analysis_dir / "suppression_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    review_lines = [
        "# Baseline exploratory suppression review",
        "",
        f"- Lambda weight: `{float(args.lambda_weight):.2f}`",
        f"- Candidate rows analyzed: `{summary['candidate_count']:,}`",
        f"- Hard-suppressed rows: `{summary['suppressed_count']:,}`",
        f"- Top-100 overlap after suppression: `{summary['top100_overlap_count']}`",
        f"- Top-100 pairs removed or replaced: `{summary['top100_removed_count']}`",
        "",
        "## Main reasons for hard suppression",
    ]
    for reason, count in summary["hard_block_reason_counts"].items():
        review_lines.append(f"- `{reason}`: `{count:,}`")
    review_lines.extend(
        [
            "",
            "## Notes",
            "- This suppression layer is baseline-exploratory only.",
            "- Hard suppression uses high-precision same-family rules.",
            "- Soft penalties preserve candidates but down-rank semantically too-close pairs.",
            "- Consequential review starts from `suppression_review_queue.csv` and explicit overrides rather than a large hand-written protection list.",
        ]
    )
    (analysis_dir / "suppression_review.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")
    write_protocol(Path("paper/frontiergraph_duplicate_suppression_protocol_v1.md"))


if __name__ == "__main__":
    main()
