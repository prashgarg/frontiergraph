from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight runtime contexts
    yaml = None

NODES_REQUIRED_COLUMNS = ["code", "label"]
PAPERS_REQUIRED_COLUMNS = ["paper_id", "year", "title", "authors", "venue", "source"]
EDGES_REQUIRED_COLUMNS = [
    "paper_id",
    "year",
    "src_code",
    "dst_code",
    "relation_type",
    "evidence_type",
    "is_causal",
    "weight",
    "stability",
]
CORPUS_REQUIRED_COLUMNS = [
    "paper_id",
    "year",
    "title",
    "authors",
    "venue",
    "source",
    "src_code",
    "dst_code",
    "src_label",
    "dst_label",
    "relation_type",
    "evidence_type",
    "is_causal",
    "weight",
    "stability",
]


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    if yaml is None:
        raise ModuleNotFoundError("PyYAML is required to load YAML config files.")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_parent_dir(file_path: str | Path) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def write_jsonl(records: Iterable[dict[str, Any]], path: str | Path) -> None:
    ensure_parent_dir(path)
    with Path(path).open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def normalize_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    casted = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "1": True,
                "true": True,
                "t": True,
                "yes": True,
                "y": True,
                "0": False,
                "false": False,
                "f": False,
                "no": False,
                "n": False,
                "none": False,
                "nan": False,
            }
        )
    )
    casted = casted.where(casted.notna(), False)
    return casted.astype(bool)


def validate_columns(df: pd.DataFrame, required: list[str], table_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{table_name} missing required columns: {missing}")


def normalize_nodes_df(nodes_df: pd.DataFrame) -> pd.DataFrame:
    df = nodes_df.copy()
    if "code" not in df.columns:
        raise ValueError("nodes_df must have `code` column")
    if "label" not in df.columns:
        df["label"] = df["code"]
    df = df[["code", "label"]].dropna(subset=["code"]).drop_duplicates(subset=["code"])
    df["code"] = df["code"].astype(str)
    df["label"] = df["label"].fillna(df["code"]).astype(str)
    validate_columns(df, NODES_REQUIRED_COLUMNS, "nodes")
    return df


def normalize_papers_df(papers_df: pd.DataFrame) -> pd.DataFrame:
    df = papers_df.copy()
    required = ["paper_id", "year"]
    validate_columns(df, required, "papers")
    defaults = {
        "title": "",
        "authors": "",
        "venue": "",
        "source": "",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df["paper_id"] = df["paper_id"].astype(str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    for col in ["title", "authors", "venue", "source"]:
        df[col] = df[col].fillna("").astype(str)
    df = df[PAPERS_REQUIRED_COLUMNS].drop_duplicates(subset=["paper_id"])
    validate_columns(df, PAPERS_REQUIRED_COLUMNS, "papers")
    return df


def normalize_edges_df(edges_df: pd.DataFrame) -> pd.DataFrame:
    df = edges_df.copy()
    required = ["paper_id", "src_code", "dst_code"]
    validate_columns(df, required, "edges")
    defaults = {
        "year": 0,
        "relation_type": "unspecified",
        "evidence_type": "unspecified",
        "is_causal": False,
        "weight": 1.0,
        "stability": np.nan,
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df["paper_id"] = df["paper_id"].astype(str)
    df["src_code"] = df["src_code"].astype(str)
    df["dst_code"] = df["dst_code"].astype(str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["relation_type"] = df["relation_type"].fillna("unspecified").astype(str)
    df["evidence_type"] = df["evidence_type"].fillna("unspecified").astype(str)
    df["is_causal"] = normalize_bool(df["is_causal"])
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0).astype(float)
    df["stability"] = pd.to_numeric(df["stability"], errors="coerce")
    df = df[EDGES_REQUIRED_COLUMNS]
    validate_columns(df, EDGES_REQUIRED_COLUMNS, "edges")
    return df


def build_corpus_df(
    nodes_df: pd.DataFrame,
    papers_df: pd.DataFrame,
    edges_df: pd.DataFrame,
) -> pd.DataFrame:
    nodes = normalize_nodes_df(nodes_df)
    papers = normalize_papers_df(papers_df)
    edges = normalize_edges_df(edges_df)

    merged = edges.merge(
        papers,
        how="left",
        on="paper_id",
        suffixes=("", "_paper"),
    )
    if "year_paper" in merged.columns:
        merged["year"] = np.where(merged["year"] > 0, merged["year"], merged["year_paper"])
    code_to_label = dict(zip(nodes["code"], nodes["label"]))
    merged["src_label"] = merged["src_code"].map(code_to_label).fillna(merged["src_code"])
    merged["dst_label"] = merged["dst_code"].map(code_to_label).fillna(merged["dst_code"])
    for col in ["title", "authors", "venue", "source"]:
        if col not in merged.columns:
            merged[col] = ""
        merged[col] = merged[col].fillna("").astype(str)
    merged["year"] = pd.to_numeric(merged["year"], errors="coerce").fillna(0).astype(int)
    merged = merged[CORPUS_REQUIRED_COLUMNS]
    validate_columns(merged, CORPUS_REQUIRED_COLUMNS, "corpus")
    return merged


def load_corpus(corpus_path: str | Path) -> pd.DataFrame:
    df = pd.read_parquet(corpus_path)
    validate_columns(df, CORPUS_REQUIRED_COLUMNS, "corpus")
    return df


def apply_evidence_filters(
    corpus_df: pd.DataFrame,
    causal_only: bool = False,
    min_stability: float | None = None,
) -> pd.DataFrame:
    df = corpus_df.copy()
    if causal_only:
        df = df[df["is_causal"]]
    if min_stability is not None:
        df = df[df["stability"].fillna(-np.inf) >= float(min_stability)]
    return df


def min_max_normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    s_min = float(series.min())
    s_max = float(series.max())
    if np.isclose(s_min, s_max):
        return pd.Series(np.ones(len(series)), index=series.index) if s_max > 0 else pd.Series(
            np.zeros(len(series)),
            index=series.index,
        )
    return (series - s_min) / (s_max - s_min)


def pair_key(u: str, v: str) -> tuple[str, str]:
    return (u, v) if u <= v else (v, u)


def candidate_id(u: str, v: str) -> str:
    return f"{u}->{v}"


def parse_json_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, list) else []
        except json.JSONDecodeError:
            return []
    return []


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)
