from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
PAPER_OUT_DIR = ROOT / "outputs" / "paper" / "49_ontology_grounding_sensitivity_reviewed_round3"

GROUNDING_PATH = DATA_DIR / "extraction_label_grounding_v2.parquet"
AUDIT_PATH = DATA_DIR / "grounding_rescue_audit_v2.parquet"
CLUSTER_SUMMARY_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2.parquet"
ADJUDICATED_PATH = DATA_DIR / "main_grounding_review_v2_adjudicated.parquet"
REMAINING_ROW_MAJORITY_PATH = DATA_DIR / "remaining_heuristic_row_review_majority.parquet"
REMAINING_HARD_FINAL_PATH = DATA_DIR / "remaining_heuristic_no_majority_final_adjudicated.parquet"
ONTOLOGY_PATH = DATA_DIR / "ontology_v2_final.json"

GROUNDING_REVIEWED_PATH = DATA_DIR / "extraction_label_grounding_v2_reviewed_round3.parquet"
OVERLAY_REVIEWED_PATH = DATA_DIR / "ontology_enrichment_overlay_v2_reviewed_round3.parquet"
PROPOSALS_REVIEWED_PATH = DATA_DIR / "ontology_missing_concept_proposals_v2_reviewed_round3.parquet"
CLUSTERS_REVIEWED_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2_reviewed_round3.parquet"
NOTE_PATH = DATA_DIR / "reviewed_overlay_application_note_round3.md"


def load_module(script_name: str, module_name: str):
    path = ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def modal_from_supporting_runs(row: pd.Series, stub: str, decision: str) -> str | None:
    values: list[str] = []
    for prefix in ("rh1", "rh2", "rh3"):
        decision_col = f"{prefix}_decision"
        value_col = f"{prefix}_{stub}"
        if (
            decision_col in row.index
            and value_col in row.index
            and row.get(decision_col) == decision
            and pd.notna(row.get(value_col))
            and str(row.get(value_col)).strip()
        ):
            values.append(str(row.get(value_col)).strip())
    if not values:
        return None
    counts = pd.Series(values).value_counts()
    return str(counts.index[0])


def normalize_remaining_majority() -> pd.DataFrame:
    majority = pd.read_parquet(REMAINING_ROW_MAJORITY_PATH).copy()
    majority = majority[majority["majority_decision"].notna()].copy()
    majority["final_decision"] = majority["majority_decision"]
    majority["review_item_type"] = "row"
    majority["applied_review_source"] = "remaining_row_majority_review"
    majority["manual_canonical_target_label"] = majority.apply(
        lambda row: modal_from_supporting_runs(row, "canonical_target_label", str(row["final_decision"])),
        axis=1,
    )
    majority["manual_new_concept_family_label"] = majority.apply(
        lambda row: modal_from_supporting_runs(row, "new_concept_family_label", str(row["final_decision"])),
        axis=1,
    )
    majority["manual_reason"] = None
    return majority


def normalize_remaining_hard_final() -> pd.DataFrame:
    hard = pd.read_parquet(REMAINING_HARD_FINAL_PATH).copy()
    hard["review_item_type"] = "row"
    source_map = {
        "remaining_hard_modal": "remaining_hard_modal_review",
        "remaining_hard_modal_weak": "remaining_hard_modal_weak_review",
        "manual_override": "remaining_manual_override_review",
    }
    hard["applied_review_source"] = hard["adjudication_source"].map(source_map).fillna("remaining_hard_review")
    return hard


