"""Deterministic surprise scoring, including the human-vs-code surprise golden case."""

from __future__ import annotations

import math

import pytest

from sdb.engine.surprise import score_surprise
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, Region, SourceType
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
    # Both hops cross a domain, but each predicate crosses on 1 of its 1 edges here, so the jump is
    # fully predictable from the predicate and earns little: weight = 1 - (1+0.5)/(1+1) = 0.25 each
    # (ADR 0034). A flat count would have said 2.
    assert score.domain_jumps == pytest.approx(0.5)
    # These fixture nodes carry no region, so the region term (ADR 0039) contributes nothing and the
    # hand-calc total is unchanged — the region axis is strictly additive, never a tax on the rest.
    assert score.region_jumps == pytest.approx(0.0)
    assert score.temporal_gap == pytest.approx(0.4)
    assert score.hub_penalty == pytest.approx(0.0)
    assert score.total == pytest.approx(5.6)  # see docs/confidence-rubric.md


def test_domain_jump_weight_discounts_a_jump_the_predicate_guarantees() -> None:
    """A jump is only surprising if the predicate did not already imply it (ADR 0034).

    The fixture's four predicates each cross a domain on their single edge, so each is fully
    predictable and discounted alike. The real seed separates them sharply: `located_in` lands in
    `geography` on 94% of its edges (weight ~0.07) while `follows` almost never crosses (~0.92).
    """
    graph = _fixture()
    # Every predicate here jumps on 1/1 edges -> P = (1+0.5)/(1+1) = 0.75 -> weight 0.25.
    for predicate in (Predicate.INFLUENCED_BY, Predicate.DERIVED_FROM, Predicate.FOLLOWS):
        assert graph.domain_jump_weight(predicate) == pytest.approx(0.25)
    # An unseen predicate has no evidence either way and smooths to the 0.5 prior, not a free jump.
    assert graph.domain_jump_weight(Predicate.MENTIONED_IN) == pytest.approx(0.5)
    # Bounded [0, 1], so W_DOMAIN keeps its meaning: a fully-unexpected jump is still worth 2.0.
    for predicate in Predicate:
        assert 0.0 <= graph.domain_jump_weight(predicate) <= 1.0


def _rnode(node_id: str, domain: Domain, region: Region) -> Node:
    return Node(id=node_id, label=node_id, domain=domain, type="x", region=region)


def _region_fixture() -> KnowledgeGraph:
    """Two edges chosen to isolate each axis (ADR 0039): one crosses a domain but not a region, the
    other crosses a region but not a domain."""
    nodes = (
        _rnode("a", Domain.SCIENCE, Region.WESTERN),
        _rnode("b", Domain.HISTORY, Region.WESTERN),  # same culture, other discipline
        _rnode("c", Domain.SCIENCE, Region.NEAR_EASTERN),  # same discipline, other culture
    )
    statements = (
        _statement("a", Predicate.PART_OF, "b"),  # domain jump only
        _statement("a", Predicate.INFLUENCED_BY, "c"),  # region jump only
    )
    return KnowledgeGraph(nodes, statements)


def _one_hop(graph: KnowledgeGraph, index: int, a: str, b: str) -> Path:
    st = graph.statements[index]
    return Path(node_ids=(a, b), hops=(Hop(from_id=a, to_id=b, statement=st, is_reversed=False),))


def test_region_and_domain_jumps_are_independent_axes() -> None:
    """ADR 0039: region is additive to domain because the two measure different crossings.

    A hop within one culture but across disciplines (``a --part_of--> b``, both Western) scores a
    domain jump and *no* region jump; a hop within one discipline but across cultures
    (``a --influenced_by--> c``, both science) scores a region jump and *no* domain jump — the
    cross-cultural science lineage the term exists to reward. Each predicate crosses its axis on its
    single edge, so both weights are ``1 - (1 + 0.5)/(1 + 1) = 0.25``.
    """
    graph = _region_fixture()

    domain_only = score_surprise(graph, _one_hop(graph, 0, "a", "b"))
    assert domain_only.domain_jumps == pytest.approx(0.25)
    assert domain_only.region_jumps == pytest.approx(0.0)

    region_only = score_surprise(graph, _one_hop(graph, 1, "a", "c"))
    assert region_only.domain_jumps == pytest.approx(0.0)
    assert region_only.region_jumps == pytest.approx(0.25)


def test_region_jump_weight_discounts_a_jump_the_predicate_guarantees() -> None:
    """The region twin of the domain-jump base rate (ADR 0039).

    Only regioned edges feed the rate. ``influenced_by`` crosses a region on its 1 regioned edge, so
    P = (1 + 0.5)/(1 + 1) = 0.75 and the weight is 0.25; ``part_of`` never crosses on its 1 regioned
    edge, so P = 0.25 and the weight is 0.75. A predicate with no regioned edges smooths to 0.5.
    """
    graph = _region_fixture()
    assert graph.region_jump_weight(Predicate.INFLUENCED_BY) == pytest.approx(0.25)
    assert graph.region_jump_weight(Predicate.PART_OF) == pytest.approx(0.75)
    assert graph.region_jump_weight(Predicate.FOLLOWS) == pytest.approx(0.5)  # unseen -> prior
    for predicate in Predicate:
        assert 0.0 <= graph.region_jump_weight(predicate) <= 1.0
