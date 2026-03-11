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
    overall = site_data["opportunities"]["top_slices"]["overall"]
    assert overall, "overall opportunities should not be empty"

    row = overall[0]
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


def test_curated_opportunities_are_present_in_expected_order() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    expected_home = [
        "FG3C000003__FG3C000208",
        "FG3C000014__FG3C001221",
        "FG3C000012__FG3C000110",
        "FG3C000053__FG3C001307",
    ]
    expected_opportunities = [
        "FG3C000003__FG3C000208",
        "FG3C000014__FG3C001221",
        "FG3C000012__FG3C000110",
        "FG3C000053__FG3C001307",
        "FG3C000010__FG3C000019",
        "FG3C000030__FG3C001420",
        "FG3C000014__FG3C000024",
        "FG3C000046__FG3C000203",
    ]

    home = site_data["home"]["curated_opportunities"]
    front_set = site_data["opportunities"]["curated_front_set"]

    assert [row["pair_key"] for row in home] == expected_home
    assert [row["pair_key"] for row in front_set] == expected_opportunities

    for row in front_set:
        for field in ("headline", "summary", "why_it_matters", "how_to_start"):
            assert row[field] not in (None, "", "NA"), f"{field} should be present on curated opportunity rows"


def test_excluded_pairs_do_not_appear_in_curated_sets() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    excluded = {
        "FG3C000003__FG3C000010",
        "FG3C000014__FG3C000018",
    }

    home_pairs = {row["pair_key"] for row in site_data["home"]["curated_opportunities"]}
    front_pairs = {row["pair_key"] for row in site_data["opportunities"]["curated_front_set"]}

    assert home_pairs.isdisjoint(excluded)
    assert front_pairs.isdisjoint(excluded)
