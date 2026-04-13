from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select paper-facing concentration configs across diversification-only and sink+diversification variants.")
    parser.add_argument("--family", required=True, dest="family")
    parser.add_argument("--diversification-cutoff-csvs", required=True, dest="div_cutoff_csvs")
    parser.add_argument("--sink-cutoff-csv", required=True, dest="sink_cutoff_csv")
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--note", required=True, dest="note_path")
    return parser.parse_args()


def _parse_paths(raw: str) -> list[Path]:
    return [Path(x.strip()) for x in str(raw).split(",") if x.strip()]


def _summarize_diversification(cutoff_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        cutoff_df.groupby(["horizon", "diversify_window"], as_index=False)
        .agg(
            candidate_family_mode=("candidate_family_mode", "first"),
            path_to_direct_scope=("path_to_direct_scope", "first"),
            concentration_variant=("concentration_variant", "first"),
            mean_precision_at_100=("diversified_precision_at_100", "mean"),
            mean_recall_at_100=("diversified_recall_at_100", "mean"),
            mean_mrr=("diversified_mrr", "mean"),
            mean_unique_theme_pair_keys_top100=("top100_diversified_unique_theme_pair_keys", "mean"),
            mean_unique_semantic_family_keys_top100=("top100_diversified_unique_semantic_family_keys", "mean"),
            mean_top_target_share_top100=("top100_diversified_top_target_share", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "diversify_window"])
        .reset_index(drop=True)
    )
    grouped["variant"] = "diversification_only"
    grouped["sink_start_pct"] = 0.995
    grouped["sink_lambda"] = 0.0
    grouped["repeat_log_lambda"] = 0.0
    grouped["repeat_linear_lambda"] = 0.0
    grouped["config_id"] = grouped["diversify_window"].map(lambda w: f"diversification_only_w{int(w)}")
    return grouped


