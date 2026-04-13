from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a narrow robustness sweep for compression-confidence weights.")
    parser.add_argument(
        "--frontier",
        default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv",
        dest="frontier_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument(
        "--weight-sets",
        default=(
            "baseline=0.55,0.30,0.15;"
            "resolution_heavier=0.60,0.25,0.15;"
            "support_heavier=0.50,0.30,0.20;"
            "mediator_heavier=0.45,0.35,0.20;"
            "balanced=0.50,0.25,0.25"
        ),
    )
    parser.add_argument("--windows", default="100,250,500")
    parser.add_argument("--low-quantile", type=float, default=0.25, dest="low_quantile")
    return parser.parse_args()


def _parse_weight_sets(raw: str) -> list[tuple[str, float, float, float]]:
    out: list[tuple[str, float, float, float]] = []
    for chunk in str(raw).split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, values = chunk.split("=", 1)
        parts = [float(x.strip()) for x in values.split(",")]
        if len(parts) != 3:
            raise ValueError(f"Expected 3 weights for {name}, got {parts}")
        total = sum(parts)
        if total <= 0:
            raise ValueError(f"Non-positive weight sum for {name}")
        normed = tuple(x / total for x in parts)
        out.append((name.strip(), normed[0], normed[1], normed[2]))
    if not out:
        raise ValueError("No weight sets parsed")
    return out


def _parse_windows(raw: str) -> list[int]:
    return [int(float(x.strip())) for x in str(raw).split(",") if x.strip()]


