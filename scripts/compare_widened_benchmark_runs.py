from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two widened benchmark output directories.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def _load_overall(run_dir: Path, label: str) -> pd.DataFrame:
    df = pd.read_csv(run_dir / "widened_overall_summary.csv")
    df["run_label"] = label
    return df


def main() -> None:
    args = parse_args()
    baseline_dir = Path(args.baseline_dir)
    candidate_dir = Path(args.candidate_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base = _load_overall(baseline_dir, "baseline")
    cand = _load_overall(candidate_dir, "candidate")

    merged = base.merge(
        cand,
        on=["model", "horizon"],
        how="inner",
        suffixes=("_baseline", "_candidate"),
    )
    for metric in [
        "mean_mrr",
        "mean_recall_at_100",
        "mean_top_share_realized",
        "mean_top_mean_endpoint_broadness_pct",
        "mean_top_mean_endpoint_resolution_score",
        "mean_top_mean_mediator_specificity_score",
    ]:
        merged[f"delta_{metric}"] = (
            pd.to_numeric(merged[f"{metric}_candidate"], errors="coerce").fillna(0.0)
            - pd.to_numeric(merged[f"{metric}_baseline"], errors="coerce").fillna(0.0)
        )

    keep_cols = [
        "model",
        "horizon",
        "mean_mrr_baseline",
        "mean_mrr_candidate",
        "delta_mean_mrr",
        "mean_recall_at_100_baseline",
        "mean_recall_at_100_candidate",
        "delta_mean_recall_at_100",
        "mean_top_share_realized_baseline",
        "mean_top_share_realized_candidate",
        "delta_mean_top_share_realized",
        "mean_top_mean_endpoint_broadness_pct_baseline",
        "mean_top_mean_endpoint_broadness_pct_candidate",
        "delta_mean_top_mean_endpoint_broadness_pct",
        "mean_top_mean_endpoint_resolution_score_baseline",
        "mean_top_mean_endpoint_resolution_score_candidate",
        "delta_mean_top_mean_endpoint_resolution_score",
        "mean_top_mean_mediator_specificity_score_baseline",
        "mean_top_mean_mediator_specificity_score_candidate",
        "delta_mean_top_mean_mediator_specificity_score",
    ]
    comp = merged[keep_cols].sort_values(["horizon", "model"]).reset_index(drop=True)
    comp.to_csv(out_path.with_suffix(".csv"), index=False)

    lines = [
        "# Widened Benchmark Comparison",
        "",
        f"- baseline: `{baseline_dir}`",
        f"- candidate: `{candidate_dir}`",
        "",
        "## Score drift",
        "",
    ]
    for row in comp.itertuples(index=False):
        lines.append(
            f"- h={int(row.horizon)}, {row.model}: "
            f"delta MRR={float(row.delta_mean_mrr):+.5f}, "
            f"delta R@100={float(row.delta_mean_recall_at_100):+.5f}, "
            f"delta realized-share={float(row.delta_mean_top_share_realized):+.5f}"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("Small score drift implies the richer detail fields can be turned on for historical object rendering without materially changing the benchmark.")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
