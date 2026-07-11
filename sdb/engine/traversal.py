"""Deterministic traversal: find candidate simple paths from a source node.

Two strategies behind one entry point, :func:`find_paths` (ADR 0010):

- :func:`enumerate_paths` exhaustively lists every simple path with a hop count in
  ``[min_hops, max_hops]``. It is exact but exponential in degree x depth, so it takes an optional
  ``budget`` and raises :class:`SearchBudgetExceededError` past it.
- :func:`guided_paths` is a deterministic best-first walk that spends a fixed budget on the most
  *promising* prefixes — those accumulating rare edges, domain jumps and endpoint unexpectedness
  (the surprise signal), while avoiding hubs. It bounds work on large harvested graphs.

:func:`find_paths` enumerates exhaustively while that is cheap and only falls back to the guided
walk when a search would exceed the budget, so small graphs (the seed) are explored exhaustively and
their results are unchanged. Hub-avoidance and rare-edge preference remain realized in the
*surprise* ranking (ADR 0001); the walk only *orders* discovery, never a found path's score.
"""

from __future__ import annotations

import heapq
import itertools

from sdb.constants import (
    EXACT_PATH_BUDGET,
    GUIDED_CANDIDATE_BUDGET,
    GUIDED_EXPANSION_BUDGET,
    HUB_DEGREE_THRESHOLD,
    W_DOMAIN,
    W_ENDPOINT,
    W_HUB,
    W_RARITY,
)
from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import Hop, Path


class SearchBudgetExceededError(Exception):
    """Raised by :func:`enumerate_paths` when a bounded enumeration would exceed its budget."""


def find_paths(graph: KnowledgeGraph, source: str, min_hops: int, max_hops: int) -> list[Path]:
    """Find candidate simple paths from ``source``: exact when tractable, guided when explosive.

    Enumerates exhaustively under :data:`~sdb.constants.EXACT_PATH_BUDGET`; if that budget would be
    exceeded (a large, dense graph), falls back to the bounded :func:`guided_paths`. On small graphs
    the exact branch always runs, so results are identical to plain exhaustive enumeration.

    Raises:
        KeyError: If ``source`` is not a node in the graph.
    """
    try:
        return enumerate_paths(graph, source, min_hops, max_hops, budget=EXACT_PATH_BUDGET)
    except SearchBudgetExceededError:
        return guided_paths(
            graph,
            source,
            min_hops,
            max_hops,
            max_candidates=GUIDED_CANDIDATE_BUDGET,
            max_expansions=GUIDED_EXPANSION_BUDGET,
        )


def enumerate_paths(
    graph: KnowledgeGraph,
    source: str,
    min_hops: int,
    max_hops: int,
    *,
    budget: int | None = None,
) -> list[Path]:
    """Enumerate all simple paths from ``source`` with ``min_hops..max_hops`` edges.

    Parallel edges (distinct statements between the same two nodes) yield distinct paths. Output
    order is deterministic. When ``budget`` is set, enumeration raises
    :class:`SearchBudgetExceededError` as soon as it would emit more than ``budget`` paths (used by
    :func:`find_paths` to detect an explosive search cheaply); ``budget=None`` is unlimited.

    Raises:
        KeyError: If ``source`` is not a node in the graph.
        SearchBudgetExceededError: If ``budget`` is set and the enumeration would exceed it.
    """
    if not graph.has_node(source):
        raise KeyError(source)

    results: list[Path] = []

    def walk(current: str, visited: frozenset[str], hops: list[Hop]) -> None:
        if len(hops) >= min_hops:
            results.append(_build_path(source, hops))
            if budget is not None and len(results) > budget:
                raise SearchBudgetExceededError(source)
        if len(hops) >= max_hops:
            return
        for neighbor, statement, is_reversed in graph.incident(current):
            if neighbor in visited:
                continue
            hop = Hop(
                from_id=current,
                to_id=neighbor,
                statement=statement,
                is_reversed=is_reversed,
            )
            walk(neighbor, visited | {neighbor}, [*hops, hop])

    walk(source, frozenset({source}), [])
    return results


