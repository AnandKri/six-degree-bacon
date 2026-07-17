"""KnowledgeGraph: integrity checks, derived features, and topic resolution."""

from __future__ import annotations

import math

import pytest

from sdb.graph.build import GraphIntegrityError, KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Node, Source, Statement


def _node(node_id: str, domain: Domain = Domain.HISTORY) -> Node:
    return Node(id=node_id, label=node_id.title(), domain=domain, type="x")


def _statement(subject: str, predicate: Predicate, obj: str) -> Statement:
    return Statement(
        subject=subject,
        predicate=predicate,
        object=obj,
        sources=(Source(id="w", source_type=SourceType.WIKIPEDIA),),
    )


def test_duplicate_node_id_raises() -> None:
    with pytest.raises(GraphIntegrityError):
        KnowledgeGraph((_node("a"), _node("a")), ())


def test_dangling_endpoint_raises() -> None:
    with pytest.raises(GraphIntegrityError):
        KnowledgeGraph((_node("a"),), (_statement("a", Predicate.PART_OF, "ghost"),))


def test_degree_and_rarity() -> None:
    nodes = (_node("a"), _node("b"), _node("c"))
    statements = (
        _statement("a", Predicate.PART_OF, "b"),
        _statement("b", Predicate.PART_OF, "c"),
        _statement("a", Predicate.FOLLOWS, "c"),
    )
    graph = KnowledgeGraph(nodes, statements)
    assert graph.total_edges == 3
    assert graph.degree("a") == 2
    assert graph.rarity(Predicate.FOLLOWS) == pytest.approx(-math.log2(1 / 3))
    assert graph.rarity(Predicate.INSPIRED_BY) == 0.0  # unseen predicate


def test_find_topic_matches(seed_graph: KnowledgeGraph) -> None:
    assert seed_graph.find_topic("roman empire") == "roman_empire"
    assert seed_graph.find_topic("Imperium Romanum") == "roman_empire"  # alias
    assert seed_graph.find_topic("Q2277") == "roman_empire"  # wikidata qid
    assert seed_graph.find_topic("Rome") == "rome"  # the city, not the empire's "Rome" alias
    assert seed_graph.find_topic("does not exist") is None


def test_own_identity_beats_another_nodes_alias() -> None:
    # `roman_empire` (aliased "Rome") is inserted first, but the city's own id/label must win — else
    # the map's precomputed results for `rome` would silently be the empire's (a real bug we hit).
    empire = Node(
        id="roman_empire",
        label="Roman Empire",
        domain=Domain.HISTORY,
        type="empire",
        aliases=("Rome",),
    )
    city = Node(id="rome", label="Rome", domain=Domain.GEOGRAPHY, type="city")
    graph = KnowledgeGraph((empire, city), ())
    assert graph.find_topic("Rome") == "rome"  # id/label beats the earlier node's alias
    assert graph.find_topic("nope") is None
    # But an alias still resolves when nothing matches a primary field.
    assert KnowledgeGraph((empire,), ()).find_topic("Rome") == "roman_empire"


def test_suggest_returns_close_labels(seed_graph: KnowledgeGraph) -> None:
    assert "Roman Empire" in seed_graph.suggest("Roman Empyre")
