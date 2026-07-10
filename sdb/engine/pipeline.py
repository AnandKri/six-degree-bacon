"""The discovery pipeline: topic → ranked, narrated, sourced results."""

from __future__ import annotations

from sdb.constants import (
    MAX_HOPS_DEFAULT,
    MIN_HOPS_DEFAULT,
    POSSIBLY_THRESHOLD,
    TOP_DEFAULT,
)
from sdb.engine.confidence import score_trust
from sdb.engine.narrate import narrate
from sdb.engine.surprise import score_surprise
from sdb.engine.traversal import enumerate_paths
from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import DiscoveryResult


class TopicNotFoundError(LookupError):
    """Raised when a topic cannot be resolved to a node; carries near-miss suggestions."""

    def __init__(self, topic: str, suggestions: list[str]) -> None:
        """Store the unresolved ``topic`` and suggested alternatives."""
        self.topic = topic
        self.suggestions = suggestions
        super().__init__(f"topic not found: {topic!r}")


def discover(
    graph: KnowledgeGraph,
    topic: str,
    *,
    min_hops: int = MIN_HOPS_DEFAULT,
    max_hops: int = MAX_HOPS_DEFAULT,
    top: int = TOP_DEFAULT,
    min_trust: float = POSSIBLY_THRESHOLD,
) -> list[DiscoveryResult]:
    """Discover the highest-scoring "wow" paths from ``topic``.

    Each path scores ``surprise x trust``; results are ranked by that composite and deduplicated to
    the single best path per endpoint. Paths whose trust is below ``min_trust`` are dropped — the
    default (:data:`~sdb.constants.POSSIBLY_THRESHOLD`) is the "wow with evidence" gate; lower it to
    :data:`~sdb.constants.TRUST_FLOOR` to include speculative ``Possibly:`` paths.

    Raises:
        TopicNotFoundError: If ``topic`` does not resolve to a node.
    """
    source = graph.find_topic(topic)
    if source is None:
        raise TopicNotFoundError(topic, graph.suggest(topic))

    best_by_endpoint: dict[str, DiscoveryResult] = {}
    for path in enumerate_paths(graph, source, min_hops, max_hops):
        trust = score_trust(graph, path)
        if trust.total < min_trust:
            continue
        surprise = score_surprise(graph, path)
        til, possibly = narrate(graph, path, trust.total)
        result = DiscoveryResult(
            path=path,
            trust=trust.total,
            surprise=surprise.total,
            score=surprise.total * trust.total,
            til=til,
            possibly=possibly,
        )
        endpoint = path.node_ids[-1]
        incumbent = best_by_endpoint.get(endpoint)
        if incumbent is None or (result.score, result.trust) > (
            incumbent.score,
            incumbent.trust,
        ):
            best_by_endpoint[endpoint] = result

    ranked = sorted(
        best_by_endpoint.values(),
        key=lambda result: (result.score, result.trust),
        reverse=True,
    )
    return ranked[:top]
