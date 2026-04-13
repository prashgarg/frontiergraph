from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.build_current_reranked_frontier import _coalesce_merge_columns as frontier_coalesce
from scripts.build_surface_layer_backtest import _coalesce_merge_columns as backtest_coalesce


ROOT = Path(__file__).resolve().parents[1]


def test_merge_coalescers_drop_suffix_columns() -> None:
    raw = pd.DataFrame(
        [
            {
                "u": "A",
                "v": "B",
                "endpoint_broadness_pct_x": 0.25,
                "endpoint_broadness_pct_y": 0.30,
                "source_family_x": "macro",
                "source_family_y": "macro",
                "theme_pair_key_x": "macro__finance",
                "theme_pair_key_y": "macro__finance",
            }
        ]
    )
    cols = ["endpoint_broadness_pct", "source_family", "theme_pair_key"]
    for fn in (frontier_coalesce, backtest_coalesce):
        out = fn(raw.copy(), cols)
        assert "endpoint_broadness_pct" in out.columns
        assert "source_family" in out.columns
        assert "theme_pair_key" in out.columns
        assert float(out.loc[0, "endpoint_broadness_pct"]) == 0.30
        assert out.loc[0, "source_family"] == "macro"
        assert out.loc[0, "theme_pair_key"] == "macro__finance"
        assert not any(col.endswith("_x") or col.endswith("_y") for col in out.columns)


def test_active_frontier_artifacts_have_clean_surface_columns() -> None:
    required = {
        "endpoint_broadness_pct",
        "source_family",
        "target_family",
        "semantic_family_key",
        "source_theme",
        "target_theme",
        "theme_pair_key",
        "paper_surface_penalty",
        "surface_rank",
    }
    paths = [
        ROOT / "outputs" / "paper" / "85_current_reranked_frontier_path_to_direct_quality_surface" / "current_reranked_frontier.csv",
        ROOT / "outputs" / "paper" / "93_current_reranked_frontier_path_to_direct_pool2000" / "current_reranked_frontier.csv",
        ROOT / "outputs" / "paper" / "84_surface_layer_backtest_path_to_direct" / "surface_cutoff_eval.csv",
    ]
    for path in paths:
        assert path.exists(), f"expected artifact to exist: {path}"
        cols = pd.read_csv(path, nrows=0).columns.tolist()
        assert not any(col.endswith("_x") or col.endswith("_y") for col in cols), f"unexpected suffix column in {path}"
        if "current_reranked_frontier" in path.name:
            assert required.issubset(cols), f"missing surfaced columns in {path}"

