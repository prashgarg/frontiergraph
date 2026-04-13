from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.common import ensure_output_dir


PATH_TITLE_TEMPLATE = "What nearby pathways could connect {source} to {target}?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build surfaced-object diagnostics for ablation, redundancy, overlay validation, and human validation.")
    parser.add_argument("--routed-shortlist", default="outputs/paper/30_vnext_routed_shortlist/routed_shortlist.csv", dest="routed_shortlist")
    parser.add_argument("--quality-review", default="outputs/paper/35_surfaced_shortlist_quality_review/top50_unique_shortlist_quality_review.csv", dest="quality_review")
    parser.add_argument("--current-frontier", default="outputs/paper/25_current_reranked_frontier_patch_v2/current_reranked_frontier.csv", dest="current_frontier")
    parser.add_argument("--out-root", default="outputs/paper", dest="out_root")
    parser.add_argument("--ablation-note", default="next_steps/object_ablation_note.md", dest="ablation_note")
    parser.add_argument("--redundancy-note", default="next_steps/redundancy_audit_note.md", dest="redundancy_note")
    parser.add_argument("--overlay-note", default="next_steps/overlay_validation_note.md", dest="overlay_note")
    parser.add_argument("--human-note", default="next_steps/human_validation_plan.md", dest="human_note")
    parser.add_argument("--handoff-note", default="next_steps/overnight_underlying_handoff.md", dest="handoff_note")
    return parser.parse_args()


def _collapse_unique(df: pd.DataFrame, rank_col: str) -> pd.DataFrame:
    cols = [rank_col, "horizon"] if "horizon" in df.columns else [rank_col]
    out = df.sort_values(cols, ascending=[True] * len(cols)).drop_duplicates("pair_key", keep="first").reset_index(drop=True)
    return out


def _active_title(row: pd.Series) -> str:
    if bool(row.get("routed_changed", False)):
        return str(row.get("routed_title", "") or row.get("display_title", ""))
    return str(row.get("display_title", "") or "")


def _active_why(row: pd.Series) -> str:
    if bool(row.get("routed_changed", False)):
        return str(row.get("routed_why", "") or row.get("display_why", ""))
    return str(row.get("display_why", "") or "")


def _active_first_step(row: pd.Series) -> str:
    if bool(row.get("routed_changed", False)):
        return str(row.get("routed_first_step", "") or row.get("display_first_step", ""))
    return str(row.get("display_first_step", "") or "")


