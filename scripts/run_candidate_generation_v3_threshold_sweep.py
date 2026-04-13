from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a narrow historical calibration sweep for candidate-generation v3 gates.")
    parser.add_argument(
        "--panel",
        default="outputs/paper/84_surface_layer_backtest_path_to_direct/historical_feature_panel.parquet",
        dest="panel_path",
    )
    parser.add_argument(
        "--frontier",
        default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv",
        dest="frontier_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--broad-start-pcts", default="0.75,0.80,0.85")
    parser.add_argument("--resolution-cuts", default="0.15,0.18,0.22")
    parser.add_argument("--mediator-cuts", default="0.20,0.25,0.30")
    parser.add_argument("--path-cuts", default="1.5,2.0,3.0")
    parser.add_argument("--compression-resolution-cut", type=float, default=0.15, dest="compression_resolution_cut")
    parser.add_argument("--compression-mediator-cut", type=float, default=0.35, dest="compression_mediator_cut")
    parser.add_argument("--k-values", default="100,500,2000,5000")
    return parser.parse_args()


def _parse_floats(raw: str) -> list[float]:
    return [float(x.strip()) for x in str(raw).split(",") if x.strip()]


def _parse_ints(raw: str) -> list[int]:
    return [int(float(x.strip())) for x in str(raw).split(",") if x.strip()]


def _ensure_panel_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "transparent_rank" not in out.columns:
        if "rank" in out.columns:
            out["transparent_rank"] = pd.to_numeric(out["rank"], errors="coerce").fillna(0).astype(int)
        else:
            out["transparent_rank"] = np.arange(1, len(out) + 1)
    if "endpoint_broadness_pct" not in out.columns:
        broad = pd.to_numeric(out.get("endpoint_broadness_raw", 0.0), errors="coerce").fillna(0.0).astype(float)
        lo, hi = float(broad.min()), float(broad.max())
        if hi <= lo:
            out["endpoint_broadness_pct"] = 0.0
        else:
            out["endpoint_broadness_pct"] = ((broad - lo) / (hi - lo)).clip(0.0, 1.0)
    for col, default in [
        ("endpoint_resolution_score", 0.0),
        ("focal_mediator_specificity_score", 0.5),
        ("path_support_raw", 0.0),
        ("motif_count", 0),
        ("mediator_count", 0),
        ("appears_within_h", 0),
    ]:
        series = out[col] if col in out.columns else pd.Series(default, index=out.index)
        out[col] = pd.to_numeric(series, errors="coerce").fillna(default)
    for col in ["candidate_scope_bucket", "candidate_subfamily", "local_topology_class", "u_label", "v_label", "u", "v"]:
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str)
    return out


