from __future__ import annotations

import argparse
import collections
import difflib
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build node-alignment judge inputs with lexical candidate suggestions.")
    parser.add_argument("--dataset", choices=["recite"], default="recite")
    parser.add_argument("--benchmark-source", required=True)
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--prompt-family", required=True)
    parser.add_argument("--subset-jsonl", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        return value
    return []


def parse_benchmark_id(openalex_work_id: str) -> str:
    return str(openalex_work_id).rstrip("/").split("/")[-1]


def pred_nodes_from_output(output: dict[str, Any]) -> list[str]:
    return [str(node["label"]) for node in output.get("nodes", []) if str(node.get("label", "")).strip()]


def normalize_label(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(text: str) -> set[str]:
    return {tok for tok in normalize_label(text).split() if tok}


def char_ngrams(text: str, ngram_range: tuple[int, int] = (3, 5)) -> collections.Counter[str]:
    text = f" {normalize_label(text)} "
    counter: collections.Counter[str] = collections.Counter()
    for n in range(ngram_range[0], ngram_range[1] + 1):
        if len(text) < n:
            continue
        for i in range(len(text) - n + 1):
            counter[text[i : i + n]] += 1
    return counter


def cosine_from_counters(a: collections.Counter[str], b: collections.Counter[str]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    dot = sum(a[key] * b[key] for key in keys)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def tfidf_cosine_scores(labels_a: list[str], labels_b: list[str]) -> list[list[float]]:
    counters_a = [char_ngrams(label) for label in labels_a]
    counters_b = [char_ngrams(label) for label in labels_b]
    return [[cosine_from_counters(ca, cb) for cb in counters_b] for ca in counters_a]


def pair_scores(left: str, right: str, tfidf_cosine: float) -> dict[str, float]:
    left_norm = normalize_label(left)
    right_norm = normalize_label(right)
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    token_jaccard = 0.0 if union == 0 else intersection / union
    sequence_ratio = difflib.SequenceMatcher(a=left_norm, b=right_norm).ratio()
    normalized_exact = 1.0 if left_norm and left_norm == right_norm else 0.0
    combined_score = max(normalized_exact, tfidf_cosine, token_jaccard, sequence_ratio * 0.85)
    return {
        "normalized_exact": round(normalized_exact, 3),
        "token_jaccard": round(token_jaccard, 3),
        "sequence_ratio": round(sequence_ratio, 3),
        "tfidf_cosine": round(tfidf_cosine, 3),
        "combined_score": round(combined_score, 3),
    }


def top_candidates(source_labels: list[str], target_labels: list[str], top_k: int) -> list[dict[str, Any]]:
    cosine = tfidf_cosine_scores(source_labels, target_labels)
    out = []
    for i, source in enumerate(source_labels):
        scored = []
        for j, target in enumerate(target_labels):
            scores = pair_scores(source, target, cosine[i][j] if i < len(cosine) and j < len(cosine[i]) else 0.0)
            scored.append(
                {
                    "candidate_node": target,
                    **scores,
                }
            )
        scored.sort(key=lambda row: (row["combined_score"], row["tfidf_cosine"], row["token_jaccard"], row["sequence_ratio"]), reverse=True)
        out.append(
            {
                "source_node": source,
                "candidates": scored[:top_k],
            }
        )
    return out


def load_recite_gold(recite_parquet: Path) -> dict[str, dict[str, Any]]:
    df = pd.read_parquet(recite_parquet)
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        out[str(row["id"])] = {
            "benchmark_id": str(row["id"]),
            "title": str(row["title"]),
            "abstract": str(row.get("abstract", "")),
            "gold_nodes": [str(item) for item in safe_list(row["nodes"]) if str(item).strip()],
        }
    return out


def main() -> None:
    args = parse_args()
    gold = load_recite_gold(Path(args.benchmark_source))
    subset_ids = None
    if args.subset_jsonl:
        subset_ids = {str(row["benchmark_id"]) for row in iter_jsonl(Path(args.subset_jsonl))}

    out_rows = []
    for row in iter_jsonl(Path(args.results_jsonl)):
        benchmark_id = parse_benchmark_id(str(row["openalex_work_id"]))
        if subset_ids is not None and benchmark_id not in subset_ids:
            continue
        gold_row = gold[benchmark_id]
        pred_nodes = pred_nodes_from_output(row["output"])
        gold_nodes = gold_row["gold_nodes"]
        out_rows.append(
            {
                "benchmark_dataset": args.dataset,
                "benchmark_id": benchmark_id,
                "prompt_family": args.prompt_family,
                "condition_id": row["condition_id"],
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "title": gold_row["title"],
                "abstract": gold_row["abstract"],
                "gold_nodes": gold_nodes,
                "pred_nodes": pred_nodes,
                "gold_node_candidates": top_candidates(gold_nodes, pred_nodes, args.top_k),
                "pred_node_candidates": top_candidates(pred_nodes, gold_nodes, args.top_k),
            }
        )

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
