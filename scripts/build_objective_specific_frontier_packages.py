from __future__ import annotations

import argparse
import json
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


EXPORT_COLS = [
    "horizon",
    "surface_rank",
    "frontier_rank",
    "reranker_rank",
    "transparent_rank",
    "u",
    "v",
    "u_label",
    "v_label",
    "candidate_family",
    "candidate_subfamily",
    "candidate_scope_bucket",
    "focal_mediator_label",
    "local_topology_class",
    "theme_pair_key",
    "semantic_family_key",
    "source_theme",
    "target_theme",
    "source_family",
    "target_family",
    "endpoint_broadness_raw",
    "endpoint_broadness_pct",
    "endpoint_resolution_score",
    "focal_mediator_specificity_score",
    "paper_surface_penalty",
    "textbook_like_penalty",
    "generic_mediator_penalty",
    "surface_penalty",
    "sink_penalty",
    "diversification_penalty",
    "top_mediators_json",
    "top_paths_json",
    "compressed_triplet_json",
    "compression_confidence",
    "compression_failure_reason",
    "candidate_generation_gate_failed",
    "candidate_generation_gate_reason",
]


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


def _field_memberships(row: pd.Series) -> list[dict[str, Any]]:
    endpoint_text = _normalize_text(f"{row.get('u_label', '')} {row.get('v_label', '')}")
    mediator_text = _normalize_text(str(row.get("focal_mediator_label", "")))
    endpoint_matches: list[str] = []
    mediator_matches: list[str] = []
    for field_def in FIELD_SHELF_DEFS:
        slug = str(field_def["slug"])
        tokens = [_normalize_text(tok) for tok in field_def["match_tokens"]]
        endpoint_match = any(tok and tok in endpoint_text for tok in tokens)
        mediator_match = any(tok and tok in mediator_text for tok in tokens)
        if endpoint_match:
            endpoint_matches.append(slug)
        if mediator_match:
            mediator_matches.append(slug)

    if endpoint_matches:
        rows = []
        for slug in sorted(set(endpoint_matches)):
            rows.append(
                {
                    "field_slug": slug,
                    "field_assignment_source": "endpoint_and_mediator" if slug in mediator_matches else "endpoint_only",
                    "field_endpoint_match": True,
                    "field_mediator_match": slug in mediator_matches,
                }
            )
        return rows

    if mediator_matches:
        rows = []
        for slug in sorted(set(mediator_matches)):
            rows.append(
                {
                    "field_slug": slug,
                    "field_assignment_source": "mediator_only",
                    "field_endpoint_match": False,
                    "field_mediator_match": True,
                }
            )
        return rows

    return [
        {
            "field_slug": "other",
            "field_assignment_source": "other",
            "field_endpoint_match": False,
            "field_mediator_match": False,
        }
    ]


def _load_df(path: Path) -> pd.DataFrame:
    usecols = [c for c in EXPORT_COLS if c in pd.read_csv(path, nrows=0).columns.tolist()]
    return pd.read_csv(path, usecols=usecols, low_memory=False)


def _metric_block(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "n_rows": 0,
            "unique_targets": 0,
            "unique_sources": 0,
            "unique_theme_pairs": 0,
            "top_target_share": 0.0,
            "wtp_share": 0.0,
            "green_share": 0.0,
            "broad_endpoint_share": 0.0,
            "textbook_like_share": 0.0,
            "mean_transparent_rank": 0.0,
            "mean_endpoint_resolution": 0.0,
        }
    target_counts = df["v_label"].astype(str).value_counts()
    return {
        "n_rows": int(len(df)),
        "unique_targets": int(df["v_label"].astype(str).nunique()),
        "unique_sources": int(df["u_label"].astype(str).nunique()),
        "unique_theme_pairs": int(df["theme_pair_key"].astype(str).nunique()),
        "top_target_share": float(target_counts.iloc[0] / len(df)) if not target_counts.empty else 0.0,
        "wtp_share": float(df["semantic_family_key"].astype(str).str.contains("willingness to pay").mean()),
        "green_share": float(df["theme_pair_key"].astype(str).str.contains("environment_climate").mean()),
        "broad_endpoint_share": float((df["endpoint_broadness_pct"].astype(float) >= 0.85).mean()),
        "textbook_like_share": float((df["textbook_like_penalty"].astype(float) > 0).mean()),
        "mean_transparent_rank": float(df["transparent_rank"].astype(float).mean()),
        "mean_endpoint_resolution": float(df["endpoint_resolution_score"].astype(float).mean()),
    }


