from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.benchmark_enrichment import map_text_to_code
from src.analysis.common import CandidateBuildConfig, build_candidate_table, check_no_leakage, first_appearance_map
from src.analysis.eval_stats import compute_main_table_with_ci, compute_significance_tests
from src.analysis.vintage_exercise import build_vintage_tables


def _tiny_corpus() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": "P1",
                "year": 2000,
                "title": "t1",
                "authors": "",
                "venue": "",
                "source": "",
                "src_code": "A",
                "dst_code": "B",
                "src_label": "A",
                "dst_label": "B",
                "relation_type": "claim",
                "evidence_type": "reg",
                "is_causal": True,
                "weight": 1.0,
                "stability": 0.8,
            },
            {
                "paper_id": "P2",
                "year": 2000,
                "title": "t2",
                "authors": "",
                "venue": "",
                "source": "",
                "src_code": "B",
                "dst_code": "C",
                "src_label": "B",
                "dst_label": "C",
                "relation_type": "claim",
                "evidence_type": "reg",
                "is_causal": True,
                "weight": 1.0,
                "stability": 0.7,
            },
            {
                "paper_id": "P3",
                "year": 2003,
                "title": "t3",
                "authors": "",
                "venue": "",
                "source": "",
                "src_code": "A",
                "dst_code": "C",
                "src_label": "A",
                "dst_label": "C",
                "relation_type": "claim",
                "evidence_type": "reg",
                "is_causal": True,
                "weight": 1.0,
                "stability": 0.9,
            },
        ]
    )


def test_eval_stats_tables_have_expected_shape() -> None:
    df = pd.DataFrame(
        [
            {"model": "main", "horizon": 1, "cutoff_year_t": 2001, "recall_at_100": 0.1, "mrr": 0.02},
            {"model": "main", "horizon": 1, "cutoff_year_t": 2002, "recall_at_100": 0.2, "mrr": 0.03},
            {"model": "pref_attach", "horizon": 1, "cutoff_year_t": 2001, "recall_at_100": 0.08, "mrr": 0.015},
            {"model": "pref_attach", "horizon": 1, "cutoff_year_t": 2002, "recall_at_100": 0.18, "mrr": 0.025},
        ]
    )
    main_table = compute_main_table_with_ci(df, n_boot=200, seed=7)
    sig = compute_significance_tests(df, n_boot=200, seed=7)
    assert {"model", "horizon", "metric", "mean", "ci_lo", "ci_hi", "n_cutoffs"}.issubset(main_table.columns)
    assert {"metric", "horizon", "model_a", "model_b", "delta", "p_value", "ci_lo", "ci_hi"}.issubset(sig.columns)
    assert (main_table["ci_hi"] >= main_table["ci_lo"]).all()


def test_leakage_and_reproducibility() -> None:
    corpus = _tiny_corpus()
    fmap = first_appearance_map(corpus)
    assert check_no_leakage(corpus, cutoff_t=2001, horizon_h=3, first_year_map=fmap)

    cfg = CandidateBuildConfig()
    train = corpus[corpus["year"] <= 2000]
    a = build_candidate_table(train, cutoff_t=2001, cfg=cfg)
    b = build_candidate_table(train, cutoff_t=2001, cfg=cfg)
    assert not a.empty
    assert a[["u", "v", "score"]].equals(b[["u", "v", "score"]])


def test_vintage_time_to_fill_nonnegative() -> None:
    corpus = _tiny_corpus()
    cfg = CandidateBuildConfig()
    pred, real, _ = build_vintage_tables(corpus, years=[2001], horizon_h=5, k_values=[50], cfg=cfg)
    assert not pred.empty
    realized = real[real["realized_within_h"] == 1]
    assert (realized["time_to_fill"] >= 1).all()


def test_benchmark_mapping_integrity() -> None:
    exact = {"educational attainment": "I21"}
    candidates = [("I21", "educational attainment", {"educational", "attainment"})]
    code, score = map_text_to_code("Educational Attainment", exact, candidates)
    assert code == "I21"
    assert np.isclose(score, 1.0)
    code2, score2 = map_text_to_code("completely unrelated token", exact, candidates)
    assert code2 is None
    assert score2 < 0.5

