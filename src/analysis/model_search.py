from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.analysis.common import (
    CandidateBuildConfig,
    build_candidate_table,
    check_no_leakage,
    ensure_output_dir,
    first_appearance_map,
    future_edges_for,
    set_seed,
)
from src.utils import load_config, load_corpus


def evaluate_ranking(ranking_df: pd.DataFrame, future_edges: set[tuple[str, str]], k: int = 100) -> dict[str, float]:
    if ranking_df.empty:
        return {"recall_at_100": 0.0, "mrr": 0.0, "n_future_edges": float(len(future_edges))}
    rank_map = {(str(r.u), str(r.v)): int(i + 1) for i, r in enumerate(ranking_df[["u", "v"]].itertuples(index=False))}
    total = max(1, len(future_edges))
    hits = sum(1 for e in future_edges if rank_map.get(e, np.inf) <= k)
    rr = [1.0 / rank_map[e] if e in rank_map else 0.0 for e in future_edges]
    return {
        "recall_at_100": float(hits) / float(total),
        "mrr": float(np.mean(rr) if rr else 0.0),
        "n_future_edges": float(len(future_edges)),
    }


def build_all_pairs(nodes: list[str]) -> pd.DataFrame:
    arr = np.array(sorted(set(nodes)), dtype=object)
    if arr.size == 0:
        return pd.DataFrame(columns=["u", "v"])
    u = np.repeat(arr, arr.size)
    v = np.tile(arr, arr.size)
    mask = u != v
    return pd.DataFrame({"u": u[mask], "v": v[mask]})


