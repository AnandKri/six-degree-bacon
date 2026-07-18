"""Schema model behaviour: source reliability rubric, temporal midpoints, immutability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sdb.schema.enums import Domain, SourceType, WikidataRank
from sdb.schema.models import Node, Source


def test_wikipedia_source_ignores_rank() -> None:
    source = Source(id="s", source_type=SourceType.WIKIPEDIA, rank=WikidataRank.NORMAL)
    assert source.reliability == pytest.approx(0.75)


def test_wikidata_source_applies_rank() -> None:
    preferred = Source(
        id="s", source_type=SourceType.WIKIDATA_WITH_REF, rank=WikidataRank.PREFERRED
    )
    normal = Source(id="s", source_type=SourceType.WIKIDATA_WITH_REF, rank=WikidataRank.NORMAL)
    assert preferred.reliability == pytest.approx(0.90)
    assert normal.reliability == pytest.approx(0.90 * 0.85)


def test_node_midpoint_year() -> None:
    both = Node(id="a", label="A", domain=Domain.HISTORY, type="x", start_year=-100, end_year=100)
    start_only = Node(id="b", label="B", domain=Domain.HISTORY, type="x", start_year=-753)
    undated = Node(id="c", label="C", domain=Domain.HISTORY, type="x")
    assert both.midpoint_year == pytest.approx(0.0)
    assert start_only.midpoint_year == pytest.approx(-753.0)
    assert undated.midpoint_year is None


def test_active_period_overrides_existence_extent_for_midpoint() -> None:
    """ADR 0041: ``midpoint_year`` keys off the *active period* (floruit) when present, so a
    long-lived node reads its era of influence rather than a midpoint stretched to the present."""
    india = Node(
        id="india",
        label="India",
        domain=Domain.HISTORY,
        type="region",
        start_year=-3300,
        end_year=2025,
        active_start=-600,
        active_end=1200,
    )
    # The existence midpoint would be a meaningless -637.5; the floruit lands it in classical India.
    assert india._midpoint(india.start_year, india.end_year) == pytest.approx(-637.5)
    assert india.active_midpoint == pytest.approx(300.0)
    assert india.midpoint_year == pytest.approx(300.0)


def test_midpoint_falls_back_to_existence_without_an_active_period() -> None:
    """A node with no curated active period (e.g. a harvested one) still scores off its existence
    extent — the active axis is additive, never required (ADR 0041)."""
    node = Node(id="a", label="A", domain=Domain.HISTORY, type="x", start_year=-100, end_year=100)
    assert node.active_midpoint is None
    assert node.midpoint_year == pytest.approx(0.0)


def test_models_are_frozen() -> None:
    node = Node(id="a", label="A", domain=Domain.HISTORY, type="x")
    with pytest.raises(ValidationError):
        node.label = "B"  # type: ignore[misc]
