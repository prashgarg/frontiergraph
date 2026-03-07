from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from src.analysis.common import (
    CandidateBuildConfig,
    build_candidate_table,
    check_no_leakage,
    ensure_output_dir,
    first_appearance_map,
)
from src.utils import load_config, load_corpus


def _load_candidate_config(config_path: str, best_config_path: str | None) -> CandidateBuildConfig:
    cfg = load_config(config_path)
    feature_cfg = cfg.get("features", {})
    score_cfg = cfg.get("scoring", {})
    out = CandidateBuildConfig(
        tau=int(feature_cfg.get("tau", 2)),
        max_path_len=int(feature_cfg.get("max_path_len", 2)),
        max_neighbors_per_mediator=int(feature_cfg.get("max_neighbors_per_mediator", 120)),
        alpha=float(score_cfg.get("alpha", 0.5)),
        beta=float(score_cfg.get("beta", 0.2)),
        gamma=float(score_cfg.get("gamma", 0.3)),
        delta=float(score_cfg.get("delta", 0.2)),
    )
    if best_config_path and Path(best_config_path).exists():
        payload = yaml.safe_load(Path(best_config_path).read_text(encoding="utf-8")) or {}
        for k, v in payload.items():
            if hasattr(out, k):
                setattr(out, k, v)
    return out


def build_vintage_tables(
    corpus_df: pd.DataFrame,
    years: list[int],
    horizon_h: int,
    k_values: list[int],
    cfg: CandidateBuildConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    first_year = first_appearance_map(corpus_df)
    max_k = max(k_values)
    pred_rows: list[pd.DataFrame] = []
    real_rows: list[dict] = []
    leakage_lines: list[str] = []

    for t in years:
        train = corpus_df[corpus_df["year"] <= (t - 1)]
        no_leak = check_no_leakage(corpus_df, cutoff_t=t, horizon_h=horizon_h, first_year_map=first_year)
        leakage_lines.append(f"- anchor {t}, h={horizon_h}, no_leakage={no_leak}")
        cand = build_candidate_table(train, cutoff_t=t, cfg=cfg)
        if cand.empty:
            continue
        top = cand.head(max_k).copy()
        top["anchor_year"] = int(t)
        top["horizon_h"] = int(horizon_h)
        top["score_decile"] = (
            pd.qcut(top["score"].rank(method="first"), q=min(10, len(top)), labels=False, duplicates="drop").astype(int) + 1
        )
        pred_rows.append(top)

        for row in top.itertuples(index=False):
            edge = (str(row.u), str(row.v))
            y = first_year.get(edge)
            realized = y is not None and int(t + 1) <= int(y) <= int(t + horizon_h)
            real_rows.append(
                {
                    "anchor_year": int(t),
                    "horizon_h": int(horizon_h),
                    "u": str(row.u),
                    "v": str(row.v),
                    "rank": int(row.rank),
                    "score": float(row.score),
                    "score_decile": int(row.score_decile),
                    "realized_within_h": int(1 if realized else 0),
                    "first_realized_year": int(y) if realized else np.nan,
                    "time_to_fill": int(y - t) if realized else np.nan,
                }
            )

    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    realization = pd.DataFrame(real_rows)
    return predictions, realization, "\n".join(leakage_lines)


def plot_time_to_fill(realization: pd.DataFrame, horizon_h: int, out_path: Path) -> None:
    if realization.empty:
        return
    plt.figure(figsize=(8, 5))
    for d in sorted(realization["score_decile"].dropna().astype(int).unique()):
        g = realization[realization["score_decile"] == d]
        if g.empty:
            continue
        xs = list(range(1, horizon_h + 1))
        ys = []
        denom = max(1, len(g))
        for tau in xs:
            hit = ((g["time_to_fill"].fillna(np.inf) <= tau)).sum()
            ys.append(float(hit) / float(denom))
        plt.plot(xs, ys, marker="o", linewidth=1.5, label=f"decile {d}")
    plt.xlabel("Years since anchor")
    plt.ylabel("Cumulative fill-in rate")
    plt.title("Time-to-fill by score decile")
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def write_case_studies(
    realization: pd.DataFrame,
    out_path: Path,
    k_values: list[int],
    leakage_text: str,
) -> None:
    lines: list[str] = ["# Vintage Exercise Case Studies", ""]
    lines.append("## Leakage Audit")
    lines.append(leakage_text if leakage_text else "- none")
    lines.append("")

    for k in sorted(k_values):
        sub = realization[realization["rank"] <= k].copy()
        if sub.empty:
            continue
        lines.append(f"## Top-{k} Snapshot")
        rate = float(sub["realized_within_h"].mean())
        lines.append(f"- realized rate: {rate:.4f}")
        tp = sub[sub["realized_within_h"] == 1].sort_values(["score", "rank"], ascending=[False, True]).head(5)
        fp = sub[sub["realized_within_h"] == 0].sort_values(["score", "rank"], ascending=[False, True]).head(5)

        lines.append("- top true positives:")
        if tp.empty:
            lines.append("  - none")
        else:
            for r in tp.itertuples(index=False):
                lines.append(
                    f"  - anchor={int(r.anchor_year)} {r.u}->{r.v} rank={int(r.rank)} "
                    f"score={float(r.score):.4f} first_realized_year={int(r.first_realized_year)}"
                )
        lines.append("- top false positives:")
        if fp.empty:
            lines.append("  - none")
        else:
            for r in fp.itertuples(index=False):
                lines.append(
                    f"  - anchor={int(r.anchor_year)} {r.u}->{r.v} rank={int(r.rank)} "
                    f"score={float(r.score):.4f}"
                )
        lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vintage stock-at-year prospective exercise.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--years", type=int, nargs="+", default=[1990, 2000, 2010, 2015])
    parser.add_argument("--h", type=int, default=5, dest="horizon_h")
    parser.add_argument("--k_values", type=int, nargs="+", default=[50, 100, 500])
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus = load_corpus(args.corpus_path)
    min_y, max_y = int(corpus["year"].min()), int(corpus["year"].max())
    valid_years = sorted({int(y) for y in args.years if (min_y + 1) <= int(y) <= (max_y - args.horizon_h)})
    if not valid_years:
        raise SystemExit("No valid anchor years after filtering by corpus support.")

    cfg = _load_candidate_config(args.config_path, args.best_config_path)
    pred, real, leakage_text = build_vintage_tables(
        corpus_df=corpus,
        years=valid_years,
        horizon_h=args.horizon_h,
        k_values=sorted(set(args.k_values)),
        cfg=cfg,
    )

    p_pq = out_dir / "vintage_predictions.parquet"
    p_csv = out_dir / "vintage_predictions.csv"
    r_pq = out_dir / "vintage_realization.parquet"
    r_csv = out_dir / "vintage_realization.csv"
    fig = out_dir / "time_to_fill_curves.png"
    cases = out_dir / "case_studies.md"

    pred.to_parquet(p_pq, index=False)
    pred.to_csv(p_csv, index=False)
    real.to_parquet(r_pq, index=False)
    real.to_csv(r_csv, index=False)
    plot_time_to_fill(real, horizon_h=args.horizon_h, out_path=fig)
    write_case_studies(real, cases, k_values=args.k_values, leakage_text=leakage_text)

    print(f"Wrote: {p_pq}")
    print(f"Wrote: {p_csv}")
    print(f"Wrote: {r_pq}")
    print(f"Wrote: {r_csv}")
    print(f"Wrote: {fig}")
    print(f"Wrote: {cases}")


if __name__ == "__main__":
    main()