def _load_frontier(path: Path) -> pd.DataFrame:
    usecols = [
        "candidate_id",
        "horizon",
        "surface_rank",
        "u",
        "v",
        "u_label",
        "v_label",
        "candidate_subfamily",
        "candidate_scope_bucket",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "path_support_raw",
    ]
    df = pd.read_csv(path, usecols=usecols)
    df["candidate_id"] = df["candidate_id"].fillna("").astype(str)
    for col in ["u", "v", "u_label", "v_label", "candidate_subfamily", "candidate_scope_bucket"]:
        df[col] = df[col].fillna("").astype(str)
    for col in ["horizon", "surface_rank"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col, default in [
        ("endpoint_resolution_score", 0.0),
        ("focal_mediator_specificity_score", 0.5),
        ("path_support_raw", 0.0),
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default).astype(float)
    return df


def _compression_score(df: pd.DataFrame, w_res: float, w_med: float, w_top: float) -> pd.Series:
    topology_term = np.tanh(df["path_support_raw"].astype(float) / 4.0)
    return (
        w_res * df["endpoint_resolution_score"].astype(float)
        + w_med * df["focal_mediator_specificity_score"].astype(float)
        + w_top * topology_term.astype(float)
    ).clip(0.0, 1.0)


def _rank_corr(a: pd.Series, b: pd.Series) -> float:
    if len(a) <= 1:
        return 1.0
    return float(a.rank(method="average").corr(b.rank(method="average"), method="pearson"))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return float(len(a & b)) / float(len(a | b))


def _low_confidence_ids(frame: pd.DataFrame, score_col: str, quantile: float) -> set[str]:
    if frame.empty:
        return set()
    cut = float(frame[score_col].quantile(quantile))
    chosen = frame.loc[frame[score_col] <= cut, "candidate_id"].astype(str)
    return set(chosen.tolist())


def run() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    weight_sets = _parse_weight_sets(args.weight_sets)
    windows = _parse_windows(args.windows)
    frontier = _load_frontier(Path(args.frontier_path))

    baseline_name = weight_sets[0][0]
    variants = {}
    for name, w_res, w_med, w_top in weight_sets:
        variants[name] = {
            "resolution_weight": float(w_res),
            "mediator_weight": float(w_med),
            "topology_weight": float(w_top),
        }
        frontier[f"compression_confidence__{name}"] = _compression_score(frontier, w_res, w_med, w_top)

    detail_rows: list[dict] = []
    summary_rows: list[dict] = []
    exemplar_rows: list[dict] = []

    for horizon, horizon_df in frontier.groupby("horizon"):
        ordered = horizon_df.sort_values(["surface_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
        baseline_col = f"compression_confidence__{baseline_name}"
        for window in windows:
            sub = ordered.head(window).copy()
            baseline_low = _low_confidence_ids(sub, baseline_col, float(args.low_quantile))
            baseline_low_cut = float(sub[baseline_col].quantile(float(args.low_quantile))) if len(sub) else 0.0
            exemplar_base = sub.sort_values([baseline_col, "surface_rank"], ascending=[True, True]).head(10)
            for row in exemplar_base.itertuples(index=False):
                exemplar_rows.append(
                    {
                        "horizon": int(horizon),
                        "window": int(window),
                        "variant": baseline_name,
                        "candidate_id": str(row.candidate_id),
                        "surface_rank": int(row.surface_rank),
                        "u_label": str(row.u_label),
                        "v_label": str(row.v_label),
                        "candidate_scope_bucket": str(row.candidate_scope_bucket),
                        "candidate_subfamily": str(row.candidate_subfamily),
                        "compression_confidence": float(getattr(row, baseline_col)),
                    }
                )
            for name, _, _, _ in weight_sets:
                score_col = f"compression_confidence__{name}"
                low_ids = _low_confidence_ids(sub, score_col, float(args.low_quantile))
                row = {
                    "horizon": int(horizon),
                    "window": int(window),
                    "variant": name,
                    "mean_confidence": float(sub[score_col].mean()) if len(sub) else 0.0,
                    "sd_confidence": float(sub[score_col].std(ddof=0)) if len(sub) else 0.0,
                    "min_confidence": float(sub[score_col].min()) if len(sub) else 0.0,
                    "max_confidence": float(sub[score_col].max()) if len(sub) else 0.0,
                    "low_confidence_cut": float(sub[score_col].quantile(float(args.low_quantile))) if len(sub) else 0.0,
                    "baseline_low_confidence_cut": baseline_low_cut,
                    "rank_corr_vs_baseline": _rank_corr(sub[baseline_col], sub[score_col]) if len(sub) else 1.0,
                    "low_confidence_jaccard_vs_baseline": _jaccard(baseline_low, low_ids),
                    "low_confidence_count": int(len(low_ids)),
                    "low_confidence_share": float(len(low_ids)) / float(max(1, len(sub))),
                }
                detail_rows.append(row)
                exemplar_sub = sub.sort_values([score_col, "surface_rank"], ascending=[True, True]).head(10)
                for ex in exemplar_sub.itertuples(index=False):
                    exemplar_rows.append(
                        {
                            "horizon": int(horizon),
                            "window": int(window),
                            "variant": name,
                            "candidate_id": str(ex.candidate_id),
                            "surface_rank": int(ex.surface_rank),
                            "u_label": str(ex.u_label),
                            "v_label": str(ex.v_label),
                            "candidate_scope_bucket": str(ex.candidate_scope_bucket),
                            "candidate_subfamily": str(ex.candidate_subfamily),
                            "compression_confidence": float(getattr(ex, score_col)),
                        }
                    )
        for name, _, _, _ in weight_sets:
            block = pd.DataFrame([r for r in detail_rows if r["horizon"] == int(horizon) and r["variant"] == name])
            if block.empty:
                continue
            summary_rows.append(
                {
                    "horizon": int(horizon),
                    "variant": name,
                    **variants[name],
                    "mean_rank_corr_vs_baseline": float(block["rank_corr_vs_baseline"].mean()),
                    "mean_low_confidence_jaccard_vs_baseline": float(block["low_confidence_jaccard_vs_baseline"].mean()),
                    "mean_low_confidence_share": float(block["low_confidence_share"].mean()),
                    "mean_confidence_across_windows": float(block["mean_confidence"].mean()),
                }
            )

    detail_df = pd.DataFrame(detail_rows).sort_values(["horizon", "window", "variant"]).reset_index(drop=True)
    summary_df = pd.DataFrame(summary_rows).sort_values(["horizon", "variant"]).reset_index(drop=True)
    exemplars_df = pd.DataFrame(exemplar_rows).sort_values(["horizon", "window", "variant", "compression_confidence", "surface_rank"]).reset_index(drop=True)

    detail_df.to_csv(out_dir / "compression_weight_detail.csv", index=False)
    summary_df.to_csv(out_dir / "compression_weight_summary.csv", index=False)
    exemplars_df.to_csv(out_dir / "compression_weight_low_confidence_examples.csv", index=False)

    lines: list[str] = []
    lines.append("# Compression Weight Robustness")
    lines.append("")
    lines.append(f"- frontier: `{args.frontier_path}`")
    lines.append(f"- low-confidence quantile within window: `{float(args.low_quantile):.2f}`")
    lines.append(f"- windows: `{', '.join(str(x) for x in windows)}`")
    lines.append("")
    lines.append("## Weight sets")
    lines.append("")
    for name, cfg in variants.items():
        lines.append(
            f"- `{name}`: resolution={cfg['resolution_weight']:.2f}, mediator={cfg['mediator_weight']:.2f}, topology={cfg['topology_weight']:.2f}"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for horizon in sorted(summary_df["horizon"].unique().tolist()) if not summary_df.empty else []:
        lines.append(f"### h={int(horizon)}")
        lines.append("")
        sub = summary_df.loc[summary_df["horizon"] == int(horizon)].copy()
        for row in sub.itertuples(index=False):
            lines.append(
                f"- `{row.variant}`: mean rank-corr vs baseline = {float(row.mean_rank_corr_vs_baseline):.3f}, mean low-confidence Jaccard = {float(row.mean_low_confidence_jaccard_vs_baseline):.3f}, mean low-confidence share = {float(row.mean_low_confidence_share):.3f}"
            )
        lines.append("")

    (out_dir / "compression_weight_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "frontier_path": args.frontier_path,
        "weight_sets": variants,
        "windows": windows,
        "low_quantile": float(args.low_quantile),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
