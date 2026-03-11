from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ontology_v2 import build_embedding_text, chunked


DEFAULT_ONTOLOGY_DB = "data/production/frontiergraph_ontology_v2/ontology_v2.sqlite"
DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"
DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_ontology_v2/embeddings"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed FrontierGraph ontology strings into the reviewed ontology workspace.")
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--shard-size", type=int, default=10000)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--selection", choices=["head_pool", "unresolved_ge2", "unresolved_singletons", "all_unresolved"], default="unresolved_ge2")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def read_api_key(path: str) -> str:
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


def ensure_columns(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE string_embeddings ADD COLUMN shard_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE string_embeddings ADD COLUMN run_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def selection_sql(selection: str) -> str:
    if selection == "head_pool":
        return """
        SELECT ns.*
        FROM node_strings ns
        WHERE ns.in_head_pool = 1
        """
    if selection == "unresolved_ge2":
        return """
        SELECT ns.*
        FROM node_strings ns
        WHERE ns.distinct_papers >= 2
          AND EXISTS (
            SELECT 1
            FROM instance_mappings im
            WHERE im.normalized_label = ns.normalized_label
              AND im.concept_id IS NULL
          )
        """
    if selection == "unresolved_singletons":
        return """
        SELECT ns.*
        FROM node_strings ns
        WHERE ns.distinct_papers = 1
          AND EXISTS (
            SELECT 1
            FROM instance_mappings im
            WHERE im.normalized_label = ns.normalized_label
              AND im.concept_id IS NULL
          )
        """
    return """
    SELECT ns.*
    FROM node_strings ns
    WHERE EXISTS (
        SELECT 1
        FROM instance_mappings im
        WHERE im.normalized_label = ns.normalized_label
          AND im.concept_id IS NULL
    )
    """


def fetch_target_rows(
    conn: sqlite3.Connection,
    model: str,
    selection: str,
    shard_size: int,
    shard_index: int,
    limit: int | None,
) -> tuple[list[sqlite3.Row], dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    base_sql = selection_sql(selection)
    rows = conn.execute(
        f"""
        SELECT *
        FROM ({base_sql}) ns
        WHERE ns.normalized_label NOT IN (
            SELECT normalized_label
            FROM string_embeddings
            WHERE embedding_model = ?
        )
        ORDER BY ns.instance_count DESC, ns.distinct_papers DESC, ns.normalized_label
        """,
        (model,),
    ).fetchall()
    total_targets = len(rows)
    if limit is not None:
        rows = rows[:limit]
    if shard_size > 0:
        start = shard_index * shard_size
        end = start + shard_size
        rows = rows[start:end]
    shard_meta = {
        "selection": selection,
        "total_targets_before_sharding": total_targets,
        "selected_targets": len(rows),
        "shard_size": shard_size,
        "shard_index": shard_index,
        "limit": limit,
    }
    return rows, shard_meta


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shard_id = f"{args.selection}_shard{args.shard_index:04d}"
    output_root = Path(args.output_root)
    shard_root = output_root / f"{run_id}_{shard_id}"
    shard_root.mkdir(parents=True, exist_ok=True)
    manifest_path = shard_root / "manifest.json"

    conn = sqlite3.connect(args.ontology_db)
    ensure_columns(conn)
    rows, shard_meta = fetch_target_rows(
        conn=conn,
        model=args.model,
        selection=args.selection,
        shard_size=args.shard_size,
        shard_index=args.shard_index,
        limit=args.limit,
    )
    if not rows:
        manifest = {
            "run_id": run_id,
            "shard_id": shard_id,
            "status": "empty",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ontology_db": args.ontology_db,
            "model": args.model,
            **shard_meta,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False))
        conn.close()
        return

    api_key = read_api_key(args.api_key_path)
    embedded = 0
    inserted = 0
    request_log_path = shard_root / "requests.jsonl"
    request_log = request_log_path.open("a", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()

    for chunk_index, chunk_rows in enumerate(chunked(rows, args.batch_size), start=1):
        texts = [build_embedding_text(dict(row)) for row in chunk_rows]
        payload = {"model": args.model, "input": texts}
        request_log.write(
            json.dumps(
                {
                    "chunk_index": chunk_index,
                    "input_count": len(texts),
                    "first_label": chunk_rows[0]["normalized_label"],
                    "last_label": chunk_rows[-1]["normalized_label"],
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        request_log.flush()
        response = post_json("https://api.openai.com/v1/embeddings", payload, api_key)
        insert_rows = []
        for row, text_used, embedding_obj in zip(chunk_rows, texts, response["data"]):
            insert_rows.append(
                (
                    row["normalized_label"],
                    args.model,
                    len(embedding_obj["embedding"]),
                    text_used,
                    json.dumps(embedding_obj["embedding"], ensure_ascii=False),
                    now,
                    shard_id,
                    run_id,
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO string_embeddings (
                normalized_label, embedding_model, dimensions, text_used, vector_json, embedded_at, shard_id, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        conn.commit()
        inserted += len(insert_rows)
        embedded += len(insert_rows)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "shard_id": shard_id,
                    "embedded": embedded,
                    "remaining": len(rows) - embedded,
                },
                ensure_ascii=False,
            )
        )

    request_log.close()
    manifest = {
        "run_id": run_id,
        "shard_id": shard_id,
        "status": "completed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ontology_db": args.ontology_db,
        "model": args.model,
        "batch_size": args.batch_size,
        "inserted": inserted,
        "request_log": str(request_log_path),
        **shard_meta,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    conn.close()


if __name__ == "__main__":
    main()
