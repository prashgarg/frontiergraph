from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ontology_v2 import build_embedding_text, chunked


DEFAULT_ONTOLOGY_DB = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "baseline" / "ontology_v3.sqlite"
DEFAULT_API_KEY_PATH = ROOT.parent / "key" / "openai_key_prashant.txt"
DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "research_allocation_v2" / "tail_force_mapping"
MAPPINGS_TABLE = "tail_force_mappings"
BATCH_LOG_TABLE = "tail_force_mapping_batches"
RUNS_TABLE = "tail_force_mapping_runs"
QUALITY_BANDS = (
    ("high", 0.72, 0.030),
    ("medium", 0.64, 0.015),
)


@dataclass(frozen=True)
class HeadVector:
    concept_id: str
    preferred_label: str
    vector: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Force-map unresolved FrontierGraph ontology labels to existing head concepts without storing tail embeddings.")
    parser.add_argument("--ontology-db", default=str(DEFAULT_ONTOLOGY_DB))
    parser.add_argument("--api-key-path", default=str(DEFAULT_API_KEY_PATH))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--embedding-client", choices=["raw", "langchain"], default="raw")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--batch-label-count", type=int, default=5000)
    parser.add_argument("--embed-batch-size", type=int, default=128)
    parser.add_argument("--query-batch-size", type=int, default=128)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--start-batch", type=int, default=0)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--limit-labels", type=int, default=None)
    parser.add_argument("--min-distinct-papers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_api_key(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def build_embedder(embedding_client: str, model: str, api_key: str, chunk_size: int) -> Any:
    if embedding_client == "raw":
        return {
            "kind": "raw",
            "model": model,
            "api_key": api_key,
        }
    if embedding_client == "langchain":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=model,
            api_key=api_key,
            chunk_size=chunk_size,
        )
    raise ValueError(f"Unknown embedding client: {embedding_client}")


