from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.common import (
    bootstrap_mean_ci,
    check_no_leakage,
    ensure_output_dir,
    first_appearance_map,
    paired_bootstrap_delta,
)
from src.utils import load_corpus


def compute_main_table_with_ci(
    backtest_df: pd.DataFrame,
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    metric_cols = [c for c in backtest_df.columns if c.startswith("recall_at_")] + [
        c for c in ["mrr"] if c in backtest_df.columns
    ]
    rows: list[dict] = []
    for (model, horizon), g in backtest_df.groupby(["model", "horizon"], dropna=False):
        for metric in metric_cols:
            mean, lo, hi = bootstrap_mean_ci(g[metric].astype(float), n_boot=n_boot, seed=seed)
            rows.append(
                {
                    "model": str(model),
                    "horizon": int(horizon),
                    "metric": metric,
                    "mean": float(mean),
                    "ci_lo": float(lo),
                    "ci_hi": float(hi),
                    "n_cutoffs": int(g["cutoff_year_t"].nunique()) if "cutoff_year_t" in g.columns else int(len(g)),
                }
            )
    return pd.DataFrame(rows)


def compute_significance_tests(
    backtest_df: pd.DataFrame,
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    target_metrics = [m for m in ["recall_at_100", "mrr"] if m in backtest_df.columns]
    rows: list[dict] = []
    model_a, model_b = "main", "pref_attach"
    for horizon in sorted(backtest_df["horizon"].dropna().unique()):
        g = backtest_df[backtest_df["horizon"] == horizon]
        a = g[g["model"] == model_a]
        b = g[g["model"] == model_b]
        if a.empty or b.empty:
            continue
        merged = a[["cutoff_year_t"] + target_metrics].merge(
            b[["cutoff_year_t"] + target_metrics],
            on="cutoff_year_t",
            suffixes=("_a", "_b"),
            how="inner",
        )
        for metric in target_metrics:
            delta, lo, hi, p = paired_bootstrap_delta(
                merged[f"{metric}_a"],
                merged[f"{metric}_b"],
                n_boot=n_boot,
                seed=seed,
            )
            rows.append(
                {
                    "metric": metric,
                    "horizon": int(horizon),
                    "model_a": model_a,
                    "model_b": model_b,
                    "delta": float(delta),
                    "p_value": float(p),
                    "ci_lo": float(lo),
                    "ci_hi": float(hi),
                    "n_pairs": int(len(merged)),
                }
            )
    return pd.DataFrame(rows)


def compute_calibration_by_decile(
    backtest_df: pd.DataFrame,
    vintage_predictions_path: str | None = None,
    vintage_realization_path: str | None = None,
) -> pd.DataFrame:
    # Preferred: candidate-level calibration from vintage outputs.
    if vintage_predictions_path and vintage_realization_path:
        p_path = Path(vintage_predictions_path)
        r_path = Path(vintage_realization_path)
        if p_path.exists() and r_path.exists():
            pred = pd.read_parquet(p_path)
            real = pd.read_parquet(r_path)
            key_cols = [c for c in ["anchor_year", "u", "v", "rank"] if c in pred.columns and c in real.columns]
            if key_cols and "score" in pred.columns and "realized_within_h" in real.columns:
                merged = pred[key_cols + ["score"]].merge(real[key_cols + ["realized_within_h", "time_to_fill"]], on=key_cols, how="inner")
                if not merged.empty:
                    merged = merged.sort_values("score", ascending=False).reset_index(drop=True)
                    merged["score_decile"] = pd.qcut(
                        merged["score"].rank(method="first"),
                        q=10,
                        labels=False,
                        duplicates="drop",
                    ).astype(int) + 1
                    out = (
                        merged.groupby("score_decile", as_index=False)
                        .agg(
                            n=("realized_within_h", "size"),
                            realized_rate=("realized_within_h", "mean"),
                            mean_time_to_fill=("time_to_fill", "mean"),
                            mean_score=("score", "mean"),
                        )
                        .sort_values("score_decile")
                    )
                    out["source"] = "vintage_candidate_level"
                    return out

    # Fallback: cutoff-level proxy calibration from recall@100.
    main_df = backtest_df[backtest_df["model"] == "main"].copy()
    if main_df.empty or "recall_at_100" not in main_df.columns:
        return pd.DataFrame(columns=["score_decile", "n", "realized_rate", "mean_time_to_fill", "mean_score", "source"])
    rows: list[dict] = []
    for horizon, g in main_df.groupby("horizon"):
        gg = g.sort_values("recall_at_100", ascending=False).copy()
        gg["score_decile"] = pd.qcut(
            gg["recall_at_100"].rank(method="first"),
            q=min(10, len(gg)),
            labels=False,
            duplicates="drop",
        ).astype(int) + 1
        agg = gg.groupby("score_decile", as_index=False)["recall_at_100"].mean()
        for row in agg.itertuples(index=False):
            rows.append(
                {
                    "score_decile": int(row.score_decile),
                    "n": int((gg["score_decile"] == row.score_decile).sum()),
                    "realized_rate": float(row.recall_at_100),
                    "mean_time_to_fill": float("nan"),
                    "mean_score": float(row.recall_at_100),
                    "source": f"cutoff_proxy_h{int(horizon)}",
                }
            )
    return pd.DataFrame(rows)


def plot_ci_table(main_table: pd.DataFrame, out_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for metric in ["recall_at_100", "mrr"]:
        sub = main_table[main_table["metric"] == metric].copy()
        if sub.empty:
            continue
        plt.figure(figsize=(8, 5))
        for model, g in sub.groupby("model"):
            g = g.sort_values("horizon")
            y = g["mean"].astype(float)
            err_low = y - g["ci_lo"].astype(float)
            err_high = g["ci_hi"].astype(float) - y
            plt.errorbar(
                g["horizon"].astype(int),
                y,
                yerr=[err_low, err_high],
                marker="o",
                capsize=3,
                label=model,
            )
        plt.xlabel("Horizon")
        plt.ylabel(metric)
        plt.title(f"{metric} with 95% CI")
        plt.legend()
        plt.tight_layout()
        path = out_dir / f"ci_{metric}.png"
        plt.savefig(path, dpi=150)
        plt.close()
        paths.append(path)
    return paths


def plot_calibration(calib_df: pd.DataFrame, out_dir: Path) -> Path | None:
    if calib_df.empty:
        return None
    plt.figure(figsize=(8, 5))
    for src, g in calib_df.groupby("source"):
        gg = g.sort_values("score_decile")
        plt.plot(
            gg["score_decile"].astype(int),
            gg["realized_rate"].astype(float),
            marker="o",
            label=str(src),
        )
    plt.xlabel("Score decile (1=lowest within source)")
    plt.ylabel("Realized rate")
    plt.title("Calibration by score decile")
    plt.legend()
    plt.tight_layout()
    path = out_dir / "calibration_by_decile.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute paper-grade evaluation statistics from backtests.")
    parser.add_argument("--backtest", required=True, dest="backtest_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--n_boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--vintage_predictions", default=None)
    parser.add_argument("--vintage_realization", default=None)
    parser.add_argument("--corpus", default=None, dest="corpus_path")
    parser.add_argument(
        "--candidate-kind",
        default="directed_causal",
        choices=[
            "directed_causal",
            "undirected_noncausal",
            "contextual_pair",
            "ordered_claim",
            "causal_claim",
            "identified_causal_claim",
        ],
    )
    parser.add_argument("--candidate-family-mode", default="path_to_direct", choices=["path_to_direct", "direct_to_path"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    backtest_df = pd.read_parquet(args.backtest_path)

    main_table = compute_main_table_with_ci(backtest_df, n_boot=args.n_boot, seed=args.seed)
    sig_table = compute_significance_tests(backtest_df, n_boot=args.n_boot, seed=args.seed)
    calib_df = compute_calibration_by_decile(
        backtest_df,
        vintage_predictions_path=args.vintage_predictions,
        vintage_realization_path=args.vintage_realization,
    )
    leakage_df = pd.DataFrame(columns=["cutoff_year_t", "horizon", "no_leakage"])
    if args.corpus_path:
        corpus_df = load_corpus(args.corpus_path)
        fmap = first_appearance_map(
            corpus_df,
            candidate_kind=str(args.candidate_kind),
            candidate_family_mode=str(args.candidate_family_mode),
        )
        rows = []
        for row in backtest_df[["cutoff_year_t", "horizon"]].drop_duplicates().itertuples(index=False):
            ok = check_no_leakage(
                corpus_df,
                cutoff_t=int(row.cutoff_year_t),
                horizon_h=int(row.horizon),
                candidate_kind=str(args.candidate_kind),
                candidate_family_mode=str(args.candidate_family_mode),
                first_year_map=fmap,
            )
            rows.append({"cutoff_year_t": int(row.cutoff_year_t), "horizon": int(row.horizon), "no_leakage": bool(ok)})
        leakage_df = pd.DataFrame(rows)

    main_pq = out_dir / "main_table_with_ci.parquet"
    main_csv = out_dir / "main_table_with_ci.csv"
    sig_pq = out_dir / "significance_tests.parquet"
    sig_csv = out_dir / "significance_tests.csv"
    cal_pq = out_dir / "calibration_by_decile.parquet"
    cal_csv = out_dir / "calibration_by_decile.csv"
    leak_csv = out_dir / "leakage_audit.csv"
    leak_pq = out_dir / "leakage_audit.parquet"

    main_table.to_parquet(main_pq, index=False)
    main_table.to_csv(main_csv, index=False)
    sig_table.to_parquet(sig_pq, index=False)
    sig_table.to_csv(sig_csv, index=False)
    calib_df.to_parquet(cal_pq, index=False)
    calib_df.to_csv(cal_csv, index=False)
    leakage_df.to_parquet(leak_pq, index=False)
    leakage_df.to_csv(leak_csv, index=False)

    fig_paths: list[Path] = []
    try:
        fig_paths = plot_ci_table(main_table, out_dir=out_dir)
        cal_fig = plot_calibration(calib_df, out_dir=out_dir)
        if cal_fig is not None:
            fig_paths.append(cal_fig)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to render eval-stat figures: {exc}")

    print(f"Wrote: {main_pq}")
    print(f"Wrote: {main_csv}")
    print(f"Wrote: {sig_pq}")
    print(f"Wrote: {sig_csv}")
    print(f"Wrote: {cal_pq}")
    print(f"Wrote: {cal_csv}")
    print(f"Wrote: {leak_pq}")
    print(f"Wrote: {leak_csv}")
    for p in fig_paths:
        print(f"Wrote figure: {p}")


if __name__ == "__main__":
    main()
