from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
RECITE_PARQUET = DATA_ROOT / "reCITE" / "test.parquet"
DAGVERSE_PARQUET = DATA_ROOT / "dagverse" / "train.parquet"

RECITE_JSONL = DATA_ROOT / "reCITE" / "frontiergraph_abstract_benchmark.jsonl"
RECITE_MANIFEST = DATA_ROOT / "reCITE" / "frontiergraph_abstract_benchmark_manifest.json"
DAGVERSE_JSONL = DATA_ROOT / "dagverse" / "frontiergraph_arxiv_abstract_true_benchmark.jsonl"
DAGVERSE_MANIFEST = DATA_ROOT / "dagverse" / "frontiergraph_arxiv_abstract_true_benchmark_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build external validation benchmark inputs for FrontierGraph.")
    parser.add_argument("--skip-recite", action="store_true")
    parser.add_argument("--skip-dagverse", action="store_true")
    parser.add_argument("--dagverse-limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    return parser.parse_args()


def rough_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_jsonable(v) for v in value]
    if hasattr(value, "tolist"):
        return normalize_jsonable(value.tolist())
    if pd.isna(value):
        return None
    return value


def build_recite() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    df = pd.read_parquet(RECITE_PARQUET)
    rows: list[dict[str, Any]] = []
    token_counts: list[int] = []
    for row in df.to_dict(orient="records"):
        title = str(row["title"]).strip()
        abstract = str(row["abstract"]).strip()
        rendered_tokens = rough_tokens(title + "\n\n" + abstract)
        token_counts.append(rendered_tokens)
        rows.append(
            {
                "openalex_work_id": f"validation://reCITE/{row['id']}",
                "benchmark_dataset": "reCITE",
                "benchmark_id": row["id"],
                "title": title,
                "abstract": abstract,
                "source": row.get("source"),
                "source_url": row.get("url"),
                "domains": normalize_jsonable(row.get("domains")),
                "gold_num_nodes": int(row["num_nodes"]),
                "gold_num_edges": int(row["num_edges"]),
                "publication_date": row.get("publication_date"),
            }
        )
    manifest = {
        "dataset": "reCITE",
        "input_parquet": str(RECITE_PARQUET),
        "output_jsonl": str(RECITE_JSONL),
        "row_count": len(rows),
        "mean_gold_nodes": round(float(df["num_nodes"].mean()), 2),
        "mean_gold_edges": round(float(df["num_edges"].mean()), 2),
        "mean_input_tokens_rough": round(sum(token_counts) / len(token_counts), 2),
        "total_input_tokens_rough": int(sum(token_counts)),
        "notes": [
            "This benchmark uses title + abstract only.",
            "This is the clean first match to the current FrontierGraph extraction prompt.",
        ],
    }
    return rows, manifest


def arxiv_abs_url(pdf_or_abs_url: str) -> str:
    match = re.search(r"arxiv\.org/(?:pdf|abs)/([^/?#]+)", pdf_or_abs_url)
    if not match:
        raise ValueError(f"Could not parse arXiv id from {pdf_or_abs_url}")
    arxiv_id = match.group(1).replace(".pdf", "")
    return f"https://arxiv.org/abs/{arxiv_id}"


def fetch_html(url: str, timeout_seconds: int) -> str:
    try:
        req = urllib.request.Request(
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 FrontierGraph validation benchmark builder",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        result = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout_seconds), url],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout


def extract_meta(name: str, html: str) -> str | None:
    patterns = [
        rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"',
        rf"<meta\s+name='{re.escape(name)}'\s+content='([^']*)'",
        rf'<meta\s+property="{re.escape(name)}"\s+content="([^"]*)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return unescape(match.group(1)).strip()
    return None


def build_dagverse(timeout_seconds: int, limit: int | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    df = pd.read_parquet(DAGVERSE_PARQUET)
    subset = df[(df["source"] == "arxiv") & (df["abstract"] == True)].copy()  # noqa: E712
    subset = subset.sort_values("dag_id")
    if limit is not None:
        subset = subset.head(limit)

    rows: list[dict[str, Any]] = []
    token_counts: list[int] = []
    errors: list[dict[str, Any]] = []

    for row in subset.to_dict(orient="records"):
        abs_url = arxiv_abs_url(str(row["paper_uri"]))
        try:
            html = fetch_html(abs_url, timeout_seconds=timeout_seconds)
            title = extract_meta("citation_title", html)
            abstract = extract_meta("citation_abstract", html)
            if not title or not abstract:
                raise ValueError("Missing citation_title or citation_abstract in arXiv page.")
        except Exception as exc:  # noqa: BLE001
            errors.append({"dag_id": row["dag_id"], "paper_uri": row["paper_uri"], "error": str(exc)})
            continue

        rendered_tokens = rough_tokens(title + "\n\n" + abstract)
        token_counts.append(rendered_tokens)
        rows.append(
            {
                "openalex_work_id": f"validation://dagverse/{row['dag_id']}",
                "benchmark_dataset": "dagverse",
                "benchmark_id": row["dag_id"],
                "title": title,
                "abstract": abstract,
                "source": normalize_jsonable(row["source"]),
                "source_url": abs_url,
                "paper_uri": row["paper_uri"],
                "domain": normalize_jsonable(row.get("domain")),
                "technical": bool(normalize_jsonable(row.get("technical", False))),
                "gold_dag": normalize_jsonable(row["dag"]),
                "gold_semantic_dag": normalize_jsonable(row["semantic_dag"]),
            }
        )

    manifest = {
        "dataset": "dagverse",
        "input_parquet": str(DAGVERSE_PARQUET),
        "output_jsonl": str(DAGVERSE_JSONL),
        "filter": {"source": "arxiv", "abstract": True, "limit": limit},
        "requested_rows": int(len(subset)),
        "materialized_rows": len(rows),
        "errors": errors,
        "mean_input_tokens_rough": round(sum(token_counts) / len(token_counts), 2) if token_counts else None,
        "total_input_tokens_rough": int(sum(token_counts)),
        "notes": [
            "This benchmark uses the ArXiv-backed abstract-level subset only.",
            "It is the cleanest DAGverse slice for the current title + abstract FrontierGraph prompt.",
        ],
    }
    return rows, manifest


def main() -> None:
    args = parse_args()
    if not args.skip_recite:
        recite_rows, recite_manifest = build_recite()
        write_jsonl(RECITE_JSONL, recite_rows)
        write_json(RECITE_MANIFEST, recite_manifest)

    if not args.skip_dagverse:
        dag_rows, dag_manifest = build_dagverse(args.timeout_seconds, args.dagverse_limit)
        write_jsonl(DAGVERSE_JSONL, dag_rows)
        write_json(DAGVERSE_MANIFEST, dag_manifest)


if __name__ == "__main__":
    main()
