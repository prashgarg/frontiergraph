from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SHORTLIST = "outputs/paper/23_current_path_mediator_shortlist_patch_v1_labels_generic/current_path_mediator_shortlist.csv"
DEFAULT_CONTEXT = "outputs/paper/29_vnext_object_scored_frontier/context_transfer_scored.csv"
DEFAULT_EVIDENCE = "outputs/paper/29_vnext_object_scored_frontier/evidence_type_expansion_scored.csv"
DEFAULT_OUT = "outputs/paper/30_vnext_routed_shortlist"
DEFAULT_FINDINGS = "next_steps/vnext_routed_shortlist_findings.md"

GENERIC_ENDPOINT_LABELS = {
    "policy",
    "distance",
    "economic growth",
    "innovation",
    "employment",
    "wages",
    "health",
    "income",
    "consumption",
    "productivity",
    "investment",
    "output",
    "rate of growth",
}
GENERIC_ENDPOINT_PATTERNS = [
    r"\bpolicy variables\b",
    r"\bmodel parameters\b",
    r"\bparameters\b",
    r"\bmodels\b",
]
GENERIC_REGEX = [re.compile(p, flags=re.IGNORECASE) for p in GENERIC_ENDPOINT_PATTERNS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route the active shortlist into richer vNext object types when ontology-vNext signals are strong.")
    parser.add_argument("--shortlist", default=DEFAULT_SHORTLIST, dest="shortlist")
    parser.add_argument("--context-scored", default=DEFAULT_CONTEXT, dest="context_scored")
    parser.add_argument("--evidence-scored", default=DEFAULT_EVIDENCE, dest="evidence_scored")
    parser.add_argument("--out", default=DEFAULT_OUT, dest="out_dir")
    parser.add_argument("--findings-note", default=DEFAULT_FINDINGS, dest="findings_note")
    return parser.parse_args()


def _threshold_and_percentile(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["family_percentile"] = out["direct_object_score"].rank(method="average", pct=True, ascending=True).astype(float)
    out["threshold_q75"] = float(out["direct_object_score"].quantile(0.75)) if not out.empty else 0.0
    out["support_strength_median"] = float(pd.to_numeric(out["support_strength_score"], errors="coerce").dropna().median()) if not out.empty else 0.0
    return out


def _route_lookup(df: pd.DataFrame, route_name: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if df.empty:
        return out
    threshold = float(df["threshold_q75"].iloc[0])
    support_median = float(df["support_strength_median"].iloc[0]) if "support_strength_median" in df.columns else 0.0
    for row in df.itertuples(index=False):
        if float(row.direct_object_score) < threshold:
            continue
        out[str(row.pair_key)] = {
            "route_name": route_name,
            "score": float(row.direct_object_score),
            "family_percentile": float(row.family_percentile),
            "title": str(row.prototype_title),
            "why": str(row.prototype_why),
            "first_step": str(row.prototype_first_step),
            "threshold": threshold,
            "support_median": support_median,
            "design_family": getattr(row, "edge_design_family", ""),
            "taxonomy_confidence": _safe_float(getattr(row, "taxonomy_confidence", 0.0), 0.0),
            "identification_strength": getattr(row, "identification_strength", ""),
            "unknown_reason": getattr(row, "unknown_reason", ""),
            "support_strength_score": _safe_float(getattr(row, "support_strength_score", 0.0), 0.0),
            "context_gap_score": _safe_float(getattr(row, "context_gap_score", 0.0), 0.0),
            "matched_geo_granularity": str(getattr(row, "matched_geo_granularity", "") or ""),
            "matched_unit_count": int(getattr(row, "matched_unit_count", 0) or 0),
        }
    return out


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def _is_generic_endpoint(label: Any) -> bool:
    norm = _normalize_label(label)
    if not norm:
        return True
    if norm in GENERIC_ENDPOINT_LABELS:
        return True
    return any(pattern.search(norm) for pattern in GENERIC_REGEX)


def _pick_route(pair_key: str, context_map: dict[str, dict[str, Any]], evidence_map: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    context = context_map.get(pair_key)
    evidence = evidence_map.get(pair_key)
    if context is None and evidence is None:
        return None
    if context is None:
        return evidence
    if evidence is None:
        return context
    if context["family_percentile"] > evidence["family_percentile"]:
        return context
    if evidence["family_percentile"] > context["family_percentile"]:
        return evidence
    return context


def _validate_context_route(route: dict[str, Any] | None, row: Any) -> tuple[bool, str]:
    if route is None:
        return False, ""
    if _is_generic_endpoint(row.source_label) or _is_generic_endpoint(row.target_label):
        return False, "generic_endpoint_blocked_context_transfer"
    has_matched_geo = bool(str(route.get("matched_geo_granularity", "")).strip())
    has_matched_unit = int(route.get("matched_unit_count", 0) or 0) > 0
    strong_context = _safe_float(route.get("context_gap_score", 0.0), 0.0) >= 0.80 and _safe_float(route.get("support_strength_score", 0.0), 0.0) >= 0.75
    if has_matched_geo or has_matched_unit or strong_context:
        return True, ""
    return False, "unmatched_context_blocked_context_transfer"


def _validate_evidence_route(route: dict[str, Any] | None, row: Any) -> tuple[bool, str]:
    if route is None:
        return False, ""
    design_family = str(route.get("design_family", "") or "").strip()
    if not design_family or design_family in {"unknown", "do_not_know", "other"}:
        return False, "unresolved_design_blocked_evidence"
    if _safe_float(route.get("taxonomy_confidence", 0.0), 0.0) < 0.75:
        return False, "low_taxonomy_confidence_blocked_evidence"
    if _safe_float(route.get("support_strength_score", 0.0), 0.0) < _safe_float(route.get("support_median", 0.0), 0.0):
        return False, "low_support_blocked_evidence"
    if _is_generic_endpoint(row.source_label) and _is_generic_endpoint(row.target_label):
        return False, "generic_endpoints_blocked_evidence"
    return True, ""


def _pick_best_valid_route(context: dict[str, Any] | None, evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    if context is None:
        return evidence
    if evidence is None:
        return context
    if context["family_percentile"] > evidence["family_percentile"]:
        return context
    if evidence["family_percentile"] > context["family_percentile"]:
        return evidence
    return context


def _apply_routes(base_df: pd.DataFrame, context_map: dict[str, dict[str, Any]], evidence_map: dict[str, dict[str, Any]]) -> pd.DataFrame:
    routed = base_df.copy()
    route_names = []
    route_scores = []
    route_percentiles = []
    route_thresholds = []
    routed_titles = []
    routed_whys = []
    routed_first_steps = []
    suppressed_reasons = []
    raw_route_names = []

    for row in routed.itertuples(index=False):
        pair_key = str(row.pair_key)
        raw_context = context_map.get(pair_key)
        raw_evidence = evidence_map.get(pair_key)
        raw_best = _pick_route(pair_key, context_map, evidence_map)
        raw_route_names.append(raw_best["route_name"] if raw_best is not None else "baseline")
        suppression_reason = ""

        context_valid, context_reason = _validate_context_route(raw_context, row)
        evidence_valid, evidence_reason = _validate_evidence_route(raw_evidence, row)
        valid_context = raw_context if context_valid else None
        valid_evidence = raw_evidence if evidence_valid else None
        route = _pick_best_valid_route(valid_context, valid_evidence)

        if raw_best is not None and route is None:
            suppression_reason = context_reason or evidence_reason or "route_blocked"
        elif raw_best is not None and route is not None and raw_best["route_name"] != route["route_name"]:
            if raw_best["route_name"] == "context_transfer":
                suppression_reason = f"{context_reason}_fell_back_to_{route['route_name']}"
            elif raw_best["route_name"] == "evidence_type_expansion":
                suppression_reason = f"{evidence_reason}_fell_back_to_{route['route_name']}"
        if route is None:
            route_names.append("baseline")
            route_scores.append("")
            route_percentiles.append("")
            route_thresholds.append("")
            routed_titles.append(str(row.display_title))
            routed_whys.append(str(row.display_why))
            routed_first_steps.append(str(row.display_first_step))
        else:
            route_names.append(str(route["route_name"]))
            route_scores.append(float(route["score"]))
            route_percentiles.append(float(route["family_percentile"]))
            route_thresholds.append(float(route["threshold"]))
            routed_titles.append(str(route["title"]))
            routed_whys.append(str(route["why"]))
            routed_first_steps.append(str(route["first_step"]))
        suppressed_reasons.append(suppression_reason)

    routed["routed_object_family"] = route_names
    routed["raw_route_family"] = raw_route_names
    routed["routed_object_score"] = route_scores
    routed["routed_object_family_percentile"] = route_percentiles
    routed["routed_object_threshold"] = route_thresholds
    routed["routed_title"] = routed_titles
    routed["routed_why"] = routed_whys
    routed["routed_first_step"] = routed_first_steps
    routed["route_suppression_reason"] = suppressed_reasons
    routed["routed_changed"] = routed["routed_object_family"].ne("baseline")
    return routed


def _summary(routed: pd.DataFrame, context_df: pd.DataFrame, evidence_df: pd.DataFrame) -> dict[str, Any]:
    counts_by_h = (
        routed.groupby(["horizon", "routed_object_family"])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    return {
        "rows": int(len(routed)),
        "context_threshold_q75": float(context_df["threshold_q75"].iloc[0]) if not context_df.empty else None,
        "evidence_threshold_q75": float(evidence_df["threshold_q75"].iloc[0]) if not evidence_df.empty else None,
        "changed_rows": int(routed["routed_changed"].sum()),
        "changed_pairs_unique": int(routed.loc[routed["routed_changed"], "pair_key"].nunique()),
        "route_counts_total": routed["routed_object_family"].value_counts().to_dict(),
        "route_counts_by_horizon": counts_by_h,
        "suppression_counts": routed["route_suppression_reason"].replace("", pd.NA).dropna().value_counts().to_dict(),
    }


def _write_markdown(routed: pd.DataFrame, summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# vNext Routed Shortlist",
        "",
        "This is the active shortlist with a conservative routing layer on top.",
        "",
        "Routing rules:",
        f"- emit `context_transfer` when direct context-transfer score is in the top quartile of that family (`>= {summary['context_threshold_q75']:.3f}`)",
        f"- emit `evidence_type_expansion` when direct evidence-expansion score is in the top quartile of that family (`>= {summary['evidence_threshold_q75']:.3f}`)",
        "- resolve overlaps by whichever object scores more strongly within its own family percentile",
        "",
        "## Counts",
        "",
        f"- changed rows: `{summary['changed_rows']}`",
        f"- changed unique pairs: `{summary['changed_pairs_unique']}`",
    ]
    for route, count in summary["route_counts_total"].items():
        lines.append(f"- `{route}` total rows: `{count}`")
    for reason, count in summary.get("suppression_counts", {}).items():
        lines.append(f"- suppression `{reason}` rows: `{count}`")

    def add_section(title: str, sub: pd.DataFrame) -> None:
        lines.extend(["", f"## {title}", ""])
        if sub.empty:
            lines.append("- none")
            return
        for row in sub.head(12).itertuples(index=False):
            score_text = ""
            if str(row.routed_object_family) != "baseline":
                score_text = f" score `{float(row.routed_object_score):.3f}`"
            lines.append(
                f"- `h={int(row.horizon)}` `#{int(row.shortlist_rank)}` {row.routed_title}  \n"
                f"  Route: `{row.routed_object_family}`{score_text}  \n"
                f"  Why: {row.routed_why}  \n"
                f"  Baseline: {row.display_title}"
            )

    add_section(
        "Changed Top Rows",
        routed[routed["routed_changed"]].sort_values(["horizon", "shortlist_rank"]),
    )
    add_section(
        "Top h=5 Preview",
        routed[routed["horizon"] == 5].sort_values("shortlist_rank"),
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_findings(summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# vNext Routed Shortlist Findings",
        "",
        "## What we changed",
        "",
        "We added a conservative routing layer on top of the active path/mechanism shortlist.",
        "",
        "Routing rule:",
        "- emit `context_transfer` when context gap is high enough to land in the top quartile of the direct-scored context-transfer family",
        "- emit `evidence_type_expansion` when evidence design is narrow enough to land in the top quartile of the direct-scored evidence-expansion family",
        "- otherwise keep the baseline path/mechanism object",
        "",
        "## Counts",
        "",
        f"- changed rows: `{summary['changed_rows']}`",
        f"- changed unique pairs: `{summary['changed_pairs_unique']}`",
        f"- context threshold (q75): `{summary['context_threshold_q75']:.3f}`",
        f"- evidence threshold (q75): `{summary['evidence_threshold_q75']:.3f}`",
        f"- suppression counts: `{summary.get('suppression_counts', {})}`",
        "",
        "## First read",
        "",
        "This is the right kind of upgrade.",
        "",
        "The routing layer does not overwrite the whole shortlist. It only upgrades the object when the richer ontology signal is unusually strong.",
        "It also now blocks context-transfer routing when the endpoint labels are too generic.",
        "",
        "That makes the result easier to trust and easier to explain.",
        "",
        "## What to review next",
        "",
        "We should now compare the changed rows against their baseline titles and ask whether the routed object is genuinely more useful, or just more specific.",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    findings_path = Path(args.findings_note)
    findings_path.parent.mkdir(parents=True, exist_ok=True)

    base = pd.read_csv(args.shortlist)
    context = _threshold_and_percentile(pd.read_csv(args.context_scored))
    evidence = _threshold_and_percentile(pd.read_csv(args.evidence_scored))
    context_map = _route_lookup(context, "context_transfer")
    evidence_map = _route_lookup(evidence, "evidence_type_expansion")

    routed = _apply_routes(base, context_map, evidence_map)
    summary = _summary(routed, context, evidence)

    routed.to_csv(out_dir / "routed_shortlist.csv", index=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(routed, summary, out_dir / "routed_shortlist.md")
    _write_findings(summary, findings_path)
    print(f"Wrote routed shortlist to {out_dir}")
    print(f"Wrote findings note to {findings_path}")


if __name__ == "__main__":
    main()
