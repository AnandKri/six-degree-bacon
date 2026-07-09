"""Deterministic surprise scoring, including the human-vs-code surprise golden case."""

from __future__ import annotations

import math

import pytest

from sdb.engine.surprise import score_surprise
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Hop, Node, Path, Source, Statement


def _node(node_id: str, domain: Domain, year: int) -> Node:
    return Node(id=node_id, label=node_id, domain=domain, type="x", start_year=year, end_year=year)


def _statement(subject: str, predicate: Predicate, obj: str) -> Statement:
    return Statement(
        subject=subject,
        predicate=predicate,
        object=obj,
        sources=(Source(id="w", source_type=SourceType.WIKIPEDIA),),
    )


def _fixture() -> KnowledgeGraph:
    # Four edges, four distinct predicates (each rarity = -log2(1/4) = 2.0).
    nodes = (
        _node("x", Domain.HISTORY, 0),
        _node("y", Domain.MYTH, 100),
        _node("z", Domain.TRADE, 400),
        _node("w", Domain.SCIENCE, 0),
    )
    statements = (
        _statement("x", Predicate.INFLUENCED_BY, "y"),
        _statement("y", Predicate.DERIVED_FROM, "z"),
        _statement("x", Predicate.PART_OF, "w"),
        _statement("w", Predicate.FOLLOWS, "z"),
    )
    return KnowledgeGraph(nodes, statements)


def test_rarity_is_self_information() -> None:
    assert _fixture().rarity(Predicate.INFLUENCED_BY) == pytest.approx(-math.log2(1 / 4))


def test_surprise_matches_hand_calc() -> None:
    graph = _fixture()
    first, second = graph.statements[0], graph.statements[1]
    path = Path(
        node_ids=("x", "y", "z"),
        hops=(
            Hop(from_id="x", to_id="y", statement=first, is_reversed=False),
            Hop(from_id="y", to_id="z", statement=second, is_reversed=False),
        ),
    )
    score = score_surprise(graph, path)
    assert score.sum_rarity == pytest.approx(4.0)
    assert score.domain_jumps == 2
    assert score.temporal_gap == pytest.approx(0.4)
    assert score.length_bonus == 0
    assert score.hub_penalty == pytest.approx(0.0)
    assert score.total == pytest.approx(8.6)  # see docs/confidence-rubric.md
