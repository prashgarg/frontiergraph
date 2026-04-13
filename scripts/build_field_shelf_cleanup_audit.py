from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd


FIELD_SHELF_DEFS = [
    {
        "slug": "macro-finance",
        "title": "Macro and finance",
        "match_tokens": ["debt", "monetary", "inflation", "credit", "bank", "interest", "aggregate demand"],
    },
    {
        "slug": "development-urban",
        "title": "Development and urban",
        "match_tokens": ["urban", "city", "education", "wage", "inequality", "development", "human capital"],
    },
    {
        "slug": "trade-globalization",
        "title": "Trade and globalization",
        "match_tokens": ["trade", "export", "import", "sanctions", "globalization", "fdi"],
    },
    {
        "slug": "climate-energy",
        "title": "Climate and energy",
        "match_tokens": ["carbon", "emissions", "pollution", "environmental quality", "energy", "oil", "gas", "electricity", "mineral rents"],
    },
    {
        "slug": "innovation-productivity",
        "title": "Innovation and productivity",
        "match_tokens": ["innovation", "green innovation", "technology", "r&d", "productivity", "complexity"],
    },
]


PACKAGE_SPECS = [
    {
        "package_name": "global_exploratory_top100_pool5000",
        "path": "outputs/paper/95_objective_specific_frontier_packages/global_exploratory_top100_pool5000/package.csv",
        "kind": "global_exploratory",
    },
    {
        "package_name": "within_field_top100_pool2000",
        "path": "outputs/paper/95_objective_specific_frontier_packages/within_field_top100_pool2000/package.csv",
        "kind": "within_field",
    },
    {
        "package_name": "global_scan_top250_pool2000",
        "path": "outputs/paper/95_objective_specific_frontier_packages/global_scan_top250_pool2000/package.csv",
        "kind": "global_scan",
    },
    {
        "package_name": "global_scan_top1000_pool2000",
        "path": "outputs/paper/95_objective_specific_frontier_packages/global_scan_top1000_pool2000/package.csv",
        "kind": "global_scan",
    },
]


METHOD_LIKE_PATTERN = re.compile(
    r"\b(?:model|method|approach|framework|dataset|statistics|project|system|platform|committee|coalition|study|survey)\b",
    flags=re.IGNORECASE,
)


def _normalize_text(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9& ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "fdi": "fdi",
        "r d": "r&d",
        "wtp": "willingness to pay",
        "co2 emissions": "carbon emissions",
    }
    return alias_map.get(text, text)


def _match_field_sources(row: pd.Series, field_slug: str) -> dict[str, bool]:
    field_def = next((x for x in FIELD_SHELF_DEFS if x["slug"] == field_slug), None)
    if field_def is None:
        return {"endpoint_match": False, "mediator_match": False}
    endpoint_text = _normalize_text(f"{row.get('u_label', '')} {row.get('v_label', '')}")
    mediator_text = _normalize_text(str(row.get("focal_mediator_label", "")))
    tokens = [_normalize_text(tok) for tok in field_def["match_tokens"]]
    endpoint_match = any(tok and tok in endpoint_text for tok in tokens)
    mediator_match = any(tok and tok in mediator_text for tok in tokens)
    return {"endpoint_match": endpoint_match, "mediator_match": mediator_match}


def _add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    for col, default in [
        ("endpoint_broadness_pct", 0.0),
        ("endpoint_resolution_score", 0.0),
        ("focal_mediator_specificity_score", 0.0),
        ("compression_confidence", 0.0),
    ]:
        if col not in work.columns:
            work[col] = default
    if "focal_mediator_label" not in work.columns:
        work["focal_mediator_label"] = ""
    work["is_anchored"] = work["candidate_scope_bucket"].astype(str).eq("anchored_progression")
    work["is_causal_to_identified"] = work["candidate_subfamily"].astype(str).eq("causal_to_identified")
    work["is_broad"] = work["endpoint_broadness_pct"].fillna(0).astype(float).ge(0.80)
    work["is_low_compression"] = work["compression_confidence"].fillna(0).astype(float).lt(0.35)
    work["is_method_like_mediator"] = (
        work["focal_mediator_label"].fillna("").astype(str).str.contains(METHOD_LIKE_PATTERN, regex=True)
    )
    work["is_textbook_like"] = (
        work["is_anchored"]
        & work["is_broad"]
        & (
            work["endpoint_resolution_score"].fillna(0).astype(float).lt(0.20)
            | work["focal_mediator_specificity_score"].fillna(0).astype(float).lt(0.35)
        )
    )
    work["flag_count"] = work[
        ["is_broad", "is_low_compression", "is_method_like_mediator", "is_textbook_like"]
    ].sum(axis=1)
    work["flag_labels"] = work.apply(
        lambda row: "|".join(
            label
            for label, col in [
                ("broad_endpoint", "is_broad"),
                ("low_compression", "is_low_compression"),
                ("method_like_mediator", "is_method_like_mediator"),
                ("textbook_like", "is_textbook_like"),
            ]
            if bool(row[col])
        ),
        axis=1,
    )
    return work


