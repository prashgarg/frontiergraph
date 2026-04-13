from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map, restrict_positive_set_for_family
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    comparison_rankings_for_cutoff,
    main_ranking_for_cutoff,
    parse_cutoff_years,
    parse_horizons,
)
from src.utils import load_config, load_corpus


def classify_novelty(u: str, v: str, cooc_count: float | int | None) -> str:
    src_field = str(u)[:1]
    dst_field = str(v)[:1]
    cross = src_field != dst_field
    cooc = float(cooc_count) if cooc_count is not None and pd.notna(cooc_count) else 0.0
    zero_cooc = cooc <= 0
    if cross and zero_cooc:
        return "boundary_crossfield"
    if cross and not zero_cooc:
        return "gap_crossfield"
    if (not cross) and zero_cooc:
        return "boundary_internal"
    return "gap_internal"


def _future_positive_set(first_year_map: dict[tuple[str, str], int], cutoff_t: int, horizon_h: int) -> set[tuple[str, str]]:
    return {edge for edge, y in first_year_map.items() if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)}


def compute_gap_boundary_panel(
    corpus_df: pd.DataFrame,
    cfg: dict,
    cutoff_years: list[int],
    horizons: list[int],
    max_k: int,
) -> pd.DataFrame:
    if corpus_df.empty:
        return pd.DataFrame()
    tau = int(cfg.get("features", {}).get("tau", 2))
    candidate_cfg = candidate_cfg_from_config(cfg)
    first_year = first_appearance_map(
        corpus_df,
        candidate_kind=candidate_cfg.candidate_kind,
        candidate_family_mode=candidate_cfg.candidate_family_mode,
    )

    rows: list[dict] = []
    for t in cutoff_years:
        train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
        if train.empty:
            continue
        rankings = comparison_rankings_for_cutoff(train, cutoff_t=int(t), cfg=candidate_cfg, tau=tau)
        main_universe = rankings.get("main", pd.DataFrame(columns=["u", "v"]))
        for h in horizons:
            positives = _future_positive_set(first_year, cutoff_t=int(t), horizon_h=int(h))
            positives = restrict_positive_set_for_family(
                positives,
                candidate_pairs_df=main_universe,
                candidate_family_mode=candidate_cfg.candidate_family_mode,
            )
            for model, ranking in rankings.items():
                if ranking.empty:
                    continue
                sub = ranking.head(int(max_k)).copy()
                if sub.empty:
                    continue
                if "cooc_count" not in sub.columns:
                    sub["cooc_count"] = 0.0
                sub["src_field"] = sub["u"].astype(str).str[0]
                sub["dst_field"] = sub["v"].astype(str).str[0]
                sub["cross_field"] = (sub["src_field"] != sub["dst_field"]).astype(int)
                sub["novelty_type"] = [
                    classify_novelty(str(r.u), str(r.v), r.cooc_count) for r in sub[["u", "v", "cooc_count"]].itertuples(index=False)
                ]
                sub["realized_within_h"] = [
                    int((str(r.u), str(r.v)) in positives) for r in sub[["u", "v"]].itertuples(index=False)
                ]
                sub["first_realized_year"] = [
                    int(first_year[(str(r.u), str(r.v))]) if (str(r.u), str(r.v)) in positives else np.nan
                    for r in sub[["u", "v"]].itertuples(index=False)
                ]
                sub["time_to_fill"] = (
                    pd.to_numeric(sub["first_realized_year"], errors="coerce") - float(t)
                )
                sub["model"] = model
                sub["cutoff_year_t"] = int(t)
                sub["horizon"] = int(h)
                rows.extend(sub.to_dict(orient="records"))
    return pd.DataFrame(rows)


