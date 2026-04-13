from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_openai import OpenAIEmbeddings

from scripts.force_map_frontiergraph_unresolved_tail import (
    DEFAULT_API_KEY_PATH,
    DEFAULT_MODEL,
    DEFAULT_ONTOLOGY_DB,
    fetch_pending_labels,
    post_json,
    read_api_key,
)
from src.ontology_v2 import build_embedding_text, chunked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark raw OpenAI embedding calls against langchain_openai on unresolved FrontierGraph labels.")
    parser.add_argument("--ontology-db", default=str(DEFAULT_ONTOLOGY_DB))
    parser.add_argument("--api-key-path", default=str(DEFAULT_API_KEY_PATH))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--num-batches", type=int, default=2)
    parser.add_argument("--min-distinct-papers", type=int, default=1)
    parser.add_argument("--provider-order", choices=["raw-first", "langchain-first"], default="raw-first")
    return parser.parse_args()


def load_texts(ontology_db: str, total_labels: int, min_distinct_papers: int) -> list[str]:
    conn = sqlite3.connect(ontology_db)
    conn.row_factory = sqlite3.Row
    try:
        pending = fetch_pending_labels(
            conn=conn,
            limit_labels=total_labels,
            min_distinct_papers=min_distinct_papers,
            exclude_mode="all",
            current_run_id=None,
        )
        labels = [row["normalized_label"] for row in pending]
        if not labels:
            return []
        placeholders = ",".join("?" for _ in labels)
        node_rows = {
            row["normalized_label"]: row
            for row in conn.execute(
                f"SELECT * FROM node_strings WHERE normalized_label IN ({placeholders})",
                labels,
            ).fetchall()
        }
        return [build_embedding_text(dict(node_rows[row["normalized_label"]])) for row in pending]
    finally:
        conn.close()


def benchmark_raw(texts: list[str], model: str, api_key: str, batch_size: int) -> dict[str, object]:
    batch_times: list[float] = []
    total_vectors = 0
    started = time.perf_counter()
    for batch in chunked(texts, batch_size):
        payload = {"model": model, "input": batch}
        batch_started = time.perf_counter()
        response = post_json("https://api.openai.com/v1/embeddings", payload, api_key)
        batch_times.append(time.perf_counter() - batch_started)
        total_vectors += len(response["data"])
    total = time.perf_counter() - started
    return {
        "provider": "raw",
        "total_seconds": total,
        "batch_times_seconds": batch_times,
        "total_vectors": total_vectors,
        "avg_batch_seconds": total / max(1, len(batch_times)),
        "vectors_per_second": total_vectors / total if total > 0 else None,
    }


def benchmark_langchain(texts: list[str], model: str, api_key: str, batch_size: int) -> dict[str, object]:
    embedder = OpenAIEmbeddings(
        model=model,
        api_key=api_key,
        chunk_size=batch_size,
    )
    batch_times: list[float] = []
    total_vectors = 0
    started = time.perf_counter()
    for batch in chunked(texts, batch_size):
        batch_started = time.perf_counter()
        vectors = embedder.embed_documents(batch)
        batch_times.append(time.perf_counter() - batch_started)
        total_vectors += len(vectors)
    total = time.perf_counter() - started
    return {
        "provider": "langchain_openai",
        "total_seconds": total,
        "batch_times_seconds": batch_times,
        "total_vectors": total_vectors,
        "avg_batch_seconds": total / max(1, len(batch_times)),
        "vectors_per_second": total_vectors / total if total > 0 else None,
    }


def main() -> None:
    args = parse_args()
    api_key = read_api_key(args.api_key_path)
    texts = load_texts(
        ontology_db=args.ontology_db,
        total_labels=args.batch_size * args.num_batches,
        min_distinct_papers=args.min_distinct_papers,
    )
    if not texts:
        print(json.dumps({"status": "empty"}))
        return

    results = []
    order = ["raw", "langchain"] if args.provider_order == "raw-first" else ["langchain", "raw"]
    for provider in order:
        if provider == "raw":
            results.append(benchmark_raw(texts, args.model, api_key, args.batch_size))
        else:
            os.environ["OPENAI_API_KEY"] = api_key
            results.append(benchmark_langchain(texts, args.model, api_key, args.batch_size))

    payload = {
        "model": args.model,
        "batch_size": args.batch_size,
        "num_batches": args.num_batches,
        "total_texts": len(texts),
        "provider_order": order,
        "results": results,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
