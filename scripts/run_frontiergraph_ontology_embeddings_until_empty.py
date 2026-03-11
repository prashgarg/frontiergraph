from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ontology embeddings repeatedly for shard_index=0 until a selection is exhausted.")
    parser.add_argument("--selection", required=True, choices=["head_pool", "unresolved_ge2", "unresolved_singletons", "all_unresolved"])
    parser.add_argument("--ontology-db", default="data/production/frontiergraph_ontology_v2/ontology_v2.sqlite")
    parser.add_argument("--api-key-path", default="../key/openai_key_prashant.txt")
    parser.add_argument("--model", default="text-embedding-3-large")
    parser.add_argument("--output-root", default="data/production/frontiergraph_ontology_v2/embeddings")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--shard-size", type=int, default=10000)
    parser.add_argument("--max-shards", type=int, default=1000)
    return parser.parse_args()


def latest_manifest(output_root: Path, selection: str) -> Path | None:
    manifests = sorted(output_root.glob(f"*_{selection}_shard*/manifest.json"))
    return manifests[-1] if manifests else None


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for shard_num in range(args.max_shards):
        cmd = [
            "python3",
            "scripts/run_frontiergraph_ontology_embeddings.py",
            "--ontology-db",
            args.ontology_db,
            "--api-key-path",
            args.api_key_path,
            "--model",
            args.model,
            "--output-root",
            args.output_root,
            "--batch-size",
            str(args.batch_size),
            "--shard-size",
            str(args.shard_size),
            "--shard-index",
            "0",
            "--selection",
            args.selection,
        ]
        completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        manifest_path = latest_manifest(output_root, args.selection)
        if manifest_path is None:
            raise RuntimeError(f"No manifest found for selection {args.selection}")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("status") == "empty":
            break
    else:
        raise RuntimeError(f"Reached max_shards={args.max_shards} before selection {args.selection} was exhausted")


if __name__ == "__main__":
    main()
