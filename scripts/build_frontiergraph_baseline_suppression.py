from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.duplicate_suppression import (
    ConceptProfile,
    build_concept_profile,
    bucket_similarity,
    context_overlap,
    hard_same_family_reason,
    neighbor_overlap,
    pair_key,
    parse_json_object,
    parse_value_list,
    soft_duplicate_metrics,
)
from src.ontology_v1 import canonical_pair, normalize_label


DEFAULT_APP_DB = (
    "data/production/frontiergraph_concept_compare_v1/baseline/concept_exploratory_app.sqlite"
)
DEFAULT_ONTOLOGY_DB = (
    "data/production/frontiergraph_ontology_compare_v1/baseline/ontology_v3.sqlite"
)
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_concept_compare_v1/baseline/suppression"
DEFAULT_LAMBDA = 0.50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build baseline exploratory near-synonym suppression outputs.")
    parser.add_argument("--app-db", default=DEFAULT_APP_DB)
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--lambda-weight", type=float, default=DEFAULT_LAMBDA)
    parser.add_argument("--batch-size", type=int, default=10000)
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_reviewed_pairs(ontology_db: Path) -> dict[tuple[str, str], str]:
    conn = sqlite3.connect(ontology_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT left_normalized_label, right_normalized_label, final_decision
            FROM review_decisions
            WHERE final_decision IN ('same_concept', 'different_concept')
            """
        ).fetchall()
    finally:
        conn.close()
    return {
        canonical_pair(str(row["left_normalized_label"]), str(row["right_normalized_label"])): str(row["final_decision"])
        for row in rows
    }


def load_embeddings(ontology_db: Path) -> dict[str, list[float]]:
    conn = sqlite3.connect(ontology_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT normalized_label, vector_json FROM string_embeddings WHERE vector_json IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    embeddings: dict[str, list[float]] = {}
    for row in rows:
        embeddings[str(row["normalized_label"])] = json.loads(str(row["vector_json"]))
    return embeddings


def choose_vector(labels: list[str], embeddings: dict[str, list[float]]) -> list[float] | None:
    for label in labels:
        vector = embeddings.get(normalize_label(label))
        if vector is not None:
            return vector
    return None


def load_neighbor_map(app_db: Path) -> dict[str, set[str]]:
    conn = sqlite3.connect(app_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT source_concept_id, target_concept_id, support_count
            FROM concept_edges
            """
        ).fetchall()
    finally:
        conn.close()
    neighbors: dict[str, set[str]] = {}
    for row in rows:
        src = str(row["source_concept_id"])
        dst = str(row["target_concept_id"])
        neighbors.setdefault(src, set()).add(dst)
        neighbors.setdefault(dst, set()).add(src)
    return neighbors


