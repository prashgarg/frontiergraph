from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ENRICHED_SHORTLIST = "outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.csv"
DEFAULT_OUT_DIR = "outputs/paper/28_vnext_frontier_question_prototypes"
DEFAULT_FINDINGS = "next_steps/vnext_frontier_question_prototype_findings.md"
DEFAULT_CONCEPT_FAMILIES = "data/processed/ontology_vnext_proto_v1/concept_families.parquet"
DEFAULT_FAMILY_RELATIONS = "data/processed/ontology_vnext_proto_v1/family_relation_table.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic frontier question prototypes from the ontology vNext enriched shortlist.")
    parser.add_argument("--enriched-shortlist", default=DEFAULT_ENRICHED_SHORTLIST, dest="enriched_shortlist")
    parser.add_argument("--concept-families", default=DEFAULT_CONCEPT_FAMILIES, dest="concept_families")
    parser.add_argument("--family-relations", default=DEFAULT_FAMILY_RELATIONS, dest="family_relations")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, dest="out_dir")
    parser.add_argument("--findings-note", default=DEFAULT_FINDINGS, dest="findings_note")
    return parser.parse_args()


def _json_items(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if isinstance(parsed, list):
        out: list[str] = []
        for item in parsed:
            if isinstance(item, dict):
                val = str(item.get("value", "")).strip()
                if val:
                    out.append(val)
            else:
                val = str(item).strip()
                if val:
                    out.append(val)
        return out
    if isinstance(parsed, dict):
        val = str(parsed.get("value", "")).strip()
        return [val] if val else []
    return []


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _top_n_items(value: Any, n: int = 3) -> list[str]:
    return _dedupe_keep_order(_json_items(value))[:n]


def _list_phrase(items: list[str], default: str = "the current evidence base") -> str:
    items = [str(item).strip() for item in items if str(item).strip()]
    if not items:
        return default
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _clean_design(design: Any) -> str:
    text = str(design or "").strip()
    mapping = {
        "theory_or_model": "theory or model work",
        "descriptive_observational": "descriptive observational work",
        "time_series_econometrics": "time-series econometric work",
        "panel_FE_or_TWFE": "panel fixed-effects work",
        "DiD": "difference-in-differences work",
        "event_study": "event-study work",
        "IV": "instrumental-variables work",
        "RDD": "regression-discontinuity work",
        "experiment": "experimental work",
        "qualitative_or_case_study": "qualitative or case-study work",
        "prediction_or_forecasting": "prediction or forecasting work",
        "structural_model": "structural modeling work",
        "simulation": "simulation work",
        "do_not_know": "unclear evidence",
        "other": "other evidence",
    }
    return mapping.get(text, text.replace("_", " ") if text else "unclear evidence")


def _next_evidence_step(design: Any) -> str:
    design = str(design or "").strip()
    mapping = {
        "descriptive_observational": "quasi-experimental or panel-based follow-up",
        "time_series_econometrics": "panel, IV, or quasi-experimental follow-up",
        "panel_FE_or_TWFE": "stronger identification or mechanism-focused follow-up",
        "DiD": "alternative identification or external-validity follow-up",
        "event_study": "alternative identification or mechanism follow-up",
        "IV": "replication in new settings or mechanism evidence",
        "RDD": "replication in other settings or mechanism evidence",
        "experiment": "external-validity or context-transfer follow-up",
        "prediction_or_forecasting": "causal follow-up rather than another forecasting exercise",
        "qualitative_or_case_study": "broader quantitative follow-up",
        "theory_or_model": "credible empirical follow-up",
        "structural_model": "reduced-form or quasi-experimental follow-up",
        "simulation": "empirical validation or field evidence",
    }
    return mapping.get(design, "complementary follow-up evidence")


def _base_priority(row: pd.Series) -> float:
    horizon_penalty = 0.0 if int(row["horizon"]) == 5 else 0.5
    return float(row["shortlist_rank"]) + horizon_penalty


def _family_member_lookup(concept_families_df: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    if concept_families_df.empty:
        return out
    for family_id, sub in concept_families_df.groupby("family_id"):
        out[str(family_id)] = (
            sub[["member_concept_id", "member_label"]]
            .drop_duplicates()
            .sort_values(["member_label", "member_concept_id"])
            .to_dict(orient="records")
        )
    return out


def _family_relation_lookup(family_relations_df: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    out: dict[tuple[str, str, str], float] = {}
    if family_relations_df.empty:
        return out
    for row in family_relations_df.itertuples(index=False):
        family_id = str(getattr(row, "proposed_family_id", "") or "")
        left = str(getattr(row, "left_concept_id", "") or "")
        right = str(getattr(row, "right_concept_id", "") or "")
        key = tuple(sorted((left, right)))
        lookup_key = (family_id, key[0], key[1])
        out[lookup_key] = max(float(getattr(row, "relation_confidence", 0.0) or 0.0), out.get(lookup_key, 0.0))
    return out


def _family_usage_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = (
        pd.concat([df["source_concept_id"], df["target_concept_id"]], ignore_index=True)
        .astype(str)
        .value_counts()
        .to_dict()
    )
    return {str(key): int(val) for key, val in counts.items()}


def _family_pair_collision_counts(df: pd.DataFrame) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for row in df[["source_concept_id", "target_concept_id"]].itertuples(index=False):
        left = str(row.source_concept_id)
        right = str(row.target_concept_id)
        key = tuple(sorted((left, right)))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _relation_confidence(
    family_id: str,
    left_id: str,
    right_id: str,
    relation_lookup: dict[tuple[str, str, str], float],
) -> float:
    key = tuple(sorted((str(left_id), str(right_id))))
    return float(relation_lookup.get((str(family_id), key[0], key[1]), 0.0))


def _comparator_phrase(items: list[str]) -> str:
    if not items:
        return "adjacent sibling concepts"
    if len(items) == 1:
        return items[0]
    return _list_phrase(items)


def _build_family_aware(
    df: pd.DataFrame,
    concept_families_df: pd.DataFrame,
    family_relations_df: pd.DataFrame,
) -> pd.DataFrame:
    mask = (
        df["source_family_id"].astype(str).eq(df["target_family_id"].astype(str))
        & ~df["source_family_id"].astype(str).str.startswith("self_family__")
        & df["source_concept_id"].astype(str).ne(df["target_concept_id"].astype(str))
    )
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    family_members = _family_member_lookup(concept_families_df)
    relation_lookup = _family_relation_lookup(family_relations_df)
    usage_counts = _family_usage_counts(df)
    pair_collision_counts = _family_pair_collision_counts(df)

    def sibling_labels(row: pd.Series) -> list[str]:
        family_id = str(row["source_family_id"])
        source_id = str(row["source_concept_id"])
        target_id = str(row["target_concept_id"])
        candidates = []
        for member in family_members.get(family_id, []):
            member_id = str(member["member_concept_id"])
            if member_id in {source_id, target_id}:
                continue
            confidence = max(
                _relation_confidence(family_id, source_id, member_id, relation_lookup),
                _relation_confidence(family_id, target_id, member_id, relation_lookup),
            )
            pair_collision_count = (
                int(pair_collision_counts.get(tuple(sorted((source_id, member_id))), 0))
                + int(pair_collision_counts.get(tuple(sorted((target_id, member_id))), 0))
            )
            candidates.append(
                (
                    confidence,
                    pair_collision_count,
                    int(usage_counts.get(member_id, 0)),
                    str(member["member_label"]),
                )
            )
        if any(item[1] > 0 for item in candidates):
            candidates = [item for item in candidates if item[1] > 0]
        candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
        return [label for _, _, _, label in candidates[:2]]

    sub["family_comparator_labels"] = sub.apply(sibling_labels, axis=1)
    sub["family_comparator_phrase"] = sub["family_comparator_labels"].map(_comparator_phrase)
    sub["family_comparator_count"] = sub["family_comparator_labels"].map(len)
    sub["prototype_family"] = "family_aware"
    sub["prototype_title"] = sub.apply(
        lambda row: (
            f"Within the {row['source_family_label']} family, is the {row['source_label']} -> {row['target_label']} link more specific than sibling links involving {row['family_comparator_phrase']}?"
            if int(row["family_comparator_count"]) > 0
            else f"Within the {row['source_family_label']} family, what is specific to the {row['source_label']} -> {row['target_label']} link?"
        ),
        axis=1,
    )
    sub["prototype_why"] = sub.apply(
        lambda row: (
            f"{row['source_label']} and {row['target_label']} sit in the same broader family but remain separate canonical concepts. "
            f"The open question is whether this pair stands out relative to sibling concepts such as {row['family_comparator_phrase']}, rather than reflecting a diffuse family-level association."
            if int(row["family_comparator_count"]) > 0
            else (
                f"{row['source_label']} and {row['target_label']} sit in the same broader family but remain separate canonical concepts. "
                "The frontier is whether the family-level pattern runs through this specific pair rather than only through adjacent sibling outcomes."
            )
        ),
        axis=1,
    )
    sub["prototype_first_step"] = sub.apply(
        lambda row: (
            f"Compare support for this pair against sibling links involving {row['family_comparator_phrase']} before treating the family as one broad family-level relation."
            if int(row["family_comparator_count"]) > 0
            else "Compare this pair against adjacent family members before collapsing the whole family into one broad outcome."
        ),
        axis=1,
    )
    sub["prototype_trigger_reason"] = "same_nonself_family"
    sub["prototype_priority_score"] = sub.apply(_base_priority, axis=1)
    return sub.sort_values(["prototype_priority_score", "shortlist_rank"]).head(25).reset_index(drop=True)


def _build_context_transfer(df: pd.DataFrame) -> pd.DataFrame:
    edge_geos = df["dominant_countries_json"].map(lambda v: _top_n_items(v, 3))
    source_geos = df["source_top_geographies_json"].map(lambda v: _top_n_items(v, 3))
    target_geos = df["target_top_geographies_json"].map(lambda v: _top_n_items(v, 3))

    def qualifies(i: int) -> bool:
        edge = edge_geos.iloc[i]
        if not edge:
            return False
        endpoint_union = _dedupe_keep_order(source_geos.iloc[i] + target_geos.iloc[i])
        if not endpoint_union:
            return False
        return any(geo not in edge for geo in endpoint_union)

    mask = pd.Series([qualifies(i) for i in range(len(df))], index=df.index)
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    sub["prototype_family"] = "context_transfer"

    def make_title(row: pd.Series) -> str:
        edge = _list_phrase(_top_n_items(row["dominant_countries_json"], 2), default="its currently studied settings")
        return f"Where should we test the {row['source_label']} -> {row['target_label']} relation beyond {edge}?"

    def make_why(row: pd.Series) -> str:
        edge = _list_phrase(_top_n_items(row["dominant_countries_json"], 2), default="the currently observed settings")
        source = _list_phrase(_top_n_items(row["source_top_geographies_json"], 2), default=row["source_label"])
        target = _list_phrase(_top_n_items(row["target_top_geographies_json"], 2), default=row["target_label"])
        return (
            f"Current pair-level evidence is concentrated in {edge}, while the endpoint concepts themselves appear in settings such as "
            f"{source} and {target}. The open question is whether the relation transfers across contexts rather than remaining local to its current evidence base."
        )

    sub["prototype_title"] = sub.apply(make_title, axis=1)
    sub["prototype_why"] = sub.apply(make_why, axis=1)
    sub["prototype_first_step"] = (
        "Look for a geography or unit of analysis where both endpoints already appear but the pair evidence is still thin."
    )
    sub["prototype_trigger_reason"] = "edge_context_narrower_than_endpoint_contexts"
    sub["prototype_priority_score"] = sub.apply(_base_priority, axis=1)
    return sub.sort_values(["prototype_priority_score", "shortlist_rank"]).head(25).reset_index(drop=True)


def _build_missing_empirical_confirmation(df: pd.DataFrame) -> pd.DataFrame:
    theory_designs = {"theory_or_model", "structural_model", "simulation"}
    mask = (
        df["edge_evidence_mode"].astype(str).isin(["theory", "mixed"])
        | df["edge_design_family"].astype(str).isin(theory_designs)
    )
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    sub["prototype_family"] = "missing_empirical_confirmation"
    sub["prototype_title"] = sub.apply(
        lambda row: f"What empirical test would best check the {row['source_label']} -> {row['target_label']} relation?",
        axis=1,
    )
    sub["prototype_why"] = sub.apply(
        lambda row: (
            f"Current support is mostly {_clean_design(row['edge_design_family'])}. "
            "The frontier may not be another conceptual link, but a credible empirical test of whether the relation appears in data."
        ),
        axis=1,
    )
    sub["prototype_first_step"] = (
        "Start from settings where both endpoints already appear and identify the strongest feasible empirical design."
    )
    sub["prototype_trigger_reason"] = "theory_heavy_or_model_heavy_edge_profile"
    sub["prototype_priority_score"] = sub.apply(_base_priority, axis=1)
    return sub.sort_values(["prototype_priority_score", "shortlist_rank"]).head(25).reset_index(drop=True)


def _build_evidence_type_expansion(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["edge_evidence_mode"].astype(str).eq("empirics")
    sub = df.loc[mask].copy()
    if sub.empty:
        return sub
    sub["prototype_family"] = "evidence_type_expansion"
    sub["prototype_title"] = sub.apply(
        lambda row: f"What complementary evidence would most strengthen the {row['source_label']} -> {row['target_label']} relation?",
        axis=1,
    )
    sub["prototype_why"] = sub.apply(
        lambda row: (
            f"Current support is dominated by {_clean_design(row['edge_design_family'])}. "
            f"The next frontier may be a {_next_evidence_step(row['edge_design_family'])}, rather than another study with the same design profile."
        ),
        axis=1,
    )
    sub["prototype_first_step"] = (
        "Look for a follow-up design that complements the current evidence base rather than simply repeating it."
    )
    sub["prototype_trigger_reason"] = "empirical_edge_profile_with_single_dominant_design"
    sub["prototype_priority_score"] = sub.apply(_base_priority, axis=1)
    return sub.sort_values(["prototype_priority_score", "shortlist_rank"]).head(25).reset_index(drop=True)


def _prototype_columns(df: pd.DataFrame) -> list[str]:
    preferred = [
        "prototype_family",
        "prototype_title",
        "prototype_why",
        "prototype_first_step",
        "prototype_trigger_reason",
        "prototype_priority_score",
        "horizon",
        "shortlist_rank",
        "pair_key",
        "display_title",
        "display_why",
        "source_label",
        "target_label",
        "source_family_label",
        "target_family_label",
        "source_primary_concept_type",
        "target_primary_concept_type",
        "family_comparator_phrase",
        "edge_evidence_mode",
        "edge_design_family",
        "edge_join_method",
        "source_top_geographies_json",
        "target_top_geographies_json",
        "dominant_countries_json",
        "dominant_units_json",
        "top_mediators_json",
    ]
    return [col for col in preferred if col in df.columns]


def _collapse_review_duplicates(sub: pd.DataFrame) -> pd.DataFrame:
    if sub.empty or "pair_key" not in sub.columns:
        return sub
    ordered = sub.sort_values(["prototype_priority_score", "shortlist_rank", "horizon"]).copy()
    return ordered.drop_duplicates(subset=["pair_key"], keep="first").reset_index(drop=True)


def _write_markdown(all_df: pd.DataFrame, summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# vNext Frontier Question Prototypes",
        "",
        "These are read-only deterministic question prototypes layered on top of the active shortlist.",
        "They do not change ranking; they reinterpret the current frontier using family, context, and edge-evidence structure.",
        "",
        "## Prototype counts",
        "",
    ]
    for family_name, stats in summary["families"].items():
        lines.append(f"- `{family_name}`: `{stats['count']}` rows, `{stats['unique_pairs']}` unique pairs")

    def add_family_section(family_name: str, sub: pd.DataFrame) -> None:
        lines.extend(["", f"## {family_name}", ""])
        if sub.empty:
            lines.append("- none")
            return
        review_sub = _collapse_review_duplicates(sub)
        for row in review_sub.sort_values(["prototype_priority_score", "shortlist_rank"]).head(10).itertuples(index=False):
            lines.append(
                f"- `h={int(row.horizon)}` `#{int(row.shortlist_rank)}` {row.prototype_title}  \n"
                f"  Trigger: `{row.prototype_trigger_reason}`  \n"
                f"  Why: {row.prototype_why}  \n"
                f"  First step: {row.prototype_first_step}  \n"
                f"  Baseline: {row.display_title}"
            )

    for family_name in [
        "family_aware",
        "context_transfer",
        "missing_empirical_confirmation",
        "evidence_type_expansion",
    ]:
        add_family_section(family_name, all_df[all_df["prototype_family"] == family_name].copy())

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_findings(all_df: pd.DataFrame, summary: dict[str, Any], out_path: Path) -> None:
    counts = summary["families"]
    lines = [
        "# vNext Frontier Question Prototype Findings",
        "",
        "## What was built",
        "",
        "We generated four deterministic frontier question families on top of the enriched shortlist:",
        "",
        "- family-aware questions",
        "- context-transfer questions",
        "- missing empirical confirmation questions",
        "- evidence-type expansion questions",
        "",
        "These are interpretive overlays only. They do not rerank the active frontier.",
        "",
        "## Prototype coverage",
        "",
    ]
    for family_name, stats in counts.items():
        lines.append(f"- `{family_name}` rows: `{stats['count']}`")

    strongest = []
    if counts["context_transfer"]["count"] > 0:
        strongest.append("context-transfer questions")
    if counts["missing_empirical_confirmation"]["count"] > 0:
        strongest.append("missing empirical confirmation questions")
    if counts["evidence_type_expansion"]["count"] > 0:
        strongest.append("evidence-type expansion questions")
    if counts["family_aware"]["count"] > 0:
        strongest.append("family-aware questions")

    lines.extend(
        [
            "",
            "## First read",
            "",
            "The layered overlay is already rich enough to support new frontier objects.",
            "",
            "Most promising prototype families on first pass:",
            "- context-transfer questions look strongest as a direct use of node context",
            "- evidence-type expansion questions look strongest as a direct use of edge evidence",
            "- missing empirical confirmation questions also look good, especially for theory-heavy macro/public-finance style links",
            "- family-aware questions are more credible once reviewed families go beyond the environmental family, but they still depend heavily on comparator phrasing",
            "",
            "What looks most useful conceptually:",
            "- family-aware questions help when related outcomes should stay separate but clearly belong together",
            "- context-transfer questions turn context metadata into a substantive frontier object",
            "- missing empirical confirmation questions make theory-heavy links legible as empirical opportunities",
            "- evidence-type expansion questions make the edge-evidence layer matter, not just the node layer",
            "",
            "## Practical next step",
            "",
            "The next step should be a review pass over these prototypes to decide which of the four families belong in the paper and which should remain internal tools.",
            "If one or two families look clearly stronger, we can then build a second-generation prototype that scores those objects directly rather than only deriving them from the existing shortlist.",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    findings_path = Path(args.findings_note)
    findings_path.parent.mkdir(parents=True, exist_ok=True)

    enriched = pd.read_csv(args.enriched_shortlist)
    concept_families = pd.read_parquet(args.concept_families)
    family_relations = pd.read_parquet(args.family_relations)

    families = [
        _build_family_aware(enriched, concept_families, family_relations),
        _build_context_transfer(enriched),
        _build_missing_empirical_confirmation(enriched),
        _build_evidence_type_expansion(enriched),
    ]
    all_proto = pd.concat([df for df in families if not df.empty], ignore_index=True)
    all_proto = all_proto[_prototype_columns(all_proto)].copy()

    summary = {
        "enriched_shortlist_rows": int(len(enriched)),
        "prototype_rows": int(len(all_proto)),
        "families": {
            family_name: {
                "count": int((all_proto["prototype_family"] == family_name).sum()) if not all_proto.empty else 0,
                "unique_pairs": int(all_proto.loc[all_proto["prototype_family"] == family_name, "pair_key"].nunique()) if not all_proto.empty else 0,
            }
            for family_name in [
                "family_aware",
                "context_transfer",
                "missing_empirical_confirmation",
                "evidence_type_expansion",
            ]
        },
    }

    all_proto.to_csv(out_dir / "frontier_question_prototypes.csv", index=False)
    (out_dir / "prototype_family_counts.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(all_proto, summary, out_dir / "frontier_question_prototypes.md")
    _write_findings(all_proto, summary, findings_path)
    print(f"Wrote frontier question prototypes to {out_dir}")
    print(f"Wrote findings note to {findings_path}")


if __name__ == "__main__":
    main()