def guided_paths(
    graph: KnowledgeGraph,
    source: str,
    min_hops: int,
    max_hops: int,
    *,
    max_candidates: int,
    max_expansions: int,
) -> list[Path]:
    """Best-first walk that spends a bounded budget on the most *promising* prefixes.

    A deterministic priority frontier expands partial walks in descending order of a prefix
    *promise* — an incremental mirror of :mod:`~sdb.engine.surprise` (rare edges + domain jumps +
    endpoint unexpectedness of the current node, less a hub penalty), reusing the same weights. It
    emits a candidate whenever a popped prefix has a hop count in ``[min_hops, max_hops]`` and stops
    at ``max_candidates`` emitted paths or ``max_expansions`` frontier pops (so a pathological graph
    still terminates). Guidance orders discovery only; scoring/ranking downstream is unchanged.

    On a small graph the frontier empties before either budget binds, so the emitted *set* equals
    :func:`enumerate_paths` — the guided walk is a strict generalization, not a different answer.

    Raises:
        KeyError: If ``source`` is not a node in the graph.
    """
    if not graph.has_node(source):
        raise KeyError(source)

    counter = itertools.count()  # unique, monotonic tie-breaker so heap never compares payloads
    # Frontier entries: (-promise, seq, current, visited, hops, sum_rarity, domain_jumps, hub_pen).
    frontier: list[tuple[float, int, str, frozenset[str], tuple[Hop, ...], float, int, float]] = []

    def promise(current: str, sum_rarity: float, domain_jumps: int, hub_penalty: float) -> float:
        return (
            W_RARITY * sum_rarity
            + W_DOMAIN * domain_jumps
            + W_ENDPOINT * graph.endpoint_unexpectedness(source, current)
            - W_HUB * hub_penalty
        )

    def push(
        current: str,
        visited: frozenset[str],
        hops: tuple[Hop, ...],
        sum_rarity: float,
        domain_jumps: int,
        hub_penalty: float,
    ) -> None:
        priority = promise(current, sum_rarity, domain_jumps, hub_penalty)
        heapq.heappush(
            frontier,
            (
                -priority,
                next(counter),
                current,
                visited,
                hops,
                sum_rarity,
                domain_jumps,
                hub_penalty,
            ),
        )

    push(source, frozenset({source}), (), 0.0, 0, 0.0)
    results: list[Path] = []
    expansions = 0

    while frontier and len(results) < max_candidates and expansions < max_expansions:
        _, _, current, visited, hops, sum_rarity, domain_jumps, hub_penalty = heapq.heappop(
            frontier
        )
        expansions += 1

        if len(hops) >= min_hops:
            results.append(_build_path(source, list(hops)))
            if len(results) >= max_candidates:
                break
        if len(hops) >= max_hops:
            continue

        # Extending past `current` makes it an interior node, so it now accrues any hub penalty.
        excess = graph.degree(current) - HUB_DEGREE_THRESHOLD
        interior_penalty = max(0, excess) / HUB_DEGREE_THRESHOLD if current != source else 0.0
        for neighbor, statement, is_reversed in graph.incident(current):
            if neighbor in visited:
                continue
            hop = Hop(from_id=current, to_id=neighbor, statement=statement, is_reversed=is_reversed)
            push(
                neighbor,
                visited | {neighbor},
                (*hops, hop),
                sum_rarity + graph.rarity(statement.predicate),
                domain_jumps + (graph.node(current).domain != graph.node(neighbor).domain),
                hub_penalty + interior_penalty,
            )

    return results


def _build_path(source: str, hops: list[Hop]) -> Path:
    """Assemble a :class:`Path` from the source node and the ordered hops."""
    node_ids = (source, *(hop.to_id for hop in hops))
    return Path(node_ids=node_ids, hops=tuple(hops))
