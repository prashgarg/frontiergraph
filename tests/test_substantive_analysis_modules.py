from __future__ import annotations

import pandas as pd

from src.analysis.attention_allocation import compute_attention_panel, compute_attention_summary
from src.analysis.expert_validation_pack import build_expert_pack
from src.analysis.external_transfer_design import build_external_dataset_options, transfer_power_calibration
from src.analysis.gap_boundary import classify_novelty, compute_gap_boundary_panel, summarize_gap_boundary
from src.analysis.impact_weighted_eval import compute_impact_panel, summarize_impact_panel
from src.analysis.prospective_challenge import build_locked_predictions, build_retrospective_scoreboard
from src.analysis.ranking_utils import apply_boundary_rerank


def _tiny_cfg() -> dict:
    return {
        "features": {"tau": 2, "max_path_len": 2, "max_neighbors_per_mediator": 20},
        "scoring": {"alpha": 0.5, "beta": 0.2, "gamma": 0.3, "delta": 0.2},
        "filters": {"causal_only": False, "min_stability": None},
    }


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
                "venue": "",
                "source": "tiny",
                "src_code": src,
                "dst_code": dst,
                "src_label": f"Label-{src}",
                "dst_label": f"Label-{dst}",
                "relation_type": "claim",
                "evidence_type": "reg",
                "is_causal": False,
                "weight": 1.0,
                "stability": 1.0,
            }
        )
    return pd.DataFrame(out)


def test_attention_and_impact_panels_have_expected_columns() -> None:
    corpus = _tiny_corpus()
    cfg = _tiny_cfg()
    panel = compute_attention_panel(corpus, cfg=cfg, cutoff_years=[2001, 2002, 2003], horizons=[1], k_values=[2, 3])
    assert not panel.empty
    assert {"model", "horizon", "k", "precision_at_k", "lift_vs_random_precision"}.issubset(panel.columns)
    summary = compute_attention_summary(panel)
    assert not summary.empty
    assert {"mean_precision", "mean_lift_vs_random"}.issubset(summary.columns)

    impact = compute_impact_panel(corpus, cfg=cfg, cutoff_years=[2001, 2002, 2003], horizons=[1], k_values=[2, 3])
    assert not impact.empty
    assert {"weighted_mrr", "weighted_recall_at_2", "ndcg_at_3"}.issubset(impact.columns)
    impact_sum = summarize_impact_panel(impact, k_values=[2, 3])
    assert not impact_sum.empty


def test_gap_boundary_classification_and_summary() -> None:
    assert classify_novelty("A1", "A2", 3) == "gap_internal"
    assert classify_novelty("A1", "B2", 1) == "gap_crossfield"
    assert classify_novelty("A1", "A2", 0) == "boundary_internal"
    assert classify_novelty("A1", "B2", 0) == "boundary_crossfield"

    corpus = _tiny_corpus()
    panel = compute_gap_boundary_panel(corpus, cfg=_tiny_cfg(), cutoff_years=[2002, 2003], horizons=[1], max_k=5)
    assert not panel.empty
    summary, mix = summarize_gap_boundary(panel, k_values=[3, 5])
    assert not summary.empty
    assert not mix.empty
    assert {"novelty_type", "realized_rate"}.issubset(summary.columns)


def test_external_transfer_and_expert_pack() -> None:
    options = build_external_dataset_options()
    assert not options.empty
    assert {"dataset", "edge_proxy", "horizon_suitability"}.issubset(options.columns)

    backtest = pd.DataFrame(
        [
            {"model": "main", "horizon": 3, "cutoff_year_t": 2001, "recall_at_100": 0.1, "mrr": 0.02},
            {"model": "main", "horizon": 3, "cutoff_year_t": 2002, "recall_at_100": 0.12, "mrr": 0.025},
            {"model": "pref_attach", "horizon": 3, "cutoff_year_t": 2001, "recall_at_100": 0.08, "mrr": 0.018},
            {"model": "pref_attach", "horizon": 3, "cutoff_year_t": 2002, "recall_at_100": 0.10, "mrr": 0.020},
        ]
    )
    power = transfer_power_calibration(backtest)
    assert not power.empty
    assert {"required_n_for_80pct_power", "effect_size_d"}.issubset(power.columns)

    corpus = _tiny_corpus()
    candidates = pd.DataFrame(
        [
            {"u": "A", "v": "E", "score": 0.8},
            {"u": "C", "v": "E", "score": 0.7},
            {"u": "A", "v": "D", "score": 0.6},
            {"u": "C", "v": "B", "score": 0.5},
        ]
    )
    blinded, key, sheet = build_expert_pack(corpus, candidates_df=candidates, n_per_arm=2, seed=7)
    assert not blinded.empty
    assert not key.empty
    assert not sheet.empty
    assert {"item_id", "arm", "u", "v"}.issubset(key.columns)


def test_prospective_outputs_nonempty() -> None:
    corpus = _tiny_corpus()
    cfg = _tiny_cfg()
    locked = build_locked_predictions(corpus, cfg=cfg, anchor_year=2004, horizons=[1], k_values=[3])
    assert not locked.empty
    assert {"challenge_id", "horizon_h", "u", "v", "score"}.issubset(locked.columns)

    scoreboard = build_retrospective_scoreboard(corpus, cfg=cfg, horizons=[1], k_values=[3])
    assert not scoreboard.empty
    assert {"delta_recall_at_3", "delta_mrr"}.issubset(scoreboard.columns)


def test_boundary_quota_reranker_enforces_topk_mix() -> None:
    df = pd.DataFrame(
        [
            {"u": "A", "v": "B", "score": 0.9, "cooc_count": 5},   # non-boundary
            {"u": "A", "v": "C", "score": 0.8, "cooc_count": 4},   # non-boundary
            {"u": "A", "v": "D", "score": 0.7, "cooc_count": 3},   # non-boundary
            {"u": "A", "v": "E", "score": 0.6, "cooc_count": 2},   # non-boundary
            {"u": "A", "v": "F", "score": 0.5, "cooc_count": 2},   # non-boundary
            {"u": "A", "v": "G", "score": 0.4, "cooc_count": 1},   # non-boundary
            {"u": "A", "v": "H", "score": 0.3, "cooc_count": 1},   # non-boundary
            {"u": "A1", "v": "B1", "score": 0.2, "cooc_count": 0}, # boundary (cross-field + zero cooc)
            {"u": "A2", "v": "B2", "score": 0.1, "cooc_count": 0}, # boundary
        ]
    )
    reranked = apply_boundary_rerank(df, boundary_bonus=0.0, boundary_quota=0.2, quota_max_rank=10)
    top5 = reranked.head(5)
    boundary_hits = (
        ((top5["u"].astype(str).str[0] != top5["v"].astype(str).str[0]) & (top5["cooc_count"].astype(float) <= 0)).sum()
    )
    assert boundary_hits >= 1
