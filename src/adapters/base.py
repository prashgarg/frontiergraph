from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from src.utils import normalize_edges_df, normalize_nodes_df, normalize_papers_df


@dataclass
class AdapterResult:
    nodes_df: pd.DataFrame
    papers_df: pd.DataFrame
    edges_df: pd.DataFrame

    def normalized(self) -> "AdapterResult":
        return AdapterResult(
            nodes_df=normalize_nodes_df(self.nodes_df),
            papers_df=normalize_papers_df(self.papers_df),
            edges_df=normalize_edges_df(self.edges_df),
        )


class ClaimGraphAdapter(Protocol):
    def load(self) -> AdapterResult:
        ...

