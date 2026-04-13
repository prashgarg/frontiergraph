from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_PACKAGE = REPO_ROOT / "outputs/paper/98_objective_specific_frontier_packages_endpoint_first/within_field_top100_pool2000/package.csv"
RERANKED = REPO_ROOT / "outputs/paper/110_llm_screening_within_field_v3_analysis/within_field_llm_reranked_package.csv"
BASELINE_TOP20 = REPO_ROOT / "outputs/paper/110_llm_screening_within_field_v3_analysis/within_field_baseline_top20_summary.csv"
RERANKED_TOP20 = REPO_ROOT / "outputs/paper/110_llm_screening_within_field_v3_analysis/within_field_reranked_top20_summary.csv"
OUT_DIR = REPO_ROOT / "outputs/paper/111_within_field_llm_browse_package"


def _merge_missing_columns(left: pd.DataFrame, right: pd.DataFrame, on: list[str]) -> pd.DataFrame:
    missing = [c for c in right.columns if c not in left.columns and c not in on]
    if not missing:
        return left.copy()
    return left.merge(right[on + missing], on=on, how="left")


def _top5_lines(df: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    for row in df.head(5).itertuples(index=False):
        lines.append(
            f"  - {row.u_label} -> {row.focal_mediator_label} -> {row.v_label} | "
            f"llm_rank={row.llm_rank}, shelf_rank={row.shelf_rank}, surface_rank={row.surface_rank}"
        )
    return lines


def _build_summary_md(summary: pd.DataFrame, top20_compare: pd.DataFrame, package: pd.DataFrame) -> str:
    lines = [
        "# Within-Field LLM Browse Package",
        "",
        "Endpoint-first within-field shelves after:",
        "",
        "- weak veto from prompt `E`",
        "- pairwise within-field reranking from prompt `H`",
        "- scalar prompt `G` as a secondary diagnostic and tie-breaker",
        "",
        "The package contains surviving candidates only, so some shelves now have fewer than 100 rows.",
        "",
    ]
    for horizon in sorted(summary["horizon"].unique()):
        lines.append(f"## Horizon {horizon}")
        hsum = summary[summary["horizon"] == horizon].sort_values("field_slug")
        hcmp = top20_compare[top20_compare["horizon"] == horizon].sort_values("field_slug")
        hpack = package[package["horizon"] == horizon].sort_values(["field_slug", "llm_rank"])
        for row in hsum.itertuples(index=False):
            lines.append(f"### {row.field_slug}")
            lines.append(f"- surviving rows: {row.n_rows}")
            lines.append(f"- unique targets: {row.unique_targets}")
            lines.append(f"- top target share: {row.top_target_share:.3f}")
            lines.append(f"- broad share: {row.broad_share:.3f}")
            lines.append(f"- low-compression share: {row.low_compression_share:.3f}")
            lines.append(f"- mean scalar score: {row.mean_overall_screening_value:.3f}")
            cmp_row = hcmp[hcmp["field_slug"] == row.field_slug].iloc[0]
            lines.append(
                f"- top-20 broad share: {cmp_row.baseline_broad_share:.3f} -> {cmp_row.reranked_broad_share:.3f}"
            )
            lines.append(
                f"- top-20 low-compression share: {cmp_row.baseline_low_compression_share:.3f} -> {cmp_row.reranked_low_compression_share:.3f}"
            )
            lines.append(
                f"- top-20 top-target share: {cmp_row.baseline_top_target_share:.3f} -> {cmp_row.reranked_top_target_share:.3f}"
            )
            lines.append("- Top 5:")
            lines.extend(_top5_lines(hpack[hpack["field_slug"] == row.field_slug]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = pd.read_csv(BASE_PACKAGE)
    reranked = pd.read_csv(RERANKED)

    merged = _merge_missing_columns(
        reranked,
        base,
        on=["horizon", "field_slug", "surface_rank", "u_label", "focal_mediator_label", "v_label"],
    )

    merged = merged.sort_values(["horizon", "field_slug", "llm_rank", "surface_rank", "candidate_id"]).reset_index(drop=True)
    merged.to_csv(OUT_DIR / "package.csv", index=False)
    merged.to_parquet(OUT_DIR / "package.parquet", index=False)

    top20 = merged.groupby(["horizon", "field_slug"], sort=True, group_keys=False).head(20).copy()
    top20.to_csv(OUT_DIR / "top20.csv", index=False)

    summary = (
        merged.groupby(["horizon", "field_slug"], sort=True)
        .agg(
            n_rows=("candidate_id", "size"),
            unique_targets=("v_label", "nunique"),
            unique_sources=("u_label", "nunique"),
            top_target_share=("v_label", lambda s: s.value_counts(normalize=True, dropna=False).iloc[0]),
            broad_share=("endpoint_broadness_pct", lambda s: (s >= 0.85).mean()),
            low_compression_share=("compression_confidence", lambda s: (s < 0.35).mean()),
            mean_overall_screening_value=("overall_screening_value", "mean"),
            mean_pairwise_copeland_score=("pairwise_copeland_score", "mean"),
            mean_surface_rank=("surface_rank", "mean"),
            mean_llm_rank=("llm_rank", "mean"),
        )
        .reset_index()
    )
    summary.to_csv(OUT_DIR / "summary.csv", index=False)

    baseline_top20 = pd.read_csv(BASELINE_TOP20)
    reranked_top20 = pd.read_csv(RERANKED_TOP20)
    top20_compare = baseline_top20.merge(
        reranked_top20,
        on=["horizon", "field_slug", "top_k"],
        how="outer",
        suffixes=("_baseline", "_reranked"),
    )
    top20_compare = top20_compare.rename(
        columns={
            "top_target_share_baseline": "baseline_top_target_share",
            "top_target_share_reranked": "reranked_top_target_share",
            "broad_share_baseline": "baseline_broad_share",
            "broad_share_reranked": "reranked_broad_share",
            "low_compression_share_baseline": "baseline_low_compression_share",
            "low_compression_share_reranked": "reranked_low_compression_share",
            "mean_overall_screening_value_baseline": "baseline_mean_scalar",
            "mean_overall_screening_value_reranked": "reranked_mean_scalar",
        }
    )
    top20_compare.to_csv(OUT_DIR / "top20_compare.csv", index=False)

    summary_md = _build_summary_md(summary, top20_compare, merged)
    (OUT_DIR / "summary.md").write_text(summary_md)

    manifest = {
        "base_package": str(BASE_PACKAGE.relative_to(REPO_ROOT)),
        "reranked_analysis_package": str(RERANKED.relative_to(REPO_ROOT)),
        "n_rows": int(len(merged)),
        "n_top20_rows": int(len(top20)),
        "n_shelves": int(summary.shape[0]),
        "workflow": {
            "weak_veto": "E fail + substantive failure mode + veto_confidence>=4 + G<=2",
            "main_rerank": "repeated H pairwise within-field consensus",
            "secondary_tiebreak": "G overall_screening_value then original shelf rank",
        },
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
