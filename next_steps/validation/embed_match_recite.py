from __future__ import annotations

import argparse
import json
import math
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_RESULTS_JSONL = "data/pilots/frontiergraph_extraction_v2/runs/recite_pilot10_gpt5mini_low_v2/parsed_results.jsonl"
DEFAULT_RECITE_PARQUET = "next_steps/validation/data/reCITE/test.parquet"
DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"
DEFAULT_MODEL = "text-embedding-3-small"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embedding-assisted candidate matching between FrontierGraph outputs and ReCITE gold nodes.")
    parser.add_argument("--results-jsonl", default=DEFAULT_RESULTS_JSONL)
    parser.add_argument("--recite-parquet", default=DEFAULT_RECITE_PARQUET)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--benchmark-id", action="append", type=int, default=[])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def load_api_key(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def embed_texts(*, api_key: str, model: str, texts: list[str], timeout_seconds: int) -> dict[str, list[float]]:
    req = urllib.request.Request(
        url="https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": model, "input": texts}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return {text: item["embedding"] for text, item in zip(texts, payload["data"])}


def safe_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value) if isinstance(value, list) else []


def main() -> None:
    args = parse_args()
    recite = pd.read_parquet(args.recite_parquet).set_index("id")
    results = [json.loads(line) for line in Path(args.results_jsonl).read_text().splitlines() if line.strip()]
    if args.benchmark_id:
        results = [r for r in results if int(str(r["openalex_work_id"]).split("/")[-1]) in set(args.benchmark_id)]

    benchmark_rows: list[dict[str, Any]] = []
    all_labels: list[str] = []
    for row in results:
        benchmark_id = int(str(row["openalex_work_id"]).split("/")[-1])
        gold = [str(x) for x in safe_list(recite.loc[benchmark_id, "nodes"])]
        pred = [str(n["label"]) for n in row["output"].get("nodes", [])]
        benchmark_rows.append(
            {
                "benchmark_id": benchmark_id,
                "title": recite.loc[benchmark_id, "title"],
                "gold_labels": gold,
                "pred_labels": pred,
            }
        )
        all_labels.extend(gold)
        all_labels.extend(pred)

    unique_labels = sorted(set(all_labels))
    api_key = load_api_key(Path(args.api_key_path))
    embeddings = embed_texts(api_key=api_key, model=args.model, texts=unique_labels, timeout_seconds=args.timeout_seconds)

    output_rows: list[dict[str, Any]] = []
    for row in benchmark_rows:
        pred_to_gold = []
        for pred in row["pred_labels"]:
            scored = [
                {"gold_label": gold, "score": round(cosine(embeddings[pred], embeddings[gold]), 4)}
                for gold in row["gold_labels"]
            ]
            scored.sort(key=lambda x: x["score"], reverse=True)
            pred_to_gold.append({"pred_label": pred, "matches": scored[: args.top_k]})

        gold_to_pred = []
        for gold in row["gold_labels"]:
            scored = [
                {"pred_label": pred, "score": round(cosine(embeddings[gold], embeddings[pred]), 4)}
                for pred in row["pred_labels"]
            ]
            scored.sort(key=lambda x: x["score"], reverse=True)
            gold_to_pred.append({"gold_label": gold, "matches": scored[: args.top_k]})

        output_rows.append(
            {
                "benchmark_id": row["benchmark_id"],
                "title": row["title"],
                "embedding_model": args.model,
                "pred_to_gold": pred_to_gold,
                "gold_to_pred": gold_to_pred,
            }
        )

    out_path = Path(args.output) if args.output else Path(args.results_jsonl).parent / "recite_review" / "embedding_matches.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
