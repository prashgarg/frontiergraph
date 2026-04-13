from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir
from src.analysis.learned_reranker import (
    _feature_list,
    build_candidate_feature_panel,
    fit_glm_logit_reranker,
    fit_pairwise_logit_reranker,
    score_with_reranker,
)
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking
from src.utils import load_config, load_corpus


ENV_PATTERNS = [
    r"\bcarbon\b",
    r"\bco2\b",
    r"\bemissions?\b",
    r"\bclimate\b",
    r"\benvironment",
    r"\bpollution\b",
    r"\becological\b",
    r"\bgreen\b",
    r"\brenewable\b",
    r"\benergy\b",
    r"\bsustainab",
]
INNOV_PATTERNS = [r"\binnovation\b", r"\btechnolog", r"\bdigital\b"]
MACRO_PATTERNS = [r"\bbusiness cycle\b", r"\bgrowth\b", r"\binflation\b", r"\bhouse prices?\b", r"\bprice changes?\b", r"\bproductivity\b", r"\boutput\b"]
FIN_PATTERNS = [r"\bfinancial\b", r"\bfinance\b", r"\btax\b", r"\bbonds?\b", r"\binvestment\b", r"\bdebt\b"]
DEMAND_PATTERNS = [r"\bwages?\b", r"\bincome\b", r"\bemployment\b", r"\bwillingness to pay\b", r"\bconsumption\b"]
TRADE_PATTERNS = [r"\btrade\b", r"\bimports?\b", r"\bexports?\b", r"\bglobal", r"\burban", r"\bcity\b", r"\btourism\b", r"\bindustrial structure\b"]
UNCERTAINTY_PATTERNS = [r"\buncertainty\b", r"\brisk\b"]


@dataclass(frozen=True)
class RegularizerConfig:
    sink_start_pct: float
    sink_lambda: float
    diversify_window: int
    repeat_log_lambda: float
    repeat_linear_lambda: float

    @property
    def config_id(self) -> str:
        return (
            f"s{self.sink_start_pct:.4f}_ls{self.sink_lambda:.4f}_"
            f"w{self.diversify_window}_rl{self.repeat_log_lambda:.4f}_"
            f"rn{self.repeat_linear_lambda:.4f}"
        )

    @property
    def penalty_strength(self) -> float:
        return float(self.sink_lambda + self.repeat_log_lambda + self.repeat_linear_lambda)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate a v2.1 target-sink regularizer on held-out reranker cutoffs."
    )
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_1/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument(
        "--best-config",
        default="outputs/paper/51_v2_1_model_search/best_config.yaml",
        dest="best_config_path",
    )
    parser.add_argument(
        "--paper-meta",
        default="data/processed/research_allocation_v2_1/hybrid_papers_funding.parquet",
        dest="paper_meta_path",
    )
    parser.add_argument(
        "--tuning-best",
        default="outputs/paper/52_v2_1_learned_reranker_tuning/tuning_best_configs.csv",
        dest="tuning_best_path",
    )
    parser.add_argument(
        "--panel-cache",
        default="outputs/paper/55_v2_1_sink_regularizer_sweep/historical_feature_panel_v2_1.parquet",
        dest="panel_cache",
    )
    parser.add_argument(
        "--current-frontier",
        default="outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.parquet",
        dest="current_frontier_path",
    )
    parser.add_argument("--horizons", default="", dest="horizons")
    parser.add_argument("--candidate-family-mode", default="", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="", dest="path_to_direct_scope")
    parser.add_argument("--cutoff-years", default="1995,2000,2005,2010,2015", dest="cutoff_years")
    parser.add_argument("--pool-size", type=int, default=10000, dest="pool_size")
    parser.add_argument("--k-values", default="20,50,100", dest="k_values")
    parser.add_argument("--sink-starts", default="0.995,0.9975", dest="sink_starts")
    parser.add_argument("--sink-lambdas", default="0,0.002,0.004,0.006", dest="sink_lambdas")
    parser.add_argument("--diversify-windows", default="100,300", dest="diversify_windows")
    parser.add_argument("--repeat-log-lambdas", default="0,0.002,0.0045", dest="repeat_log_lambdas")
    parser.add_argument("--repeat-linear-lambdas", default="0,0.0015", dest="repeat_linear_lambdas")
    parser.add_argument("--out", default="outputs/paper/55_v2_1_sink_regularizer_sweep", dest="out_dir")
    parser.add_argument(
        "--note",
        default="next_steps/sink_regularizer_calibration_note.md",
        dest="note_path",
    )
    return parser.parse_args()


