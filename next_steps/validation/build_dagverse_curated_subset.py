from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_INPUT_JSONL = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark.jsonl"
DEFAULT_OUTPUT_JSONL = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_curated5.jsonl"
DEFAULT_OUTPUT_MANIFEST = "next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_curated5_manifest.json"

CURATED_IDS = [
    "arxiv_2205_01057_0",  # EHR medical covariates
    "arxiv_2208_04144_0",  # urban health observatory variables
    "arxiv_2306_05066_0",  # causal fairness with natural policy nodes
    "arxiv_2002_06746_0",  # individually fair classifier with natural aliases
    "arxiv_2112_05695_0",  # societal event forecasting
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a manually curated DAGverse subset with more natural-language node aliases.")
    parser.add_argument("--input-jsonl", default=DEFAULT_INPUT_JSONL)
    parser.add_argument("--output-jsonl", default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-manifest", default=DEFAULT_OUTPUT_MANIFEST)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def count_semantic(row: dict) -> tuple[int, int]:
    payload = row["gold_semantic_dag"]
    payload = json.loads(payload) if isinstance(payload, str) else payload
    return len(payload.get("nodes", [])), len(payload.get("edges", []))


def main() -> None:
    args = parse_args()
    rows = list(iter_jsonl(Path(args.input_jsonl)))
    row_map = {row["benchmark_id"]: row for row in rows}
    chosen = [row_map[row_id] for row_id in CURATED_IDS]

    out_jsonl = Path(args.output_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for row in chosen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "input_jsonl": str(Path(args.input_jsonl)),
        "output_jsonl": str(out_jsonl),
        "selection_type": "manual_curated_natural_language_subset",
        "benchmark_ids": CURATED_IDS,
        "rationale": [
            "Prefer rows whose semantic DAG aliases are closer to natural-language variables or concepts.",
            "Avoid rows dominated by instantiation labels like A=a1 or generic placeholders like X1, X2 where possible.",
            "Keep a mix of domains while staying closer to the FrontierGraph abstract-level graph object.",
        ],
        "semantic_counts": {
            row["benchmark_id"]: {
                "nodes": count_semantic(row)[0],
                "edges": count_semantic(row)[1],
                "title": row["title"],
            }
            for row in chosen
        },
    }
    Path(args.output_manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