def build_review_layers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, object]:
    reviewed = load_module("build_reviewed_ontology_overlay_v2.py", "overlay_reviewed_base_round3")
    grounding = pd.read_parquet(GROUNDING_PATH)
    audit = pd.read_parquet(AUDIT_PATH)
    clusters = pd.read_parquet(CLUSTER_SUMMARY_PATH)
    adjudicated = pd.read_parquet(ADJUDICATED_PATH)
    remaining_majority = normalize_remaining_majority()
    remaining_hard = normalize_remaining_hard_final()

    grounding_module = reviewed.load_grounding_module()
    ontology_rows = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    ontology_lookup = reviewed.build_ontology_lookup(ontology_rows, grounding_module.normalize_label)

    original_row_reviews = (
        adjudicated[adjudicated["review_item_type"].isin(["row", "unresolved_row"])]
        .drop_duplicates(subset=["label"])
        .set_index("label")
    )
    remaining_reviews = pd.concat([remaining_majority, remaining_hard], axis=0, ignore_index=True)
    remaining_reviews = remaining_reviews.drop_duplicates(subset=["label"], keep="last").set_index("label")
    combined_row_reviews = pd.concat(
        [original_row_reviews[~original_row_reviews.index.isin(remaining_reviews.index)], remaining_reviews],
        axis=0,
    )
    cluster_reviews = (
        adjudicated[adjudicated["review_item_type"] == "cluster_medoid"]
        .drop_duplicates(subset=["cluster_id"])
        .set_index("cluster_id")
    )
    cluster_lookup = clusters.set_index("cluster_id")

    grounding_reviewed = grounding.merge(
        audit[
            [
                "label",
                "issue_type",
                "cluster_id",
                "cluster_proposal",
                "cluster_representative_label",
                "cluster_mean_similarity",
                "cluster_weighted_freq",
                "dominant_onto_id",
                "dominant_onto_label",
                "dominant_share",
                "alt_concept_id",
                "alt_concept_label",
                "proposed_onto_id",
                "proposed_onto_label",
            ]
        ],
        on="label",
        how="left",
    )

    overlay_rows: list[dict[str, object]] = []
    proposal_rows: list[dict[str, object]] = []
    seen_proposal_keys: set[tuple[str, str]] = set()

    row_decision_counts: dict[str, int] = {}
    cluster_decision_counts: dict[str, int] = {}

    for _, row in audit.iterrows():
        label = str(row["label"])
        cluster_id = row.get("cluster_id")
        row_review = combined_row_reviews.loc[label] if label in combined_row_reviews.index else None
        cluster_review = cluster_reviews.loc[cluster_id] if pd.notna(cluster_id) and cluster_id in cluster_reviews.index else None
        cluster_row = cluster_lookup.loc[cluster_id] if pd.notna(cluster_id) and cluster_id in cluster_lookup.index else None

        heuristic = reviewed.heuristic_decision(row.get("issue_type"))
        if row_review is not None:
            decision = str(row_review["final_decision"])
            applied_source = row_review.get("applied_review_source")
            if pd.notna(applied_source) and str(applied_source).strip():
                decision_source = str(applied_source)
            else:
                decision_source = f"{row_review['review_item_type']}_review"
            source_review = row_review
            row_decision_counts[decision] = row_decision_counts.get(decision, 0) + 1
        elif cluster_review is not None:
            decision = str(cluster_review["final_decision"])
            decision_source = "cluster_review"
            source_review = cluster_review
            cluster_decision_counts[decision] = cluster_decision_counts.get(decision, 0) + 1
        else:
            decision = heuristic
            decision_source = "heuristic"
            source_review = None

        resolved_onto_id, resolved_onto_label, preferred_label = reviewed.resolve_target(
            decision=decision,
            review_row=source_review,
            audit_row=row,
            cluster_row=cluster_row,
            ontology_lookup=ontology_lookup,
            normalize_fn=grounding_module.normalize_label,
        )

        if decision in {"accept_existing_broad", "accept_existing_alias"} and not resolved_onto_id:
            if cluster_review is not None and str(cluster_review["final_decision"]) == "promote_new_concept_family":
                decision = "promote_new_concept_family"
                decision_source = f"{decision_source}_fallback_new_family"
            else:
                decision = "keep_unresolved"
                decision_source = f"{decision_source}_fallback_unresolved"

        overlay_action = reviewed.overlay_action_from_decision(decision)
        new_family_label = None
        if decision == "promote_new_concept_family":
            new_family_label = reviewed.resolve_new_family_label(source_review, row, cluster_row)

        overlay_rows.append(
            {
                "label": label,
                "label_raw": row.get("label_raw"),
                "freq": int(row.get("freq", 0)),
                "unique_papers": int(row.get("unique_papers", 0)),
                "impact_score": float(row.get("impact_score", 0.0)),
                "score_band": row.get("score_band"),
                "issue_type": row.get("issue_type"),
                "cluster_id": cluster_id,
                "overlay_action": overlay_action,
                "final_decision": decision,
                "decision_source": decision_source,
                "reviewed_preferred_target_label": preferred_label,
                "proposed_onto_id": resolved_onto_id,
                "proposed_onto_label": resolved_onto_label,
                "proposed_new_concept_family_label": new_family_label,
                "preserve_raw_label": True,
            }
        )

    overlay_df = pd.DataFrame(overlay_rows).sort_values(
        ["impact_score", "freq"], ascending=[False, False]
    ).reset_index(drop=True)

    cluster_reviewed_rows: list[dict[str, object]] = []
    for _, row in clusters.iterrows():
        cluster_id = row["cluster_id"]
        cluster_review = cluster_reviews.loc[cluster_id] if cluster_id in cluster_reviews.index else None
        decision = str(cluster_review["final_decision"]) if cluster_review is not None else reviewed.heuristic_decision(
            {
                "attach_existing_broad": "broader_concept_available",
                "add_alias_to_existing": "missing_alias",
                "propose_new_concept_family": "missing_concept_family",
                "reject_cluster": "bad_match_or_noise",
                "keep_unresolved": "unclear",
            }.get(str(row.get("cluster_proposal")), "unclear")
        )
        decision_source = "cluster_review" if cluster_review is not None else "heuristic"
        final_cluster_proposal = reviewed.cluster_proposal_from_decision(decision)

        new_family_label = None
        if decision == "promote_new_concept_family":
            new_family_label = reviewed.resolve_new_family_label(
                cluster_review,
                pd.Series({"label": row["cluster_representative_label"]}),
                row,
            )

        cluster_reviewed_rows.append(
            {
                **row.to_dict(),
                "final_decision": decision,
                "decision_source": decision_source,
                "final_cluster_proposal": final_cluster_proposal,
                "proposed_new_concept_family_label": new_family_label,
            }
        )

        if final_cluster_proposal in {"propose_new_concept_family", "keep_unresolved"}:
            proposal_key = (cluster_id, final_cluster_proposal)
            if proposal_key not in seen_proposal_keys:
                seen_proposal_keys.add(proposal_key)
                proposal_rows.append(
                    {
                        "proposal_scope": "cluster",
                        "cluster_id": cluster_id,
                        "cluster_proposal": final_cluster_proposal,
                        "decision_source": decision_source,
                        "cluster_representative_label": row["cluster_representative_label"],
                        "proposed_new_concept_family_label": new_family_label,
                        "cluster_size": int(row["cluster_size"]),
                        "cluster_weighted_freq": int(row["cluster_weighted_freq"]),
                        "cluster_weighted_unique_papers": int(row["cluster_weighted_unique_papers"]),
                        "cluster_mean_similarity": float(row["cluster_mean_similarity"]),
                        "member_labels_json": row["member_labels_json"],
                    }
                )

    for _, row in overlay_df[overlay_df["overlay_action"] == "propose_new_concept_family"].iterrows():
        cluster_id = row.get("cluster_id")
        proposal_key = (str(cluster_id), str(row["label"]))
        if proposal_key in seen_proposal_keys:
            continue
        seen_proposal_keys.add(proposal_key)
        proposal_rows.append(
            {
                "proposal_scope": "row",
                "cluster_id": cluster_id,
                "cluster_proposal": "propose_new_concept_family",
                "decision_source": row["decision_source"],
                "cluster_representative_label": row["label"],
                "proposed_new_concept_family_label": row["proposed_new_concept_family_label"],
                "cluster_size": None,
                "cluster_weighted_freq": int(row["freq"]),
                "cluster_weighted_unique_papers": int(row["unique_papers"]),
                "cluster_mean_similarity": None,
                "member_labels_json": json.dumps([row["label"]], ensure_ascii=False),
            }
        )

    clusters_reviewed_df = pd.DataFrame(cluster_reviewed_rows).sort_values(
        ["cluster_weighted_freq", "cluster_size"], ascending=[False, False]
    ).reset_index(drop=True)
    proposals_reviewed_df = pd.DataFrame(proposal_rows).sort_values(
        ["cluster_weighted_freq", "cluster_representative_label"], ascending=[False, True]
    ).reset_index(drop=True)

    grounding_reviewed = grounding_reviewed.merge(
        overlay_df[
            [
                "label",
                "overlay_action",
                "final_decision",
                "decision_source",
                "reviewed_preferred_target_label",
                "proposed_onto_id",
                "proposed_onto_label",
                "proposed_new_concept_family_label",
            ]
        ],
        on="label",
        how="left",
    )

    summary = pd.DataFrame(
        [
            {"bucket": "row_review_applied_round3", **{k: int(v) for k, v in row_decision_counts.items()}},
            {"bucket": "cluster_review_applied", **{k: int(v) for k, v in cluster_decision_counts.items()}},
            {
                "bucket": "final_overlay_actions_round3",
                **{k: int(v) for k, v in overlay_df["overlay_action"].value_counts().to_dict().items()},
            },
            {
                "bucket": "decision_sources_round3",
                **{k: int(v) for k, v in overlay_df["decision_source"].value_counts().to_dict().items()},
            },
        ]
    ).fillna(0)

    return grounding_reviewed, overlay_df, clusters_reviewed_df, proposals_reviewed_df, summary, grounding_module


