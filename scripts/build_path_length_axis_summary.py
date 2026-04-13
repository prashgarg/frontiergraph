from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize path-length axis runs.")
    parser.add_argument("--axis-root", required=True, dest="axis_root")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _collect(axis_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_frames: list[pd.DataFrame] = []
    tuning_frames: list[pd.DataFrame] = []
    for stage_dir in sorted(axis_root.glob("len_*")):
        try:
            max_path_len = int(stage_dir.name.split("_")[-1])
        except ValueError:
            continue
        tuned_path = stage_dir / "benchmark_tuned" / "widened_overall_summary.csv"
        initial_path = stage_dir / "benchmark_initial" / "widened_overall_summary.csv"
        tuning_path = stage_dir / "reranker_tuning" / "tuning_best_configs.csv"
        if tuned_path.exists():
            df = pd.read_csv(tuned_path)
            df["stage"] = "tuned"
            df["max_path_len"] = max_path_len
            benchmark_frames.append(df)
        if initial_path.exists():
            df = pd.read_csv(initial_path)
            df["stage"] = "initial"
            df["max_path_len"] = max_path_len
            benchmark_frames.append(df)
        if tuning_path.exists():
            df = pd.read_csv(tuning_path)
            df["max_path_len"] = max_path_len
            tuning_frames.append(df)
    benchmark_df = pd.concat(benchmark_frames, ignore_index=True) if benchmark_frames else pd.DataFrame()
    tuning_df = pd.concat(tuning_frames, ignore_index=True) if tuning_frames else pd.DataFrame()
    return benchmark_df, tuning_df


def _plot(benchmark_df: pd.DataFrame, out_path: Path) -> None:
    plot_df = benchmark_df.loc[
        benchmark_df["stage"].eq("tuned")
        & benchmark_df["model"].isin(["transparent"])
        | benchmark_df["stage"].eq("tuned")
        & benchmark_df["model"].str.startswith("adopted_", na=False)
    ].copy()
    if plot_df.empty:
        return
    plot_df["model_group"] = plot_df["model"].map(
        lambda x: "Transparent score" if x == "transparent" else "Tuned reranker"
    )

    horizons = sorted(plot_df["horizon"].dropna().unique())
    fig, axes = plt.subplots(1, len(horizons), figsize=(4.2 * len(horizons), 3.5), sharey=False)
    if len(horizons) == 1:
        axes = [axes]

    for ax, horizon in zip(axes, horizons):
        sub = plot_df.loc[plot_df["horizon"].eq(horizon)].sort_values(["model_group", "max_path_len"])
        for model_group, color in [("Transparent score", "#315a8a"), ("Tuned reranker", "#b55d3d")]:
            grp = sub.loc[sub["model_group"].eq(model_group)].sort_values("max_path_len")
            if grp.empty:
                continue
            ax.plot(
                grp["max_path_len"],
                grp["mean_recall_at_100"],
                marker="o",
                linewidth=2.0,
                color=color,
                label=model_group,
            )
        ax.set_title(f"h = {int(horizon)}")
        ax.set_xlabel("Maximum support-path length")
        ax.set_xticks(sorted(sub["max_path_len"].unique()))
        ax.grid(alpha=0.2)
        if ax is axes[0]:
            ax.set_ylabel("Recall@100")

    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Longer support paths: transparent score and tuned reranker", y=1.03, fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    if out_path.suffix.lower() == ".png":
        fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def _write_summary_md(benchmark_df: pd.DataFrame, tuning_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Path-length axis summary",
        "",
        "This note compares `max_path_len = 2, 3, 4, 5` on the current family design.",
        "",
    ]
    if benchmark_df.empty:
        lines.append("No benchmark outputs were found.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    tuned = benchmark_df.loc[benchmark_df["stage"].eq("tuned")].copy()
    if not tuned.empty:
        lines.append("## Tuned benchmark by horizon")
        for horizon in sorted(tuned["horizon"].unique()):
            lines.append(f"- h={int(horizon)}")
            sub = tuned.loc[tuned["horizon"].eq(horizon)].copy()
            for max_path_len in sorted(sub["max_path_len"].unique()):
                block = sub.loc[sub["max_path_len"].eq(max_path_len)]
                trans = block.loc[block["model"].eq("transparent")]
                rerank = block.loc[block["model"].str.startswith("adopted_", na=False)]
                if not trans.empty:
                    row = trans.iloc[0]
                    lines.append(
                        f"  - len={int(max_path_len)} transparent: Recall@100={float(row['mean_recall_at_100']):.4f}, "
                        f"MRR={float(row['mean_mrr']):.4f}"
                    )
                if not rerank.empty:
                    row = rerank.iloc[0]
                    lines.append(
                        f"  - len={int(max_path_len)} reranker: Recall@100={float(row['mean_recall_at_100']):.4f}, "
                        f"MRR={float(row['mean_mrr']):.4f}, model={row['model']}"
                    )
        lines.append("")
    if not tuning_df.empty:
        lines.append("## Best tuned model by path length")
        cols = ["max_path_len", "horizon", "model_kind", "feature_family", "alpha", "mean_recall_at_100", "mean_mrr"]
        for row in tuning_df[cols].sort_values(["horizon", "max_path_len"]).itertuples(index=False):
            lines.append(
                f"- h={int(row.horizon)}, len={int(row.max_path_len)}: {row.model_kind} + {row.feature_family}, "
                f"alpha={float(row.alpha):.3f}, Recall@100={float(row.mean_recall_at_100):.4f}, MRR={float(row.mean_mrr):.4f}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    axis_root = Path(args.axis_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    benchmark_df, tuning_df = _collect(axis_root)
    if not benchmark_df.empty:
        benchmark_df.to_csv(out_dir / "path_length_axis_benchmark.csv", index=False)
    if not tuning_df.empty:
        tuning_df.to_csv(out_dir / "path_length_axis_tuning_best.csv", index=False)
    _plot(benchmark_df, out_dir / "path_length_axis_recall_at_100.png")
    _write_summary_md(benchmark_df, tuning_df, out_dir / "summary.md")


if __name__ == "__main__":
    main()