def _metric_block(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "n_rows": 0,
            "anchored_share": 0.0,
            "causal_to_identified_share": 0.0,
            "high_broad_share": 0.0,
            "low_compression_share": 0.0,
            "method_like_mediator_share": 0.0,
            "textbook_like_share": 0.0,
            "unique_targets": 0,
            "top_target_share": 0.0,
            "mean_endpoint_resolution": 0.0,
            "mean_compression_confidence": 0.0,
        }
    target_counts = df["v_label"].astype(str).value_counts()
    return {
        "n_rows": int(len(df)),
        "anchored_share": float(df["is_anchored"].mean()),
        "causal_to_identified_share": float(df["is_causal_to_identified"].mean()),
        "high_broad_share": float(df["is_broad"].mean()),
        "low_compression_share": float(df["is_low_compression"].mean()),
        "method_like_mediator_share": float(df["is_method_like_mediator"].mean()),
        "textbook_like_share": float(df["is_textbook_like"].mean()),
        "unique_targets": int(df["v_label"].astype(str).nunique()),
        "top_target_share": float(target_counts.iloc[0] / len(df)) if not target_counts.empty else 0.0,
        "mean_endpoint_resolution": float(df["endpoint_resolution_score"].fillna(0).mean()),
        "mean_compression_confidence": float(df["compression_confidence"].fillna(0).mean()),
    }


def _other_bucket_patterns(df: pd.DataFrame) -> pd.DataFrame:
    other = df[df["field_slug"].astype(str) == "other"].copy()
    rows: list[dict[str, Any]] = []
    if other.empty:
        return pd.DataFrame(
            columns=["horizon", "kind", "label", "count", "share_within_other"]
        )
    for horizon, hdf in other.groupby("horizon"):
        for kind, col in [
            ("target", "v_label"),
            ("source", "u_label"),
            ("theme_pair", "theme_pair_key"),
            ("semantic_family", "semantic_family_key"),
        ]:
            counts = hdf[col].fillna("").astype(str).value_counts().head(10)
            for label, count in counts.items():
                rows.append(
                    {
                        "horizon": int(horizon),
                        "kind": kind,
                        "label": str(label),
                        "count": int(count),
                        "share_within_other": float(count / len(hdf)),
                    }
                )
    return pd.DataFrame(rows)


