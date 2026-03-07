from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.adapters.base import AdapterResult
from src.adapters.causalclaims_adapter import CausalClaimsAdapter
from src.adapters.generic_csv_adapter import GenericCSVAdapter
from src.utils import build_corpus_df, ensure_parent_dir, load_config


def build_corpus(adapter: str, out_path: str | Path, config_path: str | Path, input_path: str | None = None) -> pd.DataFrame:
    config = load_config(config_path)
    paths = config.get("paths", {})
    demo_dir = paths.get("demo_dir", "data/demo")
    external_dir = paths.get("external_dir", "data/external")

    logs: list[str] = []
    if adapter == "demo":
        adapter_obj = GenericCSVAdapter(demo_dir)
    elif adapter == "generic":
        if not input_path:
            raise ValueError("--input is required for --adapter generic")
        adapter_obj = GenericCSVAdapter(input_path)
    elif adapter == "causalclaims":
        adapter_obj = CausalClaimsAdapter(external_dir=external_dir, demo_dir=demo_dir)
    else:
        raise ValueError(f"Unknown adapter: {adapter}")

    result: AdapterResult = adapter_obj.load().normalized()
    logs.extend(getattr(adapter_obj, "logs", []))
    corpus_df = build_corpus_df(result.nodes_df, result.papers_df, result.edges_df)

    out_path = Path(out_path)
    ensure_parent_dir(out_path)
    corpus_df.to_parquet(out_path, index=False)

    nodes_sidecar = out_path.with_name(f"{out_path.stem}_nodes.parquet")
    papers_sidecar = out_path.with_name(f"{out_path.stem}_papers.parquet")
    result.nodes_df.to_parquet(nodes_sidecar, index=False)
    result.papers_df.to_parquet(papers_sidecar, index=False)

    log_path = out_path.with_name("ingest_log.json")
    with log_path.open("w", encoding="utf-8") as f:
        json.dump({"adapter": adapter, "logs": logs}, f, indent=2)

    print(f"Wrote corpus: {out_path} ({len(corpus_df)} rows)")
    print(f"Wrote nodes sidecar: {nodes_sidecar}")
    print(f"Wrote papers sidecar: {papers_sidecar}")
    print(f"Wrote ingest log: {log_path}")
    return corpus_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build normalized corpus from adapter.")
    parser.add_argument("--adapter", required=True, choices=["demo", "generic", "causalclaims"])
    parser.add_argument("--out", required=True, dest="out_path")
    parser.add_argument("--config", default="config/config.yaml", dest="config_path")
    parser.add_argument("--input", default=None, dest="input_path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_corpus(
        adapter=args.adapter,
        out_path=args.out_path,
        config_path=args.config_path,
        input_path=args.input_path,
    )


if __name__ == "__main__":
    main()

