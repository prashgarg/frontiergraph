from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


GENERIC_POLICY_TERMS = {"policy", "policies"}
SERIES_KEYWORDS = {"annual time series", "monthly", "quarterly", "time series"}
PANEL_KEYWORDS = {"panel of", "panel data"}
DESCRIPTIVE_KEYWORDS = {"dea", "malmquist", "sample of", "earnings equation", "specifications"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the 34 internal design-family inference and regime-guardrail review layer.")
    parser.add_argument(
        "--strong-edge-typed-csv",
        default="outputs/paper/33_policy_edge_typing_review/strong_substantive_edge_typed.csv",
        dest="strong_csv",
    )
    parser.add_argument(
        "--broader-regime-csv",
        default="outputs/paper/33_policy_edge_typing_review/broader_regime_bundle_typed.csv",
        dest="regime_csv",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/34_design_family_inference_review",
        dest="out_dir",
    )
    return parser.parse_args()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _json_count(value: Any) -> int:
    text = str(value or "").strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return 0
    try:
        parsed = json.loads(text)
    except Exception:
        return 0
    if isinstance(parsed, list):
        return len(parsed)
    return 0


def _contains_any(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _infer_design_family(row: pd.Series) -> tuple[str, float, str]:
    notes = _normalize(row.get("context_note_examples_json"))
    countries_count = _json_count(row.get("dominant_countries_json"))
    units = _normalize(row.get("dominant_units_json"))
    years_count = _json_count(row.get("dominant_years_json"))
    edge_mode = str(row.get("edge_evidence_mode", "") or "")

    if _contains_any(notes, PANEL_KEYWORDS) or ("countries" in notes and years_count >= 1):
        return "panel_FE_or_TWFE", 0.75, "panel_keyword_or_multi_country_panel"
    if _contains_any(notes, SERIES_KEYWORDS):
        return "time_series_econometrics", 0.75, "time_series_keyword"
    if _contains_any(notes, DESCRIPTIVE_KEYWORDS):
        return "descriptive_observational", 0.5, "descriptive_keyword_fallback"
    if edge_mode == "empirics" and (countries_count > 0 or "country" in units or "market" in units):
        return "descriptive_observational", 0.5, "empirical_context_fallback"
    if edge_mode == "empirics":
        return "descriptive_observational", 0.5, "empirical_mode_fallback"
    return "unresolved", 0.25, "insufficient_design_signal"


def _guardrail_decision(row: pd.Series) -> tuple[str, str]:
    reviewed_decision = str(row.get("regime_guardrail_decision", "") or "")
    reviewed_reason = str(row.get("regime_guardrail_reason", "") or "")
    if reviewed_decision in {"keep", "drop"}:
        return reviewed_decision, reviewed_reason or ("clean_policy_semantic" if reviewed_decision == "keep" else "boundary_case")
    source_norm = _normalize(row.get("source_label"))
    target_norm = _normalize(row.get("target_label"))
    manual_label = str(row.get("manual_review_label", "") or "")
    likely_boundary = bool(row.get("likely_boundary_case", False))

    if source_norm in GENERIC_POLICY_TERMS or target_norm in GENERIC_POLICY_TERMS:
        return "drop", "generic_policy_object"
    if manual_label == "boundary_or_near_duplicate" or likely_boundary:
        return "drop", "boundary_case"
    return "keep", "clean_policy_semantic"


def _markdown_grouped(df: pd.DataFrame, title: str, group_col: str, extra_cols: list[str]) -> str:
    lines = [f"# {title}", ""]
    for group_value, sub in df.groupby(group_col, sort=False):
        lines.append(f"## `{group_value}`")
        lines.append("")
        for row in sub.itertuples(index=False):
            lines.append(f"- `{row.source_label} -> {row.target_label}` | papers `{int(row.distinct_paper_support)}` | weight `{float(row.weight):.2f}`")
            details = []
            for col in extra_cols:
                value = getattr(row, col)
                if isinstance(value, float):
                    details.append(f"{col} `{value:.2f}`")
                else:
                    details.append(f"{col} `{value}`")
            lines.append("  " + " | ".join(details))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    strong_df = pd.read_csv(args.strong_csv)
    regime_df = pd.read_csv(args.regime_csv)

    infer_mask = strong_df["edge_typing_primary_need"].astype(str).eq("design_family_inference")
    inferred_df = strong_df[infer_mask].copy()
    inference_meta = inferred_df.apply(_infer_design_family, axis=1)
    inferred_df["proposed_design_family"] = inference_meta.map(lambda item: item[0])
    inferred_df["design_inference_confidence"] = inference_meta.map(lambda item: item[1]).astype(float)
    inferred_df["design_inference_reason"] = inference_meta.map(lambda item: item[2])
    inferred_df["needs_manual_design_review"] = inferred_df["proposed_design_family"].astype(str).eq("unresolved")
    inferred_df = inferred_df.sort_values(
        ["proposed_design_family", "design_inference_confidence", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, False, False, False, True, True],
    ).reset_index(drop=True)

    guardrail_meta = regime_df.apply(_guardrail_decision, axis=1)
    guarded_df = regime_df.copy()
    guarded_df["regime_guardrail_decision"] = guardrail_meta.map(lambda item: item[0])
    guarded_df["regime_guardrail_reason"] = guardrail_meta.map(lambda item: item[1])
    kept_regime_df = guarded_df[guarded_df["regime_guardrail_decision"].astype(str).eq("keep")].copy()
    kept_regime_df = kept_regime_df.sort_values(
        ["policy_edge_semantic_type", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)
    guarded_df = guarded_df.sort_values(
        ["regime_guardrail_decision", "policy_edge_semantic_type", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, True, False, False, True, True],
    ).reset_index(drop=True)

    inferred_csv = out_dir / "strong_substantive_design_family_inferred.csv"
    inferred_md = out_dir / "strong_substantive_design_family_inferred.md"
    guardrail_csv = out_dir / "broader_regime_bundle_guardrailed.csv"
    guardrail_md = out_dir / "broader_regime_bundle_guardrailed.md"
    kept_csv = out_dir / "broader_regime_bundle_kept.csv"
    kept_md = out_dir / "broader_regime_bundle_kept.md"
    summary_json = out_dir / "summary.json"

    inferred_df.to_csv(inferred_csv, index=False)
    guarded_df.to_csv(guardrail_csv, index=False)
    kept_regime_df.to_csv(kept_csv, index=False)
    inferred_md.write_text(
        _markdown_grouped(
            inferred_df,
            "Strong Substantive Design Family Inference",
            "proposed_design_family",
            ["design_inference_confidence", "design_inference_reason", "needs_manual_design_review"],
        ),
        encoding="utf-8",
    )
    guardrail_md.write_text(
        _markdown_grouped(
            guarded_df,
            "Broader Regime Bundle Guardrail Review",
            "regime_guardrail_decision",
            ["regime_guardrail_reason", "policy_edge_semantic_type", "broader_regime_queue_status"],
        ),
        encoding="utf-8",
    )
    kept_md.write_text(
        _markdown_grouped(
            kept_regime_df,
            "Broader Regime Bundle Kept Rows",
            "policy_edge_semantic_type",
            ["regime_guardrail_reason", "broader_regime_queue_status"],
        ),
        encoding="utf-8",
    )

    summary = {
        "design_family_inference_rows": int(len(inferred_df)),
        "design_family_counts": inferred_df["proposed_design_family"].value_counts().sort_index().to_dict(),
        "design_family_manual_review_needed": int(inferred_df["needs_manual_design_review"].astype(bool).sum()),
        "broader_regime_rows": int(len(guarded_df)),
        "broader_regime_guardrail_counts": guarded_df["regime_guardrail_decision"].value_counts().sort_index().to_dict(),
        "broader_regime_guardrail_reason_counts": guarded_df["regime_guardrail_reason"].value_counts().sort_index().to_dict(),
        "broader_regime_kept_rows": int(len(kept_regime_df)),
        "broader_regime_kept_semantic_counts": kept_regime_df["policy_edge_semantic_type"].value_counts().sort_index().to_dict(),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote design-family inference and regime-guardrail review outputs to {out_dir}")


if __name__ == "__main__":
    main()
