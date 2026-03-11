from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from src.duplicate_suppression import ConceptProfile, pair_key, soft_duplicate_metrics
from scripts.build_frontiergraph_baseline_suppression import (
    DEFAULT_APP_DB,
    DEFAULT_LAMBDA,
    DEFAULT_ONTOLOGY_DB,
    apply_overrides,
    ensure_dir,
    ensure_override_file,
    load_concept_profiles,
    load_overrides,
    load_reviewed_pairs,
)


DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_concept_compare_v1/baseline/suppression"
DEFAULT_TOP_K = 100_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact baseline exploratory suppression DB for the top-K surfaced candidates.")
    parser.add_argument("--app-db", default=DEFAULT_APP_DB)
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--lambda-weight", type=float, default=DEFAULT_LAMBDA)
    return parser.parse_args()


def target_db_path(output_root: Path, top_k: int) -> Path:
    if top_k % 1000 == 0:
        suffix = f"top{top_k // 1000}k"
    else:
        suffix = f"top{top_k}"
    return output_root / f"concept_exploratory_suppressed_{suffix}_app.sqlite"


def to_rows(conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(sql, params).fetchall()


def fetch_top_candidates(source_db: Path, top_k: int) -> tuple[list[sqlite3.Row], list[str]]:
    conn = sqlite3.connect(source_db)
    try:
        conn.row_factory = sqlite3.Row
        columns = [row[1] for row in conn.execute("PRAGMA table_info(candidates)")]
        rows = conn.execute(
            f"SELECT {', '.join(columns)} FROM candidates ORDER BY rank LIMIT ?",
            (top_k,),
        ).fetchall()
    finally:
        conn.close()
    return rows, columns


def score_rows(
    rows: list[sqlite3.Row],
    profiles: dict[str, ConceptProfile],
    reviewed_pairs: dict[tuple[str, str], str],
    overrides: dict[str, dict[str, str]],
    lambda_weight: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    scored: list[dict[str, object]] = []
    stats = {
        "candidate_count": 0,
        "suppressed_count": 0,
        "hard_same_family_count": 0,
        "override_count": 0,
    }
    for row in rows:
        row_dict = dict(row)
        u = str(row_dict["u"])
        v = str(row_dict["v"])
        left = profiles[u]
        right = profiles[v]
        pkey = pair_key(u, v)
        metrics = soft_duplicate_metrics(left, right, reviewed_pairs)
        override = overrides.get(pkey)
        if override:
            stats["override_count"] += 1
        metrics = apply_overrides(metrics, override)
        base_score = float(row_dict["score"] or 0.0)
        suppressed = int(metrics["hard_same_family"])
        final_score = base_score - lambda_weight * float(metrics["duplicate_penalty"])
        row_dict.update(
            {
                "base_score": base_score,
                "base_rank": int(row_dict["rank"] or 0),
                "soft_duplicate_score": float(metrics["soft_duplicate_score"]),
                "duplicate_penalty": float(metrics["duplicate_penalty"]),
                "final_score": final_score,
                "suppressed": suppressed,
                "hard_same_family": int(metrics["hard_same_family"]),
                "hard_same_family_reason": str(metrics["hard_same_family_reason"]),
                "pair_key": pkey,
                "override_type": str(metrics.get("override_type", "")),
                "override_value": str(metrics.get("override_value", "")),
                "contrastive_protection": int(metrics["contrastive_protection"]),
                "contrastive_reason": str(metrics["contrastive_reason"]),
                "embedding_similarity": float(metrics["embedding_similarity"]),
                "lexical_overlap": float(metrics["lexical_overlap"]),
                "containment_ratio": float(metrics["containment_ratio"]),
                "substring_containment_ratio": float(metrics["substring_containment_ratio"]),
                "shared_token_overlap": float(metrics["shared_token_overlap"]),
                "alias_overlap": float(metrics["alias_overlap"]),
                "neighbor_overlap": float(metrics["neighbor_overlap"]),
                "context_overlap": float(metrics["context_overlap"]),
                "bucket_similarity": float(metrics["bucket_similarity"]),
                "lexical_contradiction": int(metrics["lexical_contradiction"]),
                "final_rank": None,
            }
        )
        scored.append(row_dict)
        stats["candidate_count"] += 1
        stats["suppressed_count"] += suppressed
        stats["hard_same_family_count"] += int(metrics["hard_same_family"])

    visible = [row for row in scored if not row["suppressed"]]
    visible.sort(key=lambda item: (-float(item["final_score"]), -float(item["base_score"]), str(item["u"]), str(item["v"])))
    for idx, row in enumerate(visible, start=1):
        row["final_rank"] = idx
        row["score"] = row["final_score"]
        row["rank"] = idx

    summary = {
        **stats,
        "visible_count": len(visible),
        "top100_removed_count": sum(1 for row in scored if row["suppressed"] and int(row["base_rank"]) <= 100),
        "top100_overlap_count": len({(row["u"], row["v"]) for row in scored if int(row["base_rank"]) <= 100} & {(row["u"], row["v"]) for row in visible[:100]}),
        "mean_duplicate_penalty_top100_after": (
            sum(float(row["duplicate_penalty"]) for row in visible[:100]) / max(min(len(visible), 100), 1)
        ),
        "mean_duplicate_penalty_top500_before": (
            sum(float(row["duplicate_penalty"]) for row in scored if int(row["base_rank"]) <= 500)
            / max(sum(1 for row in scored if int(row["base_rank"]) <= 500), 1)
        ),
    }
    return scored, summary


def build_target_db(
    source_db: Path,
    target_db: Path,
    columns: list[str],
    scored_rows: list[dict[str, object]],
) -> None:
    if target_db.exists():
        target_db.unlink()
    ensure_dir(target_db.parent)
    conn = sqlite3.connect(target_db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"ATTACH DATABASE '{source_db}' AS src")

        # Core support tables are copied wholesale; candidate support tables are filtered to the kept candidate surface.
        for table in [
            "nodes",
            "node_details",
            "concept_edges",
            "concept_edge_profiles",
            "concept_edge_contexts",
            "concept_edge_exemplars",
            "app_meta",
        ]:
            conn.execute(f"CREATE TABLE {table} AS SELECT * FROM src.{table}")

        analysis_columns = columns + [
            "base_score",
            "base_rank",
            "soft_duplicate_score",
            "duplicate_penalty",
            "final_score",
            "suppressed",
            "hard_same_family",
            "hard_same_family_reason",
            "pair_key",
            "override_type",
            "override_value",
            "contrastive_protection",
            "contrastive_reason",
            "embedding_similarity",
            "lexical_overlap",
            "containment_ratio",
            "substring_containment_ratio",
            "shared_token_overlap",
            "alias_overlap",
            "neighbor_overlap",
            "context_overlap",
            "bucket_similarity",
            "lexical_contradiction",
            "final_rank",
        ]
        conn.execute(
            "CREATE TABLE candidate_duplicate_analysis ({cols})".format(
                cols=", ".join(f'"{col}" REAL' if col in {
                    "path_support_raw", "gap_bonus", "motif_bonus_raw", "hub_penalty", "first_year_seen",
                    "last_year_seen", "hub_penalty_raw", "path_support_norm", "motif_bonus_norm", "score",
                    "u_mean_confidence", "u_low_confidence_share", "v_mean_confidence", "v_low_confidence_share",
                    "base_score", "soft_duplicate_score", "duplicate_penalty", "final_score",
                    "embedding_similarity", "lexical_overlap", "containment_ratio", "substring_containment_ratio",
                    "shared_token_overlap", "alias_overlap", "neighbor_overlap", "context_overlap", "bucket_similarity"
                } else f'"{col}" INTEGER' if col in {
                    "mediator_count", "motif_count", "cooc_count", "rank", "u_instance_support",
                    "u_distinct_paper_support", "v_instance_support", "v_distinct_paper_support",
                    "base_rank", "suppressed", "hard_same_family", "contrastive_protection",
                    "lexical_contradiction", "final_rank"
                } else f'"{col}" TEXT' for col in analysis_columns)
            )
        )

        insert_sql = "INSERT INTO candidate_duplicate_analysis ({cols}) VALUES ({vals})".format(
            cols=", ".join(f'"{col}"' for col in analysis_columns),
            vals=", ".join("?" for _ in analysis_columns),
        )
        conn.executemany(insert_sql, [tuple(row.get(col) for col in analysis_columns) for row in scored_rows])

        kept = [row for row in scored_rows if not row["suppressed"]]
        candidate_columns = columns + [
            "base_score",
            "base_rank",
            "soft_duplicate_score",
            "duplicate_penalty",
            "final_score",
            "hard_same_family",
            "hard_same_family_reason",
            "pair_key",
            "override_type",
            "override_value",
            "contrastive_protection",
            "contrastive_reason",
            "embedding_similarity",
            "lexical_overlap",
            "containment_ratio",
            "substring_containment_ratio",
            "shared_token_overlap",
            "alias_overlap",
            "neighbor_overlap",
            "context_overlap",
            "bucket_similarity",
            "lexical_contradiction",
        ]
        conn.execute(
            "CREATE TABLE candidates AS SELECT {cols} FROM candidate_duplicate_analysis WHERE 1=0".format(
                cols=", ".join(f'"{col}"' for col in candidate_columns)
            )
        )
        candidate_insert_sql = "INSERT INTO candidates ({cols}) VALUES ({vals})".format(
            cols=", ".join(f'"{col}"' for col in candidate_columns),
            vals=", ".join("?" for _ in candidate_columns),
        )
        conn.executemany(candidate_insert_sql, [tuple(row.get(col) for col in candidate_columns) for row in kept])

        conn.execute(
            "CREATE TABLE selected_pairs (candidate_u TEXT NOT NULL, candidate_v TEXT NOT NULL, PRIMARY KEY(candidate_u, candidate_v))"
        )
        conn.executemany(
            "INSERT INTO selected_pairs(candidate_u, candidate_v) VALUES (?, ?)",
            [(str(row["u"]), str(row["v"])) for row in kept],
        )

        for table in ["candidate_mediators", "candidate_paths", "candidate_papers", "candidate_neighborhoods"]:
            conn.execute(
                f"""
                CREATE TABLE {table} AS
                SELECT src_tbl.*
                FROM src.{table} src_tbl
                JOIN selected_pairs sp
                  ON src_tbl.candidate_u = sp.candidate_u
                 AND src_tbl.candidate_v = sp.candidate_v
                """
            )

        conn.execute("CREATE INDEX idx_candidates_rank ON candidates(rank)")
        conn.execute("CREATE INDEX idx_candidates_score ON candidates(score DESC)")
        conn.execute("CREATE INDEX idx_candidates_uv ON candidates(u, v)")
        conn.execute("CREATE INDEX idx_candidate_duplicate_analysis_base_rank ON candidate_duplicate_analysis(base_rank)")
        conn.execute("CREATE INDEX idx_candidate_duplicate_analysis_final_rank ON candidate_duplicate_analysis(final_rank)")
        conn.execute("CREATE INDEX idx_candidate_duplicate_analysis_pair_key ON candidate_duplicate_analysis(pair_key)")
        conn.execute("CREATE INDEX idx_candidate_mediators_uv ON candidate_mediators(candidate_u, candidate_v, rank)")
        conn.execute("CREATE INDEX idx_candidate_paths_uv ON candidate_paths(candidate_u, candidate_v, rank)")
        conn.execute("CREATE INDEX idx_candidate_papers_uv ON candidate_papers(candidate_u, candidate_v, path_rank, paper_rank)")
        conn.execute("CREATE INDEX idx_candidate_neighborhoods_uv ON candidate_neighborhoods(candidate_u, candidate_v)")

        existing_meta = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM app_meta")}
        updates = {
            "app_mode": existing_meta.get("app_mode", "concept_exploratory"),
            "suppression_mode": "baseline_exploratory_topk",
            "suppression_top_k": str(len(scored_rows)),
            "suppression_visible_count": str(len(kept)),
            "suppression_built_at": datetime.now(timezone.utc).isoformat(),
        }
        for key, value in updates.items():
            conn.execute("DELETE FROM app_meta WHERE key = ?", (key,))
            conn.execute("INSERT INTO app_meta(key, value) VALUES (?, ?)", (key, value))

        conn.commit()
    finally:
        conn.close()


def export_review_outputs(
    output_root: Path,
    scored_rows: list[dict[str, object]],
    centrality: dict[str, float],
    stats: dict[str, object],
    lambda_weight: float,
) -> None:
    analysis_dir = output_root / "analysis"
    review_dir = output_root / "review"
    ensure_dir(analysis_dir)
    ensure_dir(review_dir)

    before = sorted(scored_rows, key=lambda row: int(row["base_rank"]))[:100]
    after_visible = [row for row in scored_rows if not row["suppressed"]]
    after_visible.sort(key=lambda row: int(row["final_rank"] or 10**12))
    after = after_visible[:100]
    removed = sorted(
        [row for row in scored_rows if row["suppressed"]],
        key=lambda row: (-float(row["base_score"]), int(row["base_rank"])),
    )[:250]
    downranked = sorted(
        [
            {
                **row,
                "rank_shift": int((row["final_rank"] or 10**12)) - int(row["base_rank"]),
            }
            for row in after_visible
        ],
        key=lambda row: (-int(row["rank_shift"]), -float(row["duplicate_penalty"])),
    )[:250]
    central_ids = {key for key, _ in sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:100]}
    review_queue = []
    review_queue.extend(removed[:100])
    review_queue.extend(
        sorted(
            [row for row in after_visible if int(row["base_rank"]) <= 500],
            key=lambda row: (-float(row["duplicate_penalty"]), -float(row["base_score"])),
        )[:150]
    )
    review_queue.extend(
        sorted(
            [row for row in scored_rows if row["u"] in central_ids or row["v"] in central_ids],
            key=lambda row: (-float(row["duplicate_penalty"]), -float(row["base_score"])),
        )[:150]
    )
    deduped_queue: list[dict[str, object]] = []
    seen = set()
    for row in review_queue:
        key = str(row["pair_key"])
        if key in seen:
            continue
        seen.add(key)
        deduped_queue.append(row)

    def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(analysis_dir / "top100_before.csv", before)
    write_csv(analysis_dir / "top100_after.csv", after)
    write_csv(analysis_dir / "removed_by_hard_block.csv", removed)
    write_csv(analysis_dir / "largest_downranked_pairs.csv", downranked)
    write_csv(review_dir / "suppression_review_queue.csv", deduped_queue[:300])

    summary = {
        **stats,
        "lambda_weight": lambda_weight,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top100_after_count": len(after),
        "removed_by_hard_block_count": len(removed),
    }
    (analysis_dir / "suppression_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Baseline exploratory suppression review",
        "",
        f"- Candidate rows scored: `{stats['candidate_count']}`",
        f"- Visible rows after suppression: `{stats['visible_count']}`",
        f"- Hard-suppressed rows: `{stats['suppressed_count']}`",
        f"- Top-100 rows removed by hard block: `{stats['top100_removed_count']}`",
        f"- Top-100 overlap after suppression: `{stats['top100_overlap_count']}`",
        f"- Mean duplicate penalty in top-100 after suppression: `{stats['mean_duplicate_penalty_top100_after']:.4f}`",
        "",
        "The review queue prioritizes: top hard-blocked rows, highest-penalty rows in the surfaced ranking, and rows touching the most central concepts.",
    ]
    (analysis_dir / "suppression_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_db = Path(args.app_db)
    ontology_db = Path(args.ontology_db)
    output_root = Path(args.output_root)
    ensure_dir(output_root)
    review_dir = output_root / "review"
    ensure_dir(review_dir)
    overrides_path = review_dir / "suppression_overrides.csv"

    started = time.time()
    reviewed_pairs = load_reviewed_pairs(ontology_db)
    profiles, centrality = load_concept_profiles(source_db, ontology_db)
    overrides = load_overrides(overrides_path)
    rows, columns = fetch_top_candidates(source_db, args.top_k)
    scored_rows, stats = score_rows(rows, profiles, reviewed_pairs, overrides, args.lambda_weight)
    target_db = target_db_path(output_root, args.top_k)
    build_target_db(source_db, target_db, columns, scored_rows)
    stats["build_seconds"] = round(time.time() - started, 3)
    export_review_outputs(output_root, scored_rows, centrality, stats, args.lambda_weight)


if __name__ == "__main__":
    main()
