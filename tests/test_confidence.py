"""Deterministic trust scoring, including the human-vs-code confidence golden case."""

from __future__ import annotations

import pytest

from sdb.engine.confidence import noisy_or, score_trust, statement_confidence
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Hop, Node, Path, Source, Statement


def _node(
    node_id: str, domain: Domain = Domain.HISTORY, start: int | None = None, end: int | None = None
) -> Node:
    return Node(id=node_id, label=node_id, domain=domain, type="x", start_year=start, end_year=end)


def _wikipedia(source_id: str) -> Source:
    return Source(id=source_id, source_type=SourceType.WIKIPEDIA)


def test_noisy_or() -> None:
    assert noisy_or([]) == 0.0
    assert noisy_or([0.75, 0.75]) == pytest.approx(0.9375)
    assert noisy_or([0.90, 0.40]) == pytest.approx(0.94)


def test_statement_confidence_matches_hand_calc() -> None:
    # Two 0.75 sources -> 0.9375 corroborated; x 0.8 link quality = 0.75 (see confidence-rubric.md).
    nodes = (_node("a", start=100, end=200), _node("b", Domain.MYTH, start=-100, end=-50))
    statement = Statement(
        subject="a",
        predicate=Predicate.INFLUENCED_BY,
        object="b",
        sources=(_wikipedia("w"), Source(id="bk", source_type=SourceType.SECONDARY_BOOK)),
        link_quality=0.8,
    )
    graph = KnowledgeGraph(nodes, (statement,))
    assert statement_confidence(graph, statement) == pytest.approx(0.75)


def test_follows_temporal_penalty() -> None:
    # "b follows a" but b (mid -75) predates a (mid 150): 0.40 penalty -> 0.75 * 0.6.
    nodes = (_node("a", start=100, end=200), _node("b", start=-100, end=-50))
    statement = Statement(
        subject="b", predicate=Predicate.FOLLOWS, object="a", sources=(_wikipedia("w"),)
    )
    graph = KnowledgeGraph(nodes, (statement,))
    assert statement_confidence(graph, statement) == pytest.approx(0.75 * 0.6)


def test_date_disorder_penalty() -> None:
    # Node 'a' has start_year > end_year: 0.50 penalty -> 0.75 * 0.5.
    nodes = (_node("a", start=200, end=100), _node("b"))
    statement = Statement(
        subject="a", predicate=Predicate.PART_OF, object="b", sources=(_wikipedia("w"),)
    )
    graph = KnowledgeGraph(nodes, (statement,))
    assert statement_confidence(graph, statement) == pytest.approx(0.75 * 0.5)


def test_path_trust_is_product() -> None:
    nodes = (_node("a"), _node("b"), _node("c"))
    first = Statement(
        subject="a", predicate=Predicate.PART_OF, object="b", sources=(_wikipedia("w"),)
    )
    second = Statement(
        subject="b", predicate=Predicate.PART_OF, object="c", sources=(_wikipedia("w"),)
    )
    graph = KnowledgeGraph(nodes, (first, second))
    path = Path(
        node_ids=("a", "b", "c"),
        hops=(
            Hop(from_id="a", to_id="b", statement=first, is_reversed=False),
            Hop(from_id="b", to_id="c", statement=second, is_reversed=False),
        ),
    )
    trust = score_trust(graph, path)
    assert trust.edge_confidences == pytest.approx((0.75, 0.75))
    assert trust.total == pytest.approx(0.5625)
