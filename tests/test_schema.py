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


def test_models_are_frozen() -> None:
    node = Node(id="a", label="A", domain=Domain.HISTORY, type="x")
    with pytest.raises(ValidationError):
        node.label = "B"  # type: ignore[misc]
