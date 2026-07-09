"""Deterministic, information-theoretic *surprise* scoring for a path.

surprise = W_RARITY·Σ rarity + W_DOMAIN·domain_jumps + W_TEMPORAL·temporal_gap
           + W_LENGTH·length_bonus + W_ENDPOINT·endpoint_unexpectedness - W_HUB·hub_penalty

All weights live in :mod:`sdb.constants`; the formula is reproducible by hand.
"""

from __future__ import annotations

from dataclasses import dataclass

from sdb.constants import (
    HUB_DEGREE_THRESHOLD,
    TEMPORAL_NORM_YEARS,
    W_DOMAIN,
    W_ENDPOINT,
    W_HUB,
    W_LENGTH,
    W_RARITY,
    W_TEMPORAL,
)
from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import Path


@dataclass(frozen=True)
class SurpriseScore:
    """A surprise score with its component breakdown (for transparency and testing)."""

    total: float
    sum_rarity: float
    domain_jumps: int
    temporal_gap: float  # normalized (years / TEMPORAL_NORM_YEARS)
    length_bonus: int
    endpoint_unexpectedness: float  # -log2 P(endpoint | start) from co-occurrence; 0 without data
    hub_penalty: float


def score_surprise(graph: KnowledgeGraph, path: Path) -> SurpriseScore:
    """Compute the deterministic surprise score for ``path``."""
    sum_rarity = sum(graph.rarity(hop.statement.predicate) for hop in path.hops)
    domain_jumps = _domain_jumps(graph, path)
    temporal_gap = _temporal_gap(graph, path)
    length_bonus = max(0, path.length - 2)
    endpoint_unexpectedness = graph.endpoint_unexpectedness(path.node_ids[0], path.node_ids[-1])
    hub_penalty = _hub_penalty(graph, path)
    total = (
        W_RARITY * sum_rarity
        + W_DOMAIN * domain_jumps
        + W_TEMPORAL * temporal_gap
        + W_LENGTH * length_bonus
        + W_ENDPOINT * endpoint_unexpectedness
        - W_HUB * hub_penalty
    )
    return SurpriseScore(
        total=total,
        sum_rarity=sum_rarity,
        domain_jumps=domain_jumps,
        temporal_gap=temporal_gap,
        length_bonus=length_bonus,
        endpoint_unexpectedness=endpoint_unexpectedness,
        hub_penalty=hub_penalty,
    )


def _domain_jumps(graph: KnowledgeGraph, path: Path) -> int:
    """Count consecutive nodes whose thematic domain differs."""
    return sum(
        graph.node(a).domain != graph.node(b).domain
        for a, b in zip(path.node_ids, path.node_ids[1:], strict=False)
    )


def _temporal_gap(graph: KnowledgeGraph, path: Path) -> float:
    """Sum of absolute midpoint-year gaps across hops, normalized by TEMPORAL_NORM_YEARS."""
    total = 0.0
    for a, b in zip(path.node_ids, path.node_ids[1:], strict=False):
        ma = graph.node(a).midpoint_year
        mb = graph.node(b).midpoint_year
        if ma is not None and mb is not None:
            total += abs(ma - mb)
    return total / TEMPORAL_NORM_YEARS


def _hub_penalty(graph: KnowledgeGraph, path: Path) -> float:
    """Penalize routing *through* high-degree hub nodes (endpoints are exempt)."""
    penalty = 0.0
    for node_id in path.node_ids[1:-1]:
        excess = graph.degree(node_id) - HUB_DEGREE_THRESHOLD
        if excess > 0:
            penalty += excess / HUB_DEGREE_THRESHOLD
    return penalty