def summarize_gap_boundary(panel_df: pd.DataFrame, k_values: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    summary_rows: list[dict] = []
    mix_rows: list[dict] = []
    for k in sorted(set(int(x) for x in k_values)):
        sub_k = panel_df[panel_df["rank"] <= k].copy()
        if sub_k.empty:
            continue
        tbl = (
            sub_k.groupby(["model", "horizon", "novelty_type"], as_index=False)
            .agg(
                n_predictions=("u", "size"),
                realized_rate=("realized_within_h", "mean"),
                mean_rank=("rank", "mean"),
                mean_time_to_fill=("time_to_fill", "mean"),
                mean_score=("score", "mean"),
            )
            .sort_values(["horizon", "model", "novelty_type"])
        )
        tbl["k"] = int(k)
        summary_rows.append(tbl)

        mix = (
            sub_k.groupby(["model", "horizon", "novelty_type"], as_index=False)
            .agg(n=("u", "size"))
            .merge(
                sub_k.groupby(["model", "horizon"], as_index=False).agg(total=("u", "size")),
                on=["model", "horizon"],
                how="left",
            )
        )
        mix["share_in_top_k"] = mix["n"] / mix["total"].replace(0, np.nan)
        mix["k"] = int(k)
        mix_rows.append(mix)
    summary_df = pd.concat(summary_rows, ignore_index=True) if summary_rows else pd.DataFrame()
    mix_df = pd.concat(mix_rows, ignore_index=True) if mix_rows else pd.DataFrame()
    return summary_df, mix_df


def compare_main_vs_pref(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()
    m = summary_df[summary_df["model"] == "main"]
    p = summary_df[summary_df["model"] == "pref_attach"]
    if m.empty or p.empty:
        return pd.DataFrame()
    joined = m.merge(
        p,
        on=["horizon", "k", "novelty_type"],
        suffixes=("_main", "_pref"),
        how="inner",
    )
    if joined.empty:
        return pd.DataFrame()
    joined["delta_realized_rate_main_minus_pref"] = joined["realized_rate_main"] - joined["realized_rate_pref"]
    joined["delta_mean_time_to_fill_main_minus_pref"] = joined["mean_time_to_fill_main"] - joined["mean_time_to_fill_pref"]
    keep = [
        "horizon",
        "k",
        "novelty_type",
        "delta_realized_rate_main_minus_pref",
        "delta_mean_time_to_fill_main_minus_pref",
        "n_predictions_main",
        "n_predictions_pref",
    ]
    return joined[keep].sort_values(["horizon", "k", "novelty_type"]).reset_index(drop=True)


def plot_novelty_mix(mix_df: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_paths: list[Path] = []
    if mix_df.empty:
        return out_paths
    for k in sorted(mix_df["k"].unique()):
        sub = mix_df[mix_df["k"] == k].copy()
        if sub.empty:
            continue
        for horizon in sorted(sub["horizon"].unique()):
            sh = sub[sub["horizon"] == horizon]
            if sh.empty:
                continue
            pivot = sh.pivot_table(index="model", columns="novelty_type", values="share_in_top_k", fill_value=0.0)
            pivot = pivot.sort_index()
            ax = pivot.plot(kind="bar", stacked=True, figsize=(9, 5), colormap="tab20")
            ax.set_ylabel("Share of top-K")
            ax.set_title(f"Novelty Mix by Model (h={int(horizon)}, K={int(k)})")
            ax.legend(title="novelty_type", bbox_to_anchor=(1.02, 1), loc="upper left")
            plt.tight_layout()
            out = out_dir / f"gap_boundary_mix_h{int(horizon)}_k{int(k)}.png"
            plt.savefig(out, dpi=150)
            plt.close()
            out_paths.append(out)
    return out_paths


def write_hypothesis_brief(summary_df: pd.DataFrame, cmp_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Workstream 09: Gap vs Boundary Decomposition",
        "",
        "## Hypotheses",
        "1. Boundary-type candidates (especially cross-field + zero co-occurrence) fill more slowly than within-field gaps.",
        "2. Main ranking should allocate more useful mass to boundary opportunities than preferential attachment.",
        "3. A credible metascience account needs both gap exploitation and boundary exploration diagnostics.",
        "",
    ]
    if not summary_df.empty:
        lines.append("## Realization Snapshot")
        snap = summary_df[(summary_df["model"] == "main") & (summary_df["k"] == 100)].sort_values(
            ["horizon", "novelty_type"]
        )
        for r in snap.itertuples(index=False):
            lines.append(
                f"- h={int(r.horizon)} {r.novelty_type}: realized_rate={float(r.realized_rate):.6f}, "
                f"mean_time_to_fill={float(r.mean_time_to_fill):.3f}"
            )
        lines.append("")
    if not cmp_df.empty:
        boundary = cmp_df[cmp_df["novelty_type"].str.contains("boundary") & (cmp_df["k"] == 100)]
        if not boundary.empty:
            wins = int((boundary["delta_realized_rate_main_minus_pref"] > 0).sum())
            lines.append(
                f"- Main beats pref_attach on boundary realized-rate in {wins}/{len(boundary)} horizon-type comparisons (K=100)."
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gap-vs-boundary decomposition and realization analysis.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument("--max_k", type=int, default=1000)
    parser.add_argument("--k_values", type=int, nargs="+", default=[100, 500, 1000])
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    cfg = load_config(args.config_path)
    candidate_cfg = candidate_cfg_from_config(cfg, best_config_path=args.best_config_path)
    cfg["features"] = dict(cfg.get("features", {}))
    cfg["scoring"] = dict(cfg.get("scoring", {}))
    cfg["filters"] = dict(cfg.get("filters", {}))
    cfg["features"]["tau"] = int(candidate_cfg.tau)
    cfg["features"]["max_path_len"] = int(candidate_cfg.max_path_len)
    cfg["features"]["max_neighbors_per_mediator"] = int(candidate_cfg.max_neighbors_per_mediator)
    cfg["scoring"]["alpha"] = float(candidate_cfg.alpha)
    cfg["scoring"]["beta"] = float(candidate_cfg.beta)
    cfg["scoring"]["gamma"] = float(candidate_cfg.gamma)
    cfg["scoring"]["delta"] = float(candidate_cfg.delta)
    cfg["filters"]["causal_only"] = bool(candidate_cfg.causal_only)
    cfg["filters"]["min_stability"] = candidate_cfg.min_stability

    horizons = parse_horizons(args.horizons, default=[3, 5, 10])
    min_y, max_y = int(corpus_df["year"].min()), int(corpus_df["year"].max())
    years = parse_cutoff_years(args.years, min_year=min_y, max_year=max_y, max_h=max(horizons), step=1)
    if not years:
        raise SystemExit("No valid cutoff years available for gap-boundary analysis.")

    panel = compute_gap_boundary_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=years,
        horizons=horizons,
        max_k=int(args.max_k),
    )
    summary, mix = summarize_gap_boundary(panel, k_values=args.k_values)
    cmp_df = compare_main_vs_pref(summary)
    panel_pq = out_dir / "gap_boundary_panel.parquet"
    panel_csv = out_dir / "gap_boundary_panel.csv"
    sum_pq = out_dir / "gap_boundary_summary.parquet"
    sum_csv = out_dir / "gap_boundary_summary.csv"
    mix_pq = out_dir / "novelty_mix_by_model.parquet"
    mix_csv = out_dir / "novelty_mix_by_model.csv"
    cmp_pq = out_dir / "main_vs_pref_by_novelty.parquet"
    cmp_csv = out_dir / "main_vs_pref_by_novelty.csv"

    panel.to_parquet(panel_pq, index=False)
    panel.to_csv(panel_csv, index=False)
    summary.to_parquet(sum_pq, index=False)
    summary.to_csv(sum_csv, index=False)
    mix.to_parquet(mix_pq, index=False)
    mix.to_csv(mix_csv, index=False)
    cmp_df.to_parquet(cmp_pq, index=False)
    cmp_df.to_csv(cmp_csv, index=False)

    figs: list[Path] = []
    try:
        figs = plot_novelty_mix(mix, out_dir=out_dir)
    except Exception as exc:
        print(f"Warning: failed to render gap-boundary figures: {exc}")

    brief = out_dir / "hypotheses_and_tasks.md"
    try:
        write_hypothesis_brief(summary, cmp_df, brief)
    except Exception as exc:
        print(f"Warning: failed to write gap-boundary brief: {exc}")

    print(f"Wrote: {panel_pq}")
    print(f"Wrote: {panel_csv}")
    print(f"Wrote: {sum_pq}")
    print(f"Wrote: {sum_csv}")
    print(f"Wrote: {mix_pq}")
    print(f"Wrote: {mix_csv}")
    print(f"Wrote: {cmp_pq}")
    print(f"Wrote: {cmp_csv}")
    if brief.exists():
        print(f"Wrote: {brief}")
    for f in figs:
        print(f"Wrote figure: {f}")


if __name__ == "__main__":
    main()
