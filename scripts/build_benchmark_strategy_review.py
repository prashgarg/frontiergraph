from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare the best learned reranker against the stronger transparent baselines.")
    parser.add_argument(
        "--tuning-best",
        default="outputs/paper/24_learned_reranker_tuning_patch_v2/tuning_best_configs.csv",
        dest="tuning_best",
    )
    parser.add_argument(
        "--tuning-eval",
        default="outputs/paper/24_learned_reranker_tuning_patch_v2/tuning_cutoff_eval.csv",
        dest="tuning_eval",
    )
    parser.add_argument(
        "--benchmark-panel",
        default="outputs/paper/37_benchmark_expansion/benchmark_expansion_panel.csv",
        dest="benchmark_panel",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/42_benchmark_strategy_review",
        dest="out_dir",
    )
    parser.add_argument(
        "--note",
        default="next_steps/benchmark_strategy_decision.md",
        dest="note_path",
    )
    return parser.parse_args()


def _load_best_reranker_rows(best_path: Path, eval_path: Path) -> pd.DataFrame:
    best_df = pd.read_csv(best_path)
    eval_df = pd.read_csv(eval_path)
    rows = []
    for best in best_df.itertuples(index=False):
        mask = (
            eval_df["horizon"].eq(int(best.horizon))
            & eval_df["model_kind"].eq(str(best.model_kind))
            & eval_df["feature_family"].eq(str(best.feature_family))
            & eval_df["pool_size"].eq(int(best.pool_size))
            & eval_df["alpha"].round(6).eq(round(float(best.alpha), 6))
        )
        block = eval_df.loc[mask].copy()
        if block.empty:
            continue
        block["model"] = "learned_reranker_best"
        block["selection_alpha"] = float(best.alpha)
        block["selection_model_kind"] = str(best.model_kind)
        block["selection_feature_family"] = str(best.feature_family)
        rows.append(block)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _prepare_reranker_metrics(best_eval: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "model",
        "cutoff_year_t",
        "horizon",
        "mrr",
        "precision_at_50",
        "precision_at_100",
        "recall_at_100",
        "selection_alpha",
        "selection_model_kind",
        "selection_feature_family",
    ]
    out = best_eval[cols].copy()
    out["benchmark_family"] = "learned_graph"
    return out


def _prepare_baseline_metrics(benchmark_panel: pd.DataFrame, allowed_cutoffs: list[int]) -> pd.DataFrame:
    keep_models = ["graph_score", "pref_attach", "degree_recency", "directed_closure", "lexical_similarity", "cooc_gap"]
    out = benchmark_panel[benchmark_panel["model"].isin(keep_models)].copy()
    out = out[out["cutoff_year_t"].isin(allowed_cutoffs)].copy()
    out["benchmark_family"] = out["model"].map(
        {
            "graph_score": "transparent_graph",
            "pref_attach": "transparent_baseline",
            "degree_recency": "transparent_baseline",
            "directed_closure": "transparent_baseline",
            "lexical_similarity": "transparent_baseline",
            "cooc_gap": "transparent_baseline",
        }
    )
    return out


def _summarize(metric_df: pd.DataFrame) -> pd.DataFrame:
    return (
        metric_df.groupby(["model", "horizon"], as_index=False)
        .agg(
            mean_precision_at_50=("precision_at_50", "mean"),
            mean_precision_at_100=("precision_at_100", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "mean_precision_at_100", "mean_mrr"], ascending=[True, False, False])
    )


def _pairwise_vs_reranker(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for horizon in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == horizon].copy()
        reranker = block[block["model"] == "learned_reranker_best"]
        if reranker.empty:
            continue
        rr = reranker.iloc[0]
        for row in block.itertuples(index=False):
            if row.model == "learned_reranker_best":
                continue
            rows.append(
                {
                    "horizon": int(horizon),
                    "comparison_model": str(row.model),
                    "delta_precision_at_100_vs_reranker": float(rr["mean_precision_at_100"] - row.mean_precision_at_100),
                    "delta_recall_at_100_vs_reranker": float(rr["mean_recall_at_100"] - row.mean_recall_at_100),
                    "delta_mrr_vs_reranker": float(rr["mean_mrr"] - row.mean_mrr),
                }
            )
    return pd.DataFrame(rows)


