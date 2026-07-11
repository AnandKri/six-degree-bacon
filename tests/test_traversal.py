"""Path search: hop bounds, simple-path invariant, parallel edges, budget + guided-walk scaling."""

from __future__ import annotations

import pytest

from sdb.constants import EXACT_PATH_BUDGET, GUIDED_CANDIDATE_BUDGET
from sdb.engine.traversal import (
    SearchBudgetExceededError,
    enumerate_paths,
    find_paths,
    guided_paths,
)
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Node, Source, Statement

_DOMAINS = tuple(Domain)
_PREDICATES = tuple(Predicate)


def _node(node_id: str, domain: Domain = Domain.HISTORY) -> Node:
    return Node(id=node_id, label=node_id, domain=domain, type="x")


def _statement(
    subject: str, obj: str, source_id: str = "w", predicate: Predicate = Predicate.PART_OF
) -> Statement:
    return Statement(
        subject=subject,
        predicate=predicate,
        object=obj,
        sources=(Source(id=source_id, source_type=SourceType.WIKIPEDIA),),
    )


def _triangle() -> KnowledgeGraph:
    nodes = (_node("a"), _node("b"), _node("c"))
    statements = (_statement("a", "b"), _statement("b", "c"), _statement("a", "c"))
    return KnowledgeGraph(nodes, statements)


def _dense_graph(n_nodes: int, degree: int) -> KnowledgeGraph:
    """A deterministic dense graph whose exhaustive [3,6] enumeration explodes past the budget."""
    nodes = tuple(_node(f"n{i}", _DOMAINS[i % len(_DOMAINS)]) for i in range(n_nodes))
    statements = tuple(
        _statement(
            f"n{i}",
            f"n{(i * 7 + j * 13 + 1) % n_nodes}",
            f"s{i}_{j}",
            _PREDICATES[(i + j) % len(_PREDICATES)],
        )
        for i in range(n_nodes)
        for j in range(degree)
        if (i * 7 + j * 13 + 1) % n_nodes != i
    )
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


# --- budget + guided walk (ADR 0010) ---------------------------------------


def test_enumerate_paths_budget_raises_only_when_exceeded() -> None:
    graph = _triangle()
    full = enumerate_paths(graph, "a", 1, 3)
    assert len(full) > 1
    # A budget below the true count aborts the enumeration; at/above it enumerates fully.
    with pytest.raises(SearchBudgetExceededError):
        enumerate_paths(graph, "a", 1, 3, budget=1)
    assert enumerate_paths(graph, "a", 1, 3, budget=len(full)) == full


def test_find_paths_is_exact_on_small_graphs() -> None:
    # Below the budget, find_paths uses the exact branch, so results are byte-identical.
    graph = _triangle()
    for lo, hi in ((1, 3), (2, 3)):
        assert find_paths(graph, "a", lo, hi) == enumerate_paths(graph, "a", lo, hi)


def test_guided_walk_equals_exhaustive_when_budget_not_binding() -> None:
    # With budgets larger than the search, the guided walk emits the same *set* (only the order
    # differs), so switching to it never changes which paths downstream ranking can see.
    graph = _triangle()
    exhaustive = set(enumerate_paths(graph, "a", 1, 3))
    guided = set(guided_paths(graph, "a", 1, 3, max_candidates=10_000, max_expansions=10_000))
    assert guided == exhaustive


def test_guided_walk_respects_bounds_and_is_deterministic() -> None:
    graph = _triangle()
    paths = guided_paths(graph, "a", 2, 3, max_candidates=100, max_expansions=100)
    assert paths
    for path in paths:
        assert 2 <= path.length <= 3
        assert path.node_ids[0] == "a"
        assert len(set(path.node_ids)) == len(path.node_ids)  # simple path
    assert paths == guided_paths(graph, "a", 2, 3, max_candidates=100, max_expansions=100)


def test_guided_walk_stops_at_candidate_budget() -> None:
    graph = _dense_graph(200, 10)
    paths = guided_paths(graph, "n0", 1, 6, max_candidates=50, max_expansions=10_000)
    assert len(paths) == 50  # emission stops exactly at the candidate budget


def test_missing_source_raises_in_both_strategies() -> None:
    graph = _triangle()
    with pytest.raises(KeyError):
        find_paths(graph, "ghost", 1, 3)
    with pytest.raises(KeyError):
        guided_paths(graph, "ghost", 1, 3, max_candidates=10, max_expansions=10)


def test_guided_walk_bounds_an_explosive_search() -> None:
    # A dense graph makes exhaustive [3,6] explode; the guided fallback stays bounded, valid, and
    # deterministic — the scaling guarantee (perf test), independent of wall-clock timing.
    graph = _dense_graph(500, 12)
    with pytest.raises(SearchBudgetExceededError):
        enumerate_paths(graph, "n0", 3, 6, budget=EXACT_PATH_BUDGET)

    result = find_paths(graph, "n0", 3, 6)
    assert 0 < len(result) <= GUIDED_CANDIDATE_BUDGET
    for path in result:
        assert 3 <= path.length <= 6
        assert path.node_ids[0] == "n0"
        assert len(set(path.node_ids)) == len(path.node_ids)
    assert [p.node_ids for p in result] == [p.node_ids for p in find_paths(graph, "n0", 3, 6)]
