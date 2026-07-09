"""Path enumeration: hop bounds, simple-path invariant, parallel edges."""

from __future__ import annotations

import pytest

from sdb.engine.traversal import enumerate_paths
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Node, Source, Statement


def _node(node_id: str) -> Node:
    return Node(id=node_id, label=node_id, domain=Domain.HISTORY, type="x")


def _statement(subject: str, obj: str, source_id: str = "w") -> Statement:
    return Statement(
        subject=subject,
        predicate=Predicate.PART_OF,
        object=obj,
        sources=(Source(id=source_id, source_type=SourceType.WIKIPEDIA),),
    )


def _triangle() -> KnowledgeGraph:
    nodes = (_node("a"), _node("b"), _node("c"))
    statements = (_statement("a", "b"), _statement("b", "c"), _statement("a", "c"))
    return KnowledgeGraph(nodes, statements)


def test_source_must_exist() -> None:
    with pytest.raises(KeyError):
        enumerate_paths(_triangle(), "ghost", 1, 3)


def test_hop_bounds_and_simple_invariant() -> None:
    paths = enumerate_paths(_triangle(), "a", 2, 3)
    assert paths
    for path in paths:
        assert 2 <= path.length <= 3
        assert path.node_ids[0] == "a"
        assert len(set(path.node_ids)) == len(path.node_ids)  # no repeated nodes


def test_parallel_edges_yield_distinct_paths() -> None:
    nodes = (_node("a"), _node("b"))
    statements = (_statement("a", "b", "s1"), _statement("a", "b", "s2"))
    graph = KnowledgeGraph(nodes, statements)
    paths = enumerate_paths(graph, "a", 1, 1)
    assert len(paths) == 2  # one 1-hop path per parallel statement
