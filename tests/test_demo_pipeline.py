from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def test_demo_pipeline_end_to_end(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.parquet"
    pairs = tmp_path / "pairs.parquet"
    paths = tmp_path / "paths.parquet"
    motifs = tmp_path / "motifs.parquet"
    candidates = tmp_path / "candidates.parquet"
    backtest = tmp_path / "backtest.parquet"
    figdir = tmp_path / "figures"
    db_path = tmp_path / "app.db"

    _run(
        [
            sys.executable,
            "-m",
            "src.build_corpus",
            "--adapter",
            "demo",
            "--out",
            str(corpus),
            "--config",
            "config/config.yaml",
        ]
    )
    _run([sys.executable, "-m", "src.features_pairs", "--in", str(corpus), "--out", str(pairs), "--tau", "2"])
    _run([sys.executable, "-m", "src.features_paths", "--in", str(corpus), "--out", str(paths), "--max_len", "2"])
    _run([sys.executable, "-m", "src.features_motifs", "--in", str(corpus), "--out", str(motifs)])
    _run(
        [
            sys.executable,
            "-m",
            "src.scoring",
            "--pairs",
            str(pairs),
            "--paths",
            str(paths),
            "--motifs",
            str(motifs),
            "--out",
            str(candidates),
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "src.backtest",
            "--corpus",
            str(corpus),
            "--out",
            str(backtest),
            "--figdir",
            str(figdir),
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "src.store_sqlite",
            "--corpus",
            str(corpus),
            "--candidates",
            str(candidates),
            "--out",
            str(db_path),
        ]
    )

    assert corpus.exists()
    assert pairs.exists()
    assert paths.exists()
    assert motifs.exists()
    assert candidates.exists()
    assert backtest.exists()
    assert db_path.exists()

    candidates_df = pd.read_parquet(candidates)
    assert not candidates_df.empty
    required_cols = {
        "path_support_raw",
        "path_support_norm",
        "gap_bonus",
        "motif_bonus_raw",
        "motif_bonus_norm",
        "hub_penalty",
        "score",
    }
    assert required_cols.issubset(set(candidates_df.columns))

    backtest_df = pd.read_parquet(backtest)
    assert {"model", "horizon", "mrr"}.issubset(set(backtest_df.columns))
    assert len(backtest_df) > 0

    with sqlite3.connect(db_path) as conn:
        node_count = pd.read_sql_query("SELECT COUNT(*) AS n FROM nodes", conn)["n"].iloc[0]
        candidate_count = pd.read_sql_query("SELECT COUNT(*) AS n FROM candidates", conn)["n"].iloc[0]
        assert int(node_count) > 0
        assert int(candidate_count) > 0