def _field_support_summary(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    match_info = work.apply(lambda row: _match_field_sources(row, str(row["field_slug"])), axis=1)
    match_df = pd.DataFrame(match_info.tolist())
    work = pd.concat([work.reset_index(drop=True), match_df], axis=1)
    work["support_source"] = "none"
    work.loc[work["endpoint_match"] & ~work["mediator_match"], "support_source"] = "endpoint_only"
    work.loc[~work["endpoint_match"] & work["mediator_match"], "support_source"] = "mediator_only"
    work.loc[work["endpoint_match"] & work["mediator_match"], "support_source"] = "both"
    rows: list[dict[str, Any]] = []
    for (horizon, field_slug), sub in work.groupby(["horizon", "field_slug"], dropna=False):
        counts = sub["support_source"].value_counts()
        rows.append(
            {
                "horizon": int(horizon),
                "field_slug": str(field_slug),
                "n_rows": int(len(sub)),
                "endpoint_only_share": float(counts.get("endpoint_only", 0) / len(sub)),
                "mediator_only_share": float(counts.get("mediator_only", 0) / len(sub)),
                "both_share": float(counts.get("both", 0) / len(sub)),
                "none_share": float(counts.get("none", 0) / len(sub)),
                "duplicate_huv_share": float(1 - sub[["horizon", "u", "v"]].drop_duplicates().shape[0] / len(sub)),
            }
        )
    return pd.DataFrame(rows)


def _render_summary(
    paper_df: pd.DataFrame,
    field_support_df: pd.DataFrame,
    other_patterns_df: pd.DataFrame,
    flagged_df: pd.DataFrame,
    out_path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Field Shelf Cleanup And Paper-Worthiness Audit")
    lines.append("")
    if not paper_df.empty:
        global_scan = paper_df[paper_df["package_name"] == "global_scan_top250_pool2000"].copy()
        if not global_scan.empty:
            lines.append("## Global Scan Top-250")
            for horizon, sub in global_scan.groupby("horizon"):
                row = sub.iloc[0]
                lines.append(
                    f"- `h={int(horizon)}`: anchored `{row['anchored_share']:.3f}`, broad `{row['high_broad_share']:.3f}`, "
                    f"low-compression `{row['low_compression_share']:.3f}`, method-like `{row['method_like_mediator_share']:.3f}`, "
                    f"textbook-like `{row['textbook_like_share']:.3f}`."
                )
            lines.append("")
        within_field = paper_df[paper_df["package_name"] == "within_field_top100_pool2000"].copy()
        if not within_field.empty:
            lines.append("## Within-Field Shelf Read")
            overall = within_field.groupby("horizon").agg(
                {
                    "high_broad_share": "mean",
                    "low_compression_share": "mean",
                    "top_target_share": "mean",
                }
            )
            for horizon, row in overall.iterrows():
                lines.append(
                    f"- `h={int(horizon)}` mean shelf broad share `{row['high_broad_share']:.3f}`, "
                    f"mean low-compression share `{row['low_compression_share']:.3f}`, "
                    f"mean top-target share `{row['top_target_share']:.3f}`."
                )
            lines.append("")
    if not field_support_df.empty:
        lines.append("## Field Assignment Source")
        for horizon, sub in field_support_df.groupby("horizon"):
            mediator_only = sub["mediator_only_share"].mean()
            endpoint_only = sub["endpoint_only_share"].mean()
            both = sub["both_share"].mean()
            lines.append(
                f"- `h={int(horizon)}` average endpoint-only `{endpoint_only:.3f}`, mediator-only `{mediator_only:.3f}`, both `{both:.3f}` across shelves."
            )
        lines.append("")
    if not other_patterns_df.empty:
        lines.append("## Other Bucket")
        other_top = other_patterns_df.sort_values(["horizon", "count"], ascending=[True, False]).groupby("horizon").head(3)
        for horizon, sub in other_top.groupby("horizon"):
            labels = ", ".join(f"{row['kind']}={row['label']}" for _, row in sub.iterrows())
            lines.append(f"- `h={int(horizon)}` top `other` patterns: {labels}.")
        lines.append("")
    if not flagged_df.empty:
        lines.append("## Flagged Examples")
        example_cols = ["package_name", "horizon", "field_slug", "surface_rank", "u_label", "focal_mediator_label", "v_label", "flag_labels"]
        show = flagged_df[example_cols].head(12)
        for _, row in show.iterrows():
            field_part = f"[{row['field_slug']}] " if pd.notna(row["field_slug"]) and str(row["field_slug"]) else ""
            lines.append(
                f"- `{row['package_name']}` `h={int(row['horizon'])}` {field_part}`{row['u_label']} -> {row['focal_mediator_label']} -> {row['v_label']}` :: `{row['flag_labels']}`"
            )
        lines.append("")
    lines.append("## Recommended Cleanup")
    lines.append("- Treat current field shelves as useful browse objects, but not yet clean subfield shelves.")
    lines.append("- Move future field assignment toward endpoint-first matching, with mediator-only matches used only as secondary support.")
    lines.append("- Keep the non-LLM paper-worthiness screen focused on broad anchored progression, low-compression objects, and textbook-like pairings.")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit current objective-specific frontier packages.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/paper/96_field_shelf_cleanup_audit"),
        help="Output directory",
    )
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    paper_rows: list[dict[str, Any]] = []
    flagged_frames: list[pd.DataFrame] = []
    within_field_df: pd.DataFrame | None = None

    for spec in PACKAGE_SPECS:
        path = Path(spec["path"])
        df = pd.read_csv(path, low_memory=False)
        df["package_name"] = spec["package_name"]
        df["package_kind"] = spec["kind"]
        if "field_slug" not in df.columns:
            df["field_slug"] = ""
        df = _add_quality_flags(df)
        group_cols = ["package_name", "package_kind", "horizon"]
        if spec["kind"] == "within_field":
            within_field_df = df.copy()
            group_cols = ["package_name", "package_kind", "horizon", "field_slug"]
        for keys, sub in df.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(group_cols, keys))
            row.update(_metric_block(sub))
            paper_rows.append(row)
        flagged = df[df["flag_count"] > 0].copy()
        flagged["field_slug"] = flagged["field_slug"].fillna("")
        flagged_frames.append(flagged)

    paper_df = pd.DataFrame(paper_rows).sort_values(
        ["package_name", "horizon", "field_slug"] if "field_slug" in pd.DataFrame(paper_rows).columns else ["package_name", "horizon"]
    )
    flagged_df = pd.concat(flagged_frames, ignore_index=True)
    flagged_df = flagged_df.sort_values(
        ["package_name", "horizon", "field_slug", "surface_rank", "flag_count"],
        ascending=[True, True, True, True, False],
    )
    flagged_keep_cols = [
        "package_name",
        "horizon",
        "field_slug",
        "surface_rank",
        "frontier_rank",
        "u_label",
        "focal_mediator_label",
        "v_label",
        "candidate_scope_bucket",
        "candidate_subfamily",
        "endpoint_broadness_pct",
        "endpoint_resolution_score",
        "focal_mediator_specificity_score",
        "compression_confidence",
        "compression_failure_reason",
        "flag_labels",
        "flag_count",
    ]
    flagged_df = flagged_df[flagged_keep_cols]

    if within_field_df is None:
        raise RuntimeError("within-field package was not loaded")
    field_support_df = _field_support_summary(within_field_df)
    other_patterns_df = _other_bucket_patterns(within_field_df)

    paper_df.to_csv(out_dir / "paperworthiness_summary.csv", index=False)
    field_support_df.to_csv(out_dir / "field_support_summary.csv", index=False)
    other_patterns_df.to_csv(out_dir / "other_bucket_patterns.csv", index=False)
    flagged_df.to_csv(out_dir / "flagged_rows.csv", index=False)
    _render_summary(paper_df, field_support_df, other_patterns_df, flagged_df, out_dir / "summary.md")


if __name__ == "__main__":
    main()
