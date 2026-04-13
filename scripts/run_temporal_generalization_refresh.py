#!/usr/bin/env python3
"""Refresh temporal generalization on the current effective-corpus benchmark stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.learned_reranker import (
    FEATURE_FAMILIES,
    build_candidate_feature_panel,
    fit_glm_logit_reranker,
    fit_pairwise_logit_reranker,
    score_with_reranker,
)
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
    pref_attach_ranking_from_universe,
)
from src.utils import load_config, load_corpus


METRIC_KS = [50, 100, 500, 1000]
TRAIN_ERA = "train_1990_2005"
HELDOUT_ERA = "heldout_2010_2015"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh temporal generalization on the current effective-corpus stack.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument(
        "--best-config",
        default="outputs/paper/69_v2_2_effective_model_search/best_config.yaml",
        dest="best_config_path",
    )
    parser.add_argument(
        "--paper-meta",
        default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet",
        dest="paper_meta_path",
    )
    parser.add_argument(
        "--panel-path",
        default="outputs/paper/123_effective_benchmark_widened_1990_2015/historical_feature_panel.parquet",
        dest="panel_path",
    )
    parser.add_argument("--years", default="1985,1990,1995,2000,2005,2010,2015")
    parser.add_argument("--train-years", default="1990,1995,2000,2005", dest="train_years")
    parser.add_argument("--holdout-years", default="2010,2015", dest="holdout_years")
    parser.add_argument("--warmup-years", default="1985", dest="warmup_years")
    parser.add_argument("--horizons", default="5,10")
    parser.add_argument("--pool-size", type=int, default=5000, dest="pool_size")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument(
        "--feature-families",
        default="quality,family_aware_composition,family_aware_boundary_gap",
        dest="feature_families",
    )
    parser.add_argument("--model-kinds", default="glm_logit,pairwise_logit", dest="model_kinds")
    parser.add_argument("--alphas", default="0.05,0.10,0.20", dest="alphas")
    parser.add_argument("--pairwise-negatives-per-positive", type=int, default=2)
    parser.add_argument("--pairwise-max-pairs-per-cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument(
        "--paper-figure",
        default="paper/temporal_generalization_refreshed.png",
        dest="paper_figure_path",
    )
    return parser.parse_args()


def _parse_csv_ints(raw: str) -> list[int]:
    return [int(float(x.strip())) for x in str(raw).split(",") if x.strip()]


def _parse_csv_floats(raw: str) -> list[float]:
    return [float(x.strip()) for x in str(raw).split(",") if x.strip()]


def _parse_csv_strs(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def _fit_model(
    train_rows: pd.DataFrame,
    model_kind: str,
    feature_family: str,
    alpha: float,
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
) -> Any | None:
    feature_names = [c for c in FEATURE_FAMILIES[str(feature_family)] if c in train_rows.columns]
    if not feature_names:
        return None
    if str(model_kind) == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if str(model_kind) == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=int(pairwise_negatives_per_positive),
            max_pairs_per_cutoff=int(pairwise_max_pairs_per_cutoff),
            seed=int(seed),
        )
    raise ValueError(f"Unsupported model_kind: {model_kind}")


def _baseline_metrics(
    cutoff_t: int,
    horizon: int,
    eval_rows: pd.DataFrame,
    corpus_df: pd.DataFrame,
    cache: dict[tuple[int, int], dict[str, float]],
) -> dict[str, float]:
    key = (int(cutoff_t), int(horizon))
    if key in cache:
        return cache[key]
    positives = {
        (str(r.u), str(r.v))
        for r in eval_rows.loc[eval_rows["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
    }
    transparent = (
        eval_rows[["u", "v", "transparent_score"]]
        .rename(columns={"transparent_score": "score"})
        .sort_values(["score", "u", "v"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    transparent["rank"] = transparent.index + 1
    train_corpus = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
    pref = pref_attach_ranking_from_universe(
        train_corpus,
        candidate_pairs_df=eval_rows[[c for c in ["u", "v", "candidate_kind"] if c in eval_rows.columns]].copy(),
    )
    transparent_m = evaluate_binary_ranking(transparent, positives=positives, k_values=METRIC_KS)
    pref_m = evaluate_binary_ranking(pref, positives=positives, k_values=METRIC_KS)
    out = {}
    for prefix, metrics in [("transparent", transparent_m), ("pref_attach", pref_m)]:
        for name, value in metrics.items():
            out[f"{prefix}_{name}"] = float(value)
    cache[key] = out
    return out


def _evaluate_cutoff(
    label: str,
    eval_rows: pd.DataFrame,
    cutoff_t: int,
    horizon: int,
    corpus_df: pd.DataFrame,
    baseline_cache: dict[tuple[int, int], dict[str, float]],
) -> dict[str, Any]:
    positives = {
        (str(r.u), str(r.v))
        for r in eval_rows.loc[eval_rows["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
    }
    metrics = evaluate_binary_ranking(eval_rows[["u", "v", "score", "rank"]], positives=positives, k_values=METRIC_KS)
    row = {
        "model": str(label),
        "cutoff_year_t": int(cutoff_t),
        "horizon": int(horizon),
        "n_eval_rows": int(len(eval_rows)),
        "n_eval_pos": int(len(positives)),
    }
    for key, value in metrics.items():
        row[key] = float(value)
    for key, value in _baseline_metrics(int(cutoff_t), int(horizon), eval_rows, corpus_df, baseline_cache).items():
        row[key] = float(value)
    row["delta_p100_vs_pref"] = float(row.get("precision_at_100", 0.0) - row.get("pref_attach_precision_at_100", 0.0))
    row["delta_p100_vs_transparent"] = float(row.get("precision_at_100", 0.0) - row.get("transparent_precision_at_100", 0.0))
    row["delta_r100_vs_pref"] = float(row.get("recall_at_100", 0.0) - row.get("pref_attach_recall_at_100", 0.0))
    row["delta_r100_vs_transparent"] = float(row.get("recall_at_100", 0.0) - row.get("transparent_recall_at_100", 0.0))
    row["delta_mrr_vs_pref"] = float(row.get("mrr", 0.0) - row.get("pref_attach_mrr", 0.0))
    row["delta_mrr_vs_transparent"] = float(row.get("mrr", 0.0) - row.get("transparent_mrr", 0.0))
    return row


def _select_training_configs(
    panel_df: pd.DataFrame,
    corpus_df: pd.DataFrame,
    train_eval_years: list[int],
    train_allowed_years: list[int],
    horizons: list[int],
    feature_families: list[str],
    model_kinds: list[str],
    alphas: list[float],
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    baseline_cache: dict[tuple[int, int], dict[str, float]] = {}
    for horizon in horizons:
        block = panel_df[panel_df["horizon"].astype(int) == int(horizon)].copy()
        if block.empty:
            continue
        for feature_family in feature_families:
            for model_kind in model_kinds:
                for alpha in alphas:
                    for cutoff_t in train_eval_years:
                        eval_rows = block[block["cutoff_year_t"].astype(int) == int(cutoff_t)].copy()
                        train_rows = block[
                            block["cutoff_year_t"].astype(int).isin(train_allowed_years)
                            & (block["cutoff_year_t"].astype(int) < int(cutoff_t))
                        ].copy()
                        if eval_rows.empty or train_rows.empty:
                            continue
                        if train_rows["appears_within_h"].astype(int).sum() <= 0 or train_rows["appears_within_h"].nunique() < 2:
                            continue
                        model = _fit_model(
                            train_rows=train_rows,
                            model_kind=model_kind,
                            feature_family=feature_family,
                            alpha=float(alpha),
                            pairwise_negatives_per_positive=int(pairwise_negatives_per_positive),
                            pairwise_max_pairs_per_cutoff=int(pairwise_max_pairs_per_cutoff),
                            seed=int(seed) + int(cutoff_t) + int(horizon),
                        )
                        if model is None:
                            continue
                        ranked = score_with_reranker(eval_rows, model)
                        row = _evaluate_cutoff(
                            label=f"{model_kind}+{feature_family}",
                            eval_rows=ranked.merge(
                                eval_rows.drop(columns=["score", "rank"], errors="ignore"),
                                on=["u", "v"],
                                how="left",
                            ),
                            cutoff_t=int(cutoff_t),
                            horizon=int(horizon),
                            corpus_df=corpus_df,
                            baseline_cache=baseline_cache,
                        )
                        row["model_kind"] = str(model_kind)
                        row["feature_family"] = str(feature_family)
                        row["alpha"] = float(alpha)
                        rows.append(row)

    cutoff_df = pd.DataFrame(rows)
    if cutoff_df.empty:
        return cutoff_df, pd.DataFrame()

    summary_df = (
        cutoff_df.groupby(["horizon", "model_kind", "feature_family", "alpha"], as_index=False)
        .agg(
            mean_p100=("precision_at_100", "mean"),
            mean_r100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
            mean_delta_p100_vs_pref=("delta_p100_vs_pref", "mean"),
            mean_delta_r100_vs_pref=("delta_r100_vs_pref", "mean"),
            mean_delta_mrr_vs_pref=("delta_mrr_vs_pref", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
            total_eval_pos=("n_eval_pos", "sum"),
        )
        .sort_values(["horizon", "mean_r100", "mean_mrr"], ascending=[True, False, False])
        .reset_index(drop=True)
    )
    summary_df["selection_objective"] = (
        summary_df["mean_mrr"].astype(float)
        + 1.5 * summary_df["mean_r100"].astype(float)
    )
    return cutoff_df, summary_df


def _pick_best(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    best = (
        summary_df.sort_values(["horizon", "selection_objective"], ascending=[True, False])
        .groupby("horizon", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    return best


def _score_model_on_eval(
    panel_df: pd.DataFrame,
    corpus_df: pd.DataFrame,
    selected_df: pd.DataFrame,
    eval_years: list[int],
    train_allowed_years: list[int],
    era_label: str,
    pairwise_negatives_per_positive: int,
    pairwise_max_pairs_per_cutoff: int,
    seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_cache: dict[tuple[int, int], dict[str, float]] = {}
    for spec in selected_df.itertuples(index=False):
        horizon = int(spec.horizon)
        block = panel_df[panel_df["horizon"].astype(int) == horizon].copy()
        if block.empty:
            continue
        for cutoff_t in eval_years:
            eval_rows = block[block["cutoff_year_t"].astype(int) == int(cutoff_t)].copy()
            train_rows = block[
                block["cutoff_year_t"].astype(int).isin(train_allowed_years)
                & (block["cutoff_year_t"].astype(int) < int(cutoff_t))
            ].copy()
            if eval_rows.empty or train_rows.empty:
                continue
            model = _fit_model(
                train_rows=train_rows,
                model_kind=str(spec.model_kind),
                feature_family=str(spec.feature_family),
                alpha=float(spec.alpha),
                pairwise_negatives_per_positive=int(pairwise_negatives_per_positive),
                pairwise_max_pairs_per_cutoff=int(pairwise_max_pairs_per_cutoff),
                seed=int(seed) + int(cutoff_t) + int(horizon),
            )
            if model is None:
                continue
            reranked = score_with_reranker(eval_rows, model)
            reranked = reranked.merge(
                eval_rows.drop(columns=["score", "rank"], errors="ignore"),
                on=["u", "v"],
                how="left",
            )
            row = _evaluate_cutoff(
                label="reranker",
                eval_rows=reranked,
                cutoff_t=int(cutoff_t),
                horizon=int(horizon),
                corpus_df=corpus_df,
                baseline_cache=baseline_cache,
            )
            row["era"] = str(era_label)
            row["model_kind"] = str(spec.model_kind)
            row["feature_family"] = str(spec.feature_family)
            row["alpha"] = float(spec.alpha)
            rows.append(row)

            pref_row = {
                "model": "pref_attach",
                "era": str(era_label),
                "cutoff_year_t": int(cutoff_t),
                "horizon": int(horizon),
                "n_eval_rows": int(len(eval_rows)),
                "n_eval_pos": int(eval_rows["appears_within_h"].astype(int).sum()),
            }
            base = _baseline_metrics(int(cutoff_t), int(horizon), eval_rows, corpus_df, baseline_cache)
            for key, value in base.items():
                if key.startswith("pref_attach_"):
                    pref_row[key.replace("pref_attach_", "")] = float(value)
            rows.append(pref_row)

    return pd.DataFrame(rows)


def _summarize_era(eval_df: pd.DataFrame) -> pd.DataFrame:
    if eval_df.empty:
        return pd.DataFrame()
    summary = (
        eval_df.groupby(["era", "model", "horizon"], as_index=False)
        .agg(
            mean_p100=("precision_at_100", "mean"),
            mean_r100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
            mean_hits100=("hits_at_100", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
            mean_eval_pos=("n_eval_pos", "mean"),
        )
        .sort_values(["horizon", "era", "model"])
        .reset_index(drop=True)
    )
    return summary


def _build_table_rows(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    rer = summary_df[summary_df["model"] == "reranker"].copy()
    pref = summary_df[summary_df["model"] == "pref_attach"].copy()
    merged = rer.merge(pref, on=["era", "horizon"], suffixes=("_reranker", "_pref"))
    merged["pct_lift_vs_pref"] = np.where(
        merged["mean_p100_pref"] > 0,
        100.0 * (merged["mean_p100_reranker"] / merged["mean_p100_pref"] - 1.0),
        np.nan,
    )
    return merged.sort_values(["era", "horizon"]).reset_index(drop=True)


def _plot_figure(table_df: pd.DataFrame, out_path: Path, title: str | None = None) -> None:
    if table_df.empty:
        return
    eras = [TRAIN_ERA, HELDOUT_ERA]
    era_labels = {
        TRAIN_ERA: "Train era\n(1990-2005)",
        HELDOUT_ERA: "Held-out era\n(2010-2015)",
    }
    horizon_order = sorted(table_df["horizon"].astype(int).unique())
    colors = {"reranker": "#1f77b4", "pref_attach": "#9aa0a6"}

    fig, axes = plt.subplots(1, len(horizon_order), figsize=(7.4, 3.3), sharey=True)
    if len(horizon_order) == 1:
        axes = [axes]

    for ax, horizon in zip(axes, horizon_order):
        sub = table_df[table_df["horizon"].astype(int) == int(horizon)].set_index("era")
        x = np.arange(len(eras))
        width = 0.34
        rer_vals = [float(sub.loc[e, "mean_p100_reranker"]) for e in eras]
        pref_vals = [float(sub.loc[e, "mean_p100_pref"]) for e in eras]
        ax.bar(x - width / 2, rer_vals, width=width, color=colors["reranker"], label="Reranker")
        ax.bar(x + width / 2, pref_vals, width=width, color=colors["pref_attach"], label="Pref. attach.")
        for i, era in enumerate(eras):
            lift = float(sub.loc[era, "pct_lift_vs_pref"])
            ax.text(
                x[i] - width / 2,
                rer_vals[i] + 0.01,
                f"{lift:+.0f}%",
                ha="center",
                va="bottom",
                fontsize=8,
                color=colors["reranker"],
            )
        ax.set_xticks(x)
        ax.set_xticklabels([era_labels[e] for e in eras], fontsize=8)
        ax.set_title(f"h={int(horizon)}", fontsize=10)
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Precision@100")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors["reranker"]),
        plt.Rectangle((0, 0), 1, 1, color=colors["pref_attach"]),
    ]
    fig.legend(handles, ["Reranker", "Pref. attach."], loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.05))
    if title:
        fig.suptitle(title, y=1.12, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _write_summary_md(
    best_df: pd.DataFrame,
    table_df: pd.DataFrame,
    out_path: Path,
    train_eval_years: list[int],
    holdout_years: list[int],
    train_allowed_years: list[int],
) -> None:
    lines = [
        "# Temporal Generalization Refresh",
        "",
        "This note refreshes the temporal generalization test on the current effective-corpus path-to-direct benchmark stack.",
        "",
        f"- Train-era selection/evaluation cutoffs: {', '.join(str(x) for x in train_eval_years)}",
        f"- Held-out evaluation cutoffs: {', '.join(str(x) for x in holdout_years)}",
        f"- Training allowed during held-out evaluation: {', '.join(str(x) for x in train_allowed_years)}",
        "",
        "## Selected reranker configurations from the train era",
        "",
    ]
    for row in best_df.itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}: {row.model_kind} + {row.feature_family}, alpha={float(row.alpha):.2f} "
            f"| train-era P@100={float(row.mean_p100):.3f}, R@100={float(row.mean_r100):.3f}, MRR={float(row.mean_mrr):.4f}"
        )
    lines.extend(["", "## Era summary", ""])
    for row in table_df.itertuples(index=False):
        lines.append(
            f"- {row.era}, h={int(row.horizon)}: reranker P@100={float(row.mean_p100_reranker):.3f}, "
            f"pref P@100={float(row.mean_p100_pref):.3f}, lift vs pref={float(row.pct_lift_vs_pref):+.1f}%, "
            f"reranker R@100={float(row.mean_r100_reranker):.3f}, pref R@100={float(row.mean_r100_pref):.3f}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    cfg.candidate_family_mode = str(args.candidate_family_mode)
    cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_df = pd.read_parquet(args.paper_meta_path) if args.paper_meta_path and Path(args.paper_meta_path).exists() else None

    horizons = parse_horizons(args.horizons, default=[5, 10])
    max_year = int(corpus_df["year"].max())
    panel_years = parse_cutoff_years(
        _parse_csv_ints(args.years),
        min_year=int(corpus_df["year"].min()),
        max_year=max_year,
        max_h=min(horizons),
        step=5,
    )
    train_eval_years = [int(x) for x in _parse_csv_ints(args.train_years) if int(x) in panel_years]
    holdout_years = [int(x) for x in _parse_csv_ints(args.holdout_years) if int(x) in panel_years]
    warmup_years = [int(x) for x in _parse_csv_ints(args.warmup_years) if int(x) in panel_years]
    train_allowed_years = sorted(set(warmup_years + train_eval_years))
    feature_families = _parse_csv_strs(args.feature_families)
    model_kinds = _parse_csv_strs(args.model_kinds)
    alphas = _parse_csv_floats(args.alphas)

    panel_path = Path(args.panel_path)
    if panel_path.exists():
        panel_df = pd.read_parquet(panel_path)
    else:
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            cutoff_years=panel_years,
            horizons=horizons,
            pool_sizes=[int(args.pool_size)],
            paper_meta_df=paper_meta_df,
        )
    pool_flag = f"in_pool_{int(args.pool_size)}"
    panel_df = panel_df[
        panel_df["cutoff_year_t"].astype(int).isin(panel_years)
        & panel_df["horizon"].astype(int).isin(horizons)
        & (panel_df[pool_flag].astype(int) == 1)
    ].copy()

    train_cutoff_df, train_summary_df = _select_training_configs(
        panel_df=panel_df,
        corpus_df=corpus_df,
        train_eval_years=train_eval_years,
        train_allowed_years=train_allowed_years,
        horizons=horizons,
        feature_families=feature_families,
        model_kinds=model_kinds,
        alphas=alphas,
        pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
        pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
        seed=int(args.seed),
    )
    if train_summary_df.empty:
        raise ValueError("No train-era temporal generalization tuning results were produced")
    best_df = _pick_best(train_summary_df)

    train_eval_df = _score_model_on_eval(
        panel_df=panel_df,
        corpus_df=corpus_df,
        selected_df=best_df,
        eval_years=train_eval_years,
        train_allowed_years=train_allowed_years,
        era_label=TRAIN_ERA,
        pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
        pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
        seed=int(args.seed),
    )
    holdout_eval_df = _score_model_on_eval(
        panel_df=panel_df,
        corpus_df=corpus_df,
        selected_df=best_df,
        eval_years=holdout_years,
        train_allowed_years=train_allowed_years,
        era_label=HELDOUT_ERA,
        pairwise_negatives_per_positive=int(args.pairwise_negatives_per_positive),
        pairwise_max_pairs_per_cutoff=int(args.pairwise_max_pairs_per_cutoff),
        seed=int(args.seed),
    )
    eval_df = pd.concat([train_eval_df, holdout_eval_df], ignore_index=True)
    era_summary_df = _summarize_era(eval_df)
    table_df = _build_table_rows(era_summary_df)

    manifest = {
        "corpus_path": args.corpus_path,
        "config_path": args.config_path,
        "best_config_path": args.best_config_path,
        "paper_meta_path": args.paper_meta_path,
        "panel_path": args.panel_path,
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "pool_size": int(args.pool_size),
        "panel_cutoff_years": [int(x) for x in panel_years],
        "train_eval_years": [int(x) for x in train_eval_years],
        "holdout_years": [int(x) for x in holdout_years],
        "warmup_years": [int(x) for x in warmup_years],
        "train_allowed_years": [int(x) for x in train_allowed_years],
        "horizons": [int(x) for x in horizons],
        "feature_families": feature_families,
        "model_kinds": model_kinds,
        "alphas": alphas,
    }

    train_cutoff_df.to_csv(Path(out_dir) / "train_selection_cutoff_eval.csv", index=False)
    train_summary_df.to_csv(Path(out_dir) / "train_selection_summary.csv", index=False)
    best_df.to_csv(Path(out_dir) / "selected_configs.csv", index=False)
    eval_df.to_csv(Path(out_dir) / "temporal_generalization_cutoff_eval.csv", index=False)
    era_summary_df.to_csv(Path(out_dir) / "temporal_generalization_era_summary.csv", index=False)
    table_df.to_csv(Path(out_dir) / "temporal_generalization_table.csv", index=False)
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_summary_md(
        best_df=best_df,
        table_df=table_df,
        out_path=Path(out_dir) / "summary.md",
        train_eval_years=train_eval_years,
        holdout_years=holdout_years,
        train_allowed_years=train_allowed_years,
    )

    fig_out = Path(out_dir) / "temporal_generalization_refreshed.png"
    _plot_figure(table_df, fig_out)
    paper_fig_out = ROOT / args.paper_figure_path
    _plot_figure(table_df, paper_fig_out)
    print(f"Wrote: {Path(out_dir) / 'temporal_generalization_era_summary.csv'}")


if __name__ == "__main__":
    main()
