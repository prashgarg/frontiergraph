from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
PAPER_OUT_DIR = ROOT / "outputs" / "paper" / "46_ontology_grounding_sensitivity_reviewed"

GROUNDING_PATH = DATA_DIR / "extraction_label_grounding_v2.parquet"
AUDIT_PATH = DATA_DIR / "grounding_rescue_audit_v2.parquet"
CLUSTER_SUMMARY_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2.parquet"
ADJUDICATED_PATH = DATA_DIR / "main_grounding_review_v2_adjudicated.parquet"
ONTOLOGY_PATH = DATA_DIR / "ontology_v2_final.json"

GROUNDING_REVIEWED_PATH = DATA_DIR / "extraction_label_grounding_v2_reviewed.parquet"
OVERLAY_REVIEWED_PATH = DATA_DIR / "ontology_enrichment_overlay_v2_reviewed.parquet"
PROPOSALS_REVIEWED_PATH = DATA_DIR / "ontology_missing_concept_proposals_v2_reviewed.parquet"
CLUSTERS_REVIEWED_PATH = DATA_DIR / "unresolved_label_cluster_summaries_v2_reviewed.parquet"
NOTE_PATH = DATA_DIR / "reviewed_overlay_application_note.md"


def load_grounding_module():
    path = ROOT / "scripts" / "build_ontology_v2_open_world_grounding.py"
    spec = importlib.util.spec_from_file_location("grounding_overlay_v2_reviewed", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def heuristic_decision(issue_type: str | None) -> str:
    return {
        "broader_concept_available": "accept_existing_broad",
        "missing_alias": "accept_existing_alias",
        "missing_concept_family": "promote_new_concept_family",
        "bad_match_or_noise": "reject_match_keep_raw",
        "unclear": "keep_unresolved",
    }.get(str(issue_type or "unclear"), "keep_unresolved")


def overlay_action_from_decision(decision: str | None) -> str:
    return {
        "accept_existing_broad": "attach_existing_broad",
        "accept_existing_alias": "add_alias_to_existing",
        "promote_new_concept_family": "propose_new_concept_family",
        "reject_match_keep_raw": "reject_cluster",
        "keep_unresolved": "keep_unresolved",
        "unclear": "keep_unresolved",
    }.get(str(decision or "keep_unresolved"), "keep_unresolved")


def cluster_proposal_from_decision(decision: str | None) -> str:
    return overlay_action_from_decision(decision)


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


def normalized(value: Any, normalize_fn) -> str:
    return normalize_fn(str(value or "")).strip()


def build_ontology_lookup(ontology_rows: list[dict[str, Any]], normalize_fn) -> dict[str, list[dict[str, Any]]]:
    lookup: dict[str, list[dict[str, Any]]] = {}
    for row in ontology_rows:
        labels = {row.get("label")}
        for source_row in row.get("_sources", []):
            labels.add(source_row.get("label"))
        for label in labels:
            label_norm = normalized(label, normalize_fn)
            if not label_norm:
                continue
            lookup.setdefault(label_norm, []).append(
                {
                    "id": row.get("id"),
                    "label": row.get("label"),
                    "source": row.get("source"),
                }
            )
    return lookup


def row_vote_label(review_row: pd.Series, field_stub: str, decision: str) -> Any:
    values = []
    for run in ("run1", "run2", "run3"):
        decision_col = f"{run}_decision"
        value_col = f"{run}_{field_stub}"
        if decision_col in review_row and value_col in review_row and review_row[decision_col] == decision:
            values.append(review_row[value_col])
    return modal_value(values)


def resolve_target(
    decision: str,
    review_row: pd.Series | None,
    audit_row: pd.Series,
    cluster_row: pd.Series | None,
    ontology_lookup: dict[str, list[dict[str, Any]]],
    normalize_fn,
) -> tuple[str | None, str | None, str | None]:
    if decision not in {"accept_existing_broad", "accept_existing_alias"}:
        return None, None, None

    preferred_label = None
    if review_row is not None and pd.notna(review_row.get("manual_canonical_target_label")):
        preferred_label = review_row.get("manual_canonical_target_label")
    if not preferred_label and review_row is not None:
        preferred_label = row_vote_label(review_row, "canonical_target_label", decision)

    context_pairs: list[tuple[Any, Any]] = []
    for label_col, id_col in [
        ("proposed_onto_label", "proposed_onto_id"),
        ("alt_concept_label", "alt_concept_id"),
        ("onto_label", "onto_id"),
        ("dominant_onto_label", "dominant_onto_id"),
        ("rank2_label", "rank2_id"),
    ]:
        if label_col in audit_row.index:
            context_pairs.append((audit_row.get(label_col), audit_row.get(id_col)))
    if cluster_row is not None:
        context_pairs.append((cluster_row.get("dominant_onto_label"), cluster_row.get("dominant_onto_id")))

    context_pairs = [(label, onto_id) for label, onto_id in context_pairs if pd.notna(label) and str(label).strip()]
    preferred_norm = normalized(preferred_label, normalize_fn) if preferred_label else ""

    if preferred_norm:
        for label, onto_id in context_pairs:
            if normalized(label, normalize_fn) == preferred_norm and pd.notna(onto_id):
                return str(onto_id), str(label), str(preferred_label)
        matches = ontology_lookup.get(preferred_norm, [])
        if len(matches) == 1:
            match = matches[0]
            return str(match["id"]), str(match["label"]), str(preferred_label)

    if decision == "accept_existing_broad":
        for label_col, id_col in [
            ("proposed_onto_label", "proposed_onto_id"),
            ("dominant_onto_label", "dominant_onto_id"),
            ("alt_concept_label", "alt_concept_id"),
            ("onto_label", "onto_id"),
        ]:
            label = audit_row.get(label_col)
            onto_id = audit_row.get(id_col)
            if pd.notna(label) and pd.notna(onto_id):
                return str(onto_id), str(label), str(preferred_label) if preferred_label else str(label)

    if decision == "accept_existing_alias":
        for label_col, id_col in [
            ("alt_concept_label", "alt_concept_id"),
            ("proposed_onto_label", "proposed_onto_id"),
            ("dominant_onto_label", "dominant_onto_id"),
            ("onto_label", "onto_id"),
        ]:
            label = audit_row.get(label_col)
            onto_id = audit_row.get(id_col)
            if pd.notna(label) and pd.notna(onto_id):
                return str(onto_id), str(label), str(preferred_label) if preferred_label else str(label)

    return None, None, str(preferred_label) if preferred_label else None


def resolve_new_family_label(
    review_row: pd.Series | None,
    audit_row: pd.Series,
    cluster_row: pd.Series | None,
) -> str:
    if review_row is not None and pd.notna(review_row.get("manual_new_concept_family_label")):
        return str(review_row["manual_new_concept_family_label"])
    if review_row is not None:
        voted = row_vote_label(review_row, "new_concept_family_label", "promote_new_concept_family")
        if voted:
            return str(voted)
    if cluster_row is not None and pd.notna(cluster_row.get("cluster_representative_label")):
        return str(cluster_row["cluster_representative_label"])
    return str(audit_row["label"])


def build_review_layers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Any]:
    grounding = pd.read_parquet(GROUNDING_PATH)
    audit = pd.read_parquet(AUDIT_PATH)
    clusters = pd.read_parquet(CLUSTER_SUMMARY_PATH)
    adjudicated = pd.read_parquet(ADJUDICATED_PATH)

    module = load_grounding_module()
    ontology_rows = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    ontology_lookup = build_ontology_lookup(ontology_rows, module.normalize_label)

    row_reviews = (
        adjudicated[adjudicated["review_item_type"].isin(["row", "unresolved_row"])]
        .drop_duplicates(subset=["label"])
        .set_index("label")
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

    overlay_rows = []
    proposal_rows = []
    seen_proposal_keys: set[tuple[str, str]] = set()

    cluster_decision_counts: Counter[str] = Counter()
    row_decision_counts: Counter[str] = Counter()

    for _, row in audit.iterrows():
        label = str(row["label"])
        cluster_id = row.get("cluster_id")
        row_review = row_reviews.loc[label] if label in row_reviews.index else None
        cluster_review = cluster_reviews.loc[cluster_id] if pd.notna(cluster_id) and cluster_id in cluster_reviews.index else None
        cluster_row = cluster_lookup.loc[cluster_id] if pd.notna(cluster_id) and cluster_id in cluster_lookup.index else None

        heuristic = heuristic_decision(row.get("issue_type"))
        if row_review is not None:
            decision = str(row_review["final_decision"])
            decision_source = f"{row_review['review_item_type']}_review"
            source_review = row_review
            row_decision_counts[decision] += 1
        elif cluster_review is not None:
            decision = str(cluster_review["final_decision"])
            decision_source = "cluster_review"
            source_review = cluster_review
            cluster_decision_counts[decision] += 1
        else:
            decision = heuristic
            decision_source = "heuristic"
            source_review = None

        resolved_onto_id, resolved_onto_label, preferred_label = resolve_target(
            decision=decision,
            review_row=source_review,
            audit_row=row,
            cluster_row=cluster_row,
            ontology_lookup=ontology_lookup,
            normalize_fn=module.normalize_label,
        )

        if decision in {"accept_existing_broad", "accept_existing_alias"} and not resolved_onto_id:
            if cluster_review is not None and str(cluster_review["final_decision"]) == "promote_new_concept_family":
                decision = "promote_new_concept_family"
                decision_source = f"{decision_source}_fallback_new_family"
            else:
                decision = "keep_unresolved"
                decision_source = f"{decision_source}_fallback_unresolved"

        overlay_action = overlay_action_from_decision(decision)
        new_family_label = None
        if decision == "promote_new_concept_family":
            new_family_label = resolve_new_family_label(source_review, row, cluster_row)

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

    cluster_reviewed_rows = []
    for _, row in clusters.iterrows():
        cluster_id = row["cluster_id"]
        cluster_review = cluster_reviews.loc[cluster_id] if cluster_id in cluster_reviews.index else None
        decision = str(cluster_review["final_decision"]) if cluster_review is not None else heuristic_decision(
            {
                "attach_existing_broad": "broader_concept_available",
                "add_alias_to_existing": "missing_alias",
                "propose_new_concept_family": "missing_concept_family",
                "reject_cluster": "bad_match_or_noise",
                "keep_unresolved": "unclear",
            }.get(str(row.get("cluster_proposal")), "unclear")
        )
        decision_source = "cluster_review" if cluster_review is not None else "heuristic"
        final_cluster_proposal = cluster_proposal_from_decision(decision)

        new_family_label = None
        if decision == "promote_new_concept_family":
            new_family_label = resolve_new_family_label(cluster_review, pd.Series({"label": row["cluster_representative_label"]}), row)

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
            {"bucket": "row_review_applied", **{k: int(v) for k, v in row_decision_counts.items()}},
            {"bucket": "cluster_review_applied", **{k: int(v) for k, v in cluster_decision_counts.items()}},
            {
                "bucket": "final_overlay_actions",
                **{k: int(v) for k, v in overlay_df["overlay_action"].value_counts().to_dict().items()},
            },
        ]
    ).fillna(0)

    return grounding_reviewed, overlay_df, clusters_reviewed_df, proposals_reviewed_df, summary, module