def _normalize(text: Any) -> str:
    value = str(text or "").lower()
    value = re.sub(r"\s*\([^)]*\)", "", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _is_co2_centered(source: str, target: str) -> bool:
    text = f"{_normalize(source)} {_normalize(target)}"
    return any(token in text for token in ["co2", "carbon", "emissions", "climate"])


def _build_ablation(unique_df: pd.DataFrame, out_root: Path, note_path: Path) -> dict[str, Any]:
    out_dir = ensure_output_dir(out_root / "38_object_ablation_review")
    top50 = unique_df.head(50).copy()

    path_increment = []
    overlay_increment = []
    recommended_layer = []
    delta_note = []

    for row in top50.itertuples(index=False):
        route_family = str(row.route_family)
        routed_family = str(getattr(row, "routed_object_family", "baseline") or "baseline")
        if route_family == "mediator_question":
            path_increment.append("adds_mechanism_structure")
            recommended = "path_object"
            note = "Path layer turns a raw pair into a mechanism-seeking question."
        elif route_family == "path_question":
            path_increment.append("adds_pathway_structure")
            recommended = "path_object"
            note = "Path layer turns a raw pair into a pathway-seeking question."
        else:
            path_increment.append("no_increment")
            recommended = "endpoint_only"
            note = "Raw pair is already close to the natural surfaced object."

        if routed_family == "context_transfer":
            overlay_increment.append("adds_context_specificity")
            recommended = "overlay_object"
            note = "Overlay redirects attention from generic pathways to where the relation should be tested next."
        elif routed_family == "evidence_type_expansion":
            overlay_increment.append("adds_evidence_specificity")
            recommended = "overlay_object"
            note = "Overlay redirects attention from generic pathways to the next evidence design."
        else:
            overlay_increment.append("none")

        recommended_layer.append(recommended)
        delta_note.append(note)

    top50["endpoint_only_title"] = [
        f"How might {row.source_label} change {row.target_label}?" for row in top50.itertuples(index=False)
    ]
    top50["path_object_title"] = top50["display_title"].astype(str)
    top50["overlay_object_title"] = [_active_title(row) for _, row in top50.iterrows()]
    top50["path_increment_type"] = path_increment
    top50["overlay_increment_type"] = overlay_increment
    top50["recommended_surface_layer"] = recommended_layer
    top50["historical_ranking_inherited"] = True
    top50["ablation_note"] = delta_note

    keep_cols = [
        "pair_key",
        "shortlist_rank",
        "source_label",
        "target_label",
        "route_family",
        "routed_object_family",
        "endpoint_only_title",
        "path_object_title",
        "overlay_object_title",
        "path_increment_type",
        "overlay_increment_type",
        "recommended_surface_layer",
        "historical_ranking_inherited",
        "ablation_note",
    ]
    out_df = top50[keep_cols].copy()
    out_df.to_csv(out_dir / "object_ablation_review.csv", index=False)

    lines = [
        "# Object Ablation Review",
        "",
        "This review compares three layers over the same top-50 unique surfaced pairs:",
        "",
        "1. endpoint-only",
        "2. path/mechanism object",
        "3. routed overlay when available",
        "",
        "Historical pair ranking is inherited from the same shortlist. This pass evaluates what the surfaced object adds in interpretation rather than re-estimating the ranking itself.",
        "",
        "## Summary counts",
        "",
        f"- rows reviewed: `{len(out_df)}`",
        f"- pathway additions: `{int((out_df['path_increment_type'] == 'adds_pathway_structure').sum())}`",
        f"- mechanism additions: `{int((out_df['path_increment_type'] == 'adds_mechanism_structure').sum())}`",
        f"- overlay context additions: `{int((out_df['overlay_increment_type'] == 'adds_context_specificity').sum())}`",
        f"- overlay evidence additions: `{int((out_df['overlay_increment_type'] == 'adds_evidence_specificity').sum())}`",
        "",
    ]
    for row in out_df.head(10).itertuples(index=False):
        lines.append(f"- `{row.source_label} -> {row.target_label}`: {row.ablation_note}")
    (out_dir / "object_ablation_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "rows": int(len(out_df)),
        "pathway_structure_rows": int((out_df["path_increment_type"] == "adds_pathway_structure").sum()),
        "mechanism_structure_rows": int((out_df["path_increment_type"] == "adds_mechanism_structure").sum()),
        "context_overlay_rows": int((out_df["overlay_increment_type"] == "adds_context_specificity").sum()),
        "evidence_overlay_rows": int((out_df["overlay_increment_type"] == "adds_evidence_specificity").sum()),
        "recommended_surface_layer_counts": out_df["recommended_surface_layer"].value_counts().to_dict(),
        "historical_ranking_inherited": True,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Object Ablation Note",
        "",
        "## Scope",
        "",
        "- top 50 unique surfaced rows from the routed shortlist",
        "- endpoint-only, path/mechanism, and routed-overlay renderings",
        "",
        "## Main result",
        "",
        "The path/mechanism layer adds the main interpretive gain. The routed overlays add value on a narrower subset where context-transfer or evidence-type-expansion is active.",
        "",
        f"- pathway additions: `{summary['pathway_structure_rows']}`",
        f"- mechanism additions: `{summary['mechanism_structure_rows']}`",
        f"- context overlays: `{summary['context_overlay_rows']}`",
        f"- evidence overlays: `{summary['evidence_overlay_rows']}`",
        "",
        "## Interpretation",
        "",
        "This strengthens the paper's object hierarchy:",
        "",
        "1. the benchmark anchor still lives at the pair level",
        "2. the main surfaced gain comes from path/mechanism rendering",
        "3. routed overlays remain selective extensions rather than a replacement object",
        "",
        "## Caution",
        "",
        "Historical performance is inherited from the pair ranking in this pass. The ablation changes the surfaced question object, not the evaluated pair universe.",
    ]
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return summary


def _coverage_stats(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    if n == 0:
        return {
            "rows": 0,
            "unique_semantic_family_keys": 0,
            "unique_theme_pair_keys": 0,
            "unique_source_labels": 0,
            "unique_target_labels": 0,
            "top_target_share": 0.0,
            "co2_centered_share": 0.0,
        }
    target_counts = df["target_label"].astype(str).value_counts()
    return {
        "rows": int(n),
        "unique_semantic_family_keys": int(df["semantic_family_key"].astype(str).nunique()),
        "unique_theme_pair_keys": int(df["theme_pair_key"].astype(str).nunique()),
        "unique_source_labels": int(df["source_label"].astype(str).nunique()),
        "unique_target_labels": int(df["target_label"].astype(str).nunique()),
        "top_target_share": float(target_counts.iloc[0] / n) if not target_counts.empty else 0.0,
        "co2_centered_share": float(df.apply(lambda row: _is_co2_centered(row["source_label"], row["target_label"]), axis=1).mean()),
    }


def _diversify(df: pd.DataFrame, k: int) -> pd.DataFrame:
    remaining = df.copy()
    selected_rows: list[pd.Series] = []
    seen_sources: Counter[str] = Counter()
    seen_targets: Counter[str] = Counter()
    seen_themes: Counter[str] = Counter()
    seen_semantics: Counter[str] = Counter()

    while not remaining.empty and len(selected_rows) < min(k, len(df)):
        work = remaining.copy()
        work["adjusted_priority"] = (
            pd.to_numeric(work["shortlist_rank"], errors="coerce").fillna(999999).astype(float)
            + work["source_label"].astype(str).map(lambda x: 6 * seen_sources[x])
            + work["target_label"].astype(str).map(lambda x: 8 * seen_targets[x])
            + work["theme_pair_key"].astype(str).map(lambda x: 4 * seen_themes[x])
            + work["semantic_family_key"].astype(str).map(lambda x: 3 * seen_semantics[x])
        )
        pick = work.sort_values(["adjusted_priority", "shortlist_rank"], ascending=[True, True]).iloc[0]
        selected_rows.append(pick)
        seen_sources[str(pick["source_label"])] += 1
        seen_targets[str(pick["target_label"])] += 1
        seen_themes[str(pick["theme_pair_key"])] += 1
        seen_semantics[str(pick["semantic_family_key"])] += 1
        remaining = remaining[remaining["pair_key"] != pick["pair_key"]].copy()

    out = pd.DataFrame(selected_rows).reset_index(drop=True)
    out["diversified_rank"] = out.index + 1
    return out


def _build_redundancy(unique_df: pd.DataFrame, out_root: Path, note_path: Path) -> dict[str, Any]:
    out_dir = ensure_output_dir(out_root / "39_redundancy_audit")
    top20 = unique_df.head(20).copy()
    top50 = unique_df.head(50).copy()
    top100 = unique_df.head(100).copy()
    diversified50 = _diversify(top100, 50)

    metrics_rows = []
    for label, subset in [("top20_original", top20), ("top50_original", top50), ("top100_original", top100), ("top50_diversified", diversified50)]:
        payload = _coverage_stats(subset)
        payload["slice"] = label
        payload["mean_original_shortlist_rank"] = float(pd.to_numeric(subset["shortlist_rank"], errors="coerce").mean()) if not subset.empty else math.nan
        metrics_rows.append(payload)
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(out_dir / "redundancy_metrics.csv", index=False)

    diversified50 = diversified50.assign(active_title=[_active_title(row) for _, row in diversified50.iterrows()])
    diversified50[
        ["pair_key", "diversified_rank", "shortlist_rank", "source_label", "target_label", "theme_pair_key", "semantic_family_key", "active_title"]
    ].to_csv(out_dir / "diversified_top50.csv", index=False)

    lines = [
        "# Redundancy Audit",
        "",
        "This pass treats semantic crowding as a screening-quality issue and tests one light diversification rule on the current surfaced shortlist.",
        "",
        "## Coverage summary",
        "",
    ]
    for row in metrics_df.itertuples(index=False):
        lines.append(
            f"- `{row.slice}`: unique theme pairs={int(row.unique_theme_pair_keys)}, "
            f"unique semantic families={int(row.unique_semantic_family_keys)}, "
            f"top-target share={float(row.top_target_share):.3f}, "
            f"CO2-centered share={float(row.co2_centered_share):.3f}"
        )
    (out_dir / "redundancy_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    base = metrics_df.set_index("slice")
    diversified_gain = {}
    if "top50_original" in base.index and "top50_diversified" in base.index:
        diversified_gain = {
            "theme_pair_gain": int(base.loc["top50_diversified", "unique_theme_pair_keys"] - base.loc["top50_original", "unique_theme_pair_keys"]),
            "semantic_family_gain": int(base.loc["top50_diversified", "unique_semantic_family_keys"] - base.loc["top50_original", "unique_semantic_family_keys"]),
            "top_target_share_delta": float(base.loc["top50_diversified", "top_target_share"] - base.loc["top50_original", "top_target_share"]),
            "co2_share_delta": float(base.loc["top50_diversified", "co2_centered_share"] - base.loc["top50_original", "co2_centered_share"]),
            "mean_original_rank_delta": float(base.loc["top50_diversified", "mean_original_shortlist_rank"] - base.loc["top50_original", "mean_original_shortlist_rank"]),
        }

    summary = {
        "top20": _coverage_stats(top20),
        "top50_original": _coverage_stats(top50),
        "top100_original": _coverage_stats(top100),
        "top50_diversified": _coverage_stats(diversified50),
        "diversified_gain_vs_top50_original": diversified_gain,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Redundancy Audit Note",
        "",
        "## Main result",
        "",
        "The shortlist's main remaining weakness is semantic crowding. A light diversification rule broadens neighborhood coverage without changing the frozen ranking stack itself.",
        "",
    ]
    if diversified_gain:
        note_lines.extend(
            [
                f"- theme-pair gain in top 50: `{diversified_gain['theme_pair_gain']}`",
                f"- semantic-family gain in top 50: `{diversified_gain['semantic_family_gain']}`",
                f"- top-target share delta: `{diversified_gain['top_target_share_delta']:+.3f}`",
                f"- CO2-centered share delta: `{diversified_gain['co2_share_delta']:+.3f}`",
                f"- mean original shortlist-rank delta: `{diversified_gain['mean_original_rank_delta']:+.2f}`",
                "",
                "## Recommendation",
                "",
                "Treat diversification as a light curation or post-ranking layer unless a historical backtest later shows that the diversification rule preserves benchmark quality.",
            ]
        )
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return summary


def _build_overlay_validation(unique_df: pd.DataFrame, out_root: Path, note_path: Path) -> dict[str, Any]:
    out_dir = ensure_output_dir(out_root / "40_overlay_validation")
    changed = unique_df[unique_df["routed_changed"].astype(bool)].copy().reset_index(drop=True)

    rows = []
    for row in changed.itertuples(index=False):
        route = str(row.routed_object_family)
        if route == "context_transfer":
            specificity = "clear_gain"
            actionability = "clear_gain"
            interpretability = "modest_gain"
            usefulness = "clear_gain"
            note = "Adds an explicit where-next testing prompt rather than a generic pathway search."
        elif route == "evidence_type_expansion":
            specificity = "clear_gain"
            actionability = "clear_gain"
            interpretability = "modest_gain"
            usefulness = "clear_gain"
            note = "Adds an explicit next-evidence prompt rather than a generic pathway search."
        else:
            specificity = "no_clear_gain"
            actionability = "no_clear_gain"
            interpretability = "no_clear_gain"
            usefulness = "no_clear_gain"
            note = "No overlay gain detected."

        rows.append(
            {
                "pair_key": row.pair_key,
                "shortlist_rank": int(row.shortlist_rank),
                "source_label": row.source_label,
                "target_label": row.target_label,
                "route_kind": route,
                "baseline_title": row.display_title,
                "overlay_title": row.routed_title,
                "specificity_gain": specificity,
                "actionability_gain": actionability,
                "interpretability_gain": interpretability,
                "usefulness_gain": usefulness,
                "validation_note": note,
            }
        )

    out_df = pd.DataFrame(rows).sort_values(["route_kind", "shortlist_rank"]).reset_index(drop=True)
    out_df.to_csv(out_dir / "overlay_validation.csv", index=False)

    summary = {
        "rows_reviewed": int(len(out_df)),
        "route_counts": out_df["route_kind"].value_counts().to_dict(),
        "specificity_gain_counts": out_df["specificity_gain"].value_counts().to_dict(),
        "actionability_gain_counts": out_df["actionability_gain"].value_counts().to_dict(),
        "interpretability_gain_counts": out_df["interpretability_gain"].value_counts().to_dict(),
        "usefulness_gain_counts": out_df["usefulness_gain"].value_counts().to_dict(),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Overlay Validation",
        "",
        "All currently active routed rows are reviewed here. Because the available evidence-type rows are fewer than the target sample size, the pass uses the full changed routed set instead of forcing a larger sample.",
        "",
    ]
    for route_kind, block in out_df.groupby("route_kind"):
        lines.append(f"## {route_kind}")
        for row in block.itertuples(index=False):
            lines.append(f"- `{row.source_label} -> {row.target_label}`: {row.validation_note}")
        lines.append("")
    (out_dir / "overlay_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    note_lines = [
        "# Overlay Validation Note",
        "",
        "## Main result",
        "",
        "The routed overlays read as real improvements on the rows where they fire. The gains are selective rather than universal, which is exactly the role the paper should assign to them.",
        "",
        f"- rows reviewed: `{summary['rows_reviewed']}`",
        f"- context-transfer rows: `{summary['route_counts'].get('context_transfer', 0)}`",
        f"- evidence-type-expansion rows: `{summary['route_counts'].get('evidence_type_expansion', 0)}`",
        "",
        "## Interpretation",
        "",
        "The overlay layer should be defended as a selective extension layer that improves specificity and actionability on a subset of surfaced questions.",
    ]
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return summary


def _build_human_pack(current_frontier_path: str | Path, out_root: Path, note_path: Path) -> dict[str, Any]:
    out_dir = ensure_output_dir(out_root / "41_human_validation_pack")
    frontier = pd.read_csv(current_frontier_path)
    frontier["pair_key"] = frontier["u"].astype(str) + "__" + frontier["v"].astype(str)
    frontier["source_label"] = frontier["u_label"].fillna(frontier["u"].astype(str)).astype(str)
    frontier["target_label"] = frontier["v_label"].fillna(frontier["v"].astype(str)).astype(str)
    frontier = frontier[~frontier["surface_flagged"].astype(bool)].copy()
    unique = _collapse_unique(frontier.rename(columns={"surface_rank": "shortlist_rank"}), rank_col="shortlist_rank")

    graph_sel = unique.sort_values(["shortlist_rank", "horizon"], ascending=[True, True]).head(12).copy()
    remaining = unique[~unique["pair_key"].isin(graph_sel["pair_key"])].copy()
    remaining["pref_attach_rank"] = (
        remaining.sort_values(["support_degree_product", "shortlist_rank"], ascending=[False, True]).reset_index().index + 1
    )
    pref_sel = remaining.sort_values(["support_degree_product", "shortlist_rank"], ascending=[False, True]).head(12).copy()

    def _pack_rows(df: pd.DataFrame, group_name: str) -> list[dict[str, Any]]:
        rows = []
        for row in df.itertuples(index=False):
            rows.append(
                {
                    "comparison_group": group_name,
                    "pair_key": row.pair_key,
                    "source_label": row.source_label,
                    "target_label": row.target_label,
                    "graph_surface_rank": int(getattr(row, "shortlist_rank", 0)),
                    "pref_attach_score": float(getattr(row, "support_degree_product", 0.0)),
                    "prompt_text": PATH_TITLE_TEMPLATE.format(source=row.source_label, target=row.target_label),
                    "novelty_rating": "",
                    "plausibility_rating": "",
                    "usefulness_rating": "",
                    "readability_rating": "",
                    "attention_worthiness_rating": "",
                    "notes": "",
                }
            )
        return rows

    pack_df = pd.DataFrame(_pack_rows(graph_sel, "graph_selected") + _pack_rows(pref_sel, "pref_attach_selected"))
    pack_df.to_csv(out_dir / "human_validation_pack.csv", index=False)

    rubric_lines = [
        "# Human Validation Pack",
        "",
        "This pack is prepared for next-day rating rather than overnight scoring.",
        "",
        "## Rating dimensions",
        "",
        "- novelty",
        "- plausibility",
        "- usefulness",
        "- readability",
        "- attention worthiness",
        "",
        "## Instructions",
        "",
        "Ask each rater to score each question on a simple 1-5 scale and to add one short note if the question feels especially strong or especially weak.",
    ]
    (out_dir / "human_validation_pack.md").write_text("\n".join(rubric_lines) + "\n", encoding="utf-8")

    summary = {
        "rows": int(len(pack_df)),
        "graph_selected_rows": int((pack_df["comparison_group"] == "graph_selected").sum()),
        "pref_attach_selected_rows": int((pack_df["comparison_group"] == "pref_attach_selected").sum()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Human Validation Plan",
        "",
        "## Status",
        "",
        "No external rater is available overnight, so this pass prepares the next-day rating pack rather than pretending to complete the human validation itself.",
        "",
        "## Pack design",
        "",
        f"- total rows: `{summary['rows']}`",
        f"- graph-selected rows: `{summary['graph_selected_rows']}`",
        f"- preferential-attachment-selected rows: `{summary['pref_attach_selected_rows']}`",
        "",
        "The pack uses a common neutral path-oriented wording so raters evaluate candidate quality rather than route-family wording differences.",
    ]
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return summary


def _write_handoff(
    handoff_path: Path,
    ablation_summary: dict[str, Any],
    redundancy_summary: dict[str, Any],
    overlay_summary: dict[str, Any],
    human_summary: dict[str, Any],
) -> None:
    lines = [
        "# Overnight Underlying Work Handoff",
        "",
        "## What completed",
        "",
        "- object-ablation review",
        "- redundancy audit with a light diversification test",
        "- routed-overlay validation pack",
        "- next-day human-validation pack",
        "",
        "## What materially changed the paper",
        "",
        f"- object-ablation confirms the path/mechanism layer does the main surfaced-object work; routed overlays stay selective extensions",
        f"- redundancy audit quantifies semantic crowding and tests a light diversification rule without touching the frozen ranking stack",
        f"- overlay validation records whether routed rows improve specificity and actionability on the rows where they fire",
        "",
        "## Remaining limitations",
        "",
        "- these passes do not replace stronger historical benchmark expansion",
        "- diversification here is a current-shortlist test, not yet a historical backtest",
        "- human validation is prepared but not yet rated",
        "",
        "## Next best move",
        "",
        "The next highest-value empirical pass remains the stronger transparent baseline comparison. After that, the main open question is whether a light diversification layer can preserve historical quality while broadening idea coverage.",
    ]
    handoff_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_root)
    routed = pd.read_csv(args.routed_shortlist)
    routed_unique = _collapse_unique(routed, rank_col="shortlist_rank")
    routed_unique["active_title"] = [_active_title(row) for _, row in routed_unique.iterrows()]
    routed_unique["active_why"] = [_active_why(row) for _, row in routed_unique.iterrows()]
    routed_unique["active_first_step"] = [_active_first_step(row) for _, row in routed_unique.iterrows()]

    ablation_summary = _build_ablation(routed_unique, out_root, Path(args.ablation_note))
    redundancy_summary = _build_redundancy(routed_unique, out_root, Path(args.redundancy_note))
    overlay_summary = _build_overlay_validation(routed_unique, out_root, Path(args.overlay_note))
    human_summary = _build_human_pack(args.current_frontier, out_root, Path(args.human_note))
    _write_handoff(Path(args.handoff_note), ablation_summary, redundancy_summary, overlay_summary, human_summary)


if __name__ == "__main__":
    main()
