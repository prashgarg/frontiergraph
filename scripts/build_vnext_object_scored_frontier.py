from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.context_normalization import (
    best_context_values,
    matched_context_sets,
    normalize_context_items,
    serialize_normalized_context_items,
)

DEFAULT_ENRICHED_SHORTLIST = "outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.csv"
DEFAULT_OUT_DIR = "outputs/paper/29_vnext_object_scored_frontier"
DEFAULT_FINDINGS = "next_steps/vnext_object_scored_frontier_findings.md"

DESIGN_GAP_POTENTIAL = {
    "descriptive_observational": 1.00,
    "prediction_or_forecasting": 0.95,
    "time_series_econometrics": 0.90,
    "qualitative_or_case_study": 0.80,
    "panel_FE_or_TWFE": 0.75,
    "event_study": 0.70,
    "DiD": 0.65,
    "IV": 0.55,
    "RDD": 0.55,
    "experiment": 0.45,
}

NEXT_EVIDENCE_STEP = {
    "descriptive_observational": "quasi-experimental or panel-based evidence",
    "prediction_or_forecasting": "causal or quasi-experimental evidence",
    "time_series_econometrics": "panel, IV, or quasi-experimental evidence",
    "qualitative_or_case_study": "broader quantitative evidence",
    "panel_FE_or_TWFE": "alternative identification or mechanism evidence",
    "event_study": "alternative identification or mechanism evidence",
    "DiD": "replication in other settings or mechanism evidence",
    "IV": "replication in new settings or mechanism evidence",
    "RDD": "replication in new settings or mechanism evidence",
    "experiment": "external-validity or context-transfer evidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Direct scorers for vNext frontier objects on the enriched shortlist.")
    parser.add_argument("--enriched-shortlist", default=DEFAULT_ENRICHED_SHORTLIST, dest="enriched_shortlist")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, dest="out_dir")
    parser.add_argument("--findings-note", default=DEFAULT_FINDINGS, dest="findings_note")
    return parser.parse_args()


