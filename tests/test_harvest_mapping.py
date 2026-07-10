"""Deterministic Wikidata-fact → model mapping: rank/reference → source reliability, PID/P31."""

from __future__ import annotations

import pytest

from sdb.harvest.mapping import (
    HARVEST_EXCLUDED_PROPERTIES,
    HARVEST_PREDICATE_ALIASES,
    HARVEST_PROPERTIES,
    WIKIDATA_PREDICATE,
    domain_for,
    make_source,
    parse_rank,
    source_type_for_references,
)
from sdb.schema.enums import PREDICATE_WIKIDATA, Domain, Predicate, SourceType, WikidataRank


def test_predicate_inverse_covers_curated_wikidata_properties() -> None:
    # Every Wikidata-backed predicate round-trips through the inverse table.
    assert WIKIDATA_PREDICATE["P361"] is Predicate.PART_OF
    assert WIKIDATA_PREDICATE["P155"] is Predicate.FOLLOWS
    assert WIKIDATA_PREDICATE["P941"] is Predicate.INSPIRED_BY  # reconnected in Phase 2 (#1)


def test_harvested_properties_exclude_bibliographic_clutter() -> None:
    # P1343 stays in the vocabulary (for curated MENTIONED_IN) but is never harvested.
    assert "P1343" in WIKIDATA_PREDICATE
    assert "P1343" in HARVEST_EXCLUDED_PROPERTIES
    assert "P1343" not in HARVEST_PROPERTIES
    assert set(HARVEST_PROPERTIES) == set(WIKIDATA_PREDICATE) - HARVEST_EXCLUDED_PROPERTIES


def test_inspired_by_now_has_a_canonical_wikidata_property() -> None:
    assert PREDICATE_WIKIDATA[Predicate.INSPIRED_BY] == "P941"


def test_alias_properties_widen_recall_onto_existing_predicates() -> None:
    # Aliases map many Wikidata properties onto one predicate, without new narration vocabulary.
    assert HARVEST_PREDICATE_ALIASES["P17"] is Predicate.LOCATED_IN  # country
    assert HARVEST_PREDICATE_ALIASES["P131"] is Predicate.LOCATED_IN  # admin territory
    assert HARVEST_PREDICATE_ALIASES["P463"] is Predicate.PART_OF  # member of
    assert set(HARVEST_PREDICATE_ALIASES) <= set(HARVEST_PROPERTIES)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("preferred", WikidataRank.PREFERRED),
        ("NormalRank", WikidataRank.NORMAL),
        ("http://wikiba.se/ontology#DeprecatedRank", WikidataRank.DEPRECATED),
        ("nonsense", WikidataRank.NORMAL),
    ],
)
def test_parse_rank(raw: str, expected: WikidataRank) -> None:
    assert parse_rank(raw) is expected


def test_source_type_reflects_reference_presence() -> None:
    assert source_type_for_references(0) is SourceType.WIKIDATA_NO_REF
    assert source_type_for_references(3) is SourceType.WIKIDATA_WITH_REF


def test_source_reliability_is_deterministic_rank_times_reference_tier() -> None:
    referenced_preferred = make_source("Q1", "P361", "Q2", "preferred", reference_count=2)
    unreferenced_normal = make_source("Q1", "P361", "Q2", "normal", reference_count=0)
    # 0.90 (with-ref) * 1.00 (preferred) ; 0.60 (no-ref) * 0.85 (normal).
    assert referenced_preferred.reliability == pytest.approx(0.90)
    assert unreferenced_normal.reliability == pytest.approx(0.51)
    # The source id encodes the exact statement, so it is stable and de-duplicable.
    assert referenced_preferred.id == "wd_Q1_P361_Q2"


def test_domain_for_takes_first_known_class_then_falls_back() -> None:
    assert domain_for(("Q34770",)) is Domain.LANGUAGE  # language
    assert domain_for(("Q99999999", "Q9174")) is Domain.RELIGION  # skips unknown, finds religion
    assert domain_for(()) is Domain.CULTURE  # documented fallback
    assert domain_for(("Q99999999",)) is Domain.CULTURE
