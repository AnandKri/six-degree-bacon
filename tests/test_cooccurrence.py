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

    def all_outbound_links(self, title: str) -> frozenset[str]:
        return frozenset(self._links.get(title, set()))  # unfiltered: the whole article's links


def _node(node_id: str, qid: str | None, label: str) -> Node:
    return Node(id=node_id, label=label, domain=Domain.HISTORY, type="x", wikidata_qid=qid)


def test_build_cooccurrence_resolves_titles_and_restricts_to_seed_nodes() -> None:
    nodes = [_node("a", "QA", "A"), _node("b", "QB", "B"), _node("c", None, "C")]
    client = _FakeWikipediaClient(
        titles={"QA": "A", "QB": "B"},  # c has no qid -> falls back to its label "C"
        links={"A": {"B", "External", "Shared"}, "B": {"A", "C"}, "C": {"Shared"}},
    )
    matrix, similarity = build_cooccurrence(nodes, client)
    # The link matrix stays restricted to seed titles: "External"/"Shared" are dropped.
    assert matrix == {"a": ["b"], "b": ["a", "c"]}
    # Similarity is measured over the *full* link sets (ADR 0029), so it sees "Shared" — which `a`
    # and `c` both link even though neither links the other: |{shared}| / |{b, external, shared}|.
    assert similarity == {"a": {"c": pytest.approx(1 / 3, abs=1e-6)}}


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


def test_shared_context_reduces_unexpectedness() -> None:
    # Second-order co-occurrence (ADR 0029): `a` links `b` directly (strength 1); `a` and `c` never
    # link each other but their full articles overlap (jaccard 0.25); `d` shares nothing. With
    # weight=2.0, alpha=0.5, N=4 the effective strengths are eff(a,b)=1, eff(a,c)=0.5 (2.0*0.25),
    # eff(a,d)=0, so denom[a] = 1.5 + 1.0 + 0.5 = 3.0. The shared-context node `c` therefore lands
    # *between* the linked `b` and the isolated `d`, instead of tying with `d` at the maximum.
    nodes = (
        _node("a", "QA", "A"),
        _node("b", "QB", "B"),
        _node("c", "QC", "C"),
        _node("d", "QD", "D"),
    )
    graph = KnowledgeGraph(nodes, (), cooccurrence={"a": ["b"]}, similarity={"a": {"c": 0.25}})
    linked = graph.endpoint_unexpectedness("a", "b")
    shared = graph.endpoint_unexpectedness("a", "c")
    isolated = graph.endpoint_unexpectedness("a", "d")
    assert linked == pytest.approx(1.0)  # -log2(1.5 / 3.0)
    assert shared == pytest.approx(math.log2(3.0))  # -log2(1.0 / 3.0)
    assert isolated == pytest.approx(math.log2(6.0))  # -log2(0.5 / 3.0)
    assert isolated > shared > linked


def test_endpoint_term_does_not_saturate(seed_graph: KnowledgeGraph) -> None:
    # ADR 0029 canary. Before the full-link similarity the endpoint term saturated for peripheral
    # nodes — house_of_wessex tied 94% of the graph at maximum unexpectedness (it links just one
    # *seed* node), collapsing the pair ranking onto trust. Sparse nodes arrive with every new
    # breadth cluster, so bound the tie fraction here to catch that regression rather than
    # rediscover it. Currently every start is fully distinct (only the single max "ties", ~1.1%).
    ids = [node.id for node in seed_graph.nodes()]
    for start in ("house_of_wessex", "confucius", "mansa_musa", "roman_empire"):
        values = [round(seed_graph.endpoint_unexpectedness(start, e), 6) for e in ids if e != start]
        assert values.count(max(values)) <= 0.05 * len(values), start


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