def _summarize_sink(cutoff_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        cutoff_df.groupby(
            [
                "horizon",
                "config_id",
                "sink_start_pct",
                "sink_lambda",
                "diversify_window",
                "repeat_log_lambda",
                "repeat_linear_lambda",
            ],
            as_index=False,
        )
        .agg(
            candidate_family_mode=("candidate_family_mode", "first"),
            path_to_direct_scope=("path_to_direct_scope", "first"),
            concentration_variant=("concentration_variant", "first"),
            mean_precision_at_100=("precision_at_100", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
            mean_unique_theme_pair_keys_top100=("unique_theme_pair_keys_top100", "mean"),
            mean_unique_semantic_family_keys_top100=("unique_semantic_family_keys_top100", "mean"),
            mean_top_target_share_top100=("top_target_share_top100", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "mean_top_target_share_top100", "mean_mrr"], ascending=[True, True, False])
        .reset_index(drop=True)
    )
    grouped["variant"] = "sink_plus_diversification"
    return grouped


def _baseline_from_div_cutoff(cutoff_df: pd.DataFrame) -> pd.DataFrame:
    return (
        cutoff_df.groupby("horizon", as_index=False)
        .agg(
            baseline_mean_precision_at_100=("reranker_precision_at_100", "mean"),
            baseline_mean_recall_at_100=("reranker_recall_at_100", "mean"),
            baseline_mean_mrr=("reranker_mrr", "mean"),
        )
        .sort_values("horizon")
        .reset_index(drop=True)
    )


def _attach_eligibility(summary_df: pd.DataFrame, baseline_df: pd.DataFrame) -> pd.DataFrame:
    out = summary_df.merge(baseline_df, on="horizon", how="left")
    out["delta_recall_at_100_vs_base"] = out["mean_recall_at_100"] - out["baseline_mean_recall_at_100"]
    out["delta_mrr_vs_base"] = out["mean_mrr"] - out["baseline_mean_mrr"]
    out["eligible"] = (
        (out["delta_recall_at_100_vs_base"] >= 0.0)
        & (out["delta_mrr_vs_base"] >= 0.0)
    ).astype(int)
    return out


def _pick_winners(summary_df: pd.DataFrame) -> pd.DataFrame:
    winners: list[pd.DataFrame] = []
    for horizon, block in summary_df.groupby("horizon", sort=True):
        eligible = block[block["eligible"].astype(int) == 1].copy()
        if eligible.empty:
            eligible = block.copy()
        eligible["variant_preference"] = eligible["variant"].map(
            lambda x: 0 if str(x) == "diversification_only" else 1
        )
        chosen = eligible.sort_values(
            [
                "mean_top_target_share_top100",
                "mean_unique_theme_pair_keys_top100",
                "variant_preference",
                "mean_mrr",
                "mean_recall_at_100",
            ],
            ascending=[True, False, True, False, False],
        ).head(1)
        winners.append(chosen.drop(columns=["variant_preference"]))
    return pd.concat(winners, ignore_index=True) if winners else pd.DataFrame()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    div_paths = _parse_paths(args.div_cutoff_csvs)
    div_cutoff_frames = [pd.read_csv(path) for path in div_paths if path.exists()]
    if not div_cutoff_frames:
        raise SystemExit("No diversification cutoff CSVs found.")
    div_cutoff_df = pd.concat(div_cutoff_frames, ignore_index=True)
    sink_cutoff_path = Path(args.sink_cutoff_csv)
    if not sink_cutoff_path.exists():
        raise SystemExit(f"Missing sink cutoff CSV: {sink_cutoff_path}")
    sink_cutoff_df = pd.read_csv(sink_cutoff_path)

    baseline_df = _baseline_from_div_cutoff(div_cutoff_df)
    div_summary = _summarize_diversification(div_cutoff_df)
    sink_summary = _summarize_sink(sink_cutoff_df)
    summary_df = pd.concat([div_summary, sink_summary], ignore_index=True)
    summary_df = _attach_eligibility(summary_df, baseline_df)
    summary_df = summary_df.sort_values(
        ["horizon", "eligible", "mean_top_target_share_top100", "mean_unique_theme_pair_keys_top100", "mean_mrr"],
        ascending=[True, False, True, False, False],
    ).reset_index(drop=True)
    winners_df = _pick_winners(summary_df)

    summary_df.to_csv(out_dir / "concentration_comparison_summary.csv", index=False)
    winners_df[
        [
            "horizon",
            "candidate_family_mode",
            "path_to_direct_scope",
            "variant",
            "config_id",
            "sink_start_pct",
            "sink_lambda",
            "diversify_window",
            "repeat_log_lambda",
            "repeat_linear_lambda",
            "mean_precision_at_100",
            "mean_recall_at_100",
            "mean_mrr",
            "mean_unique_theme_pair_keys_top100",
            "mean_unique_semantic_family_keys_top100",
            "mean_top_target_share_top100",
            "delta_recall_at_100_vs_base",
            "delta_mrr_vs_base",
            "eligible",
            "n_cutoffs",
        ]
    ].to_csv(out_dir / "recommended_concentration_configs.csv", index=False)

    note_lines = [
        "# Method v2 Concentration Selection",
        "",
        f"Family: `{args.family}`",
        "",
        "Selection rule:",
        "1. keep only variants with non-negative mean Recall@100 and mean MRR relative to the unregularized reranker",
        "2. among those, choose the lowest mean top-target share@100",
        "3. tie-break with highest mean unique theme-pair keys@100",
        "4. final tie-break prefers diversification only",
        "",
    ]
    for row in winners_df.itertuples(index=False):
        note_lines.extend(
            [
                f"## Horizon {int(row.horizon)}",
                f"- chosen variant: `{row.variant}`",
                f"- config id: `{row.config_id}`",
                f"- mean precision@100: `{float(row.mean_precision_at_100):.6f}`",
                f"- mean recall@100: `{float(row.mean_recall_at_100):.6f}`",
                f"- mean MRR: `{float(row.mean_mrr):.6f}`",
                f"- mean unique theme-pair keys@100: `{float(row.mean_unique_theme_pair_keys_top100):.2f}`",
                f"- mean unique semantic-family keys@100: `{float(row.mean_unique_semantic_family_keys_top100):.2f}`",
                f"- mean top-target share@100: `{float(row.mean_top_target_share_top100):.6f}`",
                f"- delta recall@100 vs base: `{float(row.delta_recall_at_100_vs_base):+.6f}`",
                f"- delta MRR vs base: `{float(row.delta_mrr_vs_base):+.6f}`",
                "",
            ]
        )
    Path(args.note_path).write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    payload = {
        "family": args.family,
        "winners": winners_df[
            [
                "horizon",
                "variant",
                "config_id",
                "sink_start_pct",
                "sink_lambda",
                "diversify_window",
                "repeat_log_lambda",
                "repeat_linear_lambda",
            ]
        ].to_dict(orient="records"),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
