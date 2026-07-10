"""Wikipedia-link co-occurrence build and the endpoint-surprise term it powers."""

from __future__ import annotations

import math
from collections.abc import Sequence

import pytest

from sdb.engine.surprise import score_surprise
from sdb.graph.build import KnowledgeGraph
from sdb.harvest.cooccurrence import build_cooccurrence
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Hop, Node, Path, Source, Statement


class _FakeWikipediaClient:
    """Serves canned titles and article links for the co-occurrence builder."""

    def __init__(self, titles: dict[str, str], links: dict[str, set[str]]) -> None:
        self._titles = titles
        self._links = links

    def titles_for(self, qids: Sequence[str]) -> dict[str, str]:
        return {qid: self._titles[qid] for qid in qids if qid in self._titles}

    def outbound_links(self, title: str, candidates: Sequence[str]) -> frozenset[str]:
        return frozenset(self._links.get(title, set()) & set(candidates))


def _node(node_id: str, qid: str | None, label: str) -> Node:
    return Node(id=node_id, label=label, domain=Domain.HISTORY, type="x", wikidata_qid=qid)


def test_build_cooccurrence_resolves_titles_and_restricts_to_seed_nodes() -> None:
    nodes = [_node("a", "QA", "A"), _node("b", "QB", "B"), _node("c", None, "C")]
    client = _FakeWikipediaClient(
        titles={"QA": "A", "QB": "B"},  # c has no qid -> falls back to its label "C"
        links={"A": {"B", "External"}, "B": {"A", "C"}, "C": set()},
    )
    matrix = build_cooccurrence(nodes, client)
    assert matrix == {"a": ["b"], "b": ["a", "c"]}  # "External" dropped; "c" has no outbound links


def _cooc_graph() -> KnowledgeGraph:
    nodes = (
        _node("a", "QA", "A"),
        _node("b", "QB", "B"),
        _node("c", "QC", "C"),
        _node("d", "QD", "D"),
    )
    statements = (
        _statement("a", Predicate.PART_OF, "b"),
        _statement("b", Predicate.FOLLOWS, "c"),
        _statement("c", Predicate.LOCATED_IN, "d"),
    )
    # a<->b are mutually linked (strength 2); a-c share no link (strength 0).
    return KnowledgeGraph(nodes, statements, cooccurrence={"a": ["b"], "b": ["a"]})


def _statement(subject: str, predicate: Predicate, obj: str) -> Statement:
    return Statement(
        subject=subject,
        predicate=predicate,
        object=obj,
        sources=(Source(id="w", source_type=SourceType.WIKIPEDIA),),
    )


def test_unlinked_endpoint_is_more_surprising_than_linked() -> None:
    graph = _cooc_graph()
    # N=4, alpha=0.5 -> denom[a] = 0.5*3 + (outdeg 1 + indeg 1) = 3.5.
    linked = graph.endpoint_unexpectedness("a", "b")  # strength 2 -> -log2(2.5/3.5)
    unlinked = graph.endpoint_unexpectedness("a", "c")  # strength 0 -> -log2(0.5/3.5)
    assert linked == pytest.approx(math.log2(3.5 / 2.5))
    assert unlinked == pytest.approx(math.log2(3.5 / 0.5))
    assert unlinked > linked


def test_endpoint_term_is_zero_without_cooccurrence_data() -> None:
    graph = _cooc_graph()
    bare = KnowledgeGraph(graph.nodes(), graph.statements)
    assert bare.endpoint_unexpectedness("a", "c") == 0.0
    # Same start/end is never "surprising".
    assert graph.endpoint_unexpectedness("a", "a") == 0.0


def test_score_surprise_includes_weighted_endpoint_term() -> None:
    from sdb.constants import W_ENDPOINT

    graph = _cooc_graph()
    path = Path(
        node_ids=("a", "b", "c"),
        hops=(
            Hop(from_id="a", to_id="b", statement=graph.statements[0], is_reversed=False),
            Hop(from_id="b", to_id="c", statement=graph.statements[1], is_reversed=False),
        ),
    )
    score = score_surprise(graph, path)
    assert score.endpoint_unexpectedness == pytest.approx(graph.endpoint_unexpectedness("a", "c"))
    # The endpoint term contributes W_ENDPOINT * unexpectedness to the total.
    assert score.total == pytest.approx(
        score.sum_rarity
        + 2.0 * score.domain_jumps
        + 1.5 * score.temporal_gap
        + W_ENDPOINT * score.endpoint_unexpectedness
        - 0.75 * score.hub_penalty
    )
