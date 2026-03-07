from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.features_paths import compute_path_features
from src.scoring import compute_candidate_scores
from src.utils import apply_evidence_filters


def test_scoring_formula_and_hub_penalty() -> None:
    pairs_df = pd.DataFrame(
        [
            {"u": "A", "v": "C", "cooc_count": 1, "first_year_seen": 2019, "last_year_seen": 2020, "gap_bonus": 0.5},
            {"u": "B", "v": "D", "cooc_count": 2, "first_year_seen": 2019, "last_year_seen": 2020, "gap_bonus": 0.2},
        ]
    )
    paths_df = pd.DataFrame(
        [
            {"u": "A", "v": "C", "path_support_raw": 2.0, "mediator_count": 1, "hub_penalty": 0.1, "top_mediators_json": "[]", "top_paths_json": "[]"},
            {"u": "B", "v": "D", "path_support_raw": 0.0, "mediator_count": 0, "hub_penalty": 0.0, "top_mediators_json": "[]", "top_paths_json": "[]"},
        ]
    )
    motifs_df = pd.DataFrame(
        [
            {"u": "A", "v": "C", "motif_count": 2, "motif_bonus_raw": 1.0, "top_motif_mediators_json": "[]"},
            {"u": "B", "v": "D", "motif_count": 0, "motif_bonus_raw": 0.0, "top_motif_mediators_json": "[]"},
        ]
    )
    alpha, beta, gamma, delta = 0.5, 0.2, 0.3, 0.2
    out = compute_candidate_scores(pairs_df, paths_df, motifs_df, alpha=alpha, beta=beta, gamma=gamma, delta=delta)
    row = out[(out["u"] == "A") & (out["v"] == "C")].iloc[0]
    expected = alpha * 1.0 + beta * 0.5 + gamma * 1.0 - delta * 1.0
    assert np.isclose(float(row["score"]), expected)
    assert np.isclose(float(row["hub_penalty"]), 1.0)


def test_evidence_filters_change_candidates() -> None:
    corpus = pd.DataFrame(
        [
            {"paper_id": "P1", "year": 2020, "title": "", "authors": "", "venue": "", "source": "", "src_code": "A", "dst_code": "B", "src_label": "A", "dst_label": "B", "relation_type": "pos", "evidence_type": "reg", "is_causal": True, "weight": 1.0, "stability": 0.9},
            {"paper_id": "P2", "year": 2020, "title": "", "authors": "", "venue": "", "source": "", "src_code": "B", "dst_code": "C", "src_label": "B", "dst_label": "C", "relation_type": "pos", "evidence_type": "reg", "is_causal": False, "weight": 1.0, "stability": 0.4},
            {"paper_id": "P3", "year": 2020, "title": "", "authors": "", "venue": "", "source": "", "src_code": "B", "dst_code": "D", "src_label": "B", "dst_label": "D", "relation_type": "pos", "evidence_type": "reg", "is_causal": True, "weight": 1.0, "stability": 0.8},
        ]
    )
    unfiltered = compute_path_features(corpus, max_len=2)
    filtered = compute_path_features(apply_evidence_filters(corpus, causal_only=True), max_len=2)
    unfiltered_pairs = set(zip(unfiltered["u"], unfiltered["v"]))
    filtered_pairs = set(zip(filtered["u"], filtered["v"]))
    assert unfiltered_pairs != filtered_pairs


def test_llm_estimate_and_budget_guardrails(tmp_path: Path) -> None:
    docs_path = tmp_path / "docs.jsonl"
    docs_path.write_text(
        "\n".join(
            [
                json.dumps({"paper_id": "D1", "year": 2024, "title": "T1", "abstract": "A short abstract."}),
                json.dumps({"paper_id": "D2", "year": 2024, "title": "T2", "abstract": "Another abstract."}),
            ]
        ),
        encoding="utf-8",
    )
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "llm:",
                "  model: gpt-5-nano",
                "  max_budget_usd: 0",
                "  key_path: ../key/openai_key_prashant.txt",
                "  pricing_per_million_tokens:",
                "    input_usd: 1.0",
                "    output_usd: 1.0",
                "  output_to_input_token_ratio: 0.5",
            ]
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "llm.parquet"

    estimate_only = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.adapters.llm_extractor_adapter",
            "--in",
            str(docs_path),
            "--out",
            str(out_path),
            "--config",
            str(cfg_path),
            "--estimate_cost",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert estimate_only.returncode == 0
    assert "Execution disabled" in estimate_only.stdout

    over_budget = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.adapters.llm_extractor_adapter",
            "--in",
            str(docs_path),
            "--out",
            str(out_path),
            "--config",
            str(cfg_path),
            "--estimate_cost",
            "--execute",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert over_budget.returncode != 0
    combined = f"{over_budget.stdout}\n{over_budget.stderr}"
    assert "Refusing execution" in combined