def write_note(
    summary: pd.DataFrame,
    sensitivity_summary: pd.DataFrame,
    overlay_df: pd.DataFrame,
    proposals_df: pd.DataFrame,
) -> None:
    lines = [
        "# Reviewed Overlay Application Note",
        "",
        "This pass applies adjudicated grounding-review decisions back into the ontology-v2 overlay layer.",
        "",
        "Key rules used:",
        "- row-level reviews override cluster-level reviews",
        "- reviewed cluster-medoid decisions propagate to labels in reviewed clusters when no row review exists",
        "- unresolved raw labels are always preserved",
        "- broad or alias decisions require a resolvable existing ontology target; otherwise they fall back to new-family or unresolved",
        "",
        "## Final overlay action counts",
    ]
    for action, count in overlay_df["overlay_action"].value_counts().items():
        lines.append(f"- `{action}`: `{int(count):,}`")
    lines.extend(
        [
            "",
            "## Proposal counts",
        ]
    )
    for proposal, count in proposals_df["cluster_proposal"].value_counts().items():
        lines.append(f"- `{proposal}`: `{int(count):,}`")
    lines.extend(
        [
            "",
            "## Sensitivity snapshot",
        ]
    )
    for _, row in sensitivity_summary.iterrows():
        lines.append(
            f"- threshold `{row['threshold']:.2f}`: overlay labels `{int(row['overlay_labels_with_attachment']):,}`, "
            f"overlay occurrences `{int(row['overlay_occurrences_with_attachment']):,}`, "
            f"unique grounded concepts `{int(row['unique_grounded_concepts']):,}`"
        )
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PAPER_OUT_DIR.mkdir(parents=True, exist_ok=True)

    grounding_reviewed, overlay_df, clusters_reviewed_df, proposals_reviewed_df, summary_df, module = build_review_layers()

    grounding_reviewed.to_parquet(GROUNDING_REVIEWED_PATH, index=False)
    overlay_df.to_parquet(OVERLAY_REVIEWED_PATH, index=False)
    clusters_reviewed_df.to_parquet(CLUSTERS_REVIEWED_PATH, index=False)
    proposals_reviewed_df.to_parquet(PROPOSALS_REVIEWED_PATH, index=False)

    sensitivity_summary_df, benchmark_sensitivity_df = module.build_threshold_sensitivity(
        grounding_reviewed,
        overlay_df,
        module.parse_extractions(module.EXTRACTIONS_PATH)[1],
    )
    sensitivity_summary_df.to_csv(PAPER_OUT_DIR / "summary.csv", index=False)
    benchmark_sensitivity_df.to_csv(PAPER_OUT_DIR / "benchmark_sensitivity.csv", index=False)
    module.write_sensitivity_markdown(PAPER_OUT_DIR / "summary.md", sensitivity_summary_df)

    write_note(summary_df, sensitivity_summary_df, overlay_df, proposals_reviewed_df)

    print("Reviewed overlay artifacts written.")
    print(f"Grounding reviewed rows: {len(grounding_reviewed):,}")
    print(f"Overlay reviewed rows: {len(overlay_df):,}")
    print(f"Cluster summaries reviewed: {len(clusters_reviewed_df):,}")
    print(f"Proposal rows reviewed: {len(proposals_reviewed_df):,}")


if __name__ == "__main__":
    main()
