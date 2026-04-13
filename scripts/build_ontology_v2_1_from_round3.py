from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

BASE_ONTOLOGY_PATH = DATA_DIR / "ontology_v2_final.json"
ROUND3_OVERLAY_PATH = DATA_DIR / "ontology_enrichment_overlay_v2_reviewed_round3.parquet"
ROUND3_GROUNDING_PATH = DATA_DIR / "extraction_label_grounding_v2_reviewed_round3.parquet"
BASE_MAPPING_PATH = DATA_DIR / "extraction_label_mapping_v2.parquet"

PROMOTED_FAMILIES_PATH = DATA_DIR / "ontology_v2_1_promoted_families.parquet"
ONTOLOGY_V2_1_PATH = DATA_DIR / "ontology_v2_1.json"
MAPPING_V2_1_PATH = DATA_DIR / "extraction_label_mapping_v2_1.parquet"
NOTE_PATH = DATA_DIR / "ontology_v2_1_promotion_note.md"


def normalize_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower()).strip()


def titleish(label: str) -> int:
    text = str(label or "").strip()
    if not text:
        return 0
    return sum(1 for token in text.split() if token[:1].isupper())


def choose_display_label(values: pd.Series, weights: pd.Series) -> str:
    counter: Counter[str] = Counter()
    for value, weight in zip(values, weights):
        text = str(value or "").strip()
        if text:
            counter[text] += int(weight) if pd.notna(weight) else 1
    if not counter:
        return ""
    ranked = sorted(counter.items(), key=lambda item: (-item[1], -titleish(item[0]), item[0].lower()))
    return ranked[0][0]


def stable_family_id(label_norm: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label_norm).strip("-")[:48] or "family"
    digest = hashlib.sha1(label_norm.encode("utf-8")).hexdigest()[:10]
    return f"FGV21FAM:{slug}:{digest}"


def first_nonempty(series: pd.Series) -> str | None:
    for value in series:
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return None