def _write_global_package(df: pd.DataFrame, out_dir: Path, title: str, top_k: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    top = (
        df.sort_values(["horizon", "surface_rank", "u", "v"], ascending=[True, True, True, True])
        .groupby("horizon", group_keys=False)
        .head(int(top_k))
        .reset_index(drop=True)
    )
    top.to_csv(out_dir / "package.csv", index=False)
    top.to_parquet(out_dir / "package.parquet", index=False)
    summary_rows = []
    lines = [f"# {title}", "", f"Top {top_k} per horizon.", ""]
    for horizon in sorted(top["horizon"].astype(int).unique()):
        sub = top[top["horizon"].astype(int) == int(horizon)].copy()
        summary_rows.append({"horizon": int(horizon), **_metric_block(sub)})
        lines.append(f"## Horizon {int(horizon)}")
        lines.append(f"- rows: {len(sub)}")
        lines.append(f"- unique targets: {int(sub['v_label'].astype(str).nunique())}")
        lines.append(f"- top target share: {float(sub['v_label'].astype(str).value_counts(normalize=True).iloc[0]) if not sub.empty else 0.0:.3f}")
        lines.append(f"- WTP share: {float(sub['semantic_family_key'].astype(str).str.contains('willingness to pay').mean()):.3f}")
        lines.append(f"- green share: {float(sub['theme_pair_key'].astype(str).str.contains('environment_climate').mean()):.3f}")
        lines.append("- Top 10:")
        for row in sub.nsmallest(10, "surface_rank").itertuples(index=False):
            lines.append(
                f"  - {row.u_label} -> {row.v_label} | surface_rank={int(row.surface_rank)}, transparent_rank={int(row.transparent_rank)}, "
                f"subfamily={row.candidate_subfamily}, scope={row.candidate_scope_bucket}"
            )
        lines.append("")
    pd.DataFrame(summary_rows).to_csv(out_dir / "summary.csv", index=False)
    (out_dir / "summary.md").write_text("\n".join(lines))


def _write_field_package(df: pd.DataFrame, out_dir: Path, top_k: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = df.copy()
    work["field_memberships"] = work.apply(_field_memberships, axis=1)
    exploded = work.explode("field_memberships").reset_index(drop=True)
    exploded = pd.concat(
        [exploded.drop(columns=["field_memberships"]), exploded["field_memberships"].apply(pd.Series)],
        axis=1,
    )
    field_rows = []
    summary_rows = []
    lines = ["# Within-Field Top 100 Package", "", "Top 100 per horizon within each field shelf.", ""]
    field_order = [field_def["slug"] for field_def in FIELD_SHELF_DEFS] + ["other"]
    for horizon in sorted(exploded["horizon"].astype(int).unique()):
        lines.append(f"## Horizon {int(horizon)}")
        hdf = exploded[exploded["horizon"].astype(int) == int(horizon)].copy()
        for field_slug in field_order:
            sub = (
                hdf[hdf["field_slug"].astype(str) == field_slug]
                .sort_values(["surface_rank", "u", "v"], ascending=[True, True, True])
                .head(int(top_k))
                .copy()
            )
            if sub.empty:
                continue
            field_rows.append(sub)
            summary_rows.append({"horizon": int(horizon), "field_slug": field_slug, **_metric_block(sub)})
            lines.append(f"### {field_slug}")
            lines.append(f"- rows: {len(sub)}")
            lines.append(f"- unique targets: {int(sub['v_label'].astype(str).nunique())}")
            lines.append(f"- top target share: {float(sub['v_label'].astype(str).value_counts(normalize=True).iloc[0]) if not sub.empty else 0.0:.3f}")
            lines.append(
                f"- endpoint-driven share: {float(sub['field_endpoint_match'].fillna(False).astype(bool).mean()):.3f}"
            )
            lines.append(
                f"- mediator-only share: {float(sub['field_assignment_source'].astype(str).eq('mediator_only').mean()):.3f}"
            )
            lines.append(f"- WTP share: {float(sub['semantic_family_key'].astype(str).str.contains('willingness to pay').mean()):.3f}")
            lines.append("- Top 5:")
            for row in sub.nsmallest(5, "surface_rank").itertuples(index=False):
                lines.append(
                    f"  - {row.u_label} -> {row.v_label} | surface_rank={int(row.surface_rank)}, transparent_rank={int(row.transparent_rank)}"
                )
            lines.append("")
    out = pd.concat(field_rows, ignore_index=True) if field_rows else pd.DataFrame()
    out.to_csv(out_dir / "package.csv", index=False)
    out.to_parquet(out_dir / "package.parquet", index=False)
    pd.DataFrame(summary_rows).to_csv(out_dir / "summary.csv", index=False)
    (out_dir / "summary.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build objective-specific frontier packages from current frontier artifacts.")
    parser.add_argument("--global-frontier", default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv")
    parser.add_argument("--field-frontier", default="outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv")
    parser.add_argument("--scan-frontier", default="outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    global_df = _load_df(Path(args.global_frontier))
    field_df = _load_df(Path(args.field_frontier))
    scan_df = _load_df(Path(args.scan_frontier))

    _write_global_package(global_df, out_dir / "global_exploratory_top100_pool5000", "Global Exploratory Frontier Package", top_k=100)
    _write_field_package(field_df, out_dir / "within_field_top100_pool2000", top_k=100)
    _write_global_package(scan_df, out_dir / "global_scan_top250_pool2000", "Global Scan Package", top_k=250)
    _write_global_package(scan_df, out_dir / "global_scan_top1000_pool2000", "Global Scan Package", top_k=1000)

    manifest = {
        "global_frontier": str(args.global_frontier),
        "field_frontier": str(args.field_frontier),
        "scan_frontier": str(args.scan_frontier),
        "packages": [
            {"slug": "global_exploratory_top100_pool5000", "pool_size": 5000, "objective": "global_exploratory_top100", "budget_k": 100},
            {"slug": "within_field_top100_pool2000", "pool_size": 2000, "objective": "within_field_top100", "budget_k": 100},
            {"slug": "global_scan_top250_pool2000", "pool_size": 2000, "objective": "global_scan_top250", "budget_k": 250},
            {"slug": "global_scan_top1000_pool2000", "pool_size": 2000, "objective": "global_scan_top1000", "budget_k": 1000},
        ],
        "field_assignment_mode": "endpoint_first_with_mediator_fallback",
        "field_shelf_defs": FIELD_SHELF_DEFS,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote: {out_dir}")


if __name__ == "__main__":
    main()
