"""Apply the reviewed parent-child relation layer to ontology v2.2 conservatively.

This script does not overwrite the original hierarchy fields destructively.
Instead it builds:
- selected reviewed parent edges
- ambiguity / duplicate / too-broad / cleanup audit tables
- an enriched ontology JSON with effective_* hierarchy fields

The original `parent_label` / `root_label` are preserved for provenance.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

ONTOLOGY_PATH = DATA_DIR / "ontology_v2_2_guardrailed.json"
REVIEWS_PATH = DATA_DIR / "parent_child_relation_review_results_v2_2_all_mini_low.parquet"

SELECTED_EDGES_PATH = DATA_DIR / "parent_child_reviewed_selected_edges_v2_2.parquet"
AMBIGUOUS_PATH = DATA_DIR / "parent_child_reviewed_ambiguous_candidates_v2_2.parquet"
DUPLICATE_PATH = DATA_DIR / "parent_child_reviewed_duplicate_candidates_v2_2.parquet"
TOO_BROAD_PATH = DATA_DIR / "parent_child_reviewed_too_broad_candidates_v2_2.parquet"
CLEANUP_PATH = DATA_DIR / "parent_child_reviewed_cleanup_candidates_v2_2.parquet"
ONTOLOGY_ENRICHED_PATH = DATA_DIR / "ontology_v2_2_hierarchy_enriched.json"
SUMMARY_PATH = DATA_DIR / "parent_child_reviewed_application_v2_2.md"


CONFIDENCE_SCORE = {"high": 3, "medium": 2, "low": 1}

# More-specific channels outrank broader field / fallback channels.
CHANNEL_SPECIFICITY = {
    "lexical_ngram_parent": 60,
    "existing_parent_label": 50,
    "openalex_topic_subfield": 45,
    "semantic_broader_neighbor": 35,
    "jel_code_hierarchy": 30,
    "openalex_topic_field": 20,
}


def norm_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def safe_int(value: Any) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0
    return int(value)


def safe_float(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return float(value)


def load_ontology() -> list[dict[str, Any]]:
    return json.loads(ONTOLOGY_PATH.read_text())


def load_reviews() -> pd.DataFrame:
    df = pd.read_parquet(REVIEWS_PATH).copy()
    df["child_norm"] = df["child_label"].map(norm_text)
    df["parent_norm"] = df["candidate_parent_label"].map(norm_text)
    df["confidence_score"] = df["confidence"].map(CONFIDENCE_SCORE).fillna(0).astype(int)
    df["channel_specificity"] = (
        df["candidate_channel"].map(CHANNEL_SPECIFICITY).fillna(0).astype(int)
    )
    df["parent_token_count"] = df["parent_token_count"].fillna(0).astype(int)
    df["shared_token_count"] = df["shared_token_count"].fillna(0).astype(int)
    df["lexical_parent_score"] = df["lexical_parent_score"].map(safe_float)
    df["semantic_cosine"] = df["semantic_cosine"].map(safe_float)
    return df


def collapse_duplicate_parents(valid: pd.DataFrame) -> pd.DataFrame:
    sort_cols = [
        "confidence_score",
        "channel_specificity",
        "parent_token_count",
        "shared_token_count",
        "lexical_parent_score",
        "semantic_cosine",
        "candidate_parent_label",
    ]
    ascending = [False, False, False, False, False, False, True]
    collapsed = (
        valid.sort_values(sort_cols, ascending=ascending)
        .groupby(["child_id", "parent_norm"], as_index=False)
        .first()
    )
    return collapsed


def is_directionally_reversed(row: pd.Series) -> bool:
    child = str(row.get("child_norm", "") or "").strip()
    parent = str(row.get("parent_norm", "") or "").strip()
    if not child or not parent or child == parent:
        return False
    return child in parent and parent not in child


def choose_selected_edges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid = df[(df["decision"] == "valid_parent") & (df["confidence"] == "high")].copy()
    valid = valid[valid["child_id"] != valid["candidate_parent_id"]].copy()
    valid = valid[valid["parent_norm"] != valid["child_norm"]].copy()
    # Guard against directionally reversed edges where the proposed parent is
    # just a more specific lexical expansion of the child.
    valid = valid[~valid.apply(is_directionally_reversed, axis=1)].copy()
    valid = collapse_duplicate_parents(valid)

    sort_cols = [
        "child_id",
        "confidence_score",
        "channel_specificity",
        "parent_token_count",
        "shared_token_count",
        "lexical_parent_score",
        "semantic_cosine",
        "candidate_parent_label",
    ]
    ascending = [True, False, False, False, False, False, False, True]
    valid = valid.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)

    selected_rows: list[dict[str, Any]] = []
    ambiguous_rows: list[dict[str, Any]] = []

    for child_id, sub in valid.groupby("child_id", sort=False):
        records = sub.to_dict(orient="records")
        best = records[0]
        if len(records) == 1:
            best["selection_status"] = "accepted_unique"
            selected_rows.append(best)
            continue

        second = records[1]
        best_signature = (
            best["confidence_score"],
            best["channel_specificity"],
            best["parent_token_count"],
            best["shared_token_count"],
            round(best["lexical_parent_score"], 6),
            round(best["semantic_cosine"], 6),
        )
        second_signature = (
            second["confidence_score"],
            second["channel_specificity"],
            second["parent_token_count"],
            second["shared_token_count"],
            round(second["lexical_parent_score"], 6),
            round(second["semantic_cosine"], 6),
        )
        if best_signature == second_signature:
            for rank, row in enumerate(records[:5], start=1):
                row["selection_status"] = "ambiguous_tied_best"
                row["candidate_rank_within_child"] = rank
                ambiguous_rows.append(row)
            continue

        best["selection_status"] = "accepted_best"
        best["runner_up_parent_label"] = second["candidate_parent_label"]
        best["runner_up_channel"] = second["candidate_channel"]
        selected_rows.append(best)

    selected = pd.DataFrame(selected_rows)
    ambiguous = pd.DataFrame(ambiguous_rows)
    return selected, ambiguous


def build_cleanup_tables(df: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_children = set(selected["child_id"].tolist()) if not selected.empty else set()

    duplicate = df[
        (df["decision"] == "alias_or_duplicate") & (df["confidence"].isin(["high", "medium"]))
    ].copy()

    too_broad = df[
        (df["decision"] == "plausible_but_too_broad") & (df["confidence"].isin(["high", "medium"]))
    ].copy()

    cleanup = df[
        (df["review_tier"] == "existing_parent_cleanup")
        & (df["decision"].isin(["invalid", "context_not_parent", "sibling_or_related"]))
        & (df["confidence"] == "high")
    ].copy()
    cleanup["has_selected_replacement"] = cleanup["child_id"].isin(selected_children)
    return duplicate, too_broad, cleanup


def resolve_existing_parent_id(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    by_norm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_norm[norm_text(row["label"])].append(row)

    resolved: dict[str, str | None] = {}
    for row in rows:
        parent_label = str(row.get("parent_label", "") or "").strip()
        if not parent_label:
            resolved[row["id"]] = None
            continue
        matches = by_norm.get(norm_text(parent_label), [])
        if len(matches) == 1:
            resolved[row["id"]] = matches[0]["id"]
        else:
            resolved[row["id"]] = None
    return resolved


def build_enriched_ontology(
    rows: list[dict[str, Any]],
    selected: pd.DataFrame,
    cleanup: pd.DataFrame,
) -> list[dict[str, Any]]:
    id_to_row = {row["id"]: dict(row) for row in rows}
    legacy_parent_id = resolve_existing_parent_id(rows)

    selected_map = {
        row["child_id"]: row
        for row in selected.to_dict(orient="records")
    }
    cleanup_clear_ids = set(
        cleanup.loc[~cleanup["has_selected_replacement"], "child_id"].astype(str).tolist()
    )

    effective_parent_id: dict[str, str | None] = {}
    effective_parent_label: dict[str, str] = {}
    effective_source: dict[str, str] = {}

    for row in rows:
        node_id = row["id"]
        if node_id in selected_map:
            chosen = selected_map[node_id]
            effective_parent_id[node_id] = str(chosen["candidate_parent_id"])
            effective_parent_label[node_id] = str(chosen["candidate_parent_label"])
            effective_source[node_id] = str(chosen["selection_status"])
        elif node_id in cleanup_clear_ids:
            effective_parent_id[node_id] = None
            effective_parent_label[node_id] = ""
            effective_source[node_id] = "cleared_reviewed_invalid_parent"
        else:
            effective_parent_id[node_id] = legacy_parent_id.get(node_id)
            effective_parent_label[node_id] = str(row.get("parent_label", "") or "")
            if effective_parent_label[node_id]:
                effective_source[node_id] = "legacy_parent"
            else:
                effective_source[node_id] = "no_parent"

    # Break simple cycles conservatively by clearing the lexically/weaker-ranked child edge.
    cycle_cleared: set[str] = set()
    for child_id, parent_id in list(effective_parent_id.items()):
        if not parent_id or parent_id not in effective_parent_id:
            continue
        if effective_parent_id.get(parent_id) == child_id:
            child_row = selected_map.get(child_id)
            parent_row = selected_map.get(parent_id)
            child_score = (
                child_row.get("channel_specificity", 0) if child_row else 0,
                child_row.get("confidence_score", 0) if child_row else 0,
            )
            parent_score = (
                parent_row.get("channel_specificity", 0) if parent_row else 0,
                parent_row.get("confidence_score", 0) if parent_row else 0,
            )
            loser = child_id if child_score <= parent_score else parent_id
            effective_parent_id[loser] = None
            effective_parent_label[loser] = ""
            effective_source[loser] = "cleared_cycle"
            cycle_cleared.add(loser)

    memo: dict[str, tuple[str | None, str]] = {}

    def resolve_root(node_id: str, trail: set[str]) -> tuple[str | None, str]:
        if node_id in memo:
            return memo[node_id]
        if node_id in trail:
            memo[node_id] = (None, "")
            return memo[node_id]

        parent_id = effective_parent_id.get(node_id)
        parent_label = effective_parent_label.get(node_id, "")
        row = id_to_row[node_id]
        if not parent_id:
            memo[node_id] = (None, parent_label)
            return memo[node_id]

        if parent_id not in id_to_row:
            memo[node_id] = (parent_id, parent_label)
            return memo[node_id]

        parent_row = id_to_row[parent_id]
        if not effective_parent_id.get(parent_id):
            memo[node_id] = (parent_id, parent_row["label"])
            return memo[node_id]

        root_id, root_label = resolve_root(parent_id, trail | {node_id})
        if root_id is None and not root_label:
            memo[node_id] = (parent_id, parent_row["label"])
        else:
            memo[node_id] = (root_id or parent_id, root_label or parent_row["label"])
        return memo[node_id]

    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        node_id = row["id"]
        root_id, root_label = resolve_root(node_id, set())
        enriched = dict(row)
        enriched["effective_parent_id"] = effective_parent_id.get(node_id) or ""
        enriched["effective_parent_label"] = effective_parent_label.get(node_id, "")
        enriched["effective_parent_source"] = effective_source.get(node_id, "no_parent")
        enriched["effective_root_id"] = root_id or ""
        enriched["effective_root_label"] = root_label or ""
        enriched_rows.append(enriched)

    return enriched_rows


def write_summary(
    rows: list[dict[str, Any]],
    selected: pd.DataFrame,
    ambiguous: pd.DataFrame,
    duplicate: pd.DataFrame,
    too_broad: pd.DataFrame,
    cleanup: pd.DataFrame,
    enriched_rows: list[dict[str, Any]],
) -> None:
    selected_children = selected["child_id"].nunique() if not selected.empty else 0
    replaced = 0
    confirmed = 0
    new_parent = 0
    if not selected.empty:
        same_as_current = (
            selected["child_current_parent_label"].fillna("").str.strip()
            == selected["candidate_parent_label"].fillna("").str.strip()
        )
        confirmed = int(same_as_current.sum())
        had_current = selected["child_current_has_parent"].fillna(False).astype(bool)
        replaced = int((had_current & ~same_as_current).sum())
        new_parent = int((~had_current).sum())

    effective_sources = pd.Series(
        [row.get("effective_parent_source", "no_parent") for row in enriched_rows]
    ).value_counts().to_dict()

    lines = [
        "# Parent-Child Reviewed Application v2.2",
        "",
        f"- ontology rows: `{len(rows):,}`",
        f"- selected reviewed parent edges: `{len(selected):,}` rows over `{selected_children:,}` child concepts",
        f"- confirmed current reviewed parents: `{confirmed:,}`",
        f"- replaced current parents with a reviewed better parent: `{replaced:,}`",
        f"- new parent assignments for previously flat concepts: `{new_parent:,}`",
        f"- ambiguous high-confidence valid candidates held out: `{len(ambiguous):,}`",
        f"- duplicate cleanup candidates: `{len(duplicate):,}`",
        f"- too-broad parent candidates: `{len(too_broad):,}`",
        f"- high-confidence invalid current-parent cleanup rows: `{len(cleanup):,}`",
        "",
        "## Effective Parent Source",
    ]
    for key, value in effective_sources.items():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.extend(
        [
            "",
            "## Selected Edge Channels",
        ]
    )
    if not selected.empty:
        for key, value in selected["candidate_channel"].value_counts().to_dict().items():
            lines.append(f"- `{key}`: `{value:,}`")
    lines.extend(
        [
            "",
            "## Sample Selected Edges",
            "",
        ]
    )
    sample_cols = [
        c
        for c in [
            "child_label",
            "candidate_parent_label",
            "candidate_channel",
            "review_tier",
            "selection_status",
            "reason",
        ]
        if c in selected.columns
    ]
    if not selected.empty:
        lines.append(selected[sample_cols].head(20).to_markdown(index=False))
    SUMMARY_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = load_ontology()
    reviews = load_reviews()
    selected, ambiguous = choose_selected_edges(reviews)
    duplicate, too_broad, cleanup = build_cleanup_tables(reviews, selected)

    selected.to_parquet(SELECTED_EDGES_PATH, index=False)
    ambiguous.to_parquet(AMBIGUOUS_PATH, index=False)
    duplicate.to_parquet(DUPLICATE_PATH, index=False)
    too_broad.to_parquet(TOO_BROAD_PATH, index=False)
    cleanup.to_parquet(CLEANUP_PATH, index=False)

    enriched_rows = build_enriched_ontology(rows, selected, cleanup)
    ONTOLOGY_ENRICHED_PATH.write_text(json.dumps(enriched_rows, ensure_ascii=False, indent=2))
    write_summary(rows, selected, ambiguous, duplicate, too_broad, cleanup, enriched_rows)

    print(f"selected edges: {SELECTED_EDGES_PATH}")
    print(f"ambiguous: {AMBIGUOUS_PATH}")
    print(f"duplicates: {DUPLICATE_PATH}")
    print(f"too broad: {TOO_BROAD_PATH}")
    print(f"cleanup: {CLEANUP_PATH}")
    print(f"enriched ontology: {ONTOLOGY_ENRICHED_PATH}")
    print(f"summary: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
