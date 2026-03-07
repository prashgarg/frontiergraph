from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.adapters.base import AdapterResult


class GenericCSVAdapter:
    """
    Generic adapter for user-provided claim graphs.

    Supported inputs:
    - directory containing nodes.csv/papers.csv/edges.csv (preferred)
    - single CSV/JSONL edges file with required columns
    """

    def __init__(self, input_path: str | Path):
        self.input_path = Path(input_path)

    def load(self) -> AdapterResult:
        if self.input_path.is_dir():
            return self._load_from_directory(self.input_path)
        if self.input_path.is_file():
            return self._load_from_single_file(self.input_path)
        raise FileNotFoundError(f"Input path not found: {self.input_path}")

    def _load_from_directory(self, directory: Path) -> AdapterResult:
        nodes_path = directory / "nodes.csv"
        papers_path = directory / "papers.csv"
        edges_path = directory / "edges.csv"
        if not edges_path.exists():
            raise FileNotFoundError(f"Expected edges.csv in directory: {directory}")

        edges_df = pd.read_csv(edges_path)
        papers_df = pd.read_csv(papers_path) if papers_path.exists() else self._derive_papers(edges_df)
        nodes_df = pd.read_csv(nodes_path) if nodes_path.exists() else self._derive_nodes(edges_df)
        return AdapterResult(nodes_df=nodes_df, papers_df=papers_df, edges_df=edges_df)

    def _load_from_single_file(self, path: Path) -> AdapterResult:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            edges_df = pd.read_csv(path)
        elif suffix == ".jsonl":
            edges_df = pd.read_json(path, lines=True)
        else:
            raise ValueError(f"Unsupported file extension: {suffix}. Use .csv or .jsonl")
        papers_df = self._derive_papers(edges_df)
        nodes_df = self._derive_nodes(edges_df)
        return AdapterResult(nodes_df=nodes_df, papers_df=papers_df, edges_df=edges_df)

    @staticmethod
    def _derive_papers(edges_df: pd.DataFrame) -> pd.DataFrame:
        if "paper_id" not in edges_df.columns:
            edges_df = edges_df.copy()
            edges_df["paper_id"] = [f"P{i+1}" for i in range(len(edges_df))]
        year = edges_df["year"] if "year" in edges_df.columns else 0
        papers_df = pd.DataFrame(
            {
                "paper_id": edges_df["paper_id"].astype(str),
                "year": pd.to_numeric(year, errors="coerce").fillna(0).astype(int),
                "title": edges_df.get("title", "").fillna("") if isinstance(edges_df.get("title"), pd.Series) else "",
                "authors": edges_df.get("authors", "").fillna("") if isinstance(edges_df.get("authors"), pd.Series) else "",
                "venue": edges_df.get("venue", "").fillna("") if isinstance(edges_df.get("venue"), pd.Series) else "",
                "source": edges_df.get("source", "generic").fillna("generic")
                if isinstance(edges_df.get("source"), pd.Series)
                else "generic",
            }
        )
        return papers_df.drop_duplicates(subset=["paper_id"])

    @staticmethod
    def _derive_nodes(edges_df: pd.DataFrame) -> pd.DataFrame:
        if "src_code" not in edges_df.columns or "dst_code" not in edges_df.columns:
            raise ValueError("Edges must include src_code and dst_code")
        src = pd.DataFrame(
            {
                "code": edges_df["src_code"].astype(str),
                "label": edges_df.get("src_label", edges_df["src_code"]).astype(str),
            }
        )
        dst = pd.DataFrame(
            {
                "code": edges_df["dst_code"].astype(str),
                "label": edges_df.get("dst_label", edges_df["dst_code"]).astype(str),
            }
        )
        return pd.concat([src, dst], ignore_index=True).drop_duplicates(subset=["code"])