def _parse_json_values(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    out: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                val = str(item.get("value", "")).strip()
                if val:
                    out.append(val)
            else:
                val = str(item).strip()
                if val:
                    out.append(val)
    elif isinstance(parsed, dict):
        val = str(parsed.get("value", "")).strip()
        if val:
            out.append(val)
    return out


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _merge_context_items(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for items in lists:
        for item in items:
            canonical_id = str(item.get("canonical_context_id", "")).strip()
            if not canonical_id:
                continue
            if item.get("granularity") == "unknown":
                continue
            existing = merged.get(canonical_id)
            if existing is None:
                merged[canonical_id] = dict(item)
                merged[canonical_id]["count"] = int(item.get("count", 0) or 0)
            else:
                existing["count"] = int(existing.get("count", 0) or 0) + int(item.get("count", 0) or 0)
    return sorted(
        merged.values(),
        key=lambda x: (-int(x.get("count", 0) or 0), str(x.get("normalized_display", ""))),
    )


def _context_ids(items: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("canonical_context_id", "")).strip()
        for item in items
        if str(item.get("canonical_context_id", "")).strip() and item.get("granularity") != "unknown"
    }


def _matched_unit_payload(endpoint_units: list[str], edge_units: list[str]) -> dict[str, Any]:
    endpoint = {str(item).strip() for item in endpoint_units if str(item).strip()}
    edge = {str(item).strip() for item in edge_units if str(item).strip()}
    matched = sorted(endpoint & edge)
    return {
        "matched_unit_count": len(matched),
        "matched_unit_display": matched[:3],
    }


def _geo_gap_payload(endpoint_items: list[dict[str, Any]], edge_items: list[dict[str, Any]]) -> dict[str, Any]:
    endpoint_set, edge_set, granularity = matched_context_sets(endpoint_items, edge_items)
    if granularity is None or not endpoint_set or not edge_set:
        return {
            "matched_geo_granularity": "",
            "matched_endpoint_geo_count": 0,
            "matched_edge_geo_count": 0,
            "geo_gap_score": 0.0,
            "matched_endpoint_geography_display": [],
            "matched_edge_geography_display": [],
        }
    uncovered = endpoint_set - edge_set
    matched_endpoint_items = [item for item in endpoint_items if item.get("granularity") == granularity]
    matched_edge_items = [item for item in edge_items if item.get("granularity") == granularity]
    return {
        "matched_geo_granularity": granularity,
        "matched_endpoint_geo_count": len(endpoint_set),
        "matched_edge_geo_count": len(edge_set),
        "geo_gap_score": float(len(uncovered)) / float(len(endpoint_set)) if endpoint_set else 0.0,
        "matched_endpoint_geography_display": best_context_values(matched_endpoint_items, allowed_granularities={granularity}, limit=3),
        "matched_edge_geography_display": best_context_values(matched_edge_items, allowed_granularities={granularity}, limit=2),
    }


def _list_phrase(items: list[str], default: str = "the current evidence base") -> str:
    items = [str(item).strip() for item in items if str(item).strip()]
    if not items:
        return default
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _percentile(series: pd.Series, ascending: bool = True) -> pd.Series:
    if len(series) == 0:
        return pd.Series(dtype=float)
    return series.rank(method="average", pct=True, ascending=ascending).astype(float)


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["source_geo_items_norm"] = out["source_top_geographies_json"].map(normalize_context_items)
    out["target_geo_items_norm"] = out["target_top_geographies_json"].map(normalize_context_items)
    out["edge_geo_items_norm"] = out["dominant_countries_json"].map(normalize_context_items)
    out["source_geos"] = out["source_geo_items_norm"].map(lambda items: best_context_values(items, limit=3))
    out["target_geos"] = out["target_geo_items_norm"].map(lambda items: best_context_values(items, limit=3))
    out["edge_geos"] = out["edge_geo_items_norm"].map(lambda items: best_context_values(items, limit=3))
    out["source_units"] = out["source_top_units_json"].map(_parse_json_values)
    out["target_units"] = out["target_top_units_json"].map(_parse_json_values)
    out["edge_units"] = out["dominant_units_json"].map(_parse_json_values)

    out["endpoint_geo_union"] = out.apply(
        lambda row: best_context_values(
            _merge_context_items(list(row["source_geo_items_norm"]), list(row["target_geo_items_norm"])),
            limit=3,
        ),
        axis=1,
    )
    out["endpoint_geo_items_norm"] = out.apply(
        lambda row: _merge_context_items(list(row["source_geo_items_norm"]), list(row["target_geo_items_norm"])),
        axis=1,
    )
    out["endpoint_unit_union"] = out.apply(
        lambda row: _dedupe_keep_order(list(row["source_units"]) + list(row["target_units"])), axis=1
    )
    out["endpoint_geo_count"] = out["endpoint_geo_items_norm"].map(lambda items: len(_context_ids(items))).astype(int)
    out["edge_geo_count"] = out["edge_geo_items_norm"].map(lambda items: len(_context_ids(items))).astype(int)
    out["endpoint_unit_count"] = out["endpoint_unit_union"].map(len).astype(int)
    out["edge_unit_count"] = out["edge_units"].map(len).astype(int)
    matched_unit_payload = out.apply(
        lambda row: _matched_unit_payload(list(row["endpoint_unit_union"]), list(row["edge_units"])),
        axis=1,
    )
    out["matched_unit_count"] = matched_unit_payload.map(lambda payload: payload["matched_unit_count"]).astype(int)
    out["matched_unit_display"] = matched_unit_payload.map(lambda payload: payload["matched_unit_display"])

    geo_payload = out.apply(
        lambda row: _geo_gap_payload(list(row["endpoint_geo_items_norm"]), list(row["edge_geo_items_norm"])),
        axis=1,
    )
    out["matched_geo_granularity"] = geo_payload.map(lambda payload: payload["matched_geo_granularity"])
    out["matched_endpoint_geo_count"] = geo_payload.map(lambda payload: payload["matched_endpoint_geo_count"]).astype(int)
    out["matched_edge_geo_count"] = geo_payload.map(lambda payload: payload["matched_edge_geo_count"]).astype(int)
    out["geo_gap_score"] = geo_payload.map(lambda payload: payload["geo_gap_score"]).astype(float)
    out["matched_endpoint_geography_display"] = geo_payload.map(lambda payload: payload["matched_endpoint_geography_display"])
    out["matched_edge_geography_display"] = geo_payload.map(lambda payload: payload["matched_edge_geography_display"])

    out["unit_gap_score"] = out.apply(
        lambda row: (
            max(float(row["endpoint_unit_count"] - row["edge_unit_count"]), 0.0) / float(row["endpoint_unit_count"])
            if row["endpoint_unit_count"] > 0 and row["edge_unit_count"] > 0
            else 0.0
        ),
        axis=1,
    )
    out["context_gap_score"] = out[["geo_gap_score", "unit_gap_score"]].max(axis=1)
    out["edge_context_specificity_raw"] = out.apply(
        lambda row: 1.0 / float(max((row["matched_edge_geo_count"] or row["edge_geo_count"]) + row["edge_unit_count"], 1)),
        axis=1,
    )
    out["endpoint_context_width_raw"] = out.apply(
        lambda row: float(row["endpoint_geo_count"] + row["endpoint_unit_count"]),
        axis=1,
    )
    out["support_strength_raw"] = (
        pd.to_numeric(out["distinct_paper_support"], errors="coerce").fillna(0).astype(float)
        + pd.to_numeric(out["weight"], errors="coerce").fillna(0).astype(float)
    )
    out["stability_raw"] = pd.to_numeric(out["stability"], errors="coerce").fillna(0).astype(float)

    out["support_strength_score"] = (
        0.45 * _percentile(out["support_strength_raw"], ascending=True)
        + 0.35 * _percentile(out["stability_raw"], ascending=True)
        + 0.20 * _percentile(pd.to_numeric(out["mediator_count"], errors="coerce").fillna(0).astype(float), ascending=True)
    )
    out["endpoint_context_width_score"] = _percentile(out["endpoint_context_width_raw"], ascending=True)
    out["edge_context_specificity_score"] = _percentile(out["edge_context_specificity_raw"], ascending=True)
    out["baseline_quality_score"] = 1.0 - _percentile(pd.to_numeric(out["shortlist_rank"], errors="coerce").fillna(9999).astype(float), ascending=True)
    out["design_gap_potential"] = out["edge_design_family"].map(DESIGN_GAP_POTENTIAL).fillna(0.0).astype(float)
    out["source_top_geographies_normalized_json"] = out["source_geo_items_norm"].map(serialize_normalized_context_items)
    out["target_top_geographies_normalized_json"] = out["target_geo_items_norm"].map(serialize_normalized_context_items)
    out["dominant_countries_normalized_json"] = out["edge_geo_items_norm"].map(serialize_normalized_context_items)
    out["endpoint_geographies_normalized_json"] = out["endpoint_geo_items_norm"].map(serialize_normalized_context_items)
    out["matched_endpoint_geography_display_json"] = out["matched_endpoint_geography_display"].map(
        lambda items: json.dumps(items, ensure_ascii=False)
    )
    out["matched_edge_geography_display_json"] = out["matched_edge_geography_display"].map(
        lambda items: json.dumps(items, ensure_ascii=False)
    )
    out["matched_unit_display_json"] = out["matched_unit_display"].map(lambda items: json.dumps(items, ensure_ascii=False))
    return out


def _collapse_best(df: pd.DataFrame, score_col: str, family_name: str) -> pd.DataFrame:
    if df.empty:
        return df
    ranked = df.sort_values([score_col, "baseline_quality_score", "shortlist_rank"], ascending=[False, False, True]).copy()
    best = ranked.drop_duplicates(["pair_key"], keep="first").copy()
    horizon_sets = ranked.groupby("pair_key")["horizon"].apply(lambda s: sorted({int(v) for v in s})).rename("horizons_present")
    best = best.merge(horizon_sets, on="pair_key", how="left")
    best["prototype_family"] = family_name
    return best.reset_index(drop=True)


def _build_context_transfer(df: pd.DataFrame) -> pd.DataFrame:
    eligible = df[
        (
            (df["edge_geo_count"] > 0)
            | (df["edge_unit_count"] > 0)
        )
        & (df["context_gap_score"] > 0)
    ].copy()
    if eligible.empty:
        return eligible
    eligible["direct_object_score"] = (
        0.45 * eligible["context_gap_score"]
        + 0.20 * eligible["edge_context_specificity_score"]
        + 0.20 * eligible["support_strength_score"]
        + 0.10 * eligible["endpoint_context_width_score"]
        + 0.05 * eligible["baseline_quality_score"]
    )
    best = _collapse_best(eligible, "direct_object_score", "context_transfer")
    best["prototype_title"] = best.apply(
        lambda row: f"Where should we test the {row['source_label']} -> {row['target_label']} relation next?",
        axis=1,
    )
    best["prototype_why"] = best.apply(
        lambda row: (
            f"Current pair evidence is concentrated in {_list_phrase(row['matched_edge_geography_display'][:2], default=_list_phrase(row['edge_geos'][:2], default=_list_phrase(row['edge_units'][:2], default='a narrow set of settings')))}, "
            f"while the endpoint concepts appear more broadly across {_list_phrase(row['matched_endpoint_geography_display'][:3], default=_list_phrase(row['endpoint_geo_union'][:3], default='multiple contexts'))}. "
            "That makes this a context-transfer question rather than just another generic missing link."
        ),
        axis=1,
    )
    best["prototype_first_step"] = (
        "Pick one setting where both endpoints already appear individually, but the pair-level evidence is still sparse."
    )
    best["prototype_score_components_json"] = best.apply(
        lambda row: json.dumps(
            {
                "context_gap_score": round(float(row["context_gap_score"]), 4),
                "edge_context_specificity_score": round(float(row["edge_context_specificity_score"]), 4),
                "support_strength_score": round(float(row["support_strength_score"]), 4),
                "endpoint_context_width_score": round(float(row["endpoint_context_width_score"]), 4),
                "baseline_quality_score": round(float(row["baseline_quality_score"]), 4),
            },
            ensure_ascii=False,
        ),
        axis=1,
    )
    return best.sort_values(["direct_object_score", "baseline_quality_score"], ascending=[False, False]).head(25).reset_index(drop=True)


def _build_evidence_type_expansion(df: pd.DataFrame) -> pd.DataFrame:
    eligible = df[
        df["edge_evidence_mode"].astype(str).eq("empirics")
        & df["edge_design_family"].astype(str).isin(DESIGN_GAP_POTENTIAL.keys())
    ].copy()
    if eligible.empty:
        return eligible
    eligible["direct_object_score"] = (
        0.45 * eligible["design_gap_potential"]
        + 0.30 * eligible["support_strength_score"]
        + 0.15 * eligible["endpoint_context_width_score"]
        + 0.10 * eligible["baseline_quality_score"]
    )
    best = _collapse_best(eligible, "direct_object_score", "evidence_type_expansion")
    best["prototype_title"] = best.apply(
        lambda row: f"What evidence should come next for the {row['source_label']} -> {row['target_label']} relation?",
        axis=1,
    )
    best["prototype_why"] = best.apply(
        lambda row: (
            f"Current evidence is dominated by {row['edge_design_family'].replace('_', ' ')}. "
            f"The next high-value step is likely {_list_phrase([NEXT_EVIDENCE_STEP.get(str(row['edge_design_family']), 'complementary follow-up evidence')])}, "
            "not simply another study with the same design profile."
        ),
        axis=1,
    )
    best["prototype_first_step"] = (
        "Design a follow-up study that complements the dominant existing evidence rather than repeating it."
    )
    best["prototype_score_components_json"] = best.apply(
        lambda row: json.dumps(
            {
                "design_gap_potential": round(float(row["design_gap_potential"]), 4),
                "support_strength_score": round(float(row["support_strength_score"]), 4),
                "endpoint_context_width_score": round(float(row["endpoint_context_width_score"]), 4),
                "baseline_quality_score": round(float(row["baseline_quality_score"]), 4),
            },
            ensure_ascii=False,
        ),
        axis=1,
    )
    return best.sort_values(["direct_object_score", "baseline_quality_score"], ascending=[False, False]).head(25).reset_index(drop=True)


def _keep_columns(df: pd.DataFrame) -> list[str]:
    cols = [
        "prototype_family",
        "direct_object_score",
        "prototype_title",
        "prototype_why",
        "prototype_first_step",
        "prototype_score_components_json",
        "pair_key",
        "horizon",
        "horizons_present",
        "shortlist_rank",
        "display_title",
        "display_why",
        "source_label",
        "target_label",
        "edge_evidence_mode",
        "edge_design_family",
        "source_family_label",
        "target_family_label",
        "dominant_countries_json",
        "dominant_countries_normalized_json",
        "dominant_units_json",
        "source_top_geographies_json",
        "source_top_geographies_normalized_json",
        "target_top_geographies_json",
        "target_top_geographies_normalized_json",
        "endpoint_geographies_normalized_json",
        "source_top_units_json",
        "target_top_units_json",
        "matched_geo_granularity",
        "matched_endpoint_geography_display_json",
        "matched_edge_geography_display_json",
        "matched_unit_count",
        "matched_unit_display_json",
        "identification_strength",
        "taxonomy_confidence",
        "unknown_reason",
        "context_gap_score",
        "endpoint_context_width_score",
        "support_strength_score",
        "baseline_quality_score",
    ]
    return [c for c in cols if c in df.columns]


def _write_review_markdown(context_df: pd.DataFrame, evidence_df: pd.DataFrame, summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Direct-Scored vNext Frontier Objects",
        "",
        "These objects are scored directly from the layered ontology overlay rather than only being derived from the current shortlist wording.",
        "",
        "## Counts",
        "",
        f"- context-transfer candidates: `{summary['context_transfer_count']}`",
        f"- evidence-type-expansion candidates: `{summary['evidence_type_expansion_count']}`",
        "",
    ]

    def add_section(title: str, df: pd.DataFrame) -> None:
        lines.extend(["", f"## {title}", ""])
        if df.empty:
            lines.append("- none")
            return
        for row in df.head(12).itertuples(index=False):
            lines.append(
                f"- score `{row.direct_object_score:.3f}` | {row.prototype_title}  \n"
                f"  Horizons: `{row.horizons_present}` | baseline rank `#{int(row.shortlist_rank)}`  \n"
                f"  Why: {row.prototype_why}  \n"
                f"  First step: {row.prototype_first_step}  \n"
                f"  Baseline: {row.display_title}"
            )

    add_section("Context Transfer", context_df)
    add_section("Evidence-Type Expansion", evidence_df)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_findings(summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Direct-Scored vNext Frontier Object Findings",
        "",
        "## What we did",
        "",
        "We built direct scorers for the two strongest ontology-vNext question families:",
        "",
        "- context-transfer",
        "- evidence-type expansion",
        "",
        "Unlike the first prototype pass, these objects are scored directly from family/context/evidence fields and collapsed across horizons to avoid duplicate `h=5`/`h=10` entries.",
        "",
        "## Coverage",
        "",
        f"- context-transfer shortlist after direct scoring: `{summary['context_transfer_count']}`",
        f"- evidence-type-expansion shortlist after direct scoring: `{summary['evidence_type_expansion_count']}`",
        "",
        "## First read",
        "",
        "This is a better object than the first prototype pass because it stops repeating the same pair twice and forces the ontology-vNext fields to do real work in the score.",
        "",
        "Current read:",
        "- context-transfer remains the strongest new object family",
        "- evidence-type expansion also looks strong and is easier to explain cleanly in methodological terms",
        "- these two object families now look mature enough for a paper-facing methodology discussion, even if they remain internal-only for now",
        "",
        "## Next step",
        "",
        "The next step should be a human review pass comparing these direct-scored vNext objects against the current path/mechanism shortlist, asking which ones are genuinely better research objects and which are just better metadata.",
        "If that review is favorable, the natural next move is a paper note and then a ranking experiment that mixes these richer object scores with the existing frontier retrieval system.",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    findings_path = Path(args.findings_note)
    findings_path.parent.mkdir(parents=True, exist_ok=True)

    enriched = pd.read_csv(args.enriched_shortlist)
    featured = _prepare_features(enriched)
    context_df = _build_context_transfer(featured)
    evidence_df = _build_evidence_type_expansion(featured)

    context_keep = context_df[_keep_columns(context_df)].copy() if not context_df.empty else context_df
    evidence_keep = evidence_df[_keep_columns(evidence_df)].copy() if not evidence_df.empty else evidence_df

    summary = {
        "enriched_shortlist_rows": int(len(enriched)),
        "context_transfer_count": int(len(context_keep)),
        "evidence_type_expansion_count": int(len(evidence_keep)),
    }

    context_keep.to_csv(out_dir / "context_transfer_scored.csv", index=False)
    evidence_keep.to_csv(out_dir / "evidence_type_expansion_scored.csv", index=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_review_markdown(context_keep, evidence_keep, summary, out_dir / "direct_scored_frontier_objects.md")
    _write_findings(summary, findings_path)
    print(f"Wrote direct-scored frontier objects to {out_dir}")
    print(f"Wrote findings note to {findings_path}")


if __name__ == "__main__":
    main()
