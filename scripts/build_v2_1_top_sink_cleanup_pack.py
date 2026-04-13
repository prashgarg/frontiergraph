from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a focused sink-endpoint cleanup pack for canonicalized v2.1.")
    parser.add_argument(
        "--baseline-frontier",
        default="outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.parquet",
    )
    parser.add_argument(
        "--tuned-frontier",
        default="outputs/paper/57_current_reranked_frontier_v2_1_canonicalized_tuned/current_reranked_frontier.parquet",
    )
    parser.add_argument(
        "--sink-targets",
        default="outputs/paper/54_v2_1_sink_diagnostic/sink_targets.csv",
    )
    parser.add_argument(
        "--semantic-splits",
        default="outputs/paper/54_v2_1_sink_diagnostic/high_support_flexible_endpoint_subfamilies_semantic.csv",
    )
    parser.add_argument(
        "--canonicalization-csv",
        default="data/ontology_v2/cross_source_canonicalization_applied_v2_1.csv",
    )
    parser.add_argument(
        "--out-csv",
        default="outputs/paper/59_v2_1_top_sink_cleanup_pack/top_sink_cleanup_pack.csv",
    )
    parser.add_argument(
        "--out-md",
        default="next_steps/top_sink_cleanup_pack_v2_1.md",
    )
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args()


def _norm_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower()).strip(" .")


def _top_counts(df: pd.DataFrame, label_col: str, rank_col: str, top_k: int) -> pd.DataFrame:
    top = df.sort_values(rank_col).head(top_k).copy()
    counts = top[label_col].astype(str).map(_norm_label).value_counts().rename_axis("norm_label").reset_index(name=f"top{top_k}_count")
    return counts


def _proposed_action(row: pd.Series) -> str:
    split = bool(row.get("recommended_split_semantic", False))
    canonical_members = int(row.get("canonical_member_count", 0) or 0)
    tuned_top100 = int(row.get("tuned_top100_count", 0) or 0)
    significant_clusters = int(row.get("significant_cluster_count", 0) or 0)
    if split and significant_clusters >= 2:
        return "review_for_subfamily_promotion"
    if canonical_members > 0 and tuned_top100 >= 4:
        return "canonicalize_and_regularize"
    if tuned_top100 >= 4:
        return "regularize_only"
    if canonical_members > 0:
        return "canonicalize_only"
    return "monitor"


def main() -> None:
    args = parse_args()
    baseline_frontier = pd.read_parquet(args.baseline_frontier)
    tuned_frontier = pd.read_parquet(args.tuned_frontier)
    sink_targets = pd.read_csv(args.sink_targets)
    semantic_splits = pd.read_csv(args.semantic_splits)
    canonicalization = pd.read_csv(args.canonicalization_csv)

    baseline_counts = _top_counts(baseline_frontier, "v_label", "reranker_rank", 100).rename(columns={"top100_count": "baseline_top100_count"})
    tuned_counts = _top_counts(tuned_frontier, "v_label", "surface_rank", 100).rename(columns={"top100_count": "tuned_top100_count"})
    tuned_top20 = _top_counts(tuned_frontier, "v_label", "surface_rank", 20).rename(columns={"top20_count": "tuned_top20_count"})

    canonical_summary = (
        canonicalization.assign(norm_label=canonicalization["canonical_label"].map(_norm_label))
        .groupby(["canonical_id", "canonical_label", "norm_label"], as_index=False)
        .agg(
            canonical_member_count=("member_id", "size"),
            canonical_member_sources=("member_source", lambda s: json.dumps(sorted(set(map(str, s))), ensure_ascii=False)),
            canonical_member_labels=("member_label", lambda s: json.dumps(sorted(set(map(str, s)))[:10], ensure_ascii=False)),
        )
    )

    semantic = semantic_splits.copy()
    semantic["norm_label"] = semantic["target_label"].map(_norm_label)

    sinks = sink_targets.copy()
    sinks["norm_label"] = sinks["v_label"].map(_norm_label)
    pack = (
        sinks.sort_values(["sink_score_pct", "top100_overall"], ascending=[False, False])
        .head(int(args.top_n))
        .merge(baseline_counts, on="norm_label", how="left")
        .merge(tuned_counts, on="norm_label", how="left")
        .merge(tuned_top20, on="norm_label", how="left")
        .merge(
            canonical_summary[["norm_label", "canonical_member_count", "canonical_member_sources", "canonical_member_labels"]],
            on="norm_label",
            how="left",
        )
        .merge(
            semantic[
                [
                    "norm_label",
                    "modifier_phrase_rows",
                    "modifier_total_freq",
                    "semantic_cluster_count",
                    "significant_cluster_count",
                    "semantic_cluster_entropy",
                    "recommended_split_semantic",
                    "top_semantic_clusters",
                ]
            ],
            on="norm_label",
            how="left",
        )
    )

    for col in [
        "baseline_top100_count",
        "tuned_top100_count",
        "tuned_top20_count",
        "canonical_member_count",
        "modifier_phrase_rows",
        "modifier_total_freq",
        "semantic_cluster_count",
        "significant_cluster_count",
    ]:
        if col in pack.columns:
            pack[col] = pack[col].fillna(0).astype(int)
    for col in ["semantic_cluster_entropy", "sink_score", "sink_score_pct"]:
        if col in pack.columns:
            pack[col] = pack[col].fillna(0.0).astype(float)
    if "recommended_split_semantic" in pack.columns:
        pack["recommended_split_semantic"] = pack["recommended_split_semantic"].fillna(False).astype(bool)
    pack["proposed_cleanup_action"] = pack.apply(_proposed_action, axis=1)
    pack = pack.rename(columns={"v": "target_id", "v_label": "target_label"})

    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    pack.to_csv(out_csv, index=False)

    lines = [
        "# Top Sink Cleanup Pack (v2.1 Canonicalized + Tuned)",
        "",
        "This note summarizes the highest-sink endpoints after canonicalization and the calibrated sink-regularized frontier.",
        "",
        "## Endpoints",
        "",
    ]
    for row in pack.itertuples(index=False):
        lines.append(f"### {row.target_label}")
        lines.append(f"- target id: `{row.target_id}`")
        lines.append(f"- sink score pct: `{row.sink_score_pct:.6f}`")
        lines.append(f"- baseline top-100 appearances: `{int(row.baseline_top100_count)}`")
        lines.append(f"- tuned top-20 / top-100 appearances: `{int(row.tuned_top20_count)}` / `{int(row.tuned_top100_count)}`")
        lines.append(f"- duplicate member sources absorbed: `{int(row.canonical_member_count)}`")
        lines.append(f"- semantic split suggested: `{bool(row.recommended_split_semantic)}`")
        lines.append(
            f"- semantic clusters: `{int(row.semantic_cluster_count)}` total, `{int(row.significant_cluster_count)}` significant, entropy `{float(row.semantic_cluster_entropy):.3f}`"
        )
        lines.append(f"- proposed cleanup action: `{row.proposed_cleanup_action}`")
        lines.append("")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote sink cleanup CSV: {out_csv}")
    print(f"Wrote sink cleanup note: {out_md}")


if __name__ == "__main__":
    main()
