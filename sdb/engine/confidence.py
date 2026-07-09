"""Deterministic *trust* scoring — grounded, reproducible, and LLM-free.

Per statement: multi-source corroboration (noisy-OR), entity-link quality, and validation penalties.
Per path: the product of edge confidences (a chain is only as trustworthy as its weakest link).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sdb.constants import PENALTY_DATE_DISORDER, PENALTY_TEMPORAL_IMPLAUSIBLE
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Predicate
from sdb.schema.models import Path, Statement


def noisy_or(values: Iterable[float]) -> float:
    """Combine independent evidence: ``1 - ∏(1 - value)``. Empty input → ``0.0``."""
    complement = 1.0
    for value in values:
        complement *= 1.0 - value
    return 1.0 - complement


def _clamp01(value: float) -> float:
    """Clamp a value to the closed interval [0, 1]."""
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class TrustScore:
    """A path trust score with its per-edge breakdown."""

    total: float
    edge_confidences: tuple[float, ...]


def statement_confidence(graph: KnowledgeGraph, statement: Statement) -> float:
    """Deterministic confidence (0..1) that a single statement is true."""
    confidence = noisy_or(source.reliability for source in statement.sources)
    confidence *= statement.link_quality
    for penalty in _validation_penalties(graph, statement):
        confidence *= 1.0 - penalty
    return _clamp01(confidence)


def _validation_penalties(graph: KnowledgeGraph, statement: Statement) -> list[float]:
    """Return the multiplicative penalties triggered by deterministic validators."""
    penalties: list[float] = []
    subject = graph.node(statement.subject)
    obj = graph.node(statement.object)

    for node in (subject, obj):
        if (
            node.start_year is not None
            and node.end_year is not None
            and node.start_year > node.end_year
        ):
            penalties.append(PENALTY_DATE_DISORDER)

    if statement.predicate is Predicate.FOLLOWS:
        subject_mid = subject.midpoint_year
        object_mid = obj.midpoint_year
        # "A follows B" is implausible if A predates B.
        if subject_mid is not None and object_mid is not None and subject_mid < object_mid:
            penalties.append(PENALTY_TEMPORAL_IMPLAUSIBLE)

    return penalties


def score_trust(graph: KnowledgeGraph, path: Path) -> TrustScore:
    """Compute path trust as the product (weakest-link) of edge confidences."""
    edge_confidences = tuple(statement_confidence(graph, hop.statement) for hop in path.hops)
    total = 1.0
    for confidence in edge_confidences:
        total *= confidence
    return TrustScore(total=total, edge_confidences=edge_confidences)
