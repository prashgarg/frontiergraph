from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "site" / "public" / "data" / "v2"


def load_json(name: str):
    with (PUBLIC_DATA / name).open() as handle:
        return json.load(handle)


def test_concept_index_has_safe_defaults() -> None:
    concepts = load_json("concept_index.json")
    assert concepts, "concept_index.json should not be empty"

    sample = next((row for row in concepts if row["label"] == "income / economic growth"), concepts[0])
    for numeric_key in ("in_degree", "out_degree", "neighbor_count", "weighted_degree", "pagerank"):
        assert isinstance(sample[numeric_key], (int, float)), f"{numeric_key} should be numeric"
    for list_key in ("top_countries", "top_units", "aliases", "search_terms"):
        assert isinstance(sample[list_key], list), f"{list_key} should be a list"


def test_opportunity_export_includes_public_language_fields() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)
    featured = site_data["home"]["featured_opportunities"]
    assert featured, "featured opportunities should not be empty"

    row = featured[0]
    for field in (
        "direct_link_status",
        "supporting_path_count",
        "why_now",
        "recommended_move",
        "slice_label",
        "source_context_summary",
        "target_context_summary",
    ):
        assert field in row, f"{field} should be present in exported opportunity rows"
        assert row[field] not in (None, "", "NA"), f"{field} should be human-readable"
