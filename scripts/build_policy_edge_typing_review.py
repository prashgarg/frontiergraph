from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


UNRESOLVED_DESIGN_FAMILIES = {"do_not_know", "other", "unknown"}
TARGET_KEYWORDS = {"target", "targets", "goal", "goals", "ndc", "ndcs", "indc", "indcs", "carbon neutrality", "commitment", "commitments"}
INSTRUMENT_KEYWORDS = {"tax", "taxes", "trading", "auctioning", "permit", "permits", "subsidy", "subsidies", "price", "prices", "pricing", "market", "markets", "ets", "scheme", "schemes"}
IMPLEMENTATION_KEYWORDS = {"guideline", "guidelines", "recommendation", "recommendations", "delivery", "assessment", "practice", "implementation"}
GOVERNANCE_KEYWORDS = {"protocol", "treaty", "regime", "governance", "accord", "institutional", "policy", "policies"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the broader policy edge typing review layer from the 31 and 32 review packs.")
    parser.add_argument(
        "--strong-csv",
        default="outputs/paper/32_strong_substantive_regime_review/strong_substantive_candidates.csv",
        dest="strong_csv",
    )
    parser.add_argument(
        "--policy-review-csv",
        default="outputs/paper/31_substantive_unresolved_review/policy_outcome_or_boundary_top.csv",
        dest="policy_review_csv",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/33_policy_edge_typing_review",
        dest="out_dir",
    )
    return parser.parse_args()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _json_has_content(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text and text not in {"[]", "{}", "", "nan", "None"})


def _classify_strong_edge_need(row: pd.Series) -> tuple[str, str, str]:
    design_family = str(row.get("edge_design_family", "") or "")
    dominant_relation = str(row.get("dominant_relation_type", "") or "")
    dominant_causal = str(row.get("dominant_causal_presentation", "") or "")
    edge_mode = str(row.get("edge_evidence_mode", "") or "")
    has_context = _json_has_content(row.get("dominant_countries_json")) or _json_has_content(row.get("dominant_units_json"))

    if dominant_relation != "effect" or dominant_causal == "noncausal":
        secondary = "context_scope_capture" if edge_mode == "empirics" and has_context else "none"
        return "relation_semantics_review", secondary, "association_or_noncausal_surface"
    if design_family in UNRESOLVED_DESIGN_FAMILIES:
        secondary = "context_scope_capture" if edge_mode == "empirics" and has_context else "none"
        reason = "design_family_missing_with_context" if secondary == "context_scope_capture" else "design_family_missing"
        return "design_family_inference", secondary, reason
    secondary = "context_scope_capture" if edge_mode == "empirics" and has_context else "none"
    return "substantive_ready", secondary, "typed_edge_ready"


def _classify_policy_edge_semantic_type(row: pd.Series) -> tuple[str, float, str]:
    target_norm = _normalize(row.get("target_label"))
    source_norm = _normalize(row.get("source_label"))
    context_norm = _normalize(row.get("context_note_examples_json"))

    def contains_any(text: str, keywords: set[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    for text, confidence, reason in [
        (target_norm, 1.0, "target_label_keyword"),
        (source_norm, 0.75, "source_label_keyword"),
        (context_norm, 0.5, "context_note_keyword"),
    ]:
        if contains_any(text, TARGET_KEYWORDS):
            return "policy_target", confidence, reason
        if contains_any(text, INSTRUMENT_KEYWORDS):
            return "policy_instrument", confidence, reason
        if contains_any(text, IMPLEMENTATION_KEYWORDS):
            return "implementation_mechanism", confidence, reason
        if contains_any(text, GOVERNANCE_KEYWORDS):
            return "governance_regime", confidence, reason
    return "unclassified", 0.5, "unclassified"


def _classify_broader_regime_status(row: pd.Series) -> str:
    reviewed_decision = str(row.get("regime_guardrail_decision", "") or "")
    reviewed_reason = str(row.get("regime_guardrail_reason", "") or "")
    if reviewed_decision == "drop" and reviewed_reason in {"generic_policy_object", "boundary_case"}:
        return "generic_policy_object" if reviewed_reason == "generic_policy_object" else "mixed_boundary_case"
    if reviewed_decision == "keep":
        return "clean_policy_semantic"
    target_norm = _normalize(row.get("target_label"))
    source_norm = _normalize(row.get("source_label"))
    manual_label = str(row.get("manual_review_label", "") or "")
    if target_norm == "policy" or source_norm == "policy":
        return "generic_policy_object"
    if manual_label == "boundary_or_near_duplicate" or bool(row.get("likely_boundary_case", False)):
        return "mixed_boundary_case"
    return "clean_policy_semantic"


def _markdown_grouped(df: pd.DataFrame, title: str, group_col: str) -> str:
    lines = [f"# {title}", ""]
    for group_value, sub in df.groupby(group_col, sort=False):
        lines.append(f"## `{group_value}`")
        lines.append("")
        for row in sub.itertuples(index=False):
            lines.append(f"- `{row.source_label} -> {row.target_label}` | papers `{int(row.distinct_paper_support)}` | weight `{float(row.weight):.2f}`")
            extra = []
            if hasattr(row, "edge_typing_primary_need"):
                extra.append(f"primary `{row.edge_typing_primary_need}`")
                extra.append(f"secondary `{row.edge_typing_secondary_need}`")
                extra.append(f"reason `{row.edge_typing_reason}`")
            if hasattr(row, "policy_edge_semantic_type"):
                extra.append(f"semantic `{row.policy_edge_semantic_type}`")
                if hasattr(row, "broader_regime_queue_status"):
                    extra.append(f"status `{row.broader_regime_queue_status}`")
                if hasattr(row, "policy_edge_semantic_confidence"):
                    extra.append(f"confidence `{float(row.policy_edge_semantic_confidence):.2f}`")
            lines.append("  " + " | ".join(extra))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    strong_df = pd.read_csv(args.strong_csv)
    policy_df = pd.read_csv(args.policy_review_csv)

    strong_meta = strong_df.apply(_classify_strong_edge_need, axis=1)
    strong_df = strong_df.copy()
    strong_df["edge_typing_primary_need"] = strong_meta.map(lambda item: item[0])
    strong_df["edge_typing_secondary_need"] = strong_meta.map(lambda item: item[1])
    strong_df["edge_typing_reason"] = strong_meta.map(lambda item: item[2])
    strong_df = strong_df.sort_values(
        ["edge_typing_primary_need", "edge_typing_secondary_need", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, True, False, False, True, True],
    ).reset_index(drop=True)

    regime_like_df = policy_df[
        policy_df["likely_regime_or_implementation_bundle"].fillna(False).astype(bool)
        | policy_df["manual_review_label"].astype(str).eq("regime_or_implementation_bundle")
    ].copy()
    regime_like_df["regime_queue_source"] = regime_like_df["manual_review_label"].astype(str).apply(
        lambda value: "manual_regime_bundle" if value == "regime_or_implementation_bundle" else "keyword_flagged_regime_like"
    )
    regime_meta = regime_like_df.apply(_classify_policy_edge_semantic_type, axis=1)
    reviewed_policy_mask = regime_like_df.get("regime_guardrail_decision", pd.Series("not_applicable", index=regime_like_df.index)).astype(str).ne("not_applicable")
    inferred_semantic = regime_meta.map(lambda item: item[0])
    inferred_confidence = regime_meta.map(lambda item: item[1]).astype(float)
    inferred_reason = regime_meta.map(lambda item: item[2])
    regime_like_df["policy_edge_semantic_type"] = regime_like_df.get("policy_edge_semantic_type", pd.Series("none", index=regime_like_df.index)).fillna("none").astype(str)
    regime_like_df["policy_edge_semantic_confidence"] = pd.to_numeric(
        regime_like_df.get("policy_edge_semantic_confidence", pd.Series(0.0, index=regime_like_df.index)),
        errors="coerce",
    ).fillna(0.0).astype(float)
    regime_like_df["policy_edge_semantic_reason"] = regime_like_df.get("policy_edge_semantic_reason", pd.Series("", index=regime_like_df.index)).fillna("").astype(str)
    regime_like_df.loc[~reviewed_policy_mask, "policy_edge_semantic_type"] = inferred_semantic.loc[~reviewed_policy_mask]
    regime_like_df.loc[~reviewed_policy_mask, "policy_edge_semantic_confidence"] = inferred_confidence.loc[~reviewed_policy_mask]
    regime_like_df.loc[~reviewed_policy_mask, "policy_edge_semantic_reason"] = inferred_reason.loc[~reviewed_policy_mask]
    regime_like_df["broader_regime_queue_status"] = regime_like_df.apply(_classify_broader_regime_status, axis=1)
    regime_like_df = regime_like_df.sort_values(
        ["policy_edge_semantic_type", "broader_regime_queue_status", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, True, False, False, True, True],
    ).reset_index(drop=True)

    strong_csv = out_dir / "strong_substantive_edge_typed.csv"
    strong_md = out_dir / "strong_substantive_edge_typed.md"
    regime_csv = out_dir / "broader_regime_bundle_typed.csv"
    regime_md = out_dir / "broader_regime_bundle_typed.md"
    summary_json = out_dir / "summary.json"

    strong_df.to_csv(strong_csv, index=False)
    regime_like_df.to_csv(regime_csv, index=False)
    strong_md.write_text(_markdown_grouped(strong_df, "Strong Substantive Edge Typing Review", "edge_typing_primary_need"), encoding="utf-8")
    regime_md.write_text(_markdown_grouped(regime_like_df, "Broader Regime Bundle Typed Review", "policy_edge_semantic_type"), encoding="utf-8")

    summary = {
        "strong_substantive_rows": int(len(strong_df)),
        "strong_substantive_counts_by_primary_need": strong_df["edge_typing_primary_need"].value_counts().sort_index().to_dict(),
        "strong_substantive_counts_by_secondary_need": strong_df["edge_typing_secondary_need"].value_counts().sort_index().to_dict(),
        "broader_regime_like_rows": int(len(regime_like_df)),
        "broader_regime_counts_by_semantic_type": regime_like_df["policy_edge_semantic_type"].value_counts().sort_index().to_dict(),
        "broader_regime_counts_by_status": regime_like_df["broader_regime_queue_status"].value_counts().sort_index().to_dict(),
        "broader_regime_counts_by_source": regime_like_df["regime_queue_source"].value_counts().sort_index().to_dict(),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote policy edge typing review outputs to {out_dir}")


if __name__ == "__main__":
    main()
