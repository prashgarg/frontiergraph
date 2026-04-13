from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import build_candidate_table, ensure_output_dir, first_appearance_map, restrict_positive_set_for_family
from src.analysis.learned_reranker import _future_set
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking, parse_cutoff_years, parse_horizons
from src.utils import load_config, load_corpus


def _log(message: str) -> None:
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate transparent retrieval budgets and multi-K recall on the frozen graph.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--years", default="2000,2005,2010,2015")
    parser.add_argument("--horizons", default="3,5,10,15,20")
    parser.add_argument("--pool-sizes", default="500,2000,5000,10000", dest="pool_sizes")
    parser.add_argument("--k-values", default="20,50,100,250,500", dest="k_values")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _parse_ints(raw: str) -> list[int]:
    return [int(float(x.strip())) for x in str(raw).split(",") if x.strip()]


def _score_diag(ranked_df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {
        "n_candidates_total": int(len(ranked_df)),
        "score_max": 0.0,
        "score_min": 0.0,
        "score_span_total": 0.0,
        "score_gap_1_10": 0.0,
        "score_gap_10_100": 0.0,
        "score_gap_100_500": 0.0,
        "score_span_top20": 0.0,
        "score_span_top100": 0.0,
        "score_span_top500": 0.0,
        "score_std_top100": 0.0,
    }
    if ranked_df.empty:
        return out
    score = pd.to_numeric(ranked_df["score"], errors="coerce").fillna(0.0).astype(float).reset_index(drop=True)
    out["score_max"] = float(score.iloc[0])
    out["score_min"] = float(score.iloc[-1])
    out["score_span_total"] = float(score.iloc[0] - score.iloc[-1])

    def _at(pos: int) -> float:
        idx = int(pos) - 1
        if idx < 0 or idx >= len(score):
            return float(score.iloc[-1]) if len(score) else 0.0
        return float(score.iloc[idx])

    out["score_gap_1_10"] = float(_at(1) - _at(10))
    out["score_gap_10_100"] = float(_at(10) - _at(100))
    out["score_gap_100_500"] = float(_at(100) - _at(500))
    out["score_span_top20"] = float(_at(1) - _at(min(20, len(score))))
    out["score_span_top100"] = float(_at(1) - _at(min(100, len(score))))
    out["score_span_top500"] = float(_at(1) - _at(min(500, len(score))))
    out["score_std_top100"] = float(score.head(100).std(ddof=0)) if len(score) else 0.0
    return out


def _write_summary_md(summary_df: pd.DataFrame, score_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Retrieval Budget Evaluation",
        "",
        "This note evaluates the transparent retrieval layer across pool sizes and multiple K budgets.",
        "",
    ]
    if summary_df.empty:
        lines.append("No results were produced.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    lines.append("## Mean retrieval summary by horizon and pool")
    lines.append("")
    for row in summary_df.sort_values(["horizon", "pool_size"]).itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}, pool={int(row.pool_size)}, n_cutoffs={int(row.n_cutoffs)}: pool positive rate={float(row.mean_pool_positive_rate):.4f}, "
            f"pool recall ceiling={float(row.mean_pool_recall_ceiling):.4f}, "
            f"R@20={float(row.mean_recall_at_20):.4f}, R@50={float(row.mean_recall_at_50):.4f}, "
            f"R@100={float(row.mean_recall_at_100):.4f}, R@250={float(row.mean_recall_at_250):.4f}, "
            f"R@500={float(row.mean_recall_at_500):.4f}, MRR={float(row.mean_mrr):.5f}"
        )
    if not score_df.empty:
        lines.extend(["", "## Score-plateau diagnostics by cutoff", ""])
        for row in score_df.sort_values("cutoff_year_t").itertuples(index=False):
            lines.append(
                f"- cutoff={int(row.cutoff_year_t)}: n={int(row.n_candidates_total)}, "
                f"gap(1,10)={float(row.score_gap_1_10):.6f}, gap(10,100)={float(row.score_gap_10_100):.6f}, "
                f"gap(100,500)={float(row.score_gap_100_500):.6f}, top100 span={float(row.score_span_top100):.6f}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_checkpoints(out_dir: Path, rows: list[dict], score_rows: list[dict], candidate_rows: list[dict]) -> None:
    if rows:
        pd.DataFrame(rows).to_csv(out_dir / "retrieval_budget_cutoff_eval.partial.csv", index=False)
    if score_rows:
        pd.DataFrame(score_rows).to_csv(out_dir / "retrieval_score_plateau_cutoff.partial.csv", index=False)
    if candidate_rows:
        pd.DataFrame(candidate_rows).to_csv(out_dir / "retrieval_candidate_universe_summary.partial.csv", index=False)


def main() -> None:
    args = parse_args()
    t0 = time.time()
    out_dir = ensure_output_dir(args.out_dir)
    _log(f"[retrieval-budget] start out={out_dir} family={args.candidate_family_mode}")

    corpus_df = load_corpus(args.corpus_path)
    _log(f"[retrieval-budget] loaded corpus rows={len(corpus_df):,}")
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    cfg.candidate_family_mode = str(args.candidate_family_mode)
    cfg.path_to_direct_scope = str(args.path_to_direct_scope)

    horizons = parse_horizons(args.horizons, default=[5, 10, 15])
    years = parse_cutoff_years(
        _parse_ints(args.years),
        min_year=int(corpus_df["year"].min()),
        max_year=int(corpus_df["year"].max()),
        max_h=min(horizons),
        step=5,
    )
    max_year = int(corpus_df["year"].max())
    years = [int(t) for t in years if int(t) <= max_year]
    pool_sizes = sorted(set(int(x) for x in _parse_ints(args.pool_sizes) if int(x) > 0))
    k_values = sorted(set(int(x) for x in _parse_ints(args.k_values) if int(x) > 0))
    _log(
        f"[retrieval-budget] years={years} horizons={horizons} pools={pool_sizes} k_values={k_values}"
    )

    first_year = first_appearance_map(
        corpus_df,
        candidate_kind=str(getattr(cfg, "candidate_kind", "directed_causal")),
        candidate_family_mode=str(getattr(cfg, "candidate_family_mode", "path_to_direct")),
    )
    _log(f"[retrieval-budget] built future-event map in {time.time() - t0:.1f}s")

    rows: list[dict] = []
    score_rows: list[dict] = []
    candidate_rows: list[dict] = []

    for cutoff_t in years:
        cutoff_start = time.time()
        train_df = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
        if train_df.empty:
            continue
        _log(f"[retrieval-budget] cutoff={cutoff_t}: train_rows={len(train_df):,}")
        ranked = build_candidate_table(train_df, cutoff_t=int(cutoff_t), cfg=cfg)
        if ranked.empty:
            _log(f"[retrieval-budget] cutoff={cutoff_t}: no candidates")
            continue
        ranked = ranked.sort_values(["score", "u", "v"], ascending=[False, True, True]).reset_index(drop=True)
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        _log(f"[retrieval-budget] cutoff={cutoff_t}: candidates={len(ranked):,}")
        score_rows.append({"cutoff_year_t": int(cutoff_t), **_score_diag(ranked)})

        for horizon in horizons:
            if int(cutoff_t) + int(horizon) > max_year:
                continue
            positives = _future_set(first_year, cutoff_t=int(cutoff_t), horizon_h=int(horizon))
            positives = restrict_positive_set_for_family(
                positives,
                candidate_pairs_df=ranked,
                candidate_family_mode=str(getattr(cfg, "candidate_family_mode", "path_to_direct")),
            )
            total_future = int(len(positives))
            if total_future <= 0:
                _log(f"[retrieval-budget] cutoff={cutoff_t} h={horizon}: no positives")
                continue
            candidate_rows.append(
                {
                    "cutoff_year_t": int(cutoff_t),
                    "horizon": int(horizon),
                    "n_candidates_total": int(len(ranked)),
                    "n_future_positives_total": int(total_future),
                    "future_positive_rate_total": float(total_future) / float(max(1, len(ranked))),
                }
            )
            _log(f"[retrieval-budget] cutoff={cutoff_t} h={horizon}: positives={total_future:,}")
            for pool_size in pool_sizes:
                pool = ranked.head(int(pool_size)).copy()
                pool_positive_count = int(pd.Series(list(zip(pool["u"].astype(str), pool["v"].astype(str)))).isin(positives).sum())
                metrics = evaluate_binary_ranking(
                    pool[["u", "v", "score", "rank"]].copy(),
                    positives=positives,
                    k_values=[k for k in k_values if int(k) <= int(pool_size)],
                )
                row = {
                    "cutoff_year_t": int(cutoff_t),
                    "horizon": int(horizon),
                    "pool_size": int(pool_size),
                    "n_candidates_total": int(len(ranked)),
                    "n_candidates_pool": int(len(pool)),
                    "n_future_positives_total": int(total_future),
                    "n_future_positives_in_pool": int(pool_positive_count),
                    "pool_positive_rate": float(pool_positive_count) / float(max(1, len(pool))),
                    "pool_recall_ceiling": float(pool_positive_count) / float(max(1, total_future)),
                }
                for k in k_values:
                    row[f"recall_at_{int(k)}"] = float(metrics.get(f"recall_at_{int(k)}", np.nan))
                    row[f"precision_at_{int(k)}"] = float(metrics.get(f"precision_at_{int(k)}", np.nan))
                row["mrr"] = float(metrics.get("mrr", 0.0))
                rows.append(row)
        _write_checkpoints(Path(out_dir), rows, score_rows, candidate_rows)
        _log(f"[retrieval-budget] cutoff={cutoff_t}: done in {time.time() - cutoff_start:.1f}s")

    budget_df = pd.DataFrame(rows)
    score_df = pd.DataFrame(score_rows)
    candidate_df = pd.DataFrame(candidate_rows)
    if budget_df.empty:
        (Path(out_dir) / "retrieval_budget_summary.md").write_text("# Retrieval Budget Evaluation\n\nNo results were produced.\n", encoding="utf-8")
        return

    agg_map: dict[str, tuple[str, str]] = {
        "n_candidates_total": ("n_candidates_total", "mean"),
        "n_future_positives_total": ("n_future_positives_total", "mean"),
        "mean_pool_positive_rate": ("pool_positive_rate", "mean"),
        "mean_pool_recall_ceiling": ("pool_recall_ceiling", "mean"),
        "mean_mrr": ("mrr", "mean"),
        "n_cutoffs": ("cutoff_year_t", "nunique"),
    }
    for k in k_values:
        agg_map[f"mean_recall_at_{int(k)}"] = (f"recall_at_{int(k)}", "mean")
        agg_map[f"mean_precision_at_{int(k)}"] = (f"precision_at_{int(k)}", "mean")
    summary_df = budget_df.groupby(["horizon", "pool_size"], as_index=False).agg(**agg_map).sort_values(["horizon", "pool_size"]).reset_index(drop=True)

    if not score_df.empty:
        score_summary = score_df.agg(
            mean_n_candidates_total=("n_candidates_total", "mean"),
            mean_score_gap_1_10=("score_gap_1_10", "mean"),
            mean_score_gap_10_100=("score_gap_10_100", "mean"),
            mean_score_gap_100_500=("score_gap_100_500", "mean"),
            mean_score_span_top100=("score_span_top100", "mean"),
        )
        if isinstance(score_summary, pd.Series):
            score_summary = score_summary.to_frame().T
        score_summary.to_csv(Path(out_dir) / "retrieval_score_plateau_summary.csv", index=False)

    budget_df.to_csv(Path(out_dir) / "retrieval_budget_cutoff_eval.csv", index=False)
    summary_df.to_csv(Path(out_dir) / "retrieval_budget_summary.csv", index=False)
    score_df.to_csv(Path(out_dir) / "retrieval_score_plateau_cutoff.csv", index=False)
    candidate_df.to_csv(Path(out_dir) / "retrieval_candidate_universe_summary.csv", index=False)
    _write_summary_md(summary_df, score_df, Path(out_dir) / "retrieval_budget_summary.md")

    manifest = {
        "corpus_path": args.corpus_path,
        "config_path": args.config_path,
        "best_config_path": args.best_config_path,
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "years": [int(x) for x in years],
        "horizons": [int(x) for x in horizons],
        "pool_sizes": [int(x) for x in pool_sizes],
        "k_values": [int(x) for x in k_values],
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _log(f"[retrieval-budget] wrote {Path(out_dir) / 'retrieval_budget_summary.csv'}")
    _log(f"[retrieval-budget] total runtime {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