def _write_markdown(summary_df: pd.DataFrame, compare_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Benchmark Strategy Review",
        "",
        "This pass asks whether the best learned reranker rescues the benchmark claim once the stronger transparent baselines are included.",
        "",
    ]
    for horizon in sorted(summary_df["horizon"].unique()):
        lines.append(f"## Horizon {int(horizon)}")
        block = summary_df[summary_df["horizon"] == horizon].copy()
        for row in block.itertuples(index=False):
            lines.append(
                f"- `{row.model}`: precision@100={float(row.mean_precision_at_100):.6f}, "
                f"recall@100={float(row.mean_recall_at_100):.6f}, MRR={float(row.mean_mrr):.6f}"
            )
        lines.append("")
        comp = compare_df[compare_df["horizon"] == horizon].copy()
        if not comp.empty:
            better_p = comp[comp["delta_precision_at_100_vs_reranker"] > 0]["comparison_model"].tolist()
            better_r = comp[comp["delta_recall_at_100_vs_reranker"] > 0]["comparison_model"].tolist()
            better_m = comp[comp["delta_mrr_vs_reranker"] > 0]["comparison_model"].tolist()
            lines.append(f"- Reranker beats on precision@100: {', '.join(better_p) if better_p else 'none'}")
            lines.append(f"- Reranker beats on recall@100: {', '.join(better_r) if better_r else 'none'}")
            lines.append(f"- Reranker beats on MRR: {', '.join(better_m) if better_m else 'none'}")
            lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_note(summary_df: pd.DataFrame, compare_df: pd.DataFrame, best_eval: pd.DataFrame, note_path: Path) -> None:
    lines = [
        "# Benchmark Strategy Decision",
        "",
        "## Question",
        "",
        "Can the paper's benchmark claim be rescued by moving from the transparent graph score to the best learned reranker?",
        "",
    ]
    decisions = []
    for horizon in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == horizon].copy()
        rr = block[block["model"] == "learned_reranker_best"]
        if rr.empty:
            continue
        rr_row = rr.iloc[0]
        comp = compare_df[compare_df["horizon"] == horizon].copy()
        precision_beats = comp[comp["delta_precision_at_100_vs_reranker"] > 0]["comparison_model"].tolist()
        recall_beats = comp[comp["delta_recall_at_100_vs_reranker"] > 0]["comparison_model"].tolist()
        mrr_beats = comp[comp["delta_mrr_vs_reranker"] > 0]["comparison_model"].tolist()

        lines.append(f"## Horizon {int(horizon)}")
        lines.append(
            f"- best reranker: precision@100={float(rr_row['mean_precision_at_100']):.6f}, "
            f"recall@100={float(rr_row['mean_recall_at_100']):.6f}, MRR={float(rr_row['mean_mrr']):.6f}"
        )
        lines.append(f"- beats on precision@100: {', '.join(precision_beats) if precision_beats else 'none'}")
        lines.append(f"- beats on recall@100: {', '.join(recall_beats) if recall_beats else 'none'}")
        lines.append(f"- beats on MRR: {', '.join(mrr_beats) if mrr_beats else 'none'}")
        lines.append("")

        decision = {
            "horizon": int(horizon),
            "precision_beats_strong_transparent": all(
                model in precision_beats for model in ["degree_recency", "pref_attach", "directed_closure"]
            ),
            "recall_beats_strong_transparent": all(
                model in recall_beats for model in ["degree_recency", "pref_attach", "directed_closure"]
            ),
            "mrr_beats_strong_transparent": all(
                model in mrr_beats for model in ["degree_recency", "pref_attach", "directed_closure"]
            ),
        }
        decisions.append(decision)

    rescue = all(d["precision_beats_strong_transparent"] or d["mrr_beats_strong_transparent"] for d in decisions) if decisions else False

    lines.extend(
        [
            "## Decision",
            "",
            "`partial rescue`" if rescue else "`not rescued cleanly`",
            "",
        ]
    )

    if rescue:
        lines.extend(
            [
                "The learned reranker is strong enough to keep the paper's benchmark claim alive, but the paper should be explicit that the winning graph-based benchmark is the learned reranker rather than the transparent graph score.",
                "",
                "## Recommendation",
                "",
                "1. move the comparative benchmark claim to the learned reranker",
                "2. present the transparent graph score as the interpretable retrieval layer rather than the benchmark winner",
                "3. keep the stronger transparent baselines in the paper as real comparison points",
            ]
        )
    else:
        lines.extend(
            [
                "The learned reranker does not cleanly dominate the stronger transparent baselines across the core metrics. That means the paper should not rely on a simple 'graph beats baseline' claim without revision.",
                "",
                "## Recommendation",
                "",
                "1. soften the benchmark claim in the paper",
                "2. treat the learned reranker as one useful graph-based screen, not an undisputed benchmark winner",
                "3. shift more emphasis to surfaced-object quality, overlays, and screening interpretation unless a better benchmark model is built",
            ]
        )

    if not best_eval.empty:
        config_rows = best_eval[["horizon", "selection_model_kind", "selection_feature_family", "selection_alpha"]].drop_duplicates()
        lines.extend(["", "## Best reranker configs used", ""])
        for row in config_rows.itertuples(index=False):
            lines.append(
                f"- h={int(row.horizon)}: `{row.selection_model_kind} + {row.selection_feature_family}` with alpha `{float(row.selection_alpha):.2f}`"
            )

    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(Path(args.out_dir))
    note_path = Path(args.note_path)

    best_eval = _load_best_reranker_rows(Path(args.tuning_best), Path(args.tuning_eval))
    if best_eval.empty:
        raise SystemExit("Could not locate the best reranker rows in tuning_cutoff_eval.")

    reranker_df = _prepare_reranker_metrics(best_eval)
    allowed_cutoffs = sorted(reranker_df["cutoff_year_t"].dropna().astype(int).unique().tolist())

    benchmark_df = pd.read_csv(args.benchmark_panel)
    baseline_df = _prepare_baseline_metrics(benchmark_df, allowed_cutoffs)

    metric_df = pd.concat(
        [
            reranker_df[["model", "cutoff_year_t", "horizon", "mrr", "precision_at_50", "precision_at_100", "recall_at_100"]],
            baseline_df[["model", "cutoff_year_t", "horizon", "mrr", "precision_at_50", "precision_at_100", "recall_at_100"]],
        ],
        ignore_index=True,
    )
    summary_df = _summarize(metric_df)
    compare_df = _pairwise_vs_reranker(summary_df)

    metric_df.to_csv(out_dir / "benchmark_strategy_panel.csv", index=False)
    summary_df.to_csv(out_dir / "benchmark_strategy_summary.csv", index=False)
    compare_df.to_csv(out_dir / "benchmark_strategy_vs_reranker.csv", index=False)

    summary_payload = {
        "common_cutoffs": allowed_cutoffs,
        "horizons": sorted(summary_df["horizon"].dropna().astype(int).unique().tolist()),
        "models": sorted(summary_df["model"].dropna().astype(str).unique().tolist()),
        "reranker_beats_all_strong_transparent_on_precision_at_100": bool(
            not compare_df[
                compare_df["comparison_model"].isin(["degree_recency", "pref_attach", "directed_closure"])
                & compare_df["delta_precision_at_100_vs_reranker"].le(0)
            ].empty
        )
        is False,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    _write_markdown(summary_df, compare_df, out_dir / "benchmark_strategy_review.md")
    _write_note(summary_df, compare_df, best_eval, note_path)


if __name__ == "__main__":
    main()
