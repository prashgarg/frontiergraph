from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.analysis.common import CandidateBuildConfig, build_candidate_table, ensure_output_dir, first_appearance_map
from src.analysis.ranking_utils import (
    build_all_pairs,
    candidate_cfg_from_config,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
    pref_attach_ranking,
)
from src.utils import load_config, load_corpus, pair_key


def _future_set(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {edge for edge, y in first_year_map.items() if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)}


def _boundary_set(
    edges: set[tuple[str, str]],
    cooc_positive_pairs: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for u, v in edges:
        if str(u)[:1] == str(v)[:1]:
            continue
        if pair_key(str(u), str(v)) in cooc_positive_pairs:
            continue
        out.add((str(u), str(v)))
    return out


def _cooc_positive_pair_set(train_df: pd.DataFrame) -> set[tuple[str, str]]:
    paper_nodes = (
        pd.concat(
            [
                train_df[["paper_id", "year", "src_code"]].rename(columns={"src_code": "code"}),
                train_df[["paper_id", "year", "dst_code"]].rename(columns={"dst_code": "code"}),
            ],
            ignore_index=True,
        )
        .dropna(subset=["paper_id", "code"])
        .astype({"paper_id": str, "code": str})
    )
    node_sets = paper_nodes.groupby("paper_id")["code"].apply(lambda s: sorted(set(s))).tolist()
    pairs: set[tuple[str, str]] = set()
    for nodes in node_sets:
        n = len(nodes)
        for i in range(n):
            ui = nodes[i]
            for j in range(i + 1, n):
                pairs.add(pair_key(ui, nodes[j]))
    return pairs


def _score_with_trial(feature_df: pd.DataFrame, params: dict[str, float]) -> pd.DataFrame:
    g = feature_df.copy()
    if g.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank"])
    for col in ["cooc_trend_norm", "field_same_group"]:
        if col not in g.columns:
            g[col] = 0.0
    g["score"] = (
        float(params["alpha"]) * g["path_support_norm"].astype(float)
        + float(params["beta"]) * g["gap_bonus"].astype(float)
        + float(params["gamma"]) * g["motif_bonus_norm"].astype(float)
        - float(params["delta"]) * g["hub_penalty"].astype(float)
        + float(params["cooc_trend_coef"]) * g["cooc_trend_norm"].astype(float)
        - float(params["field_hub_penalty_scale"])
        * g["hub_penalty"].astype(float)
        * g["field_same_group"].astype(float)
    )
    g = g.sort_values("score", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1
    return g


def _boundary_recall_at_k(
    ranking_df: pd.DataFrame,
    boundary_edges: set[tuple[str, str]],
    k: int,
) -> float:
    if not boundary_edges:
        return 0.0
    top = ranking_df.head(int(k))
    hits = 0
    for r in top[["u", "v"]].itertuples(index=False):
        if (str(r.u), str(r.v)) in boundary_edges:
            hits += 1
    return float(hits) / float(len(boundary_edges))


def _trial_objective(panel_df: pd.DataFrame) -> float:
    if panel_df.empty:
        return float("-inf")
    # Emphasize long horizons and boundary recovery.
    return float(
        (
            0.45 * panel_df["delta_recall_at_100"].astype(float)
            + 0.25 * (10.0 * panel_df["delta_mrr"].astype(float))
            + 0.30 * panel_df["delta_boundary_recall_at_100"].astype(float)
        ).mean()
    )


def _evaluate_panel(
    params: dict[str, float],
    years: list[int],
    horizons: list[int],
    k_ref: int,
    feature_cache: dict[int, pd.DataFrame],
    pref_cache: dict[int, pd.DataFrame],
    future_map: dict[tuple[int, int], set[tuple[str, str]]],
    boundary_map: dict[tuple[int, int], set[tuple[str, str]]],
) -> pd.DataFrame:
    rows: list[dict] = []
    for t in years:
        ranked = _score_with_trial(feature_cache[int(t)], params)
        pref_ranked = pref_cache[int(t)]
        if ranked.empty or pref_ranked.empty:
            continue
        for h in horizons:
            positives = future_map.get((int(t), int(h)), set())
            if not positives:
                continue
            boundaries = boundary_map.get((int(t), int(h)), set())
            main_m = evaluate_binary_ranking(ranked, positives=positives, k_values=[int(k_ref)])
            pref_m = evaluate_binary_ranking(pref_ranked, positives=positives, k_values=[int(k_ref)])
            row = {
                "cutoff_year_t": int(t),
                "horizon": int(h),
                "recall_at_100_main": float(main_m.get(f"recall_at_{int(k_ref)}", 0.0)),
                "recall_at_100_pref": float(pref_m.get(f"recall_at_{int(k_ref)}", 0.0)),
                "delta_recall_at_100": float(main_m.get(f"recall_at_{int(k_ref)}", 0.0))
                - float(pref_m.get(f"recall_at_{int(k_ref)}", 0.0)),
                "mrr_main": float(main_m.get("mrr", 0.0)),
                "mrr_pref": float(pref_m.get("mrr", 0.0)),
                "delta_mrr": float(main_m.get("mrr", 0.0)) - float(pref_m.get("mrr", 0.0)),
                "boundary_recall_at_100_main": _boundary_recall_at_k(ranked, boundaries, k=int(k_ref)),
                "boundary_recall_at_100_pref": _boundary_recall_at_k(pref_ranked, boundaries, k=int(k_ref)),
                "n_future_edges": int(len(positives)),
                "n_boundary_future_edges": int(len(boundaries)),
            }
            row["delta_boundary_recall_at_100"] = (
                float(row["boundary_recall_at_100_main"]) - float(row["boundary_recall_at_100_pref"])
            )
            rows.append(row)
    return pd.DataFrame(rows)


def _sample_trials(base_cfg: CandidateBuildConfig, n_trials: int, seed: int) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    base_w = np.array([max(float(base_cfg.alpha), 1e-4), max(float(base_cfg.beta), 1e-4), max(float(base_cfg.gamma), 1e-4)])
    base_w = base_w / base_w.sum()
    out: list[dict[str, float]] = []
    # Include base weights first.
    out.append(
        {
            "alpha": float(base_cfg.alpha),
            "beta": float(base_cfg.beta),
            "gamma": float(base_cfg.gamma),
            "delta": float(base_cfg.delta),
            "cooc_trend_coef": float(base_cfg.cooc_trend_coef),
            "field_hub_penalty_scale": float(base_cfg.field_hub_penalty_scale),
        }
    )
    conc = np.maximum(base_w * 45.0, 0.5)
    for _ in range(max(0, int(n_trials) - 1)):
        w = rng.dirichlet(conc)
        out.append(
            {
                "alpha": float(w[0]),
                "beta": float(w[1]),
                "gamma": float(w[2]),
                "delta": float(np.clip(rng.normal(float(base_cfg.delta), 0.05), 0.01, 0.60)),
                "cooc_trend_coef": float(np.clip(rng.normal(float(base_cfg.cooc_trend_coef), 0.06), 0.0, 0.80)),
                "field_hub_penalty_scale": float(
                    np.clip(rng.normal(float(base_cfg.field_hub_penalty_scale), 0.06), 0.0, 0.80)
                ),
            }
        )
    return out


def _aggregate_eval(panel_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    out = (
        panel_df.groupby("horizon", as_index=False)
        .agg(
            mean_delta_recall_at_100=("delta_recall_at_100", "mean"),
            mean_delta_mrr=("delta_mrr", "mean"),
            mean_delta_boundary_recall_at_100=("delta_boundary_recall_at_100", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values("horizon")
    )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Targeted long-horizon + boundary model search.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--n_trials", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--overwrite_best", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    cfg = load_config(args.config_path)
    base_cfg = candidate_cfg_from_config(cfg, best_config_path=args.best_config_path)

    horizons = parse_horizons(args.horizons, default=[5, 10, 15])
    min_y, max_y = int(corpus_df["year"].min()), int(corpus_df["year"].max())
    years = parse_cutoff_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons), step=1)
    if len(years) < 4:
        raise SystemExit("Need at least 4 valid cutoff years for targeted search.")
    split = max(2, int(np.ceil(len(years) * 0.6)))
    tune_years = years[:split]
    eval_years = years[split:] if split < len(years) else years[-2:]
    k_ref = 100

    first_year = first_appearance_map(corpus_df)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(all_nodes)
    feature_cache: dict[int, pd.DataFrame] = {}
    pref_cache: dict[int, pd.DataFrame] = {}
    cooc_pair_cache: dict[int, set[tuple[str, str]]] = {}
    for t in years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        feature_cache[int(t)] = build_candidate_table(train, cutoff_t=int(t), cfg=base_cfg)
        pref_cache[int(t)] = pref_attach_ranking(train, all_pairs_df=all_pairs)
        cooc_pair_cache[int(t)] = _cooc_positive_pair_set(train)

    future_map: dict[tuple[int, int], set[tuple[str, str]]] = {}
    boundary_map: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for t in years:
        for h in horizons:
            fset = _future_set(first_year, cutoff_t=int(t), horizon_h=int(h))
            bset = _boundary_set(fset, cooc_positive_pairs=cooc_pair_cache[int(t)])
            future_map[(int(t), int(h))] = fset
            boundary_map[(int(t), int(h))] = bset

    trial_params = _sample_trials(base_cfg, n_trials=args.n_trials, seed=args.seed)
    trial_rows: list[dict] = []
    best_trial: dict | None = None
    best_score = float("-inf")
    best_eval_panel = pd.DataFrame()
    for idx, p in enumerate(trial_params):
        tune_panel = _evaluate_panel(
            p,
            years=tune_years,
            horizons=horizons,
            k_ref=k_ref,
            feature_cache=feature_cache,
            pref_cache=pref_cache,
            future_map=future_map,
            boundary_map=boundary_map,
        )
        eval_panel = _evaluate_panel(
            p,
            years=eval_years,
            horizons=horizons,
            k_ref=k_ref,
            feature_cache=feature_cache,
            pref_cache=pref_cache,
            future_map=future_map,
            boundary_map=boundary_map,
        )
        tune_obj = _trial_objective(tune_panel)
        eval_obj = _trial_objective(eval_panel)
        row = {
            "trial_id": int(idx),
            "alpha": float(p["alpha"]),
            "beta": float(p["beta"]),
            "gamma": float(p["gamma"]),
            "delta": float(p["delta"]),
            "cooc_trend_coef": float(p["cooc_trend_coef"]),
            "field_hub_penalty_scale": float(p["field_hub_penalty_scale"]),
            "tune_objective": float(tune_obj),
            "eval_objective": float(eval_obj),
            "tune_rows": int(len(tune_panel)),
            "eval_rows": int(len(eval_panel)),
        }
        trial_rows.append(row)
        if tune_obj > best_score:
            best_score = tune_obj
            best_trial = row
            best_eval_panel = eval_panel.copy()

    trials_df = pd.DataFrame(trial_rows).sort_values("tune_objective", ascending=False).reset_index(drop=True)
    if best_trial is None:
        raise SystemExit("Targeted search failed to produce a valid trial.")

    best_cfg = CandidateBuildConfig(**asdict(base_cfg))
    best_cfg.alpha = float(best_trial["alpha"])
    best_cfg.beta = float(best_trial["beta"])
    best_cfg.gamma = float(best_trial["gamma"])
    best_cfg.delta = float(best_trial["delta"])
    best_cfg.cooc_trend_coef = float(best_trial["cooc_trend_coef"])
    best_cfg.field_hub_penalty_scale = float(best_trial["field_hub_penalty_scale"])

    eval_summary = _aggregate_eval(best_eval_panel)
    pass_rate = (
        ((eval_summary["mean_delta_recall_at_100"] >= 0) & (eval_summary["mean_delta_mrr"] >= 0)).mean()
        if not eval_summary.empty
        else 0.0
    )
    win_text = [
        "# Targeted Long-Horizon Search Summary",
        "",
        f"- tune_years: {','.join(str(y) for y in tune_years)}",
        f"- eval_years: {','.join(str(y) for y in eval_years)}",
        f"- horizons: {','.join(str(h) for h in horizons)}",
        f"- best trial id: {int(best_trial['trial_id'])}",
        f"- tune objective: {float(best_trial['tune_objective']):.8f}",
        f"- eval objective: {float(best_trial['eval_objective']):.8f}",
        f"- win share (delta recall>=0 and delta mrr>=0): {float(pass_rate):.2f}",
        "",
    ]
    if not eval_summary.empty:
        for r in eval_summary.itertuples(index=False):
            win_text.append(
                f"- h={int(r.horizon)}: delta_recall@100={float(r.mean_delta_recall_at_100):.6f}, "
                f"delta_mrr={float(r.mean_delta_mrr):.6f}, "
                f"delta_boundary_recall@100={float(r.mean_delta_boundary_recall_at_100):.6f}"
            )

    trial_pq = out_dir / "targeted_trials.parquet"
    trial_csv = out_dir / "targeted_trials.csv"
    panel_pq = out_dir / "targeted_eval_panel.parquet"
    panel_csv = out_dir / "targeted_eval_panel.csv"
    sum_pq = out_dir / "targeted_eval_summary.parquet"
    sum_csv = out_dir / "targeted_eval_summary.csv"
    best_yaml = out_dir / "targeted_best_config.yaml"
    summary_md = out_dir / "targeted_win_loss_summary.md"

    trials_df.to_parquet(trial_pq, index=False)
    trials_df.to_csv(trial_csv, index=False)
    best_eval_panel.to_parquet(panel_pq, index=False)
    best_eval_panel.to_csv(panel_csv, index=False)
    eval_summary.to_parquet(sum_pq, index=False)
    eval_summary.to_csv(sum_csv, index=False)
    with best_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(best_cfg), f, sort_keys=True)
    summary_md.write_text("\n".join(win_text) + "\n", encoding="utf-8")

    if args.overwrite_best:
        dest = Path(args.best_config_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as f:
            yaml.safe_dump(asdict(best_cfg), f, sort_keys=True)
        print(f"Overwrote best config: {dest}")

    print(f"Wrote: {trial_pq}")
    print(f"Wrote: {trial_csv}")
    print(f"Wrote: {panel_pq}")
    print(f"Wrote: {panel_csv}")
    print(f"Wrote: {sum_pq}")
    print(f"Wrote: {sum_csv}")
    print(f"Wrote: {best_yaml}")
    print(f"Wrote: {summary_md}")


if __name__ == "__main__":
    main()
