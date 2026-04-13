"""Finalize adjudication for the remaining-heuristic hard cases.

This resolves the 738 former no-majority rows from the second-pass
remaining-heuristic review:
1. strict modal rows from the 11-vote panel are accepted directly
2. tied modal rows are resolved by explicit manual adjudication
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

SOURCE_PATH = DATA_DIR / "remaining_heuristic_no_majority_modal_vote_11run.parquet"
OUTPUT_PARQUET = DATA_DIR / "remaining_heuristic_no_majority_final_adjudicated.parquet"
OUTPUT_CSV = DATA_DIR / "remaining_heuristic_no_majority_final_adjudicated.csv"
OUTPUT_MD = DATA_DIR / "remaining_heuristic_no_majority_final_adjudication_note.md"


MANUAL_OVERRIDES: dict[str, dict[str, Any]] = {
    "rhr_00262_row": {
        "label": "realized volatility (rv)",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Realized volatility",
        "manual_reason": (
            "Realized volatility is a standard finance construct. It is closely related to realized variance, "
            "but not cleanly reducible to it, so promoting a distinct family preserves the concept."
        ),
    },
    "rhr_01014_row": {
        "label": "firm-sponsored training",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Formal Training Programs",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This reads as a subtype of formal training rather than a missing standalone family. "
            "Broad grounding preserves the label without over-expanding the ontology."
        ),
    },
    "rhr_01309_row": {
        "label": "distribution of returns",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Return distribution",
        "manual_reason": (
            "This is a recognizable finance/statistics concept. Generic distribution nodes are too broad, "
            "so a dedicated family is the cleaner grounding."
        ),
    },
    "rhr_01773_row": {
        "label": "simulation methods",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Simulation",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a generic methodological phrase. Broad attachment to Simulation captures the method family "
            "without creating an unnecessary new ontology node."
        ),
    },
    "rhr_02288_row": {
        "label": "political tensions",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Political tensions",
        "manual_reason": (
            "The phrase denotes a recurring political-economy context that is broader and softer than crisis or conflict. "
            "Promoting a family preserves that distinction."
        ),
    },
    "rhr_02323_row": {
        "label": "poor health",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "State of health",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a directional state descriptor rather than a distinct concept family. "
            "Broad grounding to State of health is the safest fit."
        ),
    },
    "rhr_03027_row": {
        "label": "coal resource tax reform",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Tax reform",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a specific reform episode inside a broader tax-reform domain. "
            "A safe parent concept exists, so broad grounding is preferable to creating a one-off family."
        ),
    },
    "rhr_03732_row": {
        "label": "business cycle frequencies",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Business Cycles",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a frequency-domain specialization of business-cycle analysis rather than a separate ontology family. "
            "Broad attachment is sufficient."
        ),
    },
    "rhr_04116_row": {
        "label": "uniform rule",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "The phrase is too generic to anchor cleanly. It may be real in context, but there is no safe existing target "
            "or stable new-family interpretation."
        ),
    },
    "rhr_04543_row": {
        "label": "social transfers",
        "final_decision": "accept_existing_broad",
        "manual_canonical_target_label": "Income Transfer",
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is close to the transfer domain, but not exact enough for aliasing. "
            "Broad grounding to Income Transfer preserves the main economics meaning."
        ),
    },
    "rhr_04802_row": {
        "label": "temperature overshoot",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Temperature overshoot",
        "manual_reason": (
            "Overshoot is a distinct climate concept, not just generic overheating. "
            "A separate family better captures its policy and climate-economics use."
        ),
    },
    "rhr_04803_row": {
        "label": "this paper (current study)",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is paper-internal meta language rather than a research concept. "
            "The raw label should be preserved for traceability, but ontology attachment should be rejected."
        ),
    },
    "rhr_04922_row": {
        "label": "portfolio separation",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Portfolio separation",
        "manual_reason": (
            "This is a real finance concept and is more specific than generic portfolio allocation. "
            "Promoting a family preserves that established distinction."
        ),
    },
    "rhr_04988_row": {
        "label": "house price expectations",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "House price expectations",
        "manual_reason": (
            "Expectations about house prices are substantively distinct from house prices themselves. "
            "A dedicated family is cleaner than collapsing to the level variable."
        ),
    },
    "rhr_04995_row": {
        "label": "paper conclusions",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is paper-meta language rather than a stable concept node. "
            "Rejecting ontology attachment is safer than inventing a family."
        ),
    },
    "rhr_05059_row": {
        "label": "random regret minimisation (rrm)",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Random regret minimisation",
        "manual_reason": (
            "This is a named discrete-choice framework, not just generic regret. "
            "It merits a distinct family node."
        ),
    },
    "rhr_05219_row": {
        "label": "decisional conflict",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Decisional conflict",
        "manual_reason": (
            "This is a recognizable decision-science construct. "
            "Generic decision problem nodes are too broad for it."
        ),
    },
    "rhr_05373_row": {
        "label": "monday",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "On its own this is too fragmentary and context-dependent to serve as an ontology concept. "
            "It likely reflects a truncated weekday effect or scheduling mention."
        ),
    },
    "rhr_05648_row": {
        "label": "earlier work",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a backward-looking paper-reference phrase, not a stable research concept. "
            "Ontology attachment should be rejected."
        ),
    },
    "rhr_06510_row": {
        "label": "dominant firm",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Dominant firm",
        "manual_reason": (
            "This is a standard industrial-organization concept and is not equivalent to a generic price maker label. "
            "It should remain distinct."
        ),
    },
    "rhr_10265_row": {
        "label": "energy stock market",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Energy stock market",
        "manual_reason": (
            "This denotes a meaningful market segment and current ontology neighbors are clearly off-target. "
            "A family promotion is safer than forced broad attachment."
        ),
    },
    "rhr_11195_row": {
        "label": "policy anticipations hypothesis",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Policy anticipations hypothesis",
        "manual_reason": (
            "This reads like a named expectations-related proposition rather than a generic expectations-hypothesis alias. "
            "A distinct family keeps that specificity."
        ),
    },
    "rhr_11376_row": {
        "label": "western guangdong",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a geographic regional label. It is valid context, but not something we should eagerly promote into "
            "the ontology without a cleaner geographic hierarchy."
        ),
    },
    "rhr_12995_row": {
        "label": "erm membership",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "ERM membership",
        "manual_reason": (
            "Exchange-rate mechanism membership is a real institutional status in international macro and finance. "
            "It deserves a distinct family rather than a generic membership node."
        ),
    },
    "rhr_14528_row": {
        "label": "market services",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Market services",
        "manual_reason": (
            "This is a standard sectoral classification phrase and is not well captured by generic market nodes. "
            "A distinct family is cleaner."
        ),
    },
    "rhr_16865_row": {
        "label": "household vulnerability to poverty",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Household vulnerability to poverty",
        "manual_reason": (
            "This is a recurring development and welfare concept. "
            "Current candidates are too weak or acronym-bound to support safe aliasing."
        ),
    },
    "rhr_19557_row": {
        "label": "simple model presented in paper",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is paper-internal exposition language, not a reusable concept family. "
            "Rejecting ontology attachment is the right treatment."
        ),
    },
    "rhr_21145_row": {
        "label": "benchmarking allocation method",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This sounds method-like, but the phrase is still too generic and context-bound to justify either a new family "
            "or a safe existing target."
        ),
    },
    "rhr_22828_row": {
        "label": "first-order approach validity",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a methodological validity phrase rather than a stable canonical concept. "
            "Keeping it unresolved is safer than inventing a family."
        ),
    },
    "rhr_24075_row": {
        "label": "liberal-market economies",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Liberal market economies",
        "manual_reason": (
            "This is a named comparative-political-economy construct from the varieties-of-capitalism literature. "
            "It should remain distinct from generic market economy nodes."
        ),
    },
    "rhr_25209_row": {
        "label": "perspective of the analysis",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is framing language about how a paper is written, not a stable research concept. "
            "Ontology attachment should be rejected."
        ),
    },
    "rhr_25290_row": {
        "label": "policymakers and researchers",
        "final_decision": "reject_match_keep_raw",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This is a conjunction of actor groups, usually part of framing or audience language rather than a concept node. "
            "Rejecting the attachment is cleaner."
        ),
    },
    "rhr_25580_row": {
        "label": "professional self-regulation",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Professional self-regulation",
        "manual_reason": (
            "This is a recognizable institutional-governance concept and is more specific than generic self-regulatory organization. "
            "A dedicated family is justified."
        ),
    },
    "rhr_25742_row": {
        "label": "rating duration",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "The phrase is too ambiguous across finance and ratings contexts to resolve confidently. "
            "Leaving it unresolved is the safer option."
        ),
    },
    "rhr_26793_row": {
        "label": "tgc prices",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This acronym-heavy phrase looks like a real market label, but it is too opaque to ground safely without domain-specific expansion. "
            "Keep it unresolved."
        ),
    },
    "rhr_26909_row": {
        "label": "trade tensions",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Trade tensions",
        "manual_reason": (
            "Trade tensions is a standard softer concept than trade war, often used in policy and international-economics work. "
            "It should remain distinct."
        ),
    },
    "rhr_27317_row": {
        "label": "world interest rate (fall)",
        "final_decision": "keep_unresolved",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": None,
        "manual_reason": (
            "This mixes a macro concept with a directional episode marker. "
            "Without a cleaner canonical form, unresolved treatment is safer than forced grounding."
        ),
    },
    "rhr_27638_row": {
        "label": "use of antibiotics",
        "final_decision": "promote_new_concept_family",
        "manual_canonical_target_label": None,
        "manual_new_concept_family_label": "Antibiotic use",
        "manual_reason": (
            "This is an exposure or behavior construct that is meaningfully distinct from antibiotics as an object. "
            "A dedicated family preserves that distinction."
        ),
    },
}


def modal_value(values: list[Any]) -> Any:
    clean = [v for v in values if pd.notna(v) and str(v).strip()]
    if not clean:
        return None
    counts = Counter(clean)
    max_count = max(counts.values())
    winners = [value for value, count in counts.items() if count == max_count]
    for value in clean:
        if value in winners:
            return value
    return winners[0]


def modal_from_supporting_runs(row: pd.Series, field_stub: str, decision: str) -> str | None:
    values: list[str] = []
    for prefix in ("rh1", "rh2", "rh3"):
        decision_col = f"{prefix}_decision"
        value_col = f"{prefix}_{field_stub}"
        if (
            decision_col in row.index
            and value_col in row.index
            and row.get(decision_col) == decision
            and pd.notna(row.get(value_col))
            and str(row.get(value_col)).strip()
        ):
            values.append(str(row.get(value_col)).strip())
    chosen = modal_value(values)
    return str(chosen) if chosen is not None else None


def build_final_adjudicated() -> pd.DataFrame:
    df = pd.read_parquet(SOURCE_PATH).copy()

    df["final_decision"] = df["modal_decision"]
    df["adjudication_source"] = df["modal_type"].map(
        {
            "strict_modal": "remaining_hard_modal",
            "weak_modal": "remaining_hard_modal_weak",
            "tied_modal": "manual_override_pending",
        }
    )
    df["manual_canonical_target_label"] = df.apply(
        lambda row: modal_from_supporting_runs(row, "canonical_target_label", str(row["final_decision"]))
        if pd.notna(row.get("final_decision"))
        else None,
        axis=1,
    )
    df["manual_new_concept_family_label"] = df.apply(
        lambda row: modal_from_supporting_runs(row, "new_concept_family_label", str(row["final_decision"]))
        if pd.notna(row.get("final_decision"))
        else None,
        axis=1,
    )
    df["manual_reason"] = None

    for review_id, override in MANUAL_OVERRIDES.items():
        mask = df["review_id"] == review_id
        if not mask.any():
            continue
        df.loc[mask, "final_decision"] = override["final_decision"]
        df.loc[mask, "manual_canonical_target_label"] = override["manual_canonical_target_label"]
        df.loc[mask, "manual_new_concept_family_label"] = override["manual_new_concept_family_label"]
        df.loc[mask, "manual_reason"] = override["manual_reason"]
        df.loc[mask, "adjudication_source"] = "manual_override"

    return df


def write_note(df: pd.DataFrame) -> None:
    lines = [
        "# Remaining-Heuristic Hard-Case Final Adjudication",
        "",
        "- Input set: `738` former no-majority remaining-heuristic rows",
        f"- Resolved by strict modal vote: `{int((df['adjudication_source'] == 'remaining_hard_modal').sum()):,}`",
        f"- Resolved by manual override: `{int((df['adjudication_source'] == 'manual_override').sum()):,}`",
        "",
        "## Final decision counts",
    ]
    for decision, count in df["final_decision"].fillna("missing").value_counts().items():
        lines.append(f"- `{decision}`: `{int(count):,}`")

    lines.extend(["", "## Manual adjudications"])
    for review_id, override in MANUAL_OVERRIDES.items():
        lines.extend(
            [
                "",
                f"### `{override['label']}` (`{review_id}`)",
                f"- Final decision: `{override['final_decision']}`",
                f"- Canonical target: `{override['manual_canonical_target_label']}`"
                if override["manual_canonical_target_label"]
                else "- Canonical target: `None`",
                f"- New concept family: `{override['manual_new_concept_family_label']}`"
                if override["manual_new_concept_family_label"]
                else "- New concept family: `None`",
                f"- Reason: {override['manual_reason']}",
            ]
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df = build_final_adjudicated()
    df.to_parquet(OUTPUT_PARQUET, index=False)
    df.to_csv(OUTPUT_CSV, index=False)
    write_note(df)


if __name__ == "__main__":
    main()