def _parse_float_list(raw: str) -> list[float]:
    return [float(x.strip()) for x in str(raw).split(",") if x.strip()]


def _parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _fit_model(
    model_kind: str,
    train_rows: pd.DataFrame,
    feature_names: list[str],
    alpha: float,
):
    if model_kind == "glm_logit":
        return fit_glm_logit_reranker(train_rows, feature_names=feature_names, alpha=float(alpha))
    if model_kind == "pairwise_logit":
        return fit_pairwise_logit_reranker(
            train_rows,
            feature_names=feature_names,
            alpha=float(alpha),
            negatives_per_positive=2,
            max_pairs_per_cutoff=2000,
            seed=42,
        )
    raise ValueError(f"Unsupported model_kind: {model_kind}")


def _load_label_map(corpus_df: pd.DataFrame) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for left, right in [("src_code", "src_label"), ("dst_code", "dst_label")]:
        if left in corpus_df.columns and right in corpus_df.columns:
            tmp = corpus_df[[left, right]].drop_duplicates()
            for row in tmp.itertuples(index=False):
                code = str(getattr(row, left))
                label = str(getattr(row, right))
                if code and label and code not in label_map:
                    label_map[code] = label
    return label_map


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_family_label(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "gdp": "gdp",
        "gross domestic product gdp": "gdp",
        "gross domestic product": "gdp",
        "economic growth gdp": "gdp",
        "co2 emissions": "carbon emissions",
        "carbon emissions co2 emissions": "carbon emissions",
        "willingness to pay wtp": "willingness to pay",
        "environmental quality co2 emissions": "environmental quality",
    }
    return alias_map.get(text, text)


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _theme_for_label(label: str) -> str:
    text = _normalize_family_label(label)
    if _match_any(text, ENV_PATTERNS):
        return "environment_climate"
    if _match_any(text, INNOV_PATTERNS):
        return "innovation_technology"
    if _match_any(text, MACRO_PATTERNS):
        return "macro_cycle_prices"
    if _match_any(text, FIN_PATTERNS):
        return "finance_tax"
    if _match_any(text, DEMAND_PATTERNS):
        return "labor_income_demand"
    if _match_any(text, TRADE_PATTERNS):
        return "trade_urban_structure"
    if _match_any(text, UNCERTAINTY_PATTERNS):
        return "uncertainty_risk"
    return "other"


