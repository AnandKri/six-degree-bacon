"""Template narrator: prefixes, labels, directional phrasing."""

from __future__ import annotations

from sdb.engine.narrate import narrate
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Hop, Node, Path, Source, Statement


def _graph(subject: str, obj: str) -> tuple[KnowledgeGraph, Statement]:
    nodes = (
        Node(id="a", label="Alpha", domain=Domain.HISTORY, type="x"),
        Node(id="b", label="Beta", domain=Domain.MYTH, type="x"),
    )
    statement = Statement(
        subject=subject,
        predicate=Predicate.PART_OF,
        object=obj,
        sources=(Source(id="w", source_type=SourceType.WIKIPEDIA),),
    )
    return KnowledgeGraph(nodes, (statement,)), statement


def _forward_path() -> tuple[KnowledgeGraph, Path]:
    graph, statement = _graph("a", "b")
    path = Path(
        node_ids=("a", "b"),
        hops=(Hop(from_id="a", to_id="b", statement=statement, is_reversed=False),),
    )
    return graph, path


def test_til_high_trust() -> None:
    graph, path = _forward_path()
    text, possibly = narrate(graph, path, 0.9)
    assert text.startswith("TIL:")
    assert not possibly
    assert "Alpha" in text
    assert "Beta" in text
    assert "was part of" in text


def test_til_low_trust_is_possibly() -> None:
    graph, path = _forward_path()
    text, possibly = narrate(graph, path, 0.3)
    assert text.startswith("Possibly:")
    assert possibly


def test_reversed_phrasing() -> None:
    graph, statement = _graph("b", "a")  # statement is b -> a, traversed a -> b (reversed)
    path = Path(
        node_ids=("a", "b"),
        hops=(Hop(from_id="a", to_id="b", statement=statement, is_reversed=True),),
    )
    text, _ = narrate(graph, path, 0.9)
    assert "contained" in text  # reversed phrasing for part_of
