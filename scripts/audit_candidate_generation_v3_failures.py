from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit current frontier failure modes relevant for candidate generation v3.")
    parser.add_argument(
        "--frontier",
        default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv",
        dest="frontier_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--broad-start-pct", type=float, default=0.80, dest="broad_start_pct")
    parser.add_argument("--resolution-cut", type=float, default=0.15, dest="resolution_cut")
    parser.add_argument("--mediator-cut", type=float, default=0.25, dest="mediator_cut")
    parser.add_argument("--topk", default="100,500", dest="topk")
    return parser.parse_args()


def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "endpoint_broadness_pct" not in out.columns and "endpoint_broadness_raw" in out.columns:
        broad = pd.to_numeric(out["endpoint_broadness_raw"], errors="coerce").fillna(0.0).astype(float)
        lo, hi = float(broad.min()), float(broad.max())
        if hi <= lo:
            out["endpoint_broadness_pct"] = 0.0
        else:
            out["endpoint_broadness_pct"] = ((broad - lo) / (hi - lo)).clip(0.0, 1.0)
    if "compression_failure_reason" not in out.columns:
        resolution = pd.to_numeric(out.get("endpoint_resolution_score", 0.0), errors="coerce").fillna(0.0).astype(float)
        mediator_spec = pd.to_numeric(out.get("focal_mediator_specificity_score", 0.5), errors="coerce").fillna(0.5).astype(float)
        mediator_present = out.get("focal_mediator_label", pd.Series("", index=out.index)).fillna("").astype(str).str.strip().ne("")
        out["compression_failure_reason"] = ""
        both = (resolution < 0.15) & mediator_present & (mediator_spec < 0.35)
        out.loc[both, "compression_failure_reason"] = "broad_endpoints_and_generic_mediator"
        out.loc[(out["compression_failure_reason"] == "") & (resolution < 0.15), "compression_failure_reason"] = "broad_endpoints"
        out.loc[
            (out["compression_failure_reason"] == "") & mediator_present & (mediator_spec < 0.35),
            "compression_failure_reason",
        ] = "generic_mediator"
    return out


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.frontier_path, low_memory=False)
    df = _ensure_cols(df)
    topks = [int(x.strip()) for x in str(args.topk).split(",") if x.strip()]

    summary_rows: list[dict] = []
    flagged_rows: list[pd.DataFrame] = []

    for horizon, sub in df.groupby("horizon"):
        sub = sub.sort_values("surface_rank").reset_index(drop=True)
        for k in topks:
            top = sub.head(int(k)).copy()
            if top.empty:
                continue
            broad = pd.to_numeric(top["endpoint_broadness_pct"], errors="coerce").fillna(0.0).astype(float) >= float(args.broad_start_pct)
            resolution = pd.to_numeric(top.get("endpoint_resolution_score", 0.0), errors="coerce").fillna(0.0).astype(float)
            mediator_spec = pd.to_numeric(top.get("focal_mediator_specificity_score", 0.5), errors="coerce").fillna(0.5).astype(float)
            mediator_count = pd.to_numeric(top.get("mediator_count", 0), errors="coerce").fillna(0).astype(int)
            motif_count = pd.to_numeric(top.get("motif_count", 0), errors="coerce").fillna(0).astype(int)
            anchored = top.get("candidate_scope_bucket", pd.Series("", index=top.index)).astype(str).eq("anchored_progression")
            low_resolution = resolution < float(args.resolution_cut)
            generic_mediator = mediator_spec < float(args.mediator_cut)
            weak_compression = top["compression_failure_reason"].astype(str).ne("")
            serial_single = top.get("local_topology_class", pd.Series("", index=top.index)).astype(str).eq("serial_path") & mediator_count.le(1)
            broad_anchored_low_signal = anchored & broad & low_resolution & generic_mediator & motif_count.lt(2) & mediator_count.lt(2)

            summary_rows.append(
                {
                    "horizon": int(horizon),
                    "topk": int(k),
                    "n": int(len(top)),
                    "anchored_share": float(anchored.mean()),
                    "broad_endpoint_share": float(broad.mean()),
                    "low_resolution_share": float(low_resolution.mean()),
                    "generic_mediator_share": float(generic_mediator.mean()),
                    "weak_compression_share": float(weak_compression.mean()),
                    "serial_single_mediator_share": float(serial_single.mean()),
                    "broad_anchored_low_signal_share": float(broad_anchored_low_signal.mean()),
                    "unique_targets": int(top["v_label"].astype(str).nunique()) if "v_label" in top.columns else 0,
                    "unique_sources": int(top["u_label"].astype(str).nunique()) if "u_label" in top.columns else 0,
                }
            )

            flagged = top.loc[broad_anchored_low_signal, [
                c
                for c in [
                    "horizon",
                    "surface_rank",
                    "u_label",
                    "v_label",
                    "candidate_subfamily",
                    "candidate_scope_bucket",
                    "endpoint_broadness_pct",
                    "endpoint_resolution_score",
                    "focal_mediator_label",
                    "focal_mediator_specificity_score",
                    "path_support_raw",
                    "motif_count",
                    "mediator_count",
                    "local_topology_class",
                    "compression_failure_reason",
                ]
                if c in top.columns
            ]].copy()
            flagged["topk"] = int(k)
            flagged_rows.append(flagged)

    summary_df = pd.DataFrame(summary_rows).sort_values(["horizon", "topk"]).reset_index(drop=True)
    summary_df.to_csv(out_dir / "candidate_generation_v3_audit_summary.csv", index=False)

    flagged_df = pd.concat(flagged_rows, ignore_index=True) if flagged_rows else pd.DataFrame()
    flagged_df.to_csv(out_dir / "candidate_generation_v3_flagged_rows.csv", index=False)

    lines = [
        "# Candidate Generation v3 Audit",
        "",
        "This note audits the current surfaced frontier for failure modes that should be handled upstream in candidate generation.",
        "",
    ]
    for row in summary_df.itertuples(index=False):
        lines.extend(
            [
                f"## Horizon {int(row.horizon)} Top {int(row.topk)}",
                f"- anchored share: {float(row.anchored_share):.3f}",
                f"- broad endpoint share: {float(row.broad_endpoint_share):.3f}",
                f"- low-resolution share: {float(row.low_resolution_share):.3f}",
                f"- generic mediator share: {float(row.generic_mediator_share):.3f}",
                f"- weak compression share: {float(row.weak_compression_share):.3f}",
                f"- serial single-mediator share: {float(row.serial_single_mediator_share):.3f}",
                f"- broad anchored low-signal share: {float(row.broad_anchored_low_signal_share):.3f}",
                f"- unique sources: {int(row.unique_sources)}",
                f"- unique targets: {int(row.unique_targets)}",
                "",
            ]
        )
    (out_dir / "candidate_generation_v3_audit.md").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "frontier_path": str(args.frontier_path),
                "broad_start_pct": float(args.broad_start_pct),
                "resolution_cut": float(args.resolution_cut),
                "mediator_cut": float(args.mediator_cut),
                "topk": topks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote: {out_dir / 'candidate_generation_v3_audit_summary.csv'}")


if __name__ == "__main__":
    main()
