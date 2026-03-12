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
    overall = site_data["questions"]["top_slices"]["overall"]
    assert overall, "overall opportunities should not be empty"

    row = overall[0]
    for field in (
        "direct_link_status",
        "supporting_path_count",
        "cross_field",
        "public_pair_label",
        "top_mediator_labels",
        "why_now",
        "recommended_move",
        "slice_label",
        "source_context_summary",
        "target_context_summary",
        "representative_papers",
    ):
        assert field in row, f"{field} should be present in exported opportunity rows"
        assert row[field] not in (None, "", "NA"), f"{field} should be human-readable"


def test_representative_papers_are_deduped_and_capped() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    overall = site_data["questions"]["top_slices"]["overall"]
    assert overall, "overall opportunities should not be empty"

    checked = 0
    for row in overall[:25]:
        papers = row.get("representative_papers", [])
        assert isinstance(papers, list), "representative_papers should be a list"
        assert len(papers) <= 3, "representative_papers should cap at 3 rows"
        paper_ids = [paper["paper_id"] for paper in papers]
        assert len(paper_ids) == len(set(paper_ids)), "representative_papers should be deduped by paper_id"
        for paper in papers:
            assert paper["title"] not in (None, "", "NA"), "representative paper titles should be readable"
            assert "year" in paper, "representative papers should include year"
        checked += 1

    assert checked > 0, "expected to inspect representative paper exports"


def test_curated_opportunities_are_present_in_expected_order() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    expected_home = [
        "FG3C000003__FG3C000208",
        "FG3C000012__FG3C000110",
        "FG3C000053__FG3C001307",
    ]
    expected_questions = [
        "FG3C000003__FG3C000208",
        "FG3C000014__FG3C001221",
        "FG3C000012__FG3C000110",
        "FG3C000053__FG3C001307",
        "FG3C000010__FG3C000019",
        "FG3C000014__FG3C000024",
    ]

    home = site_data["home"]["curated_questions"]
    front_set = site_data["questions"]["curated_front_set"]

    assert [row["pair_key"] for row in home] == expected_home
    assert [row["pair_key"] for row in front_set] == expected_questions
    assert [row["homepage_role"] for row in home] == ["lead", "supporting", "supporting"]

    for row in front_set:
        for field in ("question_title", "short_why", "first_next_step", "who_its_for", "homepage_role"):
            assert row[field] not in (None, "", "NA"), f"{field} should be present on curated opportunity rows"


def test_excluded_pairs_do_not_appear_in_curated_sets() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    excluded = {
        "FG3C000003__FG3C000010",
        "FG3C000014__FG3C000018",
    }

    home_pairs = {row["pair_key"] for row in site_data["home"]["curated_questions"]}
    front_pairs = {row["pair_key"] for row in site_data["questions"]["curated_front_set"]}

    assert home_pairs.isdisjoint(excluded)
    assert front_pairs.isdisjoint(excluded)


def test_public_label_glossary_references_known_concepts() -> None:
    concepts = load_json("concept_index.json")
    concept_ids = {row["concept_id"] for row in concepts}

    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    glossary = site_data["public_label_glossary"]
    assert glossary, "public_label_glossary should not be empty"
    for concept_id, entry in glossary.items():
        assert concept_id in concept_ids, f"{concept_id} should exist in concept_index.json"
        assert entry["subtitle"] not in (None, "", "NA"), f"{concept_id} should include a readable subtitle"


def test_ecological_carrying_capacity_label_override_is_live() -> None:
    with (ROOT / "site" / "src" / "generated" / "site-data.json").open() as handle:
        site_data = json.load(handle)

    glossary = site_data["public_label_glossary"]
    assert glossary["FG3C001307"]["plain_label"] == "ecological carrying capacity"
    assert glossary["FG3C001307"]["subtitle"] == "measured here with load capacity factor"