def write_note(summary: pd.DataFrame, sensitivity_summary: pd.DataFrame, overlay_df: pd.DataFrame, proposals_df: pd.DataFrame) -> None:
    lines = [
        "# Reviewed Overlay Application Note Round 3",
        "",
        "This pass applies the manual adjudications for the last remaining 38 tied rows from the remaining-heuristic hard-case panel.",
        "",
        "Key rules used:",
        "- original adjudicated row reviews still override everything else",
        "- remaining heuristic rows with a three-run majority remain `remaining_row_majority_review`",
        "- remaining hard-case rows now use modal or manual row-level review rather than heuristic fallback",
        "- cluster reviews remain a separate neighborhood-level layer",
        "- unresolved raw labels are always preserved",
        "",
        "## Final overlay action counts",
    ]
    for action, count in overlay_df["overlay_action"].value_counts().items():
        lines.append(f"- `{action}`: `{int(count):,}`")
    lines.extend(["", "## Decision source counts"])
    for source, count in overlay_df["decision_source"].value_counts().items():
        lines.append(f"- `{source}`: `{int(count):,}`")
    lines.extend(["", "## Proposal counts"])
    for proposal, count in proposals_df["cluster_proposal"].value_counts().items():
        lines.append(f"- `{proposal}`: `{int(count):,}`")
    lines.extend(["", "## Sensitivity snapshot"])
    for _, row in sensitivity_summary.iterrows():
        lines.append(
            f"- threshold `{row['threshold']:.2f}`: overlay labels `{int(row['overlay_labels_with_attachment']):,}`, "
            f"overlay occurrences `{int(row['overlay_occurrences_with_attachment']):,}`, "
            f"unique grounded concepts `{int(row['unique_grounded_concepts']):,}`"
        )
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PAPER_OUT_DIR.mkdir(parents=True, exist_ok=True)

    grounding_reviewed, overlay_df, clusters_reviewed_df, proposals_reviewed_df, summary_df, grounding_module = build_review_layers()

    grounding_reviewed.to_parquet(GROUNDING_REVIEWED_PATH, index=False)
    overlay_df.to_parquet(OVERLAY_REVIEWED_PATH, index=False)
    clusters_reviewed_df.to_parquet(CLUSTERS_REVIEWED_PATH, index=False)
    proposals_reviewed_df.to_parquet(PROPOSALS_REVIEWED_PATH, index=False)

    sensitivity_summary_df, benchmark_sensitivity_df = grounding_module.build_threshold_sensitivity(
        grounding_reviewed,
        overlay_df,
        grounding_module.parse_extractions(grounding_module.EXTRACTIONS_PATH)[1],
    )
    sensitivity_summary_df.to_csv(PAPER_OUT_DIR / "summary.csv", index=False)
    benchmark_sensitivity_df.to_csv(PAPER_OUT_DIR / "benchmark_sensitivity.csv", index=False)
    grounding_module.write_sensitivity_markdown(PAPER_OUT_DIR / "summary.md", sensitivity_summary_df)

    write_note(summary_df, sensitivity_summary_df, overlay_df, proposals_reviewed_df)

    print("Round-3 reviewed overlay artifacts written.")
    print(f"Grounding reviewed rows: {len(grounding_reviewed):,}")
    print(f"Overlay reviewed rows: {len(overlay_df):,}")
    print(f"Cluster summaries reviewed: {len(clusters_reviewed_df):,}")
    print(f"Proposal rows reviewed: {len(proposals_reviewed_df):,}")


if __name__ == "__main__":
    main()
