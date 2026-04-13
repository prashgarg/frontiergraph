from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


UNRESOLVED_DESIGN_FAMILIES = {"do_not_know", "other", "unknown"}
TARGET_KEYWORDS = {"target", "targets", "goal", "goals", "ndc", "ndcs", "indc", "indcs", "carbon neutrality", "commitment", "commitments"}
INSTRUMENT_KEYWORDS = {"tax", "taxes", "trading", "auctioning", "permit", "permits", "subsidy", "subsidies", "price", "prices", "pricing", "market", "markets"}
IMPLEMENTATION_KEYWORDS = {"guideline", "guidelines", "recommendation", "recommendations", "delivery", "assessment", "practice", "implementation"}
GOVERNANCE_KEYWORDS = {"protocol", "treaty", "regime", "governance", "accord", "institutional"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the strong-substantive and regime review layer from the 31 review pack.")
    parser.add_argument(
        "--policy-review-csv",
        default="outputs/paper/31_substantive_unresolved_review/policy_outcome_or_boundary_top.csv",
        dest="policy_review_csv",
    )
    parser.add_argument(
        "--review-summary-json",
        default="outputs/paper/31_substantive_unresolved_review/summary.json",
        dest="review_summary_json",
    )
    parser.add_argument(
        "--manual-labels-csv",
        default="next_steps/policy_outcome_or_boundary_manual_labels.csv",
        dest="manual_labels_csv",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/32_strong_substantive_regime_review",
        dest="out_dir",
    )
    return parser.parse_args()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _json_text_has_content(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text and text not in {"[]", "{}", "", "nan", "None"})


def _classify_candidate_extension(row: pd.Series) -> str:
    design_family = str(row.get("edge_design_family", "") or "")
    dominant_causal = str(row.get("dominant_causal_presentation", "") or "")
    taxonomy_confidence = float(row.get("taxonomy_confidence", 0.0) or 0.0)
    edge_mode = str(row.get("edge_evidence_mode", "") or "")
    has_context = _json_text_has_content(row.get("dominant_countries_json")) or _json_text_has_content(row.get("dominant_units_json"))

    if (design_family in UNRESOLVED_DESIGN_FAMILIES or taxonomy_confidence < 0.75) and dominant_causal in {"explicit_causal", "implicit_causal"}:
        return "evidence_type_expansion"
    if edge_mode == "empirics" and has_context:
        return "context_transfer"
    return "none"


def _next_review_action(extension: str) -> str:
    if extension == "evidence_type_expansion":
        return "evidence_type_cleanup"
    if extension == "context_transfer":
        return "context_transfer_check"
    return "direct_substantive_review"


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


def _markdown_grouped(df: pd.DataFrame, title: str, group_col: str) -> str:
    lines = [f"# {title}", ""]
    for group_value, sub in df.groupby(group_col, sort=False):
        lines.append(f"## `{group_value}`")
        lines.append("")
        for row in sub.itertuples(index=False):
            lines.extend(
                [
                    f"- `{row.source_label} -> {row.target_label}` | papers `{int(row.distinct_paper_support)}` | weight `{float(row.weight):.2f}`",
                    f"  Follow-up: `{getattr(row, 'next_review_action', '') or getattr(row, 'policy_edge_semantic_type', '')}`",
                ]
            )
            if hasattr(row, "candidate_frontier_extension"):
                lines.append(f"  Candidate extension: `{row.candidate_frontier_extension}` | paper candidate `{bool(row.paper_candidate)}`")
            if hasattr(row, "policy_edge_semantic_type"):
                lines.append(
                    f"  Coarse policy type: `{row.policy_edge_semantic_type}` | confidence `{float(row.policy_edge_semantic_confidence):.2f}` | reason `{row.policy_edge_semantic_reason}`"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    review_df = pd.read_csv(args.policy_review_csv)
    _ = json.loads(Path(args.review_summary_json).read_text(encoding="utf-8"))
    _ = pd.read_csv(args.manual_labels_csv)

    strong_df = review_df[review_df["manual_review_label"].astype(str).eq("strong_substantive")].copy()
    strong_df["candidate_frontier_extension"] = strong_df.apply(_classify_candidate_extension, axis=1)
    strong_df["next_review_action"] = strong_df["candidate_frontier_extension"].map(_next_review_action)
    paper_support_median = float(strong_df["distinct_paper_support"].median()) if len(strong_df) else 0.0
    strong_df["paper_candidate"] = (
        strong_df["manual_review_label"].astype(str).eq("strong_substantive")
        & ~strong_df["likely_boundary_case"].fillna(False).astype(bool)
        & ~strong_df["likely_regime_or_implementation_bundle"].fillna(False).astype(bool)
        & (pd.to_numeric(strong_df["distinct_paper_support"], errors="coerce").fillna(0.0) >= paper_support_median)
    )
    strong_df = strong_df.sort_values(
        ["next_review_action", "paper_candidate", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, False, False, False, True, True],
    ).reset_index(drop=True)

    regime_df = review_df[review_df["manual_review_label"].astype(str).eq("regime_or_implementation_bundle")].copy()
    regime_meta = regime_df.apply(_classify_policy_edge_semantic_type, axis=1)
    regime_df["policy_edge_semantic_type"] = regime_meta.map(lambda item: item[0])
    regime_df["policy_edge_semantic_confidence"] = regime_meta.map(lambda item: item[1]).astype(float)
    regime_df["policy_edge_semantic_reason"] = regime_meta.map(lambda item: item[2])
    regime_df = regime_df.sort_values(
        ["policy_edge_semantic_type", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)

    strong_csv = out_dir / "strong_substantive_candidates.csv"
    strong_md = out_dir / "strong_substantive_candidates.md"
    regime_csv = out_dir / "regime_bundle_typed.csv"
    regime_md = out_dir / "regime_bundle_typed.md"
    summary_json = out_dir / "summary.json"

    strong_df.to_csv(strong_csv, index=False)
    regime_df.to_csv(regime_csv, index=False)
    strong_md.write_text(_markdown_grouped(strong_df, "Strong Substantive Candidates", "next_review_action"), encoding="utf-8")
    regime_md.write_text(_markdown_grouped(regime_df, "Regime Bundle Typed Review", "policy_edge_semantic_type"), encoding="utf-8")

    summary = {
        "strong_substantive_rows": int(len(strong_df)),
        "strong_substantive_counts_by_next_review_action": strong_df["next_review_action"].value_counts().sort_index().to_dict(),
        "strong_substantive_counts_by_candidate_frontier_extension": strong_df["candidate_frontier_extension"].value_counts().sort_index().to_dict(),
        "paper_candidate_count": int(pd.to_numeric(strong_df["paper_candidate"], errors="coerce").fillna(False).astype(bool).sum()),
        "regime_bundle_rows": int(len(regime_df)),
        "regime_bundle_counts_by_policy_edge_semantic_type": regime_df["policy_edge_semantic_type"].value_counts().sort_index().to_dict(),
        "paper_support_median": paper_support_median,
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote strong-substantive and regime review outputs to {out_dir}")


if __name__ == "__main__":
    main()