def _apply_gate(
    df: pd.DataFrame,
    broad_start_pct: float,
    resolution_cut: float,
    mediator_cut: float,
    path_cut: float,
    compression_resolution_cut: float,
    compression_mediator_cut: float,
) -> pd.DataFrame:
    out = df.copy()
    anchored = (
        out.get("candidate_scope_bucket", pd.Series("", index=out.index)).astype(str).eq("anchored_progression")
        | out.get("candidate_subfamily", pd.Series("", index=out.index)).astype(str).isin(["ordered_to_causal", "causal_to_identified"])
    )
    broad = pd.to_numeric(out["endpoint_broadness_pct"], errors="coerce").fillna(0.0).astype(float) >= float(broad_start_pct)
    resolution = pd.to_numeric(out["endpoint_resolution_score"], errors="coerce").fillna(0.0).astype(float)
    mediator_spec = pd.to_numeric(out["focal_mediator_specificity_score"], errors="coerce").fillna(0.5).astype(float)
    path_support_raw = pd.to_numeric(out["path_support_raw"], errors="coerce").fillna(0.0).astype(float)
    motif_count = pd.to_numeric(out["motif_count"], errors="coerce").fillna(0).astype(int)
    mediator_count = pd.to_numeric(out["mediator_count"], errors="coerce").fillna(0).astype(int)

    strong_structure = (path_support_raw >= float(path_cut)) | (motif_count >= 2) | (mediator_count >= 2)
    strong_resolution = resolution >= float(resolution_cut)
    strong_mediator = mediator_spec >= float(mediator_cut)
    gate_fail = anchored & broad & (~strong_structure) & (~strong_resolution) & (~strong_mediator)
    out["gate_fail"] = gate_fail.astype(int)

    mediator_present = (
        out.get("focal_mediator_label", pd.Series("", index=out.index)).astype(str).str.strip().ne("")
        | out.get("focal_mediator_id", pd.Series("", index=out.index)).astype(str).str.strip().ne("")
    )
    out["compression_failure_reason"] = ""
    both = (resolution < compression_resolution_cut) & mediator_present & (mediator_spec < compression_mediator_cut)
    out.loc[both, "compression_failure_reason"] = "broad_endpoints_and_generic_mediator"
    out.loc[(out["compression_failure_reason"] == "") & (resolution < compression_resolution_cut), "compression_failure_reason"] = "broad_endpoints"
    out.loc[
        (out["compression_failure_reason"] == "") & mediator_present & (mediator_spec < compression_mediator_cut),
        "compression_failure_reason",
    ] = "generic_mediator"

    kept = out.loc[out["gate_fail"] == 0].copy()
    kept = kept.sort_values(["transparent_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
    kept["post_gate_rank"] = np.arange(1, len(kept) + 1)
    return kept


def _ensure_diag_labels(
    frame: pd.DataFrame,
    broad_start_pct: float,
    resolution_cut: float,
    mediator_cut: float,
    path_cut: float,
    compression_resolution_cut: float,
    compression_mediator_cut: float,
) -> pd.DataFrame:
    out = frame.copy()
    if "compression_failure_reason" not in out.columns:
        resolution = pd.to_numeric(out.get("endpoint_resolution_score", 0.0), errors="coerce").fillna(0.0).astype(float)
        mediator_spec = pd.to_numeric(out.get("focal_mediator_specificity_score", 0.5), errors="coerce").fillna(0.5).astype(float)
        mediator_present = (
            out.get("focal_mediator_label", pd.Series("", index=out.index)).astype(str).str.strip().ne("")
            | out.get("focal_mediator_id", pd.Series("", index=out.index)).astype(str).str.strip().ne("")
        )
        out["compression_failure_reason"] = ""
        both = (resolution < compression_resolution_cut) & mediator_present & (mediator_spec < compression_mediator_cut)
        out.loc[both, "compression_failure_reason"] = "broad_endpoints_and_generic_mediator"
        out.loc[(out["compression_failure_reason"] == "") & (resolution < compression_resolution_cut), "compression_failure_reason"] = "broad_endpoints"
        out.loc[
            (out["compression_failure_reason"] == "") & mediator_present & (mediator_spec < compression_mediator_cut),
            "compression_failure_reason",
        ] = "generic_mediator"
    if "gate_fail" not in out.columns:
        anchored = (
            out.get("candidate_scope_bucket", pd.Series("", index=out.index)).astype(str).eq("anchored_progression")
            | out.get("candidate_subfamily", pd.Series("", index=out.index)).astype(str).isin(["ordered_to_causal", "causal_to_identified"])
        )
        broad = pd.to_numeric(out["endpoint_broadness_pct"], errors="coerce").fillna(0.0).astype(float) >= float(broad_start_pct)
        resolution = pd.to_numeric(out.get("endpoint_resolution_score", 0.0), errors="coerce").fillna(0.0).astype(float)
        mediator_spec = pd.to_numeric(out.get("focal_mediator_specificity_score", 0.5), errors="coerce").fillna(0.5).astype(float)
        path_support_raw = pd.to_numeric(out.get("path_support_raw", 0.0), errors="coerce").fillna(0.0).astype(float)
        motif_count = pd.to_numeric(out.get("motif_count", 0), errors="coerce").fillna(0).astype(int)
        mediator_count = pd.to_numeric(out.get("mediator_count", 0), errors="coerce").fillna(0).astype(int)
        strong_structure = (path_support_raw >= float(path_cut)) | (motif_count >= 2) | (mediator_count >= 2)
        strong_resolution = resolution >= float(resolution_cut)
        strong_mediator = mediator_spec >= float(mediator_cut)
        out["gate_fail"] = (anchored & broad & (~strong_structure) & (~strong_resolution) & (~strong_mediator)).astype(int)
    return out


def _diag(
    df: pd.DataFrame,
    prefix: str,
    broad_start_pct: float,
    resolution_cut: float,
    mediator_cut: float,
    path_cut: float,
    compression_resolution_cut: float,
    compression_mediator_cut: float,
) -> dict[str, float]:
    top100 = df.head(100).copy()
    top500 = df.head(500).copy()

    def share(frame: pd.DataFrame, cond: pd.Series) -> float:
        return float(cond.mean()) if len(frame) else 0.0

    out: dict[str, float] = {}
    for name, frame in [("top100", top100), ("top500", top500)]:
        if frame.empty:
            out[f"{prefix}_{name}_broad_share"] = 0.0
            out[f"{prefix}_{name}_weak_compression_share"] = 0.0
            out[f"{prefix}_{name}_broad_low_signal_share"] = 0.0
            out[f"{prefix}_{name}_top_target_share"] = 0.0
            out[f"{prefix}_{name}_unique_targets"] = 0.0
            out[f"{prefix}_{name}_unique_sources"] = 0.0
            continue
        frame = _ensure_diag_labels(
            frame,
            broad_start_pct=broad_start_pct,
            resolution_cut=resolution_cut,
            mediator_cut=mediator_cut,
            path_cut=path_cut,
            compression_resolution_cut=compression_resolution_cut,
            compression_mediator_cut=compression_mediator_cut,
        )
        broad = pd.to_numeric(frame["endpoint_broadness_pct"], errors="coerce").fillna(0.0).astype(float) >= float(broad_start_pct)
        weak = frame["compression_failure_reason"].astype(str).ne("")
        low_signal = frame["gate_fail"].astype(int) == 1 if "gate_fail" in frame.columns else pd.Series(False, index=frame.index)
        out[f"{prefix}_{name}_broad_share"] = share(frame, broad)
        out[f"{prefix}_{name}_weak_compression_share"] = share(frame, weak)
        out[f"{prefix}_{name}_broad_low_signal_share"] = share(frame, low_signal)
        out[f"{prefix}_{name}_top_target_share"] = float(frame["v_label"].astype(str).value_counts(normalize=True).iloc[0]) if "v_label" in frame.columns else 0.0
        out[f"{prefix}_{name}_unique_targets"] = float(frame["v_label"].astype(str).nunique()) if "v_label" in frame.columns else 0.0
        out[f"{prefix}_{name}_unique_sources"] = float(frame["u_label"].astype(str).nunique()) if "u_label" in frame.columns else 0.0
    return out


def _evaluate_panel_config(
    panel_df: pd.DataFrame,
    broad_start_pct: float,
    resolution_cut: float,
    mediator_cut: float,
    path_cut: float,
    compression_resolution_cut: float,
    compression_mediator_cut: float,
    k_values: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    row_blocks: list[dict] = []
    diag_blocks: list[dict] = []
    for (horizon, cutoff_t), block in panel_df.groupby(["horizon", "cutoff_year_t"]):
        base = block.sort_values(["transparent_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True).copy()
        base["rank"] = np.arange(1, len(base) + 1)
        positives = {
            (str(r.u), str(r.v))
            for r in base.loc[base["appears_within_h"].astype(int) == 1, ["u", "v"]].itertuples(index=False)
        }
        base_metrics = evaluate_binary_ranking(base[["u", "v", "rank"]].copy(), positives=positives, k_values=k_values)
        kept = _apply_gate(
            base,
            broad_start_pct=broad_start_pct,
            resolution_cut=resolution_cut,
            mediator_cut=mediator_cut,
            path_cut=path_cut,
            compression_resolution_cut=compression_resolution_cut,
            compression_mediator_cut=compression_mediator_cut,
        )
        kept_ranked = kept.rename(columns={"post_gate_rank": "rank"})
        kept_metrics = evaluate_binary_ranking(kept_ranked[["u", "v", "rank"]].copy(), positives=positives, k_values=k_values)

        base_positive_rate = float(base["appears_within_h"].astype(int).mean())
        kept_positive_rate = float(kept["appears_within_h"].astype(int).mean()) if len(kept) else 0.0
        row = {
            "horizon": int(horizon),
            "cutoff_year_t": int(cutoff_t),
            "n_candidates_base": int(len(base)),
            "n_candidates_kept": int(len(kept)),
            "candidate_keep_rate": float(len(kept)) / float(max(1, len(base))),
            "positive_rate_base": base_positive_rate,
            "positive_rate_kept": kept_positive_rate,
            "delta_positive_rate": kept_positive_rate - base_positive_rate,
            "mrr_base": float(base_metrics.get("mrr", 0.0)),
            "mrr_kept": float(kept_metrics.get("mrr", 0.0)),
            "delta_mrr": float(kept_metrics.get("mrr", 0.0) - base_metrics.get("mrr", 0.0)),
        }
        for k in k_values:
            row[f"recall_at_{k}_base"] = float(base_metrics.get(f"recall_at_{k}", 0.0))
            row[f"recall_at_{k}_kept"] = float(kept_metrics.get(f"recall_at_{k}", 0.0))
            row[f"delta_recall_at_{k}"] = float(kept_metrics.get(f"recall_at_{k}", 0.0) - base_metrics.get(f"recall_at_{k}", 0.0))
        row_blocks.append(row)

        diag = {
            "horizon": int(horizon),
            "cutoff_year_t": int(cutoff_t),
            **_diag(
                base,
                "base",
                broad_start_pct=broad_start_pct,
                resolution_cut=resolution_cut,
                mediator_cut=mediator_cut,
                path_cut=path_cut,
                compression_resolution_cut=compression_resolution_cut,
                compression_mediator_cut=compression_mediator_cut,
            ),
            **_diag(
                kept,
                "kept",
                broad_start_pct=broad_start_pct,
                resolution_cut=resolution_cut,
                mediator_cut=mediator_cut,
                path_cut=path_cut,
                compression_resolution_cut=compression_resolution_cut,
                compression_mediator_cut=compression_mediator_cut,
            ),
        }
        diag_blocks.append(diag)
    return pd.DataFrame(row_blocks), pd.DataFrame(diag_blocks)


def _pick_best(summary_df: pd.DataFrame) -> pd.DataFrame:
    survivors = summary_df[
        (summary_df["mean_delta_recall_at_5000"].astype(float) >= -0.002)
        & (summary_df["mean_delta_mrr"].astype(float) >= -0.0002)
    ].copy()
    if survivors.empty:
        survivors = summary_df.copy()
    order = [
        "horizon",
        "mean_kept_top100_broad_low_signal_share",
        "mean_kept_top100_weak_compression_share",
        "mean_kept_top100_top_target_share",
        "mean_delta_positive_rate",
        "mean_delta_recall_at_2000",
        "mean_delta_mrr",
    ]
    ascending = [True, True, True, True, False, False, False]
    best = survivors.sort_values(order, ascending=ascending).groupby("horizon", as_index=False).head(1).reset_index(drop=True)
    return best


def _write_summary(summary_df: pd.DataFrame, best_df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Candidate Generation v3 Threshold Sweep",
        "",
        "This note summarizes a narrow historical calibration of the new broad anchored candidate-generation gate.",
        "",
        "The sweep is post hoc on the cached historical panel, so it is fast and useful for calibration, but it is not yet a full rebuilt historical pipeline.",
        "",
    ]
    for row in best_df.sort_values("horizon").itertuples(index=False):
        lines.extend(
            [
                f"## Horizon {int(row.horizon)}",
                f"- broad start pct: {float(row.broad_start_pct):.2f}",
                f"- min resolution: {float(row.resolution_cut):.2f}",
                f"- min mediator specificity: {float(row.mediator_cut):.2f}",
                f"- min path support raw: {float(row.path_cut):.1f}",
                f"- mean delta positive rate: {float(row.mean_delta_positive_rate):+.6f}",
                f"- mean delta Recall@500: {float(row.mean_delta_recall_at_500):+.6f}",
                f"- mean delta Recall@2000: {float(row.mean_delta_recall_at_2000):+.6f}",
                f"- mean delta Recall@5000: {float(row.mean_delta_recall_at_5000):+.6f}",
                f"- mean delta MRR: {float(row.mean_delta_mrr):+.6f}",
                f"- kept top100 broad low-signal share: {float(row.mean_kept_top100_broad_low_signal_share):.3f}",
                f"- kept top100 weak compression share: {float(row.mean_kept_top100_weak_compression_share):.3f}",
                "",
            ]
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    panel_df = pd.read_parquet(args.panel_path)
    panel_df = _ensure_panel_cols(panel_df)
    frontier_df = pd.read_csv(args.frontier_path, low_memory=False)
    frontier_df = _ensure_panel_cols(frontier_df)

    broads = _parse_floats(args.broad_start_pcts)
    resolutions = _parse_floats(args.resolution_cuts)
    mediators = _parse_floats(args.mediator_cuts)
    paths = _parse_floats(args.path_cuts)
    k_values = _parse_ints(args.k_values)

    cutoff_rows: list[pd.DataFrame] = []
    diag_rows: list[pd.DataFrame] = []
    config_rows: list[dict] = []
    current_rows: list[dict] = []

    for broad_start_pct, resolution_cut, mediator_cut, path_cut in itertools.product(broads, resolutions, mediators, paths):
        cut_df, diag_df = _evaluate_panel_config(
            panel_df=panel_df,
            broad_start_pct=float(broad_start_pct),
            resolution_cut=float(resolution_cut),
            mediator_cut=float(mediator_cut),
            path_cut=float(path_cut),
            compression_resolution_cut=float(args.compression_resolution_cut),
            compression_mediator_cut=float(args.compression_mediator_cut),
            k_values=k_values,
        )
        cut_df["broad_start_pct"] = float(broad_start_pct)
        cut_df["resolution_cut"] = float(resolution_cut)
        cut_df["mediator_cut"] = float(mediator_cut)
        cut_df["path_cut"] = float(path_cut)
        diag_df["broad_start_pct"] = float(broad_start_pct)
        diag_df["resolution_cut"] = float(resolution_cut)
        diag_df["mediator_cut"] = float(mediator_cut)
        diag_df["path_cut"] = float(path_cut)
        cutoff_rows.append(cut_df)
        diag_rows.append(diag_df)

    cutoff_eval = pd.concat(cutoff_rows, ignore_index=True)
    diag_eval = pd.concat(diag_rows, ignore_index=True)
    cutoff_eval.to_csv(out_dir / "threshold_sweep_cutoff_eval.csv", index=False)
    diag_eval.to_csv(out_dir / "threshold_sweep_diagnostics.csv", index=False)

    summary = (
        cutoff_eval.groupby(["horizon", "broad_start_pct", "resolution_cut", "mediator_cut", "path_cut"], as_index=False)
        .agg(
            mean_candidate_keep_rate=("candidate_keep_rate", "mean"),
            mean_delta_positive_rate=("delta_positive_rate", "mean"),
            mean_delta_mrr=("delta_mrr", "mean"),
            mean_delta_recall_at_100=("delta_recall_at_100", "mean"),
            mean_delta_recall_at_500=("delta_recall_at_500", "mean"),
            mean_delta_recall_at_2000=("delta_recall_at_2000", "mean"),
            mean_delta_recall_at_5000=("delta_recall_at_5000", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
    )
    diag_summary = (
        diag_eval.groupby(["horizon", "broad_start_pct", "resolution_cut", "mediator_cut", "path_cut"], as_index=False)
        .agg(
            mean_base_top100_broad_share=("base_top100_broad_share", "mean"),
            mean_kept_top100_broad_share=("kept_top100_broad_share", "mean"),
            mean_base_top100_weak_compression_share=("base_top100_weak_compression_share", "mean"),
            mean_kept_top100_weak_compression_share=("kept_top100_weak_compression_share", "mean"),
            mean_base_top100_broad_low_signal_share=("base_top100_broad_low_signal_share", "mean"),
            mean_kept_top100_broad_low_signal_share=("kept_top100_broad_low_signal_share", "mean"),
            mean_base_top100_top_target_share=("base_top100_top_target_share", "mean"),
            mean_kept_top100_top_target_share=("kept_top100_top_target_share", "mean"),
        )
    )
    summary = summary.merge(diag_summary, on=["horizon", "broad_start_pct", "resolution_cut", "mediator_cut", "path_cut"], how="left")
    summary.to_csv(out_dir / "threshold_sweep_summary.csv", index=False)

    best = _pick_best(summary)
    best.to_csv(out_dir / "threshold_sweep_best_configs.csv", index=False)
    _write_summary(summary, best, out_dir / "threshold_sweep_summary.md")

    # Cheap post hoc current-frontier comparison for the selected config by horizon.
    for row in best.itertuples(index=False):
        horizon = int(row.horizon)
        sub = frontier_df[frontier_df["horizon"].astype(int) == horizon].sort_values("surface_rank").reset_index(drop=True).copy()
        kept = _apply_gate(
            sub,
            broad_start_pct=float(row.broad_start_pct),
            resolution_cut=float(row.resolution_cut),
            mediator_cut=float(row.mediator_cut),
            path_cut=float(row.path_cut),
            compression_resolution_cut=float(args.compression_resolution_cut),
            compression_mediator_cut=float(args.compression_mediator_cut),
        )
        current_rows.append(
            {
                "horizon": horizon,
                "broad_start_pct": float(row.broad_start_pct),
                "resolution_cut": float(row.resolution_cut),
                "mediator_cut": float(row.mediator_cut),
                "path_cut": float(row.path_cut),
                "base_rows": int(len(sub)),
                "kept_rows": int(len(kept)),
                **_diag(
                    sub,
                    "base",
                    broad_start_pct=float(row.broad_start_pct),
                    resolution_cut=float(row.resolution_cut),
                    mediator_cut=float(row.mediator_cut),
                    path_cut=float(row.path_cut),
                    compression_resolution_cut=float(args.compression_resolution_cut),
                    compression_mediator_cut=float(args.compression_mediator_cut),
                ),
                **_diag(
                    kept,
                    "kept",
                    broad_start_pct=float(row.broad_start_pct),
                    resolution_cut=float(row.resolution_cut),
                    mediator_cut=float(row.mediator_cut),
                    path_cut=float(row.path_cut),
                    compression_resolution_cut=float(args.compression_resolution_cut),
                    compression_mediator_cut=float(args.compression_mediator_cut),
                ),
            }
        )
    current_df = pd.DataFrame(current_rows)
    current_df.to_csv(out_dir / "threshold_sweep_current_frontier_posthoc.csv", index=False)

    manifest = {
        "panel_path": str(args.panel_path),
        "frontier_path": str(args.frontier_path),
        "broad_start_pcts": broads,
        "resolution_cuts": resolutions,
        "mediator_cuts": mediators,
        "path_cuts": paths,
        "compression_resolution_cut": float(args.compression_resolution_cut),
        "compression_mediator_cut": float(args.compression_mediator_cut),
        "k_values": k_values,
        "n_configs": int(len(summary)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote: {out_dir / 'threshold_sweep_summary.csv'}")


if __name__ == "__main__":
    main()