def load_concept_profiles(app_db: Path, ontology_db: Path) -> tuple[dict[str, ConceptProfile], dict[str, float]]:
    embeddings = load_embeddings(ontology_db)
    neighbors = load_neighbor_map(app_db)
    conn = sqlite3.connect(app_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT concept_id, preferred_label, aliases_json, instance_support, bucket_profile_json,
                   top_countries, top_units
            FROM node_details
            """
        ).fetchall()
        centrality_rows = conn.execute(
            """
            SELECT concept_id, SUM(weight) AS centrality
            FROM (
                SELECT source_concept_id AS concept_id, support_count AS weight FROM concept_edges
                UNION ALL
                SELECT target_concept_id AS concept_id, support_count AS weight FROM concept_edges
            )
            GROUP BY concept_id
            """
        ).fetchall()
    finally:
        conn.close()

    profiles: dict[str, ConceptProfile] = {}
    for row in rows:
        concept_id = str(row["concept_id"])
        preferred = str(row["preferred_label"])
        aliases = [str(item) for item in parse_json_object(row["aliases_json"], []) if str(item).strip()]
        labels = [preferred] + [item for item in aliases if item != preferred]
        vector = choose_vector(labels, embeddings)
        profiles[concept_id] = build_concept_profile(
            concept_id=concept_id,
            preferred_label=preferred,
            aliases_json=row["aliases_json"],
            top_countries=row["top_countries"],
            top_units=row["top_units"],
            bucket_profile_json=row["bucket_profile_json"],
            support=int(row["instance_support"] or 0),
            neighbors=neighbors.get(concept_id, set()),
            vector=None if vector is None else np.asarray(vector, dtype=np.float32),
        )
    centrality = {str(row["concept_id"]): float(row["centrality"] or 0.0) for row in centrality_rows}
    return profiles, centrality


def ensure_override_file(path: Path) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pair_key",
                "override_type",
                "override_value",
                "decision_source",
                "notes",
                "reviewed_at",
                "review_version",
            ],
        )
        writer.writeheader()


def load_overrides(path: Path) -> dict[str, dict[str, str]]:
    ensure_override_file(path)
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader if row.get("pair_key")]
    return {str(row["pair_key"]): row for row in rows}


def prepare_target_db(source_db: Path, target_db: Path) -> sqlite3.Connection:
    ensure_dir(target_db.parent)
    if target_db.exists():
        target_db.unlink()
    shutil.copy2(source_db, target_db)
    conn = sqlite3.connect(target_db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("ALTER TABLE candidates RENAME TO candidates_raw")
    conn.execute(
        """
        CREATE TABLE candidates_scored AS
        SELECT
            rowid AS candidate_rowid,
            *,
            score AS base_score,
            rank AS base_rank,
            0.0 AS soft_duplicate_score,
            0.0 AS duplicate_penalty,
            score AS final_score,
            0 AS suppressed,
            0 AS hard_same_family,
            '' AS hard_same_family_reason,
            '' AS pair_key,
            '' AS override_type,
            '' AS override_value,
            0 AS contrastive_protection,
            '' AS contrastive_reason,
            0.0 AS embedding_similarity,
            0.0 AS lexical_overlap,
            0.0 AS containment_ratio,
            0.0 AS alias_overlap,
            0.0 AS neighbor_overlap,
            0.0 AS context_overlap,
            0.0 AS bucket_similarity,
            0 AS lexical_contradiction,
            NULL AS final_rank
        FROM candidates_raw
        """
    )
    conn.execute("CREATE UNIQUE INDEX idx_candidates_scored_candidate_rowid ON candidates_scored(candidate_rowid)")
    conn.execute("CREATE INDEX idx_candidates_scored_u ON candidates_scored(u)")
    conn.execute("CREATE INDEX idx_candidates_scored_v ON candidates_scored(v)")
    conn.execute("CREATE INDEX idx_candidates_scored_score ON candidates_scored(score DESC)")
    conn.execute("CREATE INDEX idx_candidates_scored_base_rank ON candidates_scored(base_rank)")
    conn.execute("CREATE INDEX idx_candidates_scored_suppressed ON candidates_scored(suppressed)")
    conn.execute("CREATE INDEX idx_candidates_scored_pair_key ON candidates_scored(pair_key)")
    conn.execute("CREATE INDEX idx_candidates_scored_final_score ON candidates_scored(final_score DESC)")
    conn.commit()
    return conn


def apply_overrides(
    metrics: dict[str, float | int | str],
    override: dict[str, str] | None,
) -> dict[str, float | int | str]:
    if not override:
        return metrics
    override_type = (override.get("override_type") or "").strip()
    override_value = (override.get("override_value") or "").strip()
    if override_type == "manual_block":
        metrics["hard_same_family"] = 1
        metrics["hard_same_family_reason"] = "manual_block_override"
    elif override_type == "manual_protect":
        metrics["hard_same_family"] = 0
        metrics["hard_same_family_reason"] = ""
        metrics["soft_duplicate_score"] = 0.0
        metrics["duplicate_penalty"] = 0.0
        metrics["contrastive_protection"] = 1
        metrics["contrastive_reason"] = "manual_protect_override"
    elif override_type == "manual_penalty_adjust":
        try:
            penalty = float(override_value)
        except ValueError:
            penalty = float(metrics["duplicate_penalty"])
        penalty = max(0.0, min(1.0, penalty))
        metrics["soft_duplicate_score"] = penalty
        metrics["duplicate_penalty"] = penalty
    metrics["override_type"] = override_type
    metrics["override_value"] = override_value
    return metrics


def compute_updates(
    source_db: Path,
    profiles: dict[str, ConceptProfile],
    reviewed_pairs: dict[tuple[str, str], str],
    overrides: dict[str, dict[str, str]],
    lambda_weight: float,
    batch_size: int,
    target_conn: sqlite3.Connection,
) -> dict[str, int | float]:
    source = sqlite3.connect(source_db)
    source.row_factory = sqlite3.Row
    stats = {
        "candidate_count": 0,
        "suppressed_count": 0,
        "hard_same_family_count": 0,
        "override_count": 0,
    }
    try:
        cursor = source.execute("SELECT rowid, u, v, score, rank FROM candidates ORDER BY rowid")
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            updates = []
            for row in rows:
                rowid = int(row["rowid"])
                u = str(row["u"])
                v = str(row["v"])
                base_score = float(row["score"] or 0.0)
                left = profiles[u]
                right = profiles[v]
                pkey = pair_key(u, v)
                metrics = soft_duplicate_metrics(left, right, reviewed_pairs)
                override = overrides.get(pkey)
                if override:
                    stats["override_count"] += 1
                metrics = apply_overrides(metrics, override)
                suppressed = int(metrics["hard_same_family"])
                final_score = base_score - lambda_weight * float(metrics["duplicate_penalty"])
                stats["candidate_count"] += 1
                stats["suppressed_count"] += suppressed
                stats["hard_same_family_count"] += int(metrics["hard_same_family"])
                updates.append(
                    (
                        base_score,
                        int(row["rank"] or 0),
                        float(metrics["soft_duplicate_score"]),
                        float(metrics["duplicate_penalty"]),
                        final_score,
                        suppressed,
                        int(metrics["hard_same_family"]),
                        str(metrics["hard_same_family_reason"]),
                        pkey,
                        str(metrics.get("override_type", "")),
                        str(metrics.get("override_value", "")),
                        int(metrics["contrastive_protection"]),
                        str(metrics["contrastive_reason"]),
                        float(metrics["embedding_similarity"]),
                        float(metrics["lexical_overlap"]),
                        float(metrics["containment_ratio"]),
                        float(metrics["alias_overlap"]),
                        float(metrics["neighbor_overlap"]),
                        float(metrics["context_overlap"]),
                        float(metrics["bucket_similarity"]),
                        int(metrics["lexical_contradiction"]),
                        rowid,
                    )
                )
            target_conn.executemany(
                """
                UPDATE candidates_scored
                SET base_score = ?,
                    base_rank = ?,
                    soft_duplicate_score = ?,
                    duplicate_penalty = ?,
                    final_score = ?,
                    suppressed = ?,
                    hard_same_family = ?,
                    hard_same_family_reason = ?,
                    pair_key = ?,
                    override_type = ?,
                    override_value = ?,
                    contrastive_protection = ?,
                    contrastive_reason = ?,
                    embedding_similarity = ?,
                    lexical_overlap = ?,
                    containment_ratio = ?,
                    alias_overlap = ?,
                    neighbor_overlap = ?,
                    context_overlap = ?,
                    bucket_similarity = ?,
                    lexical_contradiction = ?
                WHERE candidate_rowid = ?
                """,
                updates,
            )
            target_conn.commit()
    finally:
        source.close()
    return stats


def finalize_target_db(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE candidates_scored SET score = final_score")
    conn.execute("DROP TABLE IF EXISTS final_ranks")
    conn.execute(
        """
        CREATE TEMP TABLE final_ranks AS
        SELECT
            candidate_rowid,
            ROW_NUMBER() OVER (ORDER BY final_score DESC, base_score DESC, u, v) AS final_rank
        FROM candidates_scored
        WHERE suppressed = 0
        """
    )
    conn.execute(
        """
        UPDATE candidates_scored
        SET final_rank = (
            SELECT fr.final_rank
            FROM final_ranks fr
            WHERE fr.candidate_rowid = candidates_scored.candidate_rowid
        )
        """
    )
    conn.execute("UPDATE candidates_scored SET rank = final_rank WHERE suppressed = 0")
    conn.execute("UPDATE candidates_scored SET rank = NULL WHERE suppressed = 1")
    conn.execute("DROP TABLE IF EXISTS candidate_duplicate_analysis")
    conn.execute(
        """
        CREATE TABLE candidate_duplicate_analysis AS
        SELECT
            candidate_rowid,
            pair_key,
            u,
            v,
            u_preferred_label,
            v_preferred_label,
            base_score,
            base_rank,
            soft_duplicate_score,
            duplicate_penalty,
            final_score,
            final_rank,
            suppressed,
            hard_same_family,
            hard_same_family_reason,
            override_type,
            override_value,
            contrastive_protection,
            contrastive_reason,
            embedding_similarity,
            lexical_overlap,
            containment_ratio,
            alias_overlap,
            neighbor_overlap,
            context_overlap,
            bucket_similarity,
            lexical_contradiction
        FROM candidates_scored
        """
    )
    conn.execute("DROP VIEW IF EXISTS candidates")
    conn.execute("CREATE VIEW candidates AS SELECT * FROM candidates_scored WHERE suppressed = 0")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_scored_final_rank ON candidates_scored(final_rank)")
    conn.commit()


def export_review_outputs(
    target_db: Path,
    output_root: Path,
    centrality: dict[str, float],
    stats: dict[str, int | float],
    lambda_weight: float,
) -> None:
    analysis_dir = output_root / "analysis"
    review_dir = output_root / "review"
    ensure_dir(analysis_dir)
    ensure_dir(review_dir)
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
            SELECT final_rank, u, v, u_preferred_label, v_preferred_label, base_score, final_score,
                   duplicate_penalty, hard_same_family_reason
            FROM candidates_scored
            WHERE suppressed = 0
            ORDER BY final_rank
            LIMIT 100
            """,
            conn,
        )
        removed = pd.read_sql_query(
            """
            SELECT base_rank, u, v, u_preferred_label, v_preferred_label, base_score, hard_same_family_reason
            FROM candidates_scored
            WHERE suppressed = 1
            ORDER BY base_score DESC, base_rank ASC
            LIMIT 250
            """,
            conn,
        )
        downranked = pd.read_sql_query(
            """
            SELECT base_rank, final_rank, (final_rank - base_rank) AS rank_shift, u, v,
                   u_preferred_label, v_preferred_label, base_score, final_score, duplicate_penalty
            FROM candidates_scored
            WHERE suppressed = 0 AND final_rank IS NOT NULL AND base_rank IS NOT NULL
            ORDER BY rank_shift DESC, duplicate_penalty DESC
            LIMIT 250
            """,
            conn,
        )
        central_ids = {key for key, _ in sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:100]}
        central_df = pd.read_sql_query(
            """
            SELECT base_rank, final_rank, u, v, u_preferred_label, v_preferred_label,
                   base_score, final_score, duplicate_penalty, hard_same_family_reason
            FROM candidates_scored
            WHERE (u IN ({placeholders}) OR v IN ({placeholders}))
            ORDER BY duplicate_penalty DESC, base_score DESC
            LIMIT 200
            """.format(placeholders=",".join("?" for _ in central_ids)),
            conn,
            params=tuple(central_ids) * 2,
        ) if central_ids else pd.DataFrame()
        high_penalty_top500 = pd.read_sql_query(
            """
            SELECT base_rank, final_rank, u, v, u_preferred_label, v_preferred_label,
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
            SELECT base_rank, final_rank, u, v, u_preferred_label, v_preferred_label,
                   base_score, final_score, duplicate_penalty, hard_same_family_reason,
                   alias_overlap, embedding_similarity, lexical_overlap
            FROM candidates_scored
            WHERE suppressed = 0 AND hard_same_family = 0
              AND (
                    alias_overlap >= 0.6
                 OR (duplicate_penalty BETWEEN 0.35 AND 0.55)
              )
            ORDER BY base_score DESC
            LIMIT 200
            """,
            conn,
        )
        top_hard = pd.read_sql_query(
            """
            SELECT 'hard_block_top_loss' AS queue_section, base_rank, final_rank, u, v, u_preferred_label, v_preferred_label,
                   base_score, final_score, duplicate_penalty, hard_same_family_reason, contrastive_reason
            FROM candidates_scored
            WHERE suppressed = 1
            ORDER BY base_score DESC
            LIMIT 100
            """,
            conn,
        )
    finally:
        conn.close()

    before.to_csv(analysis_dir / "top100_before.csv", index=False)
    after.to_csv(analysis_dir / "top100_after.csv", index=False)
    removed.to_csv(analysis_dir / "removed_by_hard_block.csv", index=False)
    downranked.to_csv(analysis_dir / "largest_downranked_pairs.csv", index=False)

    queue = pd.concat(
        [
            top_hard,
            high_penalty_top500.assign(queue_section="high_penalty_top500"),
            central_df.assign(queue_section="high_centrality_pairs") if not central_df.empty else pd.DataFrame(),
            boundary.assign(queue_section="boundary_cases"),
        ],
        ignore_index=True,
    )
    if not queue.empty:
        queue = queue.drop_duplicates(subset=["u", "v"], keep="first")
    queue.to_csv(review_dir / "suppression_review_queue.csv", index=False)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lambda_weight": lambda_weight,
        "candidate_count": int(stats["candidate_count"]),
        "suppressed_count": int(stats["suppressed_count"]),
        "hard_same_family_count": int(stats["hard_same_family_count"]),
        "override_count": int(stats["override_count"]),
        "top100_removed_count": int(sum(1 for _, row in before.iterrows() if not ((after["u"] == row["u"]) & (after["v"] == row["v"])).any())),
        "top100_overlap_count": int(len(set(zip(before["u"], before["v"])) & set(zip(after["u"], after["v"])))),
        "mean_duplicate_penalty_top100_after": float(after["duplicate_penalty"].mean()) if not after.empty else 0.0,
        "mean_duplicate_penalty_top500_before": float(high_penalty_top500["duplicate_penalty"].mean()) if not high_penalty_top500.empty else 0.0,
        "hard_block_reason_counts": removed["hard_same_family_reason"].value_counts().to_dict(),
    }
    with (analysis_dir / "suppression_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    review_lines = [
        "# Baseline exploratory suppression review",
        "",
        f"- Lambda weight: `{lambda_weight:.2f}`",
        f"- Candidate rows analyzed: `{stats['candidate_count']:,}`",
        f"- Hard-suppressed rows: `{stats['suppressed_count']:,}`",
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
            "- Consequential review should start from `suppression_review_queue.csv` rather than a static protection list.",
        ]
    )
    (analysis_dir / "suppression_review.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")


