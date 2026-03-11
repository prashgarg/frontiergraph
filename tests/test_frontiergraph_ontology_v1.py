from __future__ import annotations

from src.ontology_v1 import (
    canonical_pair,
    context_fingerprint,
    label_signatures,
    normalize_label,
)


def test_normalize_label_case_and_dash() -> None:
    assert normalize_label("Economic Growth") == "economic growth"
    assert normalize_label("carbon—emissions") == "carbon-emissions"


def test_label_signatures_capture_parenthetical_acronym() -> None:
    sig = label_signatures("Foreign Direct Investment (FDI)")
    assert sig["normalized_label"] == "foreign direct investment (fdi)"
    assert sig["no_paren_signature"] == "foreign direct investment"
    assert sig["paren_acronym"] == "fdi"
    assert sig["initialism_signature"] == "fdi"


def test_label_signatures_ignore_non_acronym_parenthetical_scope() -> None:
    sig = label_signatures("Eastern Region (China)")
    assert sig["normalized_label"] == "eastern region (china)"
    assert sig["no_paren_signature"] == "eastern region"
    assert sig["paren_acronym"] == ""


def test_label_signatures_keep_economics_not_economic() -> None:
    sig = label_signatures("Economics")
    assert sig["normalized_label"] == "economics"
    assert sig["singular_signature"] == "economics"


def test_context_fingerprint_is_stable() -> None:
    left = context_fingerprint(
        countries_json='["USA"]',
        unit_of_analysis_json='["individual"]',
        start_year_json="[2008]",
        end_year_json="[2009]",
        context_note="Oregon lottery",
    )
    right = context_fingerprint(
        countries_json='["USA"]',
        unit_of_analysis_json='["individual"]',
        start_year_json="[2008]",
        end_year_json="[2009]",
        context_note="Oregon lottery",
    )
    assert left == right


def test_canonical_pair_is_order_independent() -> None:
    assert canonical_pair("z", "a") == ("a", "z")
