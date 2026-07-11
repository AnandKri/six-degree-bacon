"""Deterministic Wikidata-fact → model mapping: rank/reference → source reliability, PID/P31."""

from __future__ import annotations

import pytest

from sdb.harvest.mapping import (
    HARVEST_EXCLUDED_PROPERTIES,
    HARVEST_PREDICATE_ALIASES,
    HARVEST_PROPERTIES,
    INSTANCE_OF_DOMAIN,
    WIKIDATA_PREDICATE,
    domain_for,
    make_source,
    parse_rank,
    source_type_for_references,
    temporal_extent,
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


def test_domain_table_now_covers_science_and_art() -> None:
    # These two Domains had no P31 mapping before enrichment, so every such node fell to `culture`.
    assert domain_for(("Q2465832",)) is Domain.SCIENCE  # branch of science
    assert domain_for(("Q62832",)) is Domain.SCIENCE  # observatory
    assert domain_for(("Q735",)) is Domain.ART  # art
    assert domain_for(("Q3305213",)) is Domain.ART  # painting
    # And common subtypes of existing domains no longer fall through.
    assert domain_for(("Q34876",)) is Domain.GEOGRAPHY  # province
    assert domain_for(("Q131569",)) is Domain.HISTORY  # treaty
    assert domain_for(("Q33384",)) is Domain.LANGUAGE  # dialect


def test_domain_table_keys_are_unique_wikidata_qids() -> None:
    # A duplicate key would silently drop a mapping; every key is a QID.
    assert all(qid.startswith("Q") and qid[1:].isdigit() for qid in INSTANCE_OF_DOMAIN)


def test_temporal_extent_folds_thing_and_person_dates() -> None:
    # A thing: inception -> start, dissolution -> end.
    assert temporal_extent(
        inception_year=-27, birth_year=None, death_year=None, dissolved_year=476
    ) == (-27, 476)
    # A person: birth -> start, death -> end (P571 alone used to leave them undated).
    assert temporal_extent(
        inception_year=None, birth_year=-323, death_year=-283, dissolved_year=None
    ) == (-323, -283)
    # Nothing known -> both None; inception/dissolution win if a pair somehow co-occurs.
    assert temporal_extent(
        inception_year=None, birth_year=None, death_year=None, dissolved_year=None
    ) == (None, None)
    assert temporal_extent(
        inception_year=100, birth_year=50, death_year=90, dissolved_year=200
    ) == (100, 200)
