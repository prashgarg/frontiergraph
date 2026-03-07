from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.adapters.base import AdapterResult
from src.utils import build_corpus_df, ensure_parent_dir, load_config, read_jsonl


def _safe_code(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", label.strip().upper()).strip("_")
    if not cleaned:
        cleaned = "UNKNOWN"
    return cleaned[:64]


def _estimate_tokens_for_doc(doc: dict[str, Any]) -> int:
    text = " ".join(
        [
            str(doc.get("title", "")),
            str(doc.get("abstract", "")),
            str(doc.get("text", "")),
        ]
    ).strip()
    if not text:
        return 0
    return int(math.ceil(len(text) / 4.0))


def estimate_cost(docs: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    llm_cfg = config.get("llm", {})
    prices = llm_cfg.get("pricing_per_million_tokens", {})
    in_price = float(prices.get("input_usd", 0.0))
    out_price = float(prices.get("output_usd", 0.0))
    ratio = float(llm_cfg.get("output_to_input_token_ratio", 0.25))

    token_per_doc = [_estimate_tokens_for_doc(d) for d in docs]
    total_input = int(sum(token_per_doc))
    total_output = int(math.ceil(total_input * ratio))
    projected = (total_input / 1_000_000.0) * in_price + (total_output / 1_000_000.0) * out_price
    return {
        "docs": len(docs),
        "tokens_per_doc": token_per_doc,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "projected_cost_usd": projected,
    }


def _print_estimate(est: dict[str, Any]) -> None:
    print("Cost estimate (no API call in estimate mode):")
    print(f"- docs: {est['docs']}")
    if est["tokens_per_doc"]:
        preview = est["tokens_per_doc"][:10]
        print(f"- estimated tokens per doc (first 10): {preview}")
    print(f"- total input tokens: {est['total_input_tokens']}")
    print(f"- total output tokens: {est['total_output_tokens']}")
    print(f"- projected cost USD: {est['projected_cost_usd']:.6f}")


def _load_openai_key(key_path: str | Path) -> str:
    path = Path(key_path)
    if not path.exists():
        raise FileNotFoundError(f"OpenAI key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError("OpenAI key file is empty")
    return key


def _extract_edges_with_llm(docs: list[dict[str, Any]], config: dict[str, Any]) -> AdapterResult:
    llm_cfg = config.get("llm", {})
    model = str(llm_cfg.get("model", "gpt-5-nano"))
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        key_path = llm_cfg.get("key_path", os.environ.get("OPENAI_API_KEY_FILE", "../key/openai_api_key.txt"))
        api_key = _load_openai_key(key_path)
    os.environ["OPENAI_API_KEY"] = api_key

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    edge_rows: list[dict[str, Any]] = []
    paper_rows: list[dict[str, Any]] = []
    node_map: dict[str, str] = {}

    schema_hint = (
        "Return JSON object with key `edges` as a list of objects. "
        "Each edge object must include: src_label, dst_label, relation_type, evidence_type, is_causal, weight, stability."
    )
    for i, doc in enumerate(docs, start=1):
        paper_id = str(doc.get("paper_id", doc.get("id", f"DOC_{i}")))
        year = int(doc.get("year", 0) or 0)
        title = str(doc.get("title", ""))
        text = " ".join([title, str(doc.get("abstract", "")), str(doc.get("text", ""))]).strip()
        if not text:
            continue
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract causal or relational claims as compact JSON. "
                        "Use concise concept labels. No prose."
                    ),
                },
                {"role": "user", "content": f"{schema_hint}\n\nDocument:\n{text[:12000]}"},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else "{}"
        try:
            parsed = json.loads(content or "{}")
        except json.JSONDecodeError:
            parsed = {}
        edges = parsed.get("edges", []) if isinstance(parsed, dict) else []
        for e in edges:
            src_label = str(e.get("src_label", "")).strip()
            dst_label = str(e.get("dst_label", "")).strip()
            if not src_label or not dst_label:
                continue
            src_code = _safe_code(src_label)
            dst_code = _safe_code(dst_label)
            node_map[src_code] = src_label
            node_map[dst_code] = dst_label
            edge_rows.append(
                {
                    "paper_id": paper_id,
                    "year": year,
                    "src_code": src_code,
                    "dst_code": dst_code,
                    "relation_type": str(e.get("relation_type", "unspecified")),
                    "evidence_type": str(e.get("evidence_type", "llm")),
                    "is_causal": bool(e.get("is_causal", False)),
                    "weight": float(e.get("weight", 1.0)),
                    "stability": float(e.get("stability")) if e.get("stability") is not None else None,
                }
            )
        paper_rows.append(
            {
                "paper_id": paper_id,
                "year": year,
                "title": title,
                "authors": str(doc.get("authors", "")),
                "venue": str(doc.get("venue", "")),
                "source": "llm_extractor",
            }
        )

    nodes_df = pd.DataFrame({"code": list(node_map.keys()), "label": list(node_map.values())})
    papers_df = pd.DataFrame(paper_rows)
    edges_df = pd.DataFrame(edge_rows)
    return AdapterResult(nodes_df=nodes_df, papers_df=papers_df, edges_df=edges_df).normalized()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optional LLM-based claim graph extractor (OFF by default).")
    parser.add_argument("--in", required=True, dest="in_path", help="Input docs JSONL")
    parser.add_argument("--out", required=True, dest="out_path", help="Output normalized corpus parquet")
    parser.add_argument("--config", default="config/config.yaml", dest="config_path")
    parser.add_argument("--estimate_cost", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config_path)
    docs = read_jsonl(args.in_path)
    est = estimate_cost(docs, config)
    _print_estimate(est)

    # Always require explicit execute flag for spend.
    if not args.execute:
        print("Execution disabled: pass --execute to allow OpenAI API calls.")
        return

    max_budget = float(config.get("llm", {}).get("max_budget_usd", 20))
    if est["projected_cost_usd"] > max_budget:
        raise SystemExit(
            f"Refusing execution: projected cost {est['projected_cost_usd']:.6f} exceeds budget {max_budget:.2f}."
        )

    result = _extract_edges_with_llm(docs, config)
    corpus_df = build_corpus_df(result.nodes_df, result.papers_df, result.edges_df)
    out_path = Path(args.out_path)
    ensure_parent_dir(out_path)
    corpus_df.to_parquet(out_path, index=False)
    print(f"Wrote LLM-derived corpus: {out_path} ({len(corpus_df)} rows)")


if __name__ == "__main__":
    main()
