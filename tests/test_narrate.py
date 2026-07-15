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


def _chain(middle_type: str) -> tuple[KnowledgeGraph, Path]:
    """A 2-hop path a -> b -> c, with `b`'s node type controlling the relative pronoun."""
    nodes = (
        Node(id="a", label="Alpha", domain=Domain.HISTORY, type="king"),
        Node(id="b", label="Beta", domain=Domain.MYTH, type=middle_type),
        Node(id="c", label="Gamma", domain=Domain.GEOGRAPHY, type="city"),
    )
    source = Source(id="w", source_type=SourceType.WIKIPEDIA)
    first = Statement(subject="a", predicate=Predicate.PART_OF, object="b", sources=(source,))
    second = Statement(subject="b", predicate=Predicate.PART_OF, object="c", sources=(source,))
    path = Path(
        node_ids=("a", "b", "c"),
        hops=(
            Hop(from_id="a", to_id="b", statement=first, is_reversed=False),
            Hop(from_id="b", to_id="c", statement=second, is_reversed=False),
        ),
    )
    return KnowledgeGraph(nodes, (first, second)), path


def test_til_is_a_single_sentence_with_the_subject_elided() -> None:
    # ADR 0028: the TIL is one quantized claim — the first hop in full, then relative clauses. The
    # hop-by-hop chain is rendered separately by every caller, so it is not restated (and there is
    # no meta-closer), leaving exactly one sentence.
    graph, path = _chain("deity")
    text, _ = narrate(graph, path, 0.9)
    assert text == "TIL: Alpha was part of Beta, who was part of Gamma."
    assert text.count(".") == 1  # one sentence: no restated chain, no "It connects ..." closer


def test_relative_pronoun_follows_animacy() -> None:
    # A person/personified being takes "who"; anything else takes "which".
    graph, path = _chain("city")
    text, _ = narrate(graph, path, 0.9)
    assert "Beta, which was part of Gamma" in text


def test_reversed_phrasing() -> None:
    graph, statement = _graph("b", "a")  # statement is b -> a, traversed a -> b (reversed)
    path = Path(
        node_ids=("a", "b"),
        hops=(Hop(from_id="a", to_id="b", statement=statement, is_reversed=True),),
    )
    text, _ = narrate(graph, path, 0.9)
    assert "contained" in text  # reversed phrasing for part_of