def _annotate_keys(df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    out["source_label"] = out["u"].astype(str).map(label_map).fillna(out["u"].astype(str))
    out["target_label"] = out["v"].astype(str).map(label_map).fillna(out["v"].astype(str))
    out["source_family"] = out["source_label"].map(_normalize_family_label)
    out["target_family"] = out["target_label"].map(_normalize_family_label)
    out["semantic_family_key"] = out["source_family"].astype(str) + "__" + out["target_family"].astype(str)
    out["source_theme"] = out["source_label"].map(_theme_for_label)
    out["target_theme"] = out["target_label"].map(_theme_for_label)
    out["theme_pair_key"] = out["source_theme"].astype(str) + "__" + out["target_theme"].astype(str)
    return out


def _annotate_labels(df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    out["u_label"] = out["u"].astype(str).map(label_map).fillna(out["u"].astype(str))
    out["v_label"] = out["v"].astype(str).map(label_map).fillna(out["v"].astype(str))
    return out


def _compute_sink_targets(df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "target_direct_in_degree",
        "target_support_in_degree",
        "target_incident_count",
        "target_evidence_diversity",
        "target_venue_diversity",
        "target_source_diversity",
    ]
    targets = df[["v", "v_label"] + metric_cols].drop_duplicates("v").copy()
    for col in metric_cols:
        targets[f"{col}_pct"] = targets[col].rank(method="average", pct=True)
    targets["sink_score"] = targets[[f"{c}_pct" for c in metric_cols]].mean(axis=1)
    targets["sink_score_pct"] = targets["sink_score"].rank(method="average", pct=True)
    return targets


def _apply_regularizer(
    df: pd.DataFrame,
    cfg: RegularizerConfig,
    rank_col: str = "reranker_rank",
    score_col: str = "reranker_score",
) -> pd.DataFrame:
    g = df.copy().reset_index(drop=True)
    n = len(g)
    g["reranker_pct"] = 1.0 - (g[rank_col].astype(float) - 1.0) / max(n - 1, 1)
    if cfg.sink_lambda > 0:
        width = max(1.0 - float(cfg.sink_start_pct), 1e-9)
        g["sink_excess"] = ((g["sink_score_pct"].astype(float) - cfg.sink_start_pct) / width).clip(lower=0.0, upper=1.0)
        g["sink_penalty"] = cfg.sink_lambda * g["sink_excess"]
    else:
        g["sink_excess"] = 0.0
        g["sink_penalty"] = 0.0
    g["base_priority"] = g["reranker_pct"] - g["sink_penalty"]
    g = g.sort_values(["base_priority", score_col], ascending=[False, False]).reset_index(drop=True)

    if cfg.repeat_log_lambda <= 0 and cfg.repeat_linear_lambda <= 0:
        out = g.copy()
        out["diversification_penalty"] = 0.0
        out["regularized_priority"] = out["base_priority"]
        out["regularized_rank"] = out.index + 1
        return out

    top = g.head(int(cfg.diversify_window)).copy()
    rest = g.iloc[int(cfg.diversify_window) :].copy()
    selected_rows: list[pd.Series] = []
    target_counts: dict[str, int] = {}

    while not top.empty:
        penalties = top["v"].astype(str).map(
            lambda target: (
                cfg.repeat_log_lambda * math.log1p(target_counts.get(target, 0))
                + cfg.repeat_linear_lambda * max(target_counts.get(target, 0) - 1, 0)
            )
        )
        top = top.assign(
            diversification_penalty=penalties.astype(float),
            regularized_priority=top["base_priority"] - penalties.astype(float),
        )
        chosen_idx = top.sort_values(
            ["regularized_priority", "base_priority", score_col],
            ascending=[False, False, False],
        ).index[0]
        chosen = top.loc[chosen_idx]
        selected_rows.append(chosen)
        target = str(chosen["v"])
        target_counts[target] = target_counts.get(target, 0) + 1
        top = top.drop(index=chosen_idx)

    selected_df = pd.DataFrame(selected_rows)
    if rest.empty:
        out = selected_df.copy()
    else:
        rest = rest.assign(diversification_penalty=0.0, regularized_priority=rest["base_priority"])
        out = pd.concat([selected_df, rest], ignore_index=True)
    out = out.reset_index(drop=True)
    out["regularized_rank"] = out.index + 1
    return out


def _ranking_metrics(
    ranked_df: pd.DataFrame,
    positives: set[tuple[str, str]],
    rank_col: str,
    score_col: str,
    k_values: list[int],
) -> dict[str, float]:
    tmp = ranked_df[["u", "v", score_col, rank_col]].copy().rename(columns={score_col: "score", rank_col: "rank"})
    tmp = tmp.sort_values("rank", ascending=True).reset_index(drop=True)
    return evaluate_binary_ranking(tmp, positives=positives, k_values=k_values)


def _concentration_metrics(df: pd.DataFrame, rank_col: str, k: int) -> dict[str, float]:
    top = df[df[rank_col] <= k]
    if top.empty:
        return {
            f"unique_targets_top{k}": 0,
            f"unique_theme_pair_keys_top{k}": 0,
            f"unique_semantic_family_keys_top{k}": 0,
            f"top_target_share_top{k}": 0.0,
            f"hhi_top{k}": 0.0,
        }
    counts = top["v"].astype(str).value_counts()
    shares = counts / float(len(top))
    return {
        f"unique_targets_top{k}": int(counts.size),
        f"unique_theme_pair_keys_top{k}": int(top["theme_pair_key"].astype(str).nunique()) if "theme_pair_key" in top.columns else 0,
        f"unique_semantic_family_keys_top{k}": int(top["semantic_family_key"].astype(str).nunique()) if "semantic_family_key" in top.columns else 0,
        f"top_target_share_top{k}": float(shares.iloc[0]),
        f"hhi_top{k}": float((shares**2).sum()),
    }


def _build_config_grid(args: argparse.Namespace) -> list[RegularizerConfig]:
    sink_starts = _parse_float_list(args.sink_starts)
    sink_lambdas = _parse_float_list(args.sink_lambdas)
    diversify_windows = _parse_int_list(args.diversify_windows)
    repeat_log_lambdas = _parse_float_list(args.repeat_log_lambdas)
    repeat_linear_lambdas = _parse_float_list(args.repeat_linear_lambdas)

    seen: set[tuple[float, float, int, float, float]] = set()
    configs: list[RegularizerConfig] = []
    for sink_start, sink_lambda, window, repeat_log, repeat_lin in product(
        sink_starts,
        sink_lambdas,
        diversify_windows,
        repeat_log_lambdas,
        repeat_linear_lambdas,
    ):
        effective_start = sink_start if sink_lambda > 0 else sink_starts[0]
        effective_window = window if (repeat_log > 0 or repeat_lin > 0) else diversify_windows[0]
        key = (
            float(effective_start),
            float(sink_lambda),
            int(effective_window),
            float(repeat_log),
            float(repeat_lin),
        )
        if key in seen:
            continue
        seen.add(key)
        configs.append(
            RegularizerConfig(
                sink_start_pct=float(effective_start),
                sink_lambda=float(sink_lambda),
                diversify_window=int(effective_window),
                repeat_log_lambda=float(repeat_log),
                repeat_linear_lambda=float(repeat_lin),
            )
        )
    configs = sorted(
        configs,
        key=lambda c: (
            c.penalty_strength,
            c.sink_start_pct,
            c.diversify_window,
            c.repeat_log_lambda,
            c.repeat_linear_lambda,
        ),
    )
    return configs


def _select_recommended(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for horizon, block in summary_df.groupby("horizon", sort=True):
        base = block[block["penalty_strength"] == 0].sort_values("config_id").head(1)
        if base.empty:
            continue
        base = base.iloc[0]
        eligible = block[
            (block["mean_mrr"] >= float(base["mean_mrr"]) - float(base["sem_mrr"]))
            & (block["mean_recall_at_100"] >= float(base["mean_recall_at_100"]) - float(base["sem_recall_at_100"]))
            & (block["mean_precision_at_100"] >= float(base["mean_precision_at_100"]) - float(base["sem_precision_at_100"]))
        ].copy()
        if eligible.empty:
            eligible = block.copy()
        eligible = eligible.sort_values(
            [
                "mean_hhi_top100",
                "mean_top_target_share_top100",
                "mean_unique_targets_top100",
                "penalty_strength",
                "mean_mrr",
                "mean_recall_at_100",
            ],
            ascending=[True, True, False, True, False, False],
        )
        winner = eligible.head(1).copy()
        winner["baseline_mean_mrr"] = float(base["mean_mrr"])
        winner["baseline_mean_recall_at_100"] = float(base["mean_recall_at_100"])
        winner["baseline_mean_precision_at_100"] = float(base["mean_precision_at_100"])
        rows.append(winner)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _apply_recommended_to_current_frontier(
    current_frontier: pd.DataFrame,
    recommended_df: pd.DataFrame,
) -> pd.DataFrame:
    out_frames: list[pd.DataFrame] = []
    for row in recommended_df.itertuples(index=False):
        horizon = int(row.horizon)
        sub = current_frontier[current_frontier["horizon"] == horizon].copy()
        if sub.empty:
            continue
        sink_df = _compute_sink_targets(sub)
        sub = sub.merge(sink_df[["v", "sink_score", "sink_score_pct"]], on="v", how="left")
        cfg = RegularizerConfig(
            sink_start_pct=float(row.sink_start_pct),
            sink_lambda=float(row.sink_lambda),
            diversify_window=int(row.diversify_window),
            repeat_log_lambda=float(row.repeat_log_lambda),
            repeat_linear_lambda=float(row.repeat_linear_lambda),
        )
        ranked = _apply_regularizer(sub, cfg, rank_col="reranker_rank", score_col="reranker_score")
        ranked["recommended_config_id"] = row.config_id
        out_frames.append(ranked)
    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    note_path = Path(args.note_path)
    k_values = _parse_int_list(args.k_values)
    cutoff_years = _parse_int_list(args.cutoff_years)

    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    if args.candidate_family_mode:
        cfg.candidate_family_mode = str(args.candidate_family_mode)
    if args.path_to_direct_scope:
        cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    paper_meta_path = Path(args.paper_meta_path)
    paper_meta_df = pd.read_parquet(paper_meta_path) if paper_meta_path.exists() else None
    best_df = pd.read_csv(args.tuning_best_path)
    if best_df.empty:
        raise SystemExit("No best tuning configurations found.")

    label_map = _load_label_map(corpus_df)
    panel_cache = Path(args.panel_cache)
    if panel_cache.exists():
        panel_df = pd.read_parquet(panel_cache)
    else:
        horizons = [int(x.strip()) for x in str(args.horizons).split(",") if x.strip()] if str(args.horizons).strip() else sorted(best_df["horizon"].dropna().astype(int).unique().tolist())
        panel_df = build_candidate_feature_panel(
            corpus_df=corpus_df,
            cfg=cfg,
            cutoff_years=cutoff_years,
            horizons=horizons,
            pool_sizes=[int(args.pool_size)],
            paper_meta_df=paper_meta_df,
        )
        panel_cache.parent.mkdir(parents=True, exist_ok=True)
        panel_df.to_parquet(panel_cache, index=False)

    pool_flag = f"in_pool_{int(args.pool_size)}"
    if pool_flag not in panel_df.columns:
        raise SystemExit(f"Missing pool flag `{pool_flag}` in panel.")

    configs = _build_config_grid(args)
    config_rows = pd.DataFrame(
        [
            {
                "config_id": cfg.config_id,
                "sink_start_pct": cfg.sink_start_pct,
                "sink_lambda": cfg.sink_lambda,
                "diversify_window": cfg.diversify_window,
                "repeat_log_lambda": cfg.repeat_log_lambda,
                "repeat_linear_lambda": cfg.repeat_linear_lambda,
                "penalty_strength": cfg.penalty_strength,
            }
            for cfg in configs
        ]
    )
    config_rows.to_csv(out_dir / "regularizer_grid.csv", index=False)

    cutoff_rows: list[dict[str, Any]] = []
    for best in best_df.itertuples(index=False):
        horizon = int(best.horizon)
        feature_family = str(best.feature_family)
        model_kind = str(best.model_kind)
        alpha = float(best.alpha)

        horizon_df = panel_df[
            (panel_df["horizon"] == horizon) & (panel_df[pool_flag].astype(int) == 1)
        ].copy()
        if horizon_df.empty:
            continue

        for cutoff_t in sorted(horizon_df["cutoff_year_t"].dropna().astype(int).unique()):
            eval_rows = horizon_df[horizon_df["cutoff_year_t"] == int(cutoff_t)].copy()
            train_rows = horizon_df[horizon_df["cutoff_year_t"] < int(cutoff_t)].copy()
            if eval_rows.empty or train_rows.empty or train_rows["appears_within_h"].nunique() < 2:
                continue

            feature_names = [
                c for c in _feature_list(feature_family) if c in train_rows.columns and c in eval_rows.columns
            ]
            if not feature_names:
                continue

            model = _fit_model(model_kind=model_kind, train_rows=train_rows, feature_names=feature_names, alpha=alpha)
            if model is None:
                continue

            scored = score_with_reranker(eval_rows, model).rename(columns={"score": "reranker_score", "rank": "reranker_rank"})
            merged = eval_rows.merge(scored, on=["u", "v"], how="left")
            merged = _annotate_labels(merged, label_map)
            merged = _annotate_keys(merged, label_map)
            sink_df = _compute_sink_targets(merged)
            merged = merged.merge(sink_df[["v", "sink_score", "sink_score_pct"]], on="v", how="left")
            merged = merged.sort_values(["reranker_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)

            positives = {
                (str(row.u), str(row.v))
                for row in eval_rows[eval_rows["appears_within_h"].astype(int) == 1][["u", "v"]].itertuples(index=False)
            }

            for reg_cfg in configs:
                ranked = _apply_regularizer(merged, reg_cfg)
                metrics = _ranking_metrics(
                    ranked_df=ranked,
                    positives=positives,
                    rank_col="regularized_rank",
                    score_col="reranker_score",
                    k_values=k_values,
                )
                row = {
                    "config_id": reg_cfg.config_id,
                    "sink_start_pct": reg_cfg.sink_start_pct,
                    "sink_lambda": reg_cfg.sink_lambda,
                    "diversify_window": reg_cfg.diversify_window,
                    "repeat_log_lambda": reg_cfg.repeat_log_lambda,
                    "repeat_linear_lambda": reg_cfg.repeat_linear_lambda,
                    "penalty_strength": reg_cfg.penalty_strength,
                    "horizon": horizon,
                    "candidate_family_mode": str(cfg.candidate_family_mode),
                    "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
                    "concentration_variant": "sink_plus_diversification",
                    "cutoff_year_t": int(cutoff_t),
                    "model_kind": model_kind,
                    "feature_family": feature_family,
                    "alpha": alpha,
                    "n_eval_rows": int(len(eval_rows)),
                    "n_positives": int(len(positives)),
                    "mrr": float(metrics.get("mrr", 0.0)),
                    "precision_at_20": float(metrics.get("precision_at_20", 0.0)),
                    "precision_at_50": float(metrics.get("precision_at_50", 0.0)),
                    "precision_at_100": float(metrics.get("precision_at_100", 0.0)),
                    "recall_at_20": float(metrics.get("recall_at_20", 0.0)),
                    "recall_at_50": float(metrics.get("recall_at_50", 0.0)),
                    "recall_at_100": float(metrics.get("recall_at_100", 0.0)),
                }
                row.update(_concentration_metrics(ranked, rank_col="regularized_rank", k=20))
                row.update(_concentration_metrics(ranked, rank_col="regularized_rank", k=100))
                cutoff_rows.append(row)

    if not cutoff_rows:
        raise SystemExit("No sweep results were produced.")

    cutoff_df = pd.DataFrame(cutoff_rows).sort_values(["horizon", "config_id", "cutoff_year_t"]).reset_index(drop=True)
    cutoff_df.to_csv(out_dir / "sink_regularizer_by_cutoff.csv", index=False)

    summary_df = (
        cutoff_df.groupby(
            [
                "config_id",
                "sink_start_pct",
                "sink_lambda",
                "diversify_window",
                "repeat_log_lambda",
                "repeat_linear_lambda",
                "penalty_strength",
                "horizon",
            ],
            as_index=False,
        )
        .agg(
            mean_mrr=("mrr", "mean"),
            sem_mrr=("mrr", lambda s: float(pd.Series(s).std(ddof=1) / math.sqrt(len(s))) if len(s) > 1 else 0.0),
            mean_precision_at_100=("precision_at_100", "mean"),
            sem_precision_at_100=("precision_at_100", lambda s: float(pd.Series(s).std(ddof=1) / math.sqrt(len(s))) if len(s) > 1 else 0.0),
            mean_recall_at_100=("recall_at_100", "mean"),
            sem_recall_at_100=("recall_at_100", lambda s: float(pd.Series(s).std(ddof=1) / math.sqrt(len(s))) if len(s) > 1 else 0.0),
            mean_unique_targets_top20=("unique_targets_top20", "mean"),
            mean_unique_targets_top100=("unique_targets_top100", "mean"),
            mean_unique_theme_pair_keys_top20=("unique_theme_pair_keys_top20", "mean"),
            mean_unique_theme_pair_keys_top100=("unique_theme_pair_keys_top100", "mean"),
            mean_unique_semantic_family_keys_top20=("unique_semantic_family_keys_top20", "mean"),
            mean_unique_semantic_family_keys_top100=("unique_semantic_family_keys_top100", "mean"),
            mean_top_target_share_top20=("top_target_share_top20", "mean"),
            mean_top_target_share_top100=("top_target_share_top100", "mean"),
            mean_hhi_top20=("hhi_top20", "mean"),
            mean_hhi_top100=("hhi_top100", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "mean_hhi_top100", "mean_mrr"], ascending=[True, True, False])
        .reset_index(drop=True)
    )
    summary_df.to_csv(out_dir / "sink_regularizer_summary.csv", index=False)

    recommended_df = _select_recommended(summary_df)
    recommended_df.to_csv(out_dir / "recommended_sink_regularizer_configs.csv", index=False)

    tuned_frontier = pd.DataFrame()
    current_frontier_path = Path(args.current_frontier_path)
    if current_frontier_path.exists():
        current_frontier = pd.read_parquet(current_frontier_path)
        tuned_frontier = _apply_recommended_to_current_frontier(current_frontier, recommended_df)
        tuned_frontier.to_parquet(out_dir / "current_frontier_with_tuned_sink_regularizer.parquet", index=False)
        tuned_frontier.to_csv(out_dir / "current_frontier_with_tuned_sink_regularizer.csv", index=False)

        tuned_rows: list[dict[str, Any]] = []
        for horizon, block in tuned_frontier.groupby("horizon", sort=True):
            for label in ["Willingness to pay", "Economic Growth", "R&D", "Carbon dioxide", "Total factor productivity", "Green innovation"]:
                sub = block[block["v_label"] == label]
                tuned_rows.append(
                    {
                        "horizon": int(horizon),
                        "target_label": label,
                        "baseline_top20": int((sub["reranker_rank"] <= 20).sum()),
                        "baseline_top100": int((sub["reranker_rank"] <= 100).sum()),
                        "tuned_top20": int((sub["regularized_rank"] <= 20).sum()),
                        "tuned_top100": int((sub["regularized_rank"] <= 100).sum()),
                    }
                )
        pd.DataFrame(tuned_rows).to_csv(out_dir / "tuned_current_frontier_endpoint_counts.csv", index=False)

    note_lines = [
        "# Sink Regularizer Calibration Note",
        "",
        "We calibrated a small family of target-sink regularizers on held-out cutoff years rather than choosing one penalty by hand.",
        "",
        "Selection rule:",
        "- compute walk-forward held-out performance for each regularizer setting",
        "- treat baseline performance variation across cutoffs as the tolerance band",
        "- keep only settings within roughly one baseline SEM on MRR, Recall@100, and Precision@100",
        "- among those, choose the configuration with the lowest top-100 endpoint concentration",
        "",
    ]

    for row in recommended_df.itertuples(index=False):
        note_lines.extend(
            [
                f"## Horizon {int(row.horizon)}",
                f"- recommended config: `{row.config_id}`",
                f"- sink start percentile: `{float(row.sink_start_pct):.4f}`",
                f"- sink lambda: `{float(row.sink_lambda):.4f}`",
                f"- diversify window: `{int(row.diversify_window)}`",
                f"- repeat log lambda: `{float(row.repeat_log_lambda):.4f}`",
                f"- repeat linear lambda: `{float(row.repeat_linear_lambda):.4f}`",
                f"- baseline mean MRR: `{float(row.baseline_mean_mrr):.6f}`",
                f"- baseline mean Recall@100: `{float(row.baseline_mean_recall_at_100):.6f}`",
                f"- baseline mean Precision@100: `{float(row.baseline_mean_precision_at_100):.6f}`",
                f"- tuned mean MRR: `{float(row.mean_mrr):.6f}`",
                f"- tuned mean Recall@100: `{float(row.mean_recall_at_100):.6f}`",
                f"- tuned mean Precision@100: `{float(row.mean_precision_at_100):.6f}`",
                f"- tuned mean HHI@100: `{float(row.mean_hhi_top100):.6f}`",
                f"- tuned mean top-target share@100: `{float(row.mean_top_target_share_top100):.6f}`",
                f"- tuned mean unique targets@100: `{float(row.mean_unique_targets_top100):.2f}`",
                "",
            ]
        )

    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    payload = {
        "candidate_family_mode": str(cfg.candidate_family_mode),
        "path_to_direct_scope": str(getattr(cfg, "path_to_direct_scope", "")),
        "n_grid_configs": int(config_rows.shape[0]),
        "n_cutoff_rows": int(cutoff_df.shape[0]),
        "recommended_configs": recommended_df[
            [
                "horizon",
                "config_id",
                "sink_start_pct",
                "sink_lambda",
                "diversify_window",
                "repeat_log_lambda",
                "repeat_linear_lambda",
                "mean_mrr",
                "mean_recall_at_100",
                "mean_precision_at_100",
                "mean_hhi_top100",
                "mean_top_target_share_top100",
                "mean_unique_targets_top100",
            ]
        ].to_dict(orient="records"),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote cutoff sweep: {out_dir / 'sink_regularizer_by_cutoff.csv'}")
    print(f"Wrote sweep summary: {out_dir / 'sink_regularizer_summary.csv'}")
    print(f"Wrote recommended configs: {out_dir / 'recommended_sink_regularizer_configs.csv'}")
    if not tuned_frontier.empty:
        print(f"Wrote tuned current frontier: {out_dir / 'current_frontier_with_tuned_sink_regularizer.parquet'}")
    print(f"Wrote note: {note_path}")


if __name__ == "__main__":
    main()
