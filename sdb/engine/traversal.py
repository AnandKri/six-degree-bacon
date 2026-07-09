"""Deterministic traversal: enumerate candidate simple paths from a source node.

For the small Phase-0 graph this exhaustively enumerates every simple path with a hop count in
``[min_hops, max_hops]``. Hub-avoidance and rare-edge preference are realized in the *surprise*
ranking rather than pruned here (see ADR 0001) — cleaner, and exactly equivalent for small graphs.
A guided walk replaces this for the larger graphs of Phase 1.
"""

from __future__ import annotations

from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import Hop, Path


def enumerate_paths(graph: KnowledgeGraph, source: str, min_hops: int, max_hops: int) -> list[Path]:
    """Enumerate all simple paths from ``source`` with ``min_hops..max_hops`` edges.

    Parallel edges (distinct statements between the same two nodes) yield distinct paths. Output
    order is deterministic.

    Raises:
        KeyError: If ``source`` is not a node in the graph.
    """
    if not graph.has_node(source):
        raise KeyError(source)

    results: list[Path] = []

    def walk(current: str, visited: frozenset[str], hops: list[Hop]) -> None:
        if len(hops) >= min_hops:
            results.append(_build_path(source, hops))
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


def _build_path(source: str, hops: list[Hop]) -> Path:
    """Assemble a :class:`Path` from the source node and the ordered hops."""
    node_ids = (source, *(hop.to_id for hop in hops))
    return Path(node_ids=node_ids, hops=tuple(hops))
