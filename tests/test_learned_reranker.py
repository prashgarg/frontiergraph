from __future__ import annotations

import pandas as pd

from src.analysis.common import CandidateBuildConfig
from src.analysis.learned_reranker import (
    build_candidate_feature_panel,
    build_direct_to_path_panel,
    build_path_to_direct_ripeness_panel,
    summarize_ripeness_quantiles,
    walk_forward_reranker_eval,
)


def _tiny_corpus() -> pd.DataFrame:
    rows = [
        ("P1", 2000, "A", "B"),
        ("P2", 2000, "B", "C"),
        ("P3", 2001, "C", "D"),
        ("P4", 2002, "A", "C"),
        ("P5", 2003, "B", "D"),
        ("P6", 2004, "A", "D"),
        ("P7", 2005, "D", "E"),
        ("P8", 2006, "B", "E"),
        ("P9", 2007, "A", "E"),
    ]
    out = []
    for paper_id, year, src, dst in rows:
        out.append(
            {
                "paper_id": paper_id,
                "year": int(year),
                "title": paper_id,
                "authors": "",
                "venue": "J",
                "source": "tiny",
                "src_code": src,
                "dst_code": dst,
                "src_label": src,
                "dst_label": dst,
                "relation_type": "claim",
                "evidence_type": "reg",
                "is_causal": True,
                "weight": 1.0,
                "stability": 0.9,
            }
        )
    return pd.DataFrame(out)


def _cfg() -> CandidateBuildConfig:
    return CandidateBuildConfig(
        tau=2,
        max_path_len=2,
        max_neighbors_per_mediator=20,
        alpha=0.5,
        beta=0.2,
        gamma=0.3,
        delta=0.2,
        candidate_kind="directed_causal",
    )


def test_candidate_feature_panel_builds_expected_columns() -> None:
    panel = build_candidate_feature_panel(
        corpus_df=_tiny_corpus(),
        cfg=_cfg(),
        cutoff_years=[2002, 2003, 2004, 2005],
        horizons=[1],
        pool_sizes=[10, 20],
    )
    assert not panel.empty
    expected = {
        "u",
        "v",
        "cutoff_year_t",
        "horizon",
        "appears_within_h",
        "transparent_score",
        "transparent_rank",
        "path_support_norm",
        "mediator_count",
        "source_direct_out_degree",
        "target_direct_in_degree",
        "in_pool_10",
        "in_pool_20",
        "pair_id",
    }
    assert expected.issubset(panel.columns)


def test_walk_forward_reranker_eval_runs_on_tiny_panel() -> None:
    corpus = _tiny_corpus()
    panel = build_candidate_feature_panel(
        corpus_df=corpus,
        cfg=_cfg(),
        cutoff_years=[2002, 2003, 2004, 2005, 2006],
        horizons=[1],
        pool_sizes=[20],
    )
    cutoff_df, summary_df = walk_forward_reranker_eval(
        panel_df=panel,
        corpus_df=corpus,
        feature_family_names=["base", "structural"],
        model_kinds=["glm_logit", "pairwise_logit"],
        pool_sizes=[20],
        alpha=0.05,
        pairwise_negatives_per_positive=1,
        pairwise_max_pairs_per_cutoff=50,
        seed=7,
    )
    assert not cutoff_df.empty
    assert not summary_df.empty
    assert {"model_kind", "feature_family", "pool_size", "horizon", "mrr", "recall_at_100"}.issubset(cutoff_df.columns)
    assert {"mean_mrr", "mean_recall_at_100", "mean_delta_recall_at_100_vs_transparent"}.issubset(summary_df.columns)


def test_ripeness_panels_build() -> None:
    corpus = _tiny_corpus()
    panel = build_candidate_feature_panel(
        corpus_df=corpus,
        cfg=_cfg(),
        cutoff_years=[2002, 2003, 2004, 2005, 2006],
        horizons=[1, 3],
        pool_sizes=[20],
    )
    path_panel = build_path_to_direct_ripeness_panel(panel, horizons=[1, 3])
    assert not path_panel.empty
    assert {"ripeness_score_simple", "direct_closure_h1", "direct_closure_h3"}.issubset(path_panel.columns)
    path_q = summarize_ripeness_quantiles(path_panel, score_col="ripeness_score_simple", outcome_cols=["direct_closure_h1", "direct_closure_h3"])
    assert not path_q.empty

    direct_path_panel = build_direct_to_path_panel(corpus, cutoff_years=[2002, 2003, 2004, 2005, 2006], horizons=[1, 3])
    assert not direct_path_panel.empty
    assert {"ripeness_score_simple", "path_thickens_h1", "path_thickens_h3"}.issubset(direct_path_panel.columns)