def embed_texts(embedder: Any, texts: list[str]) -> list[np.ndarray]:
    if isinstance(embedder, dict) and embedder.get("kind") == "raw":
        payload = {"model": embedder["model"], "input": texts}
        response = post_json("https://api.openai.com/v1/embeddings", payload, embedder["api_key"])
        return [
            parse_vector(json.dumps(item["embedding"], ensure_ascii=False))
            for item in response["data"]
        ]
    vectors = embedder.embed_documents(texts)
    return [np.nan_to_num(np.asarray(vector, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0) for vector in vectors]


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MAPPINGS_TABLE} (
            normalized_label TEXT PRIMARY KEY,
            preferred_label TEXT NOT NULL,
            instance_count INTEGER NOT NULL,
            distinct_papers INTEGER NOT NULL,
            candidate_concept_id TEXT NOT NULL,
            candidate_preferred_label TEXT NOT NULL,
            representative_label_used TEXT NOT NULL,
            cosine_similarity REAL NOT NULL,
            runner_up_concept_id TEXT,
            runner_up_preferred_label TEXT,
            runner_up_similarity REAL,
            margin_to_runner_up REAL,
            quality_band TEXT NOT NULL,
            mapping_source TEXT NOT NULL,
            batch_index INTEGER NOT NULL,
            run_id TEXT NOT NULL,
            mapped_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BATCH_LOG_TABLE} (
            run_id TEXT NOT NULL,
            batch_index INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            first_label TEXT,
            last_label TEXT,
            label_count INTEGER NOT NULL,
            mapped_count INTEGER NOT NULL DEFAULT 0,
            output_manifest_path TEXT,
            PRIMARY KEY (run_id, batch_index)
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RUNS_TABLE} (
            run_id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            ontology_db TEXT NOT NULL,
            batch_label_count INTEGER NOT NULL,
            embed_batch_size INTEGER NOT NULL,
            query_batch_size INTEGER NOT NULL,
            total_labels INTEGER NOT NULL,
            total_batches INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.commit()


def parse_vector(vector_json: str) -> np.ndarray:
    vector = np.asarray(json.loads(vector_json), dtype=np.float32)
    return np.nan_to_num(vector, nan=0.0, posinf=0.0, neginf=0.0)


def normalize_label(value: Any) -> str:
    return str(value or "").strip().lower()


def head_text(node_row: sqlite3.Row | None, preferred_label: str) -> str:
    if node_row is None:
        return f"label: {preferred_label}"
    return build_embedding_text(dict(node_row))


def ensure_head_embeddings(
    conn: sqlite3.Connection,
    embedder: Any,
    model: str,
    embed_batch_size: int,
    run_id: str,
) -> None:
    existing = {
        normalize_label(row[0])
        for row in conn.execute(
            "SELECT normalized_label FROM string_embeddings WHERE embedding_model = ?",
            (model,),
        ).fetchall()
    }
    missing: list[tuple[str, str]] = []
    for concept_id, preferred_label in conn.execute("SELECT concept_id, preferred_label FROM head_concepts").fetchall():
        normalized = normalize_label(preferred_label)
        if normalized not in existing:
            missing.append((concept_id, preferred_label))
    if not missing:
        return

    now = datetime.now(timezone.utc).isoformat()
    for chunk in chunked(missing, embed_batch_size):
        texts = []
        for _cid, label in chunk:
            node_row = conn.execute(
                "SELECT * FROM node_strings WHERE normalized_label = ?",
                (normalize_label(label),),
            ).fetchone()
            texts.append(head_text(node_row, label))
        embeddings = embed_texts(embedder, texts)
        rows = []
        for (concept_id, label), text_used, embedding in zip(chunk, texts, embeddings):
            rows.append(
                (
                    normalize_label(label),
                    model,
                    int(len(embedding)),
                    text_used,
                    json.dumps(embedding.tolist(), ensure_ascii=False),
                    now,
                    f"force_map_heads_{concept_id}",
                    run_id,
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO string_embeddings (
                normalized_label, embedding_model, dimensions, text_used, vector_json, embedded_at, shard_id, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def load_head_vectors(conn: sqlite3.Connection, model: str) -> list[HeadVector]:
    rows = conn.execute("SELECT concept_id, preferred_label, aliases_json FROM head_concepts ORDER BY concept_id").fetchall()
    embedded = {
        normalize_label(label): vector_json
        for label, vector_json in conn.execute(
            "SELECT normalized_label, vector_json FROM string_embeddings WHERE embedding_model = ?",
            (model,),
        ).fetchall()
    }
    vectors: list[HeadVector] = []
    for concept_id, preferred_label, aliases_json in rows:
        candidates = [preferred_label]
        try:
            candidates.extend(json.loads(aliases_json or "[]"))
        except Exception:
            pass
        vector_json = None
        representative_label = preferred_label
        for label in candidates:
            lookup = normalize_label(label)
            if lookup in embedded:
                vector_json = embedded[lookup]
                representative_label = str(label)
                break
        if vector_json is None:
            continue
        vector = parse_vector(vector_json)
        norm = np.linalg.norm(vector)
        if norm == 0.0 or not np.isfinite(norm):
            continue
        normalized_vector = np.nan_to_num(vector / norm, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        vectors.append(
            HeadVector(
                concept_id=str(concept_id),
                preferred_label=str(preferred_label),
                vector=normalized_vector,
            )
        )
    return vectors


def fetch_pending_labels(
    conn: sqlite3.Connection,
    limit_labels: int | None,
    min_distinct_papers: int,
    exclude_mode: str = "none",
    current_run_id: str | None = None,
) -> list[sqlite3.Row]:
    exclusion_sql = ""
    if exclude_mode == "all":
        exclusion_sql = f"AND sp.normalized_label NOT IN (SELECT normalized_label FROM {MAPPINGS_TABLE})"
    elif exclude_mode == "other_runs":
        exclusion_sql = f"AND sp.normalized_label NOT IN (SELECT normalized_label FROM {MAPPINGS_TABLE} WHERE run_id != ?)"
    query = f"""
        SELECT
            sp.normalized_label,
            sp.preferred_label,
            sp.instance_count,
            sp.distinct_papers
        FROM soft_map_pending sp
        WHERE sp.distinct_papers >= ?
          {exclusion_sql}
        ORDER BY sp.distinct_papers DESC, sp.instance_count DESC, sp.normalized_label
    """
    params: list[Any] = [min_distinct_papers]
    if exclude_mode == "other_runs":
        params.append(current_run_id or "")
    rows = conn.execute(query, tuple(params)).fetchall()
    if limit_labels is not None:
        rows = rows[:limit_labels]
    return rows


def existing_run_state(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return conn.execute(
        f"""
        SELECT run_id, model, ontology_db, batch_label_count, embed_batch_size, query_batch_size,
               total_labels, total_batches, started_at, updated_at, status
        FROM {RUNS_TABLE}
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()


def existing_batch_progress(conn: sqlite3.Connection, run_id: str) -> tuple[int, int]:
    row = conn.execute(
        f"""
        SELECT COALESCE(MAX(batch_index), -1), COALESCE(SUM(mapped_count), 0)
        FROM {BATCH_LOG_TABLE}
        WHERE run_id = ? AND status = 'completed'
        """,
        (run_id,),
    ).fetchone()
    max_completed_raw = row[0]
    completed_labels_raw = row[1]
    max_completed = -1 if max_completed_raw is None else int(max_completed_raw)
    completed_labels = 0 if completed_labels_raw is None else int(completed_labels_raw)
    return max_completed + 1, completed_labels


def quality_band(score: float, margin: float | None) -> str:
    margin = float(margin or 0.0)
    for name, min_score, min_margin in QUALITY_BANDS:
        if score >= min_score and margin >= min_margin:
            return name
    return "low"


def top_two_matches(query_vectors: np.ndarray, head_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scores = query_vectors @ head_matrix.T
    if head_matrix.shape[0] < 2:
        top1 = np.argmax(scores, axis=1)
        top2 = top1.copy()
        return np.stack([top1, top2], axis=1), np.take_along_axis(scores, np.stack([top1, top2], axis=1), axis=1)
    top_idx = np.argpartition(scores, -2, axis=1)[:, -2:]
    top_scores = np.take_along_axis(scores, top_idx, axis=1)
    order = np.argsort(top_scores, axis=1)[:, ::-1]
    top_idx = np.take_along_axis(top_idx, order, axis=1)
    top_scores = np.take_along_axis(top_scores, order, axis=1)
    return top_idx, top_scores


def write_progress(
    output_root: Path,
    progress: dict[str, Any],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "progress.json").write_text(
        json.dumps(progress, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    batch_log_path = output_root / "batch_log.jsonl"
    manifest_path = output_root / "run_manifest.json"

    conn = sqlite3.connect(args.ontology_db)
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)

    prior_run = existing_run_state(conn, run_id) if args.resume else None
    if prior_run is not None:
        pending = fetch_pending_labels(
            conn=conn,
            limit_labels=args.limit_labels,
            min_distinct_papers=args.min_distinct_papers,
            exclude_mode="other_runs",
            current_run_id=run_id,
        )
        total_labels = int(prior_run["total_labels"])
        total_batches = int(prior_run["total_batches"])
        started_at = str(prior_run["started_at"])
        resumed_batch_index, prior_completed_labels = existing_batch_progress(conn, run_id)
        start_batch_index = max(args.start_batch, resumed_batch_index)
        conn.execute(
            f"UPDATE {RUNS_TABLE} SET updated_at = ?, status = ? WHERE run_id = ?",
            (datetime.now(timezone.utc).isoformat(), "running", run_id),
        )
        conn.commit()
    else:
        pending = fetch_pending_labels(
            conn=conn,
            limit_labels=args.limit_labels,
            min_distinct_papers=args.min_distinct_papers,
            exclude_mode="all" if args.resume else "none",
            current_run_id=run_id,
        )
        total_labels = len(pending)
        total_batches = math.ceil(total_labels / args.batch_label_count) if total_labels else 0
        started_at = datetime.now(timezone.utc).isoformat()
        start_batch_index = args.start_batch
        prior_completed_labels = 0
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {RUNS_TABLE} (
                run_id, model, ontology_db, batch_label_count, embed_batch_size, query_batch_size,
                total_labels, total_batches, started_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                args.model,
                str(args.ontology_db),
                args.batch_label_count,
                args.embed_batch_size,
                args.query_batch_size,
                total_labels,
                total_batches,
                started_at,
                started_at,
                "dry_run" if args.dry_run else "running",
            ),
        )
        conn.commit()

    manifest = {
        "run_id": run_id,
        "ontology_db": str(args.ontology_db),
        "model": args.model,
        "embedding_client": args.embedding_client,
        "batch_label_count": args.batch_label_count,
        "embed_batch_size": args.embed_batch_size,
        "query_batch_size": args.query_batch_size,
        "min_distinct_papers": args.min_distinct_papers,
        "resume": bool(args.resume),
        "total_labels": total_labels,
        "total_batches": total_batches,
        "started_at": started_at,
        "status": "dry_run" if args.dry_run else "running",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_progress(
        output_root,
        {
            **manifest,
            "completed_batches": start_batch_index,
            "completed_labels": prior_completed_labels,
            "remaining_batches": max(0, total_batches - start_batch_index),
            "remaining_labels": max(0, total_labels - prior_completed_labels),
            "next_batch_index": start_batch_index,
        },
    )

    if args.dry_run or not pending:
        conn.execute(
            f"UPDATE {RUNS_TABLE} SET updated_at = ?, status = ? WHERE run_id = ?",
            (datetime.now(timezone.utc).isoformat(), "completed" if not pending else "dry_run", run_id),
        )
        conn.commit()
        conn.close()
        return

    api_key = read_api_key(args.api_key_path)
    embedder = build_embedder(args.embedding_client, args.model, api_key, args.embed_batch_size)
    ensure_head_embeddings(conn, embedder, args.model, args.embed_batch_size, run_id)
    head_vectors = load_head_vectors(conn, args.model)
    if not head_vectors:
        raise RuntimeError("No head vectors available for force mapping.")
    head_matrix = np.vstack([item.vector for item in head_vectors]).astype(np.float32)
    head_matrix = np.nan_to_num(head_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    completed_batches = 0
    completed_labels = 0
    with batch_log_path.open("a", encoding="utf-8") as batch_log:
        for batch_index, start in enumerate(range(0, total_labels, args.batch_label_count)):
            if batch_index < start_batch_index:
                continue
            if args.max_batches is not None and completed_batches >= args.max_batches:
                break
            batch_rows = pending[start : start + args.batch_label_count]
            if not batch_rows:
                continue
            batch_started = datetime.now(timezone.utc).isoformat()
            first_label = batch_rows[0]["normalized_label"]
            last_label = batch_rows[-1]["normalized_label"]
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {BATCH_LOG_TABLE} (
                    run_id, batch_index, started_at, completed_at, status, first_label, last_label,
                    label_count, mapped_count, output_manifest_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    batch_index,
                    batch_started,
                    None,
                    "running",
                    first_label,
                    last_label,
                    len(batch_rows),
                    0,
                    str(manifest_path),
                ),
            )
            conn.commit()

            results = []
            for embed_chunk in chunked(batch_rows, args.embed_batch_size):
                labels = [row["normalized_label"] for row in embed_chunk]
                placeholders = ",".join("?" for _ in labels)
                node_rows = {
                    row["normalized_label"]: row
                    for row in conn.execute(
                        f"SELECT * FROM node_strings WHERE normalized_label IN ({placeholders})",
                        labels,
                    ).fetchall()
                }
                texts = [build_embedding_text(dict(node_rows[row["normalized_label"]])) for row in embed_chunk]
                query_matrix = np.vstack(
                    embed_texts(embedder, texts)
                ).astype(np.float32)
                query_matrix = np.nan_to_num(query_matrix, nan=0.0, posinf=0.0, neginf=0.0)
                norms = np.linalg.norm(query_matrix, axis=1, keepdims=True)
                norms[~np.isfinite(norms)] = 1.0
                norms[norms == 0.0] = 1.0
                query_matrix = query_matrix / norms
                start_idx = 0
                for query_chunk in chunked(list(range(len(embed_chunk))), args.query_batch_size):
                    query_slice = query_matrix[start_idx : start_idx + len(query_chunk)]
                    top_indices, top_scores = top_two_matches(query_slice, head_matrix)
                    for local_row, idx_pair, score_pair in zip(embed_chunk[start_idx : start_idx + len(query_chunk)], top_indices, top_scores):
                        top1 = head_vectors[int(idx_pair[0])]
                        top2 = head_vectors[int(idx_pair[1])] if len(idx_pair) > 1 else None
                        score1 = float(score_pair[0])
                        score2 = float(score_pair[1]) if len(score_pair) > 1 else None
                        margin = None if score2 is None else float(score1 - score2)
                        results.append(
                            (
                                local_row["normalized_label"],
                                local_row["preferred_label"],
                                int(local_row["instance_count"]),
                                int(local_row["distinct_papers"]),
                                top1.concept_id,
                                top1.preferred_label,
                                top1.preferred_label,
                                score1,
                                None if top2 is None else top2.concept_id,
                                None if top2 is None else top2.preferred_label,
                                score2,
                                margin,
                                quality_band(score1, margin),
                                "force_embedding_backoff",
                                batch_index,
                                run_id,
                                datetime.now(timezone.utc).isoformat(),
                            )
                        )
                    start_idx += len(query_chunk)

            conn.executemany(
                f"""
                INSERT OR REPLACE INTO {MAPPINGS_TABLE} (
                    normalized_label, preferred_label, instance_count, distinct_papers,
                    candidate_concept_id, candidate_preferred_label, representative_label_used,
                    cosine_similarity, runner_up_concept_id, runner_up_preferred_label,
                    runner_up_similarity, margin_to_runner_up, quality_band, mapping_source,
                    batch_index, run_id, mapped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                results,
            )
            batch_completed = datetime.now(timezone.utc).isoformat()
            conn.execute(
                f"""
                UPDATE {BATCH_LOG_TABLE}
                SET completed_at = ?, status = ?, mapped_count = ?
                WHERE run_id = ? AND batch_index = ?
                """,
                (batch_completed, "completed", len(results), run_id, batch_index),
            )
            conn.commit()

            completed_batches += 1
            completed_labels += len(results)
            cumulative_batches = start_batch_index + completed_batches
            cumulative_labels = prior_completed_labels + completed_labels
            progress = {
                **manifest,
                "status": "running",
                "completed_batches": cumulative_batches,
                "completed_labels": cumulative_labels,
                "remaining_batches": max(0, total_batches - (batch_index + 1)),
                "remaining_labels": max(0, total_labels - cumulative_labels),
                "next_batch_index": batch_index + 1,
                "last_completed_batch_index": batch_index,
                "updated_at": batch_completed,
            }
            write_progress(output_root, progress)
            batch_log.write(
                json.dumps(
                    {
                        "run_id": run_id,
                        "batch_index": batch_index,
                        "label_count": len(results),
                        "first_label": first_label,
                        "last_label": last_label,
                        "completed_at": batch_completed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            batch_log.flush()
            print(json.dumps(progress, ensure_ascii=False))

    finished_at = datetime.now(timezone.utc).isoformat()
    cumulative_batches = start_batch_index + completed_batches
    cumulative_labels = prior_completed_labels + completed_labels
    final_status = "completed" if cumulative_batches >= total_batches else "partial"
    conn.execute(
        f"UPDATE {RUNS_TABLE} SET updated_at = ?, status = ? WHERE run_id = ?",
        (finished_at, final_status, run_id),
    )
    conn.commit()
    write_progress(
        output_root,
        {
            **manifest,
            "status": final_status,
            "completed_batches": cumulative_batches,
            "completed_labels": cumulative_labels,
            "remaining_batches": max(0, total_batches - cumulative_batches),
            "remaining_labels": max(0, total_labels - cumulative_labels),
            "next_batch_index": cumulative_batches,
            "updated_at": finished_at,
        },
    )
    conn.close()


if __name__ == "__main__":
    main()
