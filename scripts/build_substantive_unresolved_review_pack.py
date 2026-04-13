from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


GENERIC_STOPWORDS = {
    "the",
    "and",
    "of",
    "in",
    "to",
    "for",
    "on",
    "with",
    "from",
    "an",
    "a",
}
POLICY_BUNDLE_TERMS = {
    "policy",
    "policies",
    "protocol",
    "guidelines",
    "recommendations",
    "auctioning",
    "permit",
    "permits",
    "target",
    "targets",
    "mitigation",
    "subsidy",
    "subsidies",
    "tax",
    "taxes",
    "assessment",
    "intervention",
    "pricing",
    "scheme",
    "schemes",
}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "not_applicable": 3}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an internal review pack for substantive unresolved edges.")
    parser.add_argument(
        "--audit",
        default="data/processed/ontology_vnext_proto_v1/evidence_unknown_audit.parquet",
        dest="audit_path",
    )
    parser.add_argument(
        "--canonical",
        default="data/processed/ontology_vnext_proto_v1/canonical_concepts.parquet",
        dest="canonical_path",
    )
    parser.add_argument(
        "--families",
        default="data/processed/ontology_vnext_proto_v1/concept_families.parquet",
        dest="families_path",
    )
    parser.add_argument(
        "--manual-labels",
        default="next_steps/policy_outcome_or_boundary_manual_labels.csv",
        dest="manual_labels_path",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/31_substantive_unresolved_review",
        dest="out_dir",
    )
    return parser.parse_args()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _tokenize(value: Any) -> set[str]:
    text = _normalize(value)
    return {
        token
        for token in re.split(r"[^a-z0-9]+", text)
        if token and token not in GENERIC_STOPWORDS and len(token) >= 2
    }


def _likely_boundary_case(source_label: Any, target_label: Any) -> bool:
    source_norm = _normalize(source_label)
    target_norm = _normalize(target_label)
    if not source_norm or not target_norm:
        return False
    if source_norm in target_norm or target_norm in source_norm:
        return True
    source_tokens = _tokenize(source_label)
    target_tokens = _tokenize(target_label)
    if not source_tokens or not target_tokens:
        return False
    if source_tokens.issubset(target_tokens) or target_tokens.issubset(source_tokens):
        return True
    union = source_tokens | target_tokens
    if not union:
        return False
    return (len(source_tokens & target_tokens) / len(union)) >= 0.5


def _likely_regime_bundle(source_label: Any, target_label: Any) -> bool:
    tokens = _tokenize(source_label) | _tokenize(target_label)
    return bool(tokens & POLICY_BUNDLE_TERMS)


def _load_manual_labels(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["source_concept_id", "target_concept_id", "manual_review_label"])
    df = pd.read_csv(path)
    required = {"source_concept_id", "target_concept_id", "manual_review_label"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["source_concept_id", "target_concept_id", "manual_review_label"])
    return df[list(required)].drop_duplicates(["source_concept_id", "target_concept_id"])


