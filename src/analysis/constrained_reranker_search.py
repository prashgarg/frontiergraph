from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.analysis.common import CandidateBuildConfig, build_candidate_table, ensure_output_dir, first_appearance_map
from src.analysis.ranking_utils import (
    apply_boundary_rerank,
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


def _cooc_positive_pair_set(train_df: pd.DataFrame) -> set[tuple[str, str]]:
    paper_nodes = (
        pd.concat(
            [
                train_df[["paper_id", "src_code"]].rename(columns={"src_code": "code"}),
                train_df[["paper_id", "dst_code"]].rename(columns={"dst_code": "code"}),
            ],
            ignore_index=True,
        )
        .dropna(subset=["paper_id", "code"])
        .astype({"paper_id": str, "code": str})
    )
    sets = paper_nodes.groupby("paper_id")["code"].apply(lambda s: sorted(set(s))).tolist()
    out: set[tuple[str, str]] = set()
    for nodes in sets:
        n = len(nodes)
        for i in range(n):
            ui = nodes[i]
            for j in range(i + 1, n):
                out.add(pair_key(ui, nodes[j]))
    return out


def _boundary_set(
    edges: set[tuple[str, str]],
    cooc_pairs: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for u, v in edges:
        if str(u)[:1] == str(v)[:1]:
            continue
        if pair_key(str(u), str(v)) in cooc_pairs:
            continue
        out.add((str(u), str(v)))
    return out


def _score_from_params(feature_df: pd.DataFrame, p: dict[str, float]) -> pd.DataFrame:
    g = feature_df.copy()
    if g.empty:
        return pd.DataFrame(columns=["u", "v", "score", "rank", "cooc_count"])
    for col in ["cooc_trend_norm", "field_same_group", "hub_penalty", "path_support_norm", "gap_bonus", "motif_bonus_norm"]:
        if col not in g.columns:
            g[col] = 0.0
    g["score"] = (
        float(p["alpha"]) * g["path_support_norm"].astype(float)
        + float(p["beta"]) * g["gap_bonus"].astype(float)
        + float(p["gamma"]) * g["motif_bonus_norm"].astype(float)
        - float(p["delta"]) * g["hub_penalty"].astype(float)
        + float(p["cooc_trend_coef"]) * g["cooc_trend_norm"].astype(float)
        - float(p["field_hub_penalty_scale"]) * g["hub_penalty"].astype(float) * g["field_same_group"].astype(float)
    )
    out = g[
        [c for c in ["u", "v", "score", "cooc_count", "path_support_norm", "motif_bonus_norm", "gap_bonus", "hub_penalty"] if c in g.columns]
    ].copy()
    return out


def _boundary_recall_at_k(ranking_df: pd.DataFrame, boundary_edges: set[tuple[str, str]], k: int) -> float:
    if not boundary_edges:
        return 0.0
    top = ranking_df.head(int(k))
    hits = 0
    for r in top[["u", "v"]].itertuples(index=False):
        if (str(r.u), str(r.v)) in boundary_edges:
            hits += 1
    return float(hits) / float(len(boundary_edges))


def _eval_panel(
    weight_params: dict[str, float],
    boundary_bonus: float,
    boundary_quota: float,
    years: list[int],
    horizons: list[int],
    k_ref: int,
    feature_cache: dict[int, pd.DataFrame],
    pref_cache: dict[int, pd.DataFrame],
    future_map: dict[tuple[int, int], set[tuple[str, str]]],
    boundary_map: dict[tuple[int, int], set[tuple[str, str]]],
    quota_max_rank: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for t in years:
        scored = _score_from_params(feature_cache[int(t)], weight_params)
        if scored.empty:
            continue
        ranked = apply_boundary_rerank(
            scored,
            boundary_bonus=float(boundary_bonus),
            boundary_quota=float(boundary_quota),
            quota_max_rank=int(quota_max_rank),
        )
        pref_ranked = pref_cache[int(t)]
        if ranked.empty or pref_ranked.empty:
            continue
        for h in horizons:
            pos = future_map.get((int(t), int(h)), set())
            if not pos:
                continue
            bpos = boundary_map.get((int(t), int(h)), set())
            main_m = evaluate_binary_ranking(ranked, positives=pos, k_values=[int(k_ref)])
            pref_m = evaluate_binary_ranking(pref_ranked, positives=pos, k_values=[int(k_ref)])
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
                "boundary_recall_at_100_main": _boundary_recall_at_k(ranked, bpos, k=int(k_ref)),
                "boundary_recall_at_100_pref": _boundary_recall_at_k(pref_ranked, bpos, k=int(k_ref)),
                "n_future_edges": int(len(pos)),
                "n_boundary_future_edges": int(len(bpos)),
            }
            row["delta_boundary_recall_at_100"] = (
                float(row["boundary_recall_at_100_main"]) - float(row["boundary_recall_at_100_pref"])
            )
            rows.append(row)
    return pd.DataFrame(rows)


def _agg(panel_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame()
    return (
        panel_df.groupby("horizon", as_index=False)
        .agg(
            mean_delta_recall_at_100=("delta_recall_at_100", "mean"),
            mean_delta_mrr=("delta_mrr", "mean"),
            mean_delta_boundary_recall_at_100=("delta_boundary_recall_at_100", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values("horizon")
    )


def _objective(panel_df: pd.DataFrame) -> float:
    if panel_df.empty:
        return float("-inf")
    return float(
        (
            0.40 * panel_df["delta_recall_at_100"].astype(float)
            + 0.20 * (10.0 * panel_df["delta_mrr"].astype(float))
            + 0.40 * panel_df["delta_boundary_recall_at_100"].astype(float)
        ).mean()
    )


def _constraint_flags(
    agg_df: pd.DataFrame,
    min_overall_pass_horizons: int,
    min_boundary_pass_horizons: int,
) -> tuple[bool, int, int]:
    if agg_df.empty:
        return False, 0, 0
    overall_pass = int(
        ((agg_df["mean_delta_recall_at_100"] >= 0) & (agg_df["mean_delta_mrr"] >= 0)).sum()
    )
    boundary_pass = int((agg_df["mean_delta_boundary_recall_at_100"] >= 0).sum())
    ok = (overall_pass >= int(min_overall_pass_horizons)) and (boundary_pass >= int(min_boundary_pass_horizons))
    return ok, overall_pass, boundary_pass


def _load_weight_trials(
    base_cfg: CandidateBuildConfig,
    targeted_trials_path: str | None,
    top_n: int,
    seed: int,
) -> list[dict[str, float]]:
    cols = ["alpha", "beta", "gamma", "delta", "cooc_trend_coef", "field_hub_penalty_scale"]
    trials: list[dict[str, float]] = []
    if targeted_trials_path and Path(targeted_trials_path).exists():
        df = pd.read_csv(targeted_trials_path).sort_values("tune_objective", ascending=False).head(int(top_n))
        for r in df.itertuples(index=False):
            trials.append(
                {
                    "alpha": float(r.alpha),
                    "beta": float(r.beta),
                    "gamma": float(r.gamma),
                    "delta": float(r.delta),
                    "cooc_trend_coef": float(r.cooc_trend_coef),
                    "field_hub_penalty_scale": float(r.field_hub_penalty_scale),
                }
            )
    if trials:
        return trials

    rng = np.random.default_rng(seed)
    base = np.array([max(float(base_cfg.alpha), 1e-4), max(float(base_cfg.beta), 1e-4), max(float(base_cfg.gamma), 1e-4)])
    base = base / base.sum()
    conc = np.maximum(base * 35.0, 0.5)
    trials.append(
        {
            "alpha": float(base_cfg.alpha),
            "beta": float(base_cfg.beta),
            "gamma": float(base_cfg.gamma),
            "delta": float(base_cfg.delta),
            "cooc_trend_coef": float(base_cfg.cooc_trend_coef),
            "field_hub_penalty_scale": float(base_cfg.field_hub_penalty_scale),
        }
    )
    for _ in range(max(0, int(top_n) - 1)):
        w = rng.dirichlet(conc)
        trials.append(
            {
                "alpha": float(w[0]),
                "beta": float(w[1]),
                "gamma": float(w[2]),
                "delta": float(np.clip(rng.normal(float(base_cfg.delta), 0.05), 0.01, 0.60)),
                "cooc_trend_coef": float(np.clip(rng.normal(float(base_cfg.cooc_trend_coef), 0.05), 0.0, 0.80)),
                "field_hub_penalty_scale": float(np.clip(rng.normal(float(base_cfg.field_hub_penalty_scale), 0.05), 0.0, 0.80)),
            }
        )
    return trials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Constrained boundary-aware reranker search.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--targeted_trials", default="outputs/paper/03_model_search_targeted/targeted_trials.csv")
    parser.add_argument("--top_weight_trials", type=int, default=12)
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--k_ref", type=int, default=100)
    parser.add_argument("--boundary_bonus_grid", nargs="+", type=float, default=[0.0, 0.01, 0.02, 0.05, 0.10, 0.15])
    parser.add_argument("--boundary_quota_grid", nargs="+", type=float, default=[0.00, 0.02, 0.05, 0.10, 0.15, 0.20])
    parser.add_argument("--quota_max_rank", type=int, default=1000)
    parser.add_argument("--min_overall_pass_horizons", type=int, default=2)
    parser.add_argument("--min_boundary_pass_horizons", type=int, default=1)
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
        raise SystemExit("Need at least 4 valid cutoff years for constrained search.")
    split = max(2, int(np.ceil(len(years) * 0.6)))
    tune_years = years[:split]
    eval_years = years[split:] if split < len(years) else years[-2:]

    weight_trials = _load_weight_trials(
        base_cfg=base_cfg,
        targeted_trials_path=args.targeted_trials,
        top_n=int(args.top_weight_trials),
        seed=int(args.seed),
    )

    first_year = first_appearance_map(corpus_df)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(all_nodes)
    feature_cache: dict[int, pd.DataFrame] = {}
    pref_cache: dict[int, pd.DataFrame] = {}
    cooc_pairs_cache: dict[int, set[tuple[str, str]]] = {}
    for t in years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        feature_cache[int(t)] = build_candidate_table(train, cutoff_t=int(t), cfg=base_cfg)
        pref_cache[int(t)] = pref_attach_ranking(train, all_pairs_df=all_pairs)
        cooc_pairs_cache[int(t)] = _cooc_positive_pair_set(train)

    future_map: dict[tuple[int, int], set[tuple[str, str]]] = {}
    boundary_map: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for t in years:
        for h in horizons:
            fset = _future_set(first_year, cutoff_t=int(t), horizon_h=int(h))
            future_map[(int(t), int(h))] = fset
            boundary_map[(int(t), int(h))] = _boundary_set(fset, cooc_pairs_cache[int(t)])

    trial_rows: list[dict] = []
    best_feasible: dict | None = None
    best_feasible_tune_obj = float("-inf")
    best_fallback: dict | None = None
    best_fallback_score = float("-inf")
    best_eval_panel = pd.DataFrame()

    trial_id = 0
    for wp in weight_trials:
        for bb in sorted(set(float(x) for x in args.boundary_bonus_grid)):
            for bq in sorted(set(float(x) for x in args.boundary_quota_grid)):
                tune_panel = _eval_panel(
                    wp,
                    boundary_bonus=float(bb),
                    boundary_quota=float(bq),
                    years=tune_years,
                    horizons=horizons,
                    k_ref=int(args.k_ref),
                    feature_cache=feature_cache,
                    pref_cache=pref_cache,
                    future_map=future_map,
                    boundary_map=boundary_map,
                    quota_max_rank=int(args.quota_max_rank),
                )
                eval_panel = _eval_panel(
                    wp,
                    boundary_bonus=float(bb),
                    boundary_quota=float(bq),
                    years=eval_years,
                    horizons=horizons,
                    k_ref=int(args.k_ref),
                    feature_cache=feature_cache,
                    pref_cache=pref_cache,
                    future_map=future_map,
                    boundary_map=boundary_map,
                    quota_max_rank=int(args.quota_max_rank),
                )
                tune_agg = _agg(tune_panel)
                eval_agg = _agg(eval_panel)
                tune_obj = _objective(tune_panel)
                eval_obj = _objective(eval_panel)
                feasible, overall_pass, boundary_pass = _constraint_flags(
                    tune_agg,
                    min_overall_pass_horizons=int(args.min_overall_pass_horizons),
                    min_boundary_pass_horizons=int(args.min_boundary_pass_horizons),
                )
                row = {
                    "trial_id": int(trial_id),
                    **{k: float(v) for k, v in wp.items()},
                    "boundary_bonus": float(bb),
                    "boundary_quota": float(bq),
                    "tune_objective": float(tune_obj),
                    "eval_objective": float(eval_obj),
                    "constraint_feasible": bool(feasible),
                    "tune_overall_pass_horizons": int(overall_pass),
                    "tune_boundary_pass_horizons": int(boundary_pass),
                    "tune_rows": int(len(tune_panel)),
                    "eval_rows": int(len(eval_panel)),
                }
                trial_rows.append(row)

                if feasible and tune_obj > best_feasible_tune_obj:
                    best_feasible_tune_obj = tune_obj
                    best_feasible = row
                    best_eval_panel = eval_panel.copy()
                # Penalized fallback if no feasible trial exists.
                penalized = float(tune_obj) + 0.02 * float(overall_pass) + 0.04 * float(boundary_pass)
                if penalized > best_fallback_score:
                    best_fallback_score = penalized
                    best_fallback = row
                trial_id += 1

    trials_df = pd.DataFrame(trial_rows).sort_values(["constraint_feasible", "tune_objective"], ascending=[False, False]).reset_index(drop=True)
    chosen = best_feasible if best_feasible is not None else best_fallback
    if chosen is None:
        raise SystemExit("No constrained reranker trial was evaluated.")

    if best_feasible is None:
        # Recompute eval panel for fallback pick.
        wp = {k: float(chosen[k]) for k in ["alpha", "beta", "gamma", "delta", "cooc_trend_coef", "field_hub_penalty_scale"]}
        best_eval_panel = _eval_panel(
            wp,
            boundary_bonus=float(chosen["boundary_bonus"]),
            boundary_quota=float(chosen["boundary_quota"]),
            years=eval_years,
            horizons=horizons,
            k_ref=int(args.k_ref),
            feature_cache=feature_cache,
            pref_cache=pref_cache,
            future_map=future_map,
            boundary_map=boundary_map,
            quota_max_rank=int(args.quota_max_rank),
        )

    eval_summary = _agg(best_eval_panel)
    frontier = (
        trials_df.groupby(["boundary_quota", "boundary_bonus"], as_index=False)
        .agg(
            max_tune_objective=("tune_objective", "max"),
            feasible_share=("constraint_feasible", "mean"),
            best_eval_objective=("eval_objective", "max"),
        )
        .sort_values(["feasible_share", "max_tune_objective"], ascending=[False, False])
    )

    best_cfg = CandidateBuildConfig(**asdict(base_cfg))
    for k in ["alpha", "beta", "gamma", "delta", "cooc_trend_coef", "field_hub_penalty_scale"]:
        setattr(best_cfg, k, float(chosen[k]))
    best_cfg.boundary_bonus = float(chosen["boundary_bonus"])
    best_cfg.boundary_quota = float(chosen["boundary_quota"])
    best_cfg.boundary_quota_max_rank = int(args.quota_max_rank)

    summary_lines = [
        "# Constrained Reranker Search Summary",
        "",
        f"- tune_years: {','.join(str(y) for y in tune_years)}",
        f"- eval_years: {','.join(str(y) for y in eval_years)}",
        f"- horizons: {','.join(str(h) for h in horizons)}",
        f"- selected trial id: {int(chosen['trial_id'])}",
        f"- selected is feasible under constraints: {bool(chosen['constraint_feasible'])}",
        f"- selected boundary_bonus: {float(chosen['boundary_bonus']):.6f}",
        f"- selected boundary_quota: {float(chosen['boundary_quota']):.6f}",
        f"- selected tune objective: {float(chosen['tune_objective']):.8f}",
        f"- selected eval objective: {float(chosen['eval_objective']):.8f}",
        "",
    ]
    if not eval_summary.empty:
        for r in eval_summary.itertuples(index=False):
            summary_lines.append(
                f"- h={int(r.horizon)}: delta_recall@100={float(r.mean_delta_recall_at_100):.6f}, "
                f"delta_mrr={float(r.mean_delta_mrr):.6f}, "
                f"delta_boundary_recall@100={float(r.mean_delta_boundary_recall_at_100):.6f}"
            )

    trials_pq = out_dir / "constrained_trials.parquet"
    trials_csv = out_dir / "constrained_trials.csv"
    panel_pq = out_dir / "constrained_eval_panel.parquet"
    panel_csv = out_dir / "constrained_eval_panel.csv"
    summary_pq = out_dir / "constrained_eval_summary.parquet"
    summary_csv = out_dir / "constrained_eval_summary.csv"
    frontier_csv = out_dir / "constrained_frontier.csv"
    best_yaml = out_dir / "constrained_best_config.yaml"
    summary_md = out_dir / "constrained_win_loss_summary.md"

    trials_df.to_parquet(trials_pq, index=False)
    trials_df.to_csv(trials_csv, index=False)
    best_eval_panel.to_parquet(panel_pq, index=False)
    best_eval_panel.to_csv(panel_csv, index=False)
    eval_summary.to_parquet(summary_pq, index=False)
    eval_summary.to_csv(summary_csv, index=False)
    frontier.to_csv(frontier_csv, index=False)
    with best_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(best_cfg), f, sort_keys=True)
    summary_md.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if args.overwrite_best:
        dest = Path(args.best_config_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as f:
            yaml.safe_dump(asdict(best_cfg), f, sort_keys=True)
        print(f"Overwrote best config: {dest}")

    print(f"Wrote: {trials_pq}")
    print(f"Wrote: {trials_csv}")
    print(f"Wrote: {panel_pq}")
    print(f"Wrote: {panel_csv}")
    print(f"Wrote: {summary_pq}")
    print(f"Wrote: {summary_csv}")
    print(f"Wrote: {frontier_csv}")
    print(f"Wrote: {best_yaml}")
    print(f"Wrote: {summary_md}")


if __name__ == "__main__":
    main()
