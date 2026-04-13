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


def _load_surface_broadness_thresholds(manifest_path: Path) -> dict[int, float]:
    payload = json.loads(manifest_path.read_text())
    mapping: dict[int, float] = {}
    for part in payload.get("part_manifests", []):
        tuning_best = str(part.get("tuning_best_path", ""))
        m = re.search(r"_h(\d+)\.csv$", tuning_best)
        if not m:
            continue
        horizon = int(m.group(1))
        cfg = part.get("surface_layer_config", {}) or {}
        mapping[horizon] = float(cfg.get("broad_endpoint_start_pct", 0.85))
    return mapping


def _field_memberships(row: pd.Series) -> list[str]:
    text_parts = [
        str(row.get("u_label", "")),
        str(row.get("v_label", "")),
        str(row.get("focal_mediator_label", "")),
    ]
    combined = _normalize_text(" ".join(text_parts))
    matches: list[str] = []
    for field_def in FIELD_SHELF_DEFS:
        tokens = [_normalize_text(tok) for tok in field_def["match_tokens"]]
        if any(tok and tok in combined for tok in tokens):
            matches.append(str(field_def["slug"]))
    if not matches:
        matches.append("other")
    return sorted(set(matches))


def _explode_fields(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["field_slugs"] = work.apply(_field_memberships, axis=1)
    exploded = work.explode("field_slugs").rename(columns={"field_slugs": "field_slug"}).reset_index(drop=True)
    return exploded


def _metric_block(df: pd.DataFrame, broad_start_pct: float) -> dict[str, Any]:
    target_counts = df["v_label"].astype(str).value_counts()
    return {
        "n_selected": int(len(df)),
        "unique_theme_pair_keys": int(df["theme_pair_key"].astype(str).nunique()) if not df.empty else 0,
        "unique_semantic_family_keys": int(df["semantic_family_key"].astype(str).nunique()) if not df.empty else 0,
        "unique_sources": int(df["u_label"].astype(str).nunique()) if not df.empty else 0,
        "unique_targets": int(df["v_label"].astype(str).nunique()) if not df.empty else 0,
        "top_target_share": float(target_counts.iloc[0] / len(df)) if len(df) and not target_counts.empty else 0.0,
        "green_share": float(df["theme_pair_key"].astype(str).str.contains("environment_climate").mean()) if len(df) else 0.0,
        "wtp_share": float(df["semantic_family_key"].astype(str).str.contains("willingness to pay").mean()) if len(df) else 0.0,
        "broad_endpoint_share": float((df["endpoint_broadness_pct"].astype(float) >= float(broad_start_pct)).mean()) if len(df) else 0.0,
        "generic_endpoint_share": float((df["surface_penalty"].astype(float) > 0).mean()) if len(df) else 0.0,
        "generic_mediator_share": float((df["generic_mediator_penalty"].astype(float) > 0).mean()) if len(df) else 0.0,
        "textbook_like_share": float((df["textbook_like_penalty"].astype(float) > 0).mean()) if len(df) else 0.0,
        "mean_endpoint_broadness": float(df["endpoint_broadness_raw"].astype(float).mean()) if len(df) else 0.0,
        "mean_endpoint_resolution": float(df["endpoint_resolution_score"].astype(float).mean()) if len(df) else 0.0,
        "mean_paper_surface_penalty": float(df["paper_surface_penalty"].astype(float).mean()) if len(df) else 0.0,
        "mean_transparent_rank": float(df["transparent_rank"].astype(float).mean()) if len(df) else 0.0,
        "share_transparent_rank_gt_500": float((df["transparent_rank"].astype(int) > 500).mean()) if len(df) else 0.0,
        "share_transparent_rank_gt_1000": float((df["transparent_rank"].astype(int) > 1000).mean()) if len(df) else 0.0,
        "share_transparent_rank_gt_2000": float((df["transparent_rank"].astype(int) > 2000).mean()) if len(df) else 0.0,
    }


def _evaluate_frontier(name: str, frontier_csv: Path, manifest_path: Path, budgets: list[int], horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    usecols = [
        "horizon",
        "surface_rank",
        "transparent_rank",
        "u",
        "v",
        "u_label",
        "v_label",
        "focal_mediator_label",
        "theme_pair_key",
        "semantic_family_key",
        "endpoint_broadness_pct",
        "surface_penalty",
        "generic_mediator_penalty",
        "textbook_like_penalty",
        "endpoint_broadness_raw",
        "endpoint_resolution_score",
        "paper_surface_penalty",
    ]
    df = pd.read_csv(frontier_csv, usecols=usecols, low_memory=False)
    broad_thresholds = _load_surface_broadness_thresholds(manifest_path)
    exploded = _explode_fields(df)
    rows: list[dict[str, Any]] = []
    overlap_base: list[dict[str, Any]] = []
    field_slugs = [field_def["slug"] for field_def in FIELD_SHELF_DEFS] + ["other"]
    for horizon in horizons:
        sub = df[df["horizon"].astype(int) == int(horizon)].sort_values(["surface_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
        sub_exp = exploded[exploded["horizon"].astype(int) == int(horizon)].sort_values(["surface_rank", "u", "v"], ascending=[True, True, True]).reset_index(drop=True)
        broad_start_pct = broad_thresholds.get(int(horizon), 0.85)
        for budget in budgets:
            top_global = sub.nsmallest(int(budget), "surface_rank").copy()
            rows.append(
                {
                    "frontier_name": name,
                    "horizon": int(horizon),
                    "budget_k": int(budget),
                    "field_slug": "global",
                    "n_available": int(len(sub)),
                    "broad_endpoint_start_pct": float(broad_start_pct),
                    **_metric_block(top_global, broad_start_pct=broad_start_pct),
                }
            )
            overlap_base.append(
                {
                    "frontier_name": name,
                    "horizon": int(horizon),
                    "budget_k": int(budget),
                    "field_slug": "global",
                    "pair_keys": set(zip(top_global["u"].astype(str), top_global["v"].astype(str))),
                }
            )
            for field_slug in field_slugs:
                field_df = sub_exp[sub_exp["field_slug"].astype(str) == field_slug].copy()
                top_field = field_df.nsmallest(int(budget), "surface_rank").copy()
                rows.append(
                    {
                        "frontier_name": name,
                        "horizon": int(horizon),
                        "budget_k": int(budget),
                        "field_slug": field_slug,
                        "n_available": int(field_df[["u", "v"]].drop_duplicates().shape[0]),
                        "broad_endpoint_start_pct": float(broad_start_pct),
                        **_metric_block(top_field, broad_start_pct=broad_start_pct),
                    }
                )
                overlap_base.append(
                    {
                        "frontier_name": name,
                        "horizon": int(horizon),
                        "budget_k": int(budget),
                        "field_slug": field_slug,
                        "pair_keys": set(zip(top_field["u"].astype(str), top_field["v"].astype(str))),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(overlap_base)


def _build_overlap(compare_base: pd.DataFrame, left_name: str, right_name: str) -> pd.DataFrame:
    left = compare_base[compare_base["frontier_name"] == left_name].copy()
    right = compare_base[compare_base["frontier_name"] == right_name].copy()
    merged = left.merge(right, on=["horizon", "budget_k", "field_slug"], suffixes=(f"_{left_name}", f"_{right_name}"))
    rows: list[dict[str, Any]] = []
    for row in merged.itertuples(index=False):
        left_pairs = getattr(row, f"pair_keys_{left_name}")
        right_pairs = getattr(row, f"pair_keys_{right_name}")
        inter = len(left_pairs & right_pairs)
        union = len(left_pairs | right_pairs)
        rows.append(
            {
                "horizon": int(row.horizon),
                "budget_k": int(row.budget_k),
                "field_slug": str(row.field_slug),
                "overlap_count": int(inter),
                "jaccard": float(inter / union) if union else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _write_summary_md(path: Path, compare_df: pd.DataFrame, overlap_df: pd.DataFrame, left_name: str, right_name: str) -> None:
    lines: list[str] = [
        "# Field-Conditioned Budget Evaluation",
        "",
        "This compares current frontiers across both global and within-field budgets.",
        "",
        f"- left frontier: `{left_name}`",
        f"- right frontier: `{right_name}`",
        "- field overlay: aligned with the public field shelves plus `other`",
        "- budgets: `100, 250, 1000`",
        "",
    ]
    for budget in sorted(compare_df["budget_k"].unique()):
        lines.append(f"## Budget {budget}")
        sub = compare_df[(compare_df["budget_k"] == budget) & (compare_df["field_slug"] == "global")].sort_values("horizon")
        if not sub.empty:
            lines.append("### Global")
            for row in sub.itertuples(index=False):
                lines.append(
                    f"- h={int(row.horizon)}: top_target_share {getattr(row, f'top_target_share_{left_name}'):.3f} -> {getattr(row, f'top_target_share_{right_name}'):.3f}, "
                    f"wtp_share {getattr(row, f'wtp_share_{left_name}'):.3f} -> {getattr(row, f'wtp_share_{right_name}'):.3f}, "
                    f"green_share {getattr(row, f'green_share_{left_name}'):.3f} -> {getattr(row, f'green_share_{right_name}'):.3f}, "
                    f"unique_theme_pairs {int(getattr(row, f'unique_theme_pair_keys_{left_name}'))} -> {int(getattr(row, f'unique_theme_pair_keys_{right_name}'))}"
                )
        field_sub = compare_df[(compare_df["budget_k"] == budget) & (compare_df["field_slug"] != "global")].copy()
        if not field_sub.empty:
            lines.append("### Field highlights")
            field_sub["delta_top_target_share"] = field_sub[f"top_target_share_{right_name}"] - field_sub[f"top_target_share_{left_name}"]
            field_sub["delta_unique_theme_pairs"] = field_sub[f"unique_theme_pair_keys_{right_name}"] - field_sub[f"unique_theme_pair_keys_{left_name}"]
            focus = field_sub.sort_values(["horizon", "field_slug"]).head(12)
            for row in focus.itertuples(index=False):
                lines.append(
                    f"- h={int(row.horizon)} {row.field_slug}: top_target_share {getattr(row, f'top_target_share_{left_name}'):.3f} -> {getattr(row, f'top_target_share_{right_name}'):.3f}, "
                    f"wtp_share {getattr(row, f'wtp_share_{left_name}'):.3f} -> {getattr(row, f'wtp_share_{right_name}'):.3f}, "
                    f"unique_targets {int(getattr(row, f'unique_targets_{left_name}'))} -> {int(getattr(row, f'unique_targets_{right_name}'))}"
                )
        ov = overlap_df[overlap_df["budget_k"] == budget].copy()
        if not ov.empty:
            lines.append("### Overlap")
            for row in ov[ov["field_slug"] == "global"].sort_values("horizon").itertuples(index=False):
                lines.append(f"- h={int(row.horizon)} global overlap: {int(row.overlap_count)} items, Jaccard {float(row.jaccard):.3f}")
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate current frontiers across field-conditioned and multi-budget slices.")
    parser.add_argument("--frontier-a", default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv")
    parser.add_argument("--manifest-a", default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/manifest.json")
    parser.add_argument("--name-a", default="pool5000")
    parser.add_argument("--frontier-b", default="outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/current_reranked_frontier.csv")
    parser.add_argument("--manifest-b", default="outputs/paper/93_current_reranked_frontier_path_to_direct_pool2000/manifest.json")
    parser.add_argument("--name-b", default="pool2000")
    parser.add_argument("--budgets", default="100,250,1000")
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    budgets = [int(x.strip()) for x in str(args.budgets).split(",") if x.strip()]
    horizons = [int(x.strip()) for x in str(args.horizons).split(",") if x.strip()]

    left_metrics, left_overlap = _evaluate_frontier(
        name=str(args.name_a),
        frontier_csv=Path(args.frontier_a),
        manifest_path=Path(args.manifest_a),
        budgets=budgets,
        horizons=horizons,
    )
    right_metrics, right_overlap = _evaluate_frontier(
        name=str(args.name_b),
        frontier_csv=Path(args.frontier_b),
        manifest_path=Path(args.manifest_b),
        budgets=budgets,
        horizons=horizons,
    )
    metrics = pd.concat([left_metrics, right_metrics], ignore_index=True)
    metrics.to_csv(out_dir / "field_budget_metrics.csv", index=False)

    compare = left_metrics.merge(
        right_metrics,
        on=["horizon", "budget_k", "field_slug"],
        suffixes=(f"_{args.name_a}", f"_{args.name_b}"),
    )
    compare.to_csv(out_dir / "field_budget_compare.csv", index=False)

    overlap_base = pd.concat([left_overlap, right_overlap], ignore_index=True)
    overlap = _build_overlap(overlap_base, left_name=str(args.name_a), right_name=str(args.name_b))
    overlap.to_csv(out_dir / "field_budget_overlap.csv", index=False)

    manifest = {
        "frontier_a": str(args.frontier_a),
        "frontier_b": str(args.frontier_b),
        "manifest_a": str(args.manifest_a),
        "manifest_b": str(args.manifest_b),
        "name_a": str(args.name_a),
        "name_b": str(args.name_b),
        "budgets": budgets,
        "horizons": horizons,
        "field_shelf_defs": FIELD_SHELF_DEFS,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    _write_summary_md(out_dir / "field_budget_summary.md", compare, overlap, left_name=str(args.name_a), right_name=str(args.name_b))
    print(f"Wrote: {out_dir / 'field_budget_metrics.csv'}")
    print(f"Wrote: {out_dir / 'field_budget_compare.csv'}")
    print(f"Wrote: {out_dir / 'field_budget_overlap.csv'}")
    print(f"Wrote: {out_dir / 'field_budget_summary.md'}")


if __name__ == "__main__":
    main()