def _sort_review_rows(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_priority_rank"] = out["audit_priority"].map(PRIORITY_ORDER).fillna(99).astype(int)
    out = out.sort_values(
        ["_priority_rank", "distinct_paper_support", "weight", "source_label", "target_label"],
        ascending=[True, False, False, True, True],
    ).drop(columns=["_priority_rank"])
    return out.reset_index(drop=True)


def _attach_supporting_fields(
    audit_df: pd.DataFrame,
    canonical_df: pd.DataFrame,
    families_df: pd.DataFrame,
    manual_labels_df: pd.DataFrame,
) -> pd.DataFrame:
    out = audit_df.copy()
    canonical_lookup = canonical_df.rename(
        columns={
            "concept_id": "concept_id_tmp",
            "preferred_label": "canonical_label_tmp",
        }
    )[["concept_id_tmp", "canonical_label_tmp"]]
    family_lookup = families_df.rename(
        columns={
            "member_concept_id": "concept_id_tmp",
            "family_id": "family_id_tmp",
            "family_label": "family_label_tmp",
            "family_assignment_source": "family_assignment_source_tmp",
        }
    )[["concept_id_tmp", "family_id_tmp", "family_label_tmp", "family_assignment_source_tmp"]]

    out = out.merge(canonical_lookup, left_on="source_concept_id", right_on="concept_id_tmp", how="left").drop(columns=["concept_id_tmp"])
    out = out.rename(columns={"canonical_label_tmp": "source_canonical_label"})
    out = out.merge(canonical_lookup, left_on="target_concept_id", right_on="concept_id_tmp", how="left").drop(columns=["concept_id_tmp"])
    out = out.rename(columns={"canonical_label_tmp": "target_canonical_label"})

    out = out.merge(family_lookup, left_on="source_concept_id", right_on="concept_id_tmp", how="left").drop(columns=["concept_id_tmp"])
    out = out.rename(
        columns={
            "family_id_tmp": "source_family_id",
            "family_label_tmp": "source_family_label",
            "family_assignment_source_tmp": "source_family_assignment_source",
        }
    )
    out = out.merge(family_lookup, left_on="target_concept_id", right_on="concept_id_tmp", how="left").drop(columns=["concept_id_tmp"])
    out = out.rename(
        columns={
            "family_id_tmp": "target_family_id",
            "family_label_tmp": "target_family_label",
            "family_assignment_source_tmp": "target_family_assignment_source",
        }
    )

    out["same_reviewed_family"] = (
        out["source_family_id"].astype(str).eq(out["target_family_id"].astype(str))
        & out["source_family_assignment_source"].astype(str).eq("explicit_seed")
        & out["target_family_assignment_source"].astype(str).eq("explicit_seed")
    )
    out["has_context_entity"] = (
        out["source_context_entity_type"].astype(str).ne("none")
        | out["target_context_entity_type"].astype(str).ne("none")
    )
    out["likely_boundary_case"] = out.apply(
        lambda row: _likely_boundary_case(row["source_label"], row["target_label"]),
        axis=1,
    )
    out["likely_regime_or_implementation_bundle"] = out.apply(
        lambda row: _likely_regime_bundle(row["source_label"], row["target_label"]),
        axis=1,
    )
    out = out.merge(manual_labels_df, on=["source_concept_id", "target_concept_id"], how="left")
    out["manual_review_label"] = out["manual_review_label"].fillna("")
    return out


def _markdown_for_rows(df: pd.DataFrame, title: str) -> str:
    lines = [f"# {title}", ""]
    for idx, row in enumerate(df.itertuples(index=False), start=1):
        lines.extend(
            [
                f"## {idx}. `{row.source_label} -> {row.target_label}`",
                "",
                f"- Concepts: `{row.source_concept_id}` -> `{row.target_concept_id}`",
                f"- Subtype: `{row.substantive_subtype}` | priority `{row.audit_priority}`",
                f"- Support: papers `{int(row.distinct_paper_support)}` | weight `{float(row.weight):.2f}` | taxonomy confidence `{float(row.taxonomy_confidence):.2f}`",
                f"- Unknown reason: `{row.unknown_reason or 'none'}`",
                f"- Types: `{row.source_primary_concept_type}` -> `{row.target_primary_concept_type}`",
                f"- Context entities: `{row.source_context_entity_type}` -> `{row.target_context_entity_type}`",
                f"- Families: `{row.source_family_label}` -> `{row.target_family_label}`",
                f"- Flags: same_reviewed_family=`{bool(row.same_reviewed_family)}` | has_context_entity=`{bool(row.has_context_entity)}` | likely_boundary_case=`{bool(row.likely_boundary_case)}` | likely_regime_or_implementation_bundle=`{bool(row.likely_regime_or_implementation_bundle)}`",
                f"- Manual review label: `{row.manual_review_label or 'unlabeled'}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_df = pd.read_parquet(args.audit_path)
    canonical_df = pd.read_parquet(args.canonical_path)
    families_df = pd.read_parquet(args.families_path)
    manual_labels_df = _load_manual_labels(Path(args.manual_labels_path))

    substantive = audit_df[audit_df["audit_bucket"].astype(str).eq("substantive_unresolved")].copy()
    relation_semantic_mask = substantive.get("edge_relation_semantic_type", pd.Series("none", index=substantive.index)).astype(str).ne("none")
    relation_semantic_excluded = int(relation_semantic_mask.sum())
    substantive = substantive.loc[~relation_semantic_mask].copy()
    substantive = _attach_supporting_fields(substantive, canonical_df, families_df, manual_labels_df)

    policy_top = substantive[substantive["substantive_subtype"].astype(str).eq("policy_outcome_or_boundary")].copy()
    policy_top = _sort_review_rows(policy_top).head(50).reset_index(drop=True)

    balanced_parts = []
    for subtype, n in [
        ("policy_outcome_or_boundary", 25),
        ("event_institution_context", 15),
        ("finance_attribute_bundle", 10),
        ("quantity_count_object", 10),
        ("general_substantive_other", 15),
    ]:
        part = substantive[substantive["substantive_subtype"].astype(str).eq(subtype)].copy()
        balanced_parts.append(_sort_review_rows(part).head(n))
    strongest = pd.concat(balanced_parts, ignore_index=True)

    policy_csv = out_dir / "policy_outcome_or_boundary_top.csv"
    policy_md = out_dir / "policy_outcome_or_boundary_top.md"
    strongest_csv = out_dir / "strongest_substantive_unresolved.csv"
    strongest_md = out_dir / "strongest_substantive_unresolved.md"
    summary_json = out_dir / "summary.json"

    policy_top.to_csv(policy_csv, index=False)
    strongest.to_csv(strongest_csv, index=False)
    policy_md.write_text(_markdown_for_rows(policy_top, "Policy Outcome Or Boundary Top Review"), encoding="utf-8")
    strongest_md.write_text(_markdown_for_rows(strongest, "Strongest Substantive Unresolved Review"), encoding="utf-8")

    summary = {
        "relation_semantic_resolved_rows_excluded": relation_semantic_excluded,
        "policy_outcome_or_boundary_top_rows": int(len(policy_top)),
        "strongest_substantive_unresolved_rows": int(len(strongest)),
        "strongest_counts_by_subtype": strongest["substantive_subtype"].value_counts().sort_index().to_dict(),
        "policy_manual_review_label_counts": policy_top["manual_review_label"].replace("", "unlabeled").value_counts().sort_index().to_dict(),
        "canonical_join_coverage": {
            "source": float(policy_top["source_canonical_label"].notna().mean()) if len(policy_top) else 1.0,
            "target": float(policy_top["target_canonical_label"].notna().mean()) if len(policy_top) else 1.0,
        },
        "family_join_coverage": {
            "source": float(policy_top["source_family_label"].notna().mean()) if len(policy_top) else 1.0,
            "target": float(policy_top["target_family_label"].notna().mean()) if len(policy_top) else 1.0,
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote substantive unresolved review pack to {out_dir}")


if __name__ == "__main__":
    main()