def aggregate_family_rows(new_rows: pd.DataFrame, ontology_rows: list[dict[str, Any]]) -> pd.DataFrame:
    base_label_norms = {normalize_label(row.get("label")) for row in ontology_rows}
    grouped_rows: list[dict[str, Any]] = []

    for family_norm, group in new_rows.groupby("family_norm", sort=False):
        display_label = choose_display_label(group["family_display"], group["freq"])
        aliases = sorted({str(v).strip() for v in group["label"].tolist() + group["family_display"].tolist() if str(v).strip()})
        source_set = sorted({str(v) for v in group["decision_source"] if str(v).strip()})
        manual_flag = any("manual_override_review" in source for source in source_set)
        hard_modal_flag = any("remaining_hard_modal_review" in source for source in source_set)

        nonempty_domains = [str(v).strip() for v in group["onto_domain"] if pd.notna(v) and str(v).strip()]
        domain = Counter(nonempty_domains).most_common(1)[0][0] if nonempty_domains else "other_valid"

        parent_candidates: list[str] = []
        for col in ["proposed_onto_label_y", "dominant_onto_label", "alt_concept_label", "onto_label"]:
            if col in group.columns:
                parent_candidates.extend([str(v).strip() for v in group[col] if pd.notna(v) and str(v).strip()])
        parent_label = Counter(parent_candidates).most_common(1)[0][0] if parent_candidates else ""

        row_support = int(group["label"].nunique())
        freq_support = int(group["freq"].sum())
        unique_papers_support = int(group["unique_papers"].sum())
        max_impact = float(group["impact_score"].max())

        promote = (
            family_norm not in base_label_norms
            and (
                row_support >= 2
                or freq_support >= 50
                or manual_flag
                or hard_modal_flag
            )
        )

        grouped_rows.append(
            {
                "family_norm": family_norm,
                "family_label": display_label,
                "family_id": stable_family_id(family_norm),
                "row_support": row_support,
                "freq_support": freq_support,
                "unique_papers_support": unique_papers_support,
                "max_impact": max_impact,
                "source_count": len(source_set),
                "decision_sources_json": json.dumps(source_set, ensure_ascii=False),
                "aliases_json": json.dumps(aliases[:50], ensure_ascii=False),
                "domain": domain,
                "parent_label": parent_label,
                "description": (
                    "Reviewed synthetic concept family promoted from round-3 open-world grounding. "
                    f"Support: {row_support} labels, {freq_support} occurrences, {unique_papers_support} paper instances."
                ),
                "manual_flag": manual_flag,
                "hard_modal_flag": hard_modal_flag,
                "exists_exact_in_base_ontology": family_norm in base_label_norms,
                "promote_to_v2_1": bool(promote),
            }
        )

    families = pd.DataFrame(grouped_rows).sort_values(
        ["promote_to_v2_1", "freq_support", "row_support", "family_label"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    return families


def build_v2_1_ontology(base_rows: list[dict[str, Any]], promoted_families: pd.DataFrame) -> list[dict[str, Any]]:
    promoted_rows: list[dict[str, Any]] = []
    for row in promoted_families.itertuples(index=False):
        if not bool(row.promote_to_v2_1):
            continue
        promoted_rows.append(
            {
                "id": row.family_id,
                "label": row.family_label,
                "description": row.description,
                "source": "frontiergraph_v2_1_reviewed_family",
                "domain": row.domain or "other_valid",
                "parent_label": row.parent_label or "",
                "root_label": row.parent_label or "",
                "_sources": [
                    {
                        "source": "frontiergraph_v2_1_reviewed_family",
                        "id": row.family_id,
                        "label": row.family_label,
                    }
                ],
            }
        )
    out = list(base_rows) + promoted_rows
    return out


def build_mapping_v2_1(
    base_mapping: pd.DataFrame,
    grounding_round3: pd.DataFrame,
    promoted_families: pd.DataFrame,
    ontology_rows_v2_1: list[dict[str, Any]],
) -> pd.DataFrame:
    onto_lookup = {
        str(row["id"]): {
            "label": str(row["label"]),
            "source": str(row.get("source", "")),
            "domain": str(row.get("domain", "")),
        }
        for row in ontology_rows_v2_1
    }
    promoted_lookup = {
        str(row.family_norm): {
            "family_id": str(row.family_id),
            "family_label": str(row.family_label),
            "source": "frontiergraph_v2_1_reviewed_family",
            "domain": str(row.domain or "other_valid"),
            "promote_to_v2_1": bool(row.promote_to_v2_1),
        }
        for row in promoted_families.itertuples(index=False)
    }

    overlay_cols = [
        "label",
        "overlay_action",
        "final_decision",
        "decision_source",
        "proposed_onto_id_y",
        "proposed_onto_label_y",
        "proposed_new_concept_family_label",
        "score_band",
        "issue_type",
    ]
    overlay = grounding_round3[overlay_cols].copy()
    merged = base_mapping.merge(overlay, on="label", how="left")
    merged["family_norm"] = merged["proposed_new_concept_family_label"].map(normalize_label)

    merged["v2_1_mapping_action"] = "carry_forward_base_mapping"
    merged["original_onto_id"] = merged["onto_id"]
    merged["original_onto_label"] = merged["onto_label"]
    merged["original_score"] = merged["score"]

    existing_mask = merged["overlay_action"].isin(["attach_existing_broad", "add_alias_to_existing"]) & merged["proposed_onto_id_y"].notna()
    if existing_mask.any():
        target_ids = merged.loc[existing_mask, "proposed_onto_id_y"].astype(str)
        merged.loc[existing_mask, "onto_id"] = target_ids.values
        merged.loc[existing_mask, "onto_label"] = target_ids.map(lambda x: onto_lookup.get(x, {}).get("label", "")).values
        merged.loc[existing_mask, "onto_source"] = target_ids.map(lambda x: onto_lookup.get(x, {}).get("source", "")).values
        merged.loc[existing_mask, "onto_domain"] = target_ids.map(lambda x: onto_lookup.get(x, {}).get("domain", "")).values
        merged.loc[existing_mask, "matched_via"] = merged.loc[existing_mask, "decision_source"].astype(str).values
        merged.loc[existing_mask, "match_kind"] = merged.loc[existing_mask, "overlay_action"].map(
            {
                "attach_existing_broad": "reviewed_existing_broad",
                "add_alias_to_existing": "reviewed_existing_alias",
            }
        ).values
        merged.loc[existing_mask, "v2_1_mapping_action"] = merged.loc[existing_mask, "overlay_action"].values

    promoted_mask = merged["overlay_action"].eq("propose_new_concept_family") & merged["family_norm"].map(
        lambda x: promoted_lookup.get(x, {}).get("promote_to_v2_1", False)
    ).fillna(False)
    if promoted_mask.any():
        family_norms = merged.loc[promoted_mask, "family_norm"].astype(str)
        merged.loc[promoted_mask, "onto_id"] = family_norms.map(lambda x: promoted_lookup[x]["family_id"]).values
        merged.loc[promoted_mask, "onto_label"] = family_norms.map(lambda x: promoted_lookup[x]["family_label"]).values
        merged.loc[promoted_mask, "onto_source"] = family_norms.map(lambda x: promoted_lookup[x]["source"]).values
        merged.loc[promoted_mask, "onto_domain"] = family_norms.map(lambda x: promoted_lookup[x]["domain"]).values
        merged.loc[promoted_mask, "matched_via"] = merged.loc[promoted_mask, "decision_source"].astype(str).values
        merged.loc[promoted_mask, "match_kind"] = "reviewed_promoted_family"
        merged.loc[promoted_mask, "score"] = np.maximum(merged.loc[promoted_mask, "score"].fillna(0.0).astype(float), 0.95)
        merged.loc[promoted_mask, "v2_1_mapping_action"] = "promoted_family"

    unresolved_mask = merged["overlay_action"].isin(["keep_unresolved", "reject_cluster"])
    if unresolved_mask.any():
        for col in ["onto_id", "onto_label", "onto_source", "onto_domain"]:
            merged.loc[unresolved_mask, col] = None
        merged.loc[unresolved_mask, "score"] = np.nan
        merged.loc[unresolved_mask, "matched_via"] = merged.loc[unresolved_mask, "decision_source"].astype(str).values
        merged.loc[unresolved_mask, "match_kind"] = merged.loc[unresolved_mask, "overlay_action"].map(
            {
                "keep_unresolved": "reviewed_keep_unresolved",
                "reject_cluster": "reviewed_reject",
            }
        ).values
        merged.loc[unresolved_mask, "v2_1_mapping_action"] = merged.loc[unresolved_mask, "overlay_action"].values

    unpromoted_family_mask = merged["overlay_action"].eq("propose_new_concept_family") & ~promoted_mask
    if unpromoted_family_mask.any():
        for col in ["onto_id", "onto_label", "onto_source", "onto_domain"]:
            merged.loc[unpromoted_family_mask, col] = None
        merged.loc[unpromoted_family_mask, "score"] = np.nan
        merged.loc[unpromoted_family_mask, "matched_via"] = merged.loc[unpromoted_family_mask, "decision_source"].astype(str).values
        merged.loc[unpromoted_family_mask, "match_kind"] = "reviewed_unpromoted_family"
        merged.loc[unpromoted_family_mask, "v2_1_mapping_action"] = "unpromoted_family"

    return merged.drop(columns=["family_norm"])


def write_note(
    base_ontology_rows: list[dict[str, Any]],
    promoted_families: pd.DataFrame,
    ontology_v2_1_rows: list[dict[str, Any]],
    mapping_v2_1: pd.DataFrame,
) -> None:
    promoted_only = promoted_families[promoted_families["promote_to_v2_1"]].copy()
    lines = [
        "# Ontology v2.1 Promotion Note",
        "",
        "This pass promotes a conservative subset of reviewed round-3 new-family proposals into ontology v2.1.",
        "",
        "Promotion rule:",
        "- start from `propose_new_concept_family` rows in the round-3 reviewed overlay",
        "- collapse by normalized family label",
        "- exclude exact label overlaps already present in base ontology v2",
        "- promote only families with either `row_support >= 2`, `freq_support >= 50`, or an explicit hard-case/manual reviewed source",
        "",
        f"- base ontology size: `{len(base_ontology_rows):,}`",
        f"- promoted family candidates considered: `{len(promoted_families):,}`",
        f"- promoted family nodes added: `{len(promoted_only):,}`",
        f"- ontology v2.1 size: `{len(ontology_v2_1_rows):,}`",
        "",
        "## Mapping actions in v2.1",
    ]
    for action, count in mapping_v2_1["v2_1_mapping_action"].fillna("missing").value_counts().items():
        lines.append(f"- `{action}`: `{int(count):,}`")
    lines.extend(["", "## Top promoted families"])
    for row in promoted_only.sort_values(["freq_support", "row_support"], ascending=[False, False]).head(40).itertuples(index=False):
        lines.append(
            f"- `{row.family_label}`: row_support={int(row.row_support)}, freq_support={int(row.freq_support)}, "
            f"domain=`{row.domain}`, sources=`{row.decision_sources_json}`"
        )
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    base_ontology_rows = json.loads(BASE_ONTOLOGY_PATH.read_text(encoding="utf-8"))
    overlay = pd.read_parquet(ROUND3_OVERLAY_PATH)
    grounding = pd.read_parquet(ROUND3_GROUNDING_PATH)
    base_mapping = pd.read_parquet(BASE_MAPPING_PATH)

    new_rows = overlay[overlay["overlay_action"] == "propose_new_concept_family"].copy()
    new_rows = new_rows.merge(
        grounding[
            [
                "label",
                "onto_domain",
                "onto_label",
                "dominant_onto_label",
                "alt_concept_label",
                "proposed_onto_label_y",
            ]
        ],
        on=["label"],
        how="left",
    )
    new_rows["family_display"] = new_rows["proposed_new_concept_family_label"].astype(str).str.strip()
    new_rows["family_norm"] = new_rows["family_display"].map(normalize_label)
    new_rows = new_rows[new_rows["family_norm"] != ""].copy()

    promoted_families = aggregate_family_rows(new_rows, base_ontology_rows)
    ontology_v2_1_rows = build_v2_1_ontology(base_ontology_rows, promoted_families)
    mapping_v2_1 = build_mapping_v2_1(base_mapping, grounding, promoted_families, ontology_v2_1_rows)

    promoted_families.to_parquet(PROMOTED_FAMILIES_PATH, index=False)
    ONTOLOGY_V2_1_PATH.write_text(json.dumps(ontology_v2_1_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mapping_v2_1.to_parquet(MAPPING_V2_1_PATH, index=False)
    write_note(base_ontology_rows, promoted_families, ontology_v2_1_rows, mapping_v2_1)

    print(f"Promoted family candidates: {len(promoted_families):,}")
    print(f"Promoted into v2.1: {int(promoted_families['promote_to_v2_1'].sum()):,}")
    print(f"Ontology v2.1 size: {len(ontology_v2_1_rows):,}")
    print(f"Wrote mapping v2.1 rows: {len(mapping_v2_1):,}")


if __name__ == "__main__":
    main()