def pref_attach_ranking(train_df: pd.DataFrame, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    if train_df.empty or all_pairs_df.empty:
        return pd.DataFrame(columns=["u", "v", "score"])
    existing = (
        train_df[["src_code", "dst_code"]]
        .drop_duplicates()
        .rename(columns={"src_code": "u", "dst_code": "v"})
        .astype(str)
    )
    base = all_pairs_df.merge(existing.assign(_exists=1), on=["u", "v"], how="left")
    base = base[base["_exists"].isna()][["u", "v"]].copy()
    out_deg = train_df.groupby("src_code", as_index=False).agg(out_degree=("dst_code", "nunique"))
    in_deg = train_df.groupby("dst_code", as_index=False).agg(in_degree=("src_code", "nunique"))
    out_map = {str(r.src_code): int(r.out_degree) for r in out_deg.itertuples(index=False)}
    in_map = {str(r.dst_code): int(r.in_degree) for r in in_deg.itertuples(index=False)}
    base["score"] = [float(out_map.get(str(r.u), 0) * in_map.get(str(r.v), 0)) for r in base.itertuples(index=False)]
    base = base.sort_values("score", ascending=False).reset_index(drop=True)
    base["rank"] = base.index + 1
    return base


def score_with_coefficients(df: pd.DataFrame, cfg: CandidateBuildConfig) -> pd.DataFrame:
    g = df.copy()
    g["score"] = (
        float(cfg.alpha) * g["path_support_norm"].astype(float)
        + float(cfg.beta) * g["gap_bonus"].astype(float)
        + float(cfg.gamma) * g["motif_bonus_norm"].astype(float)
        - float(cfg.delta) * g["hub_penalty"].astype(float)
        + float(cfg.cooc_trend_coef) * g["cooc_trend_norm"].astype(float)
        - float(cfg.field_hub_penalty_scale)
        * g["hub_penalty"].astype(float)
        * g.get("field_same_group", pd.Series(0, index=g.index)).astype(float)
    )
    g = g.sort_values("score", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1
    return g


def make_structural_configs(base: CandidateBuildConfig) -> list[tuple[str, CandidateBuildConfig]]:
    c1 = CandidateBuildConfig(**asdict(base))
    c2 = CandidateBuildConfig(**asdict(base))
    c2.recency_decay_lambda = 0.08
    c3 = CandidateBuildConfig(**asdict(c2))
    c3.stability_coef = 0.5
    c3.causal_bonus = 0.2
    c4 = CandidateBuildConfig(**asdict(c3))
    c4.field_hub_penalty_scale = 0.2
    c5 = CandidateBuildConfig(**asdict(c4))
    c5.cooc_trend_coef = 0.15
    return [
        ("base_main", c1),
        ("plus_temporal", c2),
        ("plus_stability", c3),
        ("plus_field_hub", c4),
        ("plus_cooc_trend", c5),
    ]


def sample_weight_trials(n_trials: int, seed: int = 42) -> list[tuple[float, float, float, float, float]]:
    rng = np.random.default_rng(seed)
    trials: list[tuple[float, float, float, float, float]] = []
    for _ in range(n_trials):
        w = rng.dirichlet(np.array([2.0, 1.0, 1.5]))
        alpha, beta, gamma = [float(x) for x in w]
        delta = float(rng.uniform(0.05, 0.35))
        eta = float(rng.uniform(0.05, 0.35))
        trials.append((alpha, beta, gamma, delta, eta))
    return trials


def parse_years(year_values: list[int] | None, min_year: int, max_year: int, max_h: int) -> list[int]:
    if year_values:
        years = sorted(set(int(y) for y in year_values if (min_year + 1) <= int(y) <= (max_year - max_h)))
        return years
    defaults = [1990, 2000, 2010, 2015]
    years = [y for y in defaults if (min_year + 1) <= y <= (max_year - max_h)]
    if years:
        return years
    return list(range(min_year + 1, max_year - max_h + 1, 5))


def parse_horizons(raw: str) -> list[int]:
    hs = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    hs = sorted(set(h for h in hs if h > 0))
    return hs if hs else [1, 3, 5]


def run_model_search(
    corpus_df: pd.DataFrame,
    config: dict,
    cutoff_years: list[int],
    horizons: list[int],
    n_weight_trials: int = 25,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict, str]:
    set_seed(seed)
    first_year = first_appearance_map(corpus_df)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(all_nodes)

    feature_cfg = config.get("features", {})
    score_cfg = config.get("scoring", {})
    base_cfg = CandidateBuildConfig(
        tau=int(feature_cfg.get("tau", 2)),
        max_path_len=int(feature_cfg.get("max_path_len", 2)),
        max_neighbors_per_mediator=int(feature_cfg.get("max_neighbors_per_mediator", 120)),
        alpha=float(score_cfg.get("alpha", 0.5)),
        beta=float(score_cfg.get("beta", 0.2)),
        gamma=float(score_cfg.get("gamma", 0.3)),
        delta=float(score_cfg.get("delta", 0.2)),
    )

    structural_cfgs = make_structural_configs(base_cfg)
    split = max(1, len(cutoff_years) // 2)
    tune_years = cutoff_years[:split]
    eval_years = cutoff_years[split:] if split < len(cutoff_years) else cutoff_years

    pref_rankings: dict[int, pd.DataFrame] = {}
    feature_cache: dict[tuple[str, int], pd.DataFrame] = {}
    leakage_rows: list[dict] = []
    for t in cutoff_years:
        train = corpus_df[corpus_df["year"] <= (t - 1)]
        pref_rankings[t] = pref_attach_ranking(train, all_pairs_df=all_pairs)
        for h in horizons:
            leakage_rows.append({"cutoff_year_t": int(t), "horizon": int(h), "no_leakage": check_no_leakage(corpus_df, t, h, first_year)})
        for cfg_name, cfg in structural_cfgs:
            feature_cache[(cfg_name, t)] = build_candidate_table(train, cutoff_t=t, cfg=cfg)

    def evaluate_cfg(
        cfg_name: str,
        cfg: CandidateBuildConfig,
        years: list[int],
        cache_key_name: str | None = None,
    ) -> pd.DataFrame:
        rows: list[dict] = []
        cache_name = cache_key_name or cfg_name
        for t in years:
            ranking = score_with_coefficients(feature_cache[(cache_name, t)], cfg)
            pref = pref_rankings[t]
            for h in horizons:
                future = future_edges_for(first_year, cutoff_t=t, horizon_h=h)
                m = evaluate_ranking(ranking, future, k=100)
                p = evaluate_ranking(pref, future, k=100)
                rows.append(
                    {
                        "config_name": cfg_name,
                        "cutoff_year_t": int(t),
                        "horizon": int(h),
                        "recall_at_100": float(m["recall_at_100"]),
                        "mrr": float(m["mrr"]),
                        "pref_recall_at_100": float(p["recall_at_100"]),
                        "pref_mrr": float(p["mrr"]),
                    }
                )
        return pd.DataFrame(rows)

    # Evaluate structural configs with defaults.
    all_cutoff_rows: list[pd.DataFrame] = []
    for cfg_name, cfg in structural_cfgs:
        all_cutoff_rows.append(evaluate_cfg(cfg_name, cfg, years=eval_years))

    # Tune coefficients on full structural config (plus_cooc_trend), then evaluate.
    full_name, full_cfg = structural_cfgs[-1]
    trials = sample_weight_trials(n_weight_trials, seed=seed)
    best_score = -np.inf
    best_cfg = CandidateBuildConfig(**asdict(full_cfg))
    for alpha, beta, gamma, delta, eta in trials:
        trial_cfg = CandidateBuildConfig(**asdict(full_cfg))
        trial_cfg.alpha = alpha
        trial_cfg.beta = beta
        trial_cfg.gamma = gamma
        trial_cfg.delta = delta
        trial_cfg.cooc_trend_coef = eta
        tune_eval = evaluate_cfg(full_name, trial_cfg, years=tune_years)
        if tune_eval.empty:
            continue
        obj = float(tune_eval["mrr"].mean() + tune_eval["recall_at_100"].mean())
        if obj > best_score:
            best_score = obj
            best_cfg = trial_cfg

    tuned_eval = evaluate_cfg("full_optimized", best_cfg, years=eval_years, cache_key_name=full_name)
    all_cutoff_rows.append(tuned_eval)

    # Baseline rows.
    pref_rows: list[dict] = []
    for t in eval_years:
        pref = pref_rankings[t]
        for h in horizons:
            future = future_edges_for(first_year, cutoff_t=t, horizon_h=h)
            p = evaluate_ranking(pref, future, k=100)
            pref_rows.append(
                {
                    "config_name": "pref_attach",
                    "cutoff_year_t": int(t),
                    "horizon": int(h),
                    "recall_at_100": float(p["recall_at_100"]),
                    "mrr": float(p["mrr"]),
                    "pref_recall_at_100": float(p["recall_at_100"]),
                    "pref_mrr": float(p["mrr"]),
                }
            )
    cutoff_df = pd.concat(all_cutoff_rows + [pd.DataFrame(pref_rows)], ignore_index=True)

    summary = (
        cutoff_df.groupby(["config_name", "horizon"], as_index=False)
        .agg(
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
            pref_recall_at_100=("pref_recall_at_100", "mean"),
            pref_mrr=("pref_mrr", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "mean_mrr"], ascending=[True, False])
    )
    summary["delta_recall_at_100_vs_pref"] = summary["mean_recall_at_100"] - summary["pref_recall_at_100"]
    summary["delta_mrr_vs_pref"] = summary["mean_mrr"] - summary["pref_mrr"]

    win = (
        cutoff_df.groupby(["config_name", "horizon"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "win_rate_recall": float((g["recall_at_100"] >= g["pref_recall_at_100"]).mean()),
                    "win_rate_mrr": float((g["mrr"] >= g["pref_mrr"]).mean()),
                    "win_rate_both": float(
                        ((g["recall_at_100"] >= g["pref_recall_at_100"]) & (g["mrr"] >= g["pref_mrr"])).mean()
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    summary = summary.merge(win, on=["config_name", "horizon"], how="left")
    summary["tune_years"] = ",".join(str(y) for y in tune_years)
    summary["eval_years"] = ",".join(str(y) for y in eval_years)

    # Attach config payloads.
    cfg_payloads = {name: asdict(cfg) for name, cfg in structural_cfgs}
    cfg_payloads["full_optimized"] = asdict(best_cfg)
    cfg_payloads["pref_attach"] = {"baseline": "preferential_attachment"}
    summary["config_json"] = summary["config_name"].map(lambda x: json.dumps(cfg_payloads.get(x, {}), ensure_ascii=True))

    # Success summary text.
    full_summary = summary[summary["config_name"] == "full_optimized"].copy()
    if full_summary.empty:
        verdict = "No optimized model summary available."
    else:
        per_h = []
        pass_count = 0
        for row in full_summary.itertuples(index=False):
            ok = (float(row.delta_recall_at_100_vs_pref) >= 0) and (float(row.delta_mrr_vs_pref) >= 0)
            if ok:
                pass_count += 1
            per_h.append(
                f"- horizon {int(row.horizon)}: "
                f"delta_recall@100={float(row.delta_recall_at_100_vs_pref):.6f}, "
                f"delta_mrr={float(row.delta_mrr_vs_pref):.6f}, pass={ok}"
            )
        overall = pass_count >= max(1, int(np.ceil(len(full_summary) / 2)))
        verdict = "\n".join(
            [
                f"Optimized model beats-or-matches pref_attach on both metrics in {pass_count}/{len(full_summary)} horizons.",
                f"Success criterion met (most horizons): {overall}",
                *per_h,
            ]
        )

    leakage_df = pd.DataFrame(leakage_rows)
    return summary, cfg_payloads, verdict + "\n\nLeakage audit:\n" + leakage_df.to_string(index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run model-improvement ablations and select best config.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="1,3,5")
    parser.add_argument("--n_weight_trials", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus = load_corpus(args.corpus_path)
    cfg = load_config(args.config_path)
    horizons = parse_horizons(args.horizons)
    min_y, max_y = int(corpus["year"].min()), int(corpus["year"].max())
    years = parse_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons))
    if not years:
        raise SystemExit("No valid cutoff years available for model search.")

    summary, payloads, win_text = run_model_search(
        corpus_df=corpus,
        config=cfg,
        cutoff_years=years,
        horizons=horizons,
        n_weight_trials=args.n_weight_trials,
        seed=args.seed,
    )

    pq = out_dir / "ablation_grid.parquet"
    csv = out_dir / "ablation_grid.csv"
    summary.to_parquet(pq, index=False)
    summary.to_csv(csv, index=False)

    best_cfg_path = out_dir / "best_config.yaml"
    best_payload = payloads.get("full_optimized") or payloads.get("plus_cooc_trend") or {}
    with best_cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(best_payload, f, sort_keys=True)

    win_path = out_dir / "win_loss_summary.md"
    win_path.write_text("# Win/Loss Summary\n\n" + win_text + "\n", encoding="utf-8")

    print(f"Wrote: {pq}")
    print(f"Wrote: {csv}")
    print(f"Wrote: {best_cfg_path}")
    print(f"Wrote: {win_path}")


if __name__ == "__main__":
    main()