def write_protocol(path: Path) -> None:
    text = """# FrontierGraph duplicate suppression protocol v1

This protocol describes the baseline-exploratory recommendation cleanup layer.

The suppression layer is a post-ontology, pre-ranking adjustment. It does not rebuild the ontology. Instead, it
reduces recommendation waste caused by concept variants that survive ontology construction and occupy top candidate
ranks.

Two actions are taken:

1. Hard same-family suppression
- High-precision rules block clearly same-family pairs entirely.
- These include exact normalized matches, alias-family overlaps, punctuation/singular variants, and strong acronym
  equivalences.

2. Soft duplicate penalty
- All non-blocked pairs receive a duplicate score from a weighted combination of semantic similarity, lexical overlap,
  alias overlap, concept-neighbor overlap, context overlap, and bucket similarity.
- The final candidate score is the original score minus a fixed duplicate penalty weight.

Manual work is not hidden inside the model logic. Instead:
- consequential cases are written to `suppression_review_queue.csv`
- explicit manual actions belong in `suppression_overrides.csv`

Contrastive protections are used only as a seed rule layer for clearly important distinctions such as
spot/futures, product/process, quantity/quality, traded/non-traded, and similar contrastive token families.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    app_db = Path(args.app_db)
    ontology_db = Path(args.ontology_db)
    output_root = Path(args.output_root)
    ensure_dir(output_root)
    analysis_dir = output_root / "analysis"
    review_dir = output_root / "review"
    ensure_dir(analysis_dir)
    ensure_dir(review_dir)

    overrides_path = review_dir / "suppression_overrides.csv"
    overrides = load_overrides(overrides_path)
    reviewed_pairs = load_reviewed_pairs(ontology_db)
    profiles, centrality = load_concept_profiles(app_db, ontology_db)

    target_db = output_root / "concept_exploratory_suppressed_app.sqlite"
    conn = prepare_target_db(app_db, target_db)
    try:
        stats = compute_updates(
            source_db=app_db,
            profiles=profiles,
            reviewed_pairs=reviewed_pairs,
            overrides=overrides,
            lambda_weight=float(args.lambda_weight),
            batch_size=int(args.batch_size),
            target_conn=conn,
        )
        finalize_target_db(conn)
    finally:
        conn.close()

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
